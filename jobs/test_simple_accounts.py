import time
from django.test import TestCase, override_settings
from .models import User, CompanyProfile, ShopProfile


@override_settings(DEMO_SIGNUP_OTP=True, DEBUG=True)
class SimpleAccountTests(TestCase):
    def details(self, **extra):
        return self.client.post('/register/', {'name': 'Sample Person', 'phone': '9876543290', 'pincode':'604408','city':'Vandavasi', **extra})

    def verify(self):
        return self.client.post('/register/', {'otp': self.client.session['simple_signup']['code']})

    def finish(self):
        return self.client.post('/register/', {'password': 'NiceLocalPassword!81', 'confirm_password': 'NiceLocalPassword!81'})

    def test_signup_login_and_optional_shop(self):
        self.assertRedirects(self.details(), '/register/')
        self.assertEqual(User.objects.count(), 0)
        self.assertContains(self.client.get('/register/'), 'Enter the OTP shown below')
        self.assertRedirects(self.verify(), '/register/')
        self.assertEqual(User.objects.count(), 0)
        self.assertRedirects(self.finish(), '/account/')
        user = User.objects.get()
        self.assertEqual((user.first_name, user.user_type), ('Sample Person', 'individual'))
        self.assertFalse(CompanyProfile.objects.exists())
        self.assertNotIn('simple_signup', self.client.session)
        self.client.logout()
        self.assertRedirects(self.client.post('/login/', {'username': user.phone, 'password': 'NiceLocalPassword!81'}), '/dashboard/', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/dashboard/'), '/account/')
        response = self.client.post('/business/create/', {'account_type': 'shop', 'name': 'My Store', 'pincode': '600001', 'city': 'Chennai'})
        self.assertRedirects(response, '/employer/dashboard/')
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(CompanyProfile.objects.get().user_id, user.pk)
        self.assertEqual(ShopProfile.objects.get().user_id, user.pk)
        self.assertEqual(self.client.session['_auth_user_id'], str(user.pk))
        self.assertRedirects(self.client.get('/business/create/'), '/employer/dashboard/')

    def test_wrong_code_limit_expiry_and_session_binding(self):
        self.details()
        correct = self.client.session['simple_signup']['code']
        wrong = '000000'
        for _ in range(5):
            self.assertContains(self.client.post('/register/', {'otp': wrong}), 'That code is incorrect')
        self.client.post('/register/', {'otp': wrong})
        self.assertNotIn('simple_signup', self.client.session)
        self.details()
        session = self.client.session
        pending = session['simple_signup']
        pending['created'] = time.time() - 601
        session['simple_signup'] = pending
        session.save()
        response = self.client.post('/register/', {'otp': correct})
        self.assertEqual(response.context['step'], 'details')
        self.assertEqual(User.objects.count(), 0)
        self.client.logout()
        self.client.post('/register/', {'otp': correct})
        self.assertEqual(User.objects.count(), 0)

    def test_password_requires_verified_otp_and_matching_password(self):
        self.details()
        self.finish()
        self.assertEqual(User.objects.count(), 0)
        self.verify()
        self.assertContains(self.client.post('/register/', {'password': 'NiceLocalPassword!81', 'confirm_password': 'different'}), 'Passwords do not match')
        self.assertContains(self.client.post('/register/', {'password': 'abc', 'confirm_password': 'abc'}), 'Use at least 8 characters')
        self.assertFalse(User.objects.exists())

    def test_duplicate_phone_and_invalid_phone(self):
        self.assertContains(self.details(phone='123'), 'valid 10-digit')
        User.objects.create_user('existing', phone='9876543290')
        self.assertContains(self.details(), 'already registered')

    def test_numeric_password_signup_and_login(self):
        self.details()
        response = self.client.get('/register/')
        self.assertContains(response, 'Enter your OTP')
        self.assertNotContains(response, 'Demo OTP')
        self.assertNotContains(response, 'demo code')
        self.verify()
        self.assertRedirects(self.client.post('/register/', {
            'password': '12345678', 'confirm_password': '12345678',
        }), '/account/')
        user = User.objects.get()
        self.assertTrue(user.check_password('12345678'))
        self.assertNotEqual(user.password, '12345678')
        self.client.logout()
        self.assertRedirects(self.client.post('/login/', {
            'username': user.phone, 'password': '12345678',
        }), '/dashboard/', fetch_redirect_response=False)

    def test_business_intent_still_creates_personal_account_first(self):
        self.client.get('/register/?type=company')
        self.details()
        self.verify()
        self.assertRedirects(self.finish(), '/business/create/?type=company')
        self.assertFalse(CompanyProfile.objects.exists())
        self.assertEqual(User.objects.get().user_type, 'individual')

    def test_business_requires_login_and_valid_details(self):
        self.assertEqual(self.client.post('/business/create/', {}).status_code, 302)
        owner = User.objects.create_user('personal', user_type='individual')
        self.client.force_login(owner)
        self.assertContains(self.client.post('/business/create/', {'account_type': 'company', 'name': 'Office', 'pincode': '123', 'city': 'Town'}), 'errorlist')
        self.assertFalse(CompanyProfile.objects.exists())

    def test_inactive_user_cannot_sign_in(self):
        user = User.objects.create_user('disabled', phone='9876543290', password='Password!99', is_active=False)
        self.client.post('/login/', {'username': user.phone, 'password': 'Password!99'})
        self.assertNotIn('_auth_user_id', self.client.session)

    @override_settings(DEMO_SIGNUP_OTP=False)
    def test_demo_is_disabled_when_not_configured(self):
        self.assertContains(self.details(), 'Registration is unavailable')
        self.assertNotIn('simple_signup', self.client.session)
