"""Private attachment writes and authorized reads, including legacy files."""
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .models import Message


def private_storage():
    return FileSystemStorage(location=settings.CHAT_PRIVATE_ROOT,
                             file_permissions_mode=0o600, directory_permissions_mode=0o700)


@never_cache
@login_required
@require_safe
def download(request, message_id):
    from django.db.models import Q
    message = get_object_or_404(Message.objects.filter(
        Q(conversation__user_a=request.user) | Q(conversation__user_b=request.user)),
        pk=message_id)
    name = message.file.name
    if not name or not name.startswith('chat_files/') or '..' in Path(name).parts:
        raise Http404
    storage = private_storage()
    if storage.exists(name):
        file = storage.open(name, 'rb')
    else:
        # Historical files are retained without changing their DB names. The
        # matching public URL is denied by Django and the supplied Nginx rule.
        legacy = Path(safe_join(str(settings.MEDIA_ROOT), name)).resolve()
        if not legacy.is_relative_to(Path(settings.MEDIA_ROOT).resolve()) or not legacy.is_file():
            raise Http404
        file = legacy.open('rb')
    content_type = 'application/octet-stream'
    if message.msg_type == 'image':
        try:
            from PIL import Image
            image = Image.open(file)
            content_type = {'JPEG': 'image/jpeg', 'PNG': 'image/png',
                            'GIF': 'image/gif', 'WEBP': 'image/webp'}.get(image.format, content_type)
            image.verify()
        except (OSError, ValueError):
            content_type = 'application/octet-stream'
        file.seek(0)
    response = FileResponse(file, as_attachment=not content_type.startswith('image/'),
                            filename=message.file_name or Path(name).name,
                            content_type=content_type)
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return response
