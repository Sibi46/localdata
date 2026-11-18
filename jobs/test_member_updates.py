import uuid
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import (AdminAnnouncement, CompanyProfile, Conversation, ConversationAdminAccess,
                     Message, Product, ProductVisit, User, UserNotification)


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class MemberUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('announcement-admin', admin_role='super_admin')
        cls.owner = User.objects.create_user('announcement-owner', user_type='shop')
        cls.member = User.objects.create_user('announcement-member')
        cls.other = User.objects.create_user('announcement-other')
        cls.inactive = User.objects.create_user('announcement-inactive', is_active=False)
        cls.shop = CompanyProfile.objects.create(user=cls.owner, company_name='Local Store')
        cls.product = Product.objects.create(shop=cls.shop, name='Handmade product', image='products/test.png')
        cls.thread = Conversation.objects.create(user_a=cls.member, user_b=cls.owner)
        cls.message = Message.objects.create(conversation=cls.thread, sender=cls.member,
                                             receiver=cls.owner, content='<script>private</script>')

    def send(self, token=None):
        self.client.force_login(self.admin)
        return self.client.post(reverse('admin_announcements'), {
            'title': 'Local update', 'message': '<script>Hello</script>',
            'submission_id': str(token or uuid.uuid4())})

    def test_send_audience_and_duplicate_submission(self):
        token = uuid.uuid4()
        response = self.send(token)
        self.assertEqual(response.status_code, 302)
        self.send(token)
        self.assertEqual(AdminAnnouncement.objects.count(), 1)
        self.assertEqual(set(UserNotification.objects.values_list('user_id', flat=True)),
                         {self.owner.pk, self.member.pk, self.other.pk})
        self.assertContains(self.client.get(response.url), '3</strong> recipients', html=False)

    def test_open_metrics_are_private_and_mark_all_is_not_an_open(self):
        self.send()
        item = AdminAnnouncement.objects.get()
        notice = UserNotification.objects.get(user=self.member)
        self.client.force_login(self.member)
        self.client.post(reverse('mark_all_notifications_read'))
        notice.refresh_from_db()
        self.assertIsNone(notice.opened_at)
        self.client.post(reverse('notification_open', args=[notice.pk]))
        response = self.client.get(reverse('member_announcement', args=[item.pk]))
        self.assertContains(response, '&lt;script&gt;Hello&lt;/script&gt;')
        notice.refresh_from_db()
        first_open = notice.opened_at
        self.assertIsNotNone(first_open)
        self.client.get(reverse('member_announcement', args=[item.pk]))
        notice.refresh_from_db()
        self.assertEqual(notice.opened_at, first_open)
        newcomer = User.objects.create_user('late-member')
        self.client.force_login(newcomer)
        self.assertEqual(self.client.get(reverse('member_announcement', args=[item.pk])).status_code, 404)

    def test_admin_routes_reject_regular_members_and_posts_need_csrf(self):
        self.client.force_login(self.member)
        for name in ['admin_announcements', 'shop_insights', 'admin_shop_conversations']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin_announcements'), {}).status_code, 403)
        from django.test import Client
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.admin)
        self.assertEqual(protected.post(reverse('admin_announcements'), {}).status_code, 403)

    def test_views_count_unique_members_and_repeats_exclude_owner_admin_optouts(self):
        for user in [self.owner, self.admin]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.product.get_absolute_url()).status_code, 200)
        self.client.force_login(self.member)
        self.client.get(self.product.get_absolute_url(), HTTP_DNT='1')
        self.client.get(self.product.get_absolute_url(), HTTP_SEC_GPC='1')
        self.assertFalse(ProductVisit.objects.exists())
        for _ in range(2):
            self.client.get(self.product.get_absolute_url())
        self.client.force_login(self.other)
        self.client.get(self.product.get_absolute_url())
        self.assertEqual(ProductVisit.objects.count(), 2)
        self.assertEqual(ProductVisit.objects.get(viewer=self.member).view_count, 2)
        self.client.force_login(self.owner)
        response = self.client.get(reverse('product_insights'))
        self.assertEqual(response.context['totals'], {'members': 2, 'opens': 3})
        self.assertNotContains(response, self.member.username)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('product_insights')).status_code, 404)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('shop_insights'))
        self.assertEqual(response.context['page'][0].members, 2)
        self.assertEqual(response.context['page'][0].opens, 3)

    def test_shop_review_is_audited_readonly_and_excludes_nonshop_threads(self):
        personal = Conversation.objects.create(user_a=self.member, user_b=self.other)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_shop_conversation', args=[self.thread.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '&lt;script&gt;private&lt;/script&gt;')
        self.assertEqual(ConversationAdminAccess.objects.filter(admin=self.admin, conversation=self.thread).count(), 1)
        self.message.refresh_from_db()
        self.assertFalse(self.message.is_read)
        self.assertEqual(self.client.get(reverse('admin_shop_conversation', args=[personal.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('admin_shop_conversation', args=[self.thread.pk])).status_code, 405)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse('admin_shop_conversation', args=[self.thread.pk])).status_code, 403)

    def test_customer_card_and_missing_price_render_without_discount_claim(self):
        self.product.discount_percent = 20
        self.product.save()
        self.client.force_login(self.member)
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, 'Ask shop for price')
        self.assertNotContains(response, '20% off')
        self.assertEqual(self.client.get(reverse('admin_announcements')).status_code, 403)

    def test_invalid_announcement_creates_no_notifications(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('admin_announcements'), {
            'title': 'x'*161, 'message': 'Update', 'submission_id': str(uuid.uuid4())})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AdminAnnouncement.objects.exists())
        self.assertFalse(UserNotification.objects.exists())
