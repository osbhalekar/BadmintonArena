from django.contrib import admin
from .models import Plan

# Register your models here.

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan_type', 'description', 'price_per_person', 'discount_percent', 'duration_minutes', 'days_allowed')
