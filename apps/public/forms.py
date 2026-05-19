"""Forms for the public website CMS."""

from django import forms

from apps.public import models


# ── Shared widget styling ────────────────────────────────────────────────────

def _text_input(attrs=None):
    base = {
        'class': (
            'w-full rounded-lg border-slate-300 px-3 py-2 text-sm '
            'text-slate-800 placeholder-slate-400 '
            'focus:border-brand-500 focus:ring-brand-500 focus:ring-1 '
            'transition shadow-sm'
        ),
    }
    if attrs:
        base.update(attrs)
    return base


def _select(attrs=None):
    return _text_input(attrs)


def _checkbox():
    return {
        'class': (
            'rounded border-slate-300 text-brand-600 '
            'focus:ring-brand-500 transition'
        ),
    }


def _file_input():
    return {
        'class': (
            'block w-full text-sm text-slate-500 '
            'file:mr-4 file:py-2 file:px-4 file:rounded-lg '
            'file:border-0 file:text-sm file:font-medium '
            'file:bg-brand-50 file:text-brand-700 '
            'hover:file:bg-brand-100 transition cursor-pointer'
        ),
    }


def _datetime():
    return _text_input({'type': 'datetime-local'})


# ── Forms ─────────────────────────────────────────────────────────────────────

class ResearchDomainForm(forms.ModelForm):
    class Meta:
        model = models.ResearchDomain
        fields = ['name', 'description', 'icon', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs=_text_input()),
            'icon': forms.TextInput(attrs=_text_input({'placeholder': 'e.g., flask, chip, cloud'})),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class PublicationForm(forms.ModelForm):
    class Meta:
        model = models.Publication
        fields = [
            'doi', 'title', 'authors', 'journal', 'year',
            'volume', 'issue', 'pages', 'abstract', 'url',
            'pdf_file', 'is_featured',
        ]
        widgets = {
            'doi': forms.TextInput(attrs=_text_input({'placeholder': 'e.g., 10.1000/xyz123'})),
            'title': forms.TextInput(attrs=_text_input()),
            'authors': forms.Textarea(attrs={'rows': 3, 'class': _text_input()['class'], 'placeholder': 'Comma-separated or one per line'}),
            'journal': forms.TextInput(attrs=_text_input()),
            'year': forms.NumberInput(attrs=_text_input()),
            'volume': forms.TextInput(attrs=_text_input()),
            'issue': forms.TextInput(attrs=_text_input()),
            'pages': forms.TextInput(attrs=_text_input()),
            'url': forms.URLInput(attrs=_text_input({'placeholder': 'https://...'})),
            'pdf_file': forms.ClearableFileInput(attrs=_file_input()),
            'is_featured': forms.CheckboxInput(attrs=_checkbox()),
        }


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = models.BlogPost
        fields = [
            'title', 'slug', 'content', 'featured_image',
            'is_published', 'published_at', 'tags',
        ]
        widgets = {
            'title': forms.TextInput(attrs=_text_input()),
            'slug': forms.TextInput(attrs=_text_input({'placeholder': 'Auto-generated if left blank'})),
            'featured_image': forms.ClearableFileInput(attrs=_file_input()),
            'is_published': forms.CheckboxInput(attrs=_checkbox()),
            'published_at': forms.DateTimeInput(attrs=_datetime()),
            'tags': forms.TextInput(attrs=_text_input({'placeholder': 'Comma-separated tags'})),
        }


class NewsItemForm(forms.ModelForm):
    class Meta:
        model = models.NewsItem
        fields = ['title', 'content', 'image', 'published_at']
        widgets = {
            'title': forms.TextInput(attrs=_text_input()),
            'published_at': forms.DateTimeInput(attrs=_datetime()),
        }


class GalleryItemForm(forms.ModelForm):
    class Meta:
        model = models.GalleryItem
        fields = ['title', 'caption', 'image', 'video_url', 'category', 'is_featured', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs=_text_input()),
            'image': forms.ClearableFileInput(attrs=_file_input()),
            'video_url': forms.URLInput(attrs=_text_input({'placeholder': 'YouTube or other video URL'})),
            'category': forms.Select(attrs=_select()),
            'is_featured': forms.CheckboxInput(attrs=_checkbox()),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class PublicProjectForm(forms.ModelForm):
    class Meta:
        model = models.PublicProject
        fields = [
            'title', 'description', 'status', 'funding_source',
            'image', 'external_link', 'research_domains', 'members',
            'order', 'is_active',
        ]
        widgets = {
            'title': forms.TextInput(attrs=_text_input()),
            'status': forms.Select(attrs=_select()),
            'funding_source': forms.TextInput(attrs=_text_input()),
            'image': forms.ClearableFileInput(attrs=_file_input()),
            'external_link': forms.URLInput(attrs=_text_input({'placeholder': 'https://...'})),
            'research_domains': forms.SelectMultiple(attrs={**_select(), 'size': 5}),
            'members': forms.SelectMultiple(attrs={**_select(), 'size': 5}),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class HomepageStatForm(forms.ModelForm):
    class Meta:
        model = models.HomepageStat
        fields = ['label', 'value', 'order', 'is_active']
        widgets = {
            'label': forms.TextInput(attrs=_text_input()),
            'value': forms.TextInput(attrs=_text_input({'placeholder': 'e.g., 15+, 50+, 8'})),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class HomepageHighlightForm(forms.ModelForm):
    class Meta:
        model = models.HomepageHighlight
        fields = [
            'highlight_type', 'project', 'publication',
            'news_item', 'gallery_item', 'job_opening',
            'is_active',
        ]
        widgets = {
            'highlight_type': forms.Select(attrs=_select({'x-model': 'highlightType'})),
            'project': forms.Select(attrs=_select()),
            'publication': forms.Select(attrs=_select()),
            'news_item': forms.Select(attrs=_select()),
            'gallery_item': forms.Select(attrs=_select()),
            'job_opening': forms.Select(attrs=_select()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }

    def clean(self):
        cleaned = super().clean()
        htype = cleaned.get('highlight_type')
        mapping = {
            'PROJECT': 'project',
            'PUBLICATION': 'publication',
            'NEWS': 'news_item',
            'GALLERY': 'gallery_item',
            'JOB': 'job_opening',
        }
        field = mapping.get(htype)
        if field and not cleaned.get(field):
            self.add_error(field, f'Select a {htype.lower().replace("_", " ")} for this highlight.')
        # Clear unrelated FK fields so only the selected type's FK is saved
        for ft, fk in mapping.items():
            if ft != htype:
                cleaned[fk] = None
        return cleaned


class AboutPageForm(forms.ModelForm):
    """Simple editor for the About page (page='about', section='main')."""
    class Meta:
        model = models.PageSection
        fields = ['title', 'content', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs=_text_input({'placeholder': 'Page title'})),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class DataResourceForm(forms.ModelForm):
    class Meta:
        model = models.DataResource
        fields = ['title', 'description', 'resource_type', 'external_link', 'file', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs=_text_input()),
            'resource_type': forms.Select(attrs=_select()),
            'external_link': forms.URLInput(attrs=_text_input({'placeholder': 'https://...'})),
            'file': forms.ClearableFileInput(attrs=_file_input()),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class JobOpeningForm(forms.ModelForm):
    class Meta:
        model = models.JobOpening
        fields = ['title', 'description', 'requirements', 'status', 'tags', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs=_text_input()),
            'status': forms.Select(attrs=_select()),
            'tags': forms.TextInput(attrs=_text_input({'placeholder': 'Comma-separated tags'})),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class SponsorForm(forms.ModelForm):
    class Meta:
        model = models.Sponsor
        fields = ['name', 'description', 'logo', 'website_link', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs=_text_input()),
            'logo': forms.ClearableFileInput(attrs=_file_input()),
            'website_link': forms.URLInput(attrs=_text_input({'placeholder': 'https://...'})),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class ContactBlockForm(forms.ModelForm):
    class Meta:
        model = models.ContactBlock
        fields = ['label', 'value', 'icon', 'order', 'is_active']
        widgets = {
            'label': forms.TextInput(attrs=_text_input()),
            'icon': forms.Select(attrs=_select()),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class PageSectionForm(forms.ModelForm):
    class Meta:
        model = models.PageSection
        fields = ['page', 'section', 'title', 'subtitle', 'content', 'is_active', 'order']
        widgets = {
            'page': forms.Select(attrs=_select()),
            'section': forms.TextInput(attrs=_text_input({'placeholder': 'e.g., hero, intro, cta'})),
            'title': forms.TextInput(attrs=_text_input()),
            'subtitle': forms.TextInput(attrs=_text_input()),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class AlumniForm(forms.ModelForm):
    class Meta:
        model = models.Alumni
        fields = [
            'name', 'email', 'position', 'start_date', 'end_date',
            'current_affiliation', 'photo', 'bio',
            'google_scholar', 'linkedin', 'github', 'personal_website',
            'order', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs=_text_input({'placeholder': 'Full name'})),
            'email': forms.EmailInput(attrs=_text_input({'placeholder': 'email@example.com'})),
            'position': forms.Select(attrs=_select()),
            'start_date': forms.DateInput(attrs={**_text_input(), 'type': 'date'}),
            'end_date': forms.DateInput(attrs={**_text_input(), 'type': 'date'}),
            'current_affiliation': forms.TextInput(attrs=_text_input({'placeholder': 'Current job or university'})),
            'bio': forms.Textarea(attrs={**_text_input(), 'rows': 4, 'placeholder': 'Short bio...'}),
            'google_scholar': forms.URLInput(attrs=_text_input()),
            'linkedin': forms.URLInput(attrs=_text_input()),
            'github': forms.URLInput(attrs=_text_input()),
            'personal_website': forms.URLInput(attrs=_text_input()),
            'order': forms.NumberInput(attrs=_text_input()),
            'is_active': forms.CheckboxInput(attrs=_checkbox()),
        }


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = models.ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs=_text_input({'placeholder': 'Your full name'})),
            'email': forms.EmailInput(attrs=_text_input({'placeholder': 'you@example.com'})),
            'subject': forms.TextInput(attrs=_text_input({'placeholder': 'What is this about?'})),
            'message': forms.Textarea(attrs={**_text_input(), 'rows': 5, 'placeholder': 'Write your message here...'}),
        }
