from unittest.mock import patch
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from jobportal.test_support import TemporaryMediaMixin
from .models import CompanyProfile, Product, ProductImage, User
from .test_shop_catalog import image_file


class QuickProductTests(TemporaryMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('quick-owner', user_type='shop')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Easy Shop')
        cls.other = User.objects.create_user('quick-other', user_type='shop')
        cls.other_shop = CompanyProfile.objects.create(user=cls.other, company_name='Other Shop')
        cls.viewer = User.objects.create_user('quick-viewer', user_type='individual')

    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)
        self.url = reverse('product_easy_publish')

    def payload(self, **overrides):
        values = {'draft_id': str(uuid4()), 'name': 'Cotton shirt', 'price': '500',
                  'discount_percent': '10', 'images': [image_file()]}
        values.update(overrides)
        return values

    def test_editor_and_dashboard_offer_photo_entry(self):
        response = self.client.get(reverse('product_easy_add'))
        self.assertContains(response, 'data-easy-products')
        self.assertContains(response, 'data-remaining="3"')
        self.assertContains(response, reverse('product_add'))
        self.assertContains(self.client.get(reverse('employer_dashboard')), reverse('product_easy_add'))

    def test_six_photos_and_discount_publish_into_current_shop(self):
        data = self.payload(images=[image_file(f'photo{i}.png') for i in range(6)], shop=self.other_shop.pk)
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        product = Product.objects.get()
        self.assertEqual(product.shop_id, self.shop.pk)
        self.assertTrue(product.is_active)
        self.assertEqual(str(product.sale_price), '450.00')
        self.assertEqual(product.images.count(), 5)
        self.assertEqual(response.json()['id'], product.pk)

    def test_retry_of_same_draft_returns_existing_product(self):
        token = str(uuid4())
        first = self.client.post(self.url, self.payload(draft_id=token))
        second = self.client.post(self.url, self.payload(draft_id=token))
        self.assertEqual(first.json(), second.json())
        self.assertEqual(Product.objects.count(), 1)

    def test_retry_receipts_are_scoped_to_owner(self):
        token = str(uuid4())
        first = self.client.post(self.url, self.payload(draft_id=token))
        self.client.force_login(self.other)
        second = self.client.post(self.url, self.payload(draft_id=token))
        self.assertNotEqual(first.json()['id'], second.json()['id'])
        self.assertEqual(self.other_shop.products.count(), 1)

    def test_limit_cannot_be_bypassed_and_replay_works_when_full(self):
        token = str(uuid4())
        first = self.client.post(self.url, self.payload(draft_id=token))
        for _ in range(2):
            self.assertEqual(self.client.post(self.url, self.payload()).status_code, 200)
        response = self.client.post(self.url, self.payload())
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.json()['limit_reached'])
        self.assertEqual(self.client.post(self.url, self.payload(draft_id=token)).json(), first.json())
        self.assertEqual(self.shop.products.count(), 3)

    def test_approved_allowance_is_respected(self):
        self.shop.product_limit = 4
        self.shop.save(update_fields=['product_limit'])
        for _ in range(4):
            self.assertEqual(self.client.post(self.url, self.payload()).status_code, 200)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)

    def test_invalid_details_and_images_create_nothing_and_allow_correction(self):
        cases = [{'price': '0'}, {'price': '-1'}, {'discount_percent': '101'},
                 {'discount_percent': '-1'}, {'name': ''}, {'name': 'x' * 161},
                 {'images': []}, {'images': [image_file() for _ in range(7)]},
                 {'images': [SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')]}]
        for values in cases:
            with self.subTest(values=list(values)):
                token = str(uuid4())
                self.assertEqual(self.client.post(self.url, self.payload(draft_id=token, **values)).status_code, 400)
                self.assertFalse(Product.objects.exists())
                corrected = self.client.post(self.url, self.payload(draft_id=token))
                self.assertEqual(corrected.status_code, 200)
                Product.objects.all().delete()

    def test_post_only_and_csrf_required(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url, self.payload()).status_code, 403)
        self.assertFalse(Product.objects.exists())

    def test_guest_non_shop_and_inactive_owner_cannot_publish(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('product_easy_add')).status_code, 302)
        self.assertIn(self.client.post(self.url, self.payload()).status_code, (302, 401))
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(reverse('product_easy_add')).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 404)
        self.owner.is_active = False
        self.owner.save(update_fields=['is_active'])
        self.client.force_login(self.owner)
        self.assertIn(self.client.post(self.url, self.payload()).status_code, (302, 401, 404))
        self.assertFalse(Product.objects.exists())

    def test_bad_token_rejected(self):
        for token in ('', 'invalid'):
            self.assertEqual(self.client.post(self.url, self.payload(draft_id=token)).status_code, 400)
        self.assertFalse(Product.objects.exists())

    def test_processing_draft_is_not_created_twice(self):
        from django.conf import settings
        from django.core.cache import caches
        token = str(uuid4())
        cache = caches[settings.OTP_CACHE_ALIAS]
        cache.set(f'product-entry:{self.owner.pk}:{self.shop.pk}:{token}', 'processing')
        self.assertEqual(self.client.post(self.url, self.payload(draft_id=token)).status_code, 409)
        self.assertFalse(Product.objects.exists())

    def test_receipt_failure_preserves_committed_product_and_blocks_blind_retry(self):
        from django.conf import settings
        from django.core.cache import caches
        from pathlib import Path
        token = str(uuid4())
        cache = caches[settings.OTP_CACHE_ALIAS]
        with patch.object(cache, 'set', side_effect=RuntimeError('cache unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, self.payload(draft_id=token))
        product = Product.objects.get()
        self.assertTrue(Path(product.image.path).is_file())
        self.assertEqual(self.client.post(self.url, self.payload(draft_id=token)).status_code, 409)
        self.assertEqual(Product.objects.count(), 1)

    def test_gallery_failure_rolls_back_rows_and_cleans_new_uploads(self):
        from django.conf import settings
        from pathlib import Path
        before = set(Path(settings.MEDIA_ROOT).rglob('*'))
        with patch('jobs.quick_products.ProductImage.save', side_effect=RuntimeError('storage failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, self.payload(images=[image_file('one.png'), image_file('two.png')]))
        self.assertFalse(Product.objects.exists())
        self.assertFalse(ProductImage.objects.exists())
        self.assertFalse([path for path in set(Path(settings.MEDIA_ROOT).rglob('*')) - before if path.is_file()])
