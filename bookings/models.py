from django.db import models
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

# Create your models here.

class Booking(models.Model):
    PLAYER_CHOICES = [(2, 'Singles Battle'), (4, 'Doubles Battle')]

    PENDING = 'pending'
    PAID = 'paid'
    STATUS_CHOICES = [(PENDING, 'Pending payment'), (PAID, 'Paid')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    plan = models.ForeignKey('plans.Plan', on_delete=models.PROTECT, related_name='bookings')
    players = models.PositiveSmallIntegerField(choices=PLAYER_CHOICES, default=2)
    start_time = models.TimeField()

    # Snapshot of the plan's price at booking time (later plan edits won't change old bookings)
    price_per_person = models.PositiveIntegerField(default=200)
    discount_percent = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PAID)
    razorpay_order_id = models.CharField(max_length=60, blank=True)
    razorpay_payment_id = models.CharField(max_length=60, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.plan.name} ({self.created_at:%d %b %Y})"

    @property
    def active_days(self):
        return self.slots.exclude(status=Slot.CANCELLED).count()

    @property
    def total_price(self):
        gross = self.price_per_person * self.players * self.active_days
        return gross - gross * self.discount_percent // 100

    @property
    def can_cancel(self):
        return timezone.now() - self.created_at < timedelta(hours=24)

    @property
    def cancel_deadline(self):
        return self.created_at + timedelta(hours=24)


class Slot(models.Model):
    ACTIVE = 'active'
    SHIFTED = 'shifted'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (SHIFTED, 'Holiday shifted'),
        (CANCELLED, 'Cancelled'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='slots')
    court = models.PositiveSmallIntegerField(default=1)
    date = models.DateField()
    original_date = models.DateField()        # the day the user first picked
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)

    class Meta:
        ordering = ['date', 'start_time']
        constraints = [
            # Safety net: no two non-cancelled slots on the same court, date and start time
            models.UniqueConstraint(
                fields=['court', 'date', 'start_time'],
                condition=~models.Q(status='cancelled'),
                name='unique_active_slot',
            ),
        ]

    def __str__(self):
        return f"{self.date} {self.start_time:%H:%M}-{self.end_time:%H:%M} ({self.status})"

    @property
    def can_cancel(self):
        return self.status != self.CANCELLED and self.booking.can_cancel


    @property
    def price(self):
        b = self.booking
        gross = b.price_per_person * b.players
        return gross - gross * b.discount_percent // 100