from unittest import skip
from django.test import TestCase


# ─────────────────────────────────────────────────────────────────────────────
# Community Gallery Timeline — Post.event_date field and gallery grouping
# ─────────────────────────────────────────────────────────────────────────────

@skip('Retired community/family/badge feature; boundary covered by jobs.test_feature_scope')
class CommunityGalleryTest(TestCase):
    """
    Tests for the community gallery timeline feature:
    - event_date saved from POST form submission
    - invalid/missing date handled safely
    - gallery_groups grouping logic in community_page view
    """

    def _make_user(self):
        from jobs.models import User as User2
        import uuid
        phone = '97' + str(uuid.uuid4().int)[:8]
        return User2.objects.create_user(username=phone, password='test', phone=phone)

    def _make_community(self, user):
        from portal.models import Community
        import uuid
        return Community.objects.create(
            name='Test Community ' + str(uuid.uuid4().int)[:6],
            purpose='Testing',
            description='Test',
            location='Chennai',
            pincode='600001',
            created_by=user,
        )

    def _tiny_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        jpeg = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\x1e'
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4'
            b'\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
            b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4P\x00\x00\x00\x1f\xff\xd9'
        )
        return SimpleUploadedFile('test.jpg', jpeg, content_type='image/jpeg')

    def test_event_date_saved_on_post(self):
        """Posting with event_date saves the correct date."""
        from portal.models import Post, CommunityMember
        user = self._make_user()
        community = self._make_community(user)
        CommunityMember.objects.create(community=community, user=user, status='approved')
        self.client.force_login(user)
        self.client.post(f'/portal/c/{community.page_id}/post/', {
            'post_type': 'update',
            'content': 'Test gallery post',
            'image': self._tiny_image(),
            'event_date': '2024-03-15',
        })
        post = Post.objects.filter(community=community).first()
        self.assertIsNotNone(post)
        from datetime import date
        self.assertEqual(post.event_date, date(2024, 3, 15))

    def test_no_event_date_is_null(self):
        """Posting without event_date stores null."""
        from portal.models import Post, CommunityMember
        user = self._make_user()
        community = self._make_community(user)
        CommunityMember.objects.create(community=community, user=user, status='approved')
        self.client.force_login(user)
        self.client.post(f'/portal/c/{community.page_id}/post/', {
            'post_type': 'update',
            'content': 'No date post',
            'image': self._tiny_image(),
        })
        post = Post.objects.filter(community=community).first()
        self.assertIsNone(post.event_date)

    def test_invalid_event_date_ignored(self):
        """Non-date string in event_date does not cause a 500; stored as null."""
        from portal.models import Post, CommunityMember
        user = self._make_user()
        community = self._make_community(user)
        CommunityMember.objects.create(community=community, user=user, status='approved')
        self.client.force_login(user)
        resp = self.client.post(f'/portal/c/{community.page_id}/post/', {
            'post_type': 'update',
            'content': 'Bad date test',
            'image': self._tiny_image(),
            'event_date': 'not-a-date',
        })
        self.assertIn(resp.status_code, [200, 302])
        post = Post.objects.filter(community=community).first()
        self.assertIsNone(post.event_date)

    def test_gallery_groups_only_image_posts(self):
        """Only image posts appear in gallery (text-only posts excluded)."""
        from portal.models import Post, CommunityMember
        user = self._make_user()
        community = self._make_community(user)
        CommunityMember.objects.create(community=community, user=user, status='approved')
        Post.objects.create(community=community, author=user, content='Text only', is_active=True)
        self.client.force_login(user)
        self.client.post(f'/portal/c/{community.page_id}/post/', {
            'post_type': 'update',
            'content': 'With image',
            'image': self._tiny_image(),
            'event_date': '2024-06-01',
        })
        image_posts = community.posts.filter(is_active=True).exclude(image='')
        self.assertEqual(image_posts.count(), 1)
        all_posts = community.posts.filter(is_active=True).count()
        self.assertEqual(all_posts, 2)

    def test_gallery_groups_ordered_newest_first(self):
        """Image posts queryset is ordered by event_date descending."""
        from portal.models import Post, CommunityMember
        from datetime import date
        user = self._make_user()
        community = self._make_community(user)
        CommunityMember.objects.create(community=community, user=user, status='approved')
        self.client.force_login(user)
        self.client.post(f'/portal/c/{community.page_id}/post/', {
            'post_type': 'update', 'content': 'Old',
            'image': self._tiny_image(), 'event_date': '2022-01-01',
        })
        self.client.post(f'/portal/c/{community.page_id}/post/', {
            'post_type': 'update', 'content': 'New',
            'image': self._tiny_image(), 'event_date': '2025-06-01',
        })
        qs = list(community.posts.filter(is_active=True).exclude(image='').order_by('-event_date', '-created_at'))
        self.assertEqual(len(qs), 2)
        self.assertEqual(qs[0].event_date, date(2025, 6, 1))
        self.assertEqual(qs[1].event_date, date(2022, 1, 1))
