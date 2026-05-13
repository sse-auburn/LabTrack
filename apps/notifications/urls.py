"""URL patterns for the notifications app."""

from django.urls import path

from apps.notifications import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list_view, name='list'),
    path('<int:pk>/read/', views.mark_read_view, name='mark_read'),
    path('<int:pk>/delete/', views.notification_delete_view, name='delete'),
    path('read-all/', views.mark_all_read_view, name='mark_all_read'),
    path('clear-all/', views.notification_clear_all_view, name='clear_all'),
    path('unread-count/', views.unread_count_view, name='unread_count'),
]
