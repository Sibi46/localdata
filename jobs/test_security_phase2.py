"""Regression coverage for the retained production security boundaries."""
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from . import otp_security as otp
from .models import AdminProfile, CompanyProfile, Complaint, Conversation, District, Message, PinCode, State, User
from .test_shop_catalog import image_file


@override_settings(DEBUG=False, DEMO_SIGNUP_OTP=True, DEMO_PASSWORD_RESET_OTP=True)
class AccountOTPSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.delivery = patch('jobs.otp_security.deliver_code', return_value=True).start()
        self.addCleanup(patch.stopall)
        self.phone = '9876502001'

    def post(self, path, **data):
        return self.client.post(path, json.dumps(data), content_type='application/json')

    def issue(self, phone=None, purpose='signup', path='/api/send-otp/'):
        phone = phone or self.phone
        response = self.post(path, phone=phone, purpose=purpose, name='Local Person', pincode='604408')
        self.assertEqual(response.status_code, 200, response.content)
        code = self.delivery.call_args.args[1]
        self.assertNotIn(code.encode(), response.content)
        self.assertNotIn('code', self.client.session['account_otp_' + purpose])
        return code

    def proof(self, phone=None, purpose='signup', send='/api/send-otp/', verify='/api/verify-otp/'):
        phone = phone or self.phone
        code = self.issue(phone, purpose, send)
        result = self.post(verify, phone=phone, purpose=purpose, otp=code)
        self.assertEqual(result.status_code, 200, result.content)
        return code

    def signup(self, **extra):
        return self.post('/api/quick-register/', name='Local Person', phone=self.phone,
                         pincode='604408', password='SecurePassword!8', **extra)

    def user(self, **extra):
        return User.objects.create_user(self.phone, phone=self.phone, password='BeforePassword!8', **extra)

    def test_registration_endpoints_reject_missing_or_forged_legacy_flags(self):
        session = self.client.session
        session.update({'otp_verified': True, 'otp_phone': self.phone, 'reg_otp': '123456'})
        session.save()
        self.assertEqual(self.signup().status_code, 400)
        self.assertEqual(self.post('/api/verify-register-otp/', phone=self.phone,
                                  otp='123456', password='SecurePassword!8').status_code, 400)
        self.client.post('/register/process/', {'phone': self.phone, 'first_name': 'Local',
                        'password': 'SecurePassword!8', 'pincode': '604408'})
        self.client.post('/register/', {'password': 'SecurePassword!8', 'confirm_password': 'SecurePassword!8'})
        self.assertFalse(User.objects.exists())

    def test_quick_registration_consumes_phone_bound_proof(self):
        self.proof()
        self.assertEqual(self.post('/api/quick-register/', name='Local', phone='9876502002',
            pincode='604408', password='SecurePassword!8').status_code, 400)
        self.assertFalse(User.objects.exists())
        self.assertEqual(self.signup().status_code, 200)
        self.assertEqual(User.objects.get().phone, self.phone)
        self.assertNotIn('account_otp_signup', self.client.session)

    def test_multipart_registration_requires_and_consumes_same_proof(self):
        self.proof()
        response = self.client.post('/register/process/', {'phone': self.phone, 'first_name': 'Local',
            'password': 'SecurePassword!8', 'pincode': '604408', 'user_type': 'individual'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn('account_otp_signup', self.client.session)

    def test_legacy_registration_verification_keeps_creation_feature(self):
        code = self.issue(path='/api/send-register-otp/')
        response = self.post('/api/verify-register-otp/', phone=self.phone, otp=code, password='SecurePassword!8')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn('password', self.client.session.get('reg_data', {}))

    def test_legacy_password_at_send_is_hashed_and_account_created_after_verification(self):
        response = self.post('/api/send-register-otp/', phone=self.phone, name='Local Person',
                             pincode='604408', password='SecurePassword!8')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password', self.client.session['reg_data'])
        self.assertNotEqual(self.client.session['reg_data']['password_hash'], 'SecurePassword!8')
        code = self.delivery.call_args.args[1]
        self.assertEqual(self.post('/api/verify-register-otp/', phone=self.phone, otp=code).status_code, 200)
        self.assertTrue(User.objects.get().check_password('SecurePassword!8'))

    def test_production_signup_uses_delivery_and_never_displays_code(self):
        response = self.client.post('/register/', {'name': 'Local Person', 'phone': self.phone, 'pincode': '604408'})
        self.assertEqual(response.status_code, 302)
        code = self.delivery.call_args.args[1]
        self.assertNotIn('code', self.client.session['simple_signup'])
        self.assertNotIn(code.encode(), self.client.get('/register/').content)
        self.client.post('/register/', {'otp': code})
        self.client.post('/register/', {'password': 'SecurePassword!8', 'confirm_password': 'SecurePassword!8'})
        self.assertEqual(User.objects.count(), 1)

    def test_production_reset_uses_delivery_and_never_displays_code(self):
        user = self.user()
        self.client.post('/forgot-password/', {'phone': self.phone})
        code = self.delivery.call_args.args[1]
        self.assertNotIn('code', self.client.session['password_recovery'])
        self.assertNotIn(code.encode(), self.client.get('/forgot-password/').content)
        self.client.post('/forgot-password/', {'otp': code})
        self.client.post('/forgot-password/', {'password': 'AfterPassword!8', 'confirm_password': 'AfterPassword!8'})
        user.refresh_from_db()
        self.assertTrue(user.check_password('AfterPassword!8'))

    def test_recovery_preserves_legacy_phone_username_when_phone_field_is_empty(self):
        user = self.user()
        user.phone = ''
        user.save(update_fields=['phone'])
        self.client.post('/forgot-password/', {'phone': self.phone})
        code = self.delivery.call_args.args[1]
        self.client.post('/forgot-password/', {'otp': code})
        self.client.post('/forgot-password/', {'password': 'AfterPassword!8', 'confirm_password': 'AfterPassword!8'})
        user.refresh_from_db()
        self.assertTrue(user.check_password('AfterPassword!8'))

    def test_reset_rejects_wrong_phone_and_signup_purpose(self):
        self.proof()
        user = self.user()
        response = self.post('/api/reset-password/', phone=self.phone, password='AfterPassword!8')
        self.assertEqual(response.status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password('BeforePassword!8'))
        self.proof(purpose='reset')
        self.assertEqual(self.post('/api/reset-password/', phone='9876502002', password='AfterPassword!8').status_code, 400)

    def test_reset_proof_cannot_register_another_phone(self):
        self.user()
        self.proof(purpose='reset')
        response = self.post('/api/quick-register/', name='Other', phone='9876502002',
                             pincode='604408', password='SecurePassword!8')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_reset_consumption_rejects_replayed_session_and_logs_out(self):
        user = self.user()
        self.proof(purpose='reset')
        stale = dict(self.client.session['account_otp_reset'])
        self.assertEqual(self.post('/api/reset-password/', phone=self.phone, password='AfterPassword!8').status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        session = self.client.session
        session['account_otp_reset'] = stale
        session.save()
        self.assertEqual(self.post('/api/reset-password/', phone=self.phone, password='ReplayPassword!8').status_code, 400)
        user.refresh_from_db()
        self.assertTrue(user.check_password('AfterPassword!8'))

    def test_expired_challenge_and_expired_verified_proof_are_rejected(self):
        for verified in (False, True):
            with self.subTest(verified=verified):
                code = self.issue()
                if verified:
                    self.assertEqual(self.post('/api/verify-otp/', phone=self.phone, purpose='signup', otp=code).status_code, 200)
                pending = self.client.session['account_otp_signup']
                key = otp._key('proof', pending['nonce'])
                record = cache.get(key)
                record['created'] = time.time() - 601
                cache.set(key, record, 600)
                result = self.signup() if verified else self.post('/api/verify-otp/', phone=self.phone, purpose='signup', otp=code)
                self.assertEqual(result.status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_code_is_single_use_and_resend_revokes_verified_proof(self):
        code = self.proof()
        self.assertEqual(self.post('/api/verify-otp/', phone=self.phone, purpose='signup', otp=code).status_code, 400)
        self.issue()
        self.assertEqual(self.signup().status_code, 400)

    def test_attempt_limit_and_send_limit(self):
        code = self.issue()
        for _ in range(5):
            self.assertEqual(self.post('/api/verify-otp/', phone=self.phone, purpose='signup', otp='000000').status_code, 400)
        self.assertEqual(self.post('/api/verify-otp/', phone=self.phone, purpose='signup', otp=code).status_code, 400)
        self.issue()
        self.issue()
        self.assertEqual(self.post('/api/send-register-otp/', phone=self.phone).status_code, 400)

    def test_reset_rejects_admin_staff_disabled_and_legacy_verified_flag(self):
        for fields in ({'admin_role': 'super_admin'}, {'is_staff': True}, {'is_active': False}, {}):
            user = self.user(**fields)
            session = self.client.session
            session.update({'otp_verified': True, 'otp_phone': self.phone})
            session.save()
            self.assertEqual(self.post('/api/reset-password/', phone=self.phone, password='AfterPassword!8').status_code, 400)
            if fields:
                self.assertEqual(self.post('/api/send-otp/', phone=self.phone, purpose='reset').status_code, 400)
            user.delete()

    def test_delivery_failure_and_cache_failure_fail_closed(self):
        self.delivery.return_value = False
        self.assertEqual(self.post('/api/send-otp/', phone=self.phone).status_code, 400)
        self.assertNotIn('account_otp_signup', self.client.session)
        with patch('jobs.otp_security.store', side_effect=RuntimeError('cache unavailable')):
            self.assertEqual(self.signup().status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_cross_session_verification_and_malformed_payloads(self):
        code = self.issue()
        other = Client()
        result = other.post('/api/verify-otp/', json.dumps({'phone': self.phone, 'purpose': 'signup', 'otp': code}), content_type='application/json')
        self.assertEqual(result.status_code, 400)
        for path in ('/api/send-otp/', '/api/verify-otp/', '/api/send-register-otp/',
                     '/api/verify-register-otp/', '/api/quick-register/', '/api/reset-password/'):
            for body in ('{', '[]', 'null'):
                with self.subTest(path=path, body=body):
                    self.assertEqual(self.client.post(path, body, content_type='application/json').status_code, 400)

    def test_api_csrf_and_http_methods(self):
        client = Client(enforce_csrf_checks=True)
        for path in ('/api/send-otp/', '/api/verify-otp/', '/api/send-register-otp/',
                     '/api/verify-register-otp/', '/api/quick-register/', '/api/reset-password/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 405)
                self.assertEqual(client.post(path, '{}', content_type='application/json').status_code, 403)


class OTPTransportTests(TestCase):
    @override_settings(OTP_DELIVERY_ENABLED=True, TWO_FACTOR_API_KEY='synthetic-key', TWO_FACTOR_OTP_TEMPLATE='TEST')
    def test_provider_posts_code_outside_url_and_requires_success(self):
        with patch('jobs.otp_security.requests.post', return_value=Mock(ok=True, json=lambda: {'status': 'sent'})) as send:
            self.assertTrue(otp.deliver_code('9876502001', '123456'))
            args, kwargs = send.call_args
            self.assertNotIn('123456', args[0])
            self.assertNotIn('synthetic-key', args[0])
            self.assertEqual(kwargs['json']['var1'], '123456')
            self.assertFalse(kwargs['allow_redirects'])
        with patch('jobs.otp_security.requests.post', return_value=Mock(ok=True, json=lambda: {'status': 'failed'})):
            self.assertFalse(otp.deliver_code('9876502001', '123456'))

    @override_settings(DEBUG=False, DEMO_SIGNUP_OTP=True, DEMO_PASSWORD_RESET_OTP=True)
    def test_demo_flags_never_enable_production_display(self):
        self.assertFalse(otp.demo_enabled('signup'))
        self.assertFalse(otp.demo_enabled('reset'))


class StateAdminSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.state = State.objects.create(name='Security state A', code='S2A')
        cls.foreign_state = State.objects.create(name='Security state B', code='S2B')
        cls.district = District.objects.create(name='Local district', state=cls.state)
        cls.foreign_district = District.objects.create(name='Foreign district', state=cls.foreign_state)
        PinCode.objects.create(code='600101', district=cls.district)
        PinCode.objects.create(code='600102', district=cls.foreign_district)
        cls.admin = User.objects.create_user('state-security-admin', admin_role='state_admin')
        AdminProfile.objects.create(user=cls.admin, role='state_admin', state=cls.state)
        cls.local = User.objects.create_user('local-security-shop', pincode='600101', user_type='shop')
        cls.foreign = User.objects.create_user('foreign-security-shop', pincode='600102', user_type='shop')
        cls.root = User.objects.create_user('root-security-admin', admin_role='super_admin', pincode='600101')
        cls.staff = User.objects.create_user('staff-security-user', is_staff=True, pincode='600101')
        CompanyProfile.objects.create(user=cls.local, company_name='Local scoped shop')
        CompanyProfile.objects.create(user=cls.foreign, company_name='Foreign scoped shop')

    def setUp(self):
        self.client.force_login(self.admin)

    def test_scope_filters_employers_dashboard_and_reports(self):
        page = self.client.get('/state-admin/employers/')
        self.assertContains(page, 'Local scoped shop')
        self.assertNotContains(page, 'Foreign scoped shop')
        self.assertEqual(self.client.get('/state-admin/').context['pending_employers'], 1)
        report = self.client.get('/state-admin/reports/')
        self.assertEqual(report.context['business_count'], 1)

    def test_cross_state_and_privileged_target_mutations_are_denied(self):
        for user in (self.foreign, self.root, self.staff, self.admin):
            self.assertEqual(self.client.post(f'/state-admin/users/{user.pk}/suspend/').status_code, 404)
            user.refresh_from_db()
            self.assertTrue(user.is_active)
        self.assertEqual(self.client.post(f'/state-admin/users/{self.local.pk}/suspend/').status_code, 302)
        self.local.refresh_from_db()
        self.assertFalse(self.local.is_active)

    def test_forged_district_and_get_mutation_are_denied(self):
        before = User.objects.count()
        response = self.client.post('/state-admin/district-admins/create/', {
            'fullname': 'New Admin', 'phone': '9876502201', 'password': 'AdminPassword!8',
            'district_id': self.foreign_district.pk})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(User.objects.count(), before)
        self.assertEqual(self.client.get(f'/state-admin/users/{self.local.pk}/suspend/').status_code, 405)
        self.local.refresh_from_db()
        self.assertTrue(self.local.is_active)

    def test_district_alias_cannot_bypass_state_or_role_restrictions(self):
        for user in (self.foreign, self.root, self.staff):
            self.assertEqual(self.client.post('/district-admin/employers/', {
                'user_id': user.pk, 'action': 'block'}).status_code, 404)
            user.refresh_from_db()
            self.assertTrue(user.is_active)
        response = self.client.get('/district-admin/employers/')
        self.assertEqual(list(response.context['employers'].values_list('pk', flat=True)), [self.local.pk])

    def test_complaint_resolution_alias_is_geographically_scoped(self):
        complaint = Complaint.objects.create(submitted_by=self.foreign, district=self.foreign_district,
                                             subject='Foreign complaint', description='Private')
        path = f'/district-admin/complaints/{complaint.pk}/resolve/'
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.post(path, {'resolution': 'Not allowed', 'status': 'resolved'}).status_code, 404)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'open')

    def test_mutations_require_csrf_and_valid_local_post_works(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        for path in (f'/state-admin/users/{self.local.pk}/suspend/', '/state-admin/district-admins/create/'):
            self.assertEqual(client.post(path, {}).status_code, 403)
        client.get('/state-admin/employers/')
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(f'/state-admin/users/{self.local.pk}/suspend/',
                                    HTTP_X_CSRFTOKEN=token).status_code, 302)

    def test_valid_local_district_admin_creation_and_lower_role_management_remain(self):
        response = self.client.post('/state-admin/district-admins/create/', {
            'fullname': 'Local District Admin', 'phone': '9876502202',
            'password': 'AdminPassword!8', 'district_id': self.district.pk})
        self.assertEqual(response.status_code, 302)
        target = User.objects.get(phone='9876502202')
        self.assertEqual(target.admin_profile.district, self.district)
        self.assertFalse(target.is_staff)
        self.assertEqual(self.client.post(f'/state-admin/users/{target.pk}/suspend/').status_code, 302)
        target.refresh_from_db()
        self.assertFalse(target.is_active)

    def test_main_admin_keeps_global_scope_but_cannot_suspend_self(self):
        self.client.force_login(self.root)
        self.assertEqual(self.client.post(f'/state-admin/users/{self.foreign.pk}/suspend/').status_code, 302)
        self.foreign.refresh_from_db()
        self.assertFalse(self.foreign.is_active)
        self.assertEqual(self.client.post(f'/state-admin/users/{self.root.pk}/suspend/').status_code, 404)

    def test_missing_and_suspended_state_assignments_fail_closed(self):
        profile = self.admin.admin_profile
        profile.is_active = False
        profile.save()
        for path in ('/state-admin/', '/state-admin/employers/', '/state-admin/reports/',
                     '/state-admin/district-admins/create/'):
            self.assertEqual(self.client.get(path).status_code, 403)
        profile.delete()
        self.assertEqual(self.client.get('/state-admin/employers/').status_code, 403)


class ChatAttachmentSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sender = User.objects.create_user('private-chat-sender')
        cls.receiver = User.objects.create_user('private-chat-receiver')
        cls.stranger = User.objects.create_user('private-chat-stranger')
        cls.conversation = Conversation.objects.create(user_a=cls.sender, user_b=cls.receiver)

    def upload(self, file=None):
        self.client.force_login(self.sender)
        response = self.client.post(reverse('send_message'), {'conv_id': self.conversation.pk,
            'msg_type': 'file', 'file': file or SimpleUploadedFile('private.txt', b'private attachment')})
        self.assertEqual(response.status_code, 200, response.content)
        message = Message.objects.get()
        url = reverse('chat_attachment', args=[message.pk])
        self.assertIn(url, response.json()['html'])
        return message, url

    def test_new_files_are_private_and_participants_can_download(self):
        message, url = self.upload()
        self.assertTrue((Path(settings.CHAT_PRIVATE_ROOT) / message.file.name).is_file())
        self.assertFalse((Path(settings.MEDIA_ROOT) / message.file.name).exists())
        for member in (self.sender, self.receiver):
            self.client.force_login(member)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'private attachment')
            self.assertIn('private', response['Cache-Control'])
            self.assertIn('no-store', response['Cache-Control'])
            response.close()

    def test_guest_and_unrelated_user_cannot_download_or_guess_raw_media(self):
        message, url = self.upload()
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(url).status_code, 404)
        for user in (None, self.sender, self.stranger):
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.get('/media/' + message.file.name).status_code, 404)
        self.client.force_login(self.sender)
        for path in ('/media//chat_files/legacy.txt', '/media/chat_files\\legacy.txt',
                     '/media/CHAT_FILES/legacy.txt', '/media/products/../chat_files/legacy.txt'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_historical_attachment_is_preserved_but_only_authorized_route_serves_it(self):
        path = Path(settings.MEDIA_ROOT) / 'chat_files/legacy.txt'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'historical private data')
        message = Message.objects.create(conversation=self.conversation, sender=self.sender,
            receiver=self.receiver, msg_type='file', file='chat_files/legacy.txt', file_name='legacy.txt')
        self.client.force_login(self.receiver)
        response = self.client.get(reverse('chat_attachment', args=[message.pk]))
        self.assertEqual(b''.join(response.streaming_content), b'historical private data')
        response.close()
        self.assertTrue(path.exists())
        self.assertEqual(self.client.get('/media/chat_files/legacy.txt').status_code, 404)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(reverse('chat_attachment', args=[message.pk])).status_code, 404)

    def test_images_still_render_inline_and_only_safe_methods_are_allowed(self):
        message, url = self.upload(image_file('private.png'))
        response = self.client.get(url)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(response['Content-Disposition'].startswith('inline'))
        response.close()
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertContains(self.client.get(reverse('chat_room', args=[self.conversation.pk])), url)
