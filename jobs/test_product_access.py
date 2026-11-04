from django.test import TestCase,override_settings
from django.urls import reverse
from .models import CompanyProfile,Conversation,Message,Product,User,UserNotification
from .test_shop_catalog import image_file


@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.InMemoryStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ProductAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner=User.objects.create_user('allowance-owner',user_type='shop')
        cls.other=User.objects.create_user('allowance-other',user_type='shop')
        cls.admin=User.objects.create_user('allowance-admin',admin_role='super_admin')
        cls.shop=CompanyProfile.objects.create(user=cls.owner,company_name='Vandavasi Allowance Shop')
        cls.other_shop=CompanyProfile.objects.create(user=cls.other,company_name='Another Shop')

    def add(self,name='Product'):
        return self.client.post(reverse('product_add'),{'name':name,'price':'100','images':[image_file()],'is_active':'on'})

    def fill(self):
        for i in range(10):
            Product.objects.create(shop=self.shop,name=f'Existing {i}',price='100',image=image_file(f'fixture-{i}.png'),is_active=i!=0)

    def request_more(self):
        self.client.force_login(self.owner)
        return self.client.post(reverse('product_access_request'),{'requested_limit':'15','message':'Please allow more products for our local shop.'})

    def test_only_ten_free_products_can_be_added(self):
        self.client.force_login(self.owner)
        for i in range(10):self.assertEqual(self.add(str(i)).status_code,302)
        response=self.add('Eleventh product')
        self.assertEqual(response.status_code,403)
        self.assertContains(response,'Send request to Superadmin',status_code=403)
        self.assertEqual(self.shop.products.count(),10)
        self.assertContains(self.client.get(reverse('product_add')),'Your first 10 products are free')

    def test_hidden_products_count_but_edits_and_deletes_remain_available(self):
        self.fill();self.client.force_login(self.owner)
        self.assertEqual(self.add('Eleventh').status_code,403)
        product=self.shop.products.first()
        self.assertEqual(self.client.post(reverse('product_edit',args=[product.pk]),{'name':'Updated','price':'150'}).status_code,302)
        self.assertEqual(self.client.post(reverse('product_delete',args=[product.pk])).status_code,302)
        self.assertEqual(self.add('Replacement').status_code,302)
        self.assertEqual(self.shop.products.count(),10)

    def test_request_is_sent_to_superadmin_chat_and_is_not_duplicated(self):
        self.fill()
        response=self.request_more()
        self.assertEqual(response.status_code,302)
        self.shop.refresh_from_db()
        self.assertEqual((self.shop.product_limit,self.shop.requested_product_limit,self.shop.product_access_status),(10,15,'pending'))
        sent=Message.objects.get()
        self.assertEqual((sent.sender_id,sent.receiver_id),(self.owner.pk,self.admin.pk))
        self.assertIn('Requested total: 15',sent.content)
        self.assertTrue(UserNotification.objects.filter(user=self.admin,title='Shop requests more product slots').exists())
        self.request_more()
        self.assertEqual(Message.objects.count(),1)
        self.assertEqual(Conversation.objects.count(),1)

    def test_only_superadmin_can_assign_slots_and_approval_unlocks_creation(self):
        self.fill();self.request_more()
        url=reverse('product_access_assign',args=[self.shop.pk])
        self.assertEqual(self.client.post(url,{'decision':'approve','product_limit':'15'}).status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code,405)
        self.assertContains(self.client.get(reverse('product_access_requests')),self.shop.company_name)
        self.assertRedirects(self.client.post(url,{'decision':'approve','product_limit':'15','note':'You can now add your new range.'}),reverse('pilot_admin_shop',args=[self.shop.pk]))
        self.shop.refresh_from_db();self.other_shop.refresh_from_db()
        self.assertEqual((self.shop.product_limit,self.shop.product_access_status),(15,'approved'))
        self.assertEqual(self.other_shop.product_limit,10)
        self.assertTrue(Message.objects.filter(sender=self.admin,receiver=self.owner,content__contains='up to 15 products').exists())
        self.assertTrue(UserNotification.objects.filter(user=self.owner,title='More product slots approved').exists())
        self.client.force_login(self.owner)
        self.assertEqual(self.add('Eleventh approved product').status_code,302)
        self.assertContains(self.client.get(reverse('employer_dashboard')),'11 / 15 product slots used')

    def test_decline_preserves_limit_and_owner_can_request_again(self):
        self.fill();self.request_more();self.client.force_login(self.admin)
        url=reverse('product_access_assign',args=[self.shop.pk])
        self.assertEqual(self.client.post(url,{'decision':'decline'}).status_code,400)
        self.client.post(url,{'decision':'decline','note':'Please add more details.'})
        self.shop.refresh_from_db()
        self.assertEqual((self.shop.product_limit,self.shop.product_access_status),(10,'declined'))
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('product_access_request')),'Please add more details.')
        self.request_more();self.shop.refresh_from_db()
        self.assertEqual(self.shop.product_access_status,'pending')

    def test_invalid_assignment_cannot_reduce_existing_allowance(self):
        self.client.force_login(self.admin)
        for total in ['9','10','10001']:
            response=self.client.post(reverse('product_access_assign',args=[self.shop.pk]),{'decision':'approve','product_limit':total})
            self.assertEqual(response.status_code,400)
        self.shop.refresh_from_db();self.assertEqual(self.shop.product_limit,10)

    def test_shop_owner_cannot_modify_allowance_in_product_payload(self):
        self.fill();self.client.force_login(self.owner)
        response=self.client.post(reverse('product_add'),{'name':'Bypass','price':'10','product_limit':100,'images':[image_file()]})
        self.assertEqual(response.status_code,403)
        self.shop.refresh_from_db();self.assertEqual(self.shop.product_limit,10)
        self.assertEqual(self.client.get(reverse('product_access_requests')).status_code,403)

    def test_no_admin_does_not_leave_a_pending_request(self):
        self.admin.is_active=False;self.admin.save()
        self.assertContains(self.request_more(),'No Superadmin is available')
        self.shop.refresh_from_db();self.assertEqual(self.shop.product_access_status,'')
        self.assertFalse(Message.objects.exists())
