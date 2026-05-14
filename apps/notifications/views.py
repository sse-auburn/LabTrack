"""Views for the notifications app."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required
from apps.notifications.models import Notification


@login_required
def notification_list_view(request):
    """List all of the current user's notifications, paginated.
    Unread notifications are marked as read when this page is opened.
    """
    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True, read_at=timezone.now())

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')

    paginator = Paginator(notifications, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'notifications/list.html', {'page_obj': page_obj})


@login_required
@require_POST
def mark_read_view(request, pk):
    """POST: mark a single notification as read for the current user.
    Returns JSON with the updated unread count.
    """
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])

    # AJAX callers get JSON; regular form submissions get a redirect.
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        unread_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return JsonResponse({'success': True, 'unread_count': unread_count})

    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_read_view(request):
    """POST: mark all of the current user's unread notifications as read."""
    updated = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True, read_at=timezone.now())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'marked_count': updated})

    return redirect('notifications:list')


@login_required
def unread_count_view(request):
    """GET: return the number of unread notifications for the current user as JSON."""
    count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    return JsonResponse({'unread_count': count})


@login_required
def notification_delete_view(request, pk):
    """Delete a notification (owner or admin only)."""
    notification = get_object_or_404(Notification, pk=pk)

    if request.user.role != 'ADMIN' and notification.recipient != request.user:
        messages.error(request, 'You do not have permission to delete this notification.')
        return redirect('notifications:list')

    if request.method == 'POST':
        notification.delete()
        messages.success(request, 'Notification has been deleted.')
        return redirect('notifications:list')

    return render(request, 'notifications/notification_confirm_delete.html', {
        'notification': notification,
    })


@login_required
@admin_required
def notification_clear_all_view(request):
    """Admin only: delete all notifications."""
    if request.method == 'POST':
        deleted, _ = Notification.objects.all().delete()
        messages.success(request, f'{deleted} notification(s) have been cleared.')
        return redirect('notifications:list')

    return render(request, 'notifications/notification_confirm_clear_all.html')
