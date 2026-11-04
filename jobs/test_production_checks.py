from django.test import SimpleTestCase, override_settings

from .production_checks import production_configuration


@override_settings(
    DEBUG=False, DEMO_SIGNUP_OTP=False, DEMO_PASSWORD_RESET_OTP=False,
    TWO_FACTOR_API_KEY='synthetic-provider-key', TWO_FACTOR_OTP_TEMPLATE='approved-template',
    SECRET_KEY='synthetic-only-production-check-test-key-1234567890-abcdefgh',
    DATABASES={'default': {'ENGINE': 'django.db.backends.mysql', 'NAME': 'pilot',
                          'USER': 'pilot_app', 'PASSWORD': 'synthetic-only', 'HOST': '127.0.0.1'}},
    OTP_CACHE_ALIAS='otp', CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
                                'otp': {'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                                        'LOCATION': 'redis://127.0.0.1:6379/1'}},
    SITE_URL='https://www.localfrom.com', ALLOWED_HOSTS=['localfrom.com', 'www.localfrom.com'],
    SECURE_SSL_REDIRECT=True, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
)
class ProductionGuardTests(SimpleTestCase):
    def ids(self):
        return {error.id for error in production_configuration(None)}

    def test_complete_configuration_passes_without_contacting_services(self):
        self.assertEqual(self.ids(), set())

    def test_unconfigured_template_cannot_pass(self):
        with override_settings(TWO_FACTOR_API_KEY='CHANGE_ME_PROVIDER_KEY',
                               SECRET_KEY='CHANGE_ME_GENERATE_A_NEW_RANDOM_SECRET'):
            self.assertEqual(self.ids(), {'localfrom.E002', 'localfrom.E003'})

    def test_demo_codes_are_blocked_independently_of_debug(self):
        for option in ('DEMO_SIGNUP_OTP', 'DEMO_PASSWORD_RESET_OTP'):
            with self.subTest(option=option), override_settings(**{option: True}):
                self.assertEqual(self.ids(), {'localfrom.E001'})

    def test_local_database_and_process_cache_are_blocked(self):
        with override_settings(DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'}},
                               CACHES={'otp': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}):
            self.assertEqual(self.ids(), {'localfrom.E004', 'localfrom.E005'})

    def test_insecure_transport_and_wildcard_host_are_blocked(self):
        with override_settings(SESSION_COOKIE_SECURE=False, ALLOWED_HOSTS=['*']):
            self.assertEqual(self.ids(), {'localfrom.E006', 'localfrom.E007'})

    def test_debug_cannot_pass_deployment_guards(self):
        with override_settings(DEBUG=True):
            self.assertEqual(self.ids(), {'localfrom.E008'})

    def test_errors_never_contain_credentials(self):
        with override_settings(TWO_FACTOR_API_KEY='CHANGE_ME_secret-marker'):
            self.assertNotIn('secret-marker', str(production_configuration(None)))
