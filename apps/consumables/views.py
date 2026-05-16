"""Views for the consumables app."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import admin_required
from apps.activity.utils import log_activity
from apps.consumables.forms import ConsumableForm, ConsumableUsageLogForm, RestockForm
from apps.consumables.models import Consumable, ConsumableUsageLog
from apps.notifications.utils import notify_admins


@login_required
def consumable_list_view(request):
    """List all active consumables, highlighting low-stock ones. Paginated."""
    consumables = Consumable.objects.filter(is_active=True).select_related('category', 'location')
    low_stock_ids = [c.pk for c in consumables if c.is_low_stock]

    paginator = Paginator(consumables, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'consumables/list.html', {
        'page_obj': page_obj,
        'low_stock_ids': low_stock_ids,
        'low_stock_count': len(low_stock_ids),
    })


@login_required
def consumable_detail_view(request, pk):
    """Show consumable details with usage history and low-stock alert."""
    consumable = get_object_or_404(Consumable, pk=pk, is_active=True)
    usage_logs = consumable.usage_logs.select_related('used_by', 'project').order_by('-timestamp')[:20]

    return render(request, 'consumables/detail.html', {
        'consumable': consumable,
        'usage_logs': usage_logs,
        'is_low_stock': consumable.is_low_stock,
    })


@login_required
@admin_required
def consumable_create_view(request):
    """Admin only: create a new consumable."""
    if request.method == 'POST':
        form = ConsumableForm(request.POST)
        if form.is_valid():
            consumable = form.save()
            log_activity(
                actor=request.user,
                action='OTHER',
                description=f'Consumable "{consumable.name}" created.',
                content_type_label='consumable',
                object_id=consumable.pk,
                object_repr=str(consumable),
                request=request,
            )

            notify_admins(
                title='Consumable Created',
                message=f'Consumable "{consumable.name}" was created by {request.user.full_name}.',
                level='info',
                link=f'/consumables/{consumable.pk}/',
                category='consumables',
            )

            messages.success(request, f'Consumable "{consumable.name}" created successfully.')
            return redirect('consumables:detail', pk=consumable.pk)
    else:
        form = ConsumableForm()

    return render(request, 'consumables/form.html', {
        'form': form,
        'title': 'Add Consumable',
        'submit_label': 'Create',
    })


@login_required
@admin_required
def consumable_edit_view(request, pk):
    """Admin only: edit an existing consumable."""
    consumable = get_object_or_404(Consumable, pk=pk)

    if request.method == 'POST':
        form = ConsumableForm(request.POST, instance=consumable)
        if form.is_valid():
            consumable = form.save()
            log_activity(
                actor=request.user,
                action='OTHER',
                description=f'Consumable "{consumable.name}" updated.',
                content_type_label='consumable',
                object_id=consumable.pk,
                object_repr=str(consumable),
                request=request,
            )

            notify_admins(
                title='Consumable Updated',
                message=f'Consumable "{consumable.name}" was updated by {request.user.full_name}.',
                level='info',
                link=f'/consumables/{consumable.pk}/',
                category='consumables',
            )

            messages.success(request, f'Consumable "{consumable.name}" updated successfully.')
            return redirect('consumables:detail', pk=consumable.pk)
    else:
        form = ConsumableForm(instance=consumable)

    return render(request, 'consumables/form.html', {
        'form': form,
        'consumable': consumable,
        'title': f'Edit {consumable.name}',
        'submit_label': 'Save Changes',
    })


@login_required
@admin_required
def consumable_delete_view(request, pk):
    """Admin only: soft-delete (deactivate) a consumable."""
    consumable = get_object_or_404(Consumable, pk=pk)

    if request.method == 'POST':
        name = consumable.name
        consumable.is_active = False
        consumable.save(update_fields=['is_active'])
        log_activity(
            actor=request.user,
            action='OTHER',
            description=f'Consumable "{name}" deactivated.',
            content_type_label='consumable',
            object_id=consumable.pk,
            object_repr=name,
            request=request,
        )

        notify_admins(
            title='Consumable Deactivated',
            message=f'Consumable "{name}" was deactivated by {request.user.full_name}.',
            level='warning',
            link='/consumables/',
            category='consumables',
        )

        messages.success(request, f'Consumable "{name}" has been removed.')
        return redirect('consumables:list')

    return render(request, 'consumables/confirm_delete.html', {'consumable': consumable})


@login_required
def log_usage_view(request, pk):
    """Any logged-in user can log usage of a consumable."""
    consumable = get_object_or_404(Consumable, pk=pk, is_active=True)

    if request.method == 'POST':
        form = ConsumableUsageLogForm(request.POST, consumable=consumable)
        if form.is_valid():
            with transaction.atomic():
                usage_log = form.save(commit=False)
                usage_log.consumable = consumable
                usage_log.used_by = request.user
                usage_log.save()

                # NOTE: quantity deduction and low-stock notification are handled
                # by the post_save signal in consumables/signals.py.
                pass

            consumable.refresh_from_db()  # reflect signal-updated quantity

            log_activity(
                actor=request.user,
                action='CONSUMABLE_USED',
                description=(
                    f'{request.user.full_name or request.user.username} used {usage_log.quantity_used} '
                    f'{consumable.unit} of "{consumable.name}".'
                ),
                content_type_label='consumableusagelog',
                object_id=usage_log.pk,
                object_repr=str(usage_log),
                request=request,
            )

            notify_admins(
                title='Consumable Used',
                message=(
                    f'{request.user.full_name or request.user.username} used {usage_log.quantity_used} '
                    f'{consumable.unit} of "{consumable.name}".'
                ),
                level='info',
                link=f'/consumables/{consumable.pk}/',
                category='consumables',
            )

            messages.success(
                request,
                f'Usage logged: {usage_log.quantity_used} {consumable.unit} of "{consumable.name}".',
            )
            return redirect('consumables:detail', pk=consumable.pk)
    else:
        form = ConsumableUsageLogForm(consumable=consumable)

    return render(request, 'consumables/log_usage.html', {
        'form': form,
        'consumable': consumable,
    })


@login_required
@admin_required
def restock_view(request, pk):
    """Admin only: add stock to a consumable."""
    consumable = get_object_or_404(Consumable, pk=pk)

    if request.method == 'POST':
        form = RestockForm(request.POST)
        if form.is_valid():
            qty = form.cleaned_data['quantity_to_add']
            notes = form.cleaned_data.get('notes', '')

            consumable.quantity += qty
            consumable.save(update_fields=['quantity', 'updated_at'])

            log_activity(
                actor=request.user,
                action='CONSUMABLE_RESTOCKED',
                description=(
                    f'{request.user.full_name or request.user.username} restocked "{consumable.name}" '
                    f'by {qty} {consumable.unit}. Notes: {notes}'
                ),
                content_type_label='consumable',
                object_id=consumable.pk,
                object_repr=str(consumable),
                request=request,
            )

            notify_admins(
                title='Consumable Restocked',
                message=(
                    f'{request.user.full_name or request.user.username} restocked '
                    f'"{consumable.name}" by {qty} {consumable.unit}.'
                ),
                level='info',
                link=f'/consumables/{consumable.pk}/',
                category='consumables',
            )

            messages.success(
                request,
                f'Added {qty} {consumable.unit} to "{consumable.name}". '
                f'New quantity: {consumable.quantity}.',
            )
            return redirect('consumables:detail', pk=consumable.pk)
    else:
        form = RestockForm()

    return render(request, 'consumables/restock.html', {
        'form': form,
        'consumable': consumable,
    })


@login_required
@admin_required
def low_stock_list_view(request):
    """Admin only: list all consumables that are at or below their low-stock threshold."""
    all_consumables = Consumable.objects.filter(is_active=True).select_related('category', 'location')
    low_stock = [c for c in all_consumables if c.is_low_stock]

    return render(request, 'consumables/low_stock.html', {
        'consumables': low_stock,
        'count': len(low_stock),
    })
