import hashlib
import hmac
import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import transaction
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.core.validators import validate_email

from .exchange import get_or_update_exchange_rate
from .models import Payment, Subscription, PaystackWebhookEvent
from .paystack import Paystack


logger = logging.getLogger(__name__)
UserModel = get_user_model()


TIERS = {
    "tier-1": {
        "tier_label": "Tier 1",
        "name": "Every bit helps",
        "amount": 50,
        "display_amount": "R50 / month",
        "benefits": [
            "Name in our supporters list",
            "Helps spread knowledge",
        ],
        "cta": "Chip in monthly",
        "amount_type": "fixed",
        "default_frequency": "monthly",
        "contribution_label": "Monthly Contribution",
    },
    "tier-2": {
        "tier_label": "Tier 2",
        "name": "Support the journey",
        "display_amount": "Your choice",
        "benefits": [
            "Behind-the-scenes updates",
            "Vote on features and roadmaps",
        ],
        "cta": "Support the journey",
        "amount_type": "custom",
        "default_frequency": "once",
        "contribution_label": "Single Contribution",
    },
    "tier-3": {
        "tier_label": "Tier 3",
        "name": "Traders Club",
        "amount": 8800,
        "display_amount": "R8800",
        "benefits": [
            "Discuss our roadmap with us",
            "Meet the founders",
        ],
        "cta": "Start building with us",
        "amount_type": "fixed",
        "default_frequency": "once",
        "contribution_label": "Single Contribution",
    },
}


def _convert_zar_to_usd(amount_zar: Decimal, rate: Decimal) -> Decimal:
    return (amount_zar * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_currency(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_decimal(value: str):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def contribute(request):
    exchange_info = get_or_update_exchange_rate()
    try:
        usd_to_zar = (Decimal("1") / exchange_info.rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ZeroDivisionError):
        usd_to_zar = None
    tiers = []
    for key, data in TIERS.items():
        tier = {"key": key, **data}
        if data.get("amount_type") == "fixed" and data.get("amount") is not None:
            amount_zar = Decimal(data["amount"])
            tier["usd_amount"] = _convert_zar_to_usd(amount_zar, exchange_info.rate)
        tiers.append(tier)

    return render(request, "payments/contribute.html", {
        "tiers": tiers,
        "exchange_rate": exchange_info,
        "exchange_rate_url": settings.EXCHANGE_RATE_DISPLAY_URL,
        "exchange_rate_inverse": usd_to_zar,
    })


def contribute_checkout(request):
    tier_key = request.GET.get("tier") or request.POST.get("tier") or "tier-1"
    tier = TIERS.get(tier_key)

    if not tier:
        raise Http404("Tier not found")

    exchange_info = get_or_update_exchange_rate()
    try:
        usd_to_zar = (Decimal("1") / exchange_info.rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ZeroDivisionError):
        usd_to_zar = None
    tier_usd_amount = None
    if tier.get("amount_type") == "fixed" and tier.get("amount") is not None:
        tier_usd_amount = _convert_zar_to_usd(Decimal(tier["amount"]), exchange_info.rate)

    amount_value = tier.get("amount") if tier.get("amount_type") == "fixed" else ""
    if tier.get("amount_type") == "fixed" and amount_value is not None:
        amount_value = f"{Decimal(amount_value):.2f}" if not isinstance(amount_value, str) else amount_value
    frequency = tier.get("default_frequency", "once")

    email_value = request.user.email if request.user.is_authenticated else ""
    supporter_name_value = ""
    updates_email_value = ""
    show_updates_email = tier_key in {"tier-2", "tier-3"}

    amount_usd_value = ""
    if tier_usd_amount is not None:
        amount_usd_value = f"{tier_usd_amount:.2f}"

    context = {
        "tier": tier,
        "tier_key": tier_key,
        "public_key": settings.PAYSTACK_PUBLIC_KEY,
        "amount_value": amount_value,
        "frequency": frequency,
        "email_value": email_value,
        "supporter_name_value": supporter_name_value,
        "updates_email_value": updates_email_value,
        "show_updates_email": show_updates_email,
        "exchange_rate": exchange_info,
        "tier_usd_amount": tier_usd_amount,
        "exchange_rate_url": settings.EXCHANGE_RATE_DISPLAY_URL,
        "exchange_rate_inverse": usd_to_zar,
        "amount_usd_value": amount_usd_value,
    }

    if request.method == "POST":
        raw_amount = request.POST.get("amount")
        raw_amount_usd = request.POST.get("amount_usd")
        frequency_choice = request.POST.get("frequency", frequency)
        email_input = request.user.email if request.user.is_authenticated else request.POST.get("email", "").strip()
        supporter_name_input = request.POST.get("supporter_name", "").strip()
        updates_email_input = request.POST.get("updates_email", "").strip() if show_updates_email else ""
        context["email_value"] = email_input
        context["supporter_name_value"] = supporter_name_input
        context["updates_email_value"] = updates_email_input

        if tier.get("amount_type") == "fixed":
            amount_zar = Decimal(tier["amount"])
            amount_usd = _convert_zar_to_usd(amount_zar, exchange_info.rate)
            context["amount_value"] = f"{amount_zar:.2f}"
            context["amount_usd_value"] = f"{amount_usd:.2f}"
        else:
            parsed_zar = _parse_decimal(raw_amount)
            parsed_usd = _parse_decimal(raw_amount_usd)
            amount_zar = None
            amount_usd = None

            if parsed_zar is not None:
                amount_zar = _normalize_currency(parsed_zar)
            elif parsed_usd is not None:
                try:
                    amount_zar = _normalize_currency(parsed_usd / exchange_info.rate)
                except (InvalidOperation, ZeroDivisionError):
                    amount_zar = None
            if amount_zar is None:
                context.update({
                    "error": "Please enter a valid amount in ZAR or USD.",
                    "amount_value": raw_amount or "",
                    "amount_usd_value": raw_amount_usd or "",
                    "frequency": frequency_choice,
                })
                return render(request, "payments/checkout.html", context)

            amount_usd = _convert_zar_to_usd(amount_zar, exchange_info.rate)

            context["amount_value"] = f"{amount_zar:.2f}"
            context["amount_usd_value"] = f"{amount_usd:.2f}"

        if tier.get("allow_frequency"):
            if frequency_choice not in {"once", "monthly"}:
                frequency_choice = tier.get("default_frequency", "once")
        else:
            frequency_choice = tier.get("default_frequency", "once")

        context["frequency"] = frequency_choice

        if amount_zar <= 0:
            context["error"] = "Amount must be greater than zero."
            return render(request, "payments/checkout.html", context)

        amount_cents = int((amount_zar * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        email = email_input

        if not email:
            context["error"] = "Please provide a valid email address."
            context["email_value"] = email
            return render(request, "payments/checkout.html", context)

        if updates_email_input:
            try:
                validate_email(updates_email_input)
            except ValidationError:
                context["error"] = "Please provide a valid email address for updates."
                return render(request, "payments/checkout.html", context)

        plan_code = None
        if frequency_choice == "monthly":
            plan_code = settings.PAYSTACK_PLAN_CODE_MAP.get(tier_key, {}).get(frequency_choice)
            if not plan_code:
                raise ImproperlyConfigured(f"Missing Paystack plan code for {tier_key}:{frequency_choice}.")

        payment = Payment.objects.create(
            user=request.user if request.user.is_authenticated else None,
            amount=amount_cents,
            email=email,
            tier=tier_key,
            frequency=frequency_choice,
            plan_code=plan_code,
            supporter_name=supporter_name_input,
            updates_email=updates_email_input,
        )

        callback_url = request.build_absolute_uri(reverse("payments:contribute_callback"))
        metadata = {
            "tier_key": tier_key,
            "tier_label": tier.get("tier_label"),
            "frequency": frequency_choice,
            "user_id": request.user.pk if request.user.is_authenticated else None,
            "payment_reference": payment.reference,
            "custom_fields": [
                {
                    "display_name": "Tier",
                    "variable_name": "tier",
                    "value": tier.get("tier_label", tier_key),
                },
                {
                    "display_name": "Frequency",
                    "variable_name": "frequency",
                    "value": frequency_choice,
                },
            ],
        }
        if supporter_name_input:
            metadata["custom_fields"].append({
                "display_name": "Supporter Name",
                "variable_name": "supporter_name",
                "value": supporter_name_input,
            })
        if updates_email_input:
            metadata["custom_fields"].append({
                "display_name": "Updates Email",
                "variable_name": "updates_email",
                "value": updates_email_input,
            })
        if plan_code:
            metadata["plan_code"] = plan_code

        try:
            response = Paystack().initialize(
                email=email,
                amount=amount_cents,  # Paystack expects amount even when attaching a plan.
                callback_url=callback_url,
                reference=payment.reference,
                metadata=metadata,
                plan_code=plan_code,
            )
        except ValueError as exc:
            payment.delete()
            context["error"] = str(exc)
            return render(request, "payments/checkout.html", context)

        if not response.get("status") or "data" not in response:
            payment.delete()
            context["error"] = response.get("message") or "We couldn't start the checkout session. Please try again."
            return render(request, "payments/checkout.html", context)

        authorization_url = response["data"].get("authorization_url")
        if not authorization_url:
            payment.delete()
            context["error"] = "We couldn't start the checkout session. Please try again."
            return render(request, "payments/checkout.html", context)

        return redirect(authorization_url)

    return render(request, "payments/checkout.html", context)


def contribute_callback(request):
    reference = request.GET.get("trxref") or request.GET.get("reference")
    if not reference:
        return render(request, "payments/failure.html", {"message": "Missing transaction reference."})

    payment = Payment.objects.filter(reference=reference).select_related("subscription").first()
    if not payment:
        return render(request, "payments/failure.html", {"message": "Invalid transaction reference."})

    if payment.plan_code:
        return render(request, "payments/subscription_processing.html", {
            "payment": payment,
        })

    if payment.verified or payment.verify():
        return render(request, "payments/success.html", {
            "payment": payment,
            "amount_rands": payment.amount / 100,
        })

    return render(request, "payments/failure.html", {"payment": payment})


@csrf_exempt
@require_POST
def paystack_webhook(request):
    raw_body = request.body
    signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE", "")
    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()
    signature_valid = hmac.compare_digest(signature or "", computed_signature)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.warning("Received invalid JSON payload from Paystack.")
        return JsonResponse({"detail": "Invalid payload."}, status=400)

    event = payload.get("event") or ""
    data = payload.get("data") or {}
    subscription_code = _extract_subscription_code(data)
    reference = data.get("reference") or ""

    PaystackWebhookEvent.objects.create(
        event=event,
        reference=reference,
        subscription_code=subscription_code or "",
        signature=signature or "",
        signature_valid=signature_valid,
        payload=payload,
    )

    if not signature_valid:
        logger.warning("Rejected Paystack webhook %s due to signature mismatch.", event)
        return HttpResponseForbidden("Invalid signature.")

    if not event:
        return JsonResponse({"detail": "Missing event type."}, status=400)

    with transaction.atomic():
        if event == "subscription.create":
            _upsert_subscription_from_payload(data)
        elif event == "charge.success":
            if _is_subscription_charge(data):
                subscription = _upsert_subscription_from_payload(data)
                _record_subscription_charge(data, subscription)
            else:
                _record_one_off_charge(data)
        elif event == "invoice.payment_failed":
            _mark_subscription_status(subscription_code, Subscription.Status.PAST_DUE)
        elif event == "subscription.disable":
            _mark_subscription_status(subscription_code, Subscription.Status.CANCELED)
        elif event == "subscription.enable":
            _mark_subscription_status(subscription_code, Subscription.Status.ACTIVE)
        else:
            logger.info("Unhandled Paystack webhook event: %s", event)

    return JsonResponse({"status": "ok"})


def _coerce_metadata(raw_metadata):
    if isinstance(raw_metadata, dict):
        return raw_metadata
    if isinstance(raw_metadata, str):
        try:
            return json.loads(raw_metadata)
        except json.JSONDecodeError:
            return {}
    return {}


def _extract_subscription_code(data):
    subscription = data.get("subscription") or {}
    return (
        data.get("subscription_code")
        or subscription.get("subscription_code")
        or subscription.get("code")
        or ""
    )


def _extract_plan_code(data, metadata=None):
    metadata = metadata or {}
    subscription = data.get("subscription") or {}
    plan = data.get("plan") or subscription.get("plan") or {}
    if isinstance(plan, dict):
        return plan.get("plan_code") or plan.get("code") or plan.get("slug")
    if isinstance(plan, str):
        return plan
    return metadata.get("plan_code")


def _parse_next_payment_date(value):
    if not value:
        return None
    dt = parse_datetime(value)
    if not dt:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_default_timezone())
    return dt


def _resolve_user(metadata, email):
    user_id = metadata.get("user_id") if metadata else None
    user = None
    if user_id:
        try:
            user = UserModel.objects.filter(pk=int(user_id)).first()
        except (ValueError, TypeError):
            user = None
    if not user and email:
        user = UserModel.objects.filter(email__iexact=email).first()
    return user


def _upsert_subscription_from_payload(data):
    metadata = _coerce_metadata(data.get("metadata") or (data.get("subscription") or {}).get("metadata"))
    subscription_code = _extract_subscription_code(data)
    if not subscription_code:
        logger.warning("Paystack subscription payload missing subscription_code.")
        return None

    customer = data.get("customer") or (data.get("subscription") or {}).get("customer") or {}
    customer_code = customer.get("customer_code") or customer.get("code") or ""
    email = customer.get("email")

    plan_code = _extract_plan_code(data, metadata)
    if not plan_code:
        logger.warning("Paystack subscription payload missing plan_code for subscription %s.", subscription_code)
        return None

    user = _resolve_user(metadata, email)

    authorization = data.get("authorization") or (data.get("subscription") or {}).get("authorization") or {}
    card_brand = authorization.get("card_type") or authorization.get("brand") or ""
    card_last4 = authorization.get("last4") or authorization.get("last_4") or ""

    next_payment_str = data.get("next_payment_date") or (data.get("subscription") or {}).get("next_payment_date")
    next_payment_date = _parse_next_payment_date(next_payment_str)

    status = (data.get("status") or (data.get("subscription") or {}).get("status") or "active").lower()
    if status not in Subscription.Status.values:
        status = Subscription.Status.ACTIVE

    defaults = {
        "user": user,
        "plan_code": plan_code,
        "customer_code": customer_code,
        "status": status,
        "next_payment_date": next_payment_date,
        "card_brand": card_brand,
        "card_last4": card_last4,
    }

    subscription, _ = Subscription.objects.update_or_create(
        subscription_code=subscription_code,
        defaults=defaults,
    )

    if user and subscription.user_id != user.id:
        subscription.user = user
        subscription.save(update_fields=["user"])

    return subscription


def _is_subscription_charge(data):
    return bool(_extract_subscription_code(data) or _extract_plan_code(data))


def _record_subscription_charge(data, subscription):
    if not subscription:
        logger.warning("Subscription charge received without a matching subscription record.")

    metadata = _coerce_metadata(data.get("metadata"))
    plan_code = _extract_plan_code(data, metadata) or (subscription.plan_code if subscription else None)
    reference = data.get("reference")
    if not reference:
        logger.warning("Subscription charge missing reference; skipping.")
        return

    customer = data.get("customer") or {}
    email = customer.get("email") or (subscription.user.email if subscription and subscription.user else "")
    amount = data.get("amount")
    try:
        amount = int(amount) if amount is not None else None
    except (TypeError, ValueError):
        amount = None

    user = subscription.user if subscription and subscription.user else _resolve_user(metadata, email)
    tier_key = metadata.get("tier_key")
    frequency = metadata.get("frequency") or "monthly"

    payment = Payment.objects.select_for_update().filter(reference=reference).first()
    update_fields = {"verified", "paid_via_subscription", "plan_code", "subscription"}

    if payment:
        payment.plan_code = plan_code
        payment.subscription = subscription
        payment.paid_via_subscription = True
        payment.verified = True
        if amount:
            payment.amount = amount
            update_fields.add("amount")
        if tier_key and tier_key != payment.tier:
            payment.tier = tier_key
            update_fields.add("tier")
        if frequency and frequency != payment.frequency:
            payment.frequency = frequency
            update_fields.add("frequency")
        if email and email != payment.email:
            payment.email = email
            update_fields.add("email")
        if user and payment.user_id != getattr(user, "id", None):
            payment.user = user
            update_fields.add("user")
        payment.save(update_fields=list(update_fields))
    else:
        if amount is None:
            logger.warning("Unable to record subscription payment without amount for reference %s.", reference)
            return
        Payment.objects.create(
            user=user,
            amount=amount,
            email=email,
            reference=reference,
            verified=True,
            tier=tier_key,
            frequency=frequency,
            plan_code=plan_code,
            subscription=subscription,
            paid_via_subscription=True,
        )

    updated_fields = []
    next_payment_str = data.get("next_payment_date") or (data.get("subscription") or {}).get("next_payment_date")
    next_payment_date = _parse_next_payment_date(next_payment_str)
    authorization = data.get("authorization") or {}
    card_brand = authorization.get("card_type") or authorization.get("brand")
    card_last4 = authorization.get("last4") or authorization.get("last_4")

    if subscription:
        if subscription.status != Subscription.Status.ACTIVE:
            subscription.status = Subscription.Status.ACTIVE
            updated_fields.append("status")
        if next_payment_date and subscription.next_payment_date != next_payment_date:
            subscription.next_payment_date = next_payment_date
            updated_fields.append("next_payment_date")
        if card_brand and subscription.card_brand != card_brand:
            subscription.card_brand = card_brand
            updated_fields.append("card_brand")
        if card_last4 and subscription.card_last4 != card_last4:
            subscription.card_last4 = card_last4
            updated_fields.append("card_last4")
        if user and subscription.user_id != getattr(user, "id", None):
            subscription.user = user
            updated_fields.append("user")
        if updated_fields:
            subscription.save(update_fields=updated_fields)


def _record_one_off_charge(data):
    reference = data.get("reference")
    if not reference:
        return

    payment = Payment.objects.select_for_update().filter(reference=reference).first()
    if not payment:
        return

    amount = data.get("amount")
    try:
        amount = int(amount) if amount is not None else None
    except (TypeError, ValueError):
        amount = None

    update_fields = {"verified"}
    payment.verified = True
    if amount and amount != payment.amount:
        payment.amount = amount
        update_fields.add("amount")
    payment.save(update_fields=list(update_fields))


def _mark_subscription_status(subscription_code, status):
    if not subscription_code:
        return
    if status not in Subscription.Status.values:
        status = Subscription.Status.ACTIVE

    subscription = Subscription.objects.select_for_update().filter(subscription_code=subscription_code).first()
    if not subscription:
        return

    if subscription.status == status:
        return

    subscription.status = status
    subscription.save(update_fields=["status"])
