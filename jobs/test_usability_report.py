from unittest import skip
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Advertiser, CompanyProfile, LocalOffer, User, UserNotification


class UsabilityReportTests(TestCase):
    def setUp(self):
        self.client.force_login(self.person)
        session = self.client.session
        session['active_pincode'] = ''
        session.save()

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('usability-owner', user_type='company', pincode='600001')
        cls.person = User.objects.create_user('usability-person', user_type='individual', pincode='600001')
        CompanyProfile.objects.create(user=cls.owner, company_name='Usability shop')
        Advertiser.objects.create(user=cls.owner, business_name='Usability shop', status='approved')
        cls.food = LocalOffer.objects.create(owner=cls.owner, business_name='Usability shop',
            title='Food offer', category='food', discount_text='10%')
        cls.shop = LocalOffer.objects.create(business_name='Other store', title='Shopping offer',
            category='shop', discount_text='20%')
        cls.expired = LocalOffer.objects.create(business_name='Expired', title='Expired deal',
            category='food', valid_until=timezone.localdate() - timedelta(days=1))
        LocalOffer.objects.create(business_name='Unapproved', title='Hidden deal', is_active=False)

    def test_member_filter_json_matches_category_and_excludes_unavailable(self):
        response = self.client.get('/advertise/?cat=food&format=json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(set(data['offers']), {str(self.food.pk)})
        self.assertEqual(data['offers'][str(self.food.pk)]['category'], 'Food & Drinks')
        self.assertIn('Food offer', data['html'])
        self.assertNotIn('Shopping offer', data['html'])
        self.assertNotIn('Expired deal', data['html'])
        self.assertNotIn('Hidden deal', data['html'])

    def test_filter_empty_reset_and_invalid_category(self):
        empty = self.client.get('/advertise/?cat=salon&format=json').json()
        self.assertEqual(empty['count'], 0)
        self.assertIn('Browse all offers', empty['html'])
        for category in ('', 'invalid'):
            data = self.client.get('/advertise/', {'cat': category, 'format': 'json'}).json()
            self.assertEqual(data['count'], 2)
            self.assertEqual(data['category'], '')

    def test_nojavascript_category_link_still_works(self):
        response = self.client.get('/advertise/?cat=food')
        self.assertContains(response, 'Food offer')
        self.assertNotContains(response, 'Shopping offer')
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, 'aria-label="Offer categories"')
        self.assertEqual(self.client.get(f'/offers/{self.expired.pk}/store/').status_code, 404)

    def test_profile_and_mobile_navigation_have_consistent_routes(self):
        self.client.force_login(self.owner)
        response = self.client.get('/advertiser/dashboard/')
        for expected in ('aria-label="Site header"', 'aria-label="Local From home"',
                         'aria-label="My account"', 'href="/account/"',
                         'href="/ads/post/"'):
            self.assertContains(response, expected)
        self.assertNotContains(response, 'href="/advertise/dashboard/"')
        self.assertNotContains(response, 'href="/advertise/ads/create/"')

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_myask_notification_shortcut_is_role_aware_and_private(self):
        UserNotification.objects.create(user=self.owner, title='Owner alert')
        UserNotification.objects.create(user=self.person, title='Person alert')
        UserNotification.objects.create(user=self.person, title='Read alert', is_read=True)
        for user, dashboard in ((self.owner, '/employer/dashboard/'), (self.person, '/jobseeker/dashboard/')):
            self.client.force_login(user)
            response = self.client.get(reverse('network_feed'))
            self.assertEqual(response.context['account_unread_count'], 1)
            self.assertEqual(response.context['account_notifications_url'], dashboard + '#notifications')
            self.assertContains(response, 'Account notifications, 1 unread')
            self.assertContains(response, 'aria-label="My Ask shortcuts"')
