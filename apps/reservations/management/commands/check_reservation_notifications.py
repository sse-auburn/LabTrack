"""
Management command: check_reservation_notifications

Run daily (e.g. via cron: 0 8 * * * python manage.py check_reservation_notifications)
to auto-transition reservations and notify both parties when a reservation starts or ends.
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.utils import notify
from apps.reservations.models import Reservation


class Command(BaseCommand):
    help = 'Send start/end notifications for reservations and transition their status.'

    def handle(self, *args, **options):
        today = date.today()
        started = self._process_starting(today)
        ended = self._process_ending(today)
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. {started} reservation(s) activated, {ended} moved to return-pending.'
            )
        )

    def _process_starting(self, today):
        """Confirm → Active: notify both requester and equipment owner."""
        qs = Reservation.objects.filter(
            start_date=today,
            status='CONFIRMED',
            start_notified=False,
        ).select_related('requester', 'equipment', 'kit')

        count = 0
        for res in qs:
            item_name = str(res.equipment or res.kit or 'item')

            # Notify requester
            notify(
                recipient=res.requester,
                title='Your reservation starts today',
                message=(
                    f'Your reservation for "{item_name}" starts today '
                    f'({res.start_date} – {res.end_date}). '
                    f'The item is now considered to be in your possession.'
                ),
                level='info',
                link=f'/reservations/{res.pk}/',
                category='reservations',
            )

            # Notify equipment/kit owner
            owner = None
            if res.equipment and res.equipment.owner and res.equipment.owner != res.requester:
                owner = res.equipment.owner
            elif res.kit and res.kit.created_by and res.kit.created_by != res.requester:
                owner = res.kit.created_by

            if owner:
                notify(
                    recipient=owner,
                    title='Equipment reservation now active',
                    message=(
                        f'{res.requester.full_name} now has "{item_name}" '
                        f'(reservation active until {res.end_date}).'
                    ),
                    level='info',
                    link=f'/reservations/{res.pk}/',
                    category='reservations',
                )

            res.status = 'ACTIVE'
            res.start_notified = True
            res.save(update_fields=['status', 'start_notified'])
            count += 1

        return count

    def _process_ending(self, today):
        """Active/Confirmed → Return Pending: notify owner to approve return."""
        qs = Reservation.objects.filter(
            end_date=today,
            status__in=['CONFIRMED', 'ACTIVE'],
            end_notified=False,
        ).select_related('requester', 'equipment', 'kit')

        count = 0
        for res in qs:
            item_name = str(res.equipment or res.kit or 'item')

            owner = None
            if res.equipment and res.equipment.owner:
                owner = res.equipment.owner
            elif res.kit and res.kit.created_by:
                owner = res.kit.created_by

            if owner:
                notify(
                    recipient=owner,
                    title='Return approval needed',
                    message=(
                        f'{res.requester.full_name}\'s reservation for "{item_name}" '
                        f'ended today. Please confirm that you received it back.'
                    ),
                    level='warning',
                    link=f'/reservations/{res.pk}/',
                    category='reservations',
                )

            # Also remind the requester
            notify(
                recipient=res.requester,
                title='Reservation period ended',
                message=(
                    f'Your reservation for "{item_name}" ended today. '
                    f'Please ensure the item has been returned to its owner.'
                ),
                level='warning',
                link=f'/reservations/{res.pk}/',
                category='reservations',
            )

            res.status = 'RETURN_PENDING'
            res.end_notified = True
            res.save(update_fields=['status', 'end_notified'])
            count += 1

        return count
