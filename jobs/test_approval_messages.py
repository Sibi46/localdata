from django.test import TestCase
from django.urls import reverse
from .models import (AdPackage,AdPost,AdRenewal,Advertisement,Advertiser,
    CompanyProfile,Conversation,Flick,FlickAdPayment,LocalOffer,Message,User,UserNotification)


class ApprovalMessageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin=User.objects.create_user('review-admin',admin_role='super_admin',is_staff=True)
        cls.owner=User.objects.create_user('review-owner',user_type='shop')
        cls.other=User.objects.create_user('review-other')
        cls.shop=CompanyProfile.objects.create(user=cls.owner,company_name='Review Shop')

    def setUp(self):
        self.client.force_login(self.admin)

    def assert_delivery(self,text,count=1):
        sent=Message.objects.filter(sender=self.admin,receiver=self.owner)
        self.assertEqual(sent.count(),count)
        self.assertIn(text,sent.latest('pk').content)
        self.assertEqual(UserNotification.objects.filter(user=self.owner).count(),count)
        self.assertFalse(Message.objects.filter(receiver=self.other).exists())
        self.assertFalse(UserNotification.objects.filter(user=self.other).exists())
        notification=UserNotification.objects.filter(user=self.owner).latest('pk')
        self.assertTrue(notification.link.startswith('/'))
        from django.urls import resolve
        resolve(notification.link.split('#')[0])

    def offer(self):
        return LocalOffer.objects.create(owner=self.owner,business_name='Review Shop',title='Weekend discount',discount_text='10% OFF',is_active=False)

    def test_offer_approval_sends_one_private_message_and_notification(self):
        offer=self.offer()
        for _ in range(2):
            response=self.client.post(reverse('manage_offers'),{'action':'approve','pk':offer.pk})
            self.assertEqual(response.status_code,302)
        offer.refresh_from_db();self.assertTrue(offer.is_active)
        self.assert_delivery('Weekend discount')
        self.client.post(reverse('manage_offers'),{'action':'deactivate','pk':offer.pk})
        offer.refresh_from_db();self.assertFalse(offer.is_active)
        self.assert_delivery('Weekend discount')

    def test_direct_offer_approval_requires_post_and_handles_ownerless_offers(self):
        offer=self.offer();url=reverse('offer_approve',args=[offer.pk])
        self.assertEqual(self.client.get(url).status_code,405)
        self.client.post(url);self.client.post(url)
        self.assert_delivery('Weekend discount')
        offer=LocalOffer.objects.create(business_name='Legacy',title='Ownerless',is_active=False)
        self.assertEqual(self.client.post(reverse('offer_approve',args=[offer.pk])).status_code,302)
        self.assert_delivery('Weekend discount')

    def test_shop_owner_cannot_approve_or_send_an_admin_message(self):
        offer=self.offer();self.client.force_login(self.owner)
        self.client.post(reverse('manage_offers'),{'action':'approve','pk':offer.pk})
        self.client.post(reverse('offer_approve',args=[offer.pk]))
        offer.refresh_from_db();self.assertFalse(offer.is_active)
        self.assertFalse(Message.objects.exists())

    def ad(self):
        return AdPost.objects.create(user=self.owner,company_name='Review Shop',title='New collection',image='ad_posts/test.png',status='pending')

    def test_ad_review_sends_message_once(self):
        ad=self.ad();url=reverse('pilot_admin_ad',args=[ad.pk])
        for _ in range(2):self.client.post(url,{'decision':'approve'})
        self.assert_delivery('New collection')

    def test_ad_feedback_is_also_sent_in_messages(self):
        ad=self.ad()
        self.client.post(reverse('pilot_admin_ad',args=[ad.pk]),{'decision':'reject','note':'Please upload a clearer image.'})
        self.assert_delivery('Please upload a clearer image.')

    def test_legacy_ad_approval_and_renewal_notify_once(self):
        ad=self.ad()
        for _ in range(2):self.client.post(reverse('admin_ad_posts'),{'action':'approve','ad_id':ad.pk})
        self.assert_delivery('Review Shop')
        renewal=AdRenewal.objects.create(ad=ad,amount=100,transaction_id='test',screenshot='test.png')
        for _ in range(2):self.client.post(reverse('admin_ad_posts'),{'action':'approve_renewal','renewal_id':renewal.pk})
        self.assert_delivery('renewal',count=2)

    def test_advertiser_and_banner_approval_send_messages(self):
        advertiser=Advertiser.objects.create(user=self.owner,business_name='Review Shop')
        for _ in range(2):self.client.post(reverse('admin_approve_advertiser',args=[advertiser.pk]))
        self.assert_delivery('advertiser account')
        package=AdPackage.objects.create(name='Banner',ad_type='homepage_banner',price=100)
        ad=Advertisement.objects.create(advertiser=advertiser,package=package,title='Our shop banner')
        for _ in range(2):self.client.post(reverse('admin_activate_ad',args=[ad.pk]))
        self.assert_delivery('Our shop banner',count=2)

    def test_video_promotion_approval_notifies_once(self):
        flick=Flick.objects.create(user=self.owner,title='Shop video')
        payment=FlickAdPayment.objects.create(user=self.owner,flick=flick,amount=100)
        for _ in range(2):self.client.post(reverse('admin_flicks'),{'action':'approve_payment','payment_id':payment.pk})
        self.assert_delivery('video promotion')

    def test_product_access_message_still_reaches_owner(self):
        self.client.post(reverse('product_access_assign',args=[self.shop.pk]),{'decision':'approve','product_limit':'15'})
        self.assert_delivery('15 products')

    def test_workspace_approvals_send_owner_messages_once(self):
        ad=self.ad();offer=self.offer()
        for _ in range(2):
            self.client.post(reverse('assigned_action',args=['ads',ad.pk]),{'action':'approve'})
            self.client.post(reverse('assigned_action',args=['offers',offer.pk]),{'action':'activate'})
        self.assert_delivery('Weekend discount',count=2)

    def test_bulk_admin_actions_also_send_owner_messages_once(self):
        from unittest.mock import patch
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from .admin import AdvertiserAdmin,AdvertisementAdmin
        request=RequestFactory().post('/admin/');request.user=self.admin
        advertiser=Advertiser.objects.create(user=self.owner,business_name='Review Shop')
        panel=AdvertiserAdmin(Advertiser,AdminSite())
        with patch.object(panel,'message_user'):
            for _ in range(2):panel.approve_advertisers(request,Advertiser.objects.filter(pk=advertiser.pk))
        self.assert_delivery('advertiser account')
        package=AdPackage.objects.create(name='Banner',ad_type='homepage_banner',price=100)
        ad=Advertisement.objects.create(advertiser=advertiser,package=package,title='Bulk shop banner',status='pending_review')
        panel=AdvertisementAdmin(Advertisement,AdminSite())
        with patch.object(panel,'message_user'):
            for _ in range(2):panel.activate_ads(request,Advertisement.objects.filter(pk=ad.pk))
        self.assert_delivery('Bulk shop banner',count=2)

    def test_failed_message_rolls_back_approval(self):
        from unittest.mock import patch
        offer=self.offer()
        with patch('jobs.admin_messages.Message.objects.create',side_effect=RuntimeError('Test failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('offer_approve',args=[offer.pk]))
        offer.refresh_from_db();self.assertFalse(offer.is_active)
        self.assertFalse(UserNotification.objects.filter(user=self.owner).exists())
