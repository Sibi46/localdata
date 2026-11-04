from unittest import skip
from django.test import TestCase, override_settings
from .models import User, CompanyProfile, LocalOffer


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class ReportRegressionTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.get(username='report-business'))
        session = self.client.session
        session['active_pincode'] = ''
        session.save()

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create_user('report-business', user_type='shop', pincode='600001')
        cls.company = CompanyProfile.objects.create(user=owner, company_name='Test store')
        cls.offer = LocalOffer.objects.create(owner=owner, business_name='Test store', title='Food deal', discount_text='10%', category='food')
        LocalOffer.objects.create(business_name='Other store', title='Flash deal', discount_text='20%', category='shop', is_flash=True)
        LocalOffer.objects.create(business_name='Hidden', title='Not approved', discount_text='5%', category='food', is_active=False)

    def test_filters_include_matches_and_exclude_inactive(self):
        response = self.client.get('/advertise/?cat=FOOD%20')
        self.assertEqual(list(response.context['normal_offers']), [self.offer])
        self.assertFalse(response.context['flash_offers'])
        self.assertContains(response, '/business/' + self.company.company_id + '/')

    def test_empty_category_keeps_filters_and_home(self):
        response = self.client.get('/advertise/?cat=salon')
        self.assertContains(response, 'No offers here just yet.')
        self.assertContains(response, 'Browse all offers')
        self.assertContains(response, '?cat=food')
        self.assertContains(response, 'aria-label="Offer categories"')

    def test_unknown_category_falls_back_to_all(self):
        response = self.client.get('/advertise/?cat=unknown')
        self.assertEqual(response.context['active_cat'], '')
        self.assertEqual(len(response.context['normal_offers']), 1)
        self.assertEqual(len(response.context['flash_offers']), 1)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_public_quiz_and_employer_route(self):
        response = self.client.get('/quiz/play/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/login/?next=/quiz/play/')
        self.client.force_login(User.objects.get(username='report-business'))
        response = self.client.get('/quiz/play/')
        self.assertContains(response, 'id="quiz-form"')
        self.assertNotContains(response, 'id="opc-quiz-overlay"')
        self.assertEqual(self.client.get('/quiz/').status_code, 200)
