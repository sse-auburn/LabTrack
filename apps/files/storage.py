import mimetypes

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.urls import reverse

from apps.files.models import StoredFile


class DatabaseStorage(Storage):
    """
    Django storage backend that persists files as binary data in the database
    via the StoredFile model.
    """

    def _save(self, name, content):
        """Read uploaded content and store it in the DB. Return the StoredFile PK."""
        content.seek(0)
        data = content.read()
        size = len(data)
        mimetype, _ = mimetypes.guess_type(name)
        if not mimetype:
            mimetype = 'application/octet-stream'

        stored = StoredFile.objects.create(
            filename=name,
            mimetype=mimetype,
            data=data,
            size=size,
        )
        return str(stored.pk)

    def _open(self, name, mode='rb'):
        """Lookup StoredFile by PK and return a ContentFile."""
        stored = StoredFile.objects.get(pk=int(name))
        return ContentFile(stored.data, name=stored.filename)

    def delete(self, name):
        """Delete the StoredFile record by PK."""
        try:
            StoredFile.objects.filter(pk=int(name)).delete()
        except (ValueError, StoredFile.DoesNotExist):
            pass

    def exists(self, name):
        """Check if a StoredFile with the given PK exists."""
        try:
            return StoredFile.objects.filter(pk=int(name)).exists()
        except ValueError:
            return False

    def url(self, name):
        """Return the URL to the serve_db_file view."""
        try:
            return reverse('serve_db_file', kwargs={'file_id': int(name)})
        except ValueError:
            return ''

    def size(self, name):
        """Return the stored file size."""
        try:
            stored = StoredFile.objects.get(pk=int(name))
            return stored.size
        except (ValueError, StoredFile.DoesNotExist):
            return 0

    def get_valid_name(self, name):
        """Pass through — StoredFile stores the original filename."""
        return name

    def get_available_name(self, name, max_length=None):
        """No collision handling needed — each upload gets its own DB row/PK."""
        return name
