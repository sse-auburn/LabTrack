"""CMS URL patterns for the public lab website admin."""

from django.urls import path

from apps.public import cms_views

app_name = 'public_cms'

urlpatterns = [
    # Dashboard
    path('', cms_views.cms_dashboard_view, name='dashboard'),

    # Publications
    path('publications/', cms_views.publication_list_view, name='cms_publication_list'),
    path('publications/create/', cms_views.publication_create_view, name='cms_publication_create'),
    path('publications/<int:pk>/edit/', cms_views.publication_edit_view, name='cms_publication_edit'),
    path('publications/<int:pk>/delete/', cms_views.publication_delete_view, name='cms_publication_delete'),
    path('publications/<int:pk>/fetch-doi/', cms_views.publication_fetch_doi_view, name='cms_publication_fetch_doi'),

    # Blog Posts
    path('blog-posts/', cms_views.blogpost_list_view, name='cms_blogpost_list'),
    path('blog-posts/create/', cms_views.blogpost_create_view, name='cms_blogpost_create'),
    path('blog-posts/<int:pk>/edit/', cms_views.blogpost_edit_view, name='cms_blogpost_edit'),
    path('blog-posts/<int:pk>/delete/', cms_views.blogpost_delete_view, name='cms_blogpost_delete'),

    # News Items
    path('news-items/', cms_views.newsitem_list_view, name='cms_newsitem_list'),
    path('news-items/create/', cms_views.newsitem_create_view, name='cms_newsitem_create'),
    path('news-items/<int:pk>/edit/', cms_views.newsitem_edit_view, name='cms_newsitem_edit'),
    path('news-items/<int:pk>/delete/', cms_views.newsitem_delete_view, name='cms_newsitem_delete'),

    # Public Projects
    path('public-projects/', cms_views.publicproject_list_view, name='cms_publicproject_list'),
    path('public-projects/create/', cms_views.publicproject_create_view, name='cms_publicproject_create'),
    path('public-projects/<int:pk>/edit/', cms_views.publicproject_edit_view, name='cms_publicproject_edit'),
    path('public-projects/<int:pk>/delete/', cms_views.publicproject_delete_view, name='cms_publicproject_delete'),

    # Homepage Stats
    path('homepage-stats/', cms_views.homepagetat_list_view, name='cms_homepagestat_list'),
    path('homepage-stats/create/', cms_views.homepagestat_create_view, name='cms_homepagestat_create'),
    path('homepage-stats/<int:pk>/edit/', cms_views.homepagestat_edit_view, name='cms_homepagestat_edit'),
    path('homepage-stats/<int:pk>/delete/', cms_views.homepagestat_delete_view, name='cms_homepagestat_delete'),

    # Homepage Highlights
    path('homepage-highlights/', cms_views.homepagehighlight_list_view, name='cms_homepagehighlight_list'),
    path('homepage-highlights/reorder/', cms_views.homepagehighlight_reorder_view, name='cms_homepagehighlight_reorder'),
    path('homepage-highlights/create/', cms_views.homepagehighlight_create_view, name='cms_homepagehighlight_create'),
    path('homepage-highlights/<int:pk>/edit/', cms_views.homepagehighlight_edit_view, name='cms_homepagehighlight_edit'),
    path('homepage-highlights/<int:pk>/delete/', cms_views.homepagehighlight_delete_view, name='cms_homepagehighlight_delete'),

    # About Page
    path('about-page/', cms_views.aboutpage_edit_view, name='cms_aboutpage_edit'),

    # Job Openings
    path('job-openings/', cms_views.jobopening_list_view, name='cms_jobopening_list'),
    path('job-openings/create/', cms_views.jobopening_create_view, name='cms_jobopening_create'),
    path('job-openings/<int:pk>/edit/', cms_views.jobopening_edit_view, name='cms_jobopening_edit'),
    path('job-openings/<int:pk>/delete/', cms_views.jobopening_delete_view, name='cms_jobopening_delete'),

    # Sponsors
    path('sponsors/', cms_views.sponsor_list_view, name='cms_sponsor_list'),
    path('sponsors/create/', cms_views.sponsor_create_view, name='cms_sponsor_create'),
    path('sponsors/<int:pk>/edit/', cms_views.sponsor_edit_view, name='cms_sponsor_edit'),
    path('sponsors/<int:pk>/delete/', cms_views.sponsor_delete_view, name='cms_sponsor_delete'),

    # Page Sections
    path('page-sections/', cms_views.pagesection_list_view, name='cms_pagesection_list'),
    path('page-sections/create/', cms_views.pagesection_create_view, name='cms_pagesection_create'),
    path('page-sections/<int:pk>/edit/', cms_views.pagesection_edit_view, name='cms_pagesection_edit'),
    path('page-sections/<int:pk>/delete/', cms_views.pagesection_delete_view, name='cms_pagesection_delete'),

    # Alumni
    path('alumni/', cms_views.alumni_list_view, name='cms_alumni_list'),
    path('alumni/create/', cms_views.alumni_create_view, name='cms_alumni_create'),
    path('alumni/<int:pk>/edit/', cms_views.alumni_edit_view, name='cms_alumni_edit'),
    path('alumni/<int:pk>/delete/', cms_views.alumni_delete_view, name='cms_alumni_delete'),

    # Contact Messages
    path('contact-messages/', cms_views.contactmessage_list_view, name='cms_contactmessage_list'),
    path('contact-messages/<int:pk>/', cms_views.contactmessage_detail_view, name='cms_contactmessage_detail'),
    path('contact-messages/<int:pk>/delete/', cms_views.contactmessage_delete_view, name='cms_contactmessage_delete'),
]
