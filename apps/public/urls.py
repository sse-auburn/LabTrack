"""URL patterns for the public lab website."""

from django.urls import path

from apps.public import views

app_name = 'public'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('projects/', views.projects_view, name='projects'),
    path('data/', views.data_view, name='data'),
    path('jobs/', views.jobs_view, name='jobs'),
    path('sponsors/', views.sponsors_view, name='sponsors'),
    path('contact/', views.contact_view, name='contact'),

    # Team
    path('team/', views.team_view, name='team'),
    path('alumni/', views.alumni_view, name='alumni'),

    # Publications
    path('publications/', views.publications_view, name='publications'),
    path('publications/<int:pk>/', views.publication_detail_view, name='publication_detail'),

    # Blog
    path('blog/', views.blog_view, name='blog'),
    path('blog/<slug:slug>/', views.blog_detail_view, name='blog_detail'),

    # News
    path('news/', views.news_view, name='news'),
    path('news/<int:pk>/', views.news_detail_view, name='news_detail'),

    # Gallery
    path('gallery/', views.gallery_view, name='gallery'),
]
