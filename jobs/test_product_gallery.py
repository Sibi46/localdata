from jobportal.test_support import TemporaryMediaMixin
from django.test import TestCase
from django.urls import reverse
from .models import CompanyProfile, Product, ProductImage, ShopProfile, User
from .test_shop_catalog import image_file


class ProductGalleryTests(TemporaryMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('gallery-owner', user_type='shop')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Photo Store', logo=image_file('shop-logo.png'))
        cls.other = User.objects.create_user('gallery-other', user_type='shop')
        CompanyProfile.objects.create(user=cls.other, company_name='Another Store')

    def upload(self, count=6, url=None):
        self.client.force_login(self.owner)
        return self.client.post(url or reverse('product_add'), {'name': 'Everyday bag', 'description': 'A roomy cotton bag for everyday use.', 'price': '1000', 'discount_percent': '20', 'is_active': 'on', 'images': [image_file(f'view-{i}.png') for i in range(count)]})

    def test_six_images_create_detail_and_shop_link(self):
        self.assertEqual(self.upload().status_code, 302)
        product = Product.objects.get()
        self.assertEqual(product.images.count(), 5)
        self.assertEqual(list(product.images.values_list('position', flat=True)), [1,2,3,4,5])
        self.client.force_login(self.other)
        response = self.client.get(product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['gallery']), 6)
        self.assertContains(response, '₹800.00')
        self.assertContains(response, self.shop.logo.url)
        self.assertContains(response, self.shop.get_absolute_url())
        self.assertContains(response, 'Show product image 6')

    def test_seven_images_rejected_without_creating_product(self):
        response = self.upload(7)
        self.assertContains(response, 'maximum of 6 product images')
        self.assertFalse(Product.objects.exists())
        self.assertFalse(ProductImage.objects.exists())

    def test_edit_preserves_or_replaces_gallery(self):
        self.upload()
        product = Product.objects.get()
        url = reverse('product_edit', args=[product.pk])
        self.client.post(url, {'name':'New name', 'price':'1000', 'is_active':'on'})
        product.refresh_from_db()
        self.assertEqual(product.images.count(), 5)
        self.upload(2, url)
        product.refresh_from_db()
        self.assertEqual(product.images.count(), 1)
        self.assertEqual(len(self.client.get(product.get_absolute_url()).context['gallery']), 2)

    def test_other_owner_cannot_change_gallery_and_hidden_product_is_private(self):
        self.upload()
        product = Product.objects.get()
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse('product_edit', args=[product.pk]), {'name':'Invalid', 'images':[image_file()]}).status_code, 404)
        self.assertEqual(product.images.count(), 5)
        product.is_active = False
        product.save()
        self.assertEqual(self.client.get(product.get_absolute_url()).status_code, 404)
        product.is_active = True
        product.save()
        self.owner.is_active = False
        self.owner.save()
        self.assertEqual(self.client.get(product.get_absolute_url()).status_code, 404)

    def test_deleting_product_removes_gallery_rows_and_files(self):
        self.upload()
        product = Product.objects.get()
        paths = [product.image.path] + [item.image.path for item in product.images.all()]
        self.client.post(reverse('product_delete', args=[product.pk]))
        from pathlib import Path
        self.assertFalse(any(Path(path).exists() for path in paths))
        self.assertFalse(ProductImage.objects.exists())

    def test_registration_saves_shop_logo_and_banner(self):
        user = User.objects.create_user('new-branded-shop', user_type='individual')
        self.client.force_login(user)
        response = self.client.post('/business/create/', {'account_type':'shop','name':'Branded Shop','city':'Chennai','pincode':'600001','logo':image_file('logo.png'),'banner_image':image_file('banner.png')})
        self.assertRedirects(response, '/employer/dashboard/')
        company = CompanyProfile.objects.get(user=user)
        profile = ShopProfile.objects.get(user=user)
        self.assertTrue(company.logo)
        self.assertTrue(company.banner_image)
        self.assertEqual(profile.logo.name, company.logo.name)
        self.assertEqual(profile.banner_image.name, company.banner_image.name)
        self.assertContains(self.client.get(company.get_absolute_url()), company.banner_image.url)
