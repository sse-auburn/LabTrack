"""Views for the dashboard app."""

from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.accounts.models import CustomUser
from apps.activity.models import ActivityLog
from apps.equipment.models import Equipment, Category, Location
from apps.incidents.models import IncidentReport, MaintenanceLog, CalibrationLog
from apps.kits.models import Kit
from apps.notifications.models import Notification
from apps.reservations.models import Reservation
from apps.public import models as public_models


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
    active_reservations = Reservation.objects.filter(
        requester=user,
        status='ACTIVE',
    ).select_related('equipment', 'kit').order_by('end_date')

    my_pending_returns = Reservation.objects.filter(
        requester=user,
        status='RETURN_PENDING',
    ).select_related('equipment', 'kit').order_by('-returned_date')

    return_approvals = Reservation.objects.filter(
        status='RETURN_PENDING',
        equipment__owner=user,
    ).select_related('requester', 'equipment').order_by('returned_date')

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
        'active_reservations': active_reservations,
        'my_pending_returns': my_pending_returns,
        'return_approvals': return_approvals,
        'upcoming_reservations': upcoming_reservations,
        'recent_notifications': recent_notifications,
        'my_recent_activity': my_recent_activity,
        'pending_owned_equipment': pending_owned_equipment,
    }

    # ── Admin-only system data ────────────────────────────────────────────────
    if is_admin:
        total_equipment = Equipment.objects.filter(is_active=True).count()
        available_equipment = Equipment.objects.filter(is_active=True, status='AVAILABLE').count()
        pending_equipment = Equipment.objects.filter(approval_status='PENDING', is_active=True).count()
        open_incidents = IncidentReport.objects.filter(
            status__in=['OPEN', 'INVESTIGATING']
        ).count()
        total_kits = Kit.objects.filter(is_active=True).count()
        shared_kits = Kit.objects.filter(is_active=True, is_shared=True).count()
        pending_users = CustomUser.objects.filter(is_active=False).count()
        active_reservations_count = Reservation.objects.filter(status='ACTIVE').count()
        pending_returns_count = Reservation.objects.filter(status='RETURN_PENDING').count()

        overdue_reservations = Reservation.objects.filter(
            end_date__lt=today,
            status__in=['CONFIRMED', 'ACTIVE'],
        ).select_related('requester', 'equipment', 'kit').order_by('end_date')

        system_activity = ActivityLog.objects.select_related('actor').order_by('-timestamp')[:15]

        context.update({
            'total_equipment': total_equipment,
            'available_equipment': available_equipment,
            'pending_equipment': pending_equipment,
            'open_incidents': open_incidents,
            'total_kits': total_kits,
            'shared_kits': shared_kits,
            'pending_users': pending_users,
            'active_reservations_count': active_reservations_count,
            'pending_returns_count': pending_returns_count,
            'overdue_reservations': overdue_reservations,
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
    """Custom admin panel for LabTrack management."""
    if not request.user.is_admin:
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')

    counts = {
        'equipment': Equipment.objects.filter(is_active=True).count(),
        'users': CustomUser.objects.count(),
        'borrow_requests': Reservation.objects.count(),
        'reservations': Reservation.objects.count(),
        'incidents_open': IncidentReport.objects.filter(status__in=['OPEN', 'INVESTIGATING']).count(),
        'consumables': 0,
        'categories': Category.objects.count(),
        'locations': Location.objects.count(),
        'kits': Kit.objects.filter(is_active=True).count(),
        'pending_equipment': Equipment.objects.filter(approval_status='PENDING', is_active=True).count(),
        'pending_returns': Reservation.objects.filter(status='RETURN_PENDING').count(),
        'admins': CustomUser.objects.filter(role='ADMIN').count(),
        'members': CustomUser.objects.filter(role='MEMBER').count(),
        # CMS counts
        'publications': public_models.Publication.objects.count(),
        'blog_posts': public_models.BlogPost.objects.count(),
        'news_items': public_models.NewsItem.objects.count(),
        'public_projects': public_models.PublicProject.objects.count(),
        'research_domains': public_models.ResearchDomain.objects.count(),
        'job_openings': public_models.JobOpening.objects.count(),
        'sponsors': public_models.Sponsor.objects.count(),
        'maintenance': MaintenanceLog.objects.count(),
        'calibration': CalibrationLog.objects.count(),
    }

    context = {
        'counts': counts,
    }
    return render(request, 'admin_panel.html', context)
