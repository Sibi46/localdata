from jobportal.test_support import verify_account_phone
from jobportal.test_support import TemporaryMediaMixin
from decimal import Decimal
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BusinessGalleryImage, CompanyProfile, LocalOffer, Product, ShopVideo, User
from .shop_forms import ProductForm, ShopPhotosForm, ShopVideoForm


def image_file(name='product.png'):
    buffer = BytesIO()
    Image.new('RGB', (30, 30), '#537c49').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


class ShopCatalogTests(TemporaryMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('shop-owner', password='testpass', user_type='shop', pincode='600001', city='Chennai')
        cls.other = User.objects.create_user('other-owner', password='testpass', user_type='company', pincode='600002')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Corner Store', industry='Groceries')
        cls.other_shop = CompanyProfile.objects.create(user=cls.other, company_name='Corner Store', industry='Groceries')

    def product(self, **extra):
        values = dict(shop=self.shop, name='Local Coffee', image=image_file(), price=Decimal('500.00'), discount_percent=20)
        values.update(extra)
        return Product.objects.create(**values)

    def test_product_create_price_and_public_discovery(self):
        self.client.force_login(self.owner)
        result = self.client.post(reverse('product_add'), {'name': 'Local Coffee', 'price': '499.99', 'discount_percent': '15', 'is_active': 'on', 'image': image_file()})
        self.assertRedirects(result, '/employer/dashboard/#products', fetch_redirect_response=False)
        product = Product.objects.get()
        self.assertEqual(product.shop, self.shop)
        self.assertEqual(product.sale_price, Decimal('424.99'))
        viewer=User.objects.create_user('catalog-viewer',user_type='individual')
        self.client.force_login(viewer)
        for path in ['/', '/products/', '/products/?q=coffee', '/products/?q=Corner+Store', self.shop.get_absolute_url()]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Local Coffee')
                self.assertContains(response, 'Corner Store')

    def test_registration_lands_on_shop_dashboard(self):
        verify_account_phone(self.client, '9876543210')
        response = self.client.post(reverse('register_process'), {'user_type': 'shop', 'first_name': 'New owner', 'phone': '9876543210', 'password': 'testpass', 'pincode': '600001', 'org_name': 'New Neighbourhood Shop'})
        self.assertRedirects(response, reverse('employer_dashboard'))
        company = CompanyProfile.objects.get(company_name='New Neighbourhood Shop')
        self.assertContains(self.client.get(reverse('employer_dashboard')), 'Add your first product')
        self.assertEqual(company.user.user_type, 'shop')

    def test_owner_only_edit_delete_and_post_only_deletion(self):
        product = self.product()
        video = ShopVideo.objects.create(shop=self.shop, title='A look around', video='shop_videos/example.webm')
        offer = LocalOffer.objects.create(owner=self.owner, business_name=self.shop.company_name, title='Sale', discount_text='10% off')
        photo = BusinessGalleryImage.objects.create(user=self.owner, image=image_file())
        self.client.force_login(self.other)
        for name, pk in [('product_edit', product.pk), ('product_delete', product.pk), ('shop_video_edit', video.pk), ('shop_video_delete', video.pk), ('shop_offer_edit', offer.pk), ('shop_offer_delete', offer.pk), ('gallery_delete', photo.pk)]:
            response = self.client.post(reverse(name, args=[pk]), {})
            self.assertEqual(response.status_code, 404, name)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.client.force_login(self.owner)
        for name, pk in [('product_delete', product.pk), ('shop_video_delete', video.pk), ('shop_offer_delete', offer.pk), ('gallery_delete', photo.pk)]:
            self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 405)
        response = self.client.post(reverse('product_edit', args=[product.pk]), {'name': 'Updated coffee', 'price': '600.00', 'discount_percent': '25', 'is_active': 'on'})
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.sale_price, Decimal('450.00'))
        self.assertEqual(product.shop_id, self.shop.pk)
        self.assertEqual(self.client.post(reverse('product_delete', args=[product.pk])).status_code, 302)
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_invalid_prices_discounts_and_images_are_rejected(self):
        for price, discount in [('0', '0'), ('-1', '10'), ('50', '101'), ('50', '-1')]:
            form = ProductForm({'name': 'Test', 'price': price, 'discount_percent': discount}, {'image': image_file()})
            self.assertFalse(form.is_valid(), (price, discount))
        form = ProductForm({'name': 'Fake image', 'price': '10'}, {'image': SimpleUploadedFile('bad.png', b'not an image', content_type='image/png')})
        self.assertFalse(form.is_valid())
        self.assertFalse(ShopPhotosForm({}, {}).is_valid())
        self.assertFalse(ShopVideoForm({'title': 'Fake video'}, {'video': SimpleUploadedFile('bad.mp4', b'not a video', content_type='video/mp4')}).is_valid())

    def test_drafts_inactive_shops_and_area_filters(self):
        self.client.force_login(self.owner)
        published = self.product()
        self.product(name='Hidden coffee', is_active=False)
        self.product(name='Other area product', shop=self.other_shop)
        response = self.client.get('/products/?pincode=600001')
        self.assertContains(response, published.name)
        self.assertNotContains(response, 'Hidden coffee')
        self.assertNotContains(response, 'Other area product')
        self.assertContains(self.client.get('/products/?pincode='), 'Other area product')
        self.owner.is_active = False
        self.owner.save(update_fields=['is_active'])
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get('/products/?pincode='), published.name)
        self.assertEqual(self.client.get(self.shop.get_absolute_url()).status_code, 404)

    def test_store_owns_its_offers_and_media_even_when_names_match(self):
        self.client.force_login(self.owner)
        self.product()
        LocalOffer.objects.create(owner=self.owner, business_name='Old shop name', title='My own offer', discount_text='20% off')
        LocalOffer.objects.create(owner=self.other, business_name=self.shop.company_name, title='Another shop offer', discount_text='30% off')
        LocalOffer.objects.create(owner=self.owner, title='Pending offer', discount_text='5% off', is_active=False)
        LocalOffer.objects.create(owner=self.owner, title='Expired offer', discount_text='5% off', valid_until=timezone.localdate() - timezone.timedelta(days=1))
        BusinessGalleryImage.objects.create(user=self.owner, image=image_file(), caption='Inside my shop')
        ShopVideo.objects.create(shop=self.shop, title='Shop tour', video='shop_videos/tour.webm')
        ShopVideo.objects.create(shop=self.shop, title='Hidden tour', video='shop_videos/hidden.webm', is_published=False)
        response = self.client.get(self.shop.get_absolute_url())
        for text in ['My own offer', 'Inside my shop', 'Shop tour', 'All products', 'Shop details']:
            self.assertContains(response, text)
        for text in ['Another shop offer', 'Pending offer', 'Expired offer', 'Hidden tour']:
            self.assertNotContains(response, text)

    def test_upload_photos_videos_and_offer_moderation(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('gallery_upload'), {'gallery_images': [image_file('one.png'), image_file('two.png')], 'caption': 'Shop entrance'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BusinessGalleryImage.objects.filter(user=self.owner).count(), 2)
        video = SimpleUploadedFile('tour.webm', b'\x1aE\xdf\xa3' + b'valid-container-header', content_type='video/webm')
        self.assertEqual(self.client.post(reverse('shop_video_add'), {'title': 'My shop tour', 'video': video, 'is_published': 'on'}).status_code, 302)
        self.assertEqual(ShopVideo.objects.get().shop, self.shop)
        response = self.client.post(reverse('shop_offer_add'), {'title': 'Weekend special', 'discount_text': '20% off', 'category': 'shop', 'contact_phone': '9876543210'})
        self.assertEqual(response.status_code, 302)
        offer = LocalOffer.objects.get()
        self.assertEqual(offer.owner, self.owner)
        self.assertEqual(offer.business_name, self.shop.company_name)
        self.assertFalse(offer.is_active)

    def test_discounted_price_sort_and_selected_product_pagination(self):
        self.client.force_login(self.owner)
        older = self.product(name='Oldest coffee', price=Decimal('1000.00'), discount_percent=90)
        later = self.product(name='Regular coffee', price=Decimal('200.00'), discount_percent=0)
        response = self.client.get('/products/?sort=price_low')
        self.assertEqual(list(response.context['products']), [older, later])
        Product.objects.bulk_create([Product(shop=self.shop, name=f'Newer {number}', image='products/example.png', price=Decimal('20.00')) for number in range(30)])
        response = self.client.get(self.shop.get_absolute_url() + f'?product={older.pk}')
        self.assertContains(response, 'Oldest coffee')
        self.assertEqual(response.context['products'].number, 2)

    def test_anonymous_management_requires_login(self):
        for name in ['product_add', 'shop_video_add', 'shop_offer_add']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith('/register/'))
