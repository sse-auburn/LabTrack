"""
Utility helpers for creating in-app notifications and sending email alerts.
Respects per-user notification preferences (global + per-category toggles).
"""

import logging

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

User = get_user_model()

# Category names must match UserProfile field names (notify_<category>)
CATEGORY_BORROWING = 'borrowing'
CATEGORY_RESERVATIONS = 'reservations'
CATEGORY_INCIDENTS = 'incidents'
CATEGORY_EQUIPMENT = 'equipment'
CATEGORY_KITS = 'kits'
CATEGORY_CONSUMABLES = 'consumables'
CATEGORY_PROJECTS = 'projects'
CATEGORY_SYSTEM = 'system'

_ALL_CATEGORIES = {
    CATEGORY_BORROWING,
    CATEGORY_RESERVATIONS,
    CATEGORY_INCIDENTS,
    CATEGORY_EQUIPMENT,
    CATEGORY_KITS,
    CATEGORY_CONSUMABLES,
    CATEGORY_PROJECTS,
    CATEGORY_SYSTEM,
}


def _profile_allows(profile, category):
    """Return True if the user's profile permits notifications for *category*."""
    if not profile:
        return True  # No profile yet — permissive default.
    field_name = f'notify_{category}'
    return getattr(profile, field_name, True)


def _send_email(recipient, title, message, link='', category='system'):
    """Send a plain-text notification email. Silently skips if email is not configured."""
    if not recipient.email:
        return

    try:
        profile = recipient.profile
    except Exception:
        profile = None

    # Global email opt-out
    if profile and not profile.email_notifications:
        return

    # Per-category email opt-out
    if category not in _ALL_CATEGORIES or not _profile_allows(profile, category):
        return

    body_parts = [message]
    if link:
        base_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        body_parts.append(f'\nView details: {base_url}{link}')

    try:
        send_mail(
            subject=f'[LabTrack] {title}',
            message='\n'.join(body_parts),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=False,
        )
    except Exception as exc:
        # Log the failure but never let an email error break the request.
        logger.warning('Failed to send notification email to %s: %s', recipient.email, exc)


def notify(recipient, title, message, level='info', link='', category='system'):
    """Create an in-app notification and send an email for a single user.

    Parameters
    ----------
    recipient : CustomUser
        The user to notify.
    title, message, level, link : str
        Notification content.
    category : str
        One of the CATEGORY_* constants. Used to check per-user preferences.
    """
    from apps.notifications.models import Notification

    if not (recipient and recipient.is_active):
        return

    try:
        profile = recipient.profile
    except Exception:
        profile = None

    # In-app notification (respect global + per-category prefs)
    if (not profile or profile.in_app_notifications) and _profile_allows(profile, category):
        Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            level=level,
            link=link,
        )

    # Email notification (handled inside _send_email with its own checks)
    _send_email(recipient, title, message, link, category)


def notify_admins(title, message, level='info', link='', category='system'):
    """Notify all active admin users (in-app + email), respecting their preferences."""
    admins = User.objects.filter(role='ADMIN', is_active=True)
    for admin in admins:
        notify(admin, title, message, level, link, category)


def notify_users(users, title, message, level='info', link='', category='system'):
    """Notify a specific queryset or list of users."""
    for user in users:
        notify(user, title, message, level, link, category)
