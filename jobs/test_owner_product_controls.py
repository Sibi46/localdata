from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import CompanyProfile, Product, User
from .test_shop_catalog import image_file


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class OwnerProductControlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('owner-controls', user_type='shop')
        cls.other = User.objects.create_user('other-controls')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Owner shop')
        cls.product = Product.objects.create(shop=cls.shop, name='Sample product', price=100, image='products/sample.jpg')

    def test_detail_controls_only_belong_to_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, reverse('product_edit', args=[self.product.pk]))
        self.assertContains(response, reverse('product_delete', args=[self.product.pk]))
        self.client.force_login(self.other)
        response = self.client.get(self.product.get_absolute_url())
        self.assertNotContains(response, reverse('product_edit', args=[self.product.pk]))
        self.assertNotContains(response, reverse('product_delete', args=[self.product.pk]))
        self.assertEqual(self.client.post(reverse('product_delete', args=[self.product.pk])).status_code, 404)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_owner_delete_still_requires_csrf_and_post(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        url = reverse('product_delete', args=[self.product.pk])
        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        client.get(self.product.get_absolute_url())
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(url, {'csrfmiddlewaretoken': token}).status_code, 302)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_success_is_only_shown_after_valid_product_is_created(self):
        self.client.force_login(self.owner)
        invalid = self.client.post(reverse('product_add'), {'name': 'Invalid', 'price': '0'})
        self.assertEqual(invalid.status_code, 200)
        self.assertFalse(list(get_messages(invalid.wsgi_request)))
        response = self.client.post(reverse('product_add'), {
            'name': 'New product', 'price': '120', 'is_active': 'on', 'image': image_file(),
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('Your product has been added to LOCALFROM.', [str(message) for message in get_messages(response.wsgi_request)])
        self.assertTrue(Product.objects.filter(shop=self.shop, name='New product').exists())
