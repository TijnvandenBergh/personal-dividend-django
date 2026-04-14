from __future__ import annotations

from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Contribution, Etf
from .services import calc_allocation, convert_allocation, price_etfs, PricedEtf


def _months():
    return [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December"),
    ]


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

    contribution = Contribution.objects.filter(
        user=request.user, year=year, month=month,
    ).first()
    amount_cents = contribution.amount_cents if contribution else 0
    carry_in_cents = contribution.carry_in_cents if contribution else 0
    budget_cents = amount_cents + carry_in_cents

    priced = price_etfs()
    monthly = calc_allocation(budget_cents, priced)

    total_budget_cents = Contribution.objects.filter(user=request.user).aggregate(
        total=Sum(F("amount_cents") + F("carry_in_cents"))
    )["total"] or 0
    cumulative = calc_allocation(total_budget_cents, priced)

    currency = request.session.get("currency", settings.DEFAULT_CURRENCY)
    monthly_c = convert_allocation(monthly, currency)
    cumulative_c = convert_allocation(cumulative, currency)

    return render(request, "dividends/dashboard.html", {
        "year": year,
        "month": month,
        "amount": (amount_cents / 100),
        "carry_in": (carry_in_cents / 100),
        "months": _months(),
        "monthly": monthly_c,
        "cumulative": cumulative_c,
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

    Contribution.objects.update_or_create(
        user=request.user, year=year, month=month,
        defaults={
            "amount_cents": round(amount * 100),
            "carry_in_cents": round(carry_in * 100),
        },
    )
    return redirect(f"/?year={year}&month={month}")
