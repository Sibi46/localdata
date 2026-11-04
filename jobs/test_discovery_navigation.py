from django.test import TestCase
from django.urls import reverse
from .models import User, CompanyProfile, Advertiser
from .dashboard_features import registered_features
from unittest import skip


class DiscoveryNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('biz-owner', user_type='shop', pincode='600073')
        self.other = User.objects.create_user('other-biz', user_type='shop', pincode='110001')
        CompanyProfile.objects.create(user=self.user, company_name='Nearby no logo')
        CompanyProfile.objects.create(user=self.other, company_name='Remote business')

    def test_business_discovery_includes_no_logo_and_scopes_pin(self):
        self.client.force_login(self.user)
        response = self.client.get('/')
        self.assertEqual([p.company_name for p in response.context['business_logos']], ['Nearby no logo'])
        self.assertContains(response, 'Nearby no logo')
        html = response.content.decode()
        self.assertIn('/businesses/', html)
        self.assertIn('/business/' + self.user.company.company_id + '/', html)
        self.client.logout()
        self.assertEqual(len(self.client.get('/').context['business_logos']), 2)

    @skip('Tuition registration retired; current dashboard coverage is in jobs.test_feature_scope')
    def test_features_only_own_approved_services_and_pending_separate(self):
        teacher = TeacherProfile.objects.create(owner=self.user, kind='academy', name='Mine', pincode='600073', status='pending')
        TeacherProfile.objects.create(owner=self.other, kind='teacher', name='Other', pincode='110001', status='approved')
        active, pending = registered_features(self.user)
        self.assertEqual([f['label'] for f in active], ['Business profile'])
        self.assertEqual([f['label'] for f in pending], ['Tuition / Academy'])
        teacher.status = 'approved'; teacher.save()
        active, pending = registered_features(self.user)
        self.assertIn('Tuition / Academy', [f['label'] for f in active])
        self.assertFalse(pending)
        teacher.status = 'suspended'; teacher.save()
        self.assertNotIn('Tuition / Academy', [f['label'] for f in registered_features(self.user)[0]])

    def test_login_plus_and_coupon_header_removed(self):
        response = self.client.get('/login/')
        self.assertNotContains(response, 'class="bn-plus-btn"')
        self.client.force_login(self.user)
        response = self.client.get('/coupons/activate/')
        self.assertEqual(response.status_code, 404)
