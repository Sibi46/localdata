from unittest import skip
import io
import tempfile
from pathlib import Path
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .features import search_features
from .models import User, CompanyProfile, AdPost, Advertiser


@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class PdfReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.person = User.objects.create_user('report-person', user_type='individual', pincode='600001')
        cls.owner = User.objects.create_user('report-owner', user_type='shop', pincode='600001')
        cls.company = CompanyProfile.objects.create(user=cls.owner, company_name='Sample store')
        cls.post = AdPost.objects.create(user=cls.owner, company_name='Sample store', description='Local sale', image='ad_posts/sample.png', status='approved')

    def test_favicon_is_public_image(self):
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/x-icon')
        self.assertTrue(b''.join(response.streaming_content))

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_feature_search_has_server_fallback_and_no_matches(self):
        response = self.client.get('/?feature=QUIZ')
        self.assertContains(response, 'Find a feature')
        self.assertEqual(response.context['feature_matches'][0]['url'], '/quiz/play/')
        self.assertContains(self.client.get('/?feature=xyzmissing'), 'No features found.')
        self.assertEqual(search_features('career')[0]['name'], 'Jobs')

    def test_photo_upload_is_saved_and_available_to_account_templates(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            for user in (self.person, self.owner):
                self.client.force_login(user)
                data = io.BytesIO(); Image.new('RGB', (20, 20), 'blue').save(data, format='PNG')
                fields = {'first_name': 'Photo', 'photo': SimpleUploadedFile('photo.png', data.getvalue(), content_type='image/png')}
                if user == self.owner:
                    fields['company_name'] = self.company.company_name
                response = self.client.post('/profile/edit/', fields)
                self.assertEqual(response.status_code, 302)
                user.refresh_from_db()
                self.assertTrue(Path(user.seeker.photo.path).exists())
                for route in ('/profile/edit/',):
                    response = self.client.get(route, follow=True)
                    self.assertEqual(response.context['profile_photo_url'], user.seeker.photo.url)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_quiz_home_link_has_no_question_mark(self):
        response = self.client.get('/quiz/play/')
        self.assertNotContains(response, '? Home')
        self.assertContains(response, 'fa-arrow-left')

    def test_business_directory_links_and_profile_breadcrumb(self):
        self.client.force_login(self.person)
        response = self.client.get('/businesses/')
        self.assertContains(response, '/business/' + self.company.company_id + '/')
        self.assertNotContains(response, 'data-name="sample store" target="_blank"')
        response = self.client.get(reverse('business_profile', args=[self.company.company_id]))
        self.assertContains(response, '<a href="/businesses/">Shops</a>', html=True)

    def test_advertise_entry_requires_registration_and_members_can_apply(self):
        response = self.client.get('/advertise/register/')
        self.assertRedirects(response, '/register/?next=%2Fadvertise%2Fregister%2F', fetch_redirect_response=False)
        self.client.force_login(self.person)
        self.assertRedirects(self.client.get('/register/?type=company'), '/business/create/', fetch_redirect_response=False)
        self.assertContains(self.client.get('/advertise/register/'), 'Apply')

    def test_shared_navigation_and_no_global_plus(self):
        self.client.force_login(self.person)
        for path in ('/', '/messages/', '/profile/edit/', '/products/', '/advertise/'):
            response = self.client.get(path)
            html = response.content.decode()
            self.assertEqual(html.count('aria-label="Mobile navigation"') + html.count('aria-label="Primary navigation"'), 1, path)
            self.assertNotContains(response, 'class="bn-plus-btn"')
            self.assertContains(response, '/businesses/')

    def test_sponsored_ad_without_website_goes_to_details_with_store_link(self):
        self.client.force_login(self.person)
        response = self.client.get(reverse('adpost_click_track', args=[self.post.pk]))
        self.assertRedirects(response, reverse('sponsored_post_detail', args=[self.post.pk]))
        self.post.refresh_from_db(); self.assertEqual(self.post.clicks, 1)
        detail = self.client.get(response.url)
        self.assertContains(detail, 'Local sale')
        self.assertContains(detail, '/business/' + self.company.company_id + '/')

    def test_sponsored_ad_homepage_destination_uses_details(self):
        self.client.force_login(self.person)
        self.post.website = 'https://testserver/'
        self.post.save()
        self.assertRedirects(self.client.get(reverse('adpost_click_track', args=[self.post.pk])), reverse('sponsored_post_detail', args=[self.post.pk]))

    def test_sponsored_ad_valid_website_is_preserved(self):
        self.client.force_login(self.person)
        self.post.website = 'https://store.example.com/sale'
        self.post.save()
        response = self.client.get(reverse('adpost_click_track', args=[self.post.pk]))
        self.assertEqual(response.url, self.post.website)

    def test_sponsored_banner_details_work_without_website(self):
        self.client.force_login(self.person)
        advertiser = Advertiser.objects.create(user=self.owner, business_name='Sample store', status='approved', banner_image='banners/sample.png')
        response = self.client.get(reverse('sponsored_banner_detail', args=[advertiser.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Visit business profile')
