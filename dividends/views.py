from __future__ import annotations

from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Contribution, Etf
from .services import calc_allocation, convert_allocation, convert_to_eur, get_fx_rate, price_etfs


def _months():
    return [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December"),
    ]


def _get_contribution_cents(user, year, month):
    """Return (amount_cents, carry_in_cents) for a user's month, defaulting to 0."""
    contribution = Contribution.objects.filter(user=user, year=year, month=month).first()
    if contribution:
        return contribution.amount_cents, contribution.carry_in_cents
    return 0, 0


@login_required
def dashboard(request):
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except ValueError:
        return HttpResponseBadRequest("Invalid year/month")
    if not (2000 <= year <= 2100 and 1 <= month <= 12):
        return HttpResponseBadRequest("Invalid year/month")

    amount_cents, carry_in_cents = _get_contribution_cents(request.user, year, month)

    priced = price_etfs()
    monthly = calc_allocation(amount_cents + carry_in_cents, priced)

    total_budget_cents = Contribution.objects.filter(user=request.user).aggregate(
        total=Sum(F("amount_cents") + F("carry_in_cents"))
    )["total"] or 0
    cumulative = calc_allocation(total_budget_cents, priced)

    currency = request.session.get("currency", settings.DEFAULT_CURRENCY)
    rate = get_fx_rate(currency)

    return render(request, "dividends/dashboard.html", {
        "year": year,
        "month": month,
        "amount": round(amount_cents * rate / 100, 2),
        "carry_in": round(carry_in_cents * rate / 100, 2),
        "months": _months(),
        "monthly": convert_allocation(monthly, currency),
        "cumulative": convert_allocation(cumulative, currency),
        "etfs_count": Etf.objects.count(),
    })


@login_required
@require_POST
def save_contribution(request):
    try:
        year = int(request.POST.get("year"))
        month = int(request.POST.get("month"))
        amount = float(request.POST.get("amount") or 0)
        carry_in = float(request.POST.get("carry_in") or 0)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid input")

    if not (2000 <= year <= 2100 and 1 <= month <= 12 and amount >= 0 and carry_in >= 0):
        return HttpResponseBadRequest("Invalid input")

    currency = request.session.get("currency", settings.DEFAULT_CURRENCY)
    amount_cents_foreign = round(amount * 100)
    carry_in_cents_foreign = round(carry_in * 100)
    Contribution.objects.update_or_create(
        user=request.user, year=year, month=month,
        defaults={
            "amount_cents": convert_to_eur(amount_cents_foreign, currency),
            "carry_in_cents": convert_to_eur(carry_in_cents_foreign, currency),
        },
    )
    return redirect(f"/?year={year}&month={month}")
