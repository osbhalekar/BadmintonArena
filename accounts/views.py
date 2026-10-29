from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages

import calendar
from datetime import date
import holidays

from bookings.models import Slot

# Create your views here.

User = get_user_model()

def auth_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'register':
            name = request.POST.get('name', '').strip()
            age = request.POST.get('age')
            gender = request.POST.get('gender')
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password')
            image = request.FILES.get('profile_image')

            if not(name and age and gender and email and password):
                messages.error(request, 'Please fill in all fields.')
            elif User.objects.filter(username = email).exists():
                messages.error(request, 'This email is already registered.')
            else:
                User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=name,
                    age=age,
                    gender=gender,
                    profile_image=image,
                )
                messages.success(request, 'Account created successfully. Please log in.')
                return redirect('auth')

        elif action == 'login':
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            messages.error(request, 'Invalid email or password.')

    return render(request, 'auth.html')

def logout_view(request):
    logout(request)
    return redirect('auth')

@login_required
def dashboard_view(request):
    today = date.today()
    year = today.year
    holiday_map = holidays.India(years=year)   # {date: holiday name}

    # Stats for the four cards
    mine = Slot.objects.filter(booking__user=request.user, booking__status='paid')
    stats = {
        'total': mine.count(),
        'active': mine.exclude(status=Slot.CANCELLED).filter(date__gte=today).count(),
        'shifted': mine.filter(status=Slot.SHIFTED).count(),
        'cancelled': mine.filter(status=Slot.CANCELLED).count(),
    }

    # Year calendar
    cal = calendar.Calendar(firstweekday=6)    # week starts on Sunday
    months = []
    for m in range(1, 13):
        weeks = []
        for week in cal.monthdayscalendar(year, m):
            row = []
            for d in week:
                if d == 0:
                    row.append({'day': 0, 'holiday': False, 'name': '', 'today': False})
                else:
                    dt = date(year, m, d)
                    row.append({
                        'day': d,
                        'holiday': dt in holiday_map,
                        'name': holiday_map.get(dt, ''),
                        'today': dt == today,
                    })
            weeks.append(row)
        months.append({'name': calendar.month_name[m], 'weeks': weeks})

    return render(request, 'dashboard.html', {
        'months': months,
        'year': year,
        'stats': stats,
    })