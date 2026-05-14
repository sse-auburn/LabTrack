from django.db import models


class StoredFile(models.Model):
    """A file stored as binary data in the database."""

    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=100, blank=True)
    data = models.BinaryField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stored File'
        verbose_name_plural = 'Stored Files'

    def __str__(self):
        return self.filename
