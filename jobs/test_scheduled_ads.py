from datetime import timedelta
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from .models import AdPost
from . import test_ad_applications as applications
from .test_shop_catalog import image_file


class ScheduledAdTests(TestCase):
    setUpTestData = classmethod(applications.AdApplicationTests.setUpTestData.__func__)
    setUp = applications.AdApplicationTests.setUp
    data = applications.AdApplicationTests.data
    submit = applications.AdApplicationTests.submit

    def application(self):
        self.submit()
        ad=AdPost.objects.get()
        self.client.force_login(self.admin)
        return ad, reverse('pilot_admin_ad',args=[ad.pk])

    def test_admin_design_and_dates_preserve_applicant_upload(self):
        ad,url=self.application()
        original=ad.image.name
        today=timezone.localdate()
        self.client.post(url,{'decision':'approve','creative_image':image_file('designed.png'),'starts_at':str(today),'ends_at':str(today+timedelta(days=3))})
        ad.refresh_from_db()
        self.assertEqual(ad.status,'approved')
        self.assertEqual(ad.image.name,original)
        self.assertTrue(ad.creative_image)
        self.assertEqual(ad.display_image,ad.creative_image)
        self.assertEqual(ad.starts_at,today)
        self.assertTrue(ad.is_live)
        response=self.client.get('/')
        self.assertContains(response,'data-scheduled-slide')
        self.assertContains(response,ad.creative_image.url)
        self.assertEqual(self.client.get(reverse('sponsored_post_detail',args=[ad.pk])).status_code,200)

    def test_future_and_expired_ads_are_not_public_or_measured(self):
        ad,url=self.application()
        today=timezone.localdate()
        self.client.post(url,{'decision':'approve','creative_image':image_file(),'starts_at':str(today+timedelta(days=1)),'ends_at':str(today+timedelta(days=5))})
        ad.refresh_from_db();self.assertTrue(ad.is_scheduled);self.assertFalse(ad.is_live)
        self.assertNotContains(self.client.get('/'),'data-scheduled-slide')
        self.assertEqual(self.client.get(reverse('sponsored_post_detail',args=[ad.pk])).status_code,404)
        self.client.get(reverse('adpost_click_track',args=[ad.pk]))
        ad.refresh_from_db();self.assertEqual(ad.clicks,0)
        import json,uuid
        from .models import PromotionEvent
        self.client.force_login(self.other)
        response=self.client.post('/analytics/collect/promotions/',{'events':json.dumps([{'id':str(uuid.uuid4()),'kind':'ad','object':ad.pk,'action':'view'}])})
        self.assertEqual(response.status_code,204)
        self.assertFalse(PromotionEvent.objects.filter(ad=ad).exists())
        ad.starts_at=today;ad.expires_at=today;ad.save()
        self.assertTrue(ad.is_live)  # inclusive end date
        self.assertContains(self.client.get('/'),'data-scheduled-slide')
        ad.expires_at=today-timedelta(days=1);ad.save()
        self.assertFalse(ad.is_live)
        self.assertNotContains(self.client.get('/'),'data-scheduled-slide')
        self.assertEqual(self.client.get(reverse('sponsored_post_detail',args=[ad.pk])).status_code,404)

    def test_invalid_dates_and_fake_banner_do_not_approve(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        ad,url=self.application();today=timezone.localdate()
        cases=[{'starts_at':str(today)}, {'starts_at':str(today),'ends_at':str(today-timedelta(days=1))}, {'starts_at':str(today-timedelta(days=1)),'ends_at':str(today)}, {'creative_image':SimpleUploadedFile('fake.png',b'not an image',content_type='image/png')}]
        for extra in cases:
            response=self.client.post(url,{'decision':'approve',**extra})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.context['form'].errors)
            ad.refresh_from_db();self.assertEqual(ad.status,'pending')

    def test_owner_cannot_control_schedule_or_designed_banner(self):
        self.submit(starts_at='2099-01-01',creative_image=image_file('owner-design.png'))
        ad=AdPost.objects.get()
        self.assertIsNone(ad.starts_at);self.assertFalse(ad.creative_image)
        self.assertEqual(self.client.post(reverse('pilot_admin_ad',args=[ad.pk]),{'decision':'approve'}).status_code,403)

    def test_csrf_get_and_inactive_owner_protection(self):
        ad,url=self.application()
        self.client.get(url,{'decision':'approve'})
        ad.refresh_from_db();self.assertEqual(ad.status,'pending')
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.admin)
        self.assertEqual(csrf.post(url,{'decision':'approve'}).status_code,403)
        self.client.post(url,{'decision':'approve','creative_image':image_file()})
        self.owner.is_active=False;self.owner.save(update_fields=['is_active'])
        self.assertNotContains(self.client.get('/'),'data-scheduled-slide')
        self.assertEqual(self.client.get(reverse('sponsored_post_detail',args=[ad.pk])).status_code,404)
