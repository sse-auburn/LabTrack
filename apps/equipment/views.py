"""Views for the equipment app."""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.decorators import admin_required
from apps.activity.utils import log_activity
from apps.equipment.forms import (
    CategoryForm,
    EquipmentFilterForm,
    EquipmentForm,
    LifecycleEventForm,
    LocationForm,
    MovementLogForm,
)
from apps.equipment.models import Category, Equipment, LifecycleEvent, Location, MovementLog
from apps.notifications.utils import notify, notify_admins


# ---------------------------------------------------------------------------
# Equipment CRUD views
# ---------------------------------------------------------------------------

@login_required
def equipment_list_view(request):
    """
    List all active equipment with optional filtering by category, location,
    status, condition, and a free-text search query.
    
    Regular users see only APPROVED equipment. Creators can see their own
    PENDING equipment. Admins can see all PENDING equipment.
    """
    user = request.user
    is_admin = user.role == 'ADMIN'

    base_qs = Equipment.objects.select_related('category', 'location', 'owner').filter(is_active=True)

    # Visibility rules: approved for everyone, pending only for creator or admin
    if is_admin:
        queryset = base_qs
    else:
        queryset = base_qs.filter(
            Q(approval_status='APPROVED') | Q(created_by=user)
        )

    search = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    location_id = request.GET.get('location', '').strip()
    status = request.GET.get('status', '').strip()
    condition = request.GET.get('condition', '').strip()

    if search:
        q_filter = (
            Q(name__icontains=search)
            | Q(serial_number__icontains=search)
            | Q(model_number__icontains=search)
            | Q(manufacturer__icontains=search)
            | Q(description__icontains=search)
        )
        if search.isdigit():
            q_filter |= Q(pk=int(search))
        queryset = queryset.filter(q_filter)
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if location_id:
        queryset = queryset.filter(location_id=location_id)
    if status:
        queryset = queryset.filter(status=status)
    if condition:
        queryset = queryset.filter(condition=condition)

    queryset = queryset.order_by('name')

    view_mode = request.GET.get('view', 'list')
    per_page = 12 if view_mode == 'grid' else 20

    total_count = queryset.count()
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Query string without 'page' so pagination links can append &page=N cleanly
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_string = query_params.urlencode()

    return render(request, 'equipment/equipment_list.html', {
        'page_obj': page_obj,
        'equipment_list': page_obj,
        'total_count': total_count,
        'categories': Category.objects.all().order_by('name'),
        'locations': Location.objects.all().order_by('name'),
        'view_mode': view_mode,
        'query_string': query_string,
    })


@login_required
def equipment_detail_view(request, pk):
    """Show full details for a single piece of equipment."""
    equipment = get_object_or_404(
        Equipment.objects.select_related('category', 'location', 'owner', 'created_by'),
        pk=pk,
    )

    # Visibility check for pending equipment
    user = request.user
    is_admin = user.role == 'ADMIN'
    can_view_pending = (
        is_admin
        or equipment.created_by == user
        or equipment.owner == user
    )
    if equipment.approval_status == 'PENDING' and not can_view_pending:
        messages.error(request, 'This equipment is awaiting approval and is not yet visible.')
        return redirect('equipment:list')

    # Reservation history for this equipment (direct or via kit)
    from apps.reservations.models import Reservation
    from django.db.models import Q
    reservation_history = Reservation.objects.filter(
        Q(equipment=equipment) | Q(kit__items__equipment=equipment)
    ).select_related('requester').order_by('-start_date')[:10]

    # Lifecycle timeline (latest first)
    lifecycle_events = equipment.lifecycle_events.select_related('performed_by').order_by('-timestamp')[:10]

    # Movement logs (latest first)
    movement_logs = equipment.movement_logs.select_related(
        'from_location', 'to_location', 'moved_by'
    ).order_by('-timestamp')[:10]

    # Incident reports and maintenance logs
    incidents = equipment.incidents.select_related('reported_by').order_by('-created_at')[:10]
    maintenance_logs = equipment.maintenance_logs.select_related('performed_by').order_by('-created_at')[:10]

    # Form for adding a lifecycle note inline
    lifecycle_form = LifecycleEventForm(initial={'equipment': equipment})

    # Calendar events (reservations only)
    cal_events = []
    for r in Reservation.objects.filter(
        Q(equipment=equipment) | Q(kit__items__equipment=equipment),
        status__in=['PENDING', 'CONFIRMED', 'ACTIVE', 'RETURN_PENDING'],
    ).select_related('requester'):
        cal_events.append({
            'start': r.start_date.isoformat(),
            'end': r.end_date.isoformat(),
            'type': 'reservation',
            'status': r.status,
            'label': r.requester.full_name if r.requester else '',
        })

    return render(request, 'equipment/equipment_detail.html', {
        'equipment': equipment,
        'reservation_history': reservation_history,
        'lifecycle_events': lifecycle_events,
        'movement_logs': movement_logs,
        'incidents': incidents,
        'maintenance_logs': maintenance_logs,
        'lifecycle_form': lifecycle_form,
        'can_approve': (is_admin or request.user == equipment.owner) and equipment.approval_status == 'PENDING',
        'calendar_events_json': json.dumps(cal_events),
    })


@login_required
def equipment_create_view(request):
    """Create a new piece of equipment."""
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.created_by = request.user

            # Approval logic
            if equipment.owner == request.user:
                equipment.approval_status = 'APPROVED'
                equipment.approved_by = request.user
                equipment.approved_at = timezone.now()
            else:
                equipment.approval_status = 'PENDING'

            equipment.save()

            # Record a PURCHASED lifecycle event automatically
            LifecycleEvent.objects.create(
                equipment=equipment,
                event_type='PURCHASED',
                description=f'Equipment "{equipment.name}" added to inventory by {request.user.full_name}.',
                performed_by=request.user,
            )

            log_activity(
                actor=request.user,
                action='EQUIPMENT_CREATED',
                description=f'Equipment "{equipment.name}" was added to the inventory.',
                content_type_label='equipment',
                object_id=equipment.pk,
                object_repr=str(equipment),
                request=request,
            )

            if equipment.approval_status == 'PENDING':
                if equipment.owner:
                    notify(
                        recipient=equipment.owner,
                        title='Equipment Assigned — Your Approval Required',
                        message=(
                            f'"{equipment.name}" has been assigned to you by {request.user.full_name}. '
                            f'Please review and approve or reject it.'
                        ),
                        level='warning',
                        link=f'/equipment/pending/',
                        category='equipment',
                    )
                messages.success(
                    request,
                    f'Equipment "{equipment.name}" has been submitted and is awaiting approval from the assigned owner.'
                )
            else:
                notify_admins(
                    title='Equipment Created',
                    message=f'Equipment "{equipment.name}" was added to the inventory by {request.user.full_name}.',
                    level='info',
                    link=f'/equipment/{equipment.pk}/',
                    category='equipment',
                )
                messages.success(request, f'Equipment "{equipment.name}" has been added successfully.')

            return redirect('equipment:detail', pk=equipment.pk)
    else:
        form = EquipmentForm()

    return render(request, 'equipment/equipment_form.html', {
        'form': form,
        'action': 'Create',
    })


@login_required
def equipment_edit_view(request, pk):
    """
    Edit an existing piece of equipment.
    Only the owner, creator, or an admin may edit.
    """
    equipment = get_object_or_404(Equipment, pk=pk)

    # Permission check: owner, creator, or admin
    if request.user not in (equipment.owner, equipment.created_by) and request.user.role != 'ADMIN':
        messages.error(request, 'You do not have permission to edit this equipment.')
        return redirect('equipment:detail', pk=pk)

    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=equipment)
        if form.is_valid():
            updated = form.save(commit=False)
            original_owner = equipment.owner

            # Re-approval required if owner changed to someone else
            if updated.owner != original_owner and updated.owner != request.user:
                updated.approval_status = 'PENDING'
                updated.approved_by = None
                updated.approved_at = None
            elif request.user.role == 'ADMIN' and updated.approval_status == 'PENDING':
                # Admin can auto-approve during edit
                updated.approval_status = 'APPROVED'
                updated.approved_by = request.user
                updated.approved_at = timezone.now()

            updated.save()

            log_activity(
                actor=request.user,
                action='EQUIPMENT_UPDATED',
                description=f'Equipment "{equipment.name}" was updated by {request.user.full_name}.',
                content_type_label='equipment',
                object_id=equipment.pk,
                object_repr=str(equipment),
                request=request,
            )

            notify_admins(
                title='Equipment Updated',
                message=f'Equipment "{equipment.name}" was updated by {request.user.full_name}.',
                level='info',
                link=f'/equipment/{equipment.pk}/',
                category='equipment',
            )

            messages.success(request, f'Equipment "{equipment.name}" has been updated.')
            return redirect('equipment:detail', pk=pk)
    else:
        form = EquipmentForm(instance=equipment)

    return render(request, 'equipment/equipment_form.html', {
        'form': form,
        'equipment': equipment,
        'action': 'Edit',
    })


@login_required
def equipment_delete_view(request, pk):
    """Soft-delete (deactivate) a piece of equipment. Owner, creator, or admin only."""
    equipment = get_object_or_404(Equipment, pk=pk)

    if request.user not in (equipment.owner, equipment.created_by) and request.user.role != 'ADMIN':
        messages.error(request, 'Only the equipment owner, creator, or an admin can delete it.')
        return redirect('equipment:detail', pk=pk)

    if request.method == 'POST':
        equipment_name = equipment.name
        equipment.is_active = False
        equipment.status = 'RETIRED'
        equipment.save(update_fields=['is_active', 'status'])

        log_activity(
            actor=request.user,
            action='EQUIPMENT_DELETED',
            description=f'Equipment "{equipment_name}" was retired/deleted by {request.user.full_name}.',
            content_type_label='equipment',
            object_id=equipment.pk,
            object_repr=equipment_name,
            request=request,
        )

        notify_admins(
            title='Equipment Retired',
            message=f'Equipment "{equipment_name}" was retired/deleted by {request.user.full_name}.',
            level='warning',
            link='/equipment/',
            category='equipment',
        )

        messages.success(request, f'Equipment "{equipment_name}" has been retired.')
        return redirect('equipment:list')

    return render(request, 'equipment/equipment_confirm_delete.html', {
        'equipment': equipment,
    })


@login_required
@admin_required
def equipment_bulk_delete_view(request):
    """Soft-delete (deactivate) multiple equipment items at once. Admin only."""
    if request.method == 'POST':
        equipment_ids = request.POST.getlist('equipment_ids')
        if not equipment_ids:
            messages.error(request, 'No items selected.')
            return redirect('equipment:list')

        items = Equipment.objects.filter(pk__in=equipment_ids, is_active=True)
        if not items.exists():
            messages.error(request, 'None of the selected items were found.')
            return redirect('equipment:list')

        count = 0
        for item in items:
            item.is_active = False
            item.status = 'RETIRED'
            item.save(update_fields=['is_active', 'status'])
            log_activity(
                actor=request.user,
                action='EQUIPMENT_DELETED',
                description=f'Equipment "{item.name}" was retired/deleted by {request.user.full_name}.',
                content_type_label='equipment',
                object_id=item.pk,
                object_repr=item.name,
                request=request,
            )
            count += 1

        notify_admins(
            title='Equipment Bulk Retired',
            message=f'{request.user.full_name} retired {count} equipment item(s).',
            level='warning',
            link='/equipment/',
            category='equipment',
        )
        messages.success(request, f'{count} equipment item(s) have been retired.')
        return redirect('equipment:list')

    else:
        equipment_ids = request.GET.getlist('ids')
        if not equipment_ids:
            messages.error(request, 'No items selected.')
            return redirect('equipment:list')

        items = Equipment.objects.filter(pk__in=equipment_ids, is_active=True)
        return render(request, 'equipment/equipment_bulk_delete.html', {
            'items': items,
            'equipment_ids': equipment_ids,
        })


# ---------------------------------------------------------------------------
# Equipment approval views
# ---------------------------------------------------------------------------

@login_required
def equipment_pending_list_view(request):
    """List equipment pending approval. Admins see all; owners see equipment assigned to them."""
    user = request.user
    if user.role == 'ADMIN':
        queryset = Equipment.objects.filter(approval_status='PENDING', is_active=True)
    else:
        # Owners see equipment assigned to them needing approval; creators see what they submitted
        queryset = Equipment.objects.filter(
            approval_status='PENDING', is_active=True
        ).filter(Q(owner=user) | Q(created_by=user))

    queryset = queryset.select_related('category', 'location', 'owner', 'created_by').order_by('-created_at')
    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'equipment/equipment_pending_list.html', {
        'page_obj': page_obj,
        'pending_list': page_obj,
        'total_count': queryset.count(),
    })


@login_required
def equipment_approve_view(request, pk):
    """Approve a pending piece of equipment. The assigned owner or an admin may approve."""
    equipment = get_object_or_404(Equipment, pk=pk, approval_status='PENDING', is_active=True)

    if request.user != equipment.owner and request.user.role != 'ADMIN':
        messages.error(request, 'Only the assigned owner or an admin can approve this equipment.')
        return redirect('equipment:detail', pk=pk)

    equipment.approval_status = 'APPROVED'
    equipment.approved_by = request.user
    equipment.approved_at = timezone.now()
    equipment.save(update_fields=['approval_status', 'approved_by', 'approved_at'])

    log_activity(
        actor=request.user,
        action='EQUIPMENT_APPROVED',
        description=f'Equipment "{equipment.name}" was approved by {request.user.full_name}.',
        content_type_label='equipment',
        object_id=equipment.pk,
        object_repr=str(equipment),
        request=request,
    )

    # Notify creator if they are not the approver
    if equipment.created_by and equipment.created_by != request.user:
        notify(
            recipient=equipment.created_by,
            title='Equipment Approved',
            message=f'"{equipment.name}" has been approved by {request.user.full_name}.',
            level='success',
            link=f'/equipment/{equipment.pk}/',
            category='equipment',
        )

    messages.success(request, f'Equipment "{equipment.name}" has been approved.')
    return redirect('equipment:detail', pk=equipment.pk)


@login_required
def equipment_reject_view(request, pk):
    """Reject a pending piece of equipment. The assigned owner or an admin may reject."""
    equipment = get_object_or_404(Equipment, pk=pk, approval_status='PENDING', is_active=True)

    if request.user != equipment.owner and request.user.role != 'ADMIN':
        messages.error(request, 'Only the assigned owner or an admin can reject this equipment.')
        return redirect('equipment:detail', pk=pk)

    equipment.approval_status = 'REJECTED'
    equipment.is_active = False
    equipment.status = 'RETIRED'
    equipment.save(update_fields=['approval_status', 'is_active', 'status'])

    log_activity(
        actor=request.user,
        action='EQUIPMENT_REJECTED',
        description=f'Equipment "{equipment.name}" was rejected by {request.user.full_name}.',
        content_type_label='equipment',
        object_id=equipment.pk,
        object_repr=str(equipment),
        request=request,
    )

    # Notify creator if they are not the rejector
    if equipment.created_by and equipment.created_by != request.user:
        notify(
            recipient=equipment.created_by,
            title='Equipment Rejected',
            message=f'"{equipment.name}" was rejected by {request.user.full_name}.',
            level='error',
            link='/equipment/',
            category='equipment',
        )

    messages.success(request, f'Equipment "{equipment.name}" has been rejected.')
    return redirect('equipment:pending_list')


# ---------------------------------------------------------------------------
# Lifecycle timeline view
# ---------------------------------------------------------------------------

@login_required
def lifecycle_timeline_view(request, pk):
    """Full lifecycle event timeline for a piece of equipment."""
    equipment = get_object_or_404(Equipment, pk=pk)

    # Handle inline event creation (POST from detail page or this page)
    if request.method == 'POST':
        form = LifecycleEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.equipment = equipment
            event.performed_by = request.user
            event.save()
            messages.success(request, 'Lifecycle event recorded.')
            return redirect('equipment:lifecycle', pk=pk)
    else:
        form = LifecycleEventForm(initial={'equipment': equipment})

    events = equipment.lifecycle_events.select_related('performed_by').order_by('-timestamp')
    paginator = Paginator(events, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'equipment/lifecycle_timeline.html', {
        'equipment': equipment,
        'page_obj': page_obj,
        'form': form,
    })


# ---------------------------------------------------------------------------
# Equipment movement view
# ---------------------------------------------------------------------------

@login_required
def equipment_move_view(request, pk):
    """Log a movement of equipment from one location to another. Owner only."""
    equipment = get_object_or_404(Equipment, pk=pk)

    if request.user != equipment.owner:
        messages.error(request, 'Only the equipment owner can move it.')
        return redirect('equipment:detail', pk=pk)

    if request.method == 'POST':
        form = MovementLogForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.equipment = equipment
            movement.moved_by = request.user
            movement.save()

            # Update the equipment's current location
            equipment.location = movement.to_location
            equipment.save(update_fields=['location'])

            log_activity(
                actor=request.user,
                action='EQUIPMENT_UPDATED',
                description=(
                    f'Equipment "{equipment.name}" moved from '
                    f'"{movement.from_location}" to "{movement.to_location}" '
                    f'by {request.user.full_name}.'
                ),
                content_type_label='equipment',
                object_id=equipment.pk,
                object_repr=str(equipment),
                request=request,
            )

            notify_admins(
                title='Equipment Moved',
                message=(
                    f'Equipment "{equipment.name}" moved from '
                    f'"{movement.from_location}" to "{movement.to_location}" '
                    f'by {request.user.full_name}.'
                ),
                level='info',
                link=f'/equipment/{equipment.pk}/',
                category='equipment',
            )

            messages.success(request, f'Movement of "{equipment.name}" has been logged.')
            return redirect('equipment:detail', pk=pk)
    else:
        # Pre-populate from_location with the equipment's current location
        form = MovementLogForm(initial={'from_location': equipment.location})

    return render(request, 'equipment/equipment_move.html', {
        'form': form,
        'equipment': equipment,
    })


# ---------------------------------------------------------------------------
# Category views
# ---------------------------------------------------------------------------

@login_required
def category_list_view(request):
    """List all equipment categories."""
    categories = Category.objects.order_by('name')

    return render(request, 'equipment/category_list.html', {
        'categories': categories,
    })


@login_required
def category_create_view(request):
    """Create a new equipment category."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()

            log_activity(
                actor=request.user,
                action='OTHER',
                description=f'Category "{category.name}" created by {request.user.full_name}.',
                content_type_label='category',
                object_id=category.pk,
                object_repr=str(category),
                request=request,
            )

            notify_admins(
                title='Category Created',
                message=f'Category "{category.name}" was created by {request.user.full_name}.',
                level='info',
                link='/equipment/categories/',
                category='equipment',
            )

            messages.success(request, f'Category "{category.name}" has been created.')
            return redirect('equipment:category_list')
    else:
        form = CategoryForm()

    return render(request, 'equipment/category_form.html', {
        'form': form,
        'action': 'Create',
    })


@login_required
def category_edit_view(request, pk):
    """Edit an existing equipment category."""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()

            log_activity(
                actor=request.user,
                action='OTHER',
                description=f'Category "{category.name}" updated by {request.user.full_name}.',
                content_type_label='category',
                object_id=category.pk,
                object_repr=str(category),
                request=request,
            )

            notify_admins(
                title='Category Updated',
                message=f'Category "{category.name}" was updated by {request.user.full_name}.',
                level='info',
                link='/equipment/categories/',
                category='equipment',
            )

            messages.success(request, f'Category "{category.name}" has been updated.')
            return redirect('equipment:category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'equipment/category_form.html', {
        'form': form,
        'category': category,
        'action': 'Edit',
    })


@login_required
@admin_required
def category_delete_view(request, pk):
    """Delete an equipment category (admin only)."""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()

        log_activity(
            actor=request.user,
            action='OTHER',
            description=f'Category "{name}" deleted by {request.user.full_name}.',
            content_type_label='category',
            object_id=pk,
            object_repr=name,
            request=request,
        )

        notify_admins(
            title='Category Deleted',
            message=f'Category "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='/equipment/categories/',
            category='equipment',
        )

        messages.success(request, f'Category "{name}" has been deleted.')
        return redirect('equipment:category_list')

    return render(request, 'equipment/category_confirm_delete.html', {
        'category': category,
    })


# ---------------------------------------------------------------------------
# Location views
# ---------------------------------------------------------------------------

@login_required
def location_list_view(request):
    """List all lab locations."""
    locations = Location.objects.order_by('name')

    return render(request, 'equipment/location_list.html', {
        'locations': locations,
    })


@login_required
def location_create_view(request):
    """Create a new lab location."""
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.save()

            log_activity(
                actor=request.user,
                action='OTHER',
                description=f'Location "{location.name}" created by {request.user.full_name}.',
                content_type_label='location',
                object_id=location.pk,
                object_repr=str(location),
                request=request,
            )

            notify_admins(
                title='Location Created',
                message=f'Location "{location.name}" was created by {request.user.full_name}.',
                level='info',
                link='/equipment/locations/',
                category='equipment',
            )

            messages.success(request, f'Location "{location.name}" has been created.')
            return redirect('equipment:location_list')
    else:
        form = LocationForm()

    return render(request, 'equipment/location_form.html', {
        'form': form,
        'action': 'Create',
    })


@login_required
def location_edit_view(request, pk):
    """Edit an existing lab location."""
    location = get_object_or_404(Location, pk=pk)
    if request.method == 'POST':
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()

            log_activity(
                actor=request.user,
                action='OTHER',
                description=f'Location "{location.name}" updated by {request.user.full_name}.',
                content_type_label='location',
                object_id=location.pk,
                object_repr=str(location),
                request=request,
            )

            notify_admins(
                title='Location Updated',
                message=f'Location "{location.name}" was updated by {request.user.full_name}.',
                level='info',
                link='/equipment/locations/',
                category='equipment',
            )

            messages.success(request, f'Location "{location.name}" has been updated.')
            return redirect('equipment:location_list')
    else:
        form = LocationForm(instance=location)

    return render(request, 'equipment/location_form.html', {
        'form': form,
        'location': location,
        'action': 'Edit',
    })


@login_required
@admin_required
def location_delete_view(request, pk):
    """Delete a lab location (admin only)."""
    location = get_object_or_404(Location, pk=pk)
    if request.method == 'POST':
        name = location.name
        location.delete()

        log_activity(
            actor=request.user,
            action='OTHER',
            description=f'Location "{name}" deleted by {request.user.full_name}.',
            content_type_label='location',
            object_id=pk,
            object_repr=name,
            request=request,
        )

        notify_admins(
            title='Location Deleted',
            message=f'Location "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='/equipment/locations/',
            category='equipment',
        )

        messages.success(request, f'Location "{name}" has been deleted.')
        return redirect('equipment:location_list')

    return render(request, 'equipment/location_confirm_delete.html', {
        'location': location,
    })


# ---------------------------------------------------------------------------
# Availability JSON endpoint
# ---------------------------------------------------------------------------

@login_required
def equipment_availability_json(request):
    """Return busy date ranges for an equipment item or kit as JSON.

    Query params: ?equipment=<pk>  OR  ?kit=<pk>
    Response: {"busy": [{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "reason": "..."}]}
    """
    from apps.incidents.models import MaintenanceLog
    from apps.kits.models import Kit
    from apps.reservations.models import Reservation

    equipment_pks = request.GET.getlist('equipment')
    kit_pk = request.GET.get('kit')

    if not equipment_pks and not kit_pk:
        return JsonResponse({'busy': []})

    busy = []
    today = timezone.now().date()

    def add_reservation(res):
        busy.append({'start': str(res.start_date), 'end': str(res.end_date), 'reason': 'reserved'})

    def add_maintenance(mlog):
        start = mlog.scheduled_date or today
        end = mlog.completed_date or start
        busy.append({'start': str(start), 'end': str(end), 'reason': 'maintenance'})

    if equipment_pks:
        valid_pks = list(
            Equipment.objects.filter(pk__in=equipment_pks, is_active=True).values_list('pk', flat=True)
        )
        for equipment_pk in valid_pks:
            for res in Reservation.objects.filter(
                Q(equipment_id=equipment_pk) | Q(kit__items__equipment_id=equipment_pk),
                status__in=['CONFIRMED', 'ACTIVE', 'PENDING', 'RETURN_PENDING']
            ):
                add_reservation(res)
            for mlog in MaintenanceLog.objects.filter(equipment_id=equipment_pk, status__in=['SCHEDULED', 'IN_PROGRESS']):
                add_maintenance(mlog)

    else:
        try:
            kit_obj = Kit.objects.get(pk=kit_pk, is_active=True)
        except Kit.DoesNotExist:
            return JsonResponse({'busy': []})

        for res in Reservation.objects.filter(kit_id=kit_pk, status__in=['CONFIRMED', 'ACTIVE', 'PENDING', 'RETURN_PENDING']):
            add_reservation(res)

        eq_pks = list(kit_obj.items.values_list('equipment__pk', flat=True))
        for eq_pk in eq_pks:
            for res in Reservation.objects.filter(equipment_id=eq_pk, status__in=['CONFIRMED', 'ACTIVE', 'PENDING', 'RETURN_PENDING']):
                add_reservation(res)
            for mlog in MaintenanceLog.objects.filter(equipment_id=eq_pk, status__in=['SCHEDULED', 'IN_PROGRESS']):
                add_maintenance(mlog)

    return JsonResponse({'busy': busy})
