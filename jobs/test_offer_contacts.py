from django.test import TestCase, override_settings
from .models import User, CompanyProfile, LocalOffer
from .offer_links import attach_offer_links, whatsapp_number


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class OfferContactTests(TestCase):
    def setUp(self):
        reader = User.objects.create_user('contact-reader', user_type='individual')
        self.client.force_login(reader)

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('contact-store', user_type='shop', phone='9876543210', whatsapp='+91 98765 43210')
        cls.profile = CompanyProfile.objects.create(user=cls.owner, company_name='NSG Cafe')
        other = User.objects.create_user('unrelated-store', user_type='shop', phone='9123456789')
        cls.other = CompanyProfile.objects.create(user=other, company_name='Testing')

    def offer(self, **kwargs):
        fields = dict(business_name='NSG CAFE', title='Example offer', discount_text='10%', is_active=True)
        fields.update(kwargs)
        return LocalOffer.objects.create(**fields)

    def test_ownerless_offer_resolves_unambiguous_store_and_public_contact(self):
        offer = attach_offer_links(self.offer(contact_phone='1234567890', link_url='https://wa.me/911234567890'))
        self.assertEqual(offer.store_profile, self.profile)
        self.assertEqual(offer.store_url, '/business/' + self.profile.company_id + '/')
        self.assertEqual(offer.whatsapp_url, 'https://wa.me/919876543210')

    def test_unrelated_owner_does_not_supply_store_or_private_contact(self):
        offer = attach_offer_links(self.offer(business_name='Hotel', owner=self.other.user))
        self.assertIsNone(offer.store_profile)
        self.assertEqual(offer.store_url, f'/offers/{offer.pk}/store/')
        self.assertEqual(offer.whatsapp_url, '')
        response = self.client.get(offer.store_url)
        self.assertContains(response, '<h1 style="margin:20px 0">Hotel</h1>', html=True)
        self.assertNotContains(response, self.other.company_id)
        self.assertContains(response, 'verified WhatsApp contact is not available')

    def test_whatsapp_link_is_never_the_store_destination(self):
        offer = attach_offer_links(self.offer(business_name='Unlisted merchant', link_url='https://wa.me/919876543210'))
        self.assertEqual(offer.store_url, f'/offers/{offer.pk}/store/')
        self.assertEqual(offer.whatsapp_url, 'https://wa.me/919876543210')

    def test_ambiguous_business_names_do_not_guess_a_store(self):
        user = User.objects.create_user('duplicate-cafe', user_type='shop')
        CompanyProfile.objects.create(user=user, company_name='NSG CAFE')
        self.assertIsNone(attach_offer_links(self.offer()).store_profile)

    def test_owner_supplied_contact_is_preserved_for_matching_business(self):
        offer = attach_offer_links(self.offer(owner=self.owner, contact_phone='9765432109'))
        self.assertEqual(offer.whatsapp_phone, '919765432109')

    def test_owner_resolves_duplicate_shop_names(self):
        duplicate = User.objects.create_user('same-name-store', user_type='shop')
        CompanyProfile.objects.create(user=duplicate, company_name='NSG CAFE')
        offer = attach_offer_links(self.offer(owner=self.owner))
        self.assertEqual(offer.store_profile, self.profile)

    def test_inactive_offer_store_is_not_public(self):
        offer = self.offer(is_active=False)
        self.assertEqual(self.client.get(f'/offers/{offer.pk}/store/').status_code, 404)

    def test_phone_formatting_does_not_duplicate_country_codes(self):
        for value in ('9876543210', '+91 98765 43210', '919876543210', '00919876543210'):
            with self.subTest(value=value):
                self.assertEqual(whatsapp_number(value), '919876543210')
        for value in ('', '1234567890', '3456789012', 'abc9876543210', '123'):
            self.assertEqual(whatsapp_number(value), '')
        self.assertEqual(whatsapp_number('+44 20 7946 0123'), '442079460123')
