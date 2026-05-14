from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from apps.files.models import StoredFile


@login_required
def serve_db_file(request, file_id):
    """Serve a StoredFile by its primary key."""
    stored = get_object_or_404(StoredFile, pk=file_id)
    response = HttpResponse(
        stored.data,
        content_type=stored.mimetype or 'application/octet-stream',
    )
    response['Content-Disposition'] = f'inline; filename="{stored.filename}"'
    response['Content-Length'] = stored.size
    return response
