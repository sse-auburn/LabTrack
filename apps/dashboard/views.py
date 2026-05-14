"""Views for the dashboard app."""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import redirect, render

from apps.accounts.decorators import admin_required
from apps.activity.models import ActivityLog
from apps.borrowing.models import BorrowRequest, KitItemReturnApproval
from apps.consumables.models import Consumable
from apps.equipment.models import Equipment
from apps.incidents.models import IncidentReport
from apps.notifications.models import Notification
from apps.reservations.models import Reservation


@login_required
def dashboard_redirect_view(request):
    """Redirect to the appropriate dashboard based on the user's role."""
    if request.user.role == 'ADMIN':
        return redirect('dashboard:admin')
    return redirect('dashboard:member')


@login_required
def member_dashboard_view(request):
    """Dashboard for regular members."""
    user = request.user
    today = date.today()
    week_ahead = today + timedelta(days=7)

    active_borrows = BorrowRequest.objects.filter(
        borrower=user,
        status__in=['APPROVED', 'ACTIVE'],
    ).select_related('equipment', 'kit').order_by('due_date')

    # Borrows submitted for return, awaiting owner confirmation
    my_pending_returns = BorrowRequest.objects.filter(
        borrower=user,
        status='RETURN_PENDING',
    ).select_related('equipment', 'kit').order_by('-returned_date')

    # Returns on equipment the user owns — needs their confirmation
    return_approvals = BorrowRequest.objects.filter(
        status='RETURN_PENDING',
        equipment__owner=user,
    ).select_related('borrower', 'equipment').order_by('returned_date')

    # Kit item return approvals assigned to this user
    kit_item_approvals = KitItemReturnApproval.objects.filter(
        owner=user,
        confirmed_by__isnull=True,
        borrow_request__status='RETURN_PENDING',
    ).select_related('borrow_request__borrower', 'borrow_request__kit', 'equipment')

    upcoming_reservations = Reservation.objects.filter(
        requester=user,
        status='CONFIRMED',
        start_date__gte=today,
        start_date__lte=week_ahead,
    ).select_related('equipment', 'kit').order_by('start_date')

    recent_notifications = Notification.objects.filter(
        recipient=user,
        is_read=False,
    ).order_by('-created_at')[:5]

    recent_activity = ActivityLog.objects.filter(
        actor=user,
    ).order_by('-timestamp')[:10]

    return render(request, 'dashboard/member.html', {
        'active_borrows': active_borrows,
        'my_pending_returns': my_pending_returns,
        'return_approvals': return_approvals,
        'kit_item_approvals': kit_item_approvals,
        'upcoming_reservations': upcoming_reservations,
        'recent_notifications': recent_notifications,
        'recent_activity': recent_activity,
    })


@admin_required
def admin_dashboard_view(request):
    """Dashboard for administrators with system-wide statistics."""
    today = date.today()

    # Core counts
    total_equipment = Equipment.objects.filter(is_active=True).count()
    available_equipment = Equipment.objects.filter(status='AVAILABLE', is_active=True).count()
    pending_equipment = Equipment.objects.filter(approval_status='PENDING', is_active=True).count()
    # Admins handle kit returns (equipment returns go to equipment owners)
    pending_approvals = BorrowRequest.objects.filter(
        status='RETURN_PENDING', kit__isnull=False
    ).count()
    open_incidents = IncidentReport.objects.filter(
        status__in=['OPEN', 'INVESTIGATING']
    ).count()

    # Overdue borrows
    overdue_borrows = BorrowRequest.objects.filter(
        due_date__lt=today,
        status__in=['APPROVED', 'ACTIVE'],
    ).select_related('borrower', 'equipment', 'kit').order_by('due_date')

    # Low-stock consumables
    all_consumables = Consumable.objects.filter(is_active=True).select_related('category')
    low_stock_consumables = [c for c in all_consumables if c.is_low_stock]

    # Recent activity
    recent_activity = ActivityLog.objects.select_related('actor').order_by('-timestamp')[:15]

    # Most borrowed equipment (top 5)
    most_borrowed = (
        BorrowRequest.objects
        .exclude(equipment__isnull=True)
        .values('equipment__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Category usage (top 5)
    category_usage = (
        BorrowRequest.objects
        .exclude(equipment__isnull=True)
        .exclude(equipment__category__isnull=True)
        .values('equipment__category__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    # Monthly borrows for the last 6 months (for chart)
    monthly_borrows = []
    for i in range(5, -1, -1):
        # Calculate the first day of the month i months ago
        month_offset = today.month - i
        year_offset = today.year
        while month_offset <= 0:
            month_offset += 12
            year_offset -= 1
        month_start = date(year_offset, month_offset, 1)
        # Last day of that month
        if month_offset == 12:
            month_end = date(year_offset + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year_offset, month_offset + 1, 1) - timedelta(days=1)

        count = BorrowRequest.objects.filter(
            requested_date__date__gte=month_start,
            requested_date__date__lte=month_end,
        ).count()

        monthly_borrows.append({
            'month': month_start.strftime('%b %Y'),
            'count': count,
        })

    return render(request, 'dashboard/admin.html', {
        'total_equipment': total_equipment,
        'available_equipment': available_equipment,
        'pending_equipment': pending_equipment,
        'pending_approvals': pending_approvals,
        'overdue_borrows': overdue_borrows,
        'low_stock_consumables': low_stock_consumables,
        'open_incidents': open_incidents,
        'recent_activity': recent_activity,
        'most_borrowed': most_borrowed,
        'category_usage': category_usage,
        'monthly_borrows': monthly_borrows,
    })


@admin_required
def admin_panel_view(request):
    """Functional admin panel — central hub for managing the entire system."""
    from django.apps import apps
    from apps.accounts.models import CustomUser
    from apps.equipment.models import Category, Location
    from apps.kits.models import Kit
    from apps.projects.models import Project
    from apps.incidents.models import MaintenanceLog, CalibrationLog

    today = date.today()

    counts = {
        'users': CustomUser.objects.count(),
        'members': CustomUser.objects.filter(role='MEMBER').count(),
        'admins': CustomUser.objects.filter(role='ADMIN').count(),
        'equipment': Equipment.objects.filter(is_active=True).count(),
        'categories': Category.objects.count(),
        'locations': Location.objects.count(),
        'kits': Kit.objects.count(),
        'projects': Project.objects.count(),
        'consumables': Consumable.objects.filter(is_active=True).count(),
        'borrow_requests': BorrowRequest.objects.count(),
        'pending_returns': BorrowRequest.objects.filter(status='RETURN_PENDING').count(),
        'pending_equipment': Equipment.objects.filter(approval_status='PENDING', is_active=True).count(),
        'overdue': BorrowRequest.objects.filter(due_date__lt=today, status__in=['APPROVED', 'ACTIVE']).count(),
        'reservations': Reservation.objects.count(),
        'incidents_open': IncidentReport.objects.filter(status__in=['OPEN', 'INVESTIGATING']).count(),
        'maintenance': MaintenanceLog.objects.count(),
        'calibration': CalibrationLog.objects.count(),
        'activity': ActivityLog.objects.count(),
        'notifications': Notification.objects.filter(is_read=False).count(),
    }

    return render(request, 'admin_panel.html', {'counts': counts})
