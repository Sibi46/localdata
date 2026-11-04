"""SEO coverage for the current shop, product and news application."""
import re
from xml.etree import ElementTree
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from jobs.models import CompanyProfile, User


@override_settings(SITE_URL='https://www.localfrom.com',
                   ALLOWED_HOSTS=['localfrom.com', 'www.localfrom.com', 'localhost'])
class CanonicalDomainTests(SimpleTestCase):
    def response(self, method, host):
        from django.http import HttpResponse
        from .seo import SEOMiddleware
        request = getattr(RequestFactory(), method)('/products/?q=local', HTTP_HOST=host)
        return SEOMiddleware(lambda request: HttpResponse('ok'))(request)

    def test_apex_get_redirects_to_configured_www_preserving_path_and_query(self):
        response = self.response('get', 'localfrom.com')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'https://www.localfrom.com/products/?q=local')

    def test_canonical_host_and_localhost_do_not_redirect(self):
        for host in ('www.localfrom.com', 'localhost'):
            with self.subTest(host=host):
                self.assertEqual(self.response('get', host).status_code, 200)

    def test_post_on_apex_is_not_redirected(self):
        self.assertEqual(self.response('post', 'localfrom.com').status_code, 200)


@override_settings(SITE_URL='https://ourpincode.com')
class SEOTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('seo-owner', user_type='shop', pincode='600001')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Local Store', industry='Retail')

    def locations(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return [node.text for node in ElementTree.fromstring(response.content).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]

    def test_public_sitemaps_exclude_retired_features(self):
        index = self.locations('/sitemap.xml')
        self.assertTrue(any('/sitemaps/businesses.xml' in url for url in index))
        self.assertFalse(any('/sitemaps/jobs.xml' in url for url in index))
        paths = self.locations('/sitemaps/pages.xml') + self.locations('/sitemaps/businesses.xml')
        self.assertIn('https://ourpincode.com' + self.shop.get_absolute_url(), paths)
        self.assertFalse(any('/jobs/' in url or '/vouchers/' in url for url in paths))

    def test_inactive_shop_is_excluded(self):
        self.owner.is_active = False
        self.owner.save()
        self.assertEqual(self.locations('/sitemaps/businesses.xml'), [])

    def test_home_metadata_has_canonical_and_current_brand(self):
        response = self.client.get('/')
        self.assertContains(response, '<link rel="canonical" href="https://ourpincode.com/">', html=True)
        self.assertContains(response, 'Local From')
        self.assertEqual(len(re.findall('name="description"', response.content.decode())), 1)

    def test_private_auth_pages_are_noindex(self):
        for path in ['/login/', '/register/']:
            self.assertIn('noindex', self.client.get(path)['X-Robots-Tag'])
