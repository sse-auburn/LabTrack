"""Views for the kits app."""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.activity.utils import log_activity
from apps.kits.forms import KitForm, KitItemForm
from apps.kits.models import Kit, KitItem
from apps.notifications.utils import notify_admins


@login_required
def kit_list_view(request):
    """List kits: split into the user's own and everyone else's."""
    from django.db.models import Q as _Q
    search = request.GET.get('q', '').strip()
    base_qs = Kit.objects.filter(is_active=True).prefetch_related('items__equipment').select_related('created_by')
    my_kits = base_qs.filter(created_by=request.user)
    shared_kits = base_qs.filter(is_shared=True).exclude(created_by=request.user)
    if search:
        sq = _Q(name__icontains=search) | _Q(description__icontains=search)
        if search.isdigit():
            sq |= _Q(pk=int(search))
        my_kits = my_kits.filter(sq)
        shared_kits = shared_kits.filter(sq)
    return render(request, 'kits/kit_list.html', {
        'my_kits': my_kits,
        'shared_kits': shared_kits,
        'search': search,
    })


@login_required
def kit_detail_view(request, pk):
    """Show kit details including its items and reservation history."""
    kit = get_object_or_404(
        Kit.objects.prefetch_related('items__equipment').select_related('created_by'),
        pk=pk,
    )
    from apps.reservations.models import Reservation as _Res
    reservation_history = kit.reservations.select_related(
        'requester'
    ).order_by('-start_date')[:20]

    # Calendar events — kit-level reservations + per-item equipment reservations
    cal_events = []
    res_statuses = ['PENDING', 'CONFIRMED', 'ACTIVE', 'RETURN_PENDING']

    for r in kit.reservations.filter(status__in=res_statuses).select_related('requester'):
        cal_events.append({
            'start': r.start_date.isoformat(),
            'end': r.end_date.isoformat(),
            'type': 'reservation',
            'status': r.status,
            'label': r.requester.full_name if r.requester else '',
        })

    # Also include individual equipment reservations so items reserved outside
    # of this kit still appear as busy.
    eq_pks = list(kit.items.values_list('equipment__pk', flat=True))
    for r in _Res.objects.filter(equipment_id__in=eq_pks, status__in=res_statuses).select_related('requester'):
        cal_events.append({
            'start': r.start_date.isoformat(),
            'end': r.end_date.isoformat(),
            'type': 'reservation',
            'status': r.status,
            'label': r.requester.full_name if r.requester else '',
        })

    return render(request, 'kits/kit_detail.html', {
        'kit': kit,
        'reservation_history': reservation_history,
        'calendar_events_json': json.dumps(cal_events),
    })


@login_required
def kit_create_view(request):
    """Create a new kit (any authenticated user)."""
    from apps.equipment.models import Equipment as EquipmentModel
    available_equipment = EquipmentModel.objects.filter(
        is_active=True
    ).select_related('category').order_by('name')

    if request.method == 'POST':
        form = KitForm(request.POST)
        if form.is_valid():
            kit = form.save(commit=False)
            kit.created_by = request.user
            kit.save()

            equipment_ids = request.POST.getlist('equipment_ids')
            added = []
            for eq_id in equipment_ids:
                try:
                    eq = EquipmentModel.objects.get(pk=int(eq_id), is_active=True)
                    KitItem.objects.create(kit=kit, equipment=eq)
                    added.append(eq.name)
                except (ValueError, EquipmentModel.DoesNotExist):
                    continue

            log_activity(
                actor=request.user,
                action='KIT_CREATED',
                description=f'{request.user.full_name or request.user.username} created kit "{kit.name}"',
                content_type_label='kit',
                object_id=kit.pk,
                object_repr=str(kit),
                request=request,
            )

            notify_admins(
                title='Kit Created',
                message=f'Kit "{kit.name}" was created by {request.user.full_name or request.user.username}.',
                level='info',
                link=f'/kits/{kit.pk}/',
                category='kits',
            )

            messages.success(request, f'Kit "{kit.name}" created successfully.')
            return redirect('kits:detail', pk=kit.pk)
    else:
        form = KitForm()

    return render(request, 'kits/kit_form.html', {
        'form': form,
        'action': 'Create',
        'available_equipment': available_equipment,
    })


@login_required
def kit_edit_view(request, pk):
    """Edit an existing kit."""
    kit = get_object_or_404(Kit, pk=pk)

    if kit.created_by != request.user:
        messages.error(request, 'You do not have permission to edit this kit.')
        return redirect('kits:detail', pk=kit.pk)

    from apps.equipment.models import Equipment as EquipmentModel

    if request.method == 'POST':
        existing_ids = set(kit.items.values_list('equipment_id', flat=True))
        form = KitForm(request.POST, instance=kit)
        if form.is_valid():
            form.save()

            equipment_ids = request.POST.getlist('equipment_ids')
            for eq_id in equipment_ids:
                try:
                    eq = EquipmentModel.objects.get(pk=int(eq_id), is_active=True)
                    if eq.pk not in existing_ids:
                        KitItem.objects.create(kit=kit, equipment=eq)
                        existing_ids.add(eq.pk)
                except (ValueError, EquipmentModel.DoesNotExist):
                    continue

            log_activity(
                actor=request.user,
                action='KIT_UPDATED',
                description=f'{request.user.full_name or request.user.username} updated kit "{kit.name}"',
                content_type_label='kit',
                object_id=kit.pk,
                object_repr=str(kit),
                request=request,
            )

            notify_admins(
                title='Kit Updated',
                message=f'Kit "{kit.name}" was updated by {request.user.full_name or request.user.username}.',
                level='info',
                link=f'/kits/{kit.pk}/',
                category='kits',
            )

            messages.success(request, f'Kit "{kit.name}" updated successfully.')
            return redirect('kits:detail', pk=kit.pk)
    else:
        form = KitForm(instance=kit)

    existing_ids = set(kit.items.values_list('equipment_id', flat=True))
    available_equipment = EquipmentModel.objects.filter(
        is_active=True
    ).exclude(pk__in=existing_ids).select_related('category').order_by('name')

    return render(request, 'kits/kit_form.html', {
        'form': form,
        'kit': kit,
        'action': 'Edit',
        'available_equipment': available_equipment,
    })


@login_required
def kit_delete_view(request, pk):
    """Delete a kit (admin or the creator only)."""
    kit = get_object_or_404(Kit, pk=pk)

    if kit.created_by != request.user and request.user.role != 'ADMIN':
        messages.error(request, 'You do not have permission to delete this kit.')
        return redirect('kits:detail', pk=kit.pk)

    if request.method == 'POST':
        kit_name = kit.name
        kit.delete()

        log_activity(
            actor=request.user,
            action='KIT_DELETED',
            description=f'{request.user.full_name or request.user.username} deleted kit "{kit_name}"',
            content_type_label='kit',
            object_id=pk,
            object_repr=kit_name,
            request=request,
        )

        notify_admins(
            title='Kit Deleted',
            message=f'Kit "{kit_name}" was deleted by {request.user.full_name or request.user.username}.',
            level='warning',
            link='/kits/',
            category='kits',
        )

        messages.success(request, f'Kit "{kit_name}" deleted.')
        return redirect('kits:list')

    return render(request, 'kits/kit_confirm_delete.html', {'kit': kit})


@login_required
def kit_item_add_view(request, pk):
    """Add one or more pieces of equipment to a kit."""
    kit = get_object_or_404(Kit, pk=pk)

    if kit.created_by != request.user:
        messages.error(request, 'You do not have permission to modify this kit.')
        return redirect('kits:detail', pk=kit.pk)

    from apps.equipment.models import Equipment as EquipmentModel
    existing_ids = set(kit.items.values_list('equipment_id', flat=True))
    available_equipment = EquipmentModel.objects.filter(
        is_active=True
    ).exclude(pk__in=existing_ids).select_related('category', 'location').order_by('name')

    if request.method == 'POST':
        equipment_ids = request.POST.getlist('equipment_ids')
        added = []
        for eq_id in equipment_ids:
            try:
                eq = EquipmentModel.objects.get(pk=int(eq_id), is_active=True)
                if eq.pk not in existing_ids:
                    KitItem.objects.create(kit=kit, equipment=eq)
                    added.append(eq.name)
                    existing_ids.add(eq.pk)
            except (ValueError, EquipmentModel.DoesNotExist):
                continue

        if added:
            names = ', '.join(f'"{n}"' for n in added)
            log_activity(
                actor=request.user,
                action='KIT_UPDATED',
                description=f'{request.user.full_name or request.user.username} added {names} to kit "{kit.name}"',
                content_type_label='kit',
                object_id=kit.pk,
                object_repr=str(kit),
                request=request,
            )
            notify_admins(
                title='Kit Items Added',
                message=(
                    f'{request.user.full_name or request.user.username} added '
                    f'{len(added)} item(s) to kit "{kit.name}".'
                ),
                level='info',
                link=f'/kits/{kit.pk}/',
                category='kits',
            )
            messages.success(request, f'{len(added)} item(s) added to kit "{kit.name}".')
        else:
            messages.warning(request, 'No items were added. Please select at least one.')
        return redirect('kits:detail', pk=kit.pk)

    return render(request, 'kits/kit_item_form.html', {
        'kit': kit,
        'available_equipment': available_equipment,
    })


@login_required
def kit_item_remove_view(request, pk, item_pk):
    """Remove a piece of equipment from a kit."""
    kit = get_object_or_404(Kit, pk=pk)
    item = get_object_or_404(KitItem, pk=item_pk, kit=kit)

    if kit.created_by != request.user:
        messages.error(request, 'You do not have permission to modify this kit.')
        return redirect('kits:detail', pk=kit.pk)

    if request.method == 'POST':
        equipment_name = item.equipment.name
        item.delete()

        log_activity(
            actor=request.user,
            action='KIT_UPDATED',
            description=(
                f'{request.user.full_name or request.user.username} removed "{equipment_name}" from kit "{kit.name}"'
            ),
            content_type_label='kit',
            object_id=kit.pk,
            object_repr=str(kit),
            request=request,
        )

        notify_admins(
            title='Kit Item Removed',
            message=(
                f'{request.user.full_name or request.user.username} removed '
                f'"{equipment_name}" from kit "{kit.name}".'
            ),
            level='warning',
            link=f'/kits/{kit.pk}/',
            category='kits',
        )

        messages.success(request, f'"{equipment_name}" removed from kit "{kit.name}".')
        return redirect('kits:detail', pk=kit.pk)

    return render(request, 'kits/kit_item_confirm_remove.html', {
        'kit': kit,
        'item': item,
    })
