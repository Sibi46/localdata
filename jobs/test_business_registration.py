from jobportal.test_support import verify_account_phone
from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import User, CompanyProfile, ShopProfile


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BusinessRegistrationTests(TestCase):
    def post(self, **data):
        fields = {'user_type': 'shop', 'phone': '9000000001', 'password': 'new-password',
                  'org_name': 'Test shop', 'pincode': '600073'}
        fields.update(data)
        return self.client.post('/register/process/', fields,
                                HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_anonymous_registration_cannot_take_over_existing_account(self):
        owner = User.objects.create_user('existing', password='original-password',
                phone='9000000001', email='owner@example.com', business_phone='9000000002')
        for fields in ({}, {'phone': '9000000002'},
                       {'phone': '9000000003', 'email': 'OWNER@example.com'}):
            response = self.post(**fields)
            self.assertFalse(response.json()['success'])
            owner.refresh_from_db()
            self.assertTrue(owner.check_password('original-password'))
            self.assertNotEqual(owner.user_type, 'shop')
            self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(CompanyProfile.objects.exists())

    def test_authenticated_owner_can_register_business(self):
        owner = User.objects.create_user('owner', phone='9000000001')
        self.client.force_login(owner, backend='django.contrib.auth.backends.ModelBackend')
        self.assertTrue(self.post().json()['success'])
        owner.refresh_from_db()
        self.assertEqual(owner.user_type, 'shop')
        self.assertTrue(owner.salesman_biz_id.startswith('BIZ'))
        self.assertEqual(User.objects.count(), 1)

    def test_registration_uploads_logo_and_banner(self):
        def image(name):
            stream = BytesIO()
            Image.new('RGB', (12, 12), 'blue').save(stream, format='PNG')
            return SimpleUploadedFile(name, stream.getvalue(), content_type='image/png')
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            verify_account_phone(self.client, '9000000001')
            self.assertTrue(self.post(logo=image('logo.png'), banner_image=image('banner.png')).json()['success'])
            business = User.objects.get(phone='9000000001')
            self.assertTrue(business.salesman_biz_id)
            for profile in (CompanyProfile.objects.get(user=business), ShopProfile.objects.get(user=business)):
                self.assertTrue(profile.logo)
                self.assertTrue(profile.banner_image)
            response = self.client.get('/employer/dashboard/')
            self.assertContains(response, business.company.logo.url)
            self.assertContains(response, business.company.banner_image.url)

    def test_edit_images_preserves_profile_and_unselected_image(self):
        def image(name):
            stream = BytesIO()
            Image.new('RGB', (12, 12), 'green').save(stream, format='PNG')
            return SimpleUploadedFile(name, stream.getvalue(), content_type='image/png')

        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            owner = User.objects.create_user('image-owner', user_type='company',
                city='Chennai', address='Main Road', pincode='600073',
                email='owner@example.com', whatsapp='9000000001')
            profile = CompanyProfile.objects.create(user=owner, company_name='Business',
                industry='Retail', company_size='10', website='https://example.com',
                logo=image('old-logo.png'), banner_image=image('old-banner.png'))
            self.client.force_login(owner, backend='django.contrib.auth.backends.ModelBackend')
            old_banner = profile.banner_image.name
            fields = {'company_name': 'Business', 'industry': 'Retail', 'company_size': '10',
                      'website': 'https://example.com', 'city': 'Chennai', 'address': 'Main Road',
                      'pincode': '600073', 'email': 'owner@example.com', 'whatsapp': '9000000001'}
            response = self.client.post('/employer/dashboard/', {**fields, 'logo': image('new-logo.png')})
            self.assertEqual(response.status_code, 302)
            profile.refresh_from_db()
            self.assertIn('new-logo', profile.logo.name)
            self.assertEqual(profile.banner_image.name, old_banner)
            new_logo = profile.logo.name
            self.client.post('/employer/dashboard/', {**fields, 'banner_image': image('new-banner.png')})
            profile.refresh_from_db()
            owner.refresh_from_db()
            self.assertIn('new-banner', profile.banner_image.name)
            self.assertEqual(profile.logo.name, new_logo)
            self.assertEqual((owner.city, owner.address, owner.pincode, owner.email, owner.whatsapp),
                ('Chennai', 'Main Road', '600073', 'owner@example.com', '9000000001'))
            self.assertEqual((profile.industry, profile.company_size, profile.website),
                ('Retail', '10', 'https://example.com'))
            response = self.client.get('/employer/dashboard/')
            self.assertContains(response, 'Your profile &amp; shop details')
            self.assertContains(response, profile.logo.url)
            self.assertContains(response, profile.banner_image.url)
