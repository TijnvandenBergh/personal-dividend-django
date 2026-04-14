"""Pure-ish business logic: allocation math, price provider, FX."""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, asdict
from datetime import timedelta
from typing import Iterable

from django.conf import settings
from django.utils import timezone

from .models import Etf, FxRate, Price

logger = logging.getLogger(__name__)

PRICE_CACHE_SECONDS = 5 * 60
FX_CACHE_SECONDS = 60 * 60  # 1 hour


@dataclass
class PricedEtf:
    id: int
    ticker: str
    name: str
    weight_pct: float
    price_cents: int


@dataclass
class AllocationItem:
    id: int
    ticker: str
    name: str
    weight_pct: float
    price_cents: int
    target_cents: int
    shares: int
    spent_cents: int
    diff_cents: int


@dataclass
class AllocationTotals:
    budget_cents: int
    spent_cents: int
    rest_cents: int


@dataclass
class AllocationResult:
    items: list[AllocationItem]
    totals: AllocationTotals

    def as_dict(self) -> dict:
        return {
            "items": [asdict(i) for i in self.items],
            "totals": asdict(self.totals),
        }


def calc_allocation(budget_cents: int, priced: Iterable[PricedEtf]) -> AllocationResult:
    items: list[AllocationItem] = []
    for item in priced:
        target = round(budget_cents * (item.weight_pct / 100))
        shares = max(0, target // item.price_cents) if item.price_cents > 0 else 0
        spent = shares * item.price_cents
        items.append(AllocationItem(
            id=item.id, ticker=item.ticker, name=item.name,
            weight_pct=item.weight_pct, price_cents=item.price_cents,
            target_cents=target, shares=shares, spent_cents=spent,
            diff_cents=target - spent,
        ))
    spent_total = sum(i.spent_cents for i in items)
    return AllocationResult(
        items=items,
        totals=AllocationTotals(
            budget_cents=budget_cents,
            spent_cents=spent_total,
            rest_cents=budget_cents - spent_total,
        ),
    )


def _mock_fetch_price_cents(ticker: str) -> int:
    """Fallback: random price in cents. Deterministic tests can monkeypatch this."""
    return int(5000 + random.random() * 5000)


def _fetch_price_cents_yfinance(ticker: str) -> int | None:
    """Fetch the latest market price via Yahoo Finance, return cents or None."""
    yahoo_symbol = getattr(settings, "YAHOO_TICKER_MAP", {}).get(ticker, ticker)
    try:
        import yfinance as yf  # noqa: E402

        info = yf.Ticker(yahoo_symbol).fast_info
        price = getattr(info, "last_price", None)
        if price is None or price <= 0:
            return None
        return int(round(price * 100))
    except Exception:
        logger.warning("yfinance fetch failed for %s (%s)", ticker, yahoo_symbol, exc_info=True)
        return None


def get_live_price_cents(ticker: str) -> int:
    cutoff = timezone.now() - timedelta(seconds=PRICE_CACHE_SECONDS)
    latest = Price.objects.filter(ticker=ticker, asof__gte=cutoff).order_by("-asof").first()
    if latest is not None:
        return latest.price_cents
    price = _fetch_price_cents_yfinance(ticker)
    if price is None:
        price = _mock_fetch_price_cents(ticker)
    Price.objects.create(ticker=ticker, price_cents=price)
    return price


def price_etfs() -> list[PricedEtf]:
    return [
        PricedEtf(
            id=e.id, ticker=e.ticker, name=e.name,
            weight_pct=e.weight_pct,
            price_cents=get_live_price_cents(e.ticker),
        )
        for e in Etf.objects.all()
    ]


def _fetch_ecb_rates() -> dict[str, float] | None:
    """Fetch latest FX rates from the ECB API. Returns {currency: rate} or None."""
    import urllib.request
    import json

    url = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD+GBP.EUR.SP00.A?lastNObservations=1&format=jsondata"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        rates: dict[str, float] = {"EUR": 1.0}
        series = data["dataSets"][0]["series"]
        keys = data["structure"]["dimensions"]["series"]
        currency_dim = next(d for d in keys if d["id"] == "CURRENCY")
        for key, series_data in series.items():
            idx = int(key.split(":")[1])
            currency_code = currency_dim["values"][idx]["id"]
            obs = series_data["observations"]
            latest = obs[max(obs.keys())]
            rates[currency_code] = latest[0]
        return rates
    except Exception:
        logger.warning("ECB FX rate fetch failed", exc_info=True)
        return None


def get_fx_rate(currency: str) -> float:
    """Return the exchange rate for 1 EUR = X <currency>, cached for 1 hour."""
    if currency == "EUR":
        return 1.0

    cutoff = timezone.now() - timedelta(seconds=FX_CACHE_SECONDS)
    cached = FxRate.objects.filter(currency=currency, asof__gte=cutoff).order_by("-asof").first()
    if cached is not None:
        return cached.rate

    ecb_rates = _fetch_ecb_rates()
    if ecb_rates:
        for code, rate in ecb_rates.items():
            if code != "EUR":
                FxRate.objects.create(currency=code, rate=rate)
        if currency in ecb_rates:
            return ecb_rates[currency]

    return settings.FX_RATES_FROM_EUR.get(currency, 1.0)


def convert_from_eur(amount_cents_eur: int, currency: str) -> int:
    rate = get_fx_rate(currency)
    return int(round(amount_cents_eur * rate))


def convert_to_eur(amount_cents_foreign: int, currency: str) -> int:
    """Convert an amount in *currency* cents to EUR cents."""
    rate = get_fx_rate(currency)
    if rate == 0:
        return amount_cents_foreign
    return int(round(amount_cents_foreign / rate))


def convert_allocation(result: AllocationResult, currency: str) -> AllocationResult:
    """Return the allocation with all *_cents amounts converted to `currency`.

    Share counts stay the same; only monetary fields are scaled by the FX rate.
    """
    rate = get_fx_rate(currency)

    def c(n: int) -> int:
        return int(round(n * rate))

    items = [
        AllocationItem(
            id=i.id, ticker=i.ticker, name=i.name, weight_pct=i.weight_pct,
            price_cents=c(i.price_cents),
            target_cents=c(i.target_cents),
            shares=i.shares,
            spent_cents=c(i.spent_cents),
            diff_cents=c(i.diff_cents),
        )
        for i in result.items
    ]
    totals = AllocationTotals(
        budget_cents=c(result.totals.budget_cents),
        spent_cents=c(result.totals.spent_cents),
        rest_cents=c(result.totals.rest_cents),
    )
    return AllocationResult(items=items, totals=totals)
