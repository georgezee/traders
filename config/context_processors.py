"""Global context helpers for templates."""
from __future__ import annotations

from .metadata import PageMeta, build_page_meta


def default_metadata(request):
    """Inject a baseline ``page_meta`` structure for every request."""

    return {
        "page_meta": build_page_meta(request, PageMeta()),
    }
