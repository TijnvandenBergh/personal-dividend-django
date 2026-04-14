from __future__ import annotations

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Contribution, Etf, Price
from .services import (
    AllocationResult, PricedEtf, calc_allocation, convert_allocation,
    get_live_price_cents, price_etfs,
)

User = get_user_model()


class AllocationMathTests(TestCase):
    def test_basic_allocation(self):
        items = [
            PricedEtf(id=1, ticker="A", name="A", weight_pct=50, price_cents=1000),
            PricedEtf(id=2, ticker="B", name="B", weight_pct=50, price_cents=2500),
        ]
        r = calc_allocation(10_000, items)
        self.assertEqual(r.items[0].shares, 5)
        self.assertEqual(r.items[0].spent_cents, 5000)
        self.assertEqual(r.items[1].shares, 2)
        self.assertEqual(r.items[1].spent_cents, 5000)
        self.assertEqual(r.totals.budget_cents, 10_000)
        self.assertEqual(r.totals.spent_cents, 10_000)
        self.assertEqual(r.totals.rest_cents, 0)

    def test_zero_price_yields_zero_shares(self):
        items = [PricedEtf(id=1, ticker="A", name="A", weight_pct=100, price_cents=0)]
        r = calc_allocation(10_000, items)
        self.assertEqual(r.items[0].shares, 0)
        self.assertEqual(r.items[0].spent_cents, 0)
        self.assertEqual(r.totals.rest_cents, 10_000)

    def test_convert_allocation_scales_money_only(self):
        items = [PricedEtf(id=1, ticker="A", name="A", weight_pct=100, price_cents=1000)]
        r = calc_allocation(10_000, items)
        c = convert_allocation(r, "USD")  # 1.08
        self.assertEqual(c.items[0].shares, r.items[0].shares)
        self.assertEqual(c.totals.budget_cents, round(10_000 * 1.08))

    def test_as_dict_serializes(self):
        r = AllocationResult(items=[], totals=None.__class__)  # type: ignore
        # Just ensure calc_allocation produces serializable dict:
        r2 = calc_allocation(0, [])
        self.assertIn("items", r2.as_dict())
        self.assertIn("totals", r2.as_dict())


class PriceServiceTests(TestCase):
    def test_price_is_cached(self):
        with mock.patch(
            "dividends.services._mock_fetch_price_cents", return_value=7777
        ) as m:
            self.assertEqual(get_live_price_cents("XYZ"), 7777)
            self.assertEqual(get_live_price_cents("XYZ"), 7777)
            self.assertEqual(m.call_count, 1)
        self.assertEqual(Price.objects.filter(ticker="XYZ").count(), 1)

    def test_price_etfs_uses_existing_etfs(self):
        Etf.objects.create(ticker="ZZZ", name="Z", weight_pct=100)
        with mock.patch("dividends.services._mock_fetch_price_cents", return_value=5000):
            priced = price_etfs()
        self.assertTrue(any(p.ticker == "ZZZ" for p in priced))


class AuthTests(TestCase):
    def test_register_creates_account_and_logs_in(self):
        r = self.client.post(reverse("accounts:register"), {
            "email": "a@b.co", "password": "secret12",
        })
        self.assertRedirects(r, reverse("dividends:dashboard"))
        self.assertTrue(User.objects.filter(username="a@b.co").exists())

    def test_register_rejects_short_password(self):
        r = self.client.post(reverse("accounts:register"), {
            "email": "a@b.co", "password": "short",
        })
        self.assertContains(r, "at least 8")

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(username="a@b.co", password="secret12")
        r = self.client.post(reverse("accounts:register"), {
            "email": "a@b.co", "password": "secret12",
        })
        self.assertContains(r, "already registered")

    def test_register_rejects_bad_email(self):
        r = self.client.post(reverse("accounts:register"), {
            "email": "nope", "password": "secret12",
        })
        self.assertContains(r, "Invalid email")

    def test_login_and_logout(self):
        User.objects.create_user(username="a@b.co", password="secret12")
        r = self.client.post(reverse("accounts:login"), {
            "email": "a@b.co", "password": "secret12",
        })
        self.assertRedirects(r, reverse("dividends:dashboard"))
        r = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(r, reverse("accounts:login"))

    def test_login_rejects_bad_credentials(self):
        User.objects.create_user(username="a@b.co", password="secret12")
        r = self.client.post(reverse("accounts:login"), {
            "email": "a@b.co", "password": "wrongpass",
        })
        self.assertContains(r, "Invalid credentials")


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="a@b.co", password="secret12")
        self.client.force_login(self.user)

    def test_dashboard_requires_auth(self):
        self.client.logout()
        r = self.client.get(reverse("dividends:dashboard"))
        self.assertEqual(r.status_code, 302)

    def test_dashboard_renders(self):
        with mock.patch("dividends.services._mock_fetch_price_cents", return_value=5000):
            r = self.client.get(reverse("dividends:dashboard"))
        self.assertEqual(r.status_code, 200)
        # Seeded ETF names are present:
        self.assertContains(r, "Vanguard FTSE All-World High Dividend Yield")

    def test_save_contribution_persists_and_redirects(self):
        with mock.patch("dividends.services._mock_fetch_price_cents", return_value=5000):
            r = self.client.post(reverse("dividends:save_contribution"), {
                "year": 2026, "month": 4, "amount": "500", "carry_in": "25",
            })
        self.assertEqual(r.status_code, 302)
        c = Contribution.objects.get(user=self.user, year=2026, month=4)
        self.assertEqual(c.amount_cents, 50_000)
        self.assertEqual(c.carry_in_cents, 2_500)

    def test_save_contribution_updates_on_conflict(self):
        Contribution.objects.create(user=self.user, year=2026, month=4, amount_cents=100, carry_in_cents=0)
        self.client.post(reverse("dividends:save_contribution"), {
            "year": 2026, "month": 4, "amount": "1", "carry_in": "0",
        })
        self.assertEqual(
            Contribution.objects.get(user=self.user, year=2026, month=4).amount_cents,
            100,
        )

    def test_save_contribution_rejects_bad_input(self):
        r = self.client.post(reverse("dividends:save_contribution"), {
            "year": "abc", "month": 4, "amount": "1", "carry_in": "0",
        })
        self.assertEqual(r.status_code, 400)
        r = self.client.post(reverse("dividends:save_contribution"), {
            "year": 1999, "month": 4, "amount": "1", "carry_in": "0",
        })
        self.assertEqual(r.status_code, 400)

    def test_dashboard_rejects_bad_query(self):
        r = self.client.get(reverse("dividends:dashboard"), {"year": "abc"})
        self.assertEqual(r.status_code, 400)


class PreferencesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="a@b.co", password="secret12")
        self.client.force_login(self.user)

    def test_theme_toggle(self):
        r = self.client.post(reverse("accounts:set_theme"), {"theme": "light"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.session["theme"], "light")

    def test_theme_rejects_bogus_value(self):
        self.client.post(reverse("accounts:set_theme"), {"theme": "rainbow"})
        self.assertIn(self.client.session["theme"], {"dark", "light"})

    def test_currency_switch(self):
        r = self.client.post(reverse("accounts:set_currency"), {"currency": "USD"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.session["currency"], "USD")
        with mock.patch("dividends.services._mock_fetch_price_cents", return_value=5000):
            r = self.client.get(reverse("dividends:dashboard"))
        self.assertContains(r, "$")

    def test_currency_rejects_bogus_value(self):
        self.client.post(reverse("accounts:set_currency"), {"currency": "JPY"})
        self.assertEqual(self.client.session["currency"], "EUR")


class TemplateFilterTests(TestCase):
    def test_cents_as_money(self):
        from .templatetags.dividend_extras import cents_as_money
        self.assertEqual(cents_as_money(12345), "123.45")
        self.assertEqual(cents_as_money(-100), "-1.00")
        self.assertEqual(cents_as_money("not-a-number"), "")


class HealthTests(TestCase):
    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})
