"""
Management command: fix_category_colors

Assigns unique hex colors to any category that:
  - has no color (empty string)
  - is black (#000000, the browser picker default)
  - shares its color with another category

Run manually:
    python manage.py fix_category_colors
"""

from collections import Counter

from django.core.management.base import BaseCommand

from apps.equipment.models import Category
from apps.equipment.utils import generate_unique_color


class Command(BaseCommand):
    help = 'Assign unique colors to categories that are black, empty, or share a color.'

    def handle(self, *args, **options):
        categories = list(Category.objects.all())

        if not categories:
            self.stdout.write(self.style.SUCCESS('No categories found.'))
            return

        color_counts = Counter(cat.color for cat in categories)

        # Colors already used by exactly one category that are neither empty nor black.
        good_colors = {
            color for color, count in color_counts.items()
            if count == 1 and color and color != '#000000'
        }

        to_fix = [
            cat for cat in categories
            if not cat.color or cat.color == '#000000' or color_counts[cat.color] > 1
        ]

        if not to_fix:
            self.stdout.write(self.style.SUCCESS('All category colors are already unique.'))
            return

        used = set(good_colors)
        fixed = 0
        for cat in to_fix:
            old_color = cat.color or '(none)'
            new_color = generate_unique_color(used)
            cat.color = new_color
            cat.save(update_fields=['color'])
            used.add(new_color)
            fixed += 1
            self.stdout.write(f'  {cat.name}: {old_color} -> {new_color}')

        self.stdout.write(self.style.SUCCESS(f'Fixed {fixed} category color(s).'))
