"""
Management command: expire_reservations

Scans all confirmed reservations whose end_date has passed and transitions
them to EXPIRED, freeing up the reserved equipment/kit status back to AVAILABLE.

Run manually:
    python manage.py expire_reservations

Recommended schedule (cron / Celery / systemd timer):
    # Run daily at midnight
    0 0 * * * cd /path/to/project && /path/to/venv/bin/python manage.py expire_reservations >> /var/log/labtrack/expiry.log 2>&1
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.activity.utils import log_activity
from apps.equipment.utils import sync_equipment_status
from apps.reservations.models import Reservation


class Command(BaseCommand):
    help = 'Expire reservations whose end_date has passed.'

    def handle(self, *args, **options):
        today = date.today()

        expired_reservations = Reservation.objects.filter(
            status='CONFIRMED',
            end_date__lt=today,
        ).select_related('equipment', 'kit')

        count = expired_reservations.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired reservations found.'))
            return

        updated = 0
        with transaction.atomic():
            for reservation in expired_reservations:
                equipment = reservation.equipment
                kit = reservation.kit

                reservation.status = 'EXPIRED'
                reservation.save(update_fields=['status'])

                # Recompute status after expiry — another blocker may still apply.
                if equipment:
                    sync_equipment_status(equipment)
                if kit:
                    for kit_item in kit.items.select_related('equipment'):
                        sync_equipment_status(kit_item.equipment)

                log_activity(
                    actor=None,
                    action='RESERVATION_EXPIRED',
                    description=(
                        f'Reservation #{reservation.pk} for '
                        f'{reservation.equipment or reservation.kit} expired '
                        f'(end date was {reservation.end_date}).'
                    ),
                    content_type_label='reservation',
                    object_id=reservation.pk,
                    object_repr=str(reservation),
                )
                updated += 1

        self.stdout.write(
            self.style.WARNING(f'Expired {updated} reservation(s).')
        )
