from django import forms
from django.template.loader import render_to_string
from django.test import TestCase, SimpleTestCase

from .account import BusinessDetailsForm
from .models import CompanyProfile, Product, User
from .shop_categories import ShopCategoriesField
from .simple_accounts import BusinessForm


class ShopCategoryValidationTests(SimpleTestCase):
    def test_normalizes_duplicates_and_keeps_custom_categories(self):
        field = ShopCategoriesField(required=False, max_length=100)
        self.assertEqual(field.clean(' food, bakery, FOOD, Home made '), 'Food, Bakery, Home made')
        self.assertEqual(field.clean(''), '')
        self.assertEqual(field.clean('Old local business'), 'Old local business')

    def test_limits_category_count_and_total_length(self):
        field = ShopCategoriesField(required=False, max_length=100)
        for value in ('Food,Bakery,Cafe,Clothing,Other,Snacks', 'x' * 101):
            with self.assertRaises(forms.ValidationError):
                field.clean(value)

    def test_widget_available_for_registration_and_edit(self):
        for form, name in [(BusinessForm(), 'category'), (BusinessDetailsForm(), 'industry')]:
            html = str(form[name])
            self.assertIn('data-category-picker', html)
            self.assertIn('data-category-option="Food"', html)
            self.assertIn('data-category-custom', html)

    def test_tags_escape_user_text_and_handle_legacy_categories(self):
        html = render_to_string('includes/shop_category_tags.html', {'category': 'Bakery, <script>alert(1)</script>'})
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertEqual(html.count('class="shop-category-tag"'), 2)
        self.assertIn('Local shop', render_to_string('includes/shop_category_tags.html', {'category': ''}))


class ShopCategoryIntegrationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('category-owner', user_type='shop')
        self.shop = CompanyProfile.objects.create(user=self.owner, company_name='Category shop', industry='Clothing')
        self.client.force_login(self.owner)

    def test_multiple_categories_saved_and_rendered_as_separate_tags(self):
        form = BusinessDetailsForm({'company_name': self.shop.company_name,
                                    'industry': 'Food, Bakery, Handmade snacks'}, instance=self.shop)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.industry, 'Food, Bakery, Handmade snacks')
        for url in (self.shop.get_absolute_url(), '/businesses/', '/'):
            response = self.client.get(url)
            self.assertContains(response, 'class="shop-category-tag">Bakery</span>')
            self.assertContains(response, 'class="shop-category-tag">Handmade snacks</span>')

    def test_food_discovery_includes_a_secondary_food_category_and_products(self):
        self.shop.industry = 'Groceries, Bakery'
        self.shop.save()
        product = Product.objects.create(shop=self.shop, name='Bread', category='Fresh', price=None, image='products/test.jpg')
        response = self.client.get('/food/')
        self.assertContains(response, 'Bread')
        self.assertIn(self.shop, response.context['matching_shops'])
        self.assertIn(product, list(response.context['products']))

    def test_category_search_finds_a_secondary_category(self):
        self.shop.industry = 'Groceries, Bakery'
        self.shop.save()
        response = self.client.get('/businesses/', {'q': 'Bakery'})
        self.assertContains(response, self.shop.company_name)
