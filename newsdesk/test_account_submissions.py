from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from jobportal.test_support import TemporaryMediaMixin
from jobs.models import Country, District, PinCode, State, User, UserNotification
from jobs.test_shop_catalog import image_file
from .models import NewsAgent, NewsContributor, NewsItem


class AccountNewsTests(TemporaryMediaMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        country, _ = Country.objects.get_or_create(code='IN', defaults={'name': 'India'})
        state, _ = State.objects.get_or_create(name='Account Test Tamil Nadu', code='TN', country=country)
        district, _ = District.objects.get_or_create(name='Vandavasi Account Test District', state=state)
        cls.pin, _ = PinCode.objects.get_or_create(code='604408', defaults={'area_name': 'Vandavasi', 'district': district})
        cls.reader = User.objects.create_user('news-account-reader', first_name='Reader', phone='9876500013', pincode='604408')
        cls.other = User.objects.create_user('news-account-other')
        cls.editor = User.objects.create_user('news-account-editor')
        NewsAgent.objects.create(user=cls.editor, pincode=cls.pin)

    def setUp(self):
        super().setUp()
        self.client.force_login(self.reader)

    def submit(self, **extra):
        response = self.client.get(reverse('newsdesk:share'))
        data = {'token': response.context['form']['token'].value(), 'body': 'A water supply update for our local area.', 'accuracy': 'on'}
        data.update(extra)
        return self.client.post(reverse('newsdesk:share'), data), data

    def test_signed_in_reader_posts_content_without_phone_or_identity_intake(self):
        page = self.client.get(reverse('newsdesk:share'))
        self.assertEqual(set(page.context['form'].fields), {'token', 'body', 'photo', 'accuracy'})
        self.assertNotContains(page, 'name="phone"')
        result, data = self.submit(photo=image_file(), status='published', author=self.other.pk, phone='9999999999', pincode='999999')
        self.assertEqual(result.status_code, 302)
        item = NewsItem.objects.get()
        self.assertEqual((item.author_id, item.status, item.pincode_id), (self.reader.pk, 'draft', self.pin.pk))
        self.assertFalse(NewsContributor.objects.exists())
        self.assertTrue(UserNotification.objects.filter(user=self.editor, title='Reader news awaiting review').exists())
        self.assertEqual(self.client.get(reverse('newsdesk:detail', args=[item.pk])).status_code, 404)
        repeated = self.client.post(reverse('newsdesk:share'), data)
        self.assertEqual(repeated.status_code, 302)
        self.assertEqual(NewsItem.objects.count(), 1)

    def test_receipt_and_draft_media_are_private_and_reader_cannot_publish(self):
        self.submit(photo=image_file())
        item = NewsItem.objects.get()
        receipt = reverse('newsdesk:account_submission', args=[item.pk])
        self.assertEqual(self.client.get(receipt).status_code, 200)
        self.assertEqual(self.client.get(reverse('newsdesk:media', args=[item.pk, 'photo'])).status_code, 403)
        self.assertEqual(self.client.post(reverse('newsdesk:edit', args=[item.pk]), {'status': 'published'}).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(receipt).status_code, 404)
        item.refresh_from_db(); self.assertEqual(item.status, 'draft')

    def test_bad_content_tokens_and_csrf_are_rejected(self):
        self.assertEqual(self.submit(body='')[0].status_code, 400)
        self.assertEqual(self.submit(token='00000000-0000-0000-0000-000000000000')[0].status_code, 400)
        secure = Client(enforce_csrf_checks=True); secure.force_login(self.reader)
        self.assertEqual(secure.post(reverse('newsdesk:share'), {'body': 'Test'}).status_code, 403)
        self.assertFalse(NewsItem.objects.exists())

    def test_only_editor_can_publish_existing_draft(self):
        self.submit()
        item = NewsItem.objects.get()
        self.client.force_login(self.editor)
        response = self.client.post(reverse('newsdesk:edit', args=[item.pk]), {
            'title': 'Reviewed local update', 'body': item.body, 'category': 'news', 'kind': 'news', 'status': 'published',
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db(); self.assertEqual(item.status, 'published')
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(reverse('newsdesk:detail', args=[item.pk])).status_code, 200)

    def test_hourly_account_limit_is_enforced(self):
        for _ in range(10):
            self.assertEqual(self.submit()[0].status_code, 302)
        self.assertContains(self.submit()[0], 'hourly submission limit', status_code=400)
        self.assertEqual(NewsItem.objects.filter(author=self.reader).count(), 10)

    def test_account_phone_does_not_grant_access_to_legacy_identity_documents(self):
        contributor = NewsContributor.objects.create(user=self.other, phone=self.reader.phone, name='Private contributor',
            pincode=self.pin, address='Private address', aadhaar='original.pdf', profile_photo='original.jpg', phone_verified_at=timezone.now())
        self.assertEqual(self.submit()[0].status_code, 302)
        contributor.refresh_from_db()
        self.assertEqual(contributor.user_id, self.other.pk)
        self.assertEqual(self.client.get(reverse('newsdesk:identity_file', args=[contributor.pk, 'aadhaar'])).status_code, 403)
