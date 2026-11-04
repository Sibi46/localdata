"""Temporary public signup never authenticates or recovers an existing account."""
import json
import time
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from . import otp_security as otp
from .models import User


@override_settings(
    PUBLIC_DEMO_SIGNUP=True, DEBUG=False,
    DEMO_SIGNUP_OTP=False, DEMO_PASSWORD_RESET_OTP=False,
    TWO_FACTOR_API_KEY='', TWO_FACTOR_OTP_TEMPLATE='',
    OTP_CACHE_ALIAS='default',
)
class PublicDemoSignupTests(TestCase):
    phone = '9876507201'
    password = 'LocalPassword!123'

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        delivery = patch('jobs.otp_security.deliver_code', return_value=False)
        self.delivery = delivery.start()
        self.addCleanup(delivery.stop)

    def post(self, path, client=None, **data):
        return (client or self.client).post(
            path, json.dumps(data), content_type='application/json',
        )

    def challenge(self, path='/api/send-otp/', client=None):
        response = self.post(
            path, client=client, phone=self.phone, name='Local Person',
            pincode='604408', purpose='signup',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIs(response.json()['phone_ownership_verified'], False)
        self.assertIs(response.json()['demo'], True)
        self.assertIn('Testing code only', response.json()['message'])
        self.delivery.assert_not_called()
        return response.json()['otp']

    def proof(self):
        code = self.challenge()
        response = self.post('/api/verify-otp/', phone=self.phone, purpose='signup', otp=code)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIs(response.json()['phone_ownership_verified'], False)
        return code

    def signup(self):
        return self.post('/api/quick-register/', phone=self.phone,
                         name='Local Person', pincode='604408', password=self.password)

    def existing_user(self):
        return User.objects.create_user(self.phone, phone=self.phone, password=self.password)

    def test_browser_signup_discloses_demo_and_password_login_is_required(self):
        response = self.client.get('/register/')
        self.assertNotContains(response, 'Temporary demo signup')
        self.assertNotContains(response, 'Testing code only')
        details = {'name': 'Local Person', 'phone': self.phone, 'pincode': '604408'}
        self.assertEqual(self.client.post('/register/', details).status_code, 302)
        response = self.client.get('/register/')
        self.assertNotContains(response, 'Temporary demo signup')
        self.assertContains(response, 'does not verify phone ownership')
        self.assertContains(response, 'Demo OTP')
        code = self.client.session['simple_signup']['code']
        self.assertEqual(self.client.post('/register/', {'otp': code}).status_code, 302)
        self.assertFalse(User.objects.exists())
        self.assertEqual(self.client.post('/register/', {
            'password': self.password, 'confirm_password': self.password,
        }).status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        self.client.logout()
        self.client.post('/login/', {'username': self.phone, 'password': code})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.client.post('/login/', {'username': self.phone, 'password': self.password})
        self.assertEqual(self.client.session['_auth_user_id'], str(User.objects.get().pk))
        self.delivery.assert_not_called()

    def test_both_json_signup_endpoints_label_codes_as_unverified(self):
        for path in ('/api/send-otp/', '/api/send-register-otp/'):
            with self.subTest(path=path):
                self.challenge(path)

    def test_completing_demo_challenge_never_sets_phone_ownership_verified(self):
        self.proof()
        pending = self.client.session['account_otp_signup']
        record = otp.store().get(otp._key('proof', pending['nonce']))
        self.assertTrue(record['verified'])
        self.assertFalse(record['phone_ownership_verified'])
        result = self.signup()
        self.assertEqual(result.status_code, 200)
        self.assertIs(result.json()['phone_ownership_verified'], False)

    def test_duplicate_phone_is_rejected_by_browser_and_json_paths(self):
        self.existing_user()
        self.assertContains(self.client.post('/register/', {
            'name': 'Local Person', 'phone': self.phone, 'pincode': '604408',
        }), 'already registered')
        for path in ('/api/send-otp/', '/api/send-register-otp/'):
            self.assertEqual(self.post(path, phone=self.phone).status_code, 400)
        self.assertEqual(self.signup().status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_created_after_proof_cannot_be_replaced(self):
        self.proof()
        original = self.existing_user()
        self.assertEqual(self.signup().status_code, 400)
        original.refresh_from_db()
        self.assertTrue(original.check_password(self.password))
        self.assertEqual(User.objects.count(), 1)

    def test_signup_requires_proof_even_with_forged_legacy_flags(self):
        session = self.client.session
        session.update({'otp_verified': True, 'otp_phone': self.phone})
        session.save()
        self.assertEqual(self.signup().status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_wrong_phone_wrong_purpose_and_other_session_cannot_verify(self):
        code = self.challenge()
        for phone, purpose, client in (
            ('9876507202', 'signup', self.client),
            (self.phone, 'reset', self.client),
            (self.phone, 'signup', Client()),
        ):
            response = self.post('/api/verify-otp/', client=client,
                                 phone=phone, purpose=purpose, otp=code)
            self.assertEqual(response.status_code, 400)

    def test_expired_code_is_rejected(self):
        code = self.challenge()
        pending = self.client.session['account_otp_signup']
        key = otp._key('proof', pending['nonce'])
        record = otp.store().get(key)
        record['created'] = time.time() - 601
        otp.store().set(key, record, 600)
        self.assertEqual(self.post('/api/verify-otp/', phone=self.phone,
                                  purpose='signup', otp=code).status_code, 400)

    def test_verified_proof_is_single_use(self):
        self.proof()
        pending = dict(self.client.session['account_otp_signup'])
        self.assertEqual(self.signup().status_code, 200)
        session = self.client.session
        session['account_otp_signup'] = pending
        session.save()
        from django.test import RequestFactory
        request = RequestFactory().post('/')
        request.session = self.client.session
        with self.assertRaises(otp.OTPError):
            otp.consume(request, self.phone, 'signup')
        self.assertEqual(User.objects.count(), 1)

    def test_expired_verified_proof_cannot_create_account(self):
        self.proof()
        pending = self.client.session['account_otp_signup']
        key = otp._key('proof', pending['nonce'])
        record = otp.store().get(key)
        record['created'] = time.time() - 601
        otp.store().set(key, record, 600)
        self.assertEqual(self.signup().status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_existing_account_phone_api_requires_password_not_demo_code(self):
        self.proof()
        self.assertEqual(self.signup().status_code, 200)
        self.client.logout()
        response = self.post('/api/phone-login/', phone=self.phone, password='000000')
        self.assertFalse(response.json()['success'])
        self.assertNotIn('_auth_user_id', self.client.session)
        response = self.post('/api/phone-login/', phone=self.phone, password=self.password)
        self.assertTrue(response.json()['success'])
        self.assertEqual(self.client.session['_auth_user_id'], str(User.objects.get().pk))

    def test_attempt_and_send_limits_remain_enabled(self):
        code = self.challenge()
        for _ in range(5):
            self.assertEqual(self.post('/api/verify-otp/', phone=self.phone,
                                      purpose='signup', otp='000000').status_code, 400)
        self.assertEqual(self.post('/api/verify-otp/', phone=self.phone,
                                  purpose='signup', otp=code).status_code, 400)
        self.challenge()
        self.challenge()
        self.assertEqual(self.post('/api/send-otp/', phone=self.phone).status_code, 400)

    def test_cache_failure_does_not_create_account(self):
        with patch('jobs.otp_security.store', side_effect=RuntimeError('cache unavailable')):
            self.assertEqual(self.post('/api/send-otp/', phone=self.phone).status_code, 400)
            self.assertEqual(self.signup().status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_csrf_and_post_requirements_remain_enabled(self):
        csrf = Client(enforce_csrf_checks=True)
        for path in ('/api/send-otp/', '/api/verify-otp/', '/api/quick-register/',
                     '/api/send-register-otp/', '/api/verify-register-otp/'):
            self.assertEqual(self.client.get(path).status_code, 405)
            self.assertEqual(self.post(path, client=csrf, phone=self.phone).status_code, 403)

    def test_existing_account_reset_is_blocked_at_every_endpoint(self):
        user = self.existing_user()
        for path, data in (
            ('/api/send-otp/', {'purpose': 'reset'}),
            ('/api/send-otp/', {'allow_existing': True}),
            ('/api/verify-otp/', {'purpose': 'reset', 'otp': '123456'}),
            ('/api/reset-password/', {'password': 'ReplacementPassword!123'}),
        ):
            self.assertEqual(self.post(path, phone=self.phone, **data).status_code, 400)
        for method, data in (('get', {}), ('post', {'phone': self.phone}),
                             ('post', {'otp': '123456'}), ('post', {'password': self.password})):
            response = getattr(self.client, method)('/forgot-password/', data)
            self.assertContains(response, 'Password recovery is temporarily unavailable', status_code=503)
            self.assertNotContains(response, '<form', status_code=503)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.password))
        self.delivery.assert_not_called()

    def test_reset_proof_issued_before_mode_switch_cannot_be_verified_or_consumed(self):
        user = self.existing_user()
        with override_settings(PUBLIC_DEMO_SIGNUP=False), patch(
            'jobs.otp_security.deliver_code', return_value=True,
        ) as delivery:
            response = self.post('/api/send-otp/', phone=self.phone, purpose='reset')
            self.assertEqual(response.status_code, 200)
            code = delivery.call_args.args[1]
            self.assertEqual(self.post('/api/verify-otp/', phone=self.phone,
                                      purpose='reset', otp=code).status_code, 200)
        self.assertEqual(self.post('/api/verify-otp/', phone=self.phone,
                                  purpose='reset', otp=code).status_code, 400)
        self.assertEqual(self.post('/api/reset-password/', phone=self.phone,
                                  password='ReplacementPassword!123').status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.password))

    def test_turning_mode_off_revokes_demo_proof_and_hides_real_codes(self):
        code = self.challenge()
        with override_settings(PUBLIC_DEMO_SIGNUP=False), patch(
            'jobs.otp_security.deliver_code', return_value=True,
        ) as delivery:
            self.assertEqual(self.post('/api/verify-otp/', phone=self.phone,
                                      purpose='signup', otp=code).status_code, 400)
            response = self.post('/api/send-otp/', phone=self.phone)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('otp', response.json())
            self.assertNotIn(delivery.call_args.args[1].encode(), response.content)

    @override_settings(DEBUG=True, DEMO_PASSWORD_RESET_OTP=True)
    def test_public_mode_never_enables_demo_reset_even_with_legacy_flag(self):
        self.assertFalse(otp.demo_enabled('reset'))
        with self.assertRaises(otp.OTPError):
            otp.issue(type('Request', (), {'session': {}})(), self.phone, 'reset')

    def test_news_identity_still_requires_real_sms(self):
        self.client.force_login(self.existing_user())
        with patch('newsdesk.public_views.deliver_otp', return_value=False):
            response = self.post(reverse('newsdesk:share_send_otp'), phone=self.phone)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('otp', response.json())
        self.assertNotIn('news_phone_proof', self.client.session)

    def test_inactive_user_cannot_log_in_through_phone_api(self):
        user = self.existing_user()
        user.is_active = False
        user.save(update_fields=['is_active'])
        response = self.post('/api/phone-login/', phone=self.phone, password=self.password)
        self.assertFalse(response.json()['success'])
        self.assertNotIn('_auth_user_id', self.client.session)
