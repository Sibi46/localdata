from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CompanyProfile, Product, User


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class TenProductAllowanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('ten-product-owner', user_type='shop')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Ten Product Shop')

    def test_new_shop_starts_with_ten_free_slots(self):
        self.assertEqual(self.shop.product_limit, 10)

    def test_new_migration_raises_free_tier_without_touching_gallery_or_approved_limits(self):
        from .models import ProductImage
        self.shop.product_limit = 5
        self.shop.product_access_status = 'pending'
        self.shop.requested_product_limit = 25
        self.shop.product_access_note = 'Keep the existing request'
        self.shop.save()
        product = Product.objects.create(shop=self.shop, name='Existing gallery', price=100, image='products/cover.jpg')
        images = [ProductImage.objects.create(product=product, image=f'products/extra-{i}.jpg', position=i) for i in range(1,6)]
        approved_owner = User.objects.create_user('higher-approved-owner')
        approved = CompanyProfile.objects.create(user=approved_owner, company_name='Higher allowance', product_limit=30, product_access_status='approved')
        migration = import_module('jobs.migrations.0074_ten_free_products_two_image_policy')
        migration.upgrade_free_allowance(apps, SimpleNamespace(connection=connection))
        self.shop.refresh_from_db(); approved.refresh_from_db(); product.refresh_from_db()
        self.assertEqual(self.shop.product_limit,10)
        self.assertEqual((self.shop.product_access_status,self.shop.requested_product_limit,self.shop.product_access_note),('pending',25,'Keep the existing request'))
        self.assertEqual((approved.product_limit,approved.product_access_status),(30,'approved'))
        self.assertEqual(product.image.name,'products/cover.jpg')
        self.assertEqual(set(product.images.values_list('pk',flat=True)),{image.pk for image in images})
        migration.upgrade_free_allowance(apps, SimpleNamespace(connection=connection))
        self.assertEqual(CompanyProfile.objects.get(pk=self.shop.pk).product_limit,10)

    def test_migration_only_raises_lower_limits_and_preserves_requests_and_products(self):
        self.shop.product_limit = 3
        self.shop.product_access_status = 'pending'
        self.shop.requested_product_limit = 25
        self.shop.save()
        other = User.objects.create_user('ten-approved-owner')
        approved = CompanyProfile.objects.create(user=other, company_name='Approved Shop', product_limit=25)
        product = Product.objects.create(shop=self.shop, name='Keep this product', price=100, image='products/kept.jpg')
        migrate = import_module('jobs.migrations.0071_ten_free_products').upgrade_free_allowance
        migrate(apps, SimpleNamespace(connection=connection))
        self.shop.refresh_from_db()
        approved.refresh_from_db()
        self.assertEqual(self.shop.product_limit, 10)
        self.assertEqual(approved.product_limit, 25)
        self.assertEqual((self.shop.product_access_status, self.shop.requested_product_limit), ('pending', 25))
        self.assertTrue(Product.objects.filter(pk=product.pk, name='Keep this product').exists())
        migrate(apps, SimpleNamespace(connection=connection))
        self.assertEqual(CompanyProfile.objects.get(pk=self.shop.pk).product_limit, 10)

    def test_limit_page_has_both_call_buttons_and_automatic_popup(self):
        for index in range(10):
            Product.objects.create(shop=self.shop, name=f'Product {index}', price=100, image='products/kept.jpg')
        self.client.force_login(self.owner)
        for route in ('product_add', 'product_easy_add'):
            response = self.client.get(reverse(route))
            self.assertContains(response, 'id="product-limit-dialog"')
            self.assertContains(response, 'data-auto-open')
            self.assertContains(response, 'href="tel:+917305675201"')
            self.assertContains(response, 'href="tel:+919361240355"')
        dashboard = self.client.get(reverse('employer_dashboard'))
        self.assertContains(dashboard, 'data-product-count="10" data-product-limit="10"')

    def test_guest_home_popup_is_present_without_changing_server_gate(self):
        response = self.client.get('/')
        self.assertContains(response, 'id="guest-account-dialog"')
        self.assertContains(response, 'data-guest-create')
        self.assertContains(response, 'home-registration.js')
        self.assertEqual(self.client.get('/products/').status_code, 302)
        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get('/'), 'id="guest-account-dialog"')
