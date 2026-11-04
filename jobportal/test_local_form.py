from jobportal.test_support import verify_account_phone
"""Regression coverage for the reduced Local From product surface."""
from django.contrib import admin
from django.test import TestCase
from django.urls import Resolver404, resolve, reverse

from jobs.models import BusinessReview, CompanyProfile, Conversation, User
from jobs.features import FEATURES
from portal.models import Category, Community


class LocalFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.create_user(username='member', password='test-pass', user_type='individual', pincode='600001')
        cls.owner = User.objects.create_user(username='owner', password='test-pass', user_type='company', pincode='600001')
        cls.company = CompanyProfile.objects.create(user=cls.owner, company_name='Local Shop', industry='Retail')
        cls.superuser = User.objects.create_user(username='site-admin', password='test-pass', admin_role='super_admin', is_staff=True, is_superuser=True)
        cls.category = Category.objects.create(name='Neighbours', slug='neighbours')
        cls.community = Community.objects.create(name='Our street', page_id='our-street', category=cls.category, created_by=cls.owner, pincode='600001', is_verified=True)

    def test_removed_endpoints_do_not_resolve(self):
        paths = ['/jobs/', '/jobs/1/', '/post-job/', '/jobseeker/dashboard/', '/candidates/',
                 '/campus/', '/community/family/', '/community/school-corner/', '/quiz/play/',
                 '/tuition/', '/health/', '/coupons/activate/', '/vouchers/marketplace/',
                 '/portal/events/', '/portal/event/1/', '/portal/my/events/', '/smart-marketing/',
                 '/marketing/', '/api/spin/', '/referral/', '/api/nearby-jobs/',
                 '/messages/invite/1/respond/', '/district-admin/jobs/',
                 '/network/', '/network/1/connect/', '/network/1/close/']
        for path in paths:
            with self.subTest(path=path):
                try:
                    match = resolve(path)
                except Resolver404:
                    match = None
                # The legacy community slug fallback also returns 404 for retired slugs.
                if match and match.url_name == 'community_module':
                    self.assertEqual(self.client.get(path).status_code, 404)
                else:
                    self.assertIsNone(match)
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_public_pages_render_with_current_brand(self):
        self.client.force_login(self.member)
        paths = ['/', '/businesses/', '/advertise/', '/flicks/', '/news/', '/register/', '/login/', '/about/', '/terms/', '/privacy/', self.company.get_absolute_url()]
        for path in paths:
            with self.subTest(path=path):
                if path in ('/register/', '/login/'):
                    self.client.logout()
                else:
                    self.client.force_login(self.member)
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Local From')
                self.assertNotContains(response, 'Smart Marketing')
                self.assertNotContains(response, '/tuition/')
                self.assertNotContains(response, '/vouchers/')
                self.assertNotContains(response, '/jobs/')

    def test_home_catalog_excludes_retired_features(self):
        names = {feature['name'] for feature in FEATURES}
        self.assertFalse(names & {'My Ask', 'Jobs', 'Family', 'Campus', 'Quiz', 'Tuitions', 'School Corner', 'Health', 'Coupons', 'Events', 'Gift Vouchers'})
        self.assertNotIn('jobs.job', {model._meta.label_lower for model in admin.site._registry})

    def test_home_has_no_discover_images_or_community_promotions(self):
        response = self.client.get('/')
        self.assertContains(response, 'Local From')
        for removed_content in ('Discover Local From', 'home-discover', 'hp-gallery',
                                "Don't just post.", 'Create real-world impact together.',
                                'local-card-community', 'My Ask', '/network/'):
            self.assertNotContains(response, removed_content)

    def test_remaining_account_and_community_pages_render(self):
        self.client.force_login(self.member)
        for path in ['/profile/edit/', '/my-accounts/', '/messages/']:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, '/jobs/')
                self.assertNotContains(response, '/portal/events/')
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/employer/dashboard/').status_code, 200)
        for suffix in ['dashboard/', 'members/', 'edit/', 'leaders/add/', 'volunteer/', 'volunteers/', 'video/upload/', 'post/']:
            with self.subTest(community_form=suffix):
                self.assertEqual(self.client.get('/portal/c/our-street/' + suffix).status_code, 404)
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get('/super-admin/').status_code, 200)
        for path in ['/super-admin/analytics/', '/super-admin/users/', '/admin-panel/users/', '/super-admin/admin-team/', '/admin-workspace/']:
            try:
                resolve(path)
            except Resolver404:
                continue
            with self.subTest(admin_page=path):
                self.assertIn(self.client.get(path).status_code, (200, 302))

    def test_reviews_no_longer_create_rewards(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse('business_review', args=[self.company.company_id]), {'rating': 5, 'text': 'Helpful local business and friendly staff.'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(BusinessReview.objects.filter(company=self.company, user=self.member).exists())

    def test_member_registration_returns_to_active_feature(self):
        verify_account_phone(self.client, '9876543210')
        response = self.client.post(reverse('register_process'), {
            'user_type': 'employee', 'phone': '9876543210', 'password': 'test-pass',
            'first_name': 'New member', 'pincode': '600001',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.assertEqual(User.objects.get(phone='9876543210').user_type, 'individual')

    def test_business_profile_updates_without_career_or_reward_fields(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('employer_dashboard'), {
            'first_name': 'Shop owner', 'company_name': 'Updated Local Shop',
            'industry': 'Retail', 'pincode': '600001', 'preferred_pincode_1': '600002',
            'business_phone': '9876500001',
        })
        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.company.refresh_from_db()
        self.assertEqual(self.owner.preferred_pincode_1, '600002')
        self.assertEqual(self.owner.business_phone, '9876500001')
        self.assertEqual(self.company.company_name, 'Updated Local Shop')

    def test_general_messaging_survives_without_career_actions(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse('start_conversation', args=[self.owner.pk]))
        self.assertEqual(response.status_code, 302)
        conversation = Conversation.objects.get()
        self.assertEqual(self.client.get(response.url).status_code, 200)
        response = self.client.post(reverse('send_message'), {'conv_id': conversation.pk, 'content': 'Hello, are you open today?'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        response = self.client.post(reverse('send_message'), {'conv_id': conversation.pk, 'msg_type': 'interview_invite'})
        self.assertEqual(response.status_code, 400)

    def test_job_sitemaps_removed(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '/sitemaps/jobs.xml')
