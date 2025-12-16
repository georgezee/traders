"""Utilities for building structured metadata for templates."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Dict
from urllib.parse import urljoin

from django.conf import settings
from django.http import HttpRequest
from django.utils.html import strip_tags
from django.utils.text import Truncator


@dataclass
class PageMeta:
    """Container for per-page metadata and social previews."""

    title: str | None = None
    description: str | None = None
    canonical_path: str | None = None
    canonical_url: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    og_type: str | None = None
    robots: str | None = None
    json_ld: Any = None
    extra: Dict[str, str] = field(default_factory=dict)

    def merged(self, **overrides: Any) -> "PageMeta":
        """Return a copy with keyword overrides applied."""

        return replace(self, **overrides)


def _normalise_description(value: str | None) -> str | None:
    if not value:
        return None
    clean = strip_tags(value).strip()
    if not clean:
        return None
    truncated = Truncator(clean).chars(320, truncate="...")
    return " ".join(truncated.split())


def _build_absolute_url(request: HttpRequest, target: str | None) -> str:
    if not target:
        return request.build_absolute_uri()
    if target.startswith("http://") or target.startswith("https://"):
        return target
    base = request.build_absolute_uri("/")
    return urljoin(base, target.lstrip("/"))


def _serialise_json_ld(payload: Any) -> str | None:
    if payload in (None, ""):
        return None
    if isinstance(payload, (list, tuple)):
        payload = list(payload)
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _get_site_meta_setting() -> Dict[str, Any]:
    site_meta = getattr(settings, "SITE_META", {})
    if not isinstance(site_meta, dict):
        return {}
    return site_meta


def build_page_meta(request: HttpRequest, meta: PageMeta | None = None) -> Dict[str, Any]:
    """Resolve a ``PageMeta`` against site defaults for template rendering."""

    site_defaults = _get_site_meta_setting()
    meta = meta or PageMeta()

    site_name = site_defaults.get("site_name", "Traders")
    base_description = site_defaults.get("default_description")
    default_og_image = site_defaults.get("default_og_image")
    default_robots = site_defaults.get("default_robots", "index,follow")
    append_site_name = site_defaults.get("append_site_name", True)
    default_og_type = site_defaults.get("default_og_type", "website")
    default_extra = site_defaults.get("extra_meta", {})

    title = (meta.title or site_defaults.get("default_title") or site_name).strip()
    description = _normalise_description(meta.description or base_description)

    canonical_url = meta.canonical_url or _build_absolute_url(
        request,
        meta.canonical_path or site_defaults.get("default_canonical_path") or request.path,
    )

    og_title = (meta.og_title or meta.title or title).strip()
    og_description_raw = meta.og_description or description or base_description
    og_description = _normalise_description(og_description_raw)
    og_image = meta.og_image or default_og_image
    og_type = meta.og_type or default_og_type
    robots = meta.robots or default_robots

    extra = {**default_extra, **meta.extra}
    json_ld = _serialise_json_ld(meta.json_ld)

    if append_site_name and title != site_name:
        full_title = f"{title} - {site_name}"
    else:
        full_title = title

    return {
        "title": title,
        "full_title": full_title,
        "site_name": site_name,
        "description": description,
        "canonical_url": canonical_url,
        "og": {
            "title": og_title,
            "description": og_description,
            "image": og_image,
            "type": og_type,
            "site_name": site_name,
            "url": canonical_url,
        },
        "robots": robots,
        "json_ld": json_ld,
        "extra": extra,
    }


def build_json_ld_webpage(title: str, description: str | None, canonical_url: str) -> Dict[str, Any]:
    """Helper for building a basic WebPage schema block."""

    payload: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": canonical_url,
    }
    if description:
        payload["description"] = description
    return payload
