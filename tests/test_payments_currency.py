import requests
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from payments.exchange import (
    ExchangeRateError,
    ExchangeRateInfo,
    get_or_update_exchange_rate,
)
from payments.models import CurrencyConversionRate, Payment


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.django_db
def test_exchange_rate_uses_fallback_when_missing(monkeypatch):
    def _raise():
        raise ExchangeRateError("boom")

    monkeypatch.setattr("payments.exchange._fetch_remote_rate", _raise)

    info = get_or_update_exchange_rate()
    stored = CurrencyConversionRate.objects.get()
    assert stored.rate == info.rate
    assert stored.source_currency == "ZAR"
    assert stored.target_currency == "USD"


@pytest.mark.django_db
def test_exchange_rate_fetches_on_first_creation(monkeypatch):
    expected = ExchangeRateInfo(
        rate=Decimal("0.1234"),
        fetched_at=timezone.now(),
    )

    monkeypatch.setattr("payments.exchange._fetch_remote_rate", lambda: expected)

    info = get_or_update_exchange_rate()
    stored = CurrencyConversionRate.objects.get()

    assert info.rate == expected.rate
    assert stored.rate == expected.rate
    assert stored.fetched_at == expected.fetched_at


@pytest.mark.django_db
def test_exchange_rate_refreshes_after_day(monkeypatch):
    rate = CurrencyConversionRate.objects.create(
        source_currency="ZAR",
        target_currency="USD",
        rate=Decimal("0.05"),
        fetched_at=timezone.now() - timedelta(days=2),
    )
    CurrencyConversionRate.objects.filter(pk=rate.pk).update(
        updated_at=timezone.now() - timedelta(days=2)
    )

    payload = {
        "rates": {"USD": "0.060"},
        "date": "2024-05-10T12:30:00",
    }

    monkeypatch.setattr("payments.exchange.requests.get", lambda *args, **kwargs: DummyResponse(payload))

    info = get_or_update_exchange_rate()
    stored = CurrencyConversionRate.objects.get()
    assert info.rate == Decimal("0.060")
    assert stored.rate == Decimal("0.060")
    assert stored.fetched_at.date().isoformat() == "2024-05-10"


@pytest.mark.django_db
def test_exchange_rate_handles_api_failure(monkeypatch):
    rate = CurrencyConversionRate.objects.create(
        source_currency="ZAR",
        target_currency="USD",
        rate=Decimal("0.05"),
        fetched_at=timezone.now() - timedelta(days=2),
    )
    CurrencyConversionRate.objects.filter(pk=rate.pk).update(
        updated_at=timezone.now() - timedelta(days=2)
    )

    def _raise(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr("payments.exchange.requests.get", _raise)

    info = get_or_update_exchange_rate()
    stored = CurrencyConversionRate.objects.get()
    assert info.rate == Decimal("0.05")
    assert stored.rate == Decimal("0.05")


@pytest.mark.django_db
def test_contribute_view_includes_usd_conversion(client):
    CurrencyConversionRate.objects.create(
        source_currency="ZAR",
        target_currency="USD",
        rate=Decimal("0.10"),
        fetched_at=timezone.now(),
    )

    response = client.get(reverse("payments:contribute"))
    tiers = {tier["key"]: tier for tier in response.context["tiers"]}

    assert tiers["tier-1"]["usd_amount"] == Decimal("5.00")
    assert "usd_amount" not in tiers["tier-2"]


@pytest.mark.django_db
def test_checkout_custom_amount_accepts_usd(monkeypatch, client):
    CurrencyConversionRate.objects.create(
        source_currency="ZAR",
        target_currency="USD",
        rate=Decimal("0.05"),
        fetched_at=timezone.now(),
    )

    def _mock_initialize(self, **kwargs):
        return {"status": True, "data": {"authorization_url": "https://paystack.example/authorize"}}

    monkeypatch.setattr("payments.views.Paystack.initialize", _mock_initialize)

    response = client.post(
        reverse("payments:contribute_checkout"),
        data={
            "tier": "tier-2",
            "amount": "",
            "amount_usd": "5",
            "frequency": "once",
            "email": "user@example.com",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == "https://paystack.example/authorize"

    payment = Payment.objects.get()
    assert payment.amount == 10000  # R100.00 in cents
    assert payment.tier == "tier-2"
