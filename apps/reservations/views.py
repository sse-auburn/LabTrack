"""Views for the reservations app."""

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.activity.utils import log_activity
from apps.equipment.models import Equipment
from apps.equipment.utils import sync_equipment_status
from apps.notifications.utils import notify, notify_admins
from apps.reservations.forms import BulkReservationForm, ReservationForm, ReturnForm, WaitlistEntryForm
from apps.reservations.models import Reservation, ReservationItemReturn, WaitlistEntry


def _is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


@login_required
def reservation_list_view(request):
    """List reservations: members see their own; admins see all.

    Also surfaces two quick-access tables for RETURN_PENDING:
      - return_approvals  : user is the owner who must confirm
      - my_pending_returns: user is the requester waiting for owner confirmation
    """
    from django.db.models import Q

    if _is_admin(request.user):
        qs = Reservation.objects.select_related('requester', 'equipment', 'kit')
    else:
        qs = Reservation.objects.filter(
            requester=request.user
        ).select_related('equipment', 'kit')

    status_filter = request.GET.get('status', '').strip()
    from_date = request.GET.get('from_date', '').strip()
    to_date = request.GET.get('to_date', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if from_date:
        qs = qs.filter(start_date__gte=from_date)
    if to_date:
        qs = qs.filter(end_date__lte=to_date)

    paginator = Paginator(qs.order_by('-start_date'), 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    # ── Quick-access tables ───────────────────────────────────────────────
    # 1. Returns the current user needs to confirm as owner
    returns_i_must_confirm = Reservation.objects.filter(
        status='RETURN_PENDING'
    ).filter(
        Q(equipment__owner=request.user) |
        Q(kit__items__equipment__owner=request.user)
    ).distinct().select_related('requester', 'equipment', 'kit').order_by('returned_date')

    # 2. Returns the current user submitted, waiting for owner to confirm
    my_returns_waiting = Reservation.objects.filter(
        status='RETURN_PENDING',
        requester=request.user,
    ).exclude(
        Q(equipment__owner=request.user) |
        Q(kit__items__equipment__owner=request.user)
    ).distinct().select_related('requester', 'equipment', 'kit').order_by('-returned_date')

    # 3. Current & future reservations (pending, confirmed, active)
    my_current_future_reservations = Reservation.objects.filter(
        status__in=['PENDING', 'CONFIRMED', 'ACTIVE'],
        requester=request.user,
    ).select_related('requester', 'equipment', 'kit').order_by('start_date')

    # 5. Past reservations (returned, cancelled, expired, completed)
    my_past_reservations = Reservation.objects.filter(
        status__in=['RETURNED', 'CANCELLED', 'EXPIRED', 'COMPLETED'],
        requester=request.user,
    ).select_related('requester', 'equipment', 'kit').order_by('-end_date')

    # 4. Admin: returns for OTHER owners that admin can approve on behalf
    other_owner_returns = None
    if _is_admin(request.user):
        other_owner_returns = Reservation.objects.filter(
            status='RETURN_PENDING'
        ).exclude(
            Q(equipment__owner=request.user) |
            Q(kit__items__equipment__owner=request.user)
        ).distinct().select_related('requester', 'equipment', 'kit').order_by('returned_date')

    return render(request, 'reservations/reservation_list.html', {
        'reservations': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'status_filter': status_filter,
        'from_date': from_date,
        'to_date': to_date,
        'status_choices': Reservation.STATUS_CHOICES,
        'returns_i_must_confirm': returns_i_must_confirm,
        'my_returns_waiting': my_returns_waiting,
        'my_current_future_reservations': my_current_future_reservations,
        'my_past_reservations': my_past_reservations,
        'other_owner_returns': other_owner_returns,
    })


@login_required
def reservation_calendar_view(request):
    """Render a month-grid calendar of reservations."""
    import calendar
    from collections import defaultdict
    from datetime import date, timedelta

    from django.db.models import Q

    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if month < 1 or month > 12:
            raise ValueError
    except (ValueError, TypeError):
        year, month = today.year, today.month

    equipment_id = request.GET.get('equipment_id', '').strip()
    kit_id = request.GET.get('kit_id', '').strip()

    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    qs = Reservation.objects.filter(
        status__in=['PENDING', 'CONFIRMED', 'ACTIVE', 'RETURN_PENDING', 'COMPLETED', 'CANCELLED', 'EXPIRED'],
        start_date__lte=month_end,
        end_date__gte=month_start,
    ).select_related('equipment', 'kit', 'requester')

    if equipment_id:
        from apps.kits.models import KitItem
        kit_ids = KitItem.objects.filter(
            equipment_id=equipment_id
        ).values_list('kit_id', flat=True)
        qs = qs.filter(
            Q(equipment_id=equipment_id) | Q(kit_id__in=kit_ids)
        )
    elif kit_id:
        qs = qs.filter(kit_id=kit_id)

    # Index reservations across every day they span within the visible month
    reservations_by_day = defaultdict(list)
    for res in qs:
        span_start = max(res.start_date, month_start)
        span_end = min(res.end_date, month_end)
        current = span_start
        while current <= span_end:
            reservations_by_day[current.day].append(res)
            current += timedelta(days=1)

    # Build week grid (Monday-first)
    cal = calendar.monthcalendar(year, month)
    calendar_weeks = []
    for week in cal:
        week_days = []
        for day_num in week:
            if day_num == 0:
                week_days.append({'day': '', 'current_month': False, 'is_today': False, 'reservations': []})
            else:
                d = date(year, month, day_num)
                week_days.append({
                    'day': day_num,
                    'current_month': True,
                    'is_today': d == today,
                    'reservations': reservations_by_day.get(day_num, []),
                })
        calendar_weeks.append(week_days)

    # Navigation months
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_name = date(year, month, 1).strftime('%B')

    from apps.kits.models import Kit
    return render(request, 'reservations/reservation_calendar.html', {
        'calendar_weeks': calendar_weeks,
        'current_year': year,
        'current_month': month,
        'current_month_name': month_name,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'equipment_list': Equipment.objects.filter(is_active=True, approval_status='APPROVED').order_by('name'),
        'kit_list': Kit.objects.filter(is_active=True).order_by('name'),
        'selected_equipment_id': equipment_id,
        'selected_kit_id': kit_id,
    })


@login_required
def reservation_create_view(request):
    """Create a new reservation with overlap and date validation."""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.requester = request.user
            today = timezone.now().date()
            if reservation.start_date <= today:
                reservation.status = 'ACTIVE'
                reservation.start_notified = True
            else:
                reservation.status = 'CONFIRMED'
            reservation.save()

            # Sync equipment status so kit reservations are reflected on individual items.
            if reservation.equipment:
                sync_equipment_status(reservation.equipment)
            if reservation.kit:
                for kit_item in reservation.kit.items.select_related('equipment'):
                    sync_equipment_status(kit_item.equipment)

            log_activity(
                actor=request.user,
                action='RESERVATION_CREATED',
                description=(
                    f'{request.user.full_name or request.user.username} reserved '
                    f'{reservation.equipment or reservation.kit} '
                    f'({reservation.start_date} – {reservation.end_date})'
                ),
                content_type_label='reservation',
                object_id=reservation.pk,
                object_repr=str(reservation),
                request=request,
            )

            # Notify the equipment/kit owner informally
            if reservation.equipment and reservation.equipment.owner and reservation.equipment.owner != request.user:
                notify(
                    recipient=reservation.equipment.owner,
                    title='Your Equipment Was Reserved',
                    message=(
                        f'{request.user.full_name or request.user.username} has reserved '
                        f'"{reservation.equipment.name}" ({reservation.start_date} – {reservation.end_date}).'
                    ),
                    level='info',
                    link=f'/reservations/{reservation.pk}/',
                    category='reservations',
                )
            elif reservation.kit:
                # Notify all individual equipment owners in the kit
                owner_equipment = {}
                for ki in reservation.kit.items.select_related('equipment__owner'):
                    if ki.equipment.owner and ki.equipment.owner != request.user:
                        owner_equipment.setdefault(ki.equipment.owner, []).append(ki.equipment.name)
                for owner, eq_names in owner_equipment.items():
                    notify(
                        recipient=owner,
                        title='Your Equipment Was Reserved (via Kit)',
                        message=(
                            f'{request.user.full_name or request.user.username} has reserved '
                            f'"{reservation.kit.name}" which includes your equipment '
                            f'"{", ".join(eq_names)}" ({reservation.start_date} – {reservation.end_date}).'
                        ),
                        level='info',
                        link=f'/reservations/{reservation.pk}/',
                        category='reservations',
                    )

            messages.success(request, 'Reservation confirmed.')
            return redirect('reservations:detail', pk=reservation.pk)
    else:
        equipment_id = request.GET.get('equipment')
        kit_id = request.GET.get('kit')
        initial = {}
        if equipment_id:
            initial['equipment'] = equipment_id
        elif kit_id:
            initial['kit'] = kit_id
        form = ReservationForm(initial=initial)

    return render(request, 'reservations/reservation_form.html', {'form': form})


@login_required
def reservation_bulk_create_view(request):
    """Reserve multiple equipment items at once."""
    if request.method == 'POST':
        equipment_ids = request.POST.getlist('equipment_ids')
        if not equipment_ids:
            messages.error(request, 'No items selected.')
            return redirect('equipment:list')

        items = Equipment.objects.filter(pk__in=equipment_ids, is_active=True)
        if not items.exists():
            messages.error(request, 'No valid items selected.')
            return redirect('equipment:list')

        form = BulkReservationForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            purpose = form.cleaned_data['purpose']

            with transaction.atomic():
                locked_items = Equipment.objects.select_for_update().filter(
                    pk__in=[i.pk for i in items]
                )
                created = []
                for item in locked_items:
                    # Check for overlapping confirmed reservations (direct or via kit)
                    from django.db.models import Q
                    overlap = Reservation.objects.filter(
                        status__in=['PENDING', 'CONFIRMED', 'ACTIVE', 'RETURN_PENDING'],
                        start_date__lte=end_date,
                        end_date__gte=start_date,
                    ).filter(Q(equipment=item) | Q(kit__items__equipment=item)).exists()
                    if overlap:
                        continue

                    reservation = Reservation.objects.create(
                        requester=request.user,
                        equipment=item,
                        start_date=start_date,
                        end_date=end_date,
                        purpose=purpose,
                        status='CONFIRMED',
                    )
                    created.append(item.name)

            if created:
                messages.success(
                    request,
                    f'Reserved {len(created)} item(s): {", ".join(created)}.'
                )
                notify(
                    recipient=request.user,
                    title='Items Reserved',
                    message=f'You have reserved {len(created)} item(s).',
                    level='success',
                    link=reverse('reservations:list'),
                    category='reservations',
                )
            skipped = len(locked_items) - len(created)
            if skipped:
                messages.warning(request, f'{skipped} item(s) were skipped due to overlapping reservations.')

            return redirect('reservations:list')

        items = Equipment.objects.filter(pk__in=equipment_ids, is_active=True)
        return render(request, 'reservations/reservation_bulk_form.html', {
            'form': form,
            'items': items,
            'equipment_ids': equipment_ids,
        })

    else:
        equipment_ids = request.GET.getlist('ids')
        if not equipment_ids:
            messages.error(request, 'No items selected.')
            return redirect('equipment:list')

        items = Equipment.objects.filter(pk__in=equipment_ids, is_active=True)
        unavailable = Equipment.objects.filter(
            pk__in=equipment_ids
        ).filter(status__in=['BORROWED', 'RETIRED'])

        form = BulkReservationForm()
        return render(request, 'reservations/reservation_bulk_form.html', {
            'form': form,
            'items': items,
            'unavailable': unavailable,
            'equipment_ids': equipment_ids,
        })


@login_required
def reservation_detail_view(request, pk):
    """Show the details of a single reservation."""
    reservation = get_object_or_404(
        Reservation.objects.select_related('requester', 'equipment', 'kit')
        .prefetch_related('kit__items__equipment__owner'),
        pk=pk,
    )

    if not _is_admin(request.user) and reservation.requester != request.user:
        messages.error(request, 'You do not have permission to view this reservation.')
        return redirect('reservations:list')

    if reservation.equipment:
        waitlist_entries = WaitlistEntry.objects.filter(
            equipment=reservation.equipment
        ).select_related('user').order_by('position', 'created_at')
        is_owner = reservation.equipment.owner == request.user
    elif reservation.kit:
        waitlist_entries = WaitlistEntry.objects.filter(
            kit=reservation.kit
        ).select_related('user').order_by('position', 'created_at')
        is_owner = any(
            ki.equipment.owner == request.user
            for ki in reservation.kit.items.all()
        )
    else:
        waitlist_entries = WaitlistEntry.objects.none()
        is_owner = False

    return render(request, 'reservations/reservation_detail.html', {
        'reservation': reservation,
        'waitlist_entries': waitlist_entries,
        'is_owner': is_owner,
    })


@login_required
def reservation_cancel_view(request, pk):
    """Cancel a reservation and notify the next person on the waitlist."""
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'requester', 'equipment', 'equipment__owner', 'equipment__location', 'kit'
        ).prefetch_related('kit__items__equipment__owner', 'kit__items__equipment__location'),
        pk=pk,
    )

    if not _is_admin(request.user) and reservation.requester != request.user:
        messages.error(request, 'You do not have permission to cancel this reservation.')
        return redirect('reservations:list')

    if reservation.status in ('CANCELLED', 'COMPLETED', 'EXPIRED', 'RETURNED', 'RETURN_PENDING'):
        messages.error(request, 'This reservation cannot be cancelled in its current state.')
        return redirect('reservations:detail', pk=reservation.pk)

    if request.method == 'POST':
        reservation.status = 'CANCELLED'
        reservation.save()

        # Recompute status — another borrow/maintenance may still be blocking.
        if reservation.equipment:
            sync_equipment_status(reservation.equipment)
        if reservation.kit:
            for kit_item in reservation.kit.items.select_related('equipment'):
                sync_equipment_status(kit_item.equipment)

        log_activity(
            actor=request.user,
            action='RESERVATION_CANCELLED',
            description=(
                f'{request.user.full_name or request.user.username} cancelled reservation #{reservation.pk} '
                f'for {reservation.equipment or reservation.kit}'
            ),
            content_type_label='reservation',
            object_id=reservation.pk,
            object_repr=str(reservation),
            request=request,
        )

        # Notify next person on the waitlist.
        waitlist_qs = None
        if reservation.equipment:
            waitlist_qs = WaitlistEntry.objects.filter(
                equipment=reservation.equipment, notified=False
            ).order_by('position', 'created_at')
        elif reservation.kit:
            waitlist_qs = WaitlistEntry.objects.filter(
                kit=reservation.kit, notified=False
            ).order_by('position', 'created_at')

        if waitlist_qs is not None:
            next_entry = waitlist_qs.first()
            if next_entry:
                item_name = str(reservation.equipment or reservation.kit)
                notify(
                    recipient=next_entry.user,
                    title='Reservation Slot Available',
                    message=(
                        f'A reservation for "{item_name}" has been cancelled. '
                        'You are next on the waitlist — you may now reserve it.'
                    ),
                    level='info',
                    link=reverse('reservations:create'),
                    category='reservations',
                )
                next_entry.notified = True
                next_entry.save(update_fields=['notified'])

        messages.success(request, 'Reservation cancelled.')
        return redirect('reservations:list')

    return render(request, 'reservations/reservation_confirm_cancel.html', {
        'reservation': reservation,
    })


@login_required
def reservation_confirm_view(request, pk):
    """Confirm a pending reservation — allowed by the equipment/kit owner."""
    reservation = get_object_or_404(
        Reservation.objects.select_related('requester', 'equipment', 'kit'),
        pk=pk,
    )

    # Determine if user is an owner of the reserved item.
    is_owner = False
    if reservation.equipment and request.user == reservation.equipment.owner:
        is_owner = True
    elif reservation.kit:
        kit_owner_pks = reservation.kit.items.values_list('equipment__owner', flat=True)
        if request.user.pk in kit_owner_pks:
            is_owner = True

    if not is_owner and not _is_admin(request.user):
        messages.error(request, 'Only the equipment owner can confirm this reservation.')
        return redirect('reservations:detail', pk=reservation.pk)

    if reservation.status != 'PENDING':
        messages.error(request, 'Only pending reservations can be confirmed.')
        return redirect('reservations:detail', pk=reservation.pk)

    if request.method == 'POST':
        today = timezone.now().date()
        if reservation.start_date <= today:
            reservation.status = 'ACTIVE'
            reservation.start_notified = True
        else:
            reservation.status = 'CONFIRMED'
        reservation.save()

        # Sync equipment status so kit reservations are reflected on individual items.
        if reservation.equipment:
            sync_equipment_status(reservation.equipment)
        if reservation.kit:
            for kit_item in reservation.kit.items.select_related('equipment'):
                sync_equipment_status(kit_item.equipment)

        log_activity(
            actor=request.user,
            action='RESERVATION_CONFIRMED',
            description=(
                f'{request.user.full_name or request.user.username} confirmed reservation #{reservation.pk} '
                f'for {reservation.equipment or reservation.kit}'
            ),
            content_type_label='reservation',
            object_id=reservation.pk,
            object_repr=str(reservation),
            request=request,
        )

        notify(
            recipient=reservation.requester,
            title='Reservation Confirmed',
            message=(
                f'Your reservation for "{reservation.equipment or reservation.kit}" '
                f'({reservation.start_date} – {reservation.end_date}) has been confirmed.'
            ),
            level='success',
            link=f'/reservations/{reservation.pk}/',
            category='reservations',
        )

        messages.success(request, 'Reservation confirmed.')
        return redirect('reservations:detail', pk=reservation.pk)

    return redirect('reservations:detail', pk=reservation.pk)


@login_required
def reservation_return_view(request, pk):
    """Requester submits the return of a reserved item — status goes to RETURN_PENDING."""
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'requester', 'equipment', 'equipment__owner', 'equipment__location', 'kit'
        ).prefetch_related('kit__items__equipment__owner', 'kit__items__equipment__location'),
        pk=pk,
    )

    if reservation.requester != request.user:
        messages.error(request, 'Only the requester can submit a return.')
        return redirect('reservations:detail', pk=pk)

    if reservation.status not in ('CONFIRMED', 'ACTIVE'):
        messages.error(request, 'Only confirmed or active reservations can be returned.')
        return redirect('reservations:detail', pk=pk)

    if request.method == 'POST':
        reservation.status = 'RETURN_PENDING'
        reservation.returned_date = timezone.now()
        reservation.save()

        if reservation.equipment:
            form = ReturnForm(request.POST)
            if form.is_valid():
                reservation.return_condition = form.cleaned_data['return_condition']
                reservation.return_notes = form.cleaned_data.get('notes', '')
                reservation.save()
                ReservationItemReturn.objects.update_or_create(
                    reservation=reservation,
                    equipment=reservation.equipment,
                    defaults={
                        'condition': form.cleaned_data['return_condition'],
                        'notes': form.cleaned_data.get('notes', ''),
                    },
                )
        elif reservation.kit:
            reservation.return_condition = ''
            reservation.return_notes = ''
            reservation.save()
            for ki in reservation.kit.items.select_related('equipment'):
                eq = ki.equipment
                condition = request.POST.get(f'condition_{eq.pk}', 'GOOD')
                notes = request.POST.get(f'notes_{eq.pk}', '')
                ReservationItemReturn.objects.update_or_create(
                    reservation=reservation,
                    equipment=eq,
                    defaults={'condition': condition, 'notes': notes},
                )

        log_activity(
            actor=request.user,
            action='RESERVATION_RETURN_SUBMITTED',
            description=(
                f'{request.user.full_name or request.user.username} submitted return for reservation '
                f'#{reservation.pk} ({reservation.equipment or reservation.kit})'
            ),
            content_type_label='reservation',
            object_id=reservation.pk,
            object_repr=str(reservation),
            request=request,
        )

        # Notify the equipment owner(s).
        if reservation.equipment and reservation.equipment.owner and reservation.equipment.owner != request.user:
            notify(
                recipient=reservation.equipment.owner,
                title='Reservation Return Awaiting Confirmation',
                message=(
                    f'{request.user.full_name or request.user.username} has returned '
                    f'"{reservation.equipment.name}" from their reservation. '
                    f'Please confirm the return.'
                ),
                level='info',
                link=f'/reservations/{reservation.pk}/',
                category='reservations',
            )
        elif reservation.kit:
            kit_owners = {
                ki.equipment.owner
                for ki in reservation.kit.items.select_related('equipment__owner')
                if ki.equipment.owner and ki.equipment.owner != request.user
            }
            for owner in kit_owners:
                notify(
                    recipient=owner,
                    title='Reservation Return Awaiting Confirmation',
                    message=(
                        f'{request.user.full_name or request.user.username} has returned '
                        f'"{reservation.kit.name}" (includes your equipment) from their reservation. '
                        f'Please confirm the return.'
                    ),
                    level='info',
                    link=f'/reservations/{reservation.pk}/',
                    category='reservations',
                )

        messages.success(request, 'Return submitted. Waiting for owner confirmation.')
        return redirect('reservations:detail', pk=pk)
    else:
        form = ReturnForm()

    kit_item_returns = {}
    if reservation.kit:
        kit_item_returns = {
            ir.equipment_id: ir
            for ir in reservation.item_returns.all()
        }

    return render(request, 'reservations/reservation_return_form.html', {
        'form': form,
        'reservation': reservation,
        'kit_item_returns': kit_item_returns,
    })


@login_required
def reservation_return_confirm_view(request, pk):
    """Equipment/kit owner confirms the return of a reserved item."""
    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'requester', 'equipment', 'equipment__owner', 'equipment__location', 'kit'
        ).prefetch_related('kit__items__equipment__owner', 'kit__items__equipment__location', 'item_returns'),
        pk=pk,
    )

    if reservation.status not in ('RETURN_PENDING', 'ACTIVE', 'CONFIRMED'):
        messages.error(request, 'This reservation is not awaiting a return confirmation.')
        return redirect('reservations:detail', pk=pk)

    # Determine if the user is an owner of the reserved item.
    is_owner = False
    if reservation.equipment and request.user == reservation.equipment.owner:
        is_owner = True
    elif reservation.kit:
        kit_owner_pks = reservation.kit.items.values_list('equipment__owner', flat=True)
        if request.user.pk in kit_owner_pks:
            is_owner = True

    if not is_owner and not _is_admin(request.user):
        messages.error(request, 'Only the equipment owner can confirm this return.')
        return redirect('reservations:detail', pk=pk)

    if request.method == 'POST':
        if not is_owner:
            password = request.POST.get('password', '')
            if not authenticate(request, username=request.user.email, password=password):
                messages.error(request, 'Incorrect password. Admins must enter their password when confirming on behalf of another owner.')
                return redirect('reservations:return_confirm', pk=pk)

        if reservation.equipment:
            form = ReturnForm(request.POST)
            if form.is_valid():
                reservation.status = 'RETURNED'
                reservation.return_condition = form.cleaned_data['return_condition']
                reservation.return_notes = form.cleaned_data.get('notes', '')
                reservation.returned_date = timezone.now()
                reservation.return_approved_by = request.user
                reservation.return_approved_at = timezone.now()
                reservation.save()
                ReservationItemReturn.objects.update_or_create(
                    reservation=reservation,
                    equipment=reservation.equipment,
                    defaults={
                        'condition': form.cleaned_data['return_condition'],
                        'notes': form.cleaned_data.get('notes', ''),
                    },
                )
        elif reservation.kit:
            reservation.status = 'RETURNED'
            reservation.returned_date = timezone.now()
            reservation.return_approved_by = request.user
            reservation.return_approved_at = timezone.now()
            reservation.save()
            for ki in reservation.kit.items.select_related('equipment'):
                eq = ki.equipment
                condition = request.POST.get(f'condition_{eq.pk}', 'GOOD')
                notes = request.POST.get(f'notes_{eq.pk}', '')
                ReservationItemReturn.objects.update_or_create(
                    reservation=reservation,
                    equipment=eq,
                    defaults={'condition': condition, 'notes': notes},
                )

        if reservation.equipment:
            sync_equipment_status(reservation.equipment)
        if reservation.kit:
            for kit_item in reservation.kit.items.select_related('equipment'):
                sync_equipment_status(kit_item.equipment)

        notify(
            recipient=reservation.requester,
            title='Reservation Return Confirmed',
            message=(
                f'Your return of "{reservation.equipment or reservation.kit}" '
                f'has been confirmed. Thank you!'
            ),
            level='success',
            link=f'/reservations/{reservation.pk}/',
            category='reservations',
        )

        log_activity(
            actor=request.user,
            action='RESERVATION_RETURN_CONFIRMED',
            description=(
                f'{request.user.full_name or request.user.username} confirmed return for reservation '
                f'#{reservation.pk} ({reservation.equipment or reservation.kit})'
            ),
            content_type_label='reservation',
            object_id=reservation.pk,
            object_repr=str(reservation),
            request=request,
        )

        messages.success(request, 'Return confirmed.')
        return redirect('reservations:detail', pk=pk)
    else:
        form = ReturnForm(initial={
            'return_condition': reservation.return_condition or 'GOOD',
            'notes': reservation.return_notes,
        })

    kit_item_returns = {}
    if reservation.kit:
        kit_item_returns = {
            ir.equipment_id: ir
            for ir in reservation.item_returns.all()
        }

    return render(request, 'reservations/reservation_confirm_return.html', {
        'reservation': reservation,
        'form': form,
        'is_owner': is_owner,
        'kit_item_returns': kit_item_returns,
    })


@login_required
def waitlist_list_view(request):
    """List waitlist entries: admins see all; members see their own."""
    if _is_admin(request.user):
        entries = WaitlistEntry.objects.select_related('user', 'equipment', 'kit')
    else:
        entries = WaitlistEntry.objects.filter(
            user=request.user
        ).select_related('equipment', 'kit')

    return render(request, 'reservations/waitlist_list.html', {'entries': entries})


@login_required
def waitlist_create_view(request):
    """Add the current user to the waitlist for an equipment item or kit."""
    if request.method == 'POST':
        form = WaitlistEntryForm(request.POST)
        if form.is_valid():
            equipment = form.cleaned_data.get('equipment')
            kit = form.cleaned_data.get('kit')

            # Check for duplicate entry.
            existing_qs = WaitlistEntry.objects.filter(user=request.user)
            if equipment:
                existing_qs = existing_qs.filter(equipment=equipment)
            else:
                existing_qs = existing_qs.filter(kit=kit)

            if existing_qs.exists():
                messages.warning(request, 'You are already on the waitlist for this item.')
                return redirect('reservations:waitlist_list')

            # Determine next position.
            position_qs = WaitlistEntry.objects
            if equipment:
                position_qs = position_qs.filter(equipment=equipment)
            else:
                position_qs = position_qs.filter(kit=kit)

            next_position = position_qs.count() + 1

            entry = form.save(commit=False)
            entry.user = request.user
            entry.position = next_position
            entry.save()

            messages.success(
                request,
                f'You have been added to the waitlist at position {next_position}.'
            )
            return redirect('reservations:waitlist_list')
    else:
        # Pre-populate equipment/kit from GET params if provided.
        initial = {}
        equipment_id = request.GET.get('equipment_id')
        kit_id = request.GET.get('kit_id')
        if equipment_id:
            from apps.equipment.models import Equipment
            try:
                initial['equipment'] = Equipment.objects.get(pk=equipment_id)
            except Equipment.DoesNotExist:
                pass
        elif kit_id:
            from apps.kits.models import Kit
            try:
                initial['kit'] = Kit.objects.get(pk=kit_id)
            except Kit.DoesNotExist:
                pass
        form = WaitlistEntryForm(initial=initial)

    return render(request, 'reservations/waitlist_form.html', {'form': form})


@login_required
def waitlist_leave_view(request, pk):
    """Remove the current user (or any user if admin) from a waitlist entry."""
    entry = get_object_or_404(WaitlistEntry, pk=pk)

    if not _is_admin(request.user) and entry.user != request.user:
        messages.error(request, 'You do not have permission to remove this waitlist entry.')
        return redirect('reservations:waitlist_list')

    if request.method == 'POST':
        item_name = str(entry.equipment or entry.kit)
        entry.delete()
        messages.success(request, f'You have been removed from the waitlist for "{item_name}".')
        return redirect('reservations:waitlist_list')

    return render(request, 'reservations/waitlist_confirm_leave.html', {'entry': entry})


@login_required
def reservation_delete_view(request, pk):
    """Delete a reservation (admin or the requester only)."""
    reservation = get_object_or_404(
        Reservation.objects.select_related('requester', 'equipment', 'kit'),
        pk=pk,
    )

    if not _is_admin(request.user) and reservation.requester != request.user:
        messages.error(request, 'You do not have permission to delete this reservation.')
        return redirect('reservations:list')

    if request.method == 'POST':
        password = request.POST.get('password', '')
        if not authenticate(request, username=request.user.email, password=password):
            messages.error(request, 'Incorrect password. Please enter your current password to confirm deletion.')
            return redirect('reservations:delete', pk=pk)
        item_name = str(reservation.equipment or reservation.kit)
        equipment = reservation.equipment
        kit = reservation.kit
        requester = reservation.requester
        reservation.delete()

        # Recompute status now that this reservation is gone.
        if equipment:
            sync_equipment_status(equipment)
        if kit:
            for kit_item in kit.items.select_related('equipment'):
                sync_equipment_status(kit_item.equipment)

        log_activity(
            actor=request.user,
            action='RESERVATION_DELETED',
            description=f'{request.user.full_name or request.user.username} deleted reservation for {item_name}',
            content_type_label='reservation',
            object_id=pk,
            object_repr=item_name,
            request=request,
        )

        if requester:
            notify(
                recipient=requester,
                title='Reservation Deleted',
                message=f'Your reservation for "{item_name}" has been deleted.',
                level='warning',
                link=reverse('reservations:list'),
                category='reservations',
            )
        notify_admins(
            title='Reservation Deleted',
            message=f'Reservation for "{item_name}" by {requester.full_name if requester else "unknown"} was deleted.',
            level='warning',
            link=reverse('reservations:list'),
            category='reservations',
        )

        messages.success(request, f'Reservation for "{item_name}" has been deleted.')
        return redirect('reservations:list')

    return render(request, 'reservations/reservation_confirm_delete.html', {
        'reservation': reservation,
    })


@login_required
def reservation_remind_view(request, pk):
    """Send a reminder notification to the equipment/kit owner about a pending return."""
    reservation = get_object_or_404(
        Reservation.objects.select_related('requester', 'equipment', 'kit'),
        pk=pk,
    )

    if reservation.status != 'RETURN_PENDING':
        messages.error(request, 'This reservation is not awaiting a return confirmation.')
        return redirect('reservations:detail', pk=pk)

    # For kits, send reminders to all individual equipment owners
    if reservation.equipment and reservation.equipment.owner:
        owners = [reservation.equipment.owner]
    elif reservation.kit:
        owners = list({
            ki.equipment.owner
            for ki in reservation.kit.items.select_related('equipment__owner')
            if ki.equipment.owner
        })
    else:
        owners = []

    if not owners:
        messages.error(request, 'No owner is assigned to this item.')
        return redirect('reservations:detail', pk=pk)

    if request.method == 'POST':
        item_name = str(reservation.equipment or reservation.kit)
        for owner in owners:
            notify(
                recipient=owner,
                title='Return Approval Reminder',
                message=(
                    f'{request.user.full_name or request.user.username} is reminding you to confirm '
                    f'the return of "{item_name}" from reservation #{reservation.pk}.'
                ),
                level='warning',
                link=f'/reservations/{reservation.pk}/',
                category='reservations',
            )
        owner_names = ', '.join([o.full_name or o.username for o in owners])
        messages.success(request, f'Reminder sent to {owner_names}.')
        return redirect('reservations:detail', pk=pk)

    return redirect('reservations:detail', pk=pk)


@login_required
def reservation_remind_owner_view(request, pk, owner_pk):
    """Send a return-confirmation reminder to a single specific owner."""
    from apps.accounts.models import CustomUser
    reservation = get_object_or_404(
        Reservation.objects.select_related('requester', 'equipment', 'kit'),
        pk=pk,
    )

    if reservation.status != 'RETURN_PENDING':
        messages.error(request, 'This reservation is not awaiting a return confirmation.')
        return redirect('reservations:detail', pk=pk)

    if reservation.requester != request.user and not _is_admin(request.user):
        messages.error(request, 'You do not have permission to send this reminder.')
        return redirect('reservations:detail', pk=pk)

    owner = get_object_or_404(CustomUser, pk=owner_pk)

    # Verify the owner actually owns something in this reservation.
    if reservation.equipment:
        if reservation.equipment.owner_id != owner_pk:
            messages.error(request, 'This person is not the owner of that equipment.')
            return redirect('reservations:detail', pk=pk)
    elif reservation.kit:
        owns_something = reservation.kit.items.filter(
            equipment__owner_id=owner_pk
        ).exists()
        if not owns_something:
            messages.error(request, 'This person does not own any item in this kit.')
            return redirect('reservations:detail', pk=pk)

    if request.method == 'POST':
        item_name = str(reservation.equipment or reservation.kit)
        notify(
            recipient=owner,
            title='Return Approval Reminder',
            message=(
                f'{request.user.full_name or request.user.username} is reminding you to confirm '
                f'the return of "{item_name}" from reservation #{reservation.pk}.'
            ),
            level='warning',
            link=f'/reservations/{reservation.pk}/',
            category='reservations',
        )
        messages.success(request, f'Reminder sent to {owner.full_name or owner.username}.')
        return redirect('reservations:detail', pk=pk)

    return redirect('reservations:detail', pk=pk)
