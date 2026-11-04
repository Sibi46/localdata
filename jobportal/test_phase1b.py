"""Integration access policies and test isolation regression coverage."""
from pathlib import Path
from io import StringIO
import unittest
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from jobs.models import User
from .test_support import IsolatedMediaRunner, TemporaryMediaMixin, view_middleware


class AuthenticationBoundaryTests(TestCase):
    def test_guest_browser_and_api_requests_keep_registration_gate(self):
        for path in ('/news/', '/news/share/', '/news/share/otp/send/',
                     '/news/api/stories/', '/messages/', '/business/create/'):
            for method in ('get', 'post'):
                with self.subTest(path=path, method=method):
                    response = getattr(self.client, method)(path)
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith('/register/?next='))

    def test_authenticated_unverified_reader_reaches_otp_and_validation(self):
        reader = User.objects.create_user('phase1b-reader')
        self.client.force_login(reader)
        self.assertContains(self.client.get('/news/share/'), 'Verify your mobile number')
        with patch('newsdesk.public_views.deliver_otp', return_value=False):
            response = self.client.post('/news/share/otp/send/',
                '{"phone":"9876543210"}', content_type='application/json')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('news_phone_proof', self.client.session)
        self.assertEqual(self.client.get('/news/desk/').status_code, 403)

    def test_view_layer_separates_api_unauthorized_and_browser_redirect(self):
        # The outer registration policy is tested above, without this override.
        with override_settings(MIDDLEWARE=view_middleware()):
            client = Client()
            api = client.post(reverse('newsdesk:api_comment', args=[999]),
                              '{"text":"hello"}', content_type='application/json')
            self.assertEqual(api.status_code, 401)
            self.assertEqual(client.post(reverse('newsdesk:comment', args=[999]),
                                         {'text': 'hello'}).status_code, 302)


class MediaIsolationTests(TestCase):
    def test_runner_clears_lookup_and_rate_limit_cache_between_tests(self):
        cache.set('phase1b-stale-fixture', 'rolled-back district')
        cache.set('phase1b-rate-limit', 5)
        result = IsolatedMediaRunner().get_resultclass()(StringIO(), False, 0)
        test = unittest.FunctionTestCase(lambda: None)
        result.startTest(test)
        try:
            self.assertIsNone(cache.get('phase1b-stale-fixture'))
            self.assertIsNone(cache.get('phase1b-rate-limit'))
        finally:
            result.stopTest(test)

    def test_fixture_storage_is_overridden_and_cleanup_failure_cannot_skip_rollback(self):
        original = settings.MEDIA_ROOT

        class UploadCase(TemporaryMediaMixin, TestCase):
            @classmethod
            def setUpTestData(cls):
                cls.storage = settings.MEDIA_ROOT
                Path(cls.storage, 'fixture.txt').write_text('test fixture')
                User.objects.create_user('phase1b-rollback-probe')

        UploadCase.setUpClass()
        directory = Path(UploadCase.storage)
        self.assertNotEqual(str(original), str(directory))
        self.assertTrue((directory / 'fixture.txt').exists())
        # Simulate a failing class cleanup; unittest must still run the others.
        def failed_cleanup():
            raise PermissionError('simulated temporary file cleanup failure')
        UploadCase.addClassCleanup(failed_cleanup)
        try:
            UploadCase.tearDownClass()
        finally:
            UploadCase.doClassCleanups()
        self.assertFalse(User.objects.filter(username='phase1b-rollback-probe').exists())
        self.assertEqual(settings.MEDIA_ROOT, original)
        self.assertFalse(directory.exists())
        self.assertEqual(len(UploadCase.tearDown_exceptions), 1)

    def test_fixture_failure_restores_media_override(self):
        original = settings.MEDIA_ROOT

        class BrokenFixture(TemporaryMediaMixin, TestCase):
            @classmethod
            def setUpTestData(cls):
                cls.directory = Path(settings.MEDIA_ROOT)
                User.objects.create_user('phase1b-broken-fixture')
                raise ValueError('simulated fixture failure')

        with self.assertRaisesMessage(ValueError, 'simulated fixture failure'):
            BrokenFixture.setUpClass()
        BrokenFixture.doClassCleanups()
        self.assertEqual(settings.MEDIA_ROOT, original)
        self.assertFalse(BrokenFixture.directory.exists())
        self.assertFalse(User.objects.filter(username='phase1b-broken-fixture').exists())
