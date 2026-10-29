from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Plan

# Create your views here.

@login_required
def plans_view(request):
    plans = Plan.objects.all().order_by('id')
    return render(request, 'plans.html', {'plans' : plans})