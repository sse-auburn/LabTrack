"""CMS-style models for the public lab website."""

from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field


class ResearchDomain(models.Model):
    """A research area or domain that the lab works in."""
    name = models.CharField(max_length=200, unique=True)
    description = CKEditor5Field(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Icon class or identifier')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class HomepageStat(models.Model):
    """Stat displayed on the homepage stats bar."""
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=50, help_text='e.g., "15+", "50+", "8"')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.value} {self.label}"


class AboutSection(models.Model):
    """Section on the About Lab page."""
    title = models.CharField(max_length=200)
    content = CKEditor5Field()
    image = models.ImageField(upload_to='public/about/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class PublicProject(models.Model):
    """Research project displayed on the public Projects page."""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
    ]

    title = models.CharField(max_length=200)
    description = CKEditor5Field()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    funding_source = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='public/projects/', blank=True, null=True)
    external_link = models.URLField(blank=True, help_text='Link to project page or publication')
    research_domains = models.ManyToManyField(ResearchDomain, blank=True, related_name='projects')
    members = models.ManyToManyField(
        'accounts.CustomUser',
        blank=True,
        related_name='public_projects',
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class DataResource(models.Model):
    """Publication, dataset, or software tool on the Data page."""
    TYPE_CHOICES = [
        ('PUBLICATION', 'Publication'),
        ('DATASET', 'Dataset'),
        ('SOFTWARE', 'Software'),
        ('TOOL', 'Tool'),
    ]

    title = models.CharField(max_length=200)
    description = CKEditor5Field(blank=True)
    resource_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='PUBLICATION')
    external_link = models.URLField(blank=True)
    file = models.FileField(upload_to='public/data/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class JobOpening(models.Model):
    """Job posting on the Job Openings page."""
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('FILLED', 'Filled'),
    ]

    title = models.CharField(max_length=200)
    description = CKEditor5Field()
    requirements = CKEditor5Field(blank=True, help_text='Qualifications, skills, etc.')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    tags = models.CharField(max_length=200, blank=True, help_text='Comma-separated tags')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class Sponsor(models.Model):
    """Lab sponsor or partner."""
    name = models.CharField(max_length=200)
    description = CKEditor5Field(blank=True)
    logo = models.ImageField(upload_to='public/sponsors/', blank=True, null=True)
    website_link = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class ContactBlock(models.Model):
    """Contact info block (email, address, phone, etc.)."""
    ICON_CHOICES = [
        ('location', 'Location / Address'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('website', 'Website'),
        ('clock', 'Office Hours'),
    ]

    label = models.CharField(max_length=100)
    value = CKEditor5Field(help_text='Use line breaks for multi-line values')
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='location')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.label


class Publication(models.Model):
    """A publication with optional DOI auto-fetch from Crossref."""
    doi = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        unique=True,
        help_text='Enter a DOI to auto-fetch metadata (e.g., 10.1000/xyz123)',
    )
    title = models.CharField(max_length=500, blank=True)
    authors = models.TextField(blank=True, help_text='Comma-separated or one per line')
    journal = models.CharField(max_length=300, blank=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=100, blank=True)
    abstract = CKEditor5Field(blank=True)
    url = models.URLField(blank=True, help_text='Direct link to the publication')
    pdf_file = models.FileField(upload_to='public/publications/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    fetched_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', '-created_at']

    def __str__(self):
        return self.title or f"Publication {self.pk}"


class BlogPost(models.Model):
    """A blog post authored by lab members."""
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    content = CKEditor5Field()
    author = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='blog_posts',
    )
    featured_image = models.ImageField(upload_to='public/blog/', blank=True, null=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    tags = models.CharField(max_length=300, blank=True, help_text='Comma-separated tags')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class NewsItem(models.Model):
    """A short news announcement or update."""
    title = models.CharField(max_length=300)
    content = CKEditor5Field()
    is_pinned = models.BooleanField(default=False, help_text='Pin to top of the news feed')
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True, help_text='Optional expiration date')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-published_at', '-created_at']

    def __str__(self):
        return self.title


class GalleryItem(models.Model):
    """A photo or video in the lab gallery."""
    CATEGORY_CHOICES = [
        ('EVENT', 'Lab Event'),
        ('EQUIPMENT', 'Equipment'),
        ('FIELD', 'Field Work'),
        ('TEAM', 'Team'),
        ('OTHER', 'Other'),
    ]

    title = models.CharField(max_length=200)
    caption = CKEditor5Field(blank=True)
    image = models.ImageField(upload_to='public/gallery/', blank=True, null=True)
    video_url = models.URLField(blank=True, help_text='YouTube or other video link')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', 'order', '-created_at']

    def __str__(self):
        return self.title


class PageSection(models.Model):
    """Editable content sections for static pages."""

    PAGE_CHOICES = [
        ('home', 'Homepage'),
        ('about', 'About'),
        ('jobs', 'Jobs'),
        ('data', 'Data'),
        ('projects', 'Projects'),
        ('contact', 'Contact'),
    ]

    page = models.CharField(max_length=20, choices=PAGE_CHOICES)
    section = models.CharField(max_length=50, help_text='Unique key for this section, e.g. "hero", "intro"')
    title = models.CharField(max_length=300, blank=True)
    subtitle = models.CharField(max_length=300, blank=True)
    content = CKEditor5Field(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['page', 'order']
        unique_together = ['page', 'section']

    def __str__(self):
        return f"{self.get_page_display()} — {self.section}"


class ContactMessage(models.Model):
    """A message submitted via the public contact form."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    subject = models.CharField(max_length=300)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} — {self.subject}"


class HomepageHighlight(models.Model):
    """A homepage highlight that references real lab content."""
    TYPE_CHOICES = [
        ('PROJECT', 'Project'),
        ('PUBLICATION', 'Publication'),
        ('NEWS', 'News'),
        ('GALLERY', 'Gallery'),
        ('JOB', 'Job'),
    ]

    highlight_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    project = models.ForeignKey(PublicProject, on_delete=models.CASCADE, blank=True, null=True)
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, blank=True, null=True)
    news_item = models.ForeignKey(NewsItem, on_delete=models.CASCADE, blank=True, null=True)
    gallery_item = models.ForeignKey(GalleryItem, on_delete=models.CASCADE, blank=True, null=True)
    job_opening = models.ForeignKey(JobOpening, on_delete=models.CASCADE, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    @property
    def content_object(self):
        return (
            self.project or self.publication or self.news_item
            or self.gallery_item or self.job_opening
        )

    def __str__(self):
        obj = self.content_object
        return f"{self.get_highlight_type_display()} — {obj}"
