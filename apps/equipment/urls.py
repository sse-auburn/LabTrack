"""URL patterns for the equipment app."""

from django.urls import path

from apps.equipment import views

app_name = 'equipment'

urlpatterns = [
    # Equipment list & CRUD
    path('', views.equipment_list_view, name='list'),
    path('create/', views.equipment_create_view, name='create'),
    path('bulk-delete/', views.equipment_bulk_delete_view, name='bulk_delete'),
    path('pending/', views.equipment_pending_list_view, name='pending_list'),
    path('<int:pk>/', views.equipment_detail_view, name='detail'),
    path('<int:pk>/edit/', views.equipment_edit_view, name='edit'),
    path('<int:pk>/delete/', views.equipment_delete_view, name='delete'),
    path('<int:pk>/approve/', views.equipment_approve_view, name='approve'),
    path('<int:pk>/reject/', views.equipment_reject_view, name='reject'),

    # Lifecycle & movement
    path('<int:pk>/lifecycle/', views.lifecycle_timeline_view, name='lifecycle'),
    path('<int:pk>/move/', views.equipment_move_view, name='move'),

    # Categories
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/create/', views.category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit_view, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete_view, name='category_delete'),

    # Availability JSON
    path('availability/', views.equipment_availability_json, name='availability_json'),

    # Locations
    path('locations/', views.location_list_view, name='location_list'),
    path('locations/create/', views.location_create_view, name='location_create'),
    path('locations/<int:pk>/edit/', views.location_edit_view, name='location_edit'),
    path('locations/<int:pk>/delete/', views.location_delete_view, name='location_delete'),
]
