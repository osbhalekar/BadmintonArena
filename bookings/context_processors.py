from datetime import date, datetime

from django.db.models import Q

from .models import Booking, Slot


def sidebar_stats(request):
    if not request.user.is_authenticated:
        return {}

    today = date.today()
    now = datetime.now().time()

    live = (
        Slot.objects
        .filter(booking__user=request.user, booking__status=Booking.PAID)
        .exclude(status=Slot.CANCELLED)
    )
    finished = Q(date__lt=today) | Q(date=today, end_time__lte=now)

    return {
        'side_stats': {
            'bookings': Booking.objects.filter(user=request.user, status=Booking.PAID).count(),
            'upcoming': live.exclude(finished).count(),
            'completed': live.filter(finished).count(),
        }
    }