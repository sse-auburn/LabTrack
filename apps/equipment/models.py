from django.db import models

from apps.equipment.utils import generate_unique_color


class Category(models.Model):
    """Equipment category used to group similar items."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        blank=True,
        default='',
        help_text='Hex color for UI badge. Leave blank for auto-generated unique color.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.color:
            existing = set(
                Category.objects.exclude(pk=self.pk).values_list('color', flat=True)
            )
            self.color = generate_unique_color(existing)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'


class Location(models.Model):
    """Physical location within the lab (room, shelf, cabinet, etc.)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    building = models.CharField(max_length=100, blank=True)
    room = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        parts = [self.name]
        detail = f"{self.building} {self.room}".strip()
        if detail:
            parts.append(f"({detail})")
        return ' '.join(parts)

    class Meta:
        ordering = ['name']


class Equipment(models.Model):
    """A single piece of lab equipment tracked in the inventory."""

    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('BORROWED', 'Borrowed'),
        ('RESERVED', 'Reserved'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('DAMAGED', 'Damaged'),
        ('RETIRED', 'Retired'),
    ]
    CONDITION_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('GOOD', 'Good'),
        ('FAIR', 'Fair'),
        ('POOR', 'Poor'),
        ('DAMAGED', 'Damaged'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    serial_number = models.CharField(max_length=100, blank=True, unique=True, null=True)
    model_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment',
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='equipment',
    )
    owner = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_equipment',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='GOOD')
    image = models.ImageField(upload_to='equipment/', blank=True, null=True)
    purchase_date = models.DateField(blank=True, null=True)
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class LifecycleEvent(models.Model):
    """Records a significant event in an equipment item's lifecycle."""

    EVENT_CHOICES = [
        ('PURCHASED', 'Purchased'),
        ('DEPLOYED', 'Deployed'),
        ('MAINTENANCE', 'Sent to Maintenance'),
        ('REPAIRED', 'Repaired'),
        ('DAMAGED', 'Damaged'),
        ('RETIRED', 'Retired'),
        ('STATUS_CHANGE', 'Status Changed'),
        ('CONDITION_CHANGE', 'Condition Changed'),
        ('NOTE', 'Note Added'),
    ]

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='lifecycle_events',
    )
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    description = models.TextField()
    performed_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.equipment.name} - {self.event_type} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']


class MovementLog(models.Model):
    """Records when a piece of equipment is moved between locations."""

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='movement_logs',
    )
    from_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements_from',
    )
    to_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements_to',
    )
    moved_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reason = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.equipment.name} moved on {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
