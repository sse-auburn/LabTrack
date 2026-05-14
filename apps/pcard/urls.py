"""URL patterns for the P-Card app."""

from django.urls import path

from apps.pcard import views

app_name = 'pcard'

urlpatterns = [
    path('', views.transaction_list_view, name='list'),
    path('create/', views.transaction_create_view, name='create'),
    path('export/excel/', views.export_excel_view, name='export_excel'),
    path('export/pdf/', views.export_pdf_view, name='export_pdf'),
    path('<int:pk>/', views.transaction_detail_view, name='detail'),
    path('<int:pk>/edit/', views.transaction_edit_view, name='edit'),
    path('<int:pk>/delete/', views.transaction_delete_view, name='delete'),
]
