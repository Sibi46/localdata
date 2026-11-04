from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from .uploads import NewsStorage, validate_photo


class IdentityStorage(NewsStorage):
    @property
    def base_location(self):
        return str(getattr(settings, 'NEWS_IDENTITY_ROOT', Path(settings.MEDIA_ROOT).parent / 'news-identities-private'))

    def url(self, name):
        raise ValueError('Identity documents have no public URL.')


def identity_storage():
    return IdentityStorage(file_permissions_mode=0o600, directory_permissions_mode=0o700)


def validate_identity(value):
    if value.size > 5 * 1024 * 1024:
        raise ValidationError('Upload a document of 5 MB or smaller.')
    extension = Path(value.name).suffix.lower()
    if extension == '.pdf':
        value.seek(0)
        header = value.read(5)
        value.seek(0)
        if header != b'%PDF-':
            raise ValidationError('Upload a valid PDF or photo of your Aadhaar.')
    elif extension in {'.jpg', '.jpeg', '.png', '.webp'}:
        validate_photo(value)
    else:
        raise ValidationError('Use a PDF, JPEG, PNG or WebP document.')


def validate_profile_photo(value):
    if Path(value.name).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
        raise ValidationError('Use a JPEG, PNG or WebP profile photo.')
    validate_photo(value)
