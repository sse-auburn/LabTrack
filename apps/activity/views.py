"""Views for the activity app."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import admin_required
from apps.activity.models import ActivityLog


@login_required
def activity_feed_view(request):
    """Admins see all system activity; members see only their own activity.
    Supports filtering by action type via ?action= query parameter.
    Paginated.
    """
    action_filter = request.GET.get('action', '').strip()

    if request.user.role == 'ADMIN':
        logs = ActivityLog.objects.select_related('actor').order_by('-timestamp')
    else:
        logs = ActivityLog.objects.filter(
            actor=request.user
        ).select_related('actor').order_by('-timestamp')

    if action_filter:
        logs = logs.filter(action=action_filter)

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    action_choices = ActivityLog.ACTION_CHOICES

    return render(request, 'activity/feed.html', {
        'page_obj': page_obj,
        'action_choices': action_choices,
        'current_action': action_filter,
        'is_mine': False,
    })


@login_required
def my_activity_view(request):
    """Always shows only the current user's own activity feed, paginated."""
    action_filter = request.GET.get('action', '').strip()

    logs = ActivityLog.objects.filter(
        actor=request.user
    ).select_related('actor').order_by('-timestamp')

    if action_filter:
        logs = logs.filter(action=action_filter)

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    action_choices = ActivityLog.ACTION_CHOICES

    return render(request, 'activity/my_feed.html', {
        'page_obj': page_obj,
        'action_choices': action_choices,
        'current_action': action_filter,
        'is_mine': True,
    })


@login_required
@admin_required
def activity_log_delete_view(request, pk):
    """Delete an activity log entry (admin only)."""
    log = get_object_or_404(ActivityLog, pk=pk)

    if request.method == 'POST':
        log.delete()
        messages.success(request, 'Activity log entry has been deleted.')
        return redirect('activity:feed')

    return render(request, 'activity/activity_confirm_delete.html', {'log': log})
