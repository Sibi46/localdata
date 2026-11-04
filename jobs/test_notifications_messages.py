from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import CompanyProfile, Conversation, Message, User, UserNotification
from .test_shop_catalog import image_file


@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.InMemoryStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class NotificationMessageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer=User.objects.create_user('message-customer',first_name='Customer')
        cls.owner=User.objects.create_user('message-owner',first_name='Owner',user_type='shop')
        cls.outsider=User.objects.create_user('message-outsider')
        cls.shop=CompanyProfile.objects.create(user=cls.owner,company_name='Vandavasi Paper Shop')
        cls.conv=Conversation.objects.create(user_a=cls.customer,user_b=cls.owner)

    def test_notification_feed_and_inbox_are_private(self):
        own=UserNotification.objects.create(user=self.customer,title='Your own update',message='A local update',link='/messages/')
        UserNotification.objects.create(user=self.outsider,title='Other private update',message='Not yours')
        self.client.force_login(self.customer)
        data=self.client.get(reverse('notification_feed')).json()
        self.assertEqual(data['unread_count'],1)
        self.assertEqual([item['id'] for item in data['items']],[own.pk])
        self.assertContains(self.client.get(reverse('notifications')),'Your own update')
        self.assertNotContains(self.client.get(reverse('notifications')),'Other private update')
        self.assertContains(self.client.get('/'),'Notifications, 1 unread')

    def test_open_and_mark_all_require_post_and_enforce_ownership(self):
        own=UserNotification.objects.create(user=self.customer,title='Open',message='Test',link='/messages/')
        foreign=UserNotification.objects.create(user=self.outsider,title='Other',message='Other')
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('notification_open',args=[own.pk])).status_code,405)
        self.assertEqual(self.client.get(reverse('mark_all_notifications_read')).status_code,405)
        self.assertEqual(self.client.post(reverse('notification_open',args=[foreign.pk])).status_code,404)
        self.assertRedirects(self.client.post(reverse('notification_open',args=[own.pk])),'/messages/')
        own.refresh_from_db();self.assertTrue(own.is_read)
        UserNotification.objects.create(user=self.customer,title='Next',message='Next')
        response=self.client.post(reverse('mark_all_notifications_read'),HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json()['unread_count'],0)
        foreign.refresh_from_db();self.assertFalse(foreign.is_read)

    def test_external_notification_links_cannot_redirect_off_site(self):
        self.client.force_login(self.customer)
        for link in ['https://example.com/','//example.com/','javascript:alert(1)']:
            item=UserNotification.objects.create(user=self.customer,title='Update',message='Test',link=link)
            self.assertRedirects(self.client.post(reverse('notification_open',args=[item.pk])),reverse('notifications'))

    def test_unread_filter_and_pagination(self):
        UserNotification.objects.bulk_create([UserNotification(user=self.customer,title=f'Update {i}',message='Details',is_read=i==0) for i in range(25)])
        self.client.force_login(self.customer)
        response=self.client.get(reverse('notifications'),{'unread':1})
        self.assertEqual(response.context['page'].paginator.count,24)
        self.assertEqual(len(response.context['page']),20)
        self.assertEqual(len(self.client.get(reverse('notifications'),{'page':2}).context['page']),5)
        self.assertEqual(len(self.client.get(reverse('notification_feed')).json()['items']),8)

    def test_send_receive_and_notification_read_sync(self):
        self.client.force_login(self.owner)
        response=self.client.post(reverse('send_message'),{'conv_id':self.conv.pk,'content':'Hello from our shop','msg_type':'text'})
        self.assertTrue(response.json()['ok'])
        notice=UserNotification.objects.get(user=self.customer)
        self.assertIn('Vandavasi Paper Shop',notice.title)
        self.client.force_login(self.customer)
        self.assertContains(self.client.get(reverse('chat_room',args=[self.conv.pk])),'Hello from our shop')
        notice.refresh_from_db();self.assertTrue(notice.is_read)
        self.assertTrue(Message.objects.get().is_read)
        self.assertContains(self.client.get(reverse('chat_list')),'Your conversations')
        self.assertNotContains(self.client.get(reverse('chat_list')),'job listing')

    def test_polling_marks_only_own_notifications_read(self):
        Message.objects.create(conversation=self.conv,sender=self.owner,receiver=self.customer,content='New hello')
        own=UserNotification.objects.create(user=self.customer,title='Message',message='New hello',link=f'/messages/{self.conv.pk}/')
        other=UserNotification.objects.create(user=self.owner,title='Other message',message='Other',link=f'/messages/{self.conv.pk}/')
        self.client.force_login(self.customer)
        data=self.client.get(reverse('poll_messages',args=[self.conv.pk]),{'after':0}).json()
        self.assertEqual(len(data['messages']),1)
        own.refresh_from_db();other.refresh_from_db()
        self.assertTrue(own.is_read);self.assertFalse(other.is_read)
        self.assertEqual(self.client.get(reverse('poll_messages',args=[self.conv.pk]),{'after':'bad'}).status_code,400)

    def test_message_membership_and_validation(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(reverse('send_message'),{'conv_id':self.conv.pk,'content':'No access'}).status_code,403)
        self.assertEqual(self.client.get(reverse('poll_messages',args=[self.conv.pk])).status_code,403)
        self.client.force_login(self.customer)
        for data in [{'content':''},{'content':'x'*5001},{'msg_type':'image'},{'file':SimpleUploadedFile('script.html',b'<script>bad</script>')}]:
            response=self.client.post(reverse('send_message'),{'conv_id':self.conv.pk,**data})
            self.assertEqual(response.status_code,400)
        self.assertFalse(Message.objects.exists())

    def test_photo_attachments_and_escaped_message_content(self):
        self.client.force_login(self.customer)
        response=self.client.post(reverse('send_message'),{'conv_id':self.conv.pk,'msg_type':'image','file':image_file('message.png'),'content':'<script>alert(1)</script>'})
        self.assertTrue(response.json()['ok'])
        self.assertIn('&lt;script&gt;',response.json()['html'])
        self.assertNotIn('<script>',response.json()['html'])
        self.assertEqual(Message.objects.get().msg_type,'image')
