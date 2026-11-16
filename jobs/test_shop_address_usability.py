from django.test import TestCase
from django.urls import reverse

from .models import CompanyProfile, User


class ShopAddressUsabilityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('address-owner', phone='9876501789', first_name='Owner')
        self.client.force_login(self.owner)

    def create_shop(self, address=''):
        return self.client.post(reverse('business_create'), {
            'account_type': 'shop', 'name': 'Address shop', 'category': 'Food, Bakery',
            'pincode': '604408', 'city': 'Vandavasi', 'address': address,
        })

    def test_address_is_optional_during_creation(self):
        self.assertEqual(self.create_shop().status_code, 302)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.address, '')
        self.assertTrue(CompanyProfile.objects.filter(user=self.owner).exists())

    def test_address_saved_when_entered_during_creation(self):
        self.assertEqual(self.create_shop('12 Market Street').status_code, 302)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.address, '12 Market Street')

    def test_owner_can_edit_and_clear_shop_address_after_creation(self):
        self.create_shop('12 Market Street')
        shop = CompanyProfile.objects.get(user=self.owner)
        response = self.client.get(reverse('employer_dashboard'))
        self.assertContains(response, 'class="owner-edit-shop"')
        self.assertContains(response, 'Edit shop details')
        self.assertEqual(response.content.count(b'name="address"'), 1)
        for address in ('25 New Street', ''):
            response = self.client.post(reverse('employer_dashboard'), {
                'dashboard_profile': '1', 'first_name': 'Owner', 'last_name': '',
                'email': '', 'whatsapp': '', 'city': 'Vandavasi', 'address': address,
                'company_name': shop.company_name, 'industry': shop.industry,
                'description': '', 'website': '', 'company_size': '',
                'pincode': '604408', 'preferred_pincode_1': '', 'preferred_pincode_2': '',
                'business_phone': '',
            })
            self.assertEqual(response.status_code, 302)
            self.owner.refresh_from_db()
            self.assertEqual(self.owner.address, address)
