"""
Signal handlers for the incidents app.

- When a HIGH or CRITICAL severity IncidentReport is created or updated,
  update the related equipment's condition to DAMAGED.

NOTE: Notifications are handled in incident_create_view to avoid duplicates.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.incidents.models import IncidentReport


@receiver(post_save, sender=IncidentReport)
def update_equipment_condition_on_incident(sender, instance, created, **kwargs):
    """
    If a HIGH or CRITICAL incident is reported (or updated to that severity),
    mark the equipment condition as DAMAGED.
    """
    if instance.severity not in ('HIGH', 'CRITICAL'):
        return

    equipment = instance.equipment

    if equipment.condition != 'DAMAGED':
        equipment.condition = 'DAMAGED'
        equipment.save(update_fields=['condition', 'updated_at'])
