import json
import re
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest import skip
from .models import User, CompanyProfile, LocalOffer


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class FourteenReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('fourteen-user', user_type='individual', pincode='600001')
        owner = User.objects.create_user('fourteen-store', user_type='shop', pincode='600001')
        cls.company = CompanyProfile.objects.create(user=owner, company_name='Report store')
        for title, category, flash in [('Normal offer', 'food', False), ('Flash offer', 'food', True), ('Shopping offer', 'shop', False)]:
            LocalOffer.objects.create(owner=owner, business_name='Report store', title=title, category=category, discount_text='10%', is_flash=flash)

    @skip('Health and gift points retired; boundary covered by jobs.test_feature_scope')
    def test_health_filter_serializes_exact_saved_condition_keys(self):
        response = self.client.get('/health/guide/')
        self.assertContains(response, 'data-conditions="report-condition"')
        self.assertContains(response, 'id="conditionEmpty"')
        self.assertContains(response, 'keys.includes(slug)')
        self.assertContains(response, 'Show all foods')

    @skip('Health and gift points retired; boundary covered by jobs.test_feature_scope')
    def test_invalid_advice_is_an_empty_mapping_not_a_server_error(self):
        self.item.condition_advice = '[]'; self.item.save()
        response = self.client.get('/health/guide/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['items'][0].condition_slugs, '')

    @skip('Health and gift points retired; boundary covered by jobs.test_feature_scope')
    def test_nutrition_has_a_tab_and_feed_panel(self):
        response = self.client.get(reverse('guide_item', args=[self.category.slug, self.item.slug]))
        self.assertContains(response, 'data-section="nutrition"', count=2)
        self.assertContains(response, 'Published nutrition text')

    @skip('Health and gift points retired; boundary covered by jobs.test_feature_scope')
    def test_missing_nutrition_and_condition_sections_show_honest_empty_states(self):
        self.item.nutrition = ''; self.item.save()
        response = self.client.get(reverse('guide_item', args=[self.category.slug, self.item.slug]))
        self.assertContains(response, 'Nutrition information has not been published')
        response = self.client.get(reverse('condition_detail', args=[self.condition.slug]))
        self.assertContains(response, 'Information for this section has not been published yet.')
        self.assertNotContains(response, 'href="#recipes"')

    @skip('Health and gift points retired; boundary covered by jobs.test_feature_scope')
    def test_primary_navigation_is_identical_on_offers_gift_points_and_health(self):
        self.client.force_login(self.user)
        destinations = []
        for path in ('/', '/advertise/', '/coupons/activate/', '/health/guide/'):
            response = self.client.get(path)
            self.assertContains(response, 'class="opc-bottom-nav"', count=1)
            nav = re.search(r'<nav class="opc-bottom-nav".*?</nav>', response.content.decode(), re.S).group()
            destinations.append(re.findall(r'href="([^"]+)"', nav))
            self.assertNotContains(response, 'class="ag-botnav"')
            self.assertNotContains(response, '<nav id="healthNav">')
        self.assertTrue(all(item == destinations[0] for item in destinations))
        self.assertIn('/advertise/', destinations[0]); self.assertIn('/health/', destinations[0])

    @skip('Health and gift points retired; boundary covered by jobs.test_feature_scope')
    def test_gift_points_has_one_homepage_navigation_entry(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/'), 'href="/coupons/activate/"', count=1)

    def test_offers_use_shared_readable_cards_for_flash_and_normal_results(self):
        self.client.force_login(self.user)
        response = self.client.get('/advertise/?cat=food')
        self.assertContains(response, 'class="social-offer"', count=2)
        self.assertContains(response, 'Normal offer')
        self.assertContains(response, 'Flash offer')
        self.assertNotContains(response, 'Shopping offer')
        self.assertContains(response, '/business/' + self.company.company_id + '/')

    @override_settings(SOCIAL_PROFILE_URLS={'facebook':'https://www.facebook.com/example-profile', 'instagram':'https://instagram.com/'}, LOCAL_FROM_INSTAGRAM_URL='https://www.instagram.com/local_from97/')
    def test_social_links_use_configured_profiles_and_exclude_platform_homepages(self):
        self.client.force_login(self.user)
        for path in ('/', '/advertise/'):
            response = self.client.get(path)
            self.assertEqual(response.context['SOCIAL_PROFILES'][0]['url'], 'https://www.facebook.com/example-profile')
            self.assertContains(response, 'href="https://www.instagram.com/local_from97/"')
            self.assertNotContains(response, 'href="https://instagram.com/"')

    def test_registration_has_an_accessible_back_control(self):
        response = self.client.get('/register/?type=company')
        self.assertContains(response, 'Back to home')
        self.assertContains(response, 'href="/"')
