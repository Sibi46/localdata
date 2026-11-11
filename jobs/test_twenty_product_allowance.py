from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase

from .models import CompanyProfile, Product, ProductImage, User


class TwentyProductMigrationTests(TestCase):
    def test_upgrade_preserves_higher_allowances_products_and_pending_requests(self):
        shops = []
        for index, limit in enumerate([3, 10, 19, 20, 35]):
            owner = User.objects.create_user(f'twenty-owner-{index}')
            shops.append(CompanyProfile.objects.create(user=owner, company_name=f'Shop {index}',
                product_limit=limit, product_access_status='pending', requested_product_limit=40,
                product_access_note='Keep this review note'))
        product = Product.objects.create(shop=shops[0], name='Keep product', price=100, image='products/keep.jpg')
        image = ProductImage.objects.create(product=product, image='products/gallery/keep.jpg', position=1)
        upgrade = import_module('jobs.migrations.0076_twenty_free_products').upgrade_free_allowance
        for _ in range(2):
            upgrade(apps, SimpleNamespace(connection=connection))
            self.assertEqual([CompanyProfile.objects.get(pk=shop.pk).product_limit for shop in shops], [20, 20, 20, 20, 35])
        for shop in shops:
            shop.refresh_from_db()
            self.assertEqual((shop.product_access_status, shop.requested_product_limit, shop.product_access_note),
                             ('pending', 40, 'Keep this review note'))
        product.refresh_from_db(); image.refresh_from_db()
        self.assertEqual(product.image.name, 'products/keep.jpg')
        self.assertEqual(image.image.name, 'products/gallery/keep.jpg')
        self.assertEqual(product.shop_id, shops[0].pk)
