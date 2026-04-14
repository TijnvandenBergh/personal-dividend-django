# personal-dividend-app (Django port)

[![CI](https://github.com/OWNER/personal-dividend-app/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/personal-dividend-app/actions/workflows/ci.yml)
[![Vulnerability scan](https://img.shields.io/badge/scan-Trivy-1904da?logo=aquasec&logoColor=white)](https://github.com/OWNER/personal-dividend-app/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Django](https://img.shields.io/badge/Django-4.2%20LTS-092E20?logo=django&logoColor=white)](https://www.djangoproject.com)
[![Docker](https://img.shields.io/badge/container-Docker-2496ED?logo=docker&logoColor=white)](./Dockerfile)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#license)

A small personal finance dashboard for planning monthly contributions to a basket of dividend ETFs — ported from the original Angular + Node prototype to **Python + Django** (server-rendered templates, one process, one SQLite file). Enter how much you set aside this month plus any carry-over, and the app computes how many whole shares of each ETF to buy to stay close to your target weights.

## Status

Functional port of the original prototype. The core flow (register/login → enter a monthly contribution → see per-month and cumulative allocations) works end-to-end and is multi-user safe.

- **Backend:** Django 4.2 LTS (built-in auth, sessions, CSRF, admin) + SQLite via the ORM
- **Frontend:** Django templates + vanilla CSS (same light/dark tokens and layout as the Angular version)
- **Auth:** Django's session auth with bcrypt-equivalent PBKDF2 hashing; login rate-limit via `django-ratelimit`
- **Tests:** Django `TestCase` + `coverage.py`, enforced ≥80% line coverage
- **Theming:** light/dark, persisted in `localStorage` (pre-hydration) + server session, no flash on load
- **i18n:** Dutch + English via Django's built-in i18n, switchable in the UI
- **Multi-currency:** EUR / USD / GBP, switchable per session, monetary values converted at render time
- **Packaging:** single Dockerfile, docker-compose for local runs, GitHub Actions CI with Trivy scans

Still a hobby project — the price provider is mocked (random €50–€100) and there is no registration email verification. See the roadmap.

## Project structure

```
personal-dividend-django/
├── dividendapp/            # Django project (settings, urls, middleware, context procs)
├── accounts/               # login / logout / register / preferences (theme, currency)
├── dividends/              # ETFs, contributions, allocation math, prices, views
│   ├── services.py         # pure allocation math + mocked price provider + FX
│   ├── templatetags/       # cents_as_money filter
│   └── signals.py          # seeds the ETF basket on migrate
├── templates/              # base, partials, accounts/*, dividends/*
├── static/css|js/          # ported theme + tiny JS for localStorage sync
├── locale/{en,nl}/         # translations (.po → .mo)
├── Dockerfile              # python:3.12-slim → gunicorn
├── docker-compose.yml      # one-command local run (SQLite volume)
├── requirements.txt
├── .github/workflows/ci.yml
└── manage.py
```

## How to run (local, without Docker)

Prereqs: Python 3.12+, `gettext` for i18n compilation (`brew install gettext`).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py compilemessages
python manage.py createsuperuser  # or register from /accounts/register/
python manage.py runserver
```

Open <http://localhost:8000>.

## How to run (Docker, recommended)

```bash
docker-compose up --build
```

Then open <http://localhost:8000>. The SQLite file is persisted in the `app-data` volume.

## Environment variables

| Variable                | Default                                     | Purpose                                       |
| ----------------------- | ------------------------------------------- | --------------------------------------------- |
| `SECRET_KEY`            | `dev-secret-change-me`                      | Django secret (required in prod)              |
| `DJANGO_DEBUG`          | `1` (dev) / `0` (docker)                    | Toggles debug mode                            |
| `ALLOWED_HOSTS`         | `localhost 127.0.0.1 0.0.0.0 [::1] app web` | Space-separated hosts Django will respond to  |
| `CSRF_TRUSTED_ORIGINS`  | `http://localhost:8000 http://127.0.0.1:8000` | Space-separated trusted origins for CSRF    |
| `DB_FILE`               | `<repo>/app.db`                             | SQLite file path                              |
| `PORT`                  | `8000`                                      | gunicorn bind port                            |

## Run the tests

```bash
coverage run manage.py test
coverage report
```

CI fails the build below 80% line coverage.

## CI/CD

`.github/workflows/ci.yml` runs on every push and PR to `main`:

| Job                    | What it does                                                                  |
| ---------------------- | ----------------------------------------------------------------------------- |
| **Test**               | Installs deps, compiles translations, runs the Django test suite with coverage (≥80%) |
| **Vulnerability scan** | Builds the Docker image, runs Trivy filesystem + image scans, uploads SARIF   |

## Multi-currency

Three currencies are supported: **EUR (€)**, **USD ($)**, **GBP (£)**. The selector lives in the dashboard toolbar, is persisted in the user's session, and converts every monetary value at render time using a static FX table (`FX_RATES_FROM_EUR` in `settings.py`). Share counts are invariant — we only rescale the cents fields.

## Localization

Dutch and English are bundled. Switch languages via the selector in the toolbar (it uses Django's built-in `set_language` redirect view). To add new translations:

```bash
python manage.py makemessages -l nl
# edit locale/nl/LC_MESSAGES/django.po
python manage.py compilemessages
```

## UI parity notes

The UI is a 1:1 port of the Angular version: same CSS tokens (dark + light theme on `<html data-theme="...">`), same Inter font, same card / panel / table shapes, same form layout, same theme-toggle SVGs. One intentional deviation:

- The original used the Angular `CurrencyPipe` (which emits localized `€xx.xx` strings). The Django port uses a small `cents_as_money` filter that renders `12,345.67` and prefixes the currency symbol from the active session currency. Visually equivalent but not byte-identical.
- Form submissions are classic server-rendered POST → redirect instead of XHR, so there's a full page reload after saving a month. This keeps the stack dependency-free (no DRF, no frontend build step).

## Roadmap

Ideas for future iterations, roughly ordered by impact:

### Functional
- **Real market data** — replace `services._mock_fetch_price_cents` with a Yahoo Finance / Twelve Data / EODHD provider; persist intraday prices; allow user-configurable polling.
- **Live FX rates** — swap the static `FX_RATES_FROM_EUR` table for a cached ECB / exchangerate.host client.
- **Editable ETF basket per user** — today the basket is seeded globally; allow per-user tickers and target weights.
- **Transaction history screen** — list saved months, let users edit/delete them, with charts.
- **Dividend tracking** — record actual dividends received, project annual income, chart yield-on-cost.
- **Self-service password reset** — email-token reset flow.
- **CSV / JSON import-export** of contributions.
- **Notifications** — monthly reminders + dividend payout alerts (email / Telegram).
- **More currencies + per-ETF native currency** — today every ETF price is denominated in EUR.

### Technical
- **Postgres** — move off SQLite, introduce proper migrations CI.
- **OAuth / SSO** — Sign in with Google / GitHub in addition to local password.
- **HTMX** — sprinkle HTMX on the dashboard forms to avoid the full-page reload after Save & compute.
- **Playwright e2e tests** — cover login → save → see allocation in a headless browser in CI.
- **Helm chart / Kubernetes manifests** — re-port the `k8s/` manifests from the Node version.
- **OpenTelemetry + Prometheus** — traces and metrics shipped to Grafana Cloud.
- **Renovate / Dependabot** — automated dependency PRs.
- **ruff + mypy** — lint and type-check in CI.
- **Celery + Redis** — background jobs for price polling and email sending.

## License

MIT — see `LICENSE` (to be added).
