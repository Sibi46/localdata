from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse

from jobportal.test_support import TemporaryMediaMixin
from .models import CompanyProfile, Product, User
from .test_shop_catalog import image_file


class OptionalProductPriceTests(TemporaryMediaMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.owner = User.objects.create_user('optional-price-owner', user_type='shop')
        self.shop = CompanyProfile.objects.create(user=self.owner, company_name='Price Test Shop')
        self.client.force_login(self.owner)

    def publish(self, price='', discount='0'):
        return self.client.post(reverse('product_easy_publish'), {
            'draft_id': str(uuid4()), 'name': 'Test product',
            'price': price, 'discount_percent': discount, 'images': [image_file()],
        })

    def test_publish_without_price_shows_contact_message(self):
        response = self.publish(discount='20')
        self.assertEqual(response.status_code, 200)
        product = Product.objects.get()
        self.assertIsNone(product.price)
        self.assertIsNone(product.sale_price)
        self.assertEqual(product.discount_percent, 20)
        detail = self.client.get(product.get_absolute_url())
        self.assertContains(detail, 'Ask shop for price')
        self.assertNotContains(detail, '<del>')
        self.assertContains(self.client.get('/products/'), 'Ask shop for price')

    def test_discount_calculates_and_displays_selling_price(self):
        self.assertEqual(self.publish('500', '10').status_code, 200)
        product = Product.objects.get()
        self.assertEqual(product.sale_price, Decimal('450.00'))
        detail = self.client.get(product.get_absolute_url())
        self.assertContains(detail, '450.00')
        self.assertContains(detail, '<del>')

    def test_explicit_zero_and_negative_prices_still_rejected(self):
        for price in ('0', '-1'):
            self.assertEqual(self.publish(price).status_code, 400)
        self.assertEqual(Product.objects.count(), 0)

    def test_standard_form_accepts_blank_price_and_edit_can_remove_price(self):
        response = self.client.post(reverse('product_add'), {
            'name': 'Optional price', 'price': '', 'discount_percent': '',
            'images': [image_file()], 'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get()
        self.assertIsNone(product.price)
        product.price = Decimal('100')
        product.save()
        response = self.client.post(reverse('product_edit', args=[product.pk]), {
            'name': product.name, 'price': '', 'discount_percent': '10', 'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertIsNone(product.price)

    def test_unknown_prices_sort_last_in_both_directions(self):
        self.publish('')
        self.publish('500', '10')
        self.publish('100')
        for sort, expected in [('price_low', [Decimal('100'), Decimal('500'), None]),
                               ('price_high', [Decimal('500'), Decimal('100'), None])]:
            response = self.client.get('/products/', {'sort': sort})
            self.assertEqual([p.price for p in response.context['products']], expected)
