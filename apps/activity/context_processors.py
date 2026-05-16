from .models import ActivityLog


def recent_activities(request):
    """Make recent activity logs available in every template."""
    if request.user.is_authenticated:
        # Admins see all activity; members see only their own
        if getattr(request.user, 'role', None) == 'ADMIN':
            queryset = ActivityLog.objects.all()
        else:
            queryset = ActivityLog.objects.filter(actor=request.user)
        return {
            'recent_activities': queryset.select_related('actor')[:5],
            'recent_activity_count': queryset.count(),
        }
    return {
        'recent_activities': [],
        'recent_activity_count': 0,
    }
