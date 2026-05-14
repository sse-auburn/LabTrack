"""URL patterns for the dashboard app."""

from django.urls import path

from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    # 'home' and 'index' both resolve to the redirect view so that both
    # apps.accounts (which uses 'dashboard:index') and new code (which can
    # use 'dashboard:home') work without changes.
    path('', views.dashboard_redirect_view, name='home'),
    path('', views.dashboard_redirect_view, name='index'),
    path('member/', views.member_dashboard_view, name='member'),
    path('admin/', views.admin_dashboard_view, name='admin'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
]
