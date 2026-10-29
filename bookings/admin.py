from django.contrib import admin
from .models import Booking, Slot


class SlotInline(admin.TabularInline):
    model = Slot
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'players', 'status', 'start_time', 'active_days', 'total_price', 'created_at')
    list_filter = ('status', 'plan')
    inlines = [SlotInline]


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('booking', 'date', 'start_time', 'end_time', 'status', 'court')
    list_filter = ('status', 'date')