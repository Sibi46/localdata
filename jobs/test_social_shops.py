from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import BusinessFollow, CompanyProfile, Conversation, LocalOffer, User


class SocialShopTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('social-shop', user_type='shop', pincode='600001', city='Chennai')
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Neighbour Store', industry='Clothing')
        cls.customer = User.objects.create_user('social-customer', user_type='individual')
        cls.offer = LocalOffer.objects.create(owner=cls.owner, business_name=cls.shop.company_name, title='Weekend clothing sale', discount_text='20% off', category='shop', is_active=True)

    def test_public_feed_has_shop_follow_and_message_links(self):
        self.client.force_login(self.customer)
        response = self.client.get('/advertise/')
        self.assertContains(response, 'Weekend clothing sale')
        self.assertContains(response, 'Message shop')
        self.assertContains(response, reverse('start_conversation', args=[self.owner.pk]))
        self.assertContains(response, self.shop.get_absolute_url())
        self.assertContains(response, 'Follow')

    def test_followed_feed_and_idempotent_follow_unfollow(self):
        self.client.force_login(self.customer)
        url = reverse('business_follow', args=[self.shop.company_id])
        self.assertNotContains(self.client.get('/advertise/?following=1'), self.offer.title)
        for _ in range(2):
            result = self.client.post(url, {'action': 'follow'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest').json()
            self.assertEqual(result, {'following': True, 'followers': 1})
        self.assertEqual(BusinessFollow.objects.count(), 1)
        self.assertContains(self.client.get('/advertise/?following=1'), self.offer.title)
        self.assertContains(self.client.get(self.shop.get_absolute_url()), 'Following')
        self.client.post(url, {'action': 'unfollow'})
        self.assertNotContains(self.client.get('/advertise/?following=1'), self.offer.title)

    def test_category_search_and_pincode_filters(self):
        self.client.force_login(self.customer)
        for query in ['?q=clothing', '?q=Neighbour', '?cat=shop', '?pincode=600001']:
            self.assertContains(self.client.get('/advertise/' + query), self.offer.title)
        for query in ['?q=unknown', '?cat=food', '?pincode=110001']:
            self.assertNotContains(self.client.get('/advertise/' + query), self.offer.title)
        response = self.client.get('/advertise/?format=json&pincode=600001')
        self.assertEqual(response.json()['count'], 1)
        self.assertIn('Message shop', response.json()['html'])

    def test_expired_pending_and_inactive_shop_offers_are_hidden(self):
        self.client.force_login(self.customer)
        LocalOffer.objects.create(owner=self.owner, business_name=self.shop.company_name, title='Pending offer', discount_text='5%', is_active=False)
        LocalOffer.objects.create(owner=self.owner, business_name=self.shop.company_name, title='Expired offer', discount_text='5%', valid_until=timezone.localdate() - timedelta(days=1))
        response = self.client.get('/advertise/')
        self.assertNotContains(response, 'Pending offer')
        self.assertNotContains(response, 'Expired offer')
        self.owner.is_active = False
        self.owner.save()
        self.assertNotContains(self.client.get('/advertise/'), self.offer.title)

    def test_shop_message_opens_same_private_conversation(self):
        url = reverse('start_conversation', args=[self.owner.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertFalse(Conversation.objects.exists())
        self.client.force_login(self.customer)
        first = self.client.get(url)
        second = self.client.get(url)
        self.assertEqual(first.url, second.url)
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.get()
        self.assertEqual({conversation.user_a_id, conversation.user_b_id}, {self.customer.pk, self.owner.pk})
        sent = self.client.post(reverse('send_message'), {'conv_id': conversation.pk, 'msg_type': 'text', 'content': 'Is this offer still available?'})
        self.assertTrue(sent.json()['ok'])
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(first.url), 'Is this offer still available?')

    def test_shop_directory_and_profile_expose_social_actions(self):
        self.client.force_login(self.customer)
        for path in ['/businesses/', self.shop.get_absolute_url()]:
            response = self.client.get(path)
            self.assertContains(response, reverse('business_follow', args=[self.shop.company_id]))
            self.assertContains(response, reverse('start_conversation', args=[self.owner.pk]))
            self.assertContains(response, 'followers')
