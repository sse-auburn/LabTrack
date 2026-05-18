#!/bin/sh
set -e

echo "==> [scheduler] Waiting for database..."
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
  sleep 2
done
echo "==> [scheduler] Database ready."

run_daily() {
    echo "==> [scheduler] $(date -u '+%Y-%m-%d %H:%M:%S UTC') Running check_reservation_notifications..."
    python manage.py check_reservation_notifications
}

while true; do
    now=$(date -u +%s)
    today_8am=$(date -u -d 'today 08:00' +%s)
    if [ "$now" -lt "$today_8am" ]; then
        next_run=$today_8am
    else
        next_run=$(date -u -d 'tomorrow 08:00' +%s)
    fi
    sleep_secs=$((next_run - now))
    echo "==> [scheduler] Next run in ${sleep_secs}s at $(date -u -d "@${next_run}" '+%Y-%m-%d %H:%M UTC')"
    sleep "$sleep_secs"
    run_daily
done
