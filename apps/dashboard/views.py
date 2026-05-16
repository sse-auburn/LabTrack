"""Views for the dashboard app."""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.activity.models import ActivityLog
from apps.borrowing.models import BorrowRequest, KitItemReturnApproval
from apps.equipment.models import Equipment
from apps.incidents.models import IncidentReport
from apps.kits.models import Kit
from apps.notifications.models import Notification
from apps.reservations.models import Reservation


@login_required
def dashboard_redirect_view(request):
    """Legacy redirect — all users now share one dashboard."""
    return redirect('dashboard:home')


@login_required
def dashboard_home_view(request):
    """Unified dashboard for all users. Admins see system-wide stats in addition to personal data."""
    user = request.user
    today = date.today()
    week_ahead = today + timedelta(days=7)
    is_admin = user.is_admin

    # ── Personal data (everyone) ──────────────────────────────────────────────
    active_borrows = BorrowRequest.objects.filter(
        borrower=user,
        status__in=['APPROVED', 'ACTIVE'],
    ).select_related('equipment', 'kit').order_by('due_date')

    my_pending_returns = BorrowRequest.objects.filter(
        borrower=user,
        status='RETURN_PENDING',
    ).select_related('equipment', 'kit').order_by('-returned_date')

    return_approvals = BorrowRequest.objects.filter(
        status='RETURN_PENDING',
        equipment__owner=user,
    ).select_related('borrower', 'equipment').order_by('returned_date')

    kit_item_approvals = KitItemReturnApproval.objects.filter(
        owner=user,
        confirmed_by__isnull=True,
        borrow_request__status='RETURN_PENDING',
    ).select_related('borrow_request__borrower', 'borrow_request__kit', 'equipment')

    upcoming_reservations = Reservation.objects.filter(
        requester=user,
        status__in=['CONFIRMED', 'PENDING'],
    ).filter(
        Q(start_date__gte=today, start_date__lte=week_ahead) |
        Q(start_date__lte=today, end_date__gte=today)
    ).select_related('equipment', 'kit').order_by('start_date')

    recent_notifications = Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).order_by('-created_at')[:5]

    my_recent_activity = ActivityLog.objects.filter(
        actor=user,
    ).order_by('-timestamp')[:10]

    pending_owned_equipment = Equipment.objects.filter(
        approval_status='PENDING', is_active=True, owner=user
    )

    context = {
        'active_borrows': active_borrows,
        'my_pending_returns': my_pending_returns,
        'return_approvals': return_approvals,
        'kit_item_approvals': kit_item_approvals,
        'upcoming_reservations': upcoming_reservations,
        'recent_notifications': recent_notifications,
        'my_recent_activity': my_recent_activity,
        'pending_owned_equipment': pending_owned_equipment,
    }

    # ── Admin-only system data ────────────────────────────────────────────────
    if is_admin:
        total_equipment = Equipment.objects.filter(is_active=True).count()
        available_equipment = Equipment.objects.filter(status='AVAILABLE', is_active=True).count()
        pending_equipment = Equipment.objects.filter(approval_status='PENDING', is_active=True).count()
        pending_approvals = BorrowRequest.objects.filter(
            status='RETURN_PENDING', kit__isnull=False
        ).count()
        open_incidents = IncidentReport.objects.filter(
            status__in=['OPEN', 'INVESTIGATING']
        ).count()

        total_kits = Kit.objects.filter(is_active=True).count()
        shared_kits = Kit.objects.filter(is_active=True, is_shared=True).count()

        overdue_borrows = BorrowRequest.objects.filter(
            due_date__lt=today,
            status__in=['APPROVED', 'ACTIVE'],
        ).select_related('borrower', 'equipment', 'kit').order_by('due_date')

        system_activity = ActivityLog.objects.select_related('actor').order_by('-timestamp')[:15]

        context.update({
            'total_equipment': total_equipment,
            'available_equipment': available_equipment,
            'pending_equipment': pending_equipment,
            'pending_approvals': pending_approvals,
            'open_incidents': open_incidents,
            'total_kits': total_kits,
            'shared_kits': shared_kits,
            'overdue_borrows': overdue_borrows,
            'system_activity': system_activity,
        })

    return render(request, 'dashboard/home.html', context)


# Legacy views — redirect to unified dashboard
@login_required
def member_dashboard_view(request):
    return redirect('dashboard:home')


@login_required
def admin_dashboard_view(request):
    return redirect('dashboard:home')


@login_required
def admin_panel_view(request):
    return redirect('dashboard:home')
