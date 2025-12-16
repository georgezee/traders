from django.contrib import admin

from .models import Payment, Subscription, PaystackWebhookEvent, CurrencyConversionRate


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "email",
        "amount_display",
        "reference",
        "plan_code",
        "subscription_code",
        "paid_via_subscription",
        "verified",
        "created_at",
    )
    list_filter = ("verified", "paid_via_subscription", "plan_code", "created_at")
    search_fields = (
        "email",
        "reference",
        "plan_code",
        "subscription__subscription_code",
        "user__username",
        "user__email",
    )
    readonly_fields = (
        "reference",
        "verified",
        "created_at",
        "user",
        "email",
        "amount",
        "plan_code",
        "subscription",
        "paid_via_subscription",
    )
    list_select_related = ("user", "subscription")

    def amount_display(self, obj):
        return f"R{obj.amount / 100:.2f}"
    amount_display.short_description = "Amount (ZAR)"

    def subscription_code(self, obj):
        return obj.subscription.subscription_code if obj.subscription else ""
    subscription_code.short_description = "Subscription"

    def has_add_permission(self, request):
        return False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plan_code",
        "subscription_code",
        "status",
        "next_payment_date",
        "updated_at",
    )
    list_filter = ("status", "plan_code")
    search_fields = (
        "subscription_code",
        "customer_code",
        "user__username",
        "user__email",
    )
    readonly_fields = ("subscription_code", "customer_code", "created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(PaystackWebhookEvent)
class PaystackWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event", "reference", "subscription_code", "signature_valid", "received_at")
    list_filter = ("event", "signature_valid")
    search_fields = ("event", "reference", "subscription_code")
    readonly_fields = (
        "event",
        "reference",
        "subscription_code",
        "signature",
        "signature_valid",
        "payload",
        "received_at",
    )
    ordering = ("-received_at",)


@admin.register(CurrencyConversionRate)
class CurrencyConversionRateAdmin(admin.ModelAdmin):
    list_display = ("source_currency", "target_currency", "rate", "fetched_at", "updated_at")
    search_fields = ("source_currency", "target_currency")
    list_filter = ("source_currency", "target_currency")
