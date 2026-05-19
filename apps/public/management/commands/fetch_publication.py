"""Management command to fetch publication metadata from Crossref via DOI."""

import urllib.request
import urllib.error
import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.public.models import Publication


CROSSREF_URL = "https://api.crossref.org/works/{doi}"


def fetch_crossref(doi):
    """Fetch metadata from Crossref for a given DOI. Returns dict or None."""
    url = CROSSREF_URL.format(doi=doi)
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'SSELabTrack/1.0 (mailto:labtrack.sse@gmail.com)',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('message', {})
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None


def parse_crossref(message):
    """Parse Crossref message into a dict of Publication fields."""
    authors = []
    for author in message.get('author', []):
        given = author.get('given', '')
        family = author.get('family', '')
        if given and family:
            authors.append(f"{given} {family}")
        elif family:
            authors.append(family)
    authors_str = ', '.join(authors)

    # Container title (journal)
    container = message.get('container-title', [])
    journal = container[0] if container else ''

    # Published date
    published = message.get('published-print') or message.get('published-online') or message.get('published', {})
    date_parts = published.get('date-parts', [[]])[0]
    year = date_parts[0] if date_parts else None

    # Pages
    page = message.get('page', '')

    # URL
    url = message.get('URL', '')

    # Abstract (some Crossref entries have this)
    abstract = message.get('abstract', '')
    # Strip JATS tags if present
    if abstract:
        abstract = abstract.replace('<jats:p>', '').replace('</jats:p>', '').replace('<jats:abstract>', '').replace('</jats:abstract>', '').strip()

    return {
        'title': message.get('title', [''])[0] if isinstance(message.get('title'), list) else message.get('title', ''),
        'authors': authors_str,
        'journal': journal,
        'year': year,
        'volume': message.get('volume', ''),
        'issue': message.get('issue', ''),
        'pages': page,
        'abstract': abstract,
        'url': url,
    }


class Command(BaseCommand):
    help = 'Fetch publication metadata from Crossref by DOI.'

    def add_arguments(self, parser):
        parser.add_argument('doi', nargs='+', help='One or more DOIs to fetch')
        parser.add_argument(
            '--create',
            action='store_true',
            help='Create new Publication records instead of updating existing ones',
        )

    def handle(self, *args, **options):
        dois = options['doi']
        create = options['create']

        for doi in dois:
            doi = doi.strip()
            if doi.startswith('http'):
                # Extract DOI from URL if full URL given
                doi = doi.split('doi.org/')[-1]

            self.stdout.write(f"Fetching: {doi}")
            message = fetch_crossref(doi)
            if not message:
                self.stdout.write(self.style.ERROR(f"  Failed to fetch metadata for {doi}"))
                continue

            data = parse_crossref(message)

            if create:
                pub, created = Publication.objects.get_or_create(
                    doi=doi,
                    defaults={**data, 'fetched_at': timezone.now()},
                )
                if not created:
                    for key, value in data.items():
                        setattr(pub, key, value)
                    pub.fetched_at = timezone.now()
                    pub.save()
                    self.stdout.write(self.style.SUCCESS(f"  Updated: {pub.title}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"  Created: {pub.title}"))
            else:
                # Try to find existing publication by DOI
                try:
                    pub = Publication.objects.get(doi=doi)
                    for key, value in data.items():
                        setattr(pub, key, value)
                    pub.fetched_at = timezone.now()
                    pub.save()
                    self.stdout.write(self.style.SUCCESS(f"  Updated: {pub.title}"))
                except Publication.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  No existing publication found for {doi}. Use --create to make one."))
