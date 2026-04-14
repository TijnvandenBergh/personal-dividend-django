from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Etf(models.Model):
    ticker = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=200)
    weight_pct = models.FloatField()

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.ticker} ({self.weight_pct}%)"


class Contribution(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contributions")
    year = models.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    month = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    amount_cents = models.IntegerField(validators=[MinValueValidator(0)])
    carry_in_cents = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["year", "month"]
        constraints = [
            models.UniqueConstraint(fields=["user", "year", "month"], name="uniq_user_year_month"),
        ]


class FxRate(models.Model):
    currency = models.CharField(max_length=3)
    rate = models.FloatField(help_text="1 EUR = <rate> <currency>")
    asof = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-asof"]
        indexes = [models.Index(fields=["currency", "-asof"])]

    def __str__(self) -> str:
        return f"EUR/{self.currency} = {self.rate}"


class Price(models.Model):
    ticker = models.CharField(max_length=16)
    price_cents = models.IntegerField(validators=[MinValueValidator(0)])
    asof = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-asof"]
        indexes = [models.Index(fields=["ticker", "-asof"])]
