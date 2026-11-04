import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from PIL import Image, UnidentifiedImageError


class NewsStorage(FileSystemStorage):
    @property
    def base_location(self):
        # Outside /media/; resolve lazily so test settings and deployments can
        # override the location without writing to the real media directory.
        return str(getattr(settings, 'NEWSDESK_MEDIA_ROOT', Path(settings.MEDIA_ROOT).parent / 'newsdesk-private'))

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def private_storage():
    return NewsStorage()


def upload_path(instance, filename):
    return f'{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


def validate_photo(value):
    if value.size > 5 * 1024 * 1024:
        raise ValidationError('Photos must be 5 MB or smaller.')
    was_closed = value.closed
    try:
        if was_closed:
            value.open('rb')
        value.seek(0)
        with Image.open(value) as photo:
            if photo.format not in {'JPEG', 'PNG', 'WEBP'} or photo.width * photo.height > 20_000_000:
                raise ValidationError('Use a JPEG, PNG or WebP photo up to 20 megapixels.')
            photo.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise ValidationError('Upload a valid JPEG, PNG or WebP photo.')
    finally:
        if was_closed:
            value.close()
        else:
            value.seek(0)


def validate_video(value):
    if value.size > 25 * 1024 * 1024:
        raise ValidationError('Videos must be 25 MB or smaller.')
    was_closed = value.closed
    try:
        if was_closed:
            value.open('rb')
        value.seek(0)
        header = value.read(4096)
    finally:
        if was_closed:
            value.close()
        else:
            value.seek(0)
    extension = Path(value.name).suffix.lower()
    mp4 = extension == '.mp4' and len(header) >= 12 and header[4:8] == b'ftyp'
    webm = extension == '.webm' and header.startswith(b'\x1aE\xdf\xa3') and b'webm' in header
    if not (mp4 or webm):
        raise ValidationError('Upload an MP4 or WebM video.')
