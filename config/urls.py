"""
Root URL configuration for SSELabTrack.
"""

import config.admin_config  # noqa: F401 – configures admin site header/title

from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from apps.dashboard.views import admin_panel_view

urlpatterns = [
    # Admin panel (functional management hub)
    path('admin/', admin_panel_view, name='admin_panel'),

    # Django's built-in admin
    path('backoffice/', admin.site.urls),

    # Root redirect → dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),

    # Accounts (login, logout, register, profile)
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),

    # Dashboard (home after login)
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),

    # Equipment management
    path('equipment/', include('apps.equipment.urls', namespace='equipment')),

    # Borrowing / check-out management
    path('borrowing/', include('apps.borrowing.urls', namespace='borrowing')),

    # Reservations
    path('reservations/', include('apps.reservations.urls', namespace='reservations')),

    # Lab kits
    path('kits/', include('apps.kits.urls', namespace='kits')),

    # Projects
    path('projects/', include('apps.projects.urls', namespace='projects')),

    # Consumables
    path('consumables/', include('apps.consumables.urls', namespace='consumables')),

    # Incidents / maintenance reports
    path('incidents/', include('apps.incidents.urls', namespace='incidents')),

    # Notifications
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),

    # Activity log
    path('activity/', include('apps.activity.urls', namespace='activity')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
