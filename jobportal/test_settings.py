"""Local validation only: no production credentials or external services.

Run: python manage.py test jobportal.test_production --settings=jobportal.test_settings
"""
import os
from unittest.mock import patch

# Deliberately synthetic; never import this module in a deployment service.
with patch.dict(os.environ, {
    'DJANGO_SECRET_KEY': 'local-tests-only-not-a-production-secret',
    'SENTRY_DSN': '',
    'DJANGO_DEBUG': 'false',
}):
    from .settings import *

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
ALLOWED_HOSTS = ['ourpincode.com', 'www.ourpincode.com', 'testserver']
SECURE_SSL_REDIRECT = False
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
TEST_RUNNER = 'jobportal.test_support.IsolatedMediaRunner'
OTP_CACHE_ALIAS = 'default'
OTP_DELIVERY_ENABLED = False  # Tests must never send real SMS.
