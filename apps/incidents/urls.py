"""URL patterns for the incidents app."""

from django.urls import path

from apps.incidents import views

app_name = 'incidents'

urlpatterns = [
    # Incidents
    path('', views.incident_list_view, name='list'),
    path('report/', views.incident_create_view, name='create'),
    path('<int:pk>/', views.incident_detail_view, name='detail'),
    path('<int:pk>/edit/', views.incident_edit_view, name='edit'),
    path('<int:pk>/resolve/', views.incident_resolve_view, name='resolve'),
    path('<int:pk>/assign/', views.incident_assign_view, name='assign'),
    path('<int:pk>/delete/', views.incident_delete_view, name='delete'),

    # Maintenance
    path('maintenance/', views.maintenance_list_view, name='maintenance_list'),
    path('maintenance/create/', views.maintenance_create_view, name='maintenance_create'),
    path('maintenance/<int:pk>/', views.maintenance_detail_view, name='maintenance_detail'),
    path('maintenance/<int:pk>/complete/', views.maintenance_complete_view, name='maintenance_complete'),
    path('maintenance/<int:pk>/delete/', views.maintenance_delete_view, name='maintenance_delete'),

    # Calibration
    path('calibration/', views.calibration_list_view, name='calibration_list'),
    path('calibration/create/', views.calibration_create_view, name='calibration_create'),
    path('calibration/<int:pk>/delete/', views.calibration_delete_view, name='calibration_delete'),
]
