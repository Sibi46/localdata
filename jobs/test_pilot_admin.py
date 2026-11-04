from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import CompanyProfile, LocalOffer, Product, User


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PilotAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('pilot-admin-test', phone='9876500001', password='Test-password-273', admin_role='super_admin')
        cls.customer = User.objects.create_user('pilot-customer', first_name='Pilot Customer', phone='9876500002', password='Test-password-273')
        cls.owner = User.objects.create_user('pilot-shop-owner', phone='9876500003', city='Vandavasi', is_active=False)
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Pilot Stationery', description='Everything for school and office')
        cls.product = Product.objects.create(shop=cls.shop, name='Hidden notebook', price='100', is_active=False, image='products/test.png')
        LocalOffer.objects.create(owner=cls.owner, business_name='Pilot Stationery', title='Pending pencil offer', discount_text='10% off', is_active=False)

    def setUp(self):
        cache.clear()

    def test_home_pilot_content_and_footer(self):
        self.client.force_login(self.customer)
        response = self.client.get('/')
        self.assertContains(response, 'PILOT VERSION')
        self.assertContains(response, 'Vandavasi')
        self.assertContains(response, reverse('pilot_admin_login'))
        self.assertNotContains(response, 'What brings you here?')

    def test_anonymous_and_regular_users_cannot_read_admin_records(self):
        urls = [reverse('super_admin_dashboard'), reverse('super_admin_users'), reverse('pilot_admin_shop', args=[self.shop.pk]), reverse('pilot_admin_user', args=[self.customer.pk])]
        for url in urls:
            self.assertRedirects(self.client.get(url), reverse('pilot_admin_login'))
        self.client.force_login(self.customer)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.customer.is_staff = True
        self.customer.save()
        self.assertEqual(self.client.get(urls[0]).status_code, 403)

    def test_login_requires_superadmin_password_and_active_account(self):
        url = reverse('pilot_admin_login')
        response = self.client.post(url, {'phone': self.customer.phone, 'password': 'Test-password-273'})
        self.assertContains(response, 'Invalid superadmin')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post(url, {'phone': self.admin.phone, 'password': 'Test-password-273'}), reverse('super_admin_dashboard'))
        self.assertIn('no-store', self.client.get(reverse('super_admin_dashboard'))['Cache-Control'])
        self.assertEqual(self.client.get(reverse('pilot_admin_logout')).status_code, 405)
        self.client.post(reverse('pilot_admin_logout'))
        self.admin.is_active = False
        self.admin.save()
        self.assertContains(self.client.post(url, {'phone': self.admin.phone, 'password': 'Test-password-273'}), 'Invalid superadmin')

    def test_login_throttle(self):
        for _ in range(5):
            self.client.post(reverse('pilot_admin_login'), {'phone': self.admin.phone, 'password': 'incorrect'})
        response = self.client.post(reverse('pilot_admin_login'), {'phone': self.admin.phone, 'password': 'Test-password-273'})
        self.assertEqual(response.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_accepts_formatted_phone_and_copied_password_spaces(self):
        for phone in ['+91 98765 00001','919876500001','98765-00001']:
            self.client.logout()
            response=self.client.post(reverse('pilot_admin_login'),{'phone':phone,'password':' Test-password-273 '})
            self.assertRedirects(response,reverse('super_admin_dashboard'))
        self.client.logout()
        response=self.client.post(reverse('pilot_admin_login'),{'phone':self.customer.phone,'password':' Test-password-273 '})
        self.assertContains(response,'Invalid superadmin')
        self.assertNotIn('_auth_user_id',self.client.session)

    def test_lists_search_details_and_unpublished_shop_content(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('super_admin_dashboard'))
        self.assertContains(response, 'Pilot Stationery')
        self.assertContains(response, 'Inactive')
        self.assertNotContains(self.client.get(reverse('super_admin_dashboard'), {'q':'missing shop'}), 'Pilot Stationery')
        self.assertContains(self.client.get(reverse('super_admin_dashboard'), {'q':'Vandavasi'}), 'Pilot Stationery')
        self.assertContains(self.client.get(reverse('super_admin_users'), {'q':self.customer.phone}), 'Pilot Customer')
        response = self.client.get(reverse('pilot_admin_shop', args=[self.shop.pk]))
        self.assertContains(response, 'Hidden notebook')
        self.assertContains(response, 'Pending pencil offer')
        self.assertContains(response, self.owner.phone)
        response = self.client.get(reverse('pilot_admin_user', args=[self.owner.pk]))
        self.assertContains(response, reverse('pilot_admin_shop', args=[self.shop.pk]))
        self.assertNotContains(response, self.owner.password)
        self.assertEqual(self.client.get(reverse('pilot_admin_shop', args=[99999])).status_code, 404)

    def test_user_list_is_paginated(self):
        User.objects.bulk_create([User(username=f'page-user-{i}') for i in range(23)])
        self.client.force_login(self.admin)
        response = self.client.get(reverse('super_admin_users'))
        self.assertEqual(len(response.context['page']), 20)
        response = self.client.get(reverse('super_admin_users'), {'page':2})
        self.assertEqual(len(response.context['page']), 6)
