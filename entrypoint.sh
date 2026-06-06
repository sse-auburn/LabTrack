#!/bin/sh
set -e

echo "==> Waiting for database..."
until python -c "
import os, sys
db_host = os.environ.get('DB_HOST', '')
if not db_host:
    sys.exit(0)
import socket, time
for i in range(30):
    try:
        socket.create_connection((db_host, int(os.environ.get('DB_PORT', 3306))), timeout=1)
        sys.exit(0)
    except OSError:
        time.sleep(1)
sys.exit(1)
"; do
  echo "    Database unavailable, retrying..."
  sleep 2
done
echo "    Database is ready."

echo "==> Applying migrations..."
python manage.py migrate --noinput --fake-initial

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile - \
    --log-level "${GUNICORN_LOG_LEVEL:-info}"
