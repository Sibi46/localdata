import tempfile
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import AdPost, User, UserNotification
from .test_shop_catalog import image_file


class AdApplicationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner=User.objects.create_user('ad-owner',first_name='Ad Owner',phone='9876543201',user_type='individual')
        cls.other=User.objects.create_user('other-ad-owner',phone='9876543202')
        cls.admin=User.objects.create_user('ad-reviewer',phone='9876543203',admin_role='super_admin')

    def setUp(self):
        files=tempfile.TemporaryDirectory(dir=Path(settings.BASE_DIR)/'.local-data')
        self.addCleanup(files.cleanup)
        media=override_settings(MEDIA_ROOT=files.name)
        media.enable()
        self.addCleanup(media.disable)

    def data(self,**extra):
        return {'ad_type':'product','company_name':'Pilot Ads Store','title':'Cotton bags for our town','description':'Unique pilot promotion description.','image':image_file('creative.png'),'contact_name':'Shop Owner','contact_phone':'9876543201','pincode':'604408','website':'https://example.com','requested_days':'14',**extra}

    def submit(self,**extra):
        self.client.force_login(self.owner)
        return self.client.post(reverse('advertiser_register'),self.data(**extra))

    def test_public_intro_and_personal_account_can_apply(self):
        self.assertEqual(self.client.get(reverse('advertiser_register')).status_code,302)
        self.assertRedirects(self.client.post(reverse('advertiser_register'),{}),'/register/?next=%2Fadvertise%2Fregister%2F')
        self.assertRedirects(self.submit(status='approved',user=self.other.pk),reverse('ad_applications'))
        ad=AdPost.objects.get()
        self.assertEqual((ad.user_id,ad.status,ad.ad_type,ad.requested_days),(self.owner.pk,'pending','product',14))
        self.assertTrue(ad.image)
        self.assertTrue(UserNotification.objects.filter(user=self.admin,link=reverse('pilot_admin_ad',args=[ad.pk])).exists())
        self.assertIsNone(ad.approved_at)
        self.assertNotContains(self.client.get('/'),'Unique pilot promotion description.')
        self.assertEqual(self.client.get(reverse('sponsored_post_detail',args=[ad.pk])).status_code,404)

    def test_invalid_contact_type_duration_and_image_are_rejected(self):
        self.client.force_login(self.owner)
        for changes in [{'ad_type':'invented'},{'requested_days':'999'},{'contact_phone':'123'},{'pincode':'123'}, {'image':SimpleUploadedFile('fake.png',b'not an image',content_type='image/png')}]:
            response=self.client.post(reverse('advertiser_register'),self.data(**changes))
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.context['form'].errors)
            self.assertFalse(AdPost.objects.exists())

    def test_owner_status_and_edit_are_private(self):
        self.submit()
        ad=AdPost.objects.get()
        self.assertContains(self.client.get(reverse('ad_applications')),ad.title)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('ad_applications')),ad.title)
        ad.status='rejected';ad.save()
        self.assertEqual(self.client.get(reverse('ad_application_edit',args=[ad.pk])).status_code,404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('ad_application_edit',args=[ad.pk])).status_code,200)

    def test_superadmin_approval_publishes_for_requested_duration(self):
        self.submit()
        ad=AdPost.objects.get()
        urls=[reverse('pilot_admin_ads'),reverse('pilot_admin_ad',args=[ad.pk])]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code,403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(urls[0],{'status':'pending','q':'Cotton'}),ad.title)
        self.assertContains(self.client.get(urls[1]),ad.contact_phone)
        self.assertRedirects(self.client.post(urls[1],{'decision':'approve'}),urls[1])
        ad.refresh_from_db()
        self.assertEqual(ad.status,'approved')
        self.assertEqual(ad.expires_at,timezone.localdate()+timedelta(days=13))
        self.assertIsNotNone(ad.approved_at)
        self.assertTrue(UserNotification.objects.filter(user=self.owner,title='Your ad is approved').exists())
        self.client.force_login(self.other)
        self.assertContains(self.client.get('/'),'Unique pilot promotion description.')
        self.assertEqual(self.client.get(reverse('sponsored_post_detail',args=[ad.pk])).status_code,200)

    def test_rejection_requires_feedback_then_owner_can_resubmit(self):
        self.submit()
        ad=AdPost.objects.get()
        url=reverse('pilot_admin_ad',args=[ad.pk])
        self.client.force_login(self.admin)
        self.assertContains(self.client.post(url,{'decision':'reject'}),'Add a reason')
        ad.refresh_from_db();self.assertEqual(ad.status,'pending')
        self.client.post(url,{'decision':'reject','note':'Please improve the image.'})
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('ad_applications')),'Please improve the image.')
        self.client.post(reverse('ad_application_edit',args=[ad.pk]),self.data(title='Updated cotton bags'))
        ad.refresh_from_db()
        self.assertEqual((ad.status,ad.reject_note,ad.title),('pending','','Updated cotton bags'))

    def test_review_cannot_change_an_already_reviewed_application(self):
        self.submit()
        ad=AdPost.objects.get()
        url=reverse('pilot_admin_ad',args=[ad.pk])
        self.client.force_login(self.admin)
        self.client.post(url,{'decision':'approve'})
        self.client.post(url,{'decision':'reject','note':'Late review'})
        ad.refresh_from_db()
        self.assertEqual(ad.status,'approved')
