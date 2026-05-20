"""
Management command: sync_all_equipment_status

One-off cleanup command to recalculate the status of every equipment item
based on live reservations and maintenance logs.

Usage:
    python manage.py sync_all_equipment_status
    python manage.py sync_all_equipment_status --dry-run
"""

from django.core.management.base import BaseCommand

from apps.equipment.models import Equipment
from apps.equipment.utils import sync_equipment_status


class Command(BaseCommand):
    help = 'Recompute and sync the status for all equipment items.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without writing to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        queryset = Equipment.objects.filter(is_active=True)
        total = queryset.count()

        updated = 0
        unchanged = 0

        self.stdout.write(f'Scanning {total} equipment item(s)...\n')

        for equipment in queryset.iterator():
            old_status = equipment.status

            if dry_run:
                # Call a dry-run version: compute but don't save
                new_status = self._compute_status(equipment)
            else:
                sync_equipment_status(equipment)
                # Refresh to see the new value (save already happened)
                equipment.refresh_from_db()
                new_status = equipment.status

            if old_status != new_status:
                updated += 1
                self.stdout.write(
                    f'  {equipment.name}: {old_status} -> {new_status}'
                )
            else:
                unchanged += 1

        self.stdout.write('\n' + self.style.SUCCESS(
            f'Done. {updated} changed, {unchanged} unchanged (dry_run={dry_run}).'
        ))

    def _compute_status(self, equipment):
        """Mirror sync_equipment_status logic without saving."""
        from django.db.models import Q
        from apps.incidents.models import MaintenanceLog
        from apps.reservations.models import Reservation

        if equipment.status in ('DAMAGED', 'RETIRED'):
            return equipment.status

        res_q = Q(equipment=equipment) | Q(kit__items__equipment=equipment)

        if Reservation.objects.filter(
            res_q, status__in=['ACTIVE', 'RETURN_PENDING']
        ).exists():
            return 'BORROWED'

        if MaintenanceLog.objects.filter(
            equipment=equipment, status__in=['SCHEDULED', 'IN_PROGRESS']
        ).exists():
            return 'MAINTENANCE'

        return 'AVAILABLE'
