from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

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

def cr33(request):
    title = "CR33"
    description = "Placeholder page for the CR33 route."
    canonical_path = "/cr33"
    canonical_url = request.build_absolute_uri(canonical_path)
    metadata = PageMeta(
        title=title,
        description=description,
        canonical_path=canonical_path,
        json_ld=build_json_ld_webpage(title, description, canonical_url),
    )

    return render(
        request,
        "pages/cr33.html",
        {"page_meta": build_page_meta(request, metadata)},
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
