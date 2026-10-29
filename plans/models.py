from django.db import models

# Create your models here.

class Plan(models.Model):
    PLAN_TYPES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ]

    name = models.CharField(max_length=50)
    plan_type = models.CharField(max_length=10, choices=PLAN_TYPES, unique=True)
    description = models.TextField()
    price_per_person = models.PositiveIntegerField(default=200)
    discount_percent = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=120)
    days_allowed = models.PositiveIntegerField(default=8)

    def __str__(self):
        return self.name

    @property
    def original_per_person(self):
        # full price per person, before discount
        return self.price_per_person * self.days_allowed

    @property
    def discount_amount(self):
        return self.original_per_person * self.discount_percent // 100

    @property
    def total_per_person(self):
        return self.original_per_person - self.discount_amount

    @property
    def total_2_players(self):
        return self.total_per_person * 2

    @property
    def total_4_players(self):
        return self.total_per_person * 4