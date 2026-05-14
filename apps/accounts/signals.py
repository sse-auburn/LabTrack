"""
Signal handlers for the accounts app.
Auto-creates a UserProfile whenever a new CustomUser is created.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import CustomUser, UserProfile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a UserProfile when a new CustomUser is created."""
    if created:
        UserProfile.objects.create(user=instance)


