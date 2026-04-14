# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    DJANGO_DEBUG=0

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends gettext curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Compile translations and collect static files. A build-time SECRET_KEY is fine.
RUN SECRET_KEY=build-only DJANGO_DEBUG=0 python manage.py compilemessages \
 && SECRET_KEY=build-only DJANGO_DEBUG=0 python manage.py collectstatic --noinput

RUN useradd --system --uid 1001 app \
 && mkdir -p /data \
 && chown -R app:app /app /data
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn dividendapp.wsgi:application --bind 0.0.0.0:${PORT} --workers 3"]
