# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps needed to build mysqlclient and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        pkg-config \
        gcc \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    # ── Runtime defaults (override via .env or docker-compose environment) ──────
    DEBUG=False \
    ALLOWED_HOSTS=localhost \
    # Database — leave DB_HOST blank to use SQLite (dev only)
    DB_HOST="" \
    DB_PORT=3306 \
    DB_NAME=labtrack \
    DB_USER=labtrack \
    # Redis / Celery
    REDIS_URL=redis://redis:6379/0 \
    # Email — set EMAIL_HOST_USER + EMAIL_HOST_PASSWORD to enable SMTP delivery
    EMAIL_HOST=smtp.gmail.com \
    EMAIL_PORT=587 \
    EMAIL_HOST_USER="" \
    EMAIL_HOST_PASSWORD="" \
    DEFAULT_FROM_EMAIL=noreply@labtrack.local \
    SITE_URL=http://localhost \
    # Gunicorn
    GUNICORN_WORKERS=3 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_LOG_LEVEL=info

WORKDIR /app

# Runtime system deps (MySQL client library + Pillow image libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmariadb3 \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project source
COPY . .

# Create dirs that must exist at runtime
RUN mkdir -p /app/staticfiles /app/media /app/static

# Entrypoints
COPY entrypoint.sh /entrypoint.sh
COPY scheduler.sh /scheduler.sh
RUN chmod +x /entrypoint.sh /scheduler.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
