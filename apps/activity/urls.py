"""URL patterns for the activity app."""

from django.urls import path

from apps.activity import views

app_name = 'activity'

urlpatterns = [
    path('', views.activity_feed_view, name='feed'),
    path('', views.activity_feed_view, name='log'),
    path('mine/', views.my_activity_view, name='mine'),
    path('<int:pk>/delete/', views.activity_log_delete_view, name='delete'),
]