"""
Management command: mark_overdue_borrows

Scans all active borrow requests (status APPROVED or ACTIVE) whose due_date
has passed and flips their status to OVERDUE. Each record is saved individually
so the post_save signal in borrowing/signals.py fires, which sends notifications
to the borrower and admins.

Run manually:
    python manage.py mark_overdue_borrows
    python manage.py mark_overdue_borrows --dry-run

Recommended schedule (cron / Celery Beat / Windows Task Scheduler):
    # Every hour on Linux/Mac
    0 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py mark_overdue_borrows >> /var/log/labtrack/overdue.log 2>&1
"""

from datetime import date

from django.core.management.base import BaseCommand

from apps.borrowing.models import BorrowRequest


class Command(BaseCommand):
    help = 'Mark borrow requests as OVERDUE when their due_date has passed.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be marked without making any changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = date.today()

        overdue_qs = BorrowRequest.objects.filter(
            status__in=['APPROVED', 'ACTIVE'],
            due_date__lt=today,
        ).select_related('borrower', 'equipment', 'kit')

        count = overdue_qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No overdue borrows found.'))
            return

        if dry_run:
            self.stdout.write(f'Dry run — {count} borrow(s) would be marked OVERDUE:')
            for borrow in overdue_qs:
                self.stdout.write(
                    f'  #{borrow.pk} {borrow.item} '
                    f'(borrower: {borrow.borrower.username}, due: {borrow.due_date})'
                )
            return

        marked = 0
        for borrow in overdue_qs:
            borrow.status = 'OVERDUE'
            borrow.save(update_fields=['status'])
            marked += 1

        self.stdout.write(self.style.WARNING(f'Marked {marked} borrow(s) as OVERDUE.'))
