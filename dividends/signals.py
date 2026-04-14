"""Seed default ETF basket after migrations."""
from __future__ import annotations

from django.db.models.signals import post_migrate
from django.dispatch import receiver

SEED = [
    ("TDIV", "VanEck Morningstar Developed Markets Dividend Leaders", 30),
    ("VHYL", "Vanguard FTSE All-World High Dividend Yield", 25),
    ("ISPA", "iShares STOXX Global Select Dividend 100", 20),
    ("FGQI", "Fidelity Global Quality Income", 15),
    ("SPYD", "SPDR S&P Dividend Aristocrats", 10),
]


@receiver(post_migrate)
def seed_etfs(sender, **kwargs):
    if getattr(sender, "name", "") != "dividends":
        return
    from .models import Etf

    for ticker, name, weight in SEED:
        Etf.objects.get_or_create(ticker=ticker, defaults={"name": name, "weight_pct": weight})
