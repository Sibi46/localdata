from django.test import Client,TestCase
from django.urls import reverse
from django.conf import settings
from .models import LocalFromFollow,User


class LocalFromFollowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=User.objects.create_user('instagram-member',first_name='Priya')
        cls.other=User.objects.create_user('instagram-other')

    def setUp(self):self.client.force_login(self.user)

    def test_home_and_account_invite_users_to_the_correct_instagram(self):
        for path in ['/','/account/']:
            response=self.client.get(path)
            self.assertContains(response,'Follow Local From on Instagram')
            self.assertContains(response,'https://www.instagram.com/local_from97/')
            self.assertContains(response,'target="_blank" rel="noopener noreferrer"')
        self.assertFalse(LocalFromFollow.objects.exists())

    def test_old_profile_link_redirects_to_instagram(self):
        response=self.client.get(reverse('local_from_profile'))
        self.assertEqual(response.url,settings.LOCAL_FROM_INSTAGRAM_URL)

    def test_opening_instagram_does_not_record_a_verified_follow(self):
        response=self.client.post(reverse('local_from_follow'),{'action':'follow','user':self.other.pk})
        self.assertEqual(response.url,settings.LOCAL_FROM_INSTAGRAM_URL)
        self.assertFalse(LocalFromFollow.objects.exists())

    def test_not_now_dismisses_without_following(self):
        response=self.client.post(reverse('local_from_follow'),{'action':'dismiss','next':'/account/'})
        self.assertEqual(response.url,'/account/')
        preference=LocalFromFollow.objects.get(user=self.user)
        self.assertTrue(preference.prompt_dismissed);self.assertFalse(preference.is_following)
        self.assertNotContains(self.client.get('/account/'),'aria-label="Follow Local From"')
        self.assertFalse(LocalFromFollow.objects.filter(user=self.other).exists())

    def test_dismiss_requires_csrf_and_valid_action(self):
        csrf_client=Client(enforce_csrf_checks=True);csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(reverse('local_from_follow'),{'action':'dismiss'}).status_code,403)
        self.assertEqual(self.client.post(reverse('local_from_follow'),{'action':'invented'}).status_code,400)
        self.assertFalse(LocalFromFollow.objects.exists())

    def test_external_return_link_is_rejected(self):
        response=self.client.post(reverse('local_from_follow'),{'action':'dismiss','next':'https://example.com'})
        self.assertEqual(response.url,'/')

    def test_guests_can_find_instagram_in_footer(self):
        self.client.logout()
        self.assertContains(self.client.get('/'),settings.LOCAL_FROM_INSTAGRAM_URL)
