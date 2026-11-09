"""Conservative public indexing policy, shared by metadata and sitemaps."""
import json
from types import SimpleNamespace
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.db.models.functions import Length, Trim
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.decorators.http import require_safe
from django.shortcuts import render


# Shops, products and news require an account under the current access policy.
# Keep this allowlist aligned with actual anonymous-page access, never user-agent
# exceptions. A sitemap must not advertise registration redirects as landing pages.
PUBLIC_SEARCH_ROUTES = frozenset({'home', 'about'})


def origin():
    return settings.SITE_URL.rstrip('/')


def public_businesses():
    from jobs.models import CompanyProfile, User
    return CompanyProfile.objects.filter(
        user__is_active=True, user__user_type__in=User.EMPLOYER_TYPES,
    ).exclude(company_name='').exclude(company_id='').exclude(industry='').exclude(user__pincode='')


def public_stories():
    from newsdesk.permissions import published_items
    return published_items().exclude(category='birthday').exclude(title='').annotate(
        seo_length=Length(Trim('body')),
    ).filter(seo_length__gte=80)


def summary(text):
    return ' '.join(strip_tags(text).split())[:160]


def metadata(request):
    if hasattr(request, '_seo_metadata'):
        return request._seo_metadata
    match = request.resolver_match
    name = match.view_name if match else ''
    data = {
        'title': 'Local From',
        'description': 'Discover local shops, products, offers and news in Vandavasi on Local From.',
        'canonical': origin() + request.path, 'indexable': False, 'type': 'website',
        'image': origin() + '/static/images/logo.png',
    }
    if name == 'home':
        data.update(title='Local From | Shops, Products & Offers in Vandavasi',
                    description='Discover shops, products, discounts and local news in Vandavasi, Tamil Nadu. Join Local From, a pilot platform connecting our neighbourhood.', indexable=True)
    elif name == 'about':
        data.update(title='About LOCALFROM | Local Shops & Community in Vandavasi',
                    description='LOCALFROM is your local platform in Vandavasi, Tamil Nadu. Discover nearby shops, products, offers and local news in one place.', indexable=True)
    elif name == 'business_list':
        data.update(title='Local Businesses & Shops Near You | Local From',
                    description='Discover businesses and shops in your pincode. Explore local business profiles, offers and opportunities on Local From.', indexable=public_businesses().exists())
    elif name == 'business_profile':
        business = public_businesses().select_related('user').filter(company_id=match.kwargs['company_id']).first()
        if business:
            place = business.user.city or business.user.pincode
            data.update(title=f'{business.company_name} in {place} | Local From',
                        description=summary(f'Explore {business.company_name}, {business.industry} in {place}, pincode {business.user.pincode}. View its shop profile, products and local offers.'), indexable=True)
    elif name == 'newsdesk:detail':
        story = public_stories().filter(pk=match.kwargs['pk']).first()
        if story:
            data.update(title=f'{story.title} | Local From News', description=summary(story.body), indexable=True, type='article')
    data['indexable'] = data['indexable'] and name in PUBLIC_SEARCH_ROUTES
    # Search/filter/pagination variants remain crawlable but are not search landing pages.
    # Tracking-only URLs consolidate to the clean URL without a conflicting noindex.
    if any(not (key.startswith('utm_') or key in {'gclid', 'fbclid'}) for key in request.GET):
        data['indexable'] = False
    data['robots'] = 'index,follow' if data['indexable'] else 'noindex,follow'
    if name in PUBLIC_SEARCH_ROUTES:
        graph = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'Organization', '@id': origin() + '/#organization',
             'name': 'Local From', 'alternateName': 'LOCALFROM',
             'url': origin() + '/', 'logo': data['image'],
             'email': 'localfrom8@gmail.com',
             'sameAs': ['https://www.instagram.com/local_from97/'],
             'contactPoint': [
                 {'@type': 'ContactPoint', 'telephone': number, 'contactType': 'customer support',
                  'availableLanguage': ['English', 'Tamil'], 'areaServed': 'IN'}
                 for number in ('+919361240355',)
             ]},
            {'@type': 'WebSite', '@id': origin() + '/#website', 'name': 'Local From',
             'alternateName': 'LOCALFROM', 'url': origin() + '/',
             'inLanguage': ['en-IN', 'ta-IN'],
             'publisher': {'@id': origin() + '/#organization'}},
            {'@type': 'AboutPage' if name == 'about' else 'WebPage',
             '@id': data['canonical'] + '#webpage', 'url': data['canonical'],
             'name': data['title'], 'description': data['description'],
             'inLanguage': 'en-IN', 'isPartOf': {'@id': origin() + '/#website'}},
        ]}
        # Safe inside a script element even if configurable values contain HTML.
        data['json_ld'] = json.dumps(graph).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    request._seo_metadata = data
    return data


def seo_context(request):
    return {'seo': metadata(request)}


class SEOMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Derive the apex/www pair from the configured canonical origin.
        # Leave local development, unrelated hosts and POSTs intact.
        canonical_host = urlsplit(origin()).hostname
        request_host = urlsplit('//' + request.get_host()).hostname
        apex = canonical_host.removeprefix('www.')
        if (request.method in {'GET', 'HEAD'} and request_host != canonical_host
                and request_host in {apex, 'www.' + apex}):
            return HttpResponsePermanentRedirect(origin() + request.get_full_path())
        response = self.get_response(request)
        if request.path.startswith(('/static/', '/media/')):
            return response
        if request.path in {'/robots.txt', '/sitemap.xml'} or request.path.startswith('/sitemaps/'):
            return response
        content_type = response.get('Content-Type', '')
        indexable = (response.status_code == 200 and request.method in {'GET', 'HEAD'}
                     and 'text/html' in content_type and metadata(request)['indexable'])
        if not indexable and 'X-Robots-Tag' not in response:
            response['X-Robots-Tag'] = 'noindex, follow'
        return response


@require_safe
def robots(request):
    # Do not disallow private URLs here: crawlers must see their noindex header.
    # Authentication remains the access control, never robots.txt.
    return HttpResponse('User-agent: *\nAllow: /\n\nSitemap: ' + origin() + '/sitemap.xml\n', content_type='text/plain; charset=utf-8')


class CanonicalSitemap(Sitemap):
    protocol = 'https'
    limit = 1000

    def get_urls(self, page=1, site=None, protocol=None):
        return super().get_urls(page=page, site=SimpleNamespace(domain=urlsplit(origin()).netloc), protocol=urlsplit(origin()).scheme)


class PublicPagesSitemap(CanonicalSitemap):
    def items(self):
        return ['home', 'about']

    def location(self, item):
        return reverse(item)


class BusinessesSitemap(CanonicalSitemap):
    def items(self):
        if 'business_profile' not in PUBLIC_SEARCH_ROUTES:
            return public_businesses().none()
        return public_businesses().order_by('pk')

    def location(self, item):
        return reverse('business_profile', args=[item.company_id])


class NewsSitemap(CanonicalSitemap):
    def items(self):
        if 'newsdesk:detail' not in PUBLIC_SEARCH_ROUTES:
            return public_stories().none()
        return public_stories().order_by('pk')

    def location(self, item):
        return reverse('newsdesk:detail', args=[item.pk])

    def lastmod(self, item):
        return item.updated_at


SITEMAPS = {'pages': PublicPagesSitemap, 'businesses': BusinessesSitemap, 'news': NewsSitemap}


@require_safe
def sitemap_index(request):
    sections = []
    for name, sitemap_class in SITEMAPS.items():
        sitemap = sitemap_class()
        if not sitemap.paginator.count:
            continue
        base = origin() + reverse('seo_sitemap', kwargs={'section': name})
        for page in range(1, sitemap.paginator.num_pages + 1):
            sections.append({'location': base + (f'?p={page}' if page > 1 else '')})
    return render(request, 'sitemap_index.xml', {'sitemaps': sections}, content_type='application/xml')
