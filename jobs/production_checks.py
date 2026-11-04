"""Read-only deployment guards. Never print secret values or contact services."""
from urllib.parse import urlsplit

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


def configured(value):
    value = str(value or '').strip()
    return bool(value) and not value.upper().startswith(('CHANGE_ME', 'REPLACE_ME'))


@register(Tags.security, deploy=True)
def production_configuration(app_configs, **kwargs):
    errors = []

    def require(condition, number, message):
        if not condition:
            errors.append(Error(message, id=f'localfrom.E{number:03d}'))

    require(not settings.DEMO_SIGNUP_OTP and not settings.DEMO_PASSWORD_RESET_OTP,
            1, 'Production must disable both demo OTP settings.')
    public_demo = getattr(settings, 'PUBLIC_DEMO_SIGNUP', False)
    require(public_demo or (configured(settings.TWO_FACTOR_API_KEY)
            and configured(settings.TWO_FACTOR_OTP_TEMPLATE)),
            2, 'Configure real OTP delivery credentials and an approved template before launch.')
    if public_demo:
        errors.append(Warning(
            'Public demo signup is active: visible testing codes do not verify phone ownership. '
            'Password recovery is disabled; existing accounts still require their password.',
            id='localfrom.W001',
        ))
    secret = settings.SECRET_KEY
    require(configured(secret) and len(secret) >= 50 and len(set(secret)) >= 5
            and not secret.startswith('django-insecure-'),
            3, 'Configure a new, strong production signing key.')
    db = settings.DATABASES['default']
    require(db.get('ENGINE') == 'django.db.backends.mysql'
            and all(configured(db.get(key)) for key in ('NAME', 'USER', 'PASSWORD', 'HOST')),
            4, 'Configure the production MySQL database and dedicated application credentials.')
    otp_cache = settings.CACHES.get(settings.OTP_CACHE_ALIAS, {})
    require(otp_cache.get('BACKEND') == 'django.core.cache.backends.redis.RedisCache'
            and configured(otp_cache.get('LOCATION')),
            5, 'Production OTP proofs require the shared Redis cache.')
    require(settings.SECURE_SSL_REDIRECT and settings.SESSION_COOKIE_SECURE
            and settings.CSRF_COOKIE_SECURE and urlsplit(settings.SITE_URL).scheme == 'https',
            6, 'Production requires HTTPS redirects, secure cookies and an HTTPS site origin.')
    hostname = urlsplit(settings.SITE_URL).hostname
    require('*' not in settings.ALLOWED_HOSTS and hostname in settings.ALLOWED_HOSTS,
            7, 'Use explicit allowed hosts including the configured site hostname.')
    require(not settings.DEBUG, 8, 'Production must disable DEBUG.')
    return errors
