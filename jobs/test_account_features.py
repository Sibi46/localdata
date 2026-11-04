from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import BusinessFollow, BusinessReview, CompanyProfile, User


class AccountFeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('local-owner', user_type='company', pincode='600073', city='Chennai', address='Market Road')
        cls.company = CompanyProfile.objects.create(user=cls.owner, company_name='Local Store', industry='Retail', company_size='1-10')
        cls.customer = User.objects.create_user('resident', user_type='individual', pincode='600073')
        cls.other = User.objects.create_user('other-owner', user_type='shop', pincode='600001')
        cls.other_company = CompanyProfile.objects.create(user=cls.other, company_name='Other Store')

    def login(self, user=None):
        self.client.force_login(user or self.customer, backend='django.contrib.auth.backends.ModelBackend')

    def test_business_profile_editor_is_inside_dashboard(self):
        self.login(self.owner)
        self.assertRedirects(self.client.get('/profile/edit/'), '/employer/dashboard/#my-profile', fetch_redirect_response=False)
        response = self.client.get('/employer/dashboard/')
        self.assertContains(response, 'class="shop-form profile-shop-form"')
        for field in ['first_name', 'last_name', 'email', 'photo', 'company_name', 'logo', 'banner_image', 'preferred_pincode_1', 'preferred_pincode_2']:
            self.assertContains(response, 'name="' + field + '"')
        self.assertContains(response, 'data-dashboard-link')
        saved = self.client.post('/employer/dashboard/', {'dashboard_profile':'1', 'first_name':'Dashboard owner', 'company_name': self.company.company_name})
        self.assertRedirects(saved, '/employer/dashboard/#my-profile', fetch_redirect_response=False)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.first_name, 'Dashboard owner')

    def test_profile_is_full_account_hub_for_personal_and_business_users(self):
        for user in (self.customer, self.owner):
            self.login(user)
            response = self.client.get('/profile/edit/', follow=True)
            self.assertContains(response, 'Your profile &amp; shop details' if user == self.owner else 'My profile')
            self.assertContains(response, '/messages/')
            self.assertContains(response, 'preferred_pincode_1')
            self.assertContains(response, 'preferred_pincode_2')
            self.assertEqual('business_form' in response.context and response.context['business_form'] is not None, user == self.owner)
        self.assertContains(response, 'name="logo"')
        self.assertContains(response, 'name="banner_image"')
        self.assertContains(response, 'name="description"')

    def test_profile_saves_business_details_to_same_dashboard_model(self):
        self.login(self.owner)
        response = self.client.post('/profile/edit/', {'company_name': 'Renamed Local Store', 'description': 'Fresh produce and groceries.',
            'industry': 'Groceries', 'company_size': '2-10', 'website': 'https://example.com', 'business_phone': '9000000000',
            'pincode': '600073', 'preferred_pincode_1': '600001', 'preferred_pincode_2': '600002'})
        self.assertRedirects(response, '/employer/dashboard/#my-profile', fetch_redirect_response=False)
        self.company.refresh_from_db()
        self.owner.refresh_from_db()
        self.assertEqual(self.company.company_name, 'Renamed Local Store')
        self.assertEqual(self.company.description, 'Fresh produce and groceries.')
        self.assertEqual(self.owner.business_phone, '9000000000')
        dashboard = self.client.get('/employer/dashboard/')
        self.assertContains(dashboard, 'Renamed Local Store')
        self.assertContains(dashboard, 'href="#my-profile" data-dashboard-link')
        self.assertEqual(dashboard.context['company'].website, 'https://example.com')

    def test_invalid_settings_are_rejected_before_any_user_or_business_changes(self):
        self.login(self.owner)
        for changes in [
            {'preferred_pincode_1':'600073'},
            {'preferred_pincode_1':'600001', 'preferred_pincode_2':'600001'},
            {'preferred_pincode_1':'12345'}, {'preferred_pincode_1':'000001'},
            {'website':'javascript:bad'}, {'business_phone':'12'}]:
            response = self.client.post('/profile/edit/', {'first_name':'Must not save', 'company_name':'Must not save', **changes})
            self.assertEqual(response.status_code, 400, changes)
            self.owner.refresh_from_db(); self.company.refresh_from_db()
            self.assertEqual(self.owner.first_name, '')
            self.assertEqual(self.company.company_name, 'Local Store')

    def test_preferences_save_clear_and_remain_private(self):
        self.login()
        response = self.client.post('/profile/edit/', {'pincode':'600073', 'preferred_pincode_1':'600001', 'preferred_pincode_2':'600002'})
        self.assertEqual(response.status_code,302)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.preferred_pincode_2,'600002')
        self.assertEqual(self.customer.pincode,'600073')
        self.assertContains(self.client.get('/'), '600002')
        self.client.post('/profile/edit/', {'preferred_pincode_1':'', 'preferred_pincode_2':''})
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.preferred_pincode_1,'')
        self.assertEqual(self.customer.preferred_pincode_2,'')
        self.login(self.owner)
        self.client.post('/profile/edit/', {'preferred_pincode_1':'600005','preferred_pincode_2':'600006'})
        self.login(self.other)
        self.assertNotContains(self.client.get(self.company.get_absolute_url()), '600005')
        self.assertNotContains(self.client.get(self.company.get_absolute_url()), '600006')

    def test_customer_cannot_edit_a_different_business(self):
        self.login()
        self.client.post('/profile/edit/', {'company_id':self.company.company_id,'company_name':'Stolen','description':'Hijacked'})
        self.company.refresh_from_db()
        self.assertEqual(self.company.company_name,'Local Store')

    @override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.InMemoryStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
    def test_company_logo_and_banner_upload_through_profile(self):
        def photo(name):
            image = BytesIO(); Image.new('RGB',(4,4),'blue').save(image,format='PNG')
            return SimpleUploadedFile(name,image.getvalue(),content_type='image/png')
        self.login(self.owner)
        response = self.client.post('/profile/edit/', {'company_name': self.company.company_name, 'logo':photo('logo.png'),'banner_image':photo('banner.png')})
        self.assertEqual(response.status_code,302)
        self.company.refresh_from_db()
        self.assertTrue(self.company.logo)
        self.assertTrue(self.company.banner_image)

    def test_member_area_choice_is_shared_and_guest_discovery_requires_registration(self):
        # Guests see home; protected discovery/area actions require an account.
        self.assertRedirects(self.client.get('/businesses/'), '/register/?next=%2Fbusinesses%2F', fetch_redirect_response=False)
        self.login()
        response = self.client.post('/area/select/', {'pincode':'600001','next':'/businesses/'})
        self.assertRedirects(response,'/businesses/',fetch_redirect_response=False)
        self.assertEqual(self.client.session['active_pincode'],'600001')
        self.assertEqual(self.client.session['news_pincode'],'600001')
        response = self.client.get('/businesses/')
        self.assertContains(response,'Other Store')
        self.assertNotContains(response,'Local Store')
        self.assertEqual(self.client.get('/advertise/').context['pincode'],'600001')
        self.assertEqual(self.client.get('/products/').context['active_area'],'600001')

    def test_area_switch_does_not_overwrite_primary_or_preferred_locations(self):
        self.login()
        self.client.post('/area/select/',{'pincode':'600001','next':'/'})
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.pincode,'600073')
        self.assertEqual(self.client.get('/').context['active_area'],'600001')
        self.assertEqual(self.client.get('/businesses/').context['pincode'],'600001')
        self.assertEqual(self.client.get('/businesses/?pincode=600073').context['pincode'],'600073')
        self.assertEqual(self.client.get('/businesses/?pincode=').context['pincode'],'')

    def test_invalid_pins_and_external_returns_are_rejected(self):
        self.login()
        self.client.post('/area/select/',{'pincode':'600073'})
        self.client.post('/area/select/',{'pincode':'bad','next':'//evil.example/'})
        self.assertEqual(self.client.session['active_pincode'],'600073')
        response = self.client.post('/area/select/',{'pincode':'600001','next':'//evil.example/'})
        self.assertEqual(response.url,'/')
        self.login()
        response = self.client.post('/profile/edit/',{'next':'//evil.example/'})
        self.assertEqual(response.url,'/profile/edit/')

    def test_follow_is_authenticated_idempotent_and_reversible(self):
        url=reverse('business_follow',args=[self.company.company_id])
        self.assertEqual(self.client.post(url,{'action':'follow'}).status_code,302)
        self.assertFalse(BusinessFollow.objects.exists())
        self.login()
        self.assertEqual(self.client.get(url).status_code,405)
        for _ in range(2):
            data=self.client.post(url,{'action':'follow'},HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()
            self.assertTrue(data['following']); self.assertEqual(data['followers'],1)
        self.assertEqual(BusinessFollow.objects.count(),1)
        self.assertContains(self.client.get(self.company.get_absolute_url()), 'Following')
        for _ in range(2):
            self.client.post(url,{'action':'unfollow'})
        self.assertFalse(BusinessFollow.objects.exists())

    def test_self_follow_inactive_business_and_csrf_protection(self):
        url=reverse('business_follow',args=[self.company.company_id])
        self.login(self.owner)
        self.assertEqual(self.client.post(url,{'action':'follow'}).status_code,400)
        self.login()
        self.assertEqual(self.client.post(url,{'action':'bad'}).status_code,400)
        csrf_client=Client(enforce_csrf_checks=True); csrf_client.force_login(self.customer)
        self.assertEqual(csrf_client.post(url,{'action':'follow'}).status_code,403)
        self.owner.is_active=False; self.owner.save(update_fields=['is_active'])
        self.assertEqual(self.client.post(url,{'action':'follow'}).status_code,404)

    def test_following_list_is_private_and_reviews_are_not_double_counted(self):
        BusinessFollow.objects.create(company=self.company,user=self.customer)
        BusinessFollow.objects.create(company=self.company,user=self.other)
        BusinessReview.objects.create(company=self.company,user=self.customer,rating=4,text='Friendly store staff.')
        self.login()
        response=self.client.get('/businesses/?following=1&pincode=')
        self.assertEqual(response.context['businesses'].paginator.count,1)
        self.assertEqual(response.context['businesses'][0].review_count,1)
        self.assertContains(self.client.get('/profile/edit/'), '<strong>1</strong> Following',html=True)
        self.login(self.owner)
        self.assertEqual(self.client.get('/businesses/?following=1&pincode=').context['businesses'].paginator.count,0)

    def test_primary_headers_include_brand_and_account_access(self):
        from html.parser import HTMLParser
        class HeaderParser(HTMLParser):
            def __init__(self): super().__init__(); self.depth=0; self.links=[]; self.headers=0
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag == 'header':
                    if self.depth:
                        self.depth += 1
                    elif attrs.get('class') in ('account-header', 'site-header'):
                        self.depth = 1
                        self.headers += 1
                if self.depth and tag=='a': self.links.append(attrs.get('href'))
            def handle_endtag(self,tag):
                if tag=='header' and self.depth: self.depth -= 1
        self.login()
        for url in ['/', '/businesses/', self.company.get_absolute_url()]:
            response=self.client.get(url,follow=True)
            self.assertEqual(response.status_code,200,url)
            parser=HeaderParser(); parser.feed(response.content.decode())
            self.assertEqual(parser.headers,1,url)
            self.assertEqual(parser.links[0], '/', url)
            self.assertTrue(any(link in parser.links for link in ('/profile/edit/', '/account/', '/dashboard/')), url)
