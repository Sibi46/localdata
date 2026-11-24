from io import BytesIO
from unittest.mock import patch
from PIL import Image
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import CompanyProfile, User


@override_settings(SITE_URL='https://www.localfrom.com')
class ShopShareTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('share-owner', user_type='shop')
        cls.other = User.objects.create_user('share-other', user_type='shop')
        cls.member = User.objects.create_user('share-member')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Vandavasi Store')
        cls.other_shop = CompanyProfile.objects.create(user=cls.other, company_name='Another Store')

    def test_owner_page_contains_canonical_url_and_safe_whatsapp_link(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('shop_share'))
        url = 'https://www.localfrom.com' + self.shop.get_absolute_url()
        self.assertContains(response, url)
        self.assertEqual(response.context['company'], self.shop)
        self.assertTrue(response.context['whatsapp_url'].startswith('https://wa.me/?text='))
        self.assertIn('no-store', response['Cache-Control'])

    def test_qr_payload_is_canonical_and_image_is_downloadable(self):
        self.client.force_login(self.owner)
        import qrcode
        real = qrcode.QRCode.add_data
        payloads = []
        def spy(instance, data, *args, **kwargs):
            payloads.append(data)
            return real(instance, data, *args, **kwargs)
        with patch('qrcode.QRCode.add_data', spy):
            response = self.client.get(reverse('shop_share_qr')+'?download=1')
        self.assertEqual(payloads, ['https://www.localfrom.com' + self.shop.get_absolute_url()])
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(response['Content-Disposition'].startswith('attachment;'))
        self.assertIn(self.shop.company_id.lower(), response['Content-Disposition'])
        image = Image.open(BytesIO(response.content))
        self.assertEqual(image.width, image.height)
        self.assertGreaterEqual(image.width, 290)
        self.assertEqual(image.convert('RGB').getpixel((0, 0)), (255, 255, 255))

    def test_each_owner_gets_their_own_qr_and_cannot_select_another_shop(self):
        self.client.force_login(self.owner)
        own = self.client.get(reverse('shop_share_qr')).content
        response = self.client.get(reverse('shop_share'), {'shop': self.other_shop.pk})
        self.assertEqual(response.context['company'], self.shop)
        self.client.force_login(self.other)
        self.assertNotEqual(own, self.client.get(reverse('shop_share_qr')).content)

    def test_guest_and_nonowners_cannot_use_owner_tools_and_post_is_rejected(self):
        for name in ['shop_share', 'shop_share_qr']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)
        self.client.force_login(self.member)
        for name in ['shop_share', 'shop_share_qr']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse('shop_share_qr')).status_code, 405)
