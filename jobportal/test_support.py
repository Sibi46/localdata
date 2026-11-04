"""Test-only isolation helpers; production middleware and storage stay unchanged."""
import tempfile
import unittest
from pathlib import Path

from django.conf import settings
from django.core.cache import caches
from django.test import override_settings
from django.test.runner import DiscoverRunner


def verify_account_phone(client, phone, purpose='signup'):
    """Obtain real server-side test proof through the APIs; never forge flags."""
    import json
    from unittest.mock import patch
    with patch('jobs.otp_security.deliver_code', return_value=True) as delivery:
        result = client.post('/api/send-otp/', json.dumps({'phone': phone, 'purpose': purpose}),
                             content_type='application/json')
        if result.status_code != 200:
            raise AssertionError('Test OTP issuance failed: ' + result.content.decode())
        code = delivery.call_args.args[1]
    result = client.post('/api/verify-otp/', json.dumps({'phone': phone, 'purpose': purpose, 'otp': code}),
                         content_type='application/json')
    if result.status_code != 200:
        raise AssertionError('Test OTP verification failed: ' + result.content.decode())
    return code


def view_middleware():
    """Exercise view defenses separately from the integration registration gate."""
    return [item for item in settings.MIDDLEWARE
            if item != 'jobportal.middleware.LoginRequiredMiddleware']


class TemporaryMediaMixin:
    @classmethod
    def setUpClass(cls):
        # Install storage before TestCase.setUpClass calls setUpTestData.
        files = tempfile.TemporaryDirectory()
        cls.addClassCleanup(files.cleanup)
        media = override_settings(MEDIA_ROOT=files.name)
        media.enable()
        cls.addClassCleanup(media.disable)
        super().setUpClass()
        # unittest class cleanups run after Django's tearDownClass, including
        # when cleanup or fixture creation raises; rollback cannot be skipped.


class IsolatedMediaRunner(DiscoverRunner):
    def get_resultclass(self):
        base = super().get_resultclass() or unittest.TextTestResult

        class CacheIsolatedResult(base):
            def startTest(self, test):
                # Django rolls back database fixtures, but not cached lookups
                # or rate-limit counters derived from those fixtures.
                caches['default'].clear()
                super().startTest(test)

        return CacheIsolatedResult

    def run_tests(self, test_labels, **kwargs):
        root = Path(settings.BASE_DIR) / '.local-data'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='phase1b-tests-', dir=root) as directory:
            # Also direct nested TemporaryDirectory instances into the writable
            # test root. Never change the operating system's temp configuration.
            previous = tempfile.tempdir
            tempfile.tempdir = directory
            try:
                with override_settings(
                    MEDIA_ROOT=str(Path(directory) / 'media'),
                    STATIC_ROOT=str(Path(directory) / 'static'),
                    NEWSDESK_MEDIA_ROOT=str(Path(directory) / 'news'),
                    NEWS_IDENTITY_ROOT=str(Path(directory) / 'identity'),
                    CHAT_PRIVATE_ROOT=str(Path(directory) / 'chat'),
                ):
                    return super().run_tests(test_labels, **kwargs)
            finally:
                tempfile.tempdir = previous
