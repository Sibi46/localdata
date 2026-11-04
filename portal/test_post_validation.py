from unittest import skip
import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from jobs.models import User, JobSeekerProfile
from .models import Community, CommunityMember, Post


@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
@override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}, 'staticfiles': {'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}},
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class CommunityPostValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('post-author', first_name='Author', pincode='600001')
        JobSeekerProfile.objects.create(user=self.user, photo='profile.jpg')
        self.community = Community.objects.create(name='Test group', created_by=self.user, purpose='Tests', description='Test community', location='Test city', pincode='600001', join_mode='open')
        self.client.force_login(self.user)
        self.page = f'/portal/c/{self.community.page_id}/'

    def test_empty_and_invisible_posts_are_rejected(self):
        for content in ('', ' \n\t', '\u200b \u200b \ufeff'):
            response = self.client.post(self.page + 'post/', {'content':content}, follow=True)
            self.assertContains(response, 'Write a message or attach a photo before publishing.')
        self.assertEqual(Post.objects.count(), 0)

    def test_text_and_photo_only_posts_remain_supported(self):
        self.client.post(self.page + 'post/', {'content':'Published message'})
        data = io.BytesIO(); Image.new('RGB',(8,8),'blue').save(data,format='PNG')
        self.client.post(self.page + 'post/', {'content':'', 'image':SimpleUploadedFile('photo.png',data.getvalue(),content_type='image/png')})
        self.assertEqual(Post.objects.count(),2)
        self.assertTrue(Post.objects.order_by('-pk').first().image)

    def test_invalid_attachment_cannot_bypass_empty_post_validation(self):
        self.client.post(self.page + 'post/', {'image':SimpleUploadedFile('fake.png',b'not an image',content_type='image/png')})
        self.assertEqual(Post.objects.count(),0)

    def test_join_is_idempotent_and_count_is_fresh(self):
        self.client.get(self.page + 'join/')
        self.client.get(self.page + 'join/')
        self.assertEqual(CommunityMember.objects.filter(community=self.community,user=self.user).count(),1)
        response = self.client.get(self.page + 'membership-status/')
        self.assertEqual(response.json(), {'member_count':1,'status':'approved'})
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('no-store', self.client.get(self.page)['Cache-Control'])

    def test_pending_members_are_not_counted_as_approved(self):
        self.community.join_mode='approval'; self.community.save()
        self.client.get(self.page + 'join/')
        self.assertEqual(self.client.get(self.page + 'membership-status/').json(), {'member_count':0,'status':'pending'})
