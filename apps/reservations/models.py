from django.db import models


class Reservation(models.Model):
    """
    A time-bound reservation for a piece of equipment or a kit,
    created before the actual borrow/pickup date.
    """

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('ACTIVE', 'Active'),
        ('RETURN_PENDING', 'Return Pending'),
        ('RETURNED', 'Returned'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
        ('EXPIRED', 'Expired'),
    ]

    requester = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='reservations',
    )
    equipment = models.ForeignKey(
        'equipment.Equipment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reservations',
    )
    kit = models.ForeignKey(
        'kits.Kit',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reservations',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField(blank=True)
    returned_date = models.DateTimeField(null=True, blank=True)
    return_condition = models.CharField(max_length=20, blank=True)
    return_notes = models.TextField(blank=True)
    return_approved_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_returns',
    )
    return_approved_at = models.DateTimeField(null=True, blank=True)
    start_notified = models.BooleanField(default=False)
    end_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        item = self.equipment or self.kit
        return (
            f"{self.requester.full_name} reserved {item} "
            f"({self.start_date} to {self.end_date})"
        )

    class Meta:
        ordering = ['-created_at']


class WaitlistEntry(models.Model):
    """
    A position in the waitlist for a piece of equipment or kit
    that is currently unavailable.
    """

    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='waitlist_entries',
    )
    equipment = models.ForeignKey(
        'equipment.Equipment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='waitlist_entries',
    )
    kit = models.ForeignKey(
        'kits.Kit',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='waitlist_entries',
    )
    position = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        item = self.equipment or self.kit
        return f"{self.user.full_name} on waitlist for {item} (position {self.position})"

    class Meta:
        ordering = ['created_at']


class ReservationItemReturn(models.Model):
    """
    Tracks the return condition for each individual equipment item
    within a reservation. For kit reservations, one record per kit item.
    For equipment reservations, one record for the single equipment.
    """
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='item_returns',
    )
    equipment = models.ForeignKey(
        'equipment.Equipment',
        on_delete=models.CASCADE,
    )
    condition = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['reservation', 'equipment']
        ordering = ['equipment__name']

    def __str__(self):
        return f"{self.equipment.name} — {self.condition or 'No condition'}"
