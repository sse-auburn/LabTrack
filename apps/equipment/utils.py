"""Utility functions for the equipment app."""

import random
from datetime import date


def sync_equipment_status(equipment, exclude_borrow_pk=None):
    """Compute and save the correct status for *equipment* by querying live data.

    Priority (highest first):
    1. DAMAGED / RETIRED — never overridden automatically.
    2. BORROWED  — any active BorrowRequest or ACTIVE/RETURN_PENDING Reservation.
    3. MAINTENANCE — any active MaintenanceLog (SCHEDULED / IN_PROGRESS).
    4. RESERVED  — a CONFIRMED Reservation whose window spans today.
    5. AVAILABLE — nothing else blocking.
    """
    if equipment.status in ('DAMAGED', 'RETIRED'):
        return

    from django.db.models import Q
    from apps.incidents.models import MaintenanceLog
    from apps.reservations.models import Reservation

    today = date.today()
    res_q = Q(equipment=equipment) | Q(kit__items__equipment=equipment)

    if Reservation.objects.filter(
        res_q,
        status__in=['ACTIVE', 'RETURN_PENDING'],
    ).exists():
        new_status = 'BORROWED'
    else:
        borrow_blocked = False
        try:
            from apps.borrowing.models import BorrowRequest
            borrow_q = Q(equipment=equipment) | Q(kit__items__equipment=equipment)
            borrow_qs = BorrowRequest.objects.filter(
                borrow_q,
                status__in=['APPROVED', 'ACTIVE', 'RETURN_PENDING'],
            )
            if exclude_borrow_pk:
                borrow_qs = borrow_qs.exclude(pk=exclude_borrow_pk)
            borrow_blocked = borrow_qs.exists()
        except RuntimeError:
            # Borrowing app is not in INSTALLED_APPS
            pass

        if borrow_blocked:
            new_status = 'BORROWED'
        elif MaintenanceLog.objects.filter(
            equipment=equipment,
            status__in=['SCHEDULED', 'IN_PROGRESS'],
        ).exists():
            new_status = 'MAINTENANCE'
        elif Reservation.objects.filter(
            res_q,
            status='CONFIRMED',
            start_date__lte=today,
            end_date__gte=today,
        ).exists():
            new_status = 'RESERVED'
        else:
            new_status = 'AVAILABLE'

    if equipment.status != new_status:
        equipment.status = new_status
        equipment.save(update_fields=['status'])


# A curated list of pleasant, distinct Tailwind-ish hex colors.
# Used as a pool before falling back to fully random generation.
COLOR_PALETTE = [
    '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e',
    '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1',
    '#8b5cf6', '#a855f7', '#d946ef', '#ec4899', '#f43f5e', '#78716c',
    '#475569', '#0f766e', '#b45309', '#7c2d12', '#831843', '#4c1d95',
]


def generate_unique_color(existing_colors=None, attempts=50):
    """
    Return a hex color string that is not present in *existing_colors*.

    Parameters
    ----------
    existing_colors : iterable of str, optional
        Colors to avoid (e.g. ``Category.objects.values_list('color', flat=True)``).
    attempts : int
        Max tries before giving up and returning a fully random color.

    Returns
    -------
    str
        A 7-character hex color (e.g. ``#3b82f6``).
    """
    existing = set(existing_colors or [])

    # 1. Try palette colors first (visually distinct)
    palette = [c for c in COLOR_PALETTE if c not in existing]
    random.shuffle(palette)
    if palette:
        return palette[0]

    # 2. Fall back to random generation
    for _ in range(attempts):
        color = '#{:06x}'.format(random.randint(0, 0xFFFFFF))
        if color not in existing:
            return color

    # 3. Ultimate fallback — just return a random color
    return '#{:06x}'.format(random.randint(0, 0xFFFFFF))
