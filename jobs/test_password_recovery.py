import time
from django.core.cache import cache
from django.test import TestCase,override_settings
from django.urls import reverse
from .models import User
from .simple_accounts import DetailsForm


@override_settings(DEMO_PASSWORD_RESET_OTP=True, DEBUG=True)
class PasswordRecoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=User.objects.create_user('9876500194',phone='9876500194',first_name='Sibi Kumar',password='PreviousPassword!8',user_type='individual')
        cls.admin=User.objects.create_user('9876500195',phone='9876500195',password='AdminPassword!8',admin_role='super_admin')

    def setUp(self):cache.clear()

    def begin(self):return self.client.post(reverse('forgot_password'),{'phone':self.user.phone})

    def verify(self):return self.client.post(reverse('forgot_password'),{'otp':self.client.session['password_recovery']['code']})

    def test_name_accepts_letters_and_spaces_including_tamil(self):
        for name in ['Sibi Kumar','  Sibi   Kumar  ','அருண் குமார்']:
            form=DetailsForm({'name':name,'phone':'9876500196','pincode':'604408'})
            self.assertTrue(form.is_valid(),form.errors)
        for name in ['Sibi123','123456','Sibi@','Sibi 🙂']:
            form=DetailsForm({'name':name,'phone':'9876500196','pincode':'604408'})
            self.assertFalse(form.is_valid())
            self.assertIn('name',form.errors)

    def test_reset_and_sign_in_with_numeric_password(self):
        self.assertRedirects(self.begin(),reverse('forgot_password'))
        self.assertContains(self.client.get(reverse('forgot_password')),'Enter your OTP')
        self.assertRedirects(self.verify(),reverse('forgot_password'))
        self.assertNotIn('code',self.client.session['password_recovery'])
        self.assertRedirects(self.client.post(reverse('forgot_password'),{'password':'12345678','confirm_password':'12345678'}),reverse('login'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('12345678'))
        self.assertFalse(self.user.check_password('PreviousPassword!8'))
        self.assertNotIn('password_recovery',self.client.session)
        self.assertRedirects(self.client.post(reverse('login'),{'username':self.user.phone,'password':'12345678'}),reverse('dashboard'),fetch_redirect_response=False)

    def test_verification_matching_password_and_minimum_length_required(self):
        self.begin()
        self.client.post(reverse('forgot_password'),{'password':'12345678','confirm_password':'12345678'})
        self.user.refresh_from_db();self.assertTrue(self.user.check_password('PreviousPassword!8'))
        self.verify()
        self.assertContains(self.client.post(reverse('forgot_password'),{'password':'12345678','confirm_password':'different'}),'Passwords do not match')
        self.assertContains(self.client.post(reverse('forgot_password'),{'password':'123','confirm_password':'123'}),'Use at least 8 characters')

    def test_expiry_attempt_limit_and_session_binding(self):
        self.begin();code=self.client.session['password_recovery']['code']
        for _ in range(5):self.client.post(reverse('forgot_password'),{'otp':'000000'})
        self.assertNotIn('password_recovery',self.client.session)
        self.begin()
        session=self.client.session;pending=session['password_recovery'];pending['created']=time.time()-601;session['password_recovery']=pending;session.save()
        response=self.client.post(reverse('forgot_password'),{'otp':code})
        self.assertEqual(response.context['step'],'phone')
        self.client.logout()
        self.client.post(reverse('forgot_password'),{'otp':code})
        self.assertNotIn('password_recovery',self.client.session)
        self.user.refresh_from_db();self.assertTrue(self.user.check_password('PreviousPassword!8'))

    def test_resend_replaces_otp_and_is_rate_limited(self):
        self.begin();old_hash=self.client.session['password_recovery']['code_hash']
        self.client.post(reverse('forgot_password'),{'action':'resend'})
        self.assertNotEqual(self.client.session['password_recovery']['code_hash'],old_hash)
        self.client.post(reverse('forgot_password'),{'action':'resend'})
        response=self.client.post(reverse('forgot_password'),{'action':'resend'},follow=True)
        self.assertContains(response,'Too many OTP requests')

    def test_unknown_disabled_and_admin_accounts_cannot_use_displayed_otp(self):
        for phone in ['9876500198',self.admin.phone]:
            self.assertContains(self.client.post(reverse('forgot_password'),{'phone':phone}),'registered personal or shop')
            self.assertNotIn('password_recovery',self.client.session)
        self.user.is_active=False;self.user.save()
        self.assertContains(self.begin(),'registered personal or shop')
        self.assertNotIn('password_recovery',self.client.session)

    @override_settings(DEMO_PASSWORD_RESET_OTP=False)
    def test_displayed_otp_reset_requires_explicit_pilot_enablement(self):
        self.assertContains(self.begin(),'Password recovery is unavailable')
        self.assertNotIn('password_recovery',self.client.session)
