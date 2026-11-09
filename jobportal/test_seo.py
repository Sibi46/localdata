"""SEO coverage for the current shop, product and news application."""
import re
import json
from xml.etree import ElementTree
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from jobs.models import CompanyProfile, District, PinCode, State, User


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
        state=State.objects.create(name='SEO State',code='SE')
        district=District.objects.create(name='SEO District',state=state)
        pin=PinCode.objects.create(code='600001',district=district,area_name='SEO Area')
        from newsdesk.models import NewsItem
        cls.story=NewsItem.objects.create(title='Published local story',body='Useful neighbourhood news. '*10,pincode=pin,author=cls.owner,status='published')

    def locations(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return [node.text for node in ElementTree.fromstring(response.content).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]

    def test_public_sitemaps_exclude_retired_features(self):
        index = self.locations('/sitemap.xml')
        self.assertEqual(index,['https://ourpincode.com/sitemaps/pages.xml'])
        self.assertFalse(any('/sitemaps/jobs.xml' in url for url in index))
        paths = self.locations('/sitemaps/pages.xml') + self.locations('/sitemaps/businesses.xml')
        self.assertEqual(paths,['https://ourpincode.com/','https://ourpincode.com/about/'])
        self.assertEqual(self.locations('/sitemaps/news.xml'),[])
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

    def test_home_local_metadata_and_actual_brand_image(self):
        response=self.client.get('/')
        self.assertContains(response,'Local From | Shops, Products &amp; Offers in Vandavasi')
        self.assertContains(response,'name="robots" content="index,follow"')
        self.assertContains(response,'https://ourpincode.com/static/images/logo.png')
        self.assertNotContains(response,'/static/images/local-form.svg')
        self.assertNotIn('X-Robots-Tag',response)

    def test_home_organization_schema_uses_published_contacts(self):
        response=self.client.get('/')
        scripts=re.findall(r'<script type="application/ld\+json">(.*?)</script>',response.content.decode(),re.S)
        self.assertEqual(len(scripts),1)
        graph=json.loads(scripts[0])['@graph']
        organization=next(item for item in graph if item['@type']=='Organization')
        self.assertEqual(organization['logo'],'https://ourpincode.com/static/images/logo.png')
        self.assertEqual(organization['sameAs'],['https://www.instagram.com/local_from97/'])
        self.assertEqual(organization['email'],'localfrom8@gmail.com')
        self.assertEqual([item['telephone'] for item in organization['contactPoint']],['+919361240355'])
        self.assertFalse(any('aggregateRating' in item for item in graph))

    def test_sitemap_landing_pages_are_guest_accessible_and_indexable(self):
        for location in self.locations('/sitemaps/pages.xml'):
            response=self.client.get(location.removeprefix('https://ourpincode.com'))
            self.assertEqual(response.status_code,200)
            self.assertContains(response,'name="robots" content="index,follow"')
            self.assertNotIn('X-Robots-Tag',response)

    def test_about_has_one_shared_metadata_set(self):
        response=self.client.get('/about/')
        html=response.content.decode()
        self.assertNotIn('evoxu',html.casefold())
        self.assertNotIn('connecting people',html.casefold())
        self.assertNotIn('News Desk',html)
        self.assertContains(response,'Local News')
        self.assertContains(response,'LOCALFROM is your local platform in Vandavasi, Tamil Nadu.')
        self.assertEqual(len(re.findall('name="description"',html)),1)
        self.assertEqual(len(re.findall('rel="canonical"',html)),1)
        self.assertContains(response,'href="https://ourpincode.com/about/"')

    def test_googlebot_has_same_registration_gate_as_other_guests(self):
        for path in ['/products/','/businesses/',self.shop.get_absolute_url(),reverse('newsdesk:detail',args=[self.story.pk])]:
            for agent in ['Mozilla/5.0','Googlebot']:
                response=self.client.get(path,HTTP_USER_AGENT=agent)
                self.assertEqual(response.status_code,302)
                self.assertTrue(response['Location'].startswith('/register/?'))
                self.assertIn('noindex',response['X-Robots-Tag'])

    def test_logged_in_business_is_still_noindex_under_current_policy(self):
        self.client.force_login(self.owner)
        response=self.client.get(self.shop.get_absolute_url())
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'name="robots" content="noindex,follow"')
        self.assertIn('noindex',response['X-Robots-Tag'])

    def test_search_variants_are_noindex_and_tracking_consolidates(self):
        for query in ['q=store','page=2','pincode=604408']:
            response=self.client.get('/?'+query)
            self.assertIn('noindex',response['X-Robots-Tag'])
            self.assertContains(response,'rel="canonical" href="https://ourpincode.com/"')
        response=self.client.get('/?utm_source=test&fbclid=test')
        self.assertNotIn('X-Robots-Tag',response)
        self.assertContains(response,'rel="canonical" href="https://ourpincode.com/"')

    def test_robots_advertises_canonical_sitemap(self):
        response=self.client.get('/robots.txt')
        self.assertContains(response,'Sitemap: https://ourpincode.com/sitemap.xml')
        self.assertTrue(response['Content-Type'].startswith('text/plain'))

    def test_missing_page_has_noindex_header(self):
        response=self.client.get('/missing-seo-page/')
        self.assertEqual(response.status_code,404)
        self.assertIn('noindex',response['X-Robots-Tag'])
