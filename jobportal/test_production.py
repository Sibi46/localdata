import os
from pathlib import Path
import runpy
import dotenv
from types import SimpleNamespace
from copy import deepcopy
from unittest.mock import patch

from channels.testing import WebsocketCommunicator
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TransactionTestCase, RequestFactory, override_settings



class ProductionSettingsTests(SimpleTestCase):
    def load_settings(self, _isolate_local=False, **environment):
        values = {'DJANGO_SECRET_KEY': 'synthetic-test-key', **environment}
        with patch.dict(os.environ, values, clear=True), patch.object(dotenv, 'load_dotenv'):
            if _isolate_local:
                with patch.dict('sys.modules', {'jobportal.local_settings': None}):
                    return runpy.run_path(str(Path(__file__).with_name('settings.py')))
            return runpy.run_path(str(Path(__file__).with_name('settings.py')))

    def test_secret_is_required(self):
        for value in ('', '   '):
            with self.subTest(value=value), self.assertRaises(ImproperlyConfigured):
                self.load_settings(DJANGO_SECRET_KEY=value)

    def test_missing_secret_is_rejected(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(dotenv, 'load_dotenv'):
            with self.assertRaises(ImproperlyConfigured):
                runpy.run_path(str(Path(__file__).with_name('settings.py')))

    def test_secure_defaults_and_domain(self):
        config = self.load_settings()
        self.assertEqual(config['SITE_NAME'], 'Local From')
        self.assertEqual(config['SITE_URL'], 'https://www.localfrom.com')
        self.assertFalse(config['DEBUG'])
        self.assertEqual(config['ALLOWED_HOSTS'], ['localfrom.com', 'www.localfrom.com'])
        self.assertTrue(config['SESSION_COOKIE_SECURE'])
        self.assertTrue(config['CSRF_COOKIE_SECURE'])
        self.assertTrue(config['SECURE_SSL_REDIRECT'])
        self.assertEqual(config['SECURE_HSTS_SECONDS'], 0)
        self.assertEqual(config['SECURE_PROXY_SSL_HEADER'], ('HTTP_X_FORWARDED_PROTO', 'https'))

    def test_environment_overrides_and_list_whitespace(self):
        config = self.load_settings(
            _isolate_local=True,
            DJANGO_DEBUG='true', DJANGO_SECURE_SSL_REDIRECT='0',
            DJANGO_ALLOWED_HOSTS=' preview.example.com, localhost, ',
            DJANGO_CSRF_TRUSTED_ORIGINS=' https://preview.example.com, ',
            SITE_URL='https://preview.example.com/', STATIC_ROOT='/test/static',
            MEDIA_ROOT='/test/media', CACHE_LOCATION='/test/cache',
            REDIS_URL='redis://localhost:6380/2', GROQ_API_KEY='synthetic',
            GOOGLE_MAPS_KEY='synthetic-maps',
        )
        self.assertTrue(config['DEBUG'])
        self.assertFalse(config['SECURE_SSL_REDIRECT'])
        self.assertEqual(config['ALLOWED_HOSTS'], ['preview.example.com', 'localhost'])
        self.assertEqual(config['CSRF_TRUSTED_ORIGINS'], ['https://preview.example.com'])
        self.assertEqual(config['SITE_URL'], 'https://preview.example.com')
        self.assertEqual(config['STATIC_ROOT'], Path('/test/static').resolve())
        self.assertEqual(config['MEDIA_ROOT'], Path('/test/media').resolve())
        self.assertEqual(config['CACHES']['default']['LOCATION'], str(Path('/test/cache').resolve()))
        self.assertEqual(config['CHANNEL_LAYERS']['default']['CONFIG']['hosts'], ['redis://localhost:6380/2'])
        self.assertEqual(config['GROQ_API_KEY'], 'synthetic')
        self.assertEqual(config['GOOGLE_MAPS_KEY'], 'synthetic-maps')

    def test_invalid_environment_fails_clearly(self):
        for values in ({'DJANGO_DEBUG': 'typo'}, {'EMAIL_PORT': 'smtp'},
                       {'EMAIL_TIMEOUT': '0'}, {'DJANGO_SECURE_HSTS_SECONDS': '-1'},
                       {'EMAIL_USE_TLS': 'true', 'EMAIL_USE_SSL': 'true'},
                       {'SITE_URL': 'javascript:alert(1)'},
                       {'SITE_URL': 'https://user:password@example.com/path'}):
            with self.subTest(values=values), self.assertRaises(ImproperlyConfigured):
                self.load_settings(**values)

    def test_email_provider_is_configurable(self):
        config = self.load_settings(EMAIL_HOST='smtp.example.com', EMAIL_PORT='465',
                                    EMAIL_USE_TLS='false', EMAIL_USE_SSL='true',
                                    EMAIL_TIMEOUT='15')
        self.assertEqual(config['EMAIL_HOST'], 'smtp.example.com')
        self.assertEqual(config['EMAIL_PORT'], 465)
        self.assertFalse(config['EMAIL_USE_TLS'])
        self.assertTrue(config['EMAIL_USE_SSL'])
        self.assertEqual(config['EMAIL_TIMEOUT'], 15)

    @override_settings(SITE_URL='https://preview.example.com', SITE_NAME='Preview Branding')
    def test_real_templates_use_branding_context_processor(self):
        request = RequestFactory().get('/', HTTP_HOST='ourpincode.com')
        request.user = AnonymousUser()
        context = {'adv': SimpleNamespace(status='approved', business_name='Test Business',
                                          banner_image=SimpleNamespace(url='/media/test.png')),
                   'ads': []}
        # Reset the engine cache so the unrelated database-backed ad processor
        # can be substituted; the real branding processor remains registered.
        with patch('jobs.context_processors.site_ads', return_value={}), override_settings(
                TEMPLATES=deepcopy(settings.TEMPLATES)):
            gallery = render_to_string('ads_gallery.html', context, request=request)
            dashboard = render_to_string('advertiser_dashboard.html', context, request=request)
        self.assertIn('Offers worth stopping for.', gallery)
        self.assertEqual(dashboard.count('href="https://preview.example.com"'), 2)
        self.assertIn('>Preview Branding</a>', dashboard)
        for rendered in (gallery, dashboard):
            self.assertNotIn('mypincod.com', rendered)
            self.assertNotIn('{{ SITE_URL', rendered)

    def test_storage_paths_reject_empty_and_overlapping_values(self):
        checkout = Path(__file__).resolve().parent.parent
        invalid = [
            {name: value}
            for name in ('STATIC_ROOT', 'MEDIA_ROOT', 'CACHE_LOCATION')
            for value in ('', '   ')
        ]
        for name in ('STATIC_ROOT', 'MEDIA_ROOT'):
            invalid.extend({name: str(path)} for path in (
                checkout, checkout / 'uploads', checkout.parent,
                checkout / '..' / checkout.name / 'uploads',
            ))
        sibling = checkout.parent / 'isolated-test-storage'
        invalid.extend([
            {'STATIC_ROOT': str(sibling), 'MEDIA_ROOT': str(sibling)},
            {'STATIC_ROOT': str(sibling), 'MEDIA_ROOT': str(sibling / 'media')},
            {'STATIC_ROOT': str(sibling / 'static'), 'MEDIA_ROOT': str(sibling)},
        ])
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ImproperlyConfigured):
                self.load_settings(**values)

    def test_relative_paths_resolve_against_checkout(self):
        checkout = Path(__file__).resolve().parent.parent
        config = self.load_settings(STATIC_ROOT='../isolated-static',
                                    MEDIA_ROOT='../isolated-media',
                                    CACHE_LOCATION='.cache/../.cache')
        self.assertEqual(config['STATIC_ROOT'], (checkout.parent / 'isolated-static').resolve())
        self.assertEqual(config['MEDIA_ROOT'], (checkout.parent / 'isolated-media').resolve())
        self.assertEqual(config['CACHES']['default']['LOCATION'], str(checkout / '.cache'))

    def test_site_url_rejects_invalid_ports(self):
        for url in ('https://ourpincode.com:invalid', 'https://ourpincode.com:65536',
                    'https://ourpincode.com:-1', 'https://ourpincode.com:',
                    'https://ourpincode.com:0', 'https://[broken'):
            with self.subTest(url=url), self.assertRaises(ImproperlyConfigured):
                self.load_settings(SITE_URL=url)
        self.assertEqual(self.load_settings(SITE_URL='https://ourpincode.com:8443')['SITE_URL'],
                         'https://ourpincode.com:8443')

    def test_production_does_not_import_local_overrides(self):
        with patch('importlib.import_module', side_effect=AssertionError('must not import')):
            config = self.load_settings()
        self.assertFalse(config['DEBUG'])

    def test_development_local_settings_missing_vs_broken(self):
        missing = ModuleNotFoundError(name='jobportal.local_settings')
        with patch('importlib.import_module', side_effect=missing):
            self.assertTrue(self.load_settings(DJANGO_DEBUG='true')['DEBUG'])
        for error in (ModuleNotFoundError(name='missing_dependency'), ImportError('broken module')):
            with patch('importlib.import_module', side_effect=error):
                with self.assertRaises(type(error)):
                    self.load_settings(DJANGO_DEBUG='true')
        with patch('importlib.import_module', return_value=SimpleNamespace(SITE_NAME='Local Dev')):
            self.assertEqual(self.load_settings(DJANGO_DEBUG='true')['SITE_NAME'], 'Local Dev')

    def test_test_settings_restore_process_environment(self):
        source = Path(__file__).with_name('test_settings.py').read_text()
        with patch.dict(os.environ, {'DJANGO_SECRET_KEY': 'original-test-value',
                                     'SENTRY_DSN': '', 'DJANGO_DEBUG': 'false'}):
            before = dict(os.environ)
            exec(compile(source, 'test_settings.py', 'exec'),
                 {'__name__': 'jobportal._test_settings_probe', '__package__': 'jobportal'})
            self.assertEqual(dict(os.environ), before)

    @override_settings(SITE_URL='https://preview.example.com')
    def test_invitation_email_uses_canonical_site_url(self):
        from portal.views import _notify_leader

        leader = SimpleNamespace(
            token='synthetic-token',
            user=SimpleNamespace(get_full_name=lambda: 'Test Member', username='member'),
            community=SimpleNamespace(name='Test Community', page_id='test-community'),
            get_role_display=lambda: 'President',
            nominated_by=SimpleNamespace(get_full_name=lambda: 'Test Admin', username='admin'),
        )
        with patch('portal.views.send_mail') as send:
            _notify_leader(leader, 'member@example.com')
        send.assert_called_once()
        message = send.call_args.kwargs['message']
        self.assertIn('https://preview.example.com/portal/leader/accept/synthetic-token/', message)
        self.assertNotIn('mypincod.com', message)

    def test_groq_call_shape_without_network(self):
        import httpx
        from groq import Groq

        response = {'id': 'test', 'object': 'chat.completion', 'created': 0,
                    'model': 'llama-3.1-8b-instant', 'choices': [
                        {'index': 0, 'message': {'role': 'assistant', 'content': 'validated'},
                         'finish_reason': 'stop'}]}
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=response))
        with Groq(api_key='synthetic-test-key', http_client=httpx.Client(transport=transport)) as client:
            result = client.chat.completions.create(
                model='llama-3.1-8b-instant', messages=[{'role': 'user', 'content': 'test'}],
                max_tokens=500, temperature=0.7,
            )
        self.assertEqual(result.choices[0].message.content, 'validated')

    async def test_anonymous_websocket_still_rejected(self):
        from jobportal.asgi import application

        client = WebsocketCommunicator(application, '/ws/notifications/',
                                        headers=[(b'origin', b'https://ourpincode.com')])
        connected, _ = await client.connect()
        self.assertFalse(connected)
        await client.disconnect()


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class AuthenticatedWebSocketTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='websocket-test-user')
        self.client.force_login(self.user, backend='django.contrib.auth.backends.ModelBackend')
        self.cookie = f'{settings.SESSION_COOKIE_NAME}={self.client.cookies[settings.SESSION_COOKIE_NAME].value}'.encode()

    async def test_authenticated_notification_delivery(self):
        from channels.layers import get_channel_layer
        from jobportal.asgi import application

        for origin in (b'https://ourpincode.com', b'https://www.ourpincode.com'):
            client = WebsocketCommunicator(application, '/ws/notifications/', headers=[
                (b'origin', origin), (b'cookie', self.cookie)])
            connected, _ = await client.connect()
            try:
                self.assertTrue(connected)
                layer = get_channel_layer()
                await layer.group_send(f'notif_user_{self.user.pk + 1}', {
                    'type': 'send_notification', 'message': 'another user',
                })
                self.assertTrue(await client.receive_nothing(timeout=0.05))
                await layer.group_send(f'notif_user_{self.user.pk}', {
                    'type': 'send_notification', 'message': 'Test notification',
                    'link': '/portal/', 'notif_type': 'info',
                })
                self.assertEqual(await client.receive_json_from(), {
                    'message': 'Test notification', 'link': '/portal/', 'type': 'info',
                })
            finally:
                await client.disconnect()

    async def test_authenticated_untrusted_or_missing_origin_is_rejected(self):
        from jobportal.asgi import application

        for origin in (b'https://untrusted.example', None):
            headers = [(b'cookie', self.cookie)]
            if origin is not None:
                headers.append((b'origin', origin))
            client = WebsocketCommunicator(application, '/ws/notifications/', headers=headers)
            connected, _ = await client.connect()
            try:
                self.assertFalse(connected)
            finally:
                await client.disconnect()
