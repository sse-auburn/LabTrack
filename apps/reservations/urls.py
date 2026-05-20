"""URL patterns for the reservations app."""

from django.urls import path

from apps.reservations import views

app_name = 'reservations'

urlpatterns = [
    path('', views.reservation_list_view, name='list'),
    path('calendar/', views.reservation_calendar_view, name='calendar'),
    path('create/', views.reservation_create_view, name='create'),
    path('bulk/', views.reservation_bulk_create_view, name='bulk_create'),
    path('<int:pk>/', views.reservation_detail_view, name='detail'),
    path('<int:pk>/cancel/', views.reservation_cancel_view, name='cancel'),
    path('<int:pk>/confirm/', views.reservation_confirm_view, name='confirm'),
    path('<int:pk>/return/', views.reservation_return_view, name='return'),
    path('<int:pk>/return/confirm/', views.reservation_return_confirm_view, name='return_confirm'),
    path('<int:pk>/remind/', views.reservation_remind_view, name='remind'),
    path('<int:pk>/delete/', views.reservation_delete_view, name='delete'),
    path('waitlist/', views.waitlist_list_view, name='waitlist_list'),
    path('waitlist/create/', views.waitlist_create_view, name='waitlist_create'),
    path('waitlist/<int:pk>/leave/', views.waitlist_leave_view, name='waitlist_leave'),
]
