"""Global context helpers for templates."""
from __future__ import annotations

from django.conf import settings

from .metadata import PageMeta, build_page_meta


def default_metadata(request):
    """Inject a baseline ``page_meta`` structure for every request."""

    return {
        "page_meta": build_page_meta(request, PageMeta()),
    }


def site_settings(_request):
    """Expose base URLs to templates."""
    return {
        "BASE_DOMAIN": getattr(settings, "BASE_DOMAIN", "example.com"),
        "BASE_URL": getattr(settings, "BASE_URL", ""),
    }
