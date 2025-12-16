from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.utils import timezone

from .models import CurrencyConversionRate

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_CURRENCY = "ZAR"
DEFAULT_TARGET_CURRENCY = "USD"
DEFAULT_RATE_FALLBACK = Decimal("0.05")
DEFAULT_API_URL = "https://api.frankfurter.app/latest"
DEFAULT_API_TIMEOUT = 10
STALE_INTERVAL = timedelta(days=1)
RETRY_INTERVAL = timedelta(minutes=10)


@dataclass
class ExchangeRateInfo:
    rate: Decimal
    fetched_at: datetime
    source_currency: str = DEFAULT_SOURCE_CURRENCY
    target_currency: str = DEFAULT_TARGET_CURRENCY


class ExchangeRateError(Exception):
    """Raised when an exchange rate update fails."""


def _get_api_url() -> str:
    return getattr(settings, "EXCHANGE_RATE_API_URL", DEFAULT_API_URL)


def _build_request(url: str):
    formatted = url.format(source=DEFAULT_SOURCE_CURRENCY, target=DEFAULT_TARGET_CURRENCY)
    lower_url = formatted.lower()
    params = {}
    if "from=" not in lower_url:
        params["from"] = DEFAULT_SOURCE_CURRENCY
    if "to=" not in lower_url:
        params["to"] = DEFAULT_TARGET_CURRENCY
    return formatted, params


def _get_fallback_rate() -> Decimal:
    raw = getattr(settings, "EXCHANGE_RATE_FALLBACK", None)
    if raw is None:
        return DEFAULT_RATE_FALLBACK
    if isinstance(raw, Decimal):
        return raw
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError):
        logger.warning("Invalid EXCHANGE_RATE_FALLBACK setting %r, using default.", raw)
        return DEFAULT_RATE_FALLBACK


def _extract_rate(payload: dict) -> Decimal:
    if not isinstance(payload, dict):
        raise ExchangeRateError("Unexpected API response type")

    rates = payload.get("rates")
    if not isinstance(rates, dict):
        raise ExchangeRateError("Exchange rate not found in API response")

    rate = rates.get(DEFAULT_TARGET_CURRENCY)
    if rate is None:
        raise ExchangeRateError("Exchange rate not found in API response")

    try:
        return Decimal(str(rate))
    except InvalidOperation as exc:
        raise ExchangeRateError("Invalid rate returned by API") from exc


def _fetch_remote_rate() -> ExchangeRateInfo:
    api_url, params = _build_request(_get_api_url())
    try:
        response = requests.get(api_url, params=params, timeout=DEFAULT_API_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network error path
        raise ExchangeRateError(str(exc)) from exc

    try:
        payload = response.json()
    except ValueError as exc:  # pragma: no cover - unexpected response
        raise ExchangeRateError("Invalid JSON response from exchange rate API") from exc

    rate = _extract_rate(payload)

    fetched_at = payload.get("date") or payload.get("time_last_update_utc")
    if fetched_at:
        try:
            timestamp = datetime.fromisoformat(str(fetched_at).replace("Z", "+00:00"))
            if timezone.is_naive(timestamp):
                timestamp = timezone.make_aware(timestamp)
        except (ValueError, TypeError):
            timestamp = timezone.now()
    else:
        timestamp = timezone.now()

    return ExchangeRateInfo(rate=rate, fetched_at=timestamp)


def get_or_update_exchange_rate(force_refresh: bool = False) -> ExchangeRateInfo:
    now = timezone.now()
    rate_obj, created = CurrencyConversionRate.objects.get_or_create(
        source_currency=DEFAULT_SOURCE_CURRENCY,
        target_currency=DEFAULT_TARGET_CURRENCY,
        defaults={
            "rate": _get_fallback_rate(),
            "fetched_at": now,
        },
    )

    if created:
        logger.info(
            "Initialized exchange rate cache with fallback rate %s fetched at %s",
            rate_obj.rate,
            rate_obj.fetched_at,
        )

    entry = ExchangeRateInfo(rate=Decimal(rate_obj.rate), fetched_at=rate_obj.fetched_at)

    age = now - rate_obj.fetched_at
    needs_refresh = force_refresh or created

    if not needs_refresh and age >= STALE_INTERVAL:
        needs_refresh = True

    if not needs_refresh:
        return entry

    if not (force_refresh or created):
        retry_age = now - rate_obj.updated_at
        if retry_age < RETRY_INTERVAL:
            logger.info(
                "Skipping exchange rate refresh; last attempt was %s ago (retry window %s)",
                retry_age,
                RETRY_INTERVAL,
            )
            return entry

    if force_refresh:
        logger.info("Refreshing exchange rate via forced update")
    elif created:
        logger.info("Refreshing exchange rate for newly initialized cache")
    else:
        logger.info(
            "Refreshing exchange rate; data age %s (stale after %s)",
            age,
            STALE_INTERVAL,
        )

    try:
        latest = _fetch_remote_rate()
    except ExchangeRateError as exc:
        logger.warning("Failed to update exchange rate: %s", exc)
        rate_obj.save(update_fields=["updated_at"])
        return ExchangeRateInfo(rate=Decimal(rate_obj.rate), fetched_at=rate_obj.fetched_at)

    rate_obj.rate = latest.rate
    rate_obj.fetched_at = latest.fetched_at
    rate_obj.save(update_fields=["rate", "fetched_at", "updated_at"])
    logger.info(
        "Exchange rate updated to %s fetched at %s",
        latest.rate,
        latest.fetched_at,
    )
    return latest
