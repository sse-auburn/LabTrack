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
    echo "==> [scheduler] $(date '+%Y-%m-%d %H:%M:%S %Z') Running check_reservation_notifications..."
    python manage.py check_reservation_notifications
}

while true; do
    now=$(date +%s)
    today_8am=$(date -d 'today 08:00' +%s)
    if [ "$now" -lt "$today_8am" ]; then
        next_run=$today_8am
    else
        next_run=$(date -d 'tomorrow 08:00' +%s)
    fi
    sleep_secs=$((next_run - now))
    echo "==> [scheduler] Next run in ${sleep_secs}s at $(date -d "@${next_run}" '+%Y-%m-%d %H:%M %Z')"
    sleep "$sleep_secs"
    run_daily
done
