from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.models import Feedback
from config.metadata import PageMeta, build_json_ld_webpage, build_page_meta
from payments.exchange import get_or_update_exchange_rate
from payments.views import TIERS


def _build_home_context(request, *, title: str, description: str, canonical_path: str):
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
            tier["usd_amount"] = (amount_zar * exchange_info.rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tiers.append(tier)

    canonical_url = request.build_absolute_uri(canonical_path)
    metadata = PageMeta(
        title=title,
        description=description,
        canonical_path=canonical_path,
        json_ld=build_json_ld_webpage(title, description, canonical_url),
    )

    return {
        "tiers": tiers,
        "exchange_rate": exchange_info,
        "exchange_rate_inverse": usd_to_zar,
        "exchange_rate_url": settings.EXCHANGE_RATE_DISPLAY_URL,
        "page_meta": build_page_meta(request, metadata),
    }

def home(request):
    context = _build_home_context(
        request,
        title="Traders",
        description="We enable small traders to provide their services efficiently.",
        canonical_path="/",
    )
    return render(request, "home/home.html", context)


def faq(request):
    title = "Frequently Asked Questions"
    description = "Answers to common questions about Traders."
    canonical_path = "/faq"
    canonical_url = request.build_absolute_uri(canonical_path)
    metadata = PageMeta(
        title=title,
        description=description,
        canonical_path=canonical_path,
        json_ld=build_json_ld_webpage(title, description, canonical_url),
    )

    return render(
        request,
        "pages/faq.html",
        {"page_meta": build_page_meta(request, metadata)},
    )

def privacy(request):
    title = "Privacy Policy"
    description = "Understand how Traders collects, stores, and protects your data."
    canonical_path = "/privacy"
    canonical_url = request.build_absolute_uri(canonical_path)
    metadata = PageMeta(
        title=title,
        description=description,
        canonical_path=canonical_path,
        json_ld=build_json_ld_webpage(title, description, canonical_url),
    )

    return render(
        request,
        "pages/privacy.html",
        {"page_meta": build_page_meta(request, metadata)},
    )

def terms(request):
    title = "Terms of Use"
    description = "Review the terms and conditions for using Traders platform."
    canonical_path = "/terms"
    canonical_url = request.build_absolute_uri(canonical_path)
    metadata = PageMeta(
        title=title,
        description=description,
        canonical_path=canonical_path,
        json_ld=build_json_ld_webpage(title, description, canonical_url),
    )

    return render(
        request,
        "pages/terms.html",
        {"page_meta": build_page_meta(request, metadata)},
    )

def about(request):
    title = "About Traders"
    description = "Learn about how Traders works, why we built it, and who we are."
    canonical_path = "/about"
    canonical_url = request.build_absolute_uri(canonical_path)
    metadata = PageMeta(
        title=title,
        description=description,
        canonical_path=canonical_path,
        json_ld=build_json_ld_webpage(title, description, canonical_url),
    )

    return render(
        request,
        "pages/about.html",
        {"page_meta": build_page_meta(request, metadata)},
    )

@require_http_methods(["GET", "POST"])
def cr33(request):
    title = "Traders - Knife sharpening"
    description = "Book your service slot."
    canonical_path = "/cr33"
    canonical_url = request.build_absolute_uri(canonical_path)
    metadata = PageMeta(
        title=title,
        description=description,
        canonical_path=canonical_path,
        json_ld=build_json_ld_webpage(title, description, canonical_url),
    )

    default_values = {
        "intent": "bell",
        "slot": "",
        "area": "Scott Estate",
        "address": "",
        "contact": "",
    }
    form_values = {**default_values}
    form_errors: list[str] = []

    if request.method == "POST":
        form_values = {
            "intent": (request.POST.get("intent") or "").strip() or default_values["intent"],
            "slot": (request.POST.get("slot") or "").strip(),
            "area": (request.POST.get("area") or "").strip() or default_values["area"],
            "address": (request.POST.get("address") or "").strip(),
            "contact": (request.POST.get("contact") or "").strip(),
        }

        if form_values["intent"] == "slot" and not form_values["slot"]:
            form_errors.append("Please pick a 15-minute slot.")

        if not form_values["contact"]:
            form_errors.append("Add a phone number or email so we can confirm your booking.")

        if not form_values["address"]:
            form_errors.append("Please share your house number and street.")

        if not form_errors:
            intent_labels = {
                "bell": "Ring my bell during the window",
                "slot": "Come at a specific time",
                "future": "Interested in a future visit",
            }

            message_parts = [
                "CR33 knife sharpening booking interest.",
                f"Intent: {intent_labels.get(form_values['intent'], 'Not specified')}",
            ]

            if form_values["intent"] == "slot" and form_values["slot"]:
                message_parts.append(f"Preferred slot: {form_values['slot']}")
            elif form_values["intent"] == "bell":
                message_parts.append("Preferred slot: Anytime during the 09:00-11:30 window.")
            elif form_values["intent"] == "future":
                message_parts.append("Preferred slot: Interested in future visits.")

            message_parts.extend(
                [
                    f"Area: {form_values['area'] or default_values['area']}",
                    f"Address: {form_values['address'] or 'Not provided'}",
                    f"Contact: {form_values['contact'] or 'Not provided'}",
                ]
            )

            contact_value = form_values["contact"]
            email_value = contact_value if "@" in contact_value else ""
            phone_value = "" if email_value else contact_value

            feedback = Feedback(
                name=form_values.get("name", ""),
                email=email_value,
                phone=phone_value,
                feedback_type="Contact",
                feedback_category="General",
                message="\n".join(message_parts),
                target="CR33",
            )

            if request.user.is_authenticated:
                feedback.user = request.user

            feedback.save()
            messages.success(request, "Thanks! We'll confirm your knife sharpening slot.")
            return redirect("cr33")

    return render(
        request,
        "pages/cr33.html",
        {
            "page_meta": build_page_meta(request, metadata),
            "form_values": form_values,
            "form_errors": form_errors,
        },
    )

def theme_sample(request):
    return render(
        request,
        "pages/theme_sample.html",
    )

def under_construction(request):
    description = "This area of Traders is still being built. Check back soon for new content."
    canonical_path = request.path
    metadata = PageMeta(
        title="Under Construction",
        description=description,
        canonical_path=canonical_path,
        json_ld=build_json_ld_webpage(
            "Under Construction",
            description,
            request.build_absolute_uri(canonical_path),
        ),
    )

    return render(
        request,
        "pages/under_construction.html",
        {"page_meta": build_page_meta(request, metadata)},
    )
