"""The nine-feature product boundary must also apply to legacy entry points."""
from io import StringIO

from django.apps import apps
from django.contrib import admin
from django.core.management import call_command, CommandError
from django.db import connection
from django.test import TestCase
from django.urls import NoReverseMatch, Resolver404, resolve, reverse

from community.models import FamilySetup
from newsdesk.models import BirthdayCard, NewsItem
from portal.models import (
    Category, Community, CommunityLeader, CommunityMember, MemberPoints,
    PointAuditLog, PortalNotification,
)

from .assigned_admin import SECTIONS, ScopeForm
from .features import FEATURES
from .models import CompanyProfile, District, PinCode, State, User, UserNotification


class FeatureScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.create_user(
            username='feature-member', password='test-password', user_type='individual',
            pincode='604408', first_name='Neighbour',
        )
        cls.owner = User.objects.create_user(
            username='feature-owner', password='test-password', user_type='shop',
            pincode='604408',
        )
        cls.company = CompanyProfile.objects.create(
            user=cls.owner, company_name='Local scope shop', industry='Retail',
        )
        cls.superadmin = User.objects.create_user(
            username='feature-admin', password='test-password', admin_role='super_admin',
            is_staff=True, is_superuser=True,
        )
        category = Category.objects.create(name='Archive', slug='scope-archive')
        cls.legacy_community = Community.objects.create(
            name='Archived neighbourhood', page_id='scope-archive',
            category=category, created_by=cls.member, pincode='604408',
        )
        cls.family = FamilySetup.objects.create(user=cls.member)
        cls.card = BirthdayCard.objects.create(
            user=cls.member, recipient='Archived recipient', message='A historical wish',
            theme='sunshine', is_public=True,
        )
        state, _ = State.objects.get_or_create(code='SCOPE', defaults={'name': 'Scope state'})
        district, _ = District.objects.get_or_create(state=state, name='Scope district')
        cls.pin, _ = PinCode.objects.get_or_create(code='604408', defaults={'district': district})

    def test_feature_menu_contains_only_the_nine_main_destinations(self):
        self.assertEqual(len(FEATURES), 9)
        self.assertEqual({item['url'] for item in FEATURES}, {
            '/products/', '/businesses/', '/advertise/', '/news/', '/flicks/',
            '/advertise/register/', '/messages/', '/register/?type=company', '/profile/edit/',
        })

    def test_retired_routes_reject_guests_members_and_admins_without_deleting_history(self):
        paths = [
            '/community/', '/community/marketplace/', '/community/family/',
            '/portal/', '/portal/flicks/', '/portal/c/scope-archive/',
            '/portal/admin/communities/', '/super-admin/badges/',
            '/news/birthday/', f'/news/birthday/{self.card.pk}/',
            f'/news/birthday/{self.card.pk}/remove/', '/news/api/birthday/',
            '/network/', '/jobs/', '/tuition/', '/health/',
        ]
        for user in (None, self.member, self.superadmin):
            self.client.logout()
            if user:
                self.client.force_login(user)
            for path in paths:
                with self.subTest(user=user.pk if user else 'guest', path=path):
                    with self.assertRaises(Resolver404):
                        resolve(path)
                    self.assertEqual(self.client.get(path).status_code, 404)
                    self.assertEqual(self.client.post(path, {'action': 'delete'}).status_code, 404)
        self.assertTrue(Community.objects.filter(pk=self.legacy_community.pk).exists())
        self.assertTrue(FamilySetup.objects.filter(pk=self.family.pk).exists())
        self.assertTrue(BirthdayCard.objects.filter(pk=self.card.pk).exists())

    def test_retired_route_names_cannot_be_reversed(self):
        for name in ('community_hub', 'portal_home', 'super_admin_badges',
                     'newsdesk:birthday', 'newsdesk:api_birthday'):
            with self.subTest(name=name), self.assertRaises(NoReverseMatch):
                reverse(name)

    def test_main_feature_pages_render_for_members(self):
        self.client.force_login(self.member)
        for path in ('/', '/products/', '/businesses/', '/advertise/', '/news/', '/flicks/',
                     '/advertise/register/', '/messages/', '/business/create/',
                     '/account/', '/profile/edit/', '/my-accounts/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                for retired_link in ('href="/portal/', 'href="/community/',
                                     'href="/news/birthday/', 'Find jobs near me'):
                    self.assertNotContains(response, retired_link)

    def test_guest_home_and_existing_registration_gate_remain(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        for path in ('/products/', '/businesses/', '/advertise/', '/news/', '/flicks/', '/messages/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith('/register/?next='))

    def test_former_community_leader_uses_personal_dashboard(self):
        CommunityLeader.objects.create(
            community=self.legacy_community, user=self.member, role='president', status='accepted',
        )
        self.client.force_login(self.member)
        self.assertRedirects(self.client.get('/dashboard/'), '/account/', fetch_redirect_response=False)

    def test_retired_models_stay_in_schema_but_not_in_admin_editors(self):
        self.assertIsNotNone(apps.get_model('portal', 'Community'))
        self.assertIsNotNone(apps.get_model('community', 'FamilySetup'))
        self.assertTrue({'portal_community', 'community_familysetup', 'newsdesk_birthdaycard'}
                        <= set(connection.introspection.table_names()))
        self.assertFalse(any(model._meta.app_label in {'portal', 'community'}
                             for model in admin.site._registry))
        self.assertNotIn(BirthdayCard, admin.site._registry)
        self.assertIn(CompanyProfile, admin.site._registry)
        self.assertIn(NewsItem, admin.site._registry)

    def test_existing_admin_cannot_reach_retired_editors(self):
        self.client.force_login(self.superadmin)
        for path in ('/admin/portal/community/', '/admin/newsdesk/birthdaycard/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_community_moderation_is_not_assignable_or_actionable(self):
        self.assertNotIn('community', SECTIONS)
        self.assertNotIn('community', dict(ScopeForm.base_fields['sections'].choices))
        self.client.force_login(self.superadmin)
        self.assertEqual(self.client.get('/admin-workspace/community/').status_code, 403)
        self.assertEqual(self.client.post(
            f'/admin-workspace/community/{self.legacy_community.pk}/action/',
            {'action': 'approve'},
        ).status_code, 403)
        self.legacy_community.refresh_from_db()
        self.assertFalse(self.legacy_community.is_verified)

    def test_retired_points_signals_do_not_create_rewards_or_notifications(self):
        CommunityMember.objects.create(
            community=self.legacy_community, user=self.owner, status='approved',
        )
        self.assertFalse(MemberPoints.objects.exists())
        self.assertFalse(PointAuditLog.objects.exists())
        self.assertFalse(PortalNotification.objects.exists())

    def test_retired_birthday_command_cannot_send_notifications(self):
        before = UserNotification.objects.count()
        with self.assertRaisesMessage(CommandError, 'have been retired'):
            call_command('send_birthday_notifications', stdout=StringIO())
        self.assertEqual(UserNotification.objects.count(), before)
        self.assertTrue(FamilySetup.objects.filter(pk=self.family.pk).exists())

    def test_news_reading_and_editor_forms_remain_without_card_links(self):
        story = NewsItem.objects.create(
            pincode=self.pin, author=self.superadmin, title='Local shops open this week',
            body='News from local shop owners in Vandavasi.', status='published',
        )
        self.client.force_login(self.member)
        response = self.client.get('/news/?pincode=604408')
        self.assertContains(response, story.title)
        self.assertNotContains(response, '/news/birthday/')
        self.client.force_login(self.superadmin)
        for name in ('newsdesk:create', 'newsdesk:manage', 'newsdesk:submissions'):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_owner_and_admin_support_tools_remain_available(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/employer/dashboard/').status_code, 200)
        self.client.force_login(self.superadmin)
        for path in ('/super-admin/', '/super-admin/users/', '/super-admin/ads/',
                     '/super-admin/analytics/', '/super-admin/shop-directory/',
                     '/super-admin/product-requests/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
