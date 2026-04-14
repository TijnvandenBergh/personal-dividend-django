"""Pure-ish business logic: allocation math, price provider, FX."""
from __future__ import annotations

import random
from dataclasses import dataclass, asdict
from datetime import timedelta
from typing import Iterable

from django.conf import settings
from django.utils import timezone

from .models import Etf, Price

PRICE_CACHE_SECONDS = 5 * 60


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
    # €50–€100 in cents. Deterministic tests can monkeypatch this.
    return int(5000 + random.random() * 5000)


def get_live_price_cents(ticker: str) -> int:
    cutoff = timezone.now() - timedelta(seconds=PRICE_CACHE_SECONDS)
    latest = Price.objects.filter(ticker=ticker, asof__gte=cutoff).order_by("-asof").first()
    if latest is not None:
        return latest.price_cents
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


def convert_from_eur(amount_cents_eur: int, currency: str) -> int:
    rate = settings.FX_RATES_FROM_EUR.get(currency, 1.0)
    return int(round(amount_cents_eur * rate))


def convert_allocation(result: AllocationResult, currency: str) -> AllocationResult:
    """Return the allocation with all *_cents amounts converted to `currency`.

    Share counts stay the same; only monetary fields are scaled by the FX rate.
    """
    rate = settings.FX_RATES_FROM_EUR.get(currency, 1.0)

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
