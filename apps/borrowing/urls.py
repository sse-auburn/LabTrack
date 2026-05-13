"""URL patterns for the borrowing app."""

from django.urls import path
from django.views.generic import RedirectView

from apps.borrowing import views

app_name = 'borrowing'

urlpatterns = [
    path('', views.borrow_list_view, name='list'),
    path('request/', views.borrow_request_create_view, name='create'),
    path('bulk/', views.borrow_bulk_create_view, name='bulk_create'),
    path('<int:pk>/', views.borrow_detail_view, name='detail'),
    path('<int:pk>/return/', views.borrow_return_view, name='return'),
    path('<int:pk>/return/confirm/', views.borrow_return_confirm_view, name='return_confirm'),
    path('kit-item/<int:approval_pk>/confirm/', views.kit_item_return_confirm_view, name='kit_item_confirm'),
    path('<int:pk>/delete/', views.borrow_request_delete_view, name='delete'),
    path('overdue/', views.overdue_list_view, name='overdue'),
    path('returns/', views.return_queue_view, name='return_queue'),
    # Legacy URL kept for old notification links stored in the database
    path('return-queue/', RedirectView.as_view(pattern_name='borrowing:return_queue', permanent=True)),
]
