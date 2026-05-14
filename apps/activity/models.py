from django.db import models


class ActivityLog(models.Model):
    """
    A system-wide audit log entry recording actions performed by users.
    Uses simple label + id fields instead of GenericForeignKey for simplicity.
    """

    ACTION_CHOICES = [
        # Equipment
        ('EQUIPMENT_CREATED', 'Equipment Created'),
        ('EQUIPMENT_UPDATED', 'Equipment Updated'),
        ('EQUIPMENT_DELETED', 'Equipment Deleted'),
        ('EQUIPMENT_APPROVED', 'Equipment Approved'),
        ('EQUIPMENT_REJECTED', 'Equipment Rejected'),
        # Borrowing
        ('BORROW_REQUESTED', 'Borrow Requested'),
        ('BORROW_CREATED', 'Borrow Created'),
        ('BORROW_APPROVED', 'Borrow Approved'),
        ('BORROW_REJECTED', 'Borrow Rejected'),
        ('BORROW_RETURNED', 'Borrow Returned'),
        ('BORROW_OVERDUE', 'Borrow Overdue'),
        ('BORROW_RETURN_SUBMITTED', 'Borrow Return Submitted'),
        ('BORROW_DELETED', 'Borrow Deleted'),
        # Reservations
        ('RESERVATION_CREATED', 'Reservation Created'),
        ('RESERVATION_CONFIRMED', 'Reservation Confirmed'),
        ('RESERVATION_CANCELLED', 'Reservation Cancelled'),
        ('RESERVATION_RETURN_SUBMITTED', 'Reservation Return Submitted'),
        ('RESERVATION_RETURN_CONFIRMED', 'Reservation Return Confirmed'),
        ('RESERVATION_DELETED', 'Reservation Deleted'),
        ('RESERVATION_EXPIRED', 'Reservation Expired'),
        # Consumables
        ('CONSUMABLE_USED', 'Consumable Used'),
        ('CONSUMABLE_RESTOCKED', 'Consumable Restocked'),
        ('CONSUMABLE_CREATED', 'Consumable Created'),
        ('CONSUMABLE_UPDATED', 'Consumable Updated'),
        ('CONSUMABLE_DELETED', 'Consumable Deleted'),
        # Incidents
        ('INCIDENT_REPORTED', 'Incident Reported'),
        ('INCIDENT_RESOLVED', 'Incident Resolved'),
        ('INCIDENT_ASSIGNED', 'Incident Assigned'),
        ('INCIDENT_DELETED', 'Incident Deleted'),
        # Maintenance
        ('MAINTENANCE_SCHEDULED', 'Maintenance Scheduled'),
        ('MAINTENANCE_COMPLETED', 'Maintenance Completed'),
        ('MAINTENANCE_DELETED', 'Maintenance Deleted'),
        # Calibration
        ('CALIBRATION_CREATED', 'Calibration Created'),
        ('CALIBRATION_DELETED', 'Calibration Deleted'),
        # Users
        ('USER_REGISTERED', 'User Registered'),
        ('USER_CREATED', 'User Created'),
        ('USER_UPDATED', 'User Updated'),
        ('USER_DELETED', 'User Deleted'),
        ('USER_ROLE_CHANGED', 'User Role Changed'),
        ('USER_STATUS_CHANGED', 'User Status Changed'),
        # Kits
        ('KIT_CREATED', 'Kit Created'),
        ('KIT_UPDATED', 'Kit Updated'),
        ('KIT_DELETED', 'Kit Deleted'),
        # Projects
        ('PROJECT_CREATED', 'Project Created'),
        ('PROJECT_UPDATED', 'Project Updated'),
        ('PROJECT_DELETED', 'Project Deleted'),
        # Generic
        ('OTHER', 'Other'),
    ]

    actor = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    # Generic FK to related object using simple fields
    content_type_label = models.CharField(
        max_length=100, blank=True
    )  # e.g. 'equipment', 'borrowrequest'
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)  # string representation
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.actor} - {self.action} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
