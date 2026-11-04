from django.test import TestCase,override_settings
from django.urls import reverse
from .models import AdPost,CompanyProfile,Country,District,PinCode,Product,ShopProfile,State,User


@override_settings(DEMO_SIGNUP_OTP=True, DEBUG=True)
class OnboardingTests(TestCase):
    @staticmethod
    def home_header(response):
        from html.parser import HTMLParser

        class HeaderParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth, self.parts = 0, []

            def handle_starttag(self, tag, attrs):
                if tag == 'header':
                    if self.depth:
                        self.depth += 1
                    elif dict(attrs).get('class') == 'site-header':
                        self.depth = 1
                if self.depth:
                    self.parts.append(self.get_starttag_text())

            def handle_endtag(self, tag):
                if self.depth:
                    self.parts.append(f'</{tag}>')
                    if tag == 'header':
                        self.depth -= 1

            def handle_data(self, data):
                if self.depth:
                    self.parts.append(data)

        parser = HeaderParser()
        parser.feed(response.content.decode())
        return ''.join(parser.parts)

    @classmethod
    def setUpTestData(cls):
        country,_=Country.objects.get_or_create(code='IN',defaults={'name':'India'})
        state=State.objects.create(name='Test Tamil Nadu',code='TN',country=country)
        district=District.objects.create(name='Test Tiruvannamalai',state=state)
        PinCode.objects.create(code='604408',area_name='Vandavasi',district=district)
        cls.user=User.objects.create_user('onboarding-user',first_name='Sandra',phone='9876503388',pincode='604408',city='Vandavasi',user_type='individual')
        cls.other=User.objects.create_user('onboarding-other')

    def test_visitors_see_home_and_must_register_before_browsing(self):
        response=self.client.get('/')
        self.assertTemplateUsed(response,'index.html')
        self.assertContains(response,'Discover local products')
        self.assertContains(response,'js/home-registration.js')
        for url in ['/products/','/businesses/','/news/','/flicks/','/advertise/','/advertise/register/','/messages/']:
            response=self.client.get(url)
            self.assertEqual(response.status_code,302)
            self.assertTrue(response.url.startswith('/register/?next='),response.url)
        for url in ['/register/','/login/','/forgot-password/','/super-admin/login/']:
            self.assertEqual(self.client.get(url).status_code,200)
        response=self.client.get('/register/')
        self.assertContains(response,'data-account-pincode')
        self.assertContains(response,'data-account-city')
        self.assertContains(response,'js/account-location.js')

    def test_guest_home_shows_create_account_and_no_flicks_navigation(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        header = self.home_header(response)
        self.assertIn('href="/register/"', header)
        self.assertIn('Create account', header)
        self.assertNotIn('href="/login/"', header)
        self.assertNotIn('aria-label="My account"', header)
        self.assertNotIn('href="/flicks/"', html)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_member_home_replaces_create_account_with_profile_icon(self):
        self.client.force_login(self.user)
        response = self.client.get('/')
        html = response.content.decode()
        header = self.home_header(response)
        self.assertIn('href="/account/"', header)
        self.assertIn('aria-label="My account"', header)
        self.assertIn('<svg', header)
        self.assertNotIn('Create account', header)
        self.assertNotIn('href="/flicks/"', html)

    def test_shared_and_shop_headers_distinguish_guest_and_member(self):
        from django.contrib.auth.models import AnonymousUser
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        for template in ('includes/account_header.html', 'shop/header.html'):
            with self.subTest(template=template):
                request.user = AnonymousUser()
                html = render_to_string(template, {'request': request})
                self.assertIn('href="/register/"', html)
                self.assertIn('Create account', html)
                self.assertNotIn('class="account-profile-icon"', html)
                request.user = self.user
                html = render_to_string(template, {'request': request})
                self.assertNotIn('Create account', html)
                self.assertIn('<svg', html)

    def test_signup_collects_location_and_shows_shop_registration(self):
        response=self.client.post('/register/',{'name':'New Member','phone':'9876503399','pincode':'604408','city':'Vandavasi'})
        self.assertEqual(response.status_code,302)
        code=self.client.session['simple_signup']['code']
        self.client.post('/register/',{'otp':code})
        self.client.post('/register/',{'password':'12345678','confirm_password':'12345678'})
        user=User.objects.get(phone='9876503399')
        self.assertEqual((user.pincode,user.city),('604408','Vandavasi'))
        response=self.client.get('/account/')
        for text in ['New Member','9876503399','604408','Vandavasi','Register your shop']:
            self.assertContains(response,text)

    def test_shop_owner_identity_is_prefilled_and_cannot_be_replaced(self):
        self.client.force_login(self.user)
        form=self.client.get(reverse('business_create')).context['form']
        self.assertEqual(form['owner_name'].value(),'Sandra')
        self.assertEqual(form['phone'].value(),self.user.phone)
        self.assertTrue(form.fields['phone'].disabled)
        self.client.post(reverse('business_create'),{'account_type':'shop','owner_name':'Forged Owner','phone':'9999999999','name':'Sandra Store','pincode':'604408','city':'Vandavasi'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone,'9876503388')
        self.assertEqual(ShopProfile.objects.get(user=self.user).owner_name,'Sandra')
        self.assertContains(self.client.get('/account/'),'Sandra Store')

    def test_my_ads_are_limited_to_the_signed_in_user(self):
        AdPost.objects.create(user=self.user,company_name='My Shop',title='My local ad',description='Own application',image='ad_posts/test.png')
        AdPost.objects.create(user=self.other,company_name='Other Shop',title='Other private ad',description='Not mine',image='ad_posts/other.png')
        self.client.force_login(self.user)
        response=self.client.get('/account/')
        self.assertContains(response,'My local ad')
        self.assertNotContains(response,'Other private ad')

    def test_pincode_lookup_and_home_area_label(self):
        data=self.client.get('/api/pincode/604408/').json()
        self.assertTrue(data['success']);self.assertEqual(data['city'],'Vandavasi')
        self.client.force_login(self.user)
        shop=CompanyProfile.objects.create(user=self.user,company_name='Home Test Shop')
        Product.objects.create(shop=shop,name='A local product',image='products/test.png',price='99')
        response=self.client.get('/')
        self.assertNotContains(response,'js/home-registration.js')
        for text in ['Hello, Sandra','A local product']:
            self.assertContains(response,text)
        self.assertEqual(self.client.get('/products/').status_code,200)

    def test_account_area_can_be_updated(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post('/account/',{'pincode':'604408','city':'Vandavasi'}),'/account/')
        self.assertEqual(self.client.session['active_pincode'],'604408')
