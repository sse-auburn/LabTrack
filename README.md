# LabTrack

![CI](https://github.com/Auburn-Smart-Systems-Lab/LabTrack/actions/workflows/ci.yml/badge.svg)

LabTrack is a Django-based lab inventory management system. It tracks every piece of equipment a lab owns — from initial registration through borrowing, reservations, incidents, and maintenance — with role-based access for admins and members.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start — Docker (Production)](#quick-start--docker-production)
- [Raspberry Pi Deployment](#raspberry-pi-deployment)
- [Local Development (no Docker)](#local-development-no-docker)
- [Development with Docker (hot-reload)](#development-with-docker-hot-reload)
- [Running Tests](#running-tests)
- [Environment Variables](#environment-variables)
- [URL Reference](#url-reference)
- [Management Commands](#management-commands)
- [Deployment Checklist](#deployment-checklist)
- [Database Backups](#database-backups)
- [Configuring Email (SMTP)](#configuring-email-smtp)
- [Troubleshooting](#troubleshooting)

---

## Features

| Module | Summary |
|---|---|
| **Equipment** | Register, edit, and deactivate equipment; attach categories and locations; track status and condition; photo uploads; full lifecycle history; movement logs; bulk borrow, reserve, and delete (admin) |
| **Borrowing** | Borrow individual items or kits; automatic approval on submission; member submits return with condition report; equipment owner confirms receipt; overdue detection |
| **Reservations** | Time-bound reservations with start/end dates; pending → confirmed workflow; calendar view; waitlist with automatic notification on cancellation |
| **Kits** | Bundles of equipment items; personal or shared with all members; per-owner return confirmation flow |
| **Consumables** | Stock tracking with units; usage logging; restock; low-stock alerts |
| **Incidents** | Report damage or faults against equipment; assign investigators; track through Open → Investigating → Resolved → Closed; maintenance scheduling; calibration logs |
| **Projects** | Create projects, add members with Lead / Member / Observer roles |
| **P-Card** | Track purchase transactions with itemized line items, receipt upload (DB blob storage), date filtering, Excel/PDF export, and admin-approved deletion requests |
| **Files** | Custom database-backed file storage (no filesystem dependency); receipts and photos stored as binary blobs |
| **Notifications** | In-app and email notifications for every significant event; per-user opt-out by category |
| **Activity Log** | Immutable audit trail of every action across all modules (admins see all; members see their own) |
| **Accounts** | Custom user model (email login); admin-assigned roles; profile editing; per-category notification preferences |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Python 3.11 |
| Database | MySQL 8.0 (production) · SQLite (development / Pi) |
| Task queue | Celery 5, Redis 7 |
| Frontend | Tailwind CSS (CDN), vanilla JS |
| Static files | WhiteNoise |
| Web server | Gunicorn + Nginx |
| Container | Docker, Docker Compose |

---

## Quick Start — Docker (Production)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) v2 (bundled with Docker Desktop)

### 1. Clone the repository

```bash
git clone <repo-url>
cd LabTrack
```

### 2. Create your environment file

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_urlsafe(50))">
DB_PASSWORD=a-strong-database-password
SITE_URL=http://localhost        # or your public domain
```

See [Environment Variables](#environment-variables) for the full reference.

### 3. Build and start

```bash
docker compose up --build -d
```

Four containers start:

| Container | Role |
|---|---|
| `db` | MySQL 8.0, persisted in the `mysql_data` volume |
| `redis` | Redis 7, persisted in the `redis_data` volume |
| `web` | Django + Gunicorn on port 8000 (internal only) |
| `nginx` | Reverse proxy, port 80 (public) |

The `web` container waits for MySQL to pass its healthcheck before starting.
Migrations and `collectstatic` run automatically on every start.

### 4. Create the first admin account

```bash
docker compose exec web python manage.py createsuperuser
```

### 5. Open the app

- Application: **http://localhost**
- Django back-office: **http://localhost/backoffice/**

### Useful Docker commands

```bash
# Follow logs from the web container
docker compose logs -f web

# Run any management command
docker compose exec web python manage.py <command>

# Open a Django shell
docker compose exec web python manage.py shell

# Stop all containers
docker compose down

# Stop and delete all data (full reset, irreversible)
docker compose down -v
```

---

## Raspberry Pi Deployment

A separate Dockerfile and Compose file target ARM devices (Raspberry Pi 3/4/5).
The Pi image uses SQLite instead of MySQL and skips the Redis/Celery services.

```bash
# On the Pi:
git clone <repo-url>
cd LabTrack
cp .env.example .env
# Edit .env — leave DB_HOST blank (SQLite is used automatically)

docker compose -f docker-compose.pi.yml up --build -d
docker compose -f docker-compose.pi.yml exec web python manage.py createsuperuser
```

Access the app at **http://<pi-ip-address>**.

> **Note:** The Pi compose file forces `DB_HOST=""` regardless of what is in `.env`,
> so the MySQL credentials are ignored even if present.

---

## Local Development (no Docker)

### Prerequisites

- Python 3.11+

### 1. Create and activate a virtual environment

```bash
python -m venv env
source env/bin/activate        # Windows: env\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure the environment

```bash
cp .env.example .env
```

For local development set:

```env
DEBUG=True
SECRET_KEY=any-local-dev-key
# Leave DB_HOST blank — SQLite is used automatically when DB_HOST is empty
```

### 3. Migrate, create a superuser, and start

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000**.

---

## Development with Docker (hot-reload)

This overlay uses the Django dev server, mounts source code into the container, and skips MySQL/Redis/Nginx:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

The application is available at **http://localhost:8000**.
Code changes are reflected immediately without rebuilding the image.

---

## Running Tests

The test suite covers all eight application modules (136 tests).
Tests use an in-memory SQLite database — no external services required.

```bash
# Activate your virtual environment first
source env/bin/activate        # Windows: env\Scripts\activate

python manage.py test \
    apps.accounts apps.notifications apps.borrowing apps.reservations \
    apps.kits apps.incidents apps.equipment apps.consumables \
    --verbosity=2
```

To run against SQLite when your `.env` points at MySQL:

```bash
DB_HOST= python manage.py test apps.accounts apps.notifications apps.borrowing \
    apps.reservations apps.kits apps.incidents apps.equipment apps.consumables
```

### CI

Tests run automatically on every push and pull request via GitHub Actions
(`.github/workflows/ci.yml`). The badge at the top of this file shows the
status of the latest run on `master`.

---

## Environment Variables

All variables are read from `.env` via `python-decouple`.
The `.env.example` file documents every variable with its default.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | insecure default | Django secret key. **Must be changed in production.** |
| `DEBUG` | `True` | Set to `False` in production. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hostnames. |
| **Database** | | |
| `DB_HOST` | _(empty)_ | MySQL host. Leave blank to use SQLite. |
| `DB_PORT` | `3306` | MySQL port. |
| `DB_NAME` | `labtrack` | MySQL database name. |
| `DB_USER` | `labtrack` | MySQL username. |
| `DB_PASSWORD` | _(empty)_ | MySQL password. |
| **Redis / Celery** | | |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL. |
| **Email** | | |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server hostname. |
| `EMAIL_PORT` | `587` | SMTP port (587 = STARTTLS). |
| `EMAIL_HOST_USER` | _(empty)_ | SMTP username. When set together with `EMAIL_HOST_PASSWORD`, SMTP delivery is enabled. Leave blank to print emails to the console. |
| `EMAIL_HOST_PASSWORD` | _(empty)_ | SMTP password or App Password. |
| `DEFAULT_FROM_EMAIL` | `noreply@labtrack.local` | The "From" address on outgoing emails. |
| `SITE_URL` | `http://localhost` | Full public URL — used to build absolute links inside notification emails. |
| **Gunicorn** | | |
| `GUNICORN_WORKERS` | `3` | Worker processes. Recommended: `(2 × CPU cores) + 1`. |
| `GUNICORN_TIMEOUT` | `120` | Worker timeout in seconds. |
| **Nginx** | | |
| `NGINX_PORT` | `80` | Host port Nginx listens on. |
| **Logging** | | |
| `DJANGO_LOG_LEVEL` | `INFO` | Django logging level. |

---

## URL Reference

| Path | Description |
|---|---|
| `/` | Redirects to `/dashboard/` |
| `/dashboard/` | Member or admin dashboard |
| `/admin/` | LabTrack admin panel (custom management hub) |
| `/backoffice/` | Django built-in back-office (direct DB access) |
| `/accounts/login/` | Login page |
| `/accounts/register/` | Self-registration |
| `/accounts/profile/` | View own profile |
| `/accounts/profile/edit/` | Edit profile and notification preferences |
| `/accounts/members/` | Member list (admin only) |
| `/equipment/` | Equipment list |
| `/equipment/create/` | Register new equipment |
| `/borrowing/` | Borrow request list |
| `/borrowing/create/` | Submit a borrow request |
| `/borrowing/returns/` | Return queue (items awaiting owner confirmation) |
| `/reservations/` | Reservation list |
| `/reservations/create/` | Create a reservation |
| `/reservations/calendar/` | Calendar view of all reservations |
| `/kits/` | Kit list |
| `/consumables/` | Consumable list |
| `/consumables/low-stock/` | Items at or below their threshold |
| `/incidents/` | Incident list |
| `/projects/` | Project list |
| `/notifications/` | Notification inbox |
| `/activity/` | Activity log (admins see all; members see their own) |
| `/pcard/` | P-Card transaction list |
| `/pcard/create/` | Record a new purchase |
| `/pcard/export/excel/` | Export transactions to Excel |
| `/pcard/export/pdf/` | Export receipt images/PDFs compiled to a single PDF |
| `/pcard/deletion-requests/` | Deletion request queue (admin only) |

---

## Management Commands

### Mark overdue borrows

Finds all borrow requests with status `APPROVED` or `ACTIVE` whose `due_date` is
in the past and transitions them to `OVERDUE`. The transition fires the Django
signal that sends notifications to the borrower and all admins.

```bash
# Preview what would be marked (no changes)
python manage.py mark_overdue_borrows --dry-run

# Apply
python manage.py mark_overdue_borrows
```

**Scheduling this command** — run it once daily via cron or Windows Task Scheduler:

```cron
# Cron (Linux / macOS / Pi) — runs at 01:00 every day
0 1 * * * cd /path/to/LabTrack && python manage.py mark_overdue_borrows >> /var/log/labtrack-overdue.log 2>&1
```

```bash
# Docker — run inside the web container
docker compose exec web python manage.py mark_overdue_borrows
```

---

## Deployment Checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` is a unique random string (50+ characters)
- [ ] `ALLOWED_HOSTS` lists every hostname that will serve the app
- [ ] `SITE_URL` is the full public URL (used in email notification links)
- [ ] MySQL is configured (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)
- [ ] `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are set for SMTP delivery
- [ ] `DEFAULT_FROM_EMAIL` is a valid sender address
- [ ] Nginx is the only publicly exposed port (port 80, or 443 with TLS)

---

## Database Backups

```bash
# Create a mysqldump backup from the running container
docker compose exec db mysqldump -u${DB_USER:-labtrack} -p${DB_PASSWORD:-labtrack} ${DB_NAME:-labtrack} \
    > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker compose exec -T db mysql -u${DB_USER:-labtrack} -p${DB_PASSWORD:-labtrack} ${DB_NAME:-labtrack} \
    < backup_20250101_120000.sql
```

Also back up the `media_data` volume (user-uploaded images):

```bash
docker run --rm \
  -v labtrack_media_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/media_backup_$(date +%Y%m%d).tar.gz /data
```

---

## Configuring Email (SMTP)

### Gmail App Password

1. Enable **2-Step Verification** on the Gmail account.
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and generate an App Password.
3. Set in `.env`:

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx   # 16-character app password (spaces optional)
DEFAULT_FROM_EMAIL=LabTrack <you@gmail.com>
SITE_URL=https://yourdomain.com
```

Restart the web container after changing `.env`:

```bash
docker compose restart web
```

### Other SMTP providers

Change `EMAIL_HOST` and `EMAIL_PORT` for your provider. For SSL on port 465 also add `EMAIL_USE_SSL=True` to `.env` (and remove `EMAIL_PORT=587`).

### Verify SMTP is working

```bash
docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail('LabTrack test', 'Delivery confirmed.', None, ['you@example.com'])
print('Sent OK')
"
```

---

## Troubleshooting

### Web container exits immediately or migrations fail

```bash
docker compose logs web
```

Common causes:
- `DB_HOST` is set but MySQL hasn't finished starting — run `docker compose restart web` after a few seconds.
- Mismatched `DB_PASSWORD` between `.env` and the `db` service.

### Static files return 404

```bash
docker compose exec web python manage.py collectstatic --noinput
docker compose restart nginx
```

### Emails are not being sent

**Step 1** — Check which email backend is active:

```bash
docker compose exec web python -c "from django.conf import settings; print(settings.EMAIL_BACKEND)"
```

If it prints `...console.EmailBackend`, then `EMAIL_HOST_USER` or `EMAIL_HOST_PASSWORD` is missing. Set both in `.env` and restart.

**Step 2** — Test delivery directly:

```bash
docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Hello', None, ['you@example.com'])
print('OK')
"
```

**Step 3** — Check logs for SMTP errors:

```bash
docker compose logs web | grep -i email
```

Common causes: expired App Password, port 587 blocked by the hosting provider (try port 465 + `EMAIL_USE_SSL=True`).

**A user is not receiving emails despite SMTP working:**
Check their profile. The user may have disabled email notifications globally or for a specific category under **Profile → Edit Profile → Notification Preferences**.

### CSRF verification failed in production

Ensure `ALLOWED_HOSTS` includes your actual domain and that the `Host` header
is forwarded correctly from Nginx. The provided `nginx/nginx.conf` already sets
`proxy_set_header Host $host` for this purpose.

### Full development reset

```bash
docker compose down -v          # deletes all volumes including the database
docker compose up -d            # fresh start; migrations run automatically
docker compose exec web python manage.py createsuperuser
```

### Container status

```bash
docker compose ps
docker compose logs --tail=50 web
```
