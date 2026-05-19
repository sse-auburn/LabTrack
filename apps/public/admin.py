"""Django admin configuration for public website CMS models."""

import urllib.request
import urllib.error
import json

from django.contrib import admin
from django.utils import timezone

from apps.public import models


# ── Crossref fetch helper (shared by command and admin action) ──────────────

CROSSREF_URL = "https://api.crossref.org/works/{doi}"


def _fetch_crossref(doi):
    url = CROSSREF_URL.format(doi=doi)
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'SSELabTrack/1.0 (mailto:labtrack.sse@gmail.com)'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('message', {})
    except Exception:
        return None


def _parse_crossref(message):
    authors = []
    for author in message.get('author', []):
        given = author.get('given', '')
        family = author.get('family', '')
        if given and family:
            authors.append(f"{given} {family}")
        elif family:
            authors.append(family)
    container = message.get('container-title', [])
    journal = container[0] if container else ''
    published = message.get('published-print') or message.get('published-online') or message.get('published', {})
    date_parts = published.get('date-parts', [[]])[0]
    year = date_parts[0] if date_parts else None
    abstract = message.get('abstract', '')
    if abstract:
        abstract = abstract.replace('<jats:p>', '').replace('</jats:p>', '').replace('<jats:abstract>', '').replace('</jats:abstract>', '').strip()
    return {
        'title': message.get('title', [''])[0] if isinstance(message.get('title'), list) else message.get('title', ''),
        'authors': ', '.join(authors),
        'journal': journal,
        'year': year,
        'volume': message.get('volume', ''),
        'issue': message.get('issue', ''),
        'pages': message.get('page', ''),
        'abstract': abstract,
        'url': message.get('URL', ''),
    }


@admin.register(models.ResearchDomain)
class ResearchDomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'description')


@admin.register(models.HomepageStat)
class HomepageStatAdmin(admin.ModelAdmin):
    list_display = ('value', 'label', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('label', 'value')


@admin.register(models.HomepageHighlight)
class HomepageHighlightAdmin(admin.ModelAdmin):
    list_display = ('highlight_type', 'content_object', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('highlight_type', 'is_active')


@admin.register(models.AboutSection)
class AboutSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title', 'content')


@admin.register(models.PublicProject)
class PublicProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'funding_source', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('status', 'is_active', 'research_domains')
    search_fields = ('title', 'description', 'funding_source')
    filter_horizontal = ('research_domains', 'members')


@admin.register(models.DataResource)
class DataResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'resource_type', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('resource_type', 'is_active')
    search_fields = ('title', 'description')


@admin.register(models.JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('status', 'is_active')
    search_fields = ('title', 'description', 'requirements')


@admin.register(models.Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ('name', 'website_link', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'description')


@admin.register(models.ContactBlock)
class ContactBlockAdmin(admin.ModelAdmin):
    list_display = ('label', 'icon', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('label', 'value')


@admin.register(models.PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    list_display = ('page', 'section', 'title', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('page', 'is_active')
    search_fields = ('title', 'section', 'content')


@admin.register(models.ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)


@admin.register(models.Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'doi', 'year', 'journal', 'is_featured', 'fetched_at')
    list_editable = ('is_featured',)
    list_filter = ('year', 'is_featured')
    search_fields = ('title', 'authors', 'doi', 'journal')
    readonly_fields = ('fetched_at', 'created_at')
    actions = ['fetch_from_crossref']

    @admin.action(description='Fetch metadata from Crossref for selected publications')
    def fetch_from_crossref(self, request, queryset):
        updated = 0
        failed = 0
        for pub in queryset:
            if not pub.doi:
                failed += 1
                continue
            message = _fetch_crossref(pub.doi)
            if not message:
                failed += 1
                continue
            data = _parse_crossref(message)
            for key, value in data.items():
                setattr(pub, key, value)
            pub.fetched_at = timezone.now()
            pub.save()
            updated += 1
        self.message_user(request, f"Updated {updated} publication(s). {failed} failed or missing DOI.")


@admin.register(models.BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'is_published', 'published_at', 'created_at')
    list_editable = ('is_published',)
    list_filter = ('is_published', 'created_at')
    search_fields = ('title', 'content', 'tags')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'


@admin.register(models.NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at')
    search_fields = ('title', 'content')
    date_hierarchy = 'published_at'


@admin.register(models.GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_featured', 'order', 'is_active')
    list_editable = ('is_featured', 'order', 'is_active')
    list_filter = ('category', 'is_featured', 'is_active')
    search_fields = ('title', 'caption')
