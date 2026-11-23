from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from .models import (AdminActivity, BusinessGalleryImage, CompanyProfile, Conversation,
                     LocalOffer, Product, ProductImage, User)


class AdminListingDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('listing-superadmin', admin_role='super_admin')
        cls.owner = User.objects.create_user('listing-owner', user_type='shop')
        cls.member = User.objects.create_user('listing-member')
        cls.company = CompanyProfile.objects.create(user=cls.owner, company_name='Delete test shop')
        cls.product = Product.objects.create(shop=cls.company, name='Delete test item', image='products/item.jpg')
        cls.extra = Product.objects.create(shop=cls.company, name='Keep item', image='products/extra.jpg')
        cls.photo = ProductImage.objects.create(product=cls.product, image='products/second.jpg', position=1)
        cls.offer = LocalOffer.objects.create(owner=cls.owner, business_name='Delete test shop', title='Offer', discount_text='Sale')
        cls.gallery = BusinessGalleryImage.objects.create(user=cls.owner, image='business_gallery/test.jpg')
        cls.thread = Conversation.objects.create(user_a=cls.owner, user_b=cls.member)

    def test_get_is_confirmation_only_and_invalid_post_cannot_delete(self):
        self.client.force_login(self.admin)
        for name, pk in [('admin_product_delete', self.product.pk), ('admin_shop_delete', self.company.pk)]:
            url = reverse(name, args=[pk])
            self.assertContains(self.client.get(url), 'Type DELETE to confirm')
            for data in [{}, {'confirmation': 'DELETE'}, {'reason': 'Duplicate', 'confirmation': 'wrong'}]:
                self.assertEqual(self.client.post(url, data).status_code, 200)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.assertTrue(CompanyProfile.objects.filter(pk=self.company.pk).exists())
        self.assertFalse(AdminActivity.objects.filter(action='delete').exists())

    def test_product_delete_is_scoped_and_audited(self):
        self.client.force_login(self.admin)
        result = self.client.post(reverse('admin_product_delete', args=[self.product.pk]),
                                  {'confirmation': 'DELETE', 'reason': 'Duplicate item'})
        self.assertRedirects(result, reverse('pilot_admin_shop', args=[self.company.pk]))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        self.assertFalse(ProductImage.objects.filter(pk=self.photo.pk).exists())
        self.assertTrue(Product.objects.filter(pk=self.extra.pk).exists())
        log = AdminActivity.objects.get(action='delete')
        self.assertEqual(log.actor, self.admin)
        self.assertEqual(log.details['reason'], 'Duplicate item')

    def test_shop_delete_preserves_owner_conversations_and_other_shops(self):
        another = CompanyProfile.objects.create(user=self.member, company_name='Other shop')
        self.client.force_login(self.admin)
        result = self.client.post(reverse('admin_shop_delete', args=[self.company.pk]),
                                  {'confirmation': 'DELETE', 'reason': 'Duplicate shop'})
        self.assertEqual(result.status_code, 302)
        self.assertFalse(CompanyProfile.objects.filter(pk=self.company.pk).exists())
        self.assertFalse(Product.objects.filter(shop_id=self.company.pk).exists())
        self.assertFalse(LocalOffer.objects.filter(pk=self.offer.pk).exists())
        self.assertFalse(BusinessGalleryImage.objects.filter(pk=self.gallery.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.owner.pk, is_active=True).exists())
        self.assertTrue(Conversation.objects.filter(pk=self.thread.pk).exists())
        self.assertTrue(CompanyProfile.objects.filter(pk=another.pk).exists())
        self.assertEqual(AdminActivity.objects.get(action='delete').details['products'], 2)

    def test_owner_member_and_scoped_admin_cannot_delete(self):
        scoped = User.objects.create_user('delete-scoped', admin_role='scoped_admin')
        for user in [self.owner, self.member, scoped]:
            self.client.force_login(user)
            for name, pk in [('admin_product_delete', self.product.pk), ('admin_shop_delete', self.company.pk)]:
                response = self.client.post(reverse(name, args=[pk]), {'confirmation': 'DELETE', 'reason': 'Test'})
                self.assertIn(response.status_code, [302, 403])
        self.assertTrue(CompanyProfile.objects.filter(pk=self.company.pk).exists())
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_csrf_and_audit_failure_prevent_deletion(self):
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.admin)
        url = reverse('admin_shop_delete', args=[self.company.pk])
        self.assertEqual(csrf.post(url, {'confirmation': 'DELETE', 'reason': 'Test'}).status_code, 403)
        self.client.force_login(self.admin)
        with patch('jobs.admin_shop_delete.record_activity', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post(url, {'confirmation': 'DELETE', 'reason': 'Test'})
        self.assertTrue(CompanyProfile.objects.filter(pk=self.company.pk).exists())
