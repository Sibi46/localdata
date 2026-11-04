"""Scoped moderation for the remaining local marketplace features."""
from django.test import TestCase
from django.urls import reverse
from .assigned_admin import SECTIONS
from .models import AdPost, AdminProfile, District, PinCode, State, User


class AssignedAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('owner', user_type='company')
        cls.admin = User.objects.create_user('scoped', admin_role='scoped_admin')
        state = State.objects.create(name='Tamil Nadu', code='TN')
        district = District.objects.create(state=state, name='Chennai')
        PinCode.objects.create(district=district, code='600001')
        cls.scope = AdminProfile.objects.create(user=cls.admin, role='scoped_admin', state=state, sections=['ads'])
        cls.local = AdPost.objects.create(user=cls.owner, company_name='Local Shop', pincode='600001')
        cls.remote = AdPost.objects.create(user=cls.owner, company_name='Other Shop', pincode='110001')
        cls.unknown = AdPost.objects.create(user=cls.owner, company_name='Unknown Shop', pincode='999999')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_only_assigned_state_is_visible(self):
        response = self.client.get(reverse('assigned_section', args=['ads']))
        self.assertContains(response, 'Local Shop')
        self.assertNotContains(response, 'Other Shop')
        self.assertNotContains(response, 'Unknown Shop')

    def test_cross_state_writes_rejected(self):
        for ad in [self.remote, self.unknown]:
            response = self.client.post(reverse('assigned_action', args=['ads', ad.pk]), {'action': 'approve'})
            self.assertEqual(response.status_code, 404)
            ad.refresh_from_db()
            self.assertEqual(ad.status, 'pending')

    def test_local_ad_can_be_approved(self):
        response = self.client.post(reverse('assigned_action', args=['ads', self.local.pk]), {'action': 'approve'})
        self.assertEqual(response.status_code, 302)
        self.local.refresh_from_db()
        self.assertEqual(self.local.status, 'approved')

    def test_unassigned_section_is_denied(self):
        self.assertEqual(self.client.get(reverse('assigned_section', args=['news'])).status_code, 403)

    def test_disabled_assignment_fails_closed(self):
        self.scope.is_active = False
        self.scope.save()
        self.assertEqual(self.client.get(reverse('assigned_dashboard')).status_code, 404)

    def test_national_scope_can_see_other_states(self):
        self.scope.all_states = True
        self.scope.state = None
        self.scope.save()
        self.assertContains(self.client.get(reverse('assigned_section', args=['ads'])), 'Other Shop')

    def test_retired_sections_are_absent(self):
        self.assertFalse({'jobs', 'quiz', 'campus', 'tuition', 'health', 'vouchers'} & SECTIONS.keys())
