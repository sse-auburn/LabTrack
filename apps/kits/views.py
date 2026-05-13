"""Views for the kits app."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.activity.utils import log_activity
from apps.kits.forms import KitForm, KitItemForm
from apps.kits.models import Kit, KitItem


@login_required
def kit_list_view(request):
    """List kits: split into the user's own and everyone else's."""
    base_qs = Kit.objects.filter(is_active=True).prefetch_related('items__equipment').select_related('created_by')
    my_kits = base_qs.filter(created_by=request.user)
    shared_kits = base_qs.filter(is_shared=True).exclude(created_by=request.user)
    return render(request, 'kits/kit_list.html', {
        'my_kits': my_kits,
        'shared_kits': shared_kits,
    })


@login_required
def kit_detail_view(request, pk):
    """Show kit details including its items and borrow history."""
    kit = get_object_or_404(
        Kit.objects.prefetch_related('items__equipment').select_related('created_by'),
        pk=pk,
    )
    borrow_history = kit.borrow_requests.select_related(
        'borrower', 'approved_by'
    ).order_by('-requested_date')[:20]

    return render(request, 'kits/kit_detail.html', {
        'kit': kit,
        'borrow_history': borrow_history,
    })


@login_required
def kit_create_view(request):
    """Create a new kit (any authenticated user)."""
    if request.method == 'POST':
        form = KitForm(request.POST)
        if form.is_valid():
            kit = form.save(commit=False)
            kit.created_by = request.user
            kit.save()

            log_activity(
                actor=request.user,
                action='KIT_CREATED',
                description=f'{request.user.username} created kit "{kit.name}"',
                content_type_label='kit',
                object_id=kit.pk,
                object_repr=str(kit),
                request=request,
            )

            messages.success(request, f'Kit "{kit.name}" created successfully.')
            return redirect('kits:detail', pk=kit.pk)
    else:
        form = KitForm()

    return render(request, 'kits/kit_form.html', {'form': form, 'action': 'Create'})


@login_required
def kit_edit_view(request, pk):
    """Edit an existing kit."""
    kit = get_object_or_404(Kit, pk=pk)

    if kit.created_by != request.user:
        messages.error(request, 'You do not have permission to edit this kit.')
        return redirect('kits:detail', pk=kit.pk)

    if request.method == 'POST':
        form = KitForm(request.POST, instance=kit)
        if form.is_valid():
            form.save()

            log_activity(
                actor=request.user,
                action='KIT_UPDATED',
                description=f'{request.user.username} updated kit "{kit.name}"',
                content_type_label='kit',
                object_id=kit.pk,
                object_repr=str(kit),
                request=request,
            )

            messages.success(request, f'Kit "{kit.name}" updated successfully.')
            return redirect('kits:detail', pk=kit.pk)
    else:
        form = KitForm(instance=kit)

    return render(request, 'kits/kit_form.html', {'form': form, 'kit': kit, 'action': 'Edit'})


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
        messages.success(request, f'Kit "{kit_name}" deleted.')
        return redirect('kits:list')

    return render(request, 'kits/kit_confirm_delete.html', {'kit': kit})


@login_required
def kit_item_add_view(request, pk):
    """Add a piece of equipment to a kit."""
    kit = get_object_or_404(Kit, pk=pk)

    if kit.created_by != request.user:
        messages.error(request, 'You do not have permission to modify this kit.')
        return redirect('kits:detail', pk=kit.pk)

    if request.method == 'POST':
        form = KitItemForm(request.POST, kit=kit)
        if form.is_valid():
            item = form.save(commit=False)
            item.kit = kit
            item.save()

            log_activity(
                actor=request.user,
                action='KIT_UPDATED',
                description=(
                    f'{request.user.username} added "{item.equipment.name}" to kit "{kit.name}"'
                ),
                content_type_label='kit',
                object_id=kit.pk,
                object_repr=str(kit),
                request=request,
            )

            messages.success(
                request,
                f'"{item.equipment.name}" added to kit "{kit.name}".'
            )
            return redirect('kits:detail', pk=kit.pk)
    else:
        form = KitItemForm(kit=kit)

    return render(request, 'kits/kit_item_form.html', {'form': form, 'kit': kit})


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
                f'{request.user.username} removed "{equipment_name}" from kit "{kit.name}"'
            ),
            content_type_label='kit',
            object_id=kit.pk,
            object_repr=str(kit),
            request=request,
        )

        messages.success(request, f'"{equipment_name}" removed from kit "{kit.name}".')
        return redirect('kits:detail', pk=kit.pk)

    return render(request, 'kits/kit_item_confirm_remove.html', {
        'kit': kit,
        'item': item,
    })
