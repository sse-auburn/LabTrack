"""Views for the equipment app."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

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


# ---------------------------------------------------------------------------
# Equipment CRUD views
# ---------------------------------------------------------------------------

@login_required
def equipment_list_view(request):
    """
    List all active equipment with optional filtering by category, location,
    status, condition, and a free-text search query.
    """
    queryset = Equipment.objects.select_related('category', 'location', 'owner').filter(is_active=True)

    search = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    location_id = request.GET.get('location', '').strip()
    status = request.GET.get('status', '').strip()
    condition = request.GET.get('condition', '').strip()

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(serial_number__icontains=search)
            | Q(model_number__icontains=search)
            | Q(manufacturer__icontains=search)
            | Q(description__icontains=search)
        )
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    if location_id:
        queryset = queryset.filter(location_id=location_id)
    if status:
        queryset = queryset.filter(status=status)
    if condition:
        queryset = queryset.filter(condition=condition)

    queryset = queryset.order_by('name')
    total_count = queryset.count()
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'equipment/equipment_list.html', {
        'page_obj': page_obj,
        'equipment_list': page_obj,
        'total_count': total_count,
        'categories': Category.objects.all().order_by('name'),
        'locations': Location.objects.all().order_by('name'),
    })


@login_required
def equipment_detail_view(request, pk):
    """Show full details for a single piece of equipment."""
    equipment = get_object_or_404(
        Equipment.objects.select_related('category', 'location', 'owner'),
        pk=pk,
    )

    # Borrow history (equipment-specific requests)
    borrow_history = equipment.borrow_requests.select_related(
        'borrower', 'approved_by'
    ).order_by('-requested_date')[:10]

    # Lifecycle timeline (latest first)
    lifecycle_events = equipment.lifecycle_events.select_related('performed_by').order_by('-timestamp')[:10]

    # Movement logs (latest first)
    movement_logs = equipment.movement_logs.select_related(
        'from_location', 'to_location', 'moved_by'
    ).order_by('-timestamp')[:10]

    # Form for adding a lifecycle note inline
    lifecycle_form = LifecycleEventForm(initial={'equipment': equipment})

    return render(request, 'equipment/equipment_detail.html', {
        'equipment': equipment,
        'borrow_history': borrow_history,
        'lifecycle_events': lifecycle_events,
        'movement_logs': movement_logs,
        'lifecycle_form': lifecycle_form,
    })


@login_required
def equipment_create_view(request):
    """Create a new piece of equipment."""
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            equipment = form.save(commit=False)
            # Set the owner to the current user if not specified
            if not equipment.owner:
                equipment.owner = request.user
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
    Only the owner or an admin may edit.
    """
    equipment = get_object_or_404(Equipment, pk=pk)

    # Permission check: owner or admin
    if request.user != equipment.owner and request.user.role != 'ADMIN':
        messages.error(request, 'You do not have permission to edit this equipment.')
        return redirect('equipment:detail', pk=pk)

    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=equipment)
        if form.is_valid():
            form.save()

            log_activity(
                actor=request.user,
                action='EQUIPMENT_UPDATED',
                description=f'Equipment "{equipment.name}" was updated by {request.user.full_name}.',
                content_type_label='equipment',
                object_id=equipment.pk,
                object_repr=str(equipment),
                request=request,
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
    """Soft-delete (deactivate) a piece of equipment. Owner or admin only."""
    equipment = get_object_or_404(Equipment, pk=pk)

    if request.user != equipment.owner and request.user.role != 'ADMIN':
        messages.error(request, 'Only the equipment owner or an admin can delete it.')
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

        messages.success(request, f'Equipment "{equipment_name}" has been retired.')
        return redirect('equipment:list')

    return render(request, 'equipment/equipment_confirm_delete.html', {
        'equipment': equipment,
    })


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
    paginator = Paginator(categories, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'equipment/category_list.html', {
        'page_obj': page_obj,
    })


@login_required
def category_create_view(request):
    """Create a new equipment category."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
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
    paginator = Paginator(locations, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'equipment/location_list.html', {
        'page_obj': page_obj,
    })


@login_required
def location_create_view(request):
    """Create a new lab location."""
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.save()
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
        messages.success(request, f'Location "{name}" has been deleted.')
        return redirect('equipment:location_list')

    return render(request, 'equipment/location_confirm_delete.html', {
        'location': location,
    })
