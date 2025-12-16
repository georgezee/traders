from decimal import Decimal
import secrets

from django.contrib.auth.models import User
from django.db import models

from .paystack import Paystack


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="subscriptions")
    plan_code = models.CharField(max_length=100)
    subscription_code = models.CharField(max_length=120, unique=True)
    customer_code = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    next_payment_date = models.DateTimeField(null=True, blank=True)
    card_brand = models.CharField(max_length=50, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user} · {self.plan_code}"


class Payment(models.Model):
    TIER_CHOICES = [
        ("tier-1", "Every bit helps"),
        ("tier-2", "Support the journey"),
        ("tier-3", "Traders Club"),
    ]
    FREQUENCY_CHOICES = [
        ("once", "Once-off"),
        ("monthly", "Monthly"),
    ]

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    amount = models.PositiveIntegerField(help_text="Amount in cents (ZAR)")
    email = models.EmailField()
    supporter_name = models.CharField(max_length=200, blank=True)
    updates_email = models.EmailField(blank=True)
    reference = models.CharField(max_length=100, unique=True, blank=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, null=True, blank=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, null=True, blank=True)
    plan_code = models.CharField(max_length=100, null=True, blank=True)
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments")
    paid_via_subscription = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def verify(self):
        status, data = Paystack().verify_payment(self.reference)
        if not status:
            return False

        if self.plan_code or data.get("plan"):
            # Subscription payments are confirmed via webhook events.
            return True

        if data.get("amount") == self.amount:
            self.verified = True
            self.save(update_fields=["verified"])
        return self.verified


class PaystackWebhookEvent(models.Model):
    event = models.CharField(max_length=100)
    reference = models.CharField(max_length=100, blank=True)
    subscription_code = models.CharField(max_length=120, blank=True)
    signature = models.CharField(max_length=200, blank=True)
    signature_valid = models.BooleanField(default=False)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.event} @ {self.received_at:%Y-%m-%d %H:%M:%S}"


class CurrencyConversionRate(models.Model):
    source_currency = models.CharField(max_length=3)
    target_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=16, decimal_places=8)
    fetched_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("source_currency", "target_currency")

    def __str__(self) -> str:
        return f"{self.source_currency}->{self.target_currency}: {Decimal(self.rate):f}"
