"""URL patterns for the dashboard app."""

from django.urls import path

from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home_view, name='home'),
    path('', views.dashboard_home_view, name='index'),
    # Legacy URLs — redirect to unified dashboard
    path('member/', views.member_dashboard_view, name='member'),
    path('admin/', views.admin_dashboard_view, name='admin'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
]
