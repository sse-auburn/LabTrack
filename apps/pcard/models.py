from django.db import models


class PcardTransaction(models.Model):
    """A P-Card purchase transaction with receipt and itemized list."""

    transaction_date = models.DateField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    receipt_file = models.FileField(
        upload_to='pcard/receipts/',
        blank=True,
        null=True,
        help_text='Receipt image or PDF (stored in database).',
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pcard_transactions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']
        verbose_name = 'P-Card Transaction'
        verbose_name_plural = 'P-Card Transactions'

    def __str__(self):
        return f"Transaction on {self.transaction_date} — ${self.total_price}"

    @property
    def item_count(self):
        return self.items.count()


class PcardDeletionRequest(models.Model):
    """A member's request to delete a P-Card transaction (requires admin approval)."""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    transaction = models.ForeignKey(
        PcardTransaction,
        on_delete=models.CASCADE,
        related_name='deletion_requests',
    )
    requested_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='pcard_deletion_requests',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
    )
    reason = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_pcard_deletions',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'P-Card Deletion Request'
        verbose_name_plural = 'P-Card Deletion Requests'

    def __str__(self):
        return f"Delete request for #{self.transaction.pk} by {self.requested_by.full_name} ({self.status})"


class PcardItem(models.Model):
    """An individual item line within a P-Card transaction."""

    transaction = models.ForeignKey(
        PcardTransaction,
        on_delete=models.CASCADE,
        related_name='items',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'P-Card Item'
        verbose_name_plural = 'P-Card Items'

    def __str__(self):
        return f"{self.name} x{self.quantity}"

    @property
    def line_total(self):
        if self.unit_price is not None:
            return self.unit_price * self.quantity
        return None
