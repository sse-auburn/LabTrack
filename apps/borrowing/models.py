from django.db import models


class BorrowRequest(models.Model):
    """
    Represents a request by a lab member to borrow equipment or a kit.
    Tracks the full lifecycle from PENDING through RETURNED or OVERDUE.
    """

    STATUS_CHOICES = [
        ('APPROVED', 'Approved'),
        ('ACTIVE', 'Active'),           # item physically picked up
        ('RETURN_PENDING', 'Return Pending'),  # borrower submitted return, awaiting admin confirmation
        ('RETURNED', 'Returned'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]

    borrower = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='borrow_requests',
    )
    equipment = models.ForeignKey(
        'equipment.Equipment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='borrow_requests',
    )
    kit = models.ForeignKey(
        'kits.Kit',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='borrow_requests',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    purpose = models.TextField()
    requested_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_borrows',
    )
    approved_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField()
    returned_date = models.DateTimeField(null=True, blank=True)
    return_condition = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        item = self.equipment or self.kit
        return f"{self.borrower.username} borrowed {item} ({self.status})"

    @property
    def is_overdue(self):
        from datetime import date
        return self.status in ['ACTIVE', 'APPROVED'] and self.due_date < date.today()

    @property
    def days_overdue(self):
        from datetime import date
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    @property
    def item(self):
        return self.equipment or self.kit

    class Meta:
        ordering = ['-requested_date']


class KitItemReturnApproval(models.Model):
    """Per-equipment-owner approval record when a kit borrow is returned."""
    borrow_request = models.ForeignKey(
        'BorrowRequest',
        on_delete=models.CASCADE,
        related_name='kit_item_approvals',
    )
    equipment = models.ForeignKey(
        'equipment.Equipment',
        on_delete=models.CASCADE,
        related_name='kit_return_approvals',
    )
    owner = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='kit_return_approvals_to_confirm',
    )
    confirmed_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kit_return_approvals_confirmed',
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('borrow_request', 'equipment')

    @property
    def is_confirmed(self):
        return self.confirmed_by is not None
