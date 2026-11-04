from importlib import import_module
import json
from types import SimpleNamespace
import uuid

from django.apps import apps
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse

from .models import AdPost, CompanyProfile, LocalOffer, Product, PromotionEvent, User


class MemberExperienceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('reader-member', first_name='Reader', phone='9876500012', pincode='604408', city='Vandavasi', user_type='individual')
        cls.owner = User.objects.create_user('shop-member', user_type='shop')
        cls.company = CompanyProfile.objects.create(user=cls.owner, company_name='Members Shop')

    def test_reader_account_has_personal_details_and_no_shop_management(self):
        self.client.force_login(self.user)
        response = self.client.get('/account/')
        for text in ('Reader', '9876500012', '604408', 'Vandavasi', 'Register your shop'):
            self.assertContains(response, text)
        for text in ('Manage my shop', 'My ads', 'My business registration'):
            self.assertNotContains(response, text)
        self.assertNotContains(self.client.get('/products/'), 'Manage my products')
        self.assertRedirects(self.client.get('/employer/dashboard/'), '/account/', fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('product_easy_add')).status_code, 404)
        self.assertEqual(self.client.get(reverse('shop_performance')).status_code, 404)

    def test_actual_shop_registration_enables_management_not_role_string_alone(self):
        self.user.user_type = 'shop'
        self.user.save(update_fields=['user_type'])
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get('/products/'), 'Manage my products')
        self.assertRedirects(self.client.get('/dashboard/'), '/account/', fetch_redirect_response=False)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get('/account/'), 'Manage my shop')
        self.assertContains(self.client.get('/products/'), 'Manage my products')

    def test_home_has_language_selector_and_personal_account_link(self):
        response = self.client.get('/')
        self.assertContains(response, 'data-home-language')
        self.assertContains(response, 'data-product-language')
        self.assertContains(response, 'js/home-language.js')
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/'), 'href="/account/"')

    def test_free_tier_migration_keeps_products_and_approved_limits(self):
        self.company.product_limit = 10
        self.company.save(update_fields=['product_limit'])
        for index in range(6):
            Product.objects.create(shop=self.company, name=f'Kept {index}', image='products/kept.jpg', price=10)
        approved = CompanyProfile.objects.create(user=self.user, company_name='Approved', product_limit=10, product_access_status='approved')
        migration = import_module('jobs.migrations.0072_five_free_products_and_promotion_events')
        migration.apply_five_free_products(apps, SimpleNamespace(connection=connection))
        self.company.refresh_from_db(); approved.refresh_from_db()
        self.assertEqual(self.company.product_limit, 5)
        self.assertEqual(approved.product_limit, 10)
        self.assertEqual(self.company.products.count(), 6)


class PromotionMetricsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('metrics-owner', user_type='shop')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Metrics Shop')
        cls.reader = User.objects.create_user('metrics-reader')
        cls.other = User.objects.create_user('metrics-other', user_type='shop')
        CompanyProfile.objects.create(user=cls.other, company_name='Other Shop')
        cls.offer = LocalOffer.objects.create(owner=cls.owner, business_name='Metrics Shop', title='Own offer', discount_text='10%', is_active=True)
        cls.ad = AdPost.objects.create(user=cls.owner, company_name='Metrics Shop', title='Own ad', description='Offer', image='ads/test.jpg', status='approved')

    def event(self, action='view', kind='offer', pk=None, event_id=None):
        return {'id': str(event_id or uuid.uuid4()), 'action': action, 'kind': kind, 'object': pk or self.offer.pk}

    def send(self, events, client=None):
        return (client or self.client).post(reverse('promotion_collect'), {'events': json.dumps(events)})

    def test_views_clicks_unique_members_and_replay(self):
        self.client.force_login(self.reader)
        event = self.event()
        self.assertEqual(self.send([event, self.event('click')]).status_code, 204)
        self.send([event])
        self.send([self.event()])
        self.assertEqual(PromotionEvent.objects.count(), 3)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('shop_performance'))
        record = response.context['offers'].get()
        self.assertEqual((record.measured_views, record.measured_clicks, record.member_reach), (2, 1, 1))
        self.assertNotContains(response, self.reader.username)

    def test_owners_admins_and_unpublished_items_do_not_count(self):
        self.client.force_login(self.owner)
        self.send([self.event()])
        self.assertFalse(PromotionEvent.objects.exists())
        self.offer.is_active = False; self.offer.save(update_fields=['is_active'])
        self.client.force_login(self.reader)
        self.send([self.event()])
        self.assertFalse(PromotionEvent.objects.exists())

    def test_owner_dashboard_is_scoped(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse('shop_performance'))
        self.assertNotContains(response, 'Own offer')
        self.assertNotContains(response, 'Own ad')
        self.assertEqual(response.context['ads'].count(), 0)

    def test_csrf_methods_batch_limits_and_privacy(self):
        self.assertEqual(self.client.get(reverse('promotion_collect')).status_code, 405)
        secure = Client(enforce_csrf_checks=True)
        self.assertEqual(self.send([self.event()], secure).status_code, 403)
        self.assertEqual(self.send([self.event() for _ in range(21)]).status_code, 400)
        self.client.post(reverse('promotion_collect'), {'events': json.dumps([self.event()])}, HTTP_SEC_GPC='1')
        self.assertFalse(PromotionEvent.objects.exists())
