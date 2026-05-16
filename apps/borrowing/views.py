"""Views for the borrowing app."""

from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.activity.utils import log_activity
from apps.borrowing.forms import BorrowRequestForm, BulkBorrowForm, ReturnForm
from apps.borrowing.models import BorrowRequest, KitItemReturnApproval
from apps.equipment.models import Equipment
from apps.equipment.utils import sync_equipment_status
from apps.notifications.utils import notify, notify_admins
from apps.reservations.models import WaitlistEntry


def _is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@login_required
def borrow_list_view(request):
    """Paginated list of borrow requests.

    Members see only their own; admins see all. Supports ?status= filter.
    """
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '').strip()

    if _is_admin(request.user):
        qs = BorrowRequest.objects.select_related(
            'borrower', 'equipment', 'kit', 'approved_by'
        )
    else:
        qs = BorrowRequest.objects.filter(borrower=request.user).select_related(
            'equipment', 'kit', 'approved_by'
        )

    pending_count = qs.filter(status='RETURN_PENDING').count()
    overdue_count = qs.filter(
        status__in=['APPROVED', 'ACTIVE'], due_date__lt=date.today()
    ).count()
    total_count = qs.count()

    if status_filter:
        qs = qs.filter(status=status_filter)

    if search:
        from django.db.models import Q as _Q
        sq = (
            _Q(equipment__name__icontains=search)
            | _Q(kit__name__icontains=search)
            | _Q(borrower__first_name__icontains=search)
            | _Q(borrower__last_name__icontains=search)
            | _Q(purpose__icontains=search)
        )
        if search.isdigit():
            sq |= _Q(pk=int(search))
        qs = qs.filter(sq)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'borrowing/borrow_list.html', {
        'page_obj': page_obj,
        'borrow_list': page_obj,
        'status_filter': status_filter,
        'search': search,
        'status_choices': BorrowRequest.STATUS_CHOICES,
        'pending_count': pending_count,
        'overdue_count': overdue_count,
        'total_count': total_count,
    })


# ---------------------------------------------------------------------------
# Create (single)
# ---------------------------------------------------------------------------

@login_required
def borrow_request_create_view(request):
    """Create a borrow request — auto-approved immediately, no admin sign-off needed."""
    initial = {}
    equipment_id = request.GET.get('equipment_id') or request.GET.get('equipment')
    if equipment_id:
        try:
            initial['equipment'] = Equipment.objects.get(pk=equipment_id, is_active=True)
        except Equipment.DoesNotExist:
            pass
    kit_id = request.GET.get('kit_id') or request.GET.get('kit')
    if kit_id:
        from apps.kits.models import Kit
        try:
            initial['kit'] = Kit.objects.get(pk=kit_id, is_active=True)
        except Kit.DoesNotExist:
            pass

    if request.method == 'POST':
        form = BorrowRequestForm(request.POST)
        if form.is_valid():
            borrow = form.save(commit=False)
            borrow.borrower = request.user
            borrow.status = 'APPROVED'
            borrow.approved_by = None
            borrow.save()

            # Mark the item as BORROWED immediately.
            if borrow.equipment:
                borrow.equipment.status = 'BORROWED'
                borrow.equipment.save(update_fields=['status'])
            if borrow.kit:
                for kit_item in borrow.kit.items.select_related('equipment'):
                    kit_item.equipment.status = 'BORROWED'
                    kit_item.equipment.save(update_fields=['status'])

            messages.success(request, f'You are now borrowing {borrow.item}. Due back by {borrow.due_date}.')
            return redirect('borrowing:detail', pk=borrow.pk)
    else:
        form = BorrowRequestForm(initial=initial)

    return render(request, 'borrowing/borrow_request_form.html', {'form': form})


# ---------------------------------------------------------------------------
# Bulk create
# ---------------------------------------------------------------------------

@login_required
def borrow_bulk_create_view(request):
    """Borrow multiple equipment items at once."""
    if request.method == 'POST':
        equipment_ids = request.POST.getlist('equipment_ids')
        if not equipment_ids:
            messages.error(request, 'No items selected.')
            return redirect('equipment:list')

        form = BulkBorrowForm(request.POST)
        if form.is_valid():
            purpose = form.cleaned_data['purpose']
            due_date = form.cleaned_data['due_date']

            with transaction.atomic():
                items = Equipment.objects.select_for_update().filter(
                    pk__in=equipment_ids, is_active=True, status='AVAILABLE'
                )
                if not items.exists():
                    messages.error(request, 'None of the selected items are available.')
                    return redirect('equipment:list')

                created = []
                for item in items:
                    # Skip items with overlapping reservations
                    from apps.reservations.models import Reservation
                    overlap = Reservation.objects.filter(
                        status='CONFIRMED',
                        equipment=item,
                        start_date__lte=due_date,
                        end_date__gte=timezone.now().date(),
                    ).exists()
                    if overlap:
                        continue

                    borrow = BorrowRequest.objects.create(
                        borrower=request.user,
                        equipment=item,
                        purpose=purpose,
                        due_date=due_date,
                        status='APPROVED',
                    )
                    item.status = 'BORROWED'
                    item.save(update_fields=['status'])
                    created.append(item.name)

                if not created:
                    messages.error(request, 'All selected items have overlapping reservations.')
                    return redirect('equipment:list')

            messages.success(
                request,
                f'Borrowed {len(created)} item(s): {", ".join(created)}. Due back by {due_date}.'
            )
            notify(
                recipient=request.user,
                title='Items Borrowed',
                message=f'You have borrowed {len(created)} item(s). Due back by {due_date}.',
                level='success',
                link=reverse('borrowing:list'),
                category='borrowing',
            )
            notify_admins(
                title='Bulk Borrow Created',
                message=f'{request.user.full_name or request.user.username} borrowed {len(created)} item(s).',
                level='info',
                link=reverse('borrowing:list'),
                category='borrowing',
            )
            return redirect('borrowing:list')

        # Form invalid — re-show confirmation page with errors
        items = Equipment.objects.filter(
            pk__in=equipment_ids, is_active=True, status='AVAILABLE'
        )
        return render(request, 'borrowing/borrow_bulk_form.html', {
            'form': form,
            'items': items,
            'equipment_ids': equipment_ids,
        })

    else:
        equipment_ids = request.GET.getlist('ids')
        if not equipment_ids:
            messages.error(request, 'No items selected.')
            return redirect('equipment:list')

        items = Equipment.objects.filter(
            pk__in=equipment_ids, is_active=True, status='AVAILABLE'
        )
        unavailable = Equipment.objects.filter(
            pk__in=equipment_ids
        ).exclude(is_active=True, status='AVAILABLE')

        form = BulkBorrowForm()
        return render(request, 'borrowing/borrow_bulk_form.html', {
            'form': form,
            'items': items,
            'unavailable': unavailable,
            'equipment_ids': equipment_ids,
        })


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

@login_required
def borrow_detail_view(request, pk):
    """Show full details of a single borrow request."""
    borrow = get_object_or_404(
        BorrowRequest.objects.select_related(
            'borrower', 'equipment', 'kit', 'approved_by'
        ),
        pk=pk,
    )

    if not _is_admin(request.user) and borrow.borrower != request.user:
        messages.error(request, 'You do not have permission to view this request.')
        return redirect('borrowing:list')

    return render(request, 'borrowing/borrow_detail.html', {'borrow': borrow})


# ---------------------------------------------------------------------------
# Return (borrower submits) → Return confirm (admin approves)
# ---------------------------------------------------------------------------

@login_required
def borrow_return_view(request, pk):
    """Borrower submits the return form — status goes to RETURN_PENDING for admin confirmation."""
    borrow = get_object_or_404(
        BorrowRequest.objects.select_related('borrower', 'equipment', 'kit'),
        pk=pk,
    )

    # Only the original borrower can submit a return.
    if borrow.borrower != request.user:
        messages.error(request, 'Only the borrower can submit a return.')
        return redirect('borrowing:list')

    if borrow.status not in ('APPROVED', 'ACTIVE'):
        messages.error(request, 'This borrow request cannot be returned in its current state.')
        return redirect('borrowing:detail', pk=borrow.pk)

    if request.method == 'POST':
        form = ReturnForm(request.POST)
        if form.is_valid():
            borrow.status = 'RETURN_PENDING'
            borrow.returned_date = timezone.now()
            borrow.return_condition = form.cleaned_data['return_condition']
            borrow.notes = form.cleaned_data.get('notes', '')
            borrow.save()

            log_activity(
                actor=request.user,
                action='BORROW_RETURN_SUBMITTED',
                description=(
                    f'{request.user.username} submitted return for {borrow.item} '
                    f'(condition: {borrow.return_condition})'
                ),
                content_type_label='borrowrequest',
                object_id=borrow.pk,
                object_repr=str(borrow),
                request=request,
            )

            if borrow.equipment:
                # Single equipment — notify owner to confirm.
                owner = borrow.equipment.owner
                if owner and owner != request.user:
                    notify(
                        recipient=owner,
                        title='Return Awaiting Your Confirmation',
                        message=(
                            f'{request.user.full_name or request.user.username} has returned '
                            f'"{borrow.item}". Please confirm the return.'
                        ),
                        level='info',
                        link=reverse('borrowing:return_queue'),
                        category='borrowing',
                    )
            elif borrow.kit:
                # Kit — create per-owner approval records and notify each distinct owner.
                notified_owners = set()
                for kit_item in borrow.kit.items.select_related('equipment__owner'):
                    owner = kit_item.equipment.owner
                    if not owner:
                        continue
                    KitItemReturnApproval.objects.get_or_create(
                        borrow_request=borrow,
                        equipment=kit_item.equipment,
                        defaults={'owner': owner},
                    )
                    if owner.pk not in notified_owners and owner != request.user:
                        notify(
                            recipient=owner,
                            title='Kit Return Awaiting Your Confirmation',
                            message=(
                                f'{request.user.full_name or request.user.username} has returned '
                                f'kit "{borrow.kit}". Please confirm your items.'
                            ),
                            level='info',
                            link=reverse('borrowing:return_queue'),
                            category='borrowing',
                        )
                        notified_owners.add(owner.pk)

            messages.success(request, 'Return submitted. Waiting for owner confirmation.')
            return redirect('borrowing:detail', pk=borrow.pk)
    else:
        form = ReturnForm()

    return render(request, 'borrowing/borrow_return_form.html', {
        'form': form,
        'borrow': borrow,
    })


@login_required
def borrow_return_confirm_view(request, pk):
    """Equipment owner confirms a pending return for a single-equipment borrow."""
    borrow = get_object_or_404(
        BorrowRequest.objects.select_related('borrower', 'equipment', 'kit'),
        pk=pk,
        status='RETURN_PENDING',
    )

    if not borrow.equipment:
        messages.error(request, 'Use the kit item confirmation page for kit returns.')
        return redirect('borrowing:detail', pk=borrow.pk)

    if request.user != borrow.equipment.owner:
        messages.error(request, 'Only the equipment owner can confirm this return.')
        return redirect('borrowing:detail', pk=borrow.pk)

    if request.method == 'POST':
        borrow.status = 'RETURNED'
        borrow.save()

        sync_equipment_status(borrow.equipment)

        notify(
            recipient=borrow.borrower,
            title='Return Confirmed',
            message=f'Your return of {borrow.item} has been confirmed. Thank you!',
            level='success',
            link=reverse('borrowing:detail', args=[borrow.pk]),
            category='borrowing',
        )

        waitlist_qs = WaitlistEntry.objects.filter(
            equipment=borrow.equipment, notified=False
        ).order_by('position', 'created_at')
        next_entry = waitlist_qs.first()
        if next_entry:
            notify(
                recipient=next_entry.user,
                title='Item Now Available',
                message=f'{borrow.item} is now available. You are next on the waitlist!',
                level='success',
                link=reverse('borrowing:create'),
                category='borrowing',
            )
            next_entry.notified = True
            next_entry.save(update_fields=['notified'])

        log_activity(
            actor=request.user,
            action='BORROW_RETURNED',
            description=f'{request.user.username} confirmed return of {borrow.item}',
            content_type_label='borrowrequest',
            object_id=borrow.pk,
            object_repr=str(borrow),
            request=request,
        )

        messages.success(request, f'Return of {borrow.item} confirmed.')
        return redirect('borrowing:detail', pk=borrow.pk)

    return render(request, 'borrowing/borrow_confirm_return.html', {'borrow': borrow})


@login_required
def kit_item_return_confirm_view(request, approval_pk):
    """Equipment owner confirms their item within a kit return.

    When all items in the kit are confirmed, the borrow is marked RETURNED
    and all equipment freed.
    """
    approval = get_object_or_404(
        KitItemReturnApproval.objects.select_related(
            'borrow_request__borrower', 'borrow_request__kit', 'equipment', 'owner'
        ),
        pk=approval_pk,
    )

    if request.user != approval.owner:
        messages.error(request, 'Only the equipment owner can confirm this item.')
        return redirect('borrowing:detail', pk=approval.borrow_request.pk)

    if approval.is_confirmed:
        messages.info(request, 'You have already confirmed this item.')
        return redirect('borrowing:detail', pk=approval.borrow_request.pk)

    borrow = approval.borrow_request
    if borrow.status != 'RETURN_PENDING':
        messages.error(request, 'This return is no longer pending.')
        return redirect('borrowing:detail', pk=borrow.pk)

    if request.method == 'POST':
        from django.utils import timezone as tz
        approval.confirmed_by = request.user
        approval.confirmed_at = tz.now()
        approval.save()

        # Free this individual item. The parent borrow is still RETURN_PENDING,
        # so we exclude it from the active-borrow check.
        sync_equipment_status(approval.equipment, exclude_borrow_pk=borrow.pk)

        log_activity(
            actor=request.user,
            action='BORROW_RETURNED',
            description=(
                f'{request.user.username} confirmed return of '
                f'"{approval.equipment.name}" from kit "{borrow.kit}"'
            ),
            content_type_label='borrowrequest',
            object_id=borrow.pk,
            object_repr=str(borrow),
            request=request,
        )

        # Check if all items are now confirmed.
        all_confirmed = not borrow.kit_item_approvals.filter(confirmed_by__isnull=True).exists()
        if all_confirmed:
            borrow.status = 'RETURNED'
            borrow.save()

            notify(
                recipient=borrow.borrower,
                title='Kit Return Confirmed',
                message=f'Your return of kit "{borrow.kit}" has been fully confirmed. Thank you!',
                level='success',
                link=reverse('borrowing:detail', args=[borrow.pk]),
                category='borrowing',
            )

            # Notify next on waitlist.
            next_entry = WaitlistEntry.objects.filter(
                kit=borrow.kit, notified=False
            ).order_by('position', 'created_at').first()
            if next_entry:
                notify(
                    recipient=next_entry.user,
                    title='Kit Now Available',
                    message=f'Kit "{borrow.kit}" is now available. You are next on the waitlist!',
                    level='success',
                    link=reverse('kits:detail', args=[borrow.kit.pk]),
                    category='borrowing',
                )
                next_entry.notified = True
                next_entry.save(update_fields=['notified'])

            messages.success(request, f'All items confirmed. Kit "{borrow.kit}" return completed.')
        else:
            remaining = borrow.kit_item_approvals.filter(confirmed_by__isnull=True).count()
            messages.success(
                request,
                f'"{approval.equipment.name}" confirmed. {remaining} item(s) still awaiting confirmation.'
            )

        return redirect('borrowing:detail', pk=borrow.pk)

    return render(request, 'borrowing/kit_item_return_confirm.html', {
        'approval': approval,
        'borrow': borrow,
    })


# ---------------------------------------------------------------------------
# Overdue & Return queue
# ---------------------------------------------------------------------------

@login_required
def overdue_list_view(request):
    """Admin only: list borrow requests that are overdue."""
    if not _is_admin(request.user):
        messages.error(request, 'Only admins can view the overdue list.')
        return redirect('borrowing:list')

    qs = BorrowRequest.objects.filter(
        due_date__lt=date.today(),
        status__in=['APPROVED', 'ACTIVE'],
    ).select_related('borrower', 'equipment', 'kit').order_by('due_date')

    paginator = Paginator(qs, 20)
    overdue_borrows = paginator.get_page(request.GET.get('page'))

    return render(request, 'borrowing/overdue_list.html', {
        'overdue_borrows': overdue_borrows,
    })


@login_required
def return_queue_view(request):
    """List pending returns and active borrows the current user can act on as equipment owner."""
    # Single-equipment returns owned by this user (borrower submitted return)
    equipment_returns = BorrowRequest.objects.filter(
        status='RETURN_PENDING',
        equipment__owner=request.user,
    ).select_related('borrower', 'equipment').order_by('returned_date')

    # Kit item approvals assigned to this user
    kit_approvals = KitItemReturnApproval.objects.filter(
        owner=request.user,
        confirmed_by__isnull=True,
        borrow_request__status='RETURN_PENDING',
    ).select_related('borrow_request__borrower', 'borrow_request__kit', 'equipment')

    # Active borrows of this user's equipment (owner can reclaim without waiting for borrower)
    active_owned_borrows = BorrowRequest.objects.filter(
        status__in=['APPROVED', 'ACTIVE'],
        equipment__owner=request.user,
    ).select_related('borrower', 'equipment').order_by('due_date')

    return render(request, 'borrowing/return_queue.html', {
        'equipment_returns': equipment_returns,
        'kit_approvals': kit_approvals,
        'active_owned_borrows': active_owned_borrows,
    })


@login_required
def borrow_owner_reclaim_view(request, pk):
    """Equipment owner reclaims their equipment without requiring the borrower to initiate a return."""
    borrow = get_object_or_404(
        BorrowRequest.objects.select_related('borrower', 'equipment'),
        pk=pk,
    )

    if not borrow.equipment or request.user != borrow.equipment.owner:
        messages.error(request, 'Only the equipment owner can reclaim it.')
        return redirect('borrowing:detail', pk=pk)

    if borrow.status not in ('APPROVED', 'ACTIVE', 'RETURN_PENDING'):
        messages.error(request, 'This item cannot be reclaimed in its current state.')
        return redirect('borrowing:detail', pk=pk)

    if request.method == 'POST':
        borrow.status = 'RETURNED'
        borrow.returned_date = timezone.now()
        borrow.save()

        sync_equipment_status(borrow.equipment)

        notify(
            recipient=borrow.borrower,
            title='Equipment Reclaimed by Owner',
            message=(
                f'"{borrow.equipment.name}" has been reclaimed by '
                f'{request.user.full_name or request.user.username}.'
            ),
            level='warning',
            link=reverse('borrowing:detail', args=[borrow.pk]),
            category='borrowing',
        )

        log_activity(
            actor=request.user,
            action='BORROW_RETURNED',
            description=(
                f'{request.user.username} reclaimed "{borrow.equipment.name}" '
                f'from {borrow.borrower.username}'
            ),
            content_type_label='borrowrequest',
            object_id=borrow.pk,
            object_repr=str(borrow),
            request=request,
        )

        messages.success(request, f'"{borrow.equipment.name}" has been reclaimed.')
        return redirect('borrowing:detail', pk=pk)

    return render(request, 'borrowing/borrow_confirm_reclaim.html', {'borrow': borrow})


@login_required
def borrow_request_delete_view(request, pk):
    """Delete a borrow request (admin or the borrower only)."""
    borrow = get_object_or_404(
        BorrowRequest.objects.select_related('borrower', 'equipment', 'kit'),
        pk=pk,
    )

    if not _is_admin(request.user) and borrow.borrower != request.user:
        messages.error(request, 'You do not have permission to delete this borrow request.')
        return redirect('borrowing:list')

    if request.method == 'POST':
        item_name = str(borrow.item)
        equipment = borrow.equipment
        kit = borrow.kit
        # Clean up any pending kit item return approvals
        borrow.kit_item_approvals.all().delete()
        borrow.delete()

        # Recompute status now that the borrow is gone.
        if equipment:
            sync_equipment_status(equipment)
        if kit:
            for kit_item in kit.items.select_related('equipment'):
                sync_equipment_status(kit_item.equipment)
        log_activity(
            actor=request.user,
            action='BORROW_DELETED',
            description=f'{request.user.username} deleted borrow request for {item_name}',
            content_type_label='borrowrequest',
            object_id=pk,
            object_repr=item_name,
            request=request,
        )

        borrower = borrow.borrower
        if borrower:
            notify(
                recipient=borrower,
                title='Borrow Request Deleted',
                message=f'Your borrow request for "{item_name}" has been deleted.',
                level='warning',
                link=reverse('borrowing:list'),
                category='borrowing',
            )
        notify_admins(
            title='Borrow Request Deleted',
            message=f'Borrow request for "{item_name}" by {borrow.borrower.full_name if borrow.borrower else "unknown"} was deleted.',
            level='warning',
            link=reverse('borrowing:list'),
            category='borrowing',
        )

        messages.success(request, f'Borrow request for "{item_name}" has been deleted.')
        return redirect('borrowing:list')

    return render(request, 'borrowing/borrow_confirm_delete.html', {'borrow': borrow})
