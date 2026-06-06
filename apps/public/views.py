"""Public-facing lab website views (no login required)."""

from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from apps.accounts.models import CustomUser
from apps.public import forms, models


# ── Helpers ──────────────────────────────────────────────────────────────────

def _page_sections(page):
    """Fetch active PageSections for a given page as a dict keyed by section."""
    return {
        s.section: s
        for s in models.PageSection.objects.filter(page=page, is_active=True).order_by('order')
    }


# ── Homepage ─────────────────────────────────────────────────────────────────

def home_view(request):
    stats = models.HomepageStat.objects.filter(is_active=True)
    highlights = models.HomepageHighlight.objects.filter(is_active=True).select_related(
        'project', 'publication', 'news_item', 'job_opening'
    ).order_by('order')
    funding_partners = models.Sponsor.objects.filter(is_active=True, partner_type='FUNDING').order_by('order')
    collaborative_partners = models.Sponsor.objects.filter(is_active=True, partner_type='COLLABORATION').order_by('order')
    return render(request, 'public/home.html', {
        'stats': stats,
        'highlights': highlights,
        'funding_partners': funding_partners,
        'collaborative_partners': collaborative_partners,
        'page_sections': _page_sections('home'),
    })


# ── Static-ish pages ─────────────────────────────────────────────────────────

def about_view(request):
    funding_partners = models.Sponsor.objects.filter(is_active=True, partner_type='FUNDING').order_by('order')
    collaborative_partners = models.Sponsor.objects.filter(is_active=True, partner_type='COLLABORATION').order_by('order')
    return render(request, 'public/about.html', {
        'funding_partners': funding_partners,
        'collaborative_partners': collaborative_partners,
        'page_sections': _page_sections('about'),
    })


def projects_view(request):
    projects = models.PublicProject.objects.filter(is_active=True)
    domains = models.ResearchDomain.objects.filter(is_active=True)
    return render(request, 'public/projects.html', {
        'projects': projects,
        'domains': domains,
        'page_sections': _page_sections('projects'),
    })


def data_view(request):
    resources = models.DataResource.objects.filter(is_active=True)
    return render(request, 'public/data.html', {
        'resources': resources,
        'page_sections': _page_sections('data'),
    })


def jobs_view(request):
    jobs = models.JobOpening.objects.filter(is_active=True)
    return render(request, 'public/jobs.html', {
        'jobs': jobs,
        'page_sections': _page_sections('jobs'),
    })


def sponsors_view(request):
    funding_partners = models.Sponsor.objects.filter(is_active=True, partner_type='FUNDING').order_by('order')
    collaborative_partners = models.Sponsor.objects.filter(is_active=True, partner_type='COLLABORATION').order_by('order')
    return render(request, 'public/sponsors.html', {
        'funding_partners': funding_partners,
        'collaborative_partners': collaborative_partners,
    })


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def contact_view(request):
    from apps.notifications.utils import notify_admins
    blocks = models.ContactBlock.objects.filter(is_active=True)
    form = forms.ContactMessageForm(request.POST or None)
    sent = False
    if request.method == 'POST' and form.is_valid():
        msg = form.save(commit=False)
        msg.ip_address = _get_client_ip(request)
        msg.user_agent = request.META.get('HTTP_USER_AGENT', '')
        msg.save()
        notify_admins(
            title=f"New Contact Message: {msg.subject}",
            message=(
                f"From: {msg.name} ({msg.email})\n\n"
                f"{msg.message}\n\n"
                f"---\n"
                f"IP Address: {msg.ip_address or 'unknown'}\n"
                f"Device: {msg.user_agent or 'unknown'}"
            ),
            level='info',
            link='/admin/cms/',
            category='system',
            send_email=True,
        )
        sent = True
        form = forms.ContactMessageForm()
    return render(request, 'public/contact.html', {
        'blocks': blocks,
        'form': form,
        'sent': sent,
        'page_sections': _page_sections('contact'),
    })


# ── Team & Alumni ────────────────────────────────────────────────────────────

def team_view(request):
    """Show active lab members grouped by position, plus alumni."""
    members = CustomUser.objects.filter(
        is_active=True,
    ).select_related('profile').prefetch_related('profile__research_domains')

    # Separate PI from other members
    pi_users = []
    other_members = []
    for m in members:
        try:
            if m.profile.position == 'PI':
                pi_users.append(m)
            else:
                other_members.append(m)
        except CustomUser.profile.RelatedObjectDoesNotExist:
            other_members.append(m)

    # Sort remaining members by position
    position_order = {
        'POSTDOC': 0,
        'PHD': 1,
        'MS': 2,
        'UNDERGRAD': 3,
        'STAFF': 4,
        'VISITOR': 5,
    }

    def _position_key(m):
        try:
            return position_order.get(m.profile.position, 99)
        except CustomUser.profile.RelatedObjectDoesNotExist:
            return 99

    other_members = sorted(other_members, key=_position_key)

    position_labels = {
        'POSTDOC': 'Postdoctoral Researchers',
        'PHD': 'Ph.D. Students',
        'MS': 'M.S. Students',
        'UNDERGRAD': 'Undergraduate Students',
        'STAFF': 'Research Staff',
        'VISITOR': 'Visiting Researchers',
    }

    # Fetch alumni from inactive users + Alumni model
    alumni_users = CustomUser.objects.filter(
        is_active=False,
    ).select_related('profile').order_by('-date_joined')
    for user in alumni_users:
        if not hasattr(user, 'profile'):
            from apps.accounts.models import UserProfile
            UserProfile.objects.get_or_create(user=user)

    alumni_records = models.Alumni.objects.filter(is_active=True).order_by('order', 'name')

    return render(request, 'public/team.html', {
        'pi_users': pi_users,
        'members': other_members,
        'position_order': position_order,
        'position_labels': position_labels,
        'alumni_users': alumni_users,
        'alumni_records': alumni_records,
    })


def alumni_view(request):
    """Show former lab members (inactive accounts)."""
    alumni = CustomUser.objects.filter(
        is_active=False,
    ).select_related('profile').order_by('-date_joined')
    # Ensure all alumni have profiles
    for user in alumni:
        if not hasattr(user, 'profile'):
            from apps.accounts.models import UserProfile
            UserProfile.objects.get_or_create(user=user)
    return render(request, 'public/alumni.html', {'alumni': alumni})


# ── Publications ─────────────────────────────────────────────────────────────

def publications_view(request):
    """List all publications, filterable by year."""
    year = request.GET.get('year')
    publications = models.Publication.objects.all()
    if year:
        publications = publications.filter(year=year)
    years = models.Publication.objects.exclude(year__isnull=True).values_list('year', flat=True).distinct().order_by('-year')
    return render(request, 'public/publications.html', {
        'publications': publications,
        'years': years,
        'selected_year': year,
    })


def publication_detail_view(request, pk):
    pub = get_object_or_404(models.Publication, pk=pk)
    return render(request, 'public/publication_detail.html', {'publication': pub})


# ── Blog ─────────────────────────────────────────────────────────────────────

def blog_view(request):
    """List published blog posts."""
    posts = models.BlogPost.objects.filter(is_published=True)
    tag = request.GET.get('tag')
    if tag:
        posts = posts.filter(tags__icontains=tag)
    return render(request, 'public/blog.html', {
        'posts': posts,
        'tag': tag,
    })


def blog_detail_view(request, slug):
    post = get_object_or_404(models.BlogPost, slug=slug, is_published=True)
    return render(request, 'public/blog_detail.html', {'post': post})


# ── News ─────────────────────────────────────────────────────────────────────

def news_view(request):
    """List news announcements."""
    items = models.NewsItem.objects.all()
    return render(request, 'public/news.html', {'items': items})


def news_detail_view(request, pk):
    """Detail page for a single news item."""
    item = get_object_or_404(models.NewsItem, pk=pk)
    return render(request, 'public/news_detail.html', {'item': item})



