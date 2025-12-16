"""Utilities for verifying Cloudflare Turnstile responses."""

from __future__ import annotations

import logging
from typing import Iterable

import requests
from django.conf import settings


logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_turnstile(response_token: str | None, remote_ip: str | None = None, timeout: float = 5.0) -> tuple[bool, Iterable[str]]:
    """Validate a Turnstile response token against Cloudflare.

    Returns a tuple of ``(success, error_codes)``. ``error_codes`` is empty when
    validation succeeds. Any networking or parsing issue is treated as a failure.
    """

    if not response_token:
        logger.debug("Turnstile check: missing response token.")
        return False, ["missing-input-response"]

    secret = getattr(settings, "TURNSTILE_SECRET_KEY", "")
    if not secret:
        logger.warning("Turnstile secret key is not configured; rejecting request.")
        return False, ["missing-secret"]

    data: dict[str, str] = {
        "secret": secret,
        "response": response_token,
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        logger.debug(
            "Turnstile check: sending verification request (remote_ip=%s, token_prefix=%s)",
            remote_ip,
            response_token[:8],
        )
        result = requests.post(TURNSTILE_VERIFY_URL, data=data, timeout=timeout)
        logger.debug(
            "Turnstile check: received status %s", result.status_code
        )
        result.raise_for_status()
        payload = result.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Turnstile verification request failed: %s", exc)
        return False, ["request-error"]

    success = payload.get("success", False)
    error_codes = payload.get("error-codes", []) or []

    logger.debug(
        "Turnstile check: success=%s, action=%s, cdata=%s, error_codes=%s",
        success,
        payload.get("action"),
        payload.get("cdata"),
        error_codes,
    )

    if not success:
        logger.info("Turnstile verification failed: %s", error_codes)

    return bool(success), error_codes
