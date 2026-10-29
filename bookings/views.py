import uuid
from datetime import date, datetime, time, timedelta

import holidays as pyholidays
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from plans.models import Plan
from .models import Booking, Slot

OPEN_HOUR = 6
CLOSE_HOUR = 22
COURT = 1
HOLD_MINUTES = 10   # how long unpaid slots stay reserved


class BookingError(Exception):
    pass


# ---------- helpers ----------
def release_expired():
    cutoff = timezone.now() - timedelta(minutes=HOLD_MINUTES)
    Booking.objects.filter(status=Booking.PENDING, created_at__lt=cutoff).delete()


def parse_picked(raw):
    days = []
    for part in raw.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            days.append(date.fromisoformat(part))
        except ValueError:
            return None
    return days


def week_start(d):
    # weeks start on Sunday, same as the calendar
    return d - timedelta(days=(d.weekday() + 1) % 7)


def slot_taken(day, start_t, end_t):
    return Slot.objects.filter(
        court=COURT, date=day, start_time__lt=end_t, end_time__gt=start_t,
    ).exclude(status=Slot.CANCELLED).exists()


def next_free_day(day, holiday_map, start_t, end_t):
    for i in range(1, 15):
        nd = day + timedelta(days=i)
        if nd in holiday_map or slot_taken(nd, start_t, end_t):
            continue
        return nd
    return None


def validate_picks(plan, picked, today):
    need = 2 if plan.plan_type == 'monthly' else plan.days_allowed
    if len(picked) != need or len(set(picked)) != need:
        return f'Please pick exactly {need} different days.'
    for d in picked:
        if d <= today or d > today + timedelta(days=366):
            return 'Please pick days from tomorrow onwards, within the next 12 months.'
    if plan.plan_type == 'weekly':
        if len({week_start(d) for d in picked}) != 1:
            return 'Both days must be in the same week.'
    elif plan.plan_type == 'monthly':
        if len({d.weekday() for d in picked}) != 2:
            return 'Choose two different weekdays.'
    else:
        if len({(d.year, d.month) for d in picked}) != 1:
            return 'All days must be in the same month.'
    return None


# ---------- save (creates a pending booking, then goes to payment) ----------
def save_booking(request, plan, today, holiday_map):
    back = redirect('book', plan_type=plan.plan_type)

    try:
        players = int(request.POST.get('players', ''))
        start_hour = int(request.POST.get('start', '').split(':')[0])
    except ValueError:
        messages.error(request, 'Invalid booking details.')
        return back

    if players not in (2, 4):
        messages.error(request, 'Choose Singles Battle (2 players) or Doubles Battle (4 players).')
        return back
    if start_hour < OPEN_HOUR or start_hour * 60 + plan.duration_minutes > CLOSE_HOUR * 60:
        messages.error(request, 'That start time is outside opening hours.')
        return back

    picked = parse_picked(request.POST.get('picked', ''))
    if picked is None:
        messages.error(request, 'Invalid dates.')
        return back
    error = validate_picks(plan, picked, today)
    if error:
        messages.error(request, error)
        return back

    # Standard repeats each chosen weekday for 4 weeks
    weeks = plan.days_allowed // 2 if plan.plan_type == 'monthly' else 1
    wanted = sorted({d + timedelta(days=7 * i) for d in picked for i in range(weeks)})

    start_t = time(start_hour, 0)
    end_t = (datetime.combine(today, start_t) + timedelta(minutes=plan.duration_minutes)).time()

    try:
        with transaction.atomic():
            booking = Booking.objects.create(
                user=request.user,
                plan=plan,
                players=players,
                start_time=start_t,
                price_per_person=plan.price_per_person,
                discount_percent=plan.discount_percent,
                status=Booking.PENDING,
            )
            used = set()
            for d in wanted:
                final, status = d, Slot.ACTIVE
                if d in holiday_map or d in used:
                    final = next_free_day(d, holiday_map, start_t, end_t)
                    if final is None:
                        raise BookingError(f'No free day found after {d:%a %d %b}. Please choose other days.')
                    status = Slot.SHIFTED
                elif slot_taken(d, start_t, end_t):
                    raise BookingError(f'{d:%a %d %b} is already booked at that time.')
                used.add(final)
                Slot.objects.create(
                    booking=booking, court=COURT, date=final, original_date=d,
                    start_time=start_t, end_time=end_t, status=status,
                )
    except BookingError as exc:
        messages.error(request, str(exc))
        return back
    except IntegrityError:
        messages.error(request, 'Someone just booked one of those slots. Please try again.')
        return back

    return redirect('payment', pk=booking.pk)


# ---------- booking page ----------
@login_required
def book_view(request, plan_type):
    release_expired()
    plan = get_object_or_404(Plan, plan_type=plan_type)
    today = date.today()
    holiday_map = pyholidays.India(years=range(today.year, today.year + 3))

    if request.method == 'POST':
        return save_booking(request, plan, today, holiday_map)

    holiday_dict = {d.isoformat(): name for d, name in holiday_map.items()}

    taken = (
        Slot.objects.filter(date__gt=today, date__lte=today + timedelta(days=400))
        .exclude(status=Slot.CANCELLED)
        .values('date', 'start_time', 'end_time')
    )
    booked = [
        {
            'date': t['date'].isoformat(),
            'start': t['start_time'].strftime('%H:%M'),
            'end': t['end_time'].strftime('%H:%M'),
        }
        for t in taken
    ]

    config = {
        'plan_type': plan.plan_type,
        'days_allowed': plan.days_allowed,
        'duration_minutes': plan.duration_minutes,
        'price_per_person': plan.price_per_person,
        'discount_percent': plan.discount_percent,
        'open_hour': OPEN_HOUR,
        'close_hour': CLOSE_HOUR,
        'today': today.isoformat(),
        'holidays': holiday_dict,
        'booked': booked,
    }
    return render(request, 'book.html', {'plan': plan, 'config': config})


# ---------- test payment ----------
@login_required
def payment_view(request, pk):
    release_expired()
    booking = Booking.objects.filter(pk=pk, user=request.user, status=Booking.PENDING).first()
    if booking is None:
        messages.error(request, 'This payment session has expired. Please book again.')
        return redirect('plans')

    return render(request, 'payment.html', {
        'booking': booking,
        'amount': booking.total_price,
        'description': f'{booking.plan.name} plan, {booking.get_players_display()}, {booking.active_days} days',
    })


@login_required
def payment_confirm(request, pk):
    if request.method != 'POST':
        return redirect('payment', pk=pk)

    release_expired()
    booking = Booking.objects.filter(pk=pk, user=request.user, status=Booking.PENDING).first()
    if booking is None:
        messages.error(request, 'This payment session has expired. Please book again.')
        return redirect('plans')

    booking.status = Booking.PAID
    booking.razorpay_payment_id = f'mock_{uuid.uuid4().hex[:12]}'
    booking.save(update_fields=['status', 'razorpay_payment_id'])
    return redirect('booking_success')


@login_required
def booking_success(request):
    return render(request, 'booking_success.html')


# ---------- my bookings ----------
@login_required
def my_bookings(request):
    release_expired()
    bookings = (
        Booking.objects.filter(user=request.user, status=Booking.PAID)
        .select_related('plan')
        .prefetch_related('slots')
    )
    return render(request, 'my_bookings.html', {'bookings': bookings})


@login_required
def cancel_slot(request, pk):
    slot = get_object_or_404(Slot, pk=pk, booking__user=request.user, booking__status=Booking.PAID)
    if request.method == 'POST':
        if slot.status == Slot.CANCELLED:
            messages.info(request, 'That day is already cancelled.')
        elif slot.date <= date.today():
            messages.error(request, 'Past or same-day slots cannot be cancelled.')
        elif not slot.can_cancel:
            messages.error(request, 'Cancelling is only allowed within 24 hours of booking.')
        else:
            slot.status = Slot.CANCELLED
            slot.save(update_fields=['status'])
            messages.success(request, f'{slot.date:%d %b %Y} cancelled. New total: ₹{slot.booking.total_price}.')
    return redirect('my_bookings')