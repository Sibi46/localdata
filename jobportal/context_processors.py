from django.conf import settings


def site_branding(request):
    """Canonical links must not depend on an incoming Host header."""
    from urllib.parse import urlsplit
    profiles = []
    for platform, label, icon in [
        ('facebook', 'Facebook', 'fa-facebook-f'),
        ('instagram', 'Instagram', 'fa-instagram'),
        ('linkedin', 'LinkedIn', 'fa-linkedin-in'),
        ('youtube', 'YouTube', 'fa-youtube'),
    ]:
        url = getattr(settings, 'SOCIAL_PROFILE_URLS', {}).get(platform, '').strip()
        try:
            parsed = urlsplit(url)
            if parsed.scheme == 'https' and parsed.hostname and not parsed.username and parsed.path.strip('/'):
                profiles.append({'label': label, 'icon': icon, 'url': url})
        except ValueError:
            pass
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_URL': settings.SITE_URL,
        'SITE_TAGLINE': settings.SITE_TAGLINE,
        'GA4_MEASUREMENT_ID': settings.GA4_MEASUREMENT_ID,
        'SOCIAL_PROFILES': profiles,
    }
