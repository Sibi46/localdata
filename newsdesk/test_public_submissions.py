from jobportal.test_support import view_middleware
import io
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from jobs.models import District, PinCode, State, User, UserNotification
from .models import NewsAgent, NewsContributor, NewsItem, NewsSubmission


def image(name='photo.png'):
    data = io.BytesIO()
    Image.new('RGB', (20, 20), '#126452').save(data, 'PNG')
    return SimpleUploadedFile(name, data.getvalue(), content_type='image/png')


# View-level contract tests; full middleware access is covered separately.
@override_settings(MIDDLEWARE=view_middleware())
class PublicNewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('news-public-admin', admin_role='super_admin')
        cls.editor = User.objects.create_user('news-public-editor')
        cls.other_editor = User.objects.create_user('news-public-other-editor')
        cls.person = User.objects.create_user('news-public-reader', phone='9876543210')
        state = State.objects.create(name='Submission state', code='NS')
        district = District.objects.create(name='Submission district', state=state)
        cls.pin = PinCode.objects.create(code='600001', district=district)
        cls.other_pin = PinCode.objects.create(code='600002', district=district)
        NewsAgent.objects.create(user=cls.editor, pincode=cls.pin)
        NewsAgent.objects.create(user=cls.other_editor, pincode=cls.other_pin)

    def setUp(self):
        cache.clear()
        self.files = tempfile.TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        override = override_settings(NEWS_IDENTITY_ROOT=self.files.name)
        override.enable()
        self.addCleanup(override.disable)

    def url(self, name, *args):
        return reverse('newsdesk:' + name, args=args)

    def proof(self, client=None, phone='9876543210', age=0):
        client = client or self.client
        session = client.session
        session['news_phone_proof'] = {'phone': phone, 'at': time.time() - age}
        session.save()

    def fields(self, client=None, **changes):
        client = client or self.client
        page = client.get(self.url('share'))
        values = {'token': str(page.context['form'].initial['token']), 'name': 'Local Reader',
            'pincode': self.pin.code, 'address': 'Private test address', 'aadhaar': image('aadhaar.png'),
            'profile_photo': image(), 'topic': 'Reader street cleanup',
            'body': 'Residents organised a local street cleanup today.', 'terms': 'on', 'accuracy': 'on'}
        values.update(changes)
        return values

    def submission(self):
        self.proof()
        response = self.client.post(self.url('share'), self.fields())
        self.assertEqual(response.status_code, 302)
        return NewsSubmission.objects.get()

    def decision(self, **changes):
        values = {'topic': 'Edited cleanup news', 'body': 'Local volunteers cleaned the street today.',
            'category': 'community', 'decision': 'publish', 'identity_checked': 'on', 'note': 'Checked by editor.'}
        values.update(changes)
        return values

    @patch('newsdesk.public_views.make_otp', return_value='654321')
    @patch('newsdesk.public_views.deliver_otp', return_value=True)
    def test_public_otp_is_purpose_bound_hashed_and_one_use(self, send, make):
        response = self.client.post(self.url('share_send_otp'), json.dumps({'phone': '9876543210'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('654321', response.content.decode())
        self.assertNotEqual(self.client.session['news_otp']['hash'], '654321')
        self.assertNotIn('news_phone_proof', self.client.session)
        wrong = self.client.post(self.url('share_verify_otp'), json.dumps({'otp': '123456'}), content_type='application/json')
        self.assertEqual(wrong.status_code, 400)
        good = self.client.post(self.url('share_verify_otp'), json.dumps({'otp': '654321'}), content_type='application/json')
        self.assertEqual(good.status_code, 200)
        self.assertEqual(self.client.session['news_phone_proof']['phone'], '9876543210')
        self.assertNotIn('otp_verified', self.client.session)
        self.assertEqual(self.client.post(self.url('share_verify_otp'), '{"otp":"654321"}', content_type='application/json').status_code, 400)

    @patch('newsdesk.public_views.deliver_otp', return_value=False)
    def test_sms_failure_cannot_verify_or_submit(self, send):
        response = self.client.post(self.url('share_send_otp'), '{"phone":"9876543210"}', content_type='application/json')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('news_otp', self.client.session)
        self.client.post(self.url('share'), {'topic': 'Attempted bypass'})
        self.assertFalse(NewsSubmission.objects.exists())

    @patch('newsdesk.public_views.deliver_otp', return_value=True)
    def test_send_and_verify_limits_and_expiry(self, send):
        for _ in range(3):
            self.assertEqual(self.client.post(self.url('share_send_otp'), '{"phone":"9876543210"}', content_type='application/json').status_code, 200)
        self.assertEqual(self.client.post(self.url('share_send_otp'), '{"phone":"9876543210"}', content_type='application/json').status_code, 429)
        cache.clear()
        with patch('newsdesk.public_views.make_otp', return_value='654321'):
            self.client.post(self.url('share_send_otp'), '{"phone":"9876543210"}', content_type='application/json')
        for _ in range(5):
            self.assertEqual(self.client.post(self.url('share_verify_otp'), '{"otp":"111111"}', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post(self.url('share_verify_otp'), '{"otp":"654321"}', content_type='application/json').status_code, 429)
        cache.clear()
        self.client.post(self.url('share_send_otp'), '{"phone":"9876543210"}', content_type='application/json')
        session = self.client.session
        challenge = session['news_otp']
        challenge['at'] -= 601
        session['news_otp'] = challenge
        session.save()
        self.assertEqual(self.client.post(self.url('share_verify_otp'), '{"otp":"654321"}', content_type='application/json').status_code, 400)

    def test_malformed_payload_and_csrf_protection(self):
        for route in ('share_send_otp', 'share_verify_otp'):
            for body in ('{', '[]', 'null', '{"phone":null,"otp":null}'):
                self.assertEqual(self.client.post(self.url(route), body, content_type='application/json').status_code, 400)
        csrf = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf.post(self.url('share_send_otp'), '{"phone":"9876543210"}', content_type='application/json').status_code, 403)

    def test_unverified_and_expired_sessions_cannot_send(self):
        self.assertContains(self.client.get(self.url('share')), 'Verify your mobile number')
        self.proof(age=1801)
        self.client.post(self.url('share'), {'topic': 'Unverified'})
        self.assertFalse(NewsSubmission.objects.exists())

    def test_anonymous_submission_stays_private_and_notifies_only_editors(self):
        item = self.submission()
        self.assertEqual(item.status, 'pending')
        self.assertIsNone(item.published_story_id)
        self.assertFalse(NewsItem.objects.exists())
        self.assertTrue(item.terms_accepted_at)
        self.assertEqual(item.terms_version, 'news-sharing-v1')
        self.assertTrue(UserNotification.objects.filter(user=self.admin, link=self.url('review_submission', item.pk)).exists())
        self.assertTrue(UserNotification.objects.filter(user=self.editor).exists())
        self.assertFalse(UserNotification.objects.filter(user=self.other_editor).exists())
        self.assertNotContains(self.client.get(self.url('feed') + '?pincode=600001'), item.topic)

    def test_required_terms_identity_pin_and_word_limit(self):
        self.proof()
        for changes in ({'terms': ''}, {'accuracy': ''}, {'aadhaar': ''}, {'profile_photo': ''},
                        {'pincode': '999999'}, {'body': '\u200b '}, {'body': 'word ' * 201}):
            response = self.client.post(self.url('share'), self.fields(**changes))
            self.assertEqual(response.status_code, 400)
            self.assertFalse(NewsSubmission.objects.exists())
        self.assertEqual(self.client.post(self.url('share'), self.fields(body='தமிழ் ' * 200)).status_code, 302)

    def test_invalid_upload_and_oversized_document_are_rejected(self):
        self.proof()
        for file in (SimpleUploadedFile('identity.html', b'<script>alert(1)</script>'),
                     SimpleUploadedFile('identity.pdf', b'not a pdf'),
                     SimpleUploadedFile('identity.png', b'x' * (5 * 1024 * 1024 + 1))):
            self.assertEqual(self.client.post(self.url('share'), self.fields(aadhaar=file)).status_code, 400)
        self.assertFalse(NewsContributor.objects.exists())

    def test_existing_contributor_id_is_stable_and_duplicate_post_is_idempotent(self):
        item = self.submission()
        reference = item.contributor.reference
        data = self.fields()
        data.pop('aadhaar')
        data.pop('profile_photo')
        for _ in range(2):
            self.assertEqual(self.client.post(self.url('share'), data).status_code, 302)
        self.assertEqual(NewsContributor.objects.count(), 1)
        self.assertEqual(NewsSubmission.objects.count(), 2)
        self.assertEqual(NewsContributor.objects.get().reference, reference)

    def test_private_files_require_owner_proof_or_scoped_editor(self):
        item = self.submission()
        url = self.url('identity_file', item.contributor_id, 'aadhaar')
        own_response = self.client.get(url)
        self.assertEqual(own_response.status_code, 200)
        self.assertIn('attachment', own_response['Content-Disposition'])
        own_response.close()
        with self.assertRaises(ValueError):
            _ = item.contributor.aadhaar.url
        stranger = Client()
        self.assertEqual(stranger.get(url).status_code, 403)
        stranger.force_login(self.other_editor)
        self.assertEqual(stranger.get(url).status_code, 403)
        stranger.force_login(self.editor)
        response = stranger.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        response.close()

    def test_finish_clears_only_news_verification(self):
        self.proof()
        self.client.force_login(self.person)
        self.client.post(self.url('share_finish'))
        self.assertNotIn('news_phone_proof', self.client.session)
        self.assertIn('_auth_user_id', self.client.session)

    def test_only_owner_can_view_receipt(self):
        item = self.submission()
        self.assertEqual(self.client.get(self.url('submission_status', item.pk)).status_code, 200)
        other = Client()
        self.proof(other, '9123456789')
        self.assertEqual(other.get(self.url('submission_status', item.pk)).status_code, 404)

    def test_editor_scope_and_identity_check_before_publish(self):
        item = self.submission()
        other = Client()
        other.force_login(self.other_editor)
        self.assertEqual(other.get(self.url('review_submission', item.pk)).status_code, 404)
        self.assertEqual(other.post(self.url('review_submission', item.pk), self.decision()).status_code, 404)
        other.force_login(self.person)
        self.assertEqual(other.get(self.url('submissions')).status_code, 403)
        other.force_login(self.editor)
        self.assertEqual(other.post(self.url('review_submission', item.pk), self.decision(identity_checked='')).status_code, 400)
        self.assertFalse(NewsItem.objects.exists())

    def test_publication_creates_one_story_without_identity_leak(self):
        item = self.submission()
        editor = Client()
        editor.force_login(self.editor)
        url = self.url('review_submission', item.pk)
        for _ in range(2):
            self.assertEqual(editor.post(url, self.decision()).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(NewsItem.objects.count(), 1)
        self.assertEqual(item.status, 'published')
        self.assertTrue(item.contributor.document_checked_at)
        public = Client().get(self.url('detail', item.published_story_id))
        self.assertEqual(public.status_code, 200)
        self.assertContains(public, 'Edited cleanup news')
        for private in ('Private test address', '9876543210', item.contributor.aadhaar.name, item.contributor.profile_photo.name):
            self.assertNotContains(public, private)
        self.assertContains(self.client.get(self.url('submission_status', item.pk)), 'Read your published news')

    def test_super_admin_can_reject_with_note_and_nothing_is_published(self):
        item = self.submission()
        editor = Client()
        editor.force_login(self.admin)
        self.assertContains(editor.get(self.url('submissions')), item.reference)
        self.assertEqual(editor.post(self.url('review_submission', item.pk), self.decision(decision='reject', note='')).status_code, 400)
        editor.post(self.url('review_submission', item.pk), self.decision(decision='reject', note='Please provide a source.'))
        item.refresh_from_db()
        self.assertEqual(item.status, 'rejected')
        self.assertFalse(NewsItem.objects.exists())
        self.assertContains(self.client.get(self.url('submission_status', item.pk)), 'Please provide a source.')

    def test_files_roll_back_when_submission_notification_fails(self):
        from .public_services import submit_news
        from .public_forms import ShareNewsForm
        from django.contrib.auth.models import AnonymousUser
        from django.utils import timezone
        self.proof()
        data = self.fields()
        form = ShareNewsForm(data, {'aadhaar': data['aadhaar'], 'profile_photo': data['profile_photo']})
        self.assertTrue(form.is_valid())
        with patch('newsdesk.public_services.notify_editors', side_effect=RuntimeError('notification failure')):
            with self.assertRaises(RuntimeError):
                submit_news('9876543210', timezone.now(), form.cleaned_data, AnonymousUser())
        self.assertFalse(NewsSubmission.objects.exists())
        self.assertFalse(NewsContributor.objects.exists())
        self.assertEqual([p for p in Path(self.files.name).rglob('*') if p.is_file()], [])

    def test_private_storage_failure_has_feedback_and_saves_nothing(self):
        self.proof()
        with patch('newsdesk.identity_uploads.IdentityStorage._save', side_effect=OSError('storage unavailable')):
            response = self.client.post(self.url('share'), self.fields())
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Private documents could not be saved.', status_code=400)
        self.assertFalse(NewsSubmission.objects.exists())
