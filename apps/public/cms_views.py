"""CMS CRUD views for the public lab website.

All views require login. Some require admin role.
"""

import urllib.request
import urllib.error
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.activity.utils import log_activity
from apps.notifications.utils import notify_admins

from apps.public import models, forms


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_admin(user):
    return user.is_authenticated and (user.role == 'ADMIN' or user.is_superuser)


# ── Admin Panel (CMS Dashboard) ──────────────────────────────────────────────

@login_required
def cms_dashboard_view(request):
    """CMS dashboard showing counts of all public website content."""
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')

    context = {
        'counts': {
            'publications': models.Publication.objects.count(),
            'blog_posts': models.BlogPost.objects.count(),
            'news_items': models.NewsItem.objects.count(),

            'public_projects': models.PublicProject.objects.count(),
            'homepage_stats': models.HomepageStat.objects.count(),
            'job_openings': models.JobOpening.objects.count(),
            'sponsors': models.Sponsor.objects.count(),
            'page_sections': models.PageSection.objects.count(),
            'contact_messages': models.ContactMessage.objects.count(),
            'highlights': models.HomepageHighlight.objects.count(),
            'alumni': models.Alumni.objects.count(),
        }
    }
    return render(request, 'cms/dashboard.html', context)


# ── Research Domain CRUD ─────────────────────────────────────────────────────

@login_required
def researchdomain_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.ResearchDomain.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Research Domain',
        'model_name_plural': 'Research Domains',
        'create_url': 'public_cms:cms_researchdomain_create',
        'edit_url': 'public_cms:cms_researchdomain_edit',
        'delete_url': 'public_cms:cms_researchdomain_delete',
        'list_fields': ['name', 'order', 'is_active'],
    })


@login_required
def researchdomain_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.ResearchDomainForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Research Domain "{obj}" was created by {request.user.full_name}.',
            content_type_label='researchdomain',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Research Domain Created',
            message=f'Research Domain "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_researchdomain_list',
            category='system',
        )
        messages.success(request, 'Research domain created.')
        return redirect('public_cms:cms_researchdomain_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Research Domain',
        'list_url': 'public_cms:cms_researchdomain_list',
    })


@login_required
def researchdomain_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.ResearchDomain, pk=pk)
    form = forms.ResearchDomainForm(request.POST or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Research Domain "{obj}" was updated by {request.user.full_name}.',
            content_type_label='researchdomain',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Research Domain Updated',
            message=f'Research Domain "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_researchdomain_list',
            category='system',
        )
        messages.success(request, 'Research domain updated.')
        return redirect('public_cms:cms_researchdomain_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Research Domain',
        'list_url': 'public_cms:cms_researchdomain_list',
        'delete_url': 'public_cms:cms_researchdomain_delete',
    })


@login_required
def researchdomain_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.ResearchDomain, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Research Domain "{name}" was deleted by {request.user.full_name}.',
            content_type_label='researchdomain',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Research Domain Deleted',
            message=f'Research Domain "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_researchdomain_list',
            category='system',
        )
        messages.success(request, 'Research domain deleted.')
        return redirect('public_cms:cms_researchdomain_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Research Domain',
        'list_url': 'public_cms:cms_researchdomain_list',
    })


# ── Publication CRUD ─────────────────────────────────────────────────────────

@login_required
def publication_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.Publication.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Publication',
        'model_name_plural': 'Publications',
        'create_url': 'public_cms:cms_publication_create',
        'edit_url': 'public_cms:cms_publication_edit',
        'delete_url': 'public_cms:cms_publication_delete',
        'list_fields': ['title', 'doi', 'year', 'journal', 'is_featured'],
    })


@login_required
def publication_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.PublicationForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Publication "{obj}" was created by {request.user.full_name}.',
            content_type_label='publication',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Publication Created',
            message=f'Publication "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_publication_list',
            category='system',
        )
        messages.success(request, 'Publication created.')
        return redirect('public_cms:cms_publication_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Publication',
        'list_url': 'public_cms:cms_publication_list',
    })


@login_required
def publication_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.Publication, pk=pk)
    form = forms.PublicationForm(request.POST or None, request.FILES or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Publication "{obj}" was updated by {request.user.full_name}.',
            content_type_label='publication',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Publication Updated',
            message=f'Publication "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_publication_list',
            category='system',
        )
        messages.success(request, 'Publication updated.')
        return redirect('public_cms:cms_publication_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Publication',
        'list_url': 'public_cms:cms_publication_list',
        'delete_url': 'public_cms:cms_publication_delete',
    })


@login_required
def publication_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.Publication, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Publication "{name}" was deleted by {request.user.full_name}.',
            content_type_label='publication',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Publication Deleted',
            message=f'Publication "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_publication_list',
            category='system',
        )
        messages.success(request, 'Publication deleted.')
        return redirect('public_cms:cms_publication_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Publication',
        'list_url': 'public_cms:cms_publication_list',
    })


@login_required
def publication_fetch_doi_view(request, pk):
    """Fetch Crossref metadata for a publication."""
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    pub = get_object_or_404(models.Publication, pk=pk)
    if not pub.doi:
        messages.error(request, 'This publication has no DOI.')
        return redirect('public_cms:cms_publication_edit', pk=pk)

    url = f"https://api.crossref.org/works/{pub.doi}"
    req = urllib.request.Request(url, headers={'User-Agent': 'SSELabTrack/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            message = data.get('message', {})

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
                abstract = abstract.replace('<jats:p>', '').replace('</jats:p>', '').strip()

            pub.title = message.get('title', [''])[0] if isinstance(message.get('title'), list) else message.get('title', '')
            pub.authors = ', '.join(authors)
            pub.journal = journal
            pub.year = year
            pub.volume = message.get('volume', '')
            pub.issue = message.get('issue', '')
            pub.pages = message.get('page', '')
            pub.abstract = abstract
            pub.url = message.get('URL', '')
            pub.fetched_at = timezone.now()
            pub.save()
            messages.success(request, 'Metadata fetched from Crossref.')
    except Exception as e:
        messages.error(request, f'Failed to fetch DOI: {e}')

    return redirect('public_cms:cms_publication_edit', pk=pk)


# ── BlogPost CRUD ────────────────────────────────────────────────────────────

@login_required
def blogpost_list_view(request):
    items = models.BlogPost.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Blog Post',
        'model_name_plural': 'Blog Posts',
        'create_url': 'public_cms:cms_blogpost_create',
        'edit_url': 'public_cms:cms_blogpost_edit',
        'delete_url': 'public_cms:cms_blogpost_delete',
        'list_fields': ['title', 'author', 'is_published', 'published_at'],
    })


@login_required
def blogpost_create_view(request):
    form = forms.BlogPostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Blog Post "{post}" was created by {request.user.full_name}.',
            content_type_label='blogpost',
            object_id=post.pk,
            object_repr=str(post),
            request=request,
        )
        notify_admins(
            title='Blog Post Created',
            message=f'Blog Post "{post}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_blogpost_list',
            category='system',
        )
        messages.success(request, 'Blog post created.')
        return redirect('public_cms:cms_blogpost_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Blog Post',
        'list_url': 'public_cms:cms_blogpost_list',
    })


@login_required
def blogpost_edit_view(request, pk):
    item = get_object_or_404(models.BlogPost, pk=pk)
    # Only author or admin can edit
    if not _is_admin(request.user) and item.author != request.user:
        messages.error(request, 'You can only edit your own posts.')
        return redirect('public_cms:cms_blogpost_list')
    form = forms.BlogPostForm(request.POST or None, request.FILES or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Blog Post "{obj}" was updated by {request.user.full_name}.',
            content_type_label='blogpost',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Blog Post Updated',
            message=f'Blog Post "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_blogpost_list',
            category='system',
        )
        messages.success(request, 'Blog post updated.')
        return redirect('public_cms:cms_blogpost_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Blog Post',
        'list_url': 'public_cms:cms_blogpost_list',
        'delete_url': 'public_cms:cms_blogpost_delete',
    })


@login_required
def blogpost_delete_view(request, pk):
    item = get_object_or_404(models.BlogPost, pk=pk)
    if not _is_admin(request.user) and item.author != request.user:
        messages.error(request, 'You can only delete your own posts.')
        return redirect('public_cms:cms_blogpost_list')
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Blog Post "{name}" was deleted by {request.user.full_name}.',
            content_type_label='blogpost',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Blog Post Deleted',
            message=f'Blog Post "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_blogpost_list',
            category='system',
        )
        messages.success(request, 'Blog post deleted.')
        return redirect('public_cms:cms_blogpost_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Blog Post',
        'list_url': 'public_cms:cms_blogpost_list',
    })


# ── NewsItem CRUD ────────────────────────────────────────────────────────────

@login_required
def newsitem_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.NewsItem.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'News Item',
        'model_name_plural': 'News Items',
        'create_url': 'public_cms:cms_newsitem_create',
        'edit_url': 'public_cms:cms_newsitem_edit',
        'delete_url': 'public_cms:cms_newsitem_delete',
        'list_fields': ['title', 'published_at'],
    })


@login_required
def newsitem_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.NewsItemForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'News Item "{obj}" was created by {request.user.full_name}.',
            content_type_label='newsitem',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='News Item Created',
            message=f'News Item "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_newsitem_list',
            category='system',
        )
        messages.success(request, 'News item created.')
        return redirect('public_cms:cms_newsitem_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'News Item',
        'list_url': 'public_cms:cms_newsitem_list',
    })


@login_required
def newsitem_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.NewsItem, pk=pk)
    form = forms.NewsItemForm(request.POST or None, request.FILES or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'News Item "{obj}" was updated by {request.user.full_name}.',
            content_type_label='newsitem',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='News Item Updated',
            message=f'News Item "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_newsitem_list',
            category='system',
        )
        messages.success(request, 'News item updated.')
        return redirect('public_cms:cms_newsitem_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'News Item',
        'list_url': 'public_cms:cms_newsitem_list',
        'delete_url': 'public_cms:cms_newsitem_delete',
    })


@login_required
def newsitem_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.NewsItem, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'News Item "{name}" was deleted by {request.user.full_name}.',
            content_type_label='newsitem',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='News Item Deleted',
            message=f'News Item "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_newsitem_list',
            category='system',
        )
        messages.success(request, 'News item deleted.')
        return redirect('public_cms:cms_newsitem_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'News Item',
        'list_url': 'public_cms:cms_newsitem_list',
    })


# ── PublicProject CRUD ───────────────────────────────────────────────────────

@login_required
def publicproject_list_view(request):
    items = models.PublicProject.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Public Project',
        'model_name_plural': 'Public Projects',
        'create_url': 'public_cms:cms_publicproject_create',
        'edit_url': 'public_cms:cms_publicproject_edit',
        'delete_url': 'public_cms:cms_publicproject_delete',
        'list_fields': ['title', 'status', 'order', 'is_active'],
    })


@login_required
def publicproject_create_view(request):
    form = forms.PublicProjectForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Public Project "{obj}" was created by {request.user.full_name}.',
            content_type_label='publicproject',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Public Project Created',
            message=f'Public Project "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_publicproject_list',
            category='system',
        )
        messages.success(request, 'Project created.')
        return redirect('public_cms:cms_publicproject_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Public Project',
        'list_url': 'public_cms:cms_publicproject_list',
    })


@login_required
def publicproject_edit_view(request, pk):
    item = get_object_or_404(models.PublicProject, pk=pk)
    form = forms.PublicProjectForm(request.POST or None, request.FILES or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Public Project "{obj}" was updated by {request.user.full_name}.',
            content_type_label='publicproject',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Public Project Updated',
            message=f'Public Project "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_publicproject_list',
            category='system',
        )
        messages.success(request, 'Project updated.')
        return redirect('public_cms:cms_publicproject_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Public Project',
        'list_url': 'public_cms:cms_publicproject_list',
        'delete_url': 'public_cms:cms_publicproject_delete',
    })


@login_required
def publicproject_delete_view(request, pk):
    item = get_object_or_404(models.PublicProject, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Public Project "{name}" was deleted by {request.user.full_name}.',
            content_type_label='publicproject',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Public Project Deleted',
            message=f'Public Project "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_publicproject_list',
            category='system',
        )
        messages.success(request, 'Project deleted.')
        return redirect('public_cms:cms_publicproject_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Public Project',
        'list_url': 'public_cms:cms_publicproject_list',
    })


# ── HomepageStat CRUD ────────────────────────────────────────────────────────

@login_required
def homepagetat_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.HomepageStat.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Homepage Stat',
        'model_name_plural': 'Homepage Stats',
        'create_url': 'public_cms:cms_homepagestat_create',
        'edit_url': 'public_cms:cms_homepagestat_edit',
        'delete_url': 'public_cms:cms_homepagestat_delete',
        'list_fields': ['label', 'value', 'order', 'is_active'],
    })


@login_required
def homepagestat_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.HomepageStatForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Homepage Stat "{obj}" was created by {request.user.full_name}.',
            content_type_label='homepagestat',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Homepage Stat Created',
            message=f'Homepage Stat "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_homepagestat_list',
            category='system',
        )
        messages.success(request, 'Homepage stat created.')
        return redirect('public_cms:cms_homepagestat_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Homepage Stat',
        'list_url': 'public_cms:cms_homepagestat_list',
    })


@login_required
def homepagestat_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.HomepageStat, pk=pk)
    form = forms.HomepageStatForm(request.POST or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Homepage Stat "{obj}" was updated by {request.user.full_name}.',
            content_type_label='homepagestat',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Homepage Stat Updated',
            message=f'Homepage Stat "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_homepagestat_list',
            category='system',
        )
        messages.success(request, 'Homepage stat updated.')
        return redirect('public_cms:cms_homepagestat_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Homepage Stat',
        'list_url': 'public_cms:cms_homepagestat_list',
        'delete_url': 'public_cms:cms_homepagestat_delete',
    })


@login_required
def homepagestat_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.HomepageStat, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Homepage Stat "{name}" was deleted by {request.user.full_name}.',
            content_type_label='homepagestat',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Homepage Stat Deleted',
            message=f'Homepage Stat "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_homepagestat_list',
            category='system',
        )
        messages.success(request, 'Homepage stat deleted.')
        return redirect('public_cms:cms_homepagestat_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Homepage Stat',
        'list_url': 'public_cms:cms_homepagestat_list',
    })


# ── HomepageHighlight CRUD ───────────────────────────────────────────────────

@login_required
def homepagehighlight_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.HomepageHighlight.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Homepage Highlight',
        'model_name_plural': 'Homepage Highlights',
        'create_url': 'public_cms:cms_homepagehighlight_create',
        'edit_url': 'public_cms:cms_homepagehighlight_edit',
        'delete_url': 'public_cms:cms_homepagehighlight_delete',
        'list_fields': ['highlight_type', 'content_object', 'order', 'is_active'],
    })


@login_required
def homepagehighlight_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.HomepageHighlightForm(request.POST or None)
    if form.is_valid():
        highlight = form.save(commit=False)
        highlight.order = (models.HomepageHighlight.objects.aggregate(
            max_order=Max('order')
        )['max_order'] or 0) + 1
        highlight.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Homepage Highlight "{highlight}" was created by {request.user.full_name}.',
            content_type_label='homepagehighlight',
            object_id=highlight.pk,
            object_repr=str(highlight),
            request=request,
        )
        notify_admins(
            title='Homepage Highlight Created',
            message=f'Homepage Highlight "{highlight}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_homepagehighlight_list',
            category='system',
        )
        messages.success(request, 'Homepage highlight created.')
        return redirect('public_cms:cms_homepagehighlight_list')
    return render(request, 'cms/highlight_form.html', {
        'form': form,
        'model_name': 'Homepage Highlight',
        'list_url': 'public_cms:cms_homepagehighlight_list',
    })


@login_required
def homepagehighlight_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.HomepageHighlight, pk=pk)
    form = forms.HomepageHighlightForm(request.POST or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Homepage Highlight "{obj}" was updated by {request.user.full_name}.',
            content_type_label='homepagehighlight',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Homepage Highlight Updated',
            message=f'Homepage Highlight "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_homepagehighlight_list',
            category='system',
        )
        messages.success(request, 'Homepage highlight updated.')
        return redirect('public_cms:cms_homepagehighlight_list')
    return render(request, 'cms/highlight_form.html', {
        'form': form,
        'model_name': 'Homepage Highlight',
        'list_url': 'public_cms:cms_homepagehighlight_list',
        'delete_url': 'public_cms:cms_homepagehighlight_delete',
    })


@login_required
def homepagehighlight_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.HomepageHighlight, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Homepage Highlight "{name}" was deleted by {request.user.full_name}.',
            content_type_label='homepagehighlight',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Homepage Highlight Deleted',
            message=f'Homepage Highlight "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_homepagehighlight_list',
            category='system',
        )
        messages.success(request, 'Homepage highlight deleted.')
        return redirect('public_cms:cms_homepagehighlight_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Homepage Highlight',
        'list_url': 'public_cms:cms_homepagehighlight_list',
    })


# ── About Page Editor ────────────────────────────────────────────────────────

_DEFAULT_ABOUT_CONTENT = """\
<p>The Smart Systems Engineering (SSE Lab) at Auburn University is a leading research group focused on developing intelligent technologies for precision agriculture and sustainable food systems.</p>
<p>Our interdisciplinary team brings together expertise in mechanical engineering, computer science, electrical engineering, and plant science to tackle complex challenges at the intersection of technology and agriculture.</p>
<h2>Research Areas</h2>
<ul>
  <li>Smart sensor networks and IoT for crop monitoring</li>
  <li>Autonomous robotic systems for agriculture</li>
  <li>Machine learning and computer vision for plant phenotyping</li>
  <li>Controlled environment agriculture and greenhouse automation</li>
</ul>
<h2>Our Facilities</h2>
<p>The lab is housed within the Samuel Ginn College of Engineering at Auburn University, with access to state-of-the-art research greenhouses, field stations, and fabrication facilities.</p>
"""


@login_required
def aboutpage_edit_view(request):
    """Edit the single About page content (page='about', section='main')."""
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item, created = models.PageSection.objects.get_or_create(
        page='about', section='main',
        defaults={'title': 'About the Lab', 'content': _DEFAULT_ABOUT_CONTENT, 'is_active': True},
    )
    if not created and not item.content:
        item.content = _DEFAULT_ABOUT_CONTENT
        item.save()
    form = forms.AboutPageForm(request.POST or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'About Page "{obj}" was updated by {request.user.full_name}.',
            content_type_label='aboutpage',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='About Page Updated',
            message=f'About Page "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:dashboard',
            category='system',
        )
        messages.success(request, 'About page updated.')
        return redirect('public_cms:cms_aboutpage_edit')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'About Page',
        'list_url': 'public_cms:dashboard',
    })


# ── DataResource CRUD ────────────────────────────────────────────────────────

@login_required
def dataresource_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.DataResource.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Data Resource',
        'model_name_plural': 'Data Resources',
        'create_url': 'public_cms:cms_dataresource_create',
        'edit_url': 'public_cms:cms_dataresource_edit',
        'delete_url': 'public_cms:cms_dataresource_delete',
        'list_fields': ['title', 'resource_type', 'order', 'is_active'],
    })


@login_required
def dataresource_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.DataResourceForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Data Resource "{obj}" was created by {request.user.full_name}.',
            content_type_label='dataresource',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Data Resource Created',
            message=f'Data Resource "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_dataresource_list',
            category='system',
        )
        messages.success(request, 'Data resource created.')
        return redirect('public_cms:cms_dataresource_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Data Resource',
        'list_url': 'public_cms:cms_dataresource_list',
    })


@login_required
def dataresource_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.DataResource, pk=pk)
    form = forms.DataResourceForm(request.POST or None, request.FILES or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Data Resource "{obj}" was updated by {request.user.full_name}.',
            content_type_label='dataresource',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Data Resource Updated',
            message=f'Data Resource "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_dataresource_list',
            category='system',
        )
        messages.success(request, 'Data resource updated.')
        return redirect('public_cms:cms_dataresource_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Data Resource',
        'list_url': 'public_cms:cms_dataresource_list',
        'delete_url': 'public_cms:cms_dataresource_delete',
    })


@login_required
def dataresource_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.DataResource, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Data Resource "{name}" was deleted by {request.user.full_name}.',
            content_type_label='dataresource',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Data Resource Deleted',
            message=f'Data Resource "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_dataresource_list',
            category='system',
        )
        messages.success(request, 'Data resource deleted.')
        return redirect('public_cms:cms_dataresource_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Data Resource',
        'list_url': 'public_cms:cms_dataresource_list',
    })


# ── JobOpening CRUD ──────────────────────────────────────────────────────────

@login_required
def jobopening_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.JobOpening.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Job Opening',
        'model_name_plural': 'Job Openings',
        'create_url': 'public_cms:cms_jobopening_create',
        'edit_url': 'public_cms:cms_jobopening_edit',
        'delete_url': 'public_cms:cms_jobopening_delete',
        'list_fields': ['title', 'status', 'order', 'is_active'],
    })


@login_required
def jobopening_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.JobOpeningForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Job Opening "{obj}" was created by {request.user.full_name}.',
            content_type_label='jobopening',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Job Opening Created',
            message=f'Job Opening "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_jobopening_list',
            category='system',
        )
        messages.success(request, 'Job opening created.')
        return redirect('public_cms:cms_jobopening_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Job Opening',
        'list_url': 'public_cms:cms_jobopening_list',
    })


@login_required
def jobopening_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.JobOpening, pk=pk)
    form = forms.JobOpeningForm(request.POST or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Job Opening "{obj}" was updated by {request.user.full_name}.',
            content_type_label='jobopening',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Job Opening Updated',
            message=f'Job Opening "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_jobopening_list',
            category='system',
        )
        messages.success(request, 'Job opening updated.')
        return redirect('public_cms:cms_jobopening_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Job Opening',
        'list_url': 'public_cms:cms_jobopening_list',
        'delete_url': 'public_cms:cms_jobopening_delete',
    })


@login_required
def jobopening_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.JobOpening, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Job Opening "{name}" was deleted by {request.user.full_name}.',
            content_type_label='jobopening',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Job Opening Deleted',
            message=f'Job Opening "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_jobopening_list',
            category='system',
        )
        messages.success(request, 'Job opening deleted.')
        return redirect('public_cms:cms_jobopening_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Job Opening',
        'list_url': 'public_cms:cms_jobopening_list',
    })


# ── Sponsor CRUD ─────────────────────────────────────────────────────────────

@login_required
def sponsor_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.Sponsor.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Sponsor',
        'model_name_plural': 'Sponsors',
        'create_url': 'public_cms:cms_sponsor_create',
        'edit_url': 'public_cms:cms_sponsor_edit',
        'delete_url': 'public_cms:cms_sponsor_delete',
        'list_fields': ['name', 'partner_type', 'order', 'is_active'],
    })


@login_required
def sponsor_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.SponsorForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Sponsor "{obj}" was created by {request.user.full_name}.',
            content_type_label='sponsor',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Sponsor Created',
            message=f'Sponsor "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_sponsor_list',
            category='system',
        )
        messages.success(request, 'Sponsor created.')
        return redirect('public_cms:cms_sponsor_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Sponsor',
        'list_url': 'public_cms:cms_sponsor_list',
    })


@login_required
def sponsor_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.Sponsor, pk=pk)
    form = forms.SponsorForm(request.POST or None, request.FILES or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Sponsor "{obj}" was updated by {request.user.full_name}.',
            content_type_label='sponsor',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Sponsor Updated',
            message=f'Sponsor "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_sponsor_list',
            category='system',
        )
        messages.success(request, 'Sponsor updated.')
        return redirect('public_cms:cms_sponsor_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Sponsor',
        'list_url': 'public_cms:cms_sponsor_list',
        'delete_url': 'public_cms:cms_sponsor_delete',
    })


@login_required
def sponsor_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.Sponsor, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Sponsor "{name}" was deleted by {request.user.full_name}.',
            content_type_label='sponsor',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Sponsor Deleted',
            message=f'Sponsor "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_sponsor_list',
            category='system',
        )
        messages.success(request, 'Sponsor deleted.')
        return redirect('public_cms:cms_sponsor_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Sponsor',
        'list_url': 'public_cms:cms_sponsor_list',
    })


# ── ContactBlock CRUD ────────────────────────────────────────────────────────

@login_required
def contactblock_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.ContactBlock.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Contact Block',
        'model_name_plural': 'Contact Blocks',
        'create_url': 'public_cms:cms_contactblock_create',
        'edit_url': 'public_cms:cms_contactblock_edit',
        'delete_url': 'public_cms:cms_contactblock_delete',
        'list_fields': ['label', 'icon', 'order', 'is_active'],
    })


@login_required
def contactblock_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.ContactBlockForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Contact Block "{obj}" was created by {request.user.full_name}.',
            content_type_label='contactblock',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Contact Block Created',
            message=f'Contact Block "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_contactblock_list',
            category='system',
        )
        messages.success(request, 'Contact block created.')
        return redirect('public_cms:cms_contactblock_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Contact Block',
        'list_url': 'public_cms:cms_contactblock_list',
    })


@login_required
def contactblock_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.ContactBlock, pk=pk)
    form = forms.ContactBlockForm(request.POST or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Contact Block "{obj}" was updated by {request.user.full_name}.',
            content_type_label='contactblock',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Contact Block Updated',
            message=f'Contact Block "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_contactblock_list',
            category='system',
        )
        messages.success(request, 'Contact block updated.')
        return redirect('public_cms:cms_contactblock_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Contact Block',
        'list_url': 'public_cms:cms_contactblock_list',
        'delete_url': 'public_cms:cms_contactblock_delete',
    })


@login_required
def contactblock_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.ContactBlock, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Contact Block "{name}" was deleted by {request.user.full_name}.',
            content_type_label='contactblock',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Contact Block Deleted',
            message=f'Contact Block "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_contactblock_list',
            category='system',
        )
        messages.success(request, 'Contact block deleted.')
        return redirect('public_cms:cms_contactblock_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Contact Block',
        'list_url': 'public_cms:cms_contactblock_list',
    })


# ── Page Section CRUD ────────────────────────────────────────────────────────

@login_required
def pagesection_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.PageSection.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Page Section',
        'model_name_plural': 'Page Sections',
        'create_url': 'public_cms:cms_pagesection_create',
        'edit_url': 'public_cms:cms_pagesection_edit',
        'delete_url': 'public_cms:cms_pagesection_delete',
        'list_fields': ['page', 'section', 'title', 'is_active'],
    })


@login_required
def pagesection_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.PageSectionForm(request.POST or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Page Section "{obj}" was created by {request.user.full_name}.',
            content_type_label='pagesection',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Page Section Created',
            message=f'Page Section "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_pagesection_list',
            category='system',
        )
        messages.success(request, 'Page section created.')
        return redirect('public_cms:cms_pagesection_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Page Section',
        'list_url': 'public_cms:cms_pagesection_list',
    })


@login_required
def pagesection_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.PageSection, pk=pk)
    form = forms.PageSectionForm(request.POST or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Page Section "{obj}" was updated by {request.user.full_name}.',
            content_type_label='pagesection',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Page Section Updated',
            message=f'Page Section "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_pagesection_list',
            category='system',
        )
        messages.success(request, 'Page section updated.')
        return redirect('public_cms:cms_pagesection_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Page Section',
        'list_url': 'public_cms:cms_pagesection_list',
        'delete_url': 'public_cms:cms_pagesection_delete',
    })


@login_required
def pagesection_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.PageSection, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Page Section "{name}" was deleted by {request.user.full_name}.',
            content_type_label='pagesection',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Page Section Deleted',
            message=f'Page Section "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_pagesection_list',
            category='system',
        )
        messages.success(request, 'Page section deleted.')
        return redirect('public_cms:cms_pagesection_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Page Section',
        'list_url': 'public_cms:cms_pagesection_list',
    })


# ── Contact Messages (read-only + delete) ────────────────────────────────────

@login_required
def contactmessage_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.ContactMessage.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Contact Message',
        'model_name_plural': 'Contact Messages',
        'detail_url': 'public_cms:cms_contactmessage_detail',
        'delete_url': 'public_cms:cms_contactmessage_delete',
        'list_fields': ['name', 'email', 'subject', 'created_at'],
    })


@login_required
def contactmessage_detail_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.ContactMessage, pk=pk)
    return render(request, 'cms/detail.html', {
        'item': item,
        'model_name': 'Contact Message',
        'list_url': 'public_cms:cms_contactmessage_list',
        'delete_url': 'public_cms:cms_contactmessage_delete',
        'fields': [
            ('Name', item.name),
            ('Email', item.email),
            ('Subject', item.subject),
            ('Message', item.message),
            ('Received', item.created_at.strftime('%b %d, %Y %I:%M %p') if item.created_at else '—'),
        ],
    })


@login_required
def contactmessage_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.ContactMessage, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Contact Message "{name}" was deleted by {request.user.full_name}.',
            content_type_label='contactmessage',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Contact Message Deleted',
            message=f'Contact Message "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_contactmessage_list',
            category='system',
        )
        messages.success(request, 'Contact message deleted.')
        return redirect('public_cms:cms_contactmessage_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Contact Message',
        'list_url': 'public_cms:cms_contactmessage_list',
    })


# ── Alumni CRUD ──────────────────────────────────────────────────────────────

@login_required
def alumni_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    items = models.Alumni.objects.all()
    return render(request, 'cms/list.html', {
        'items': items,
        'model_name': 'Alumnus',
        'model_name_plural': 'Alumni',
        'create_url': 'public_cms:cms_alumni_create',
        'edit_url': 'public_cms:cms_alumni_edit',
        'delete_url': 'public_cms:cms_alumni_delete',
        'list_fields': ['name', 'position', 'start_date', 'end_date', 'current_affiliation', 'is_active'],
    })


@login_required
def alumni_create_view(request):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    form = forms.AlumniForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_CREATED',
            description=f'Alumnus "{obj}" was created by {request.user.full_name}.',
            content_type_label='alumni',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Alumnus Created',
            message=f'Alumnus "{obj}" was created by {request.user.full_name}.',
            level='success',
            link='public_cms:cms_alumni_list',
            category='system',
        )
        messages.success(request, 'Alumnus created.')
        return redirect('public_cms:cms_alumni_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Alumnus',
        'list_url': 'public_cms:cms_alumni_list',
    })


@login_required
def alumni_edit_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.Alumni, pk=pk)
    form = forms.AlumniForm(request.POST or None, request.FILES or None, instance=item)
    if form.is_valid():
        obj = form.save()
        log_activity(
            actor=request.user,
            action='CMS_UPDATED',
            description=f'Alumnus "{obj}" was updated by {request.user.full_name}.',
            content_type_label='alumni',
            object_id=obj.pk,
            object_repr=str(obj),
            request=request,
        )
        notify_admins(
            title='Alumnus Updated',
            message=f'Alumnus "{obj}" was updated by {request.user.full_name}.',
            level='info',
            link='public_cms:cms_alumni_list',
            category='system',
        )
        messages.success(request, 'Alumnus updated.')
        return redirect('public_cms:cms_alumni_list')
    return render(request, 'cms/form.html', {
        'form': form,
        'model_name': 'Alumnus',
        'list_url': 'public_cms:cms_alumni_list',
        'delete_url': 'public_cms:cms_alumni_delete',
    })


@login_required
def alumni_delete_view(request, pk):
    if not _is_admin(request.user):
        messages.error(request, 'Admin access required.')
        return redirect('dashboard:home')
    item = get_object_or_404(models.Alumni, pk=pk)
    if request.method == 'POST':
        name = str(item)
        pk_val = item.pk
        item.delete()
        log_activity(
            actor=request.user,
            action='CMS_DELETED',
            description=f'Alumnus "{name}" was deleted by {request.user.full_name}.',
            content_type_label='alumni',
            object_id=pk_val,
            object_repr=name,
            request=request,
        )
        notify_admins(
            title='Alumnus Deleted',
            message=f'Alumnus "{name}" was deleted by {request.user.full_name}.',
            level='warning',
            link='public_cms:cms_alumni_list',
            category='system',
        )
        messages.success(request, 'Alumnus deleted.')
        return redirect('public_cms:cms_alumni_list')
    return render(request, 'cms/confirm_delete.html', {
        'item': item,
        'model_name': 'Alumnus',
        'list_url': 'public_cms:cms_alumni_list',
    })
