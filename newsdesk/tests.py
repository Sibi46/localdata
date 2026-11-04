from unittest import skip
from jobportal.test_support import view_middleware
import io
import json
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from jobs.models import District, PinCode, State
from . import services
from .models import BirthdayCard, Comment, CommentReport, NewsAgent, NewsItem, Rating


# View-level contract tests; full middleware access is covered separately.
@override_settings(MIDDLEWARE=view_middleware())
class NewsDeskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model()
        cls.resident = user.objects.create_user(username='9876543210', password='testpass', pincode='600001')
        cls.agent = user.objects.create_user(username='agent', password='testpass')
        cls.other_agent = user.objects.create_user(username='other', password='testpass')
        cls.admin = user.objects.create_superuser(username='admin', password='testpass', email='test@example.com')
        state = State.objects.create(name='Test state', code='TS')
        district = District.objects.create(name='Test district', state=state)
        cls.pin = PinCode.objects.create(code='600001', district=district, area_name='First neighbourhood')
        cls.other_pin = PinCode.objects.create(code='600002', district=district, area_name='Second neighbourhood')
        cls.assignment = NewsAgent.objects.create(user=cls.agent, pincode=cls.pin)
        NewsAgent.objects.create(user=cls.other_agent, pincode=cls.other_pin)
        cls.item = NewsItem.objects.create(title='Local cricket tournament', body='Come cheer for your neighbours.', category='sports', pincode=cls.pin, author=cls.agent, status='published')
        cls.draft = NewsItem.objects.create(title='Unpublished story', body='Draft text', pincode=cls.pin, author=cls.agent)
        cls.other_item = NewsItem.objects.create(title='Another pincode', body='News elsewhere', pincode=cls.other_pin, author=cls.other_agent, status='published')

    def setUp(self):
        self.client.force_login(self.resident)

    def url(self, name, *args):
        return reverse('newsdesk:' + name, args=args)

    def post_json(self, name, pk=None, **data):
        return self.client.post(self.url(name, *([pk] if pk is not None else [])), json.dumps(data), content_type='application/json')

    def story_data(self, **changes):
        return {'title': 'A new local story', 'body': 'Useful local news', 'category': 'community', 'kind': 'news', 'status': 'draft', **changes}

    def test_public_feed_filters_pincode_category_and_kind(self):
        self.client.logout()
        result = self.client.get(self.url('api_feed'), {'pincode': self.pin.code, 'category': 'sports', 'kind': 'news'})
        self.assertEqual([row['id'] for row in result.json()['results']], [self.item.pk])
        self.assertEqual(self.client.get(self.url('api_feed'), {'pincode': '123'}).status_code, 400)
        self.assertEqual(self.client.get(self.url('api_feed'), {'category': 'invented'}).status_code, 400)

    def test_typed_pincode_on_feed_and_story_forms(self):
        response = self.client.get(self.url('feed'), {'pincode': self.pin.code})
        self.assertContains(response, 'name="pincode"')
        self.assertContains(response, 'inputmode="numeric"')
        self.client.force_login(self.admin)
        response = self.client.get(self.url('edit', self.item.pk))
        self.assertContains(response, 'value="600001"')
        self.assertContains(response, 'inputmode="numeric"')
        response = self.client.post(self.url('create'), self.story_data(pincode=self.other_pin.code))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(NewsItem.objects.get(title='A new local story').pincode, self.other_pin)
        response = self.client.post(self.url('create'), self.story_data(pincode='999999'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NewsItem.objects.filter(pincode__code='999999').exists())

    def test_unregistered_pincode_feed_and_atomic_creation(self):
        self.assertEqual(self.client.get(self.url('api_feed'), {'pincode': '654321'}).json()['total'], 0)
        self.assertFalse(PinCode.objects.filter(code='654321').exists())
        self.client.force_login(self.admin)
        response = self.client.post(self.url('create'), self.story_data(pincode='654321', title=''))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PinCode.objects.filter(code='654321').exists())
        response = self.client.post(self.url('create'), self.story_data(pincode='654321', status='published'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(self.url('api_feed'), {'pincode': '654321'}).json()['total'], 1)

    def test_selected_pin_remembered_and_reset(self):
        self.client.get(self.url('feed'), {'pincode': self.other_pin.code})
        self.assertEqual(self.client.get(self.url('api_feed')).json()['results'][0]['id'], self.other_item.pk)
        self.assertEqual(self.client.get(self.url('api_feed'), {'pincode': ''}).json()['total'], 2)

    def test_front_page_remembers_selected_area_and_logout_restores_public_view(self):
        self.client.get(self.url('feed'), {'pincode': self.pin.code})
        response = self.client.get(self.url('feed'))
        self.assertContains(response, self.item.title)
        self.assertNotContains(response, self.other_item.title)
        self.assertNotContains(response, self.draft.title)
        self.client.logout()
        response = self.client.get(self.url('feed'))
        self.assertContains(response, self.item.title)
        self.assertContains(response, self.other_item.title)
        response = self.client.get(self.url('feed'), {'pincode': self.pin.code})
        self.assertNotContains(response, self.other_item.title)

    def test_drafts_and_future_publications_never_public(self):
        self.assertEqual(self.client.get(self.url('api_detail', self.draft.pk)).status_code, 404)
        NewsItem.objects.filter(pk=self.item.pk).update(published_at=timezone.now() + timedelta(hours=1))
        self.assertEqual(self.client.get(self.url('api_detail', self.item.pk)).status_code, 404)

    def test_inactive_pincode_hierarchy_blocks_reads_and_agent_writes(self):
        state = self.pin.district.state
        state.is_active = False
        state.save()
        self.assertEqual(self.client.get(self.url('api_detail', self.item.pk)).status_code, 404)
        self.client.force_login(self.agent)
        self.assertEqual(self.post_json('api_create', **self.story_data()).status_code, 403)

    def test_resident_cannot_access_desk_or_assign_agents(self):
        self.assertEqual(self.client.get(self.url('manage')).status_code, 403)
        self.assertEqual(self.post_json('api_create', **self.story_data()).status_code, 403)
        self.assertEqual(self.client.get(self.url('agents')).status_code, 403)

    def test_agent_cannot_edit_or_read_other_desk_drafts(self):
        self.client.force_login(self.other_agent)
        self.assertEqual(self.post_json('api_edit', self.item.pk, **self.story_data()).status_code, 404)
        self.assertEqual(self.client.get(self.url('api_edit', self.draft.pk)).status_code, 404)
        self.assertEqual(self.client.get(self.url('agents')).status_code, 403)

    def test_agent_create_ignores_forged_author_pin_and_publication_time(self):
        self.client.force_login(self.agent)
        result = self.post_json('api_create', **self.story_data(status='published', pincode=self.other_pin.pk, author=self.admin.pk, published_at='2000-01-01'))
        self.assertEqual(result.status_code, 201, result.content)
        item = NewsItem.objects.get(pk=result.json()['id'])
        self.assertEqual(item.pincode, self.pin)
        self.assertEqual(item.author, self.agent)
        self.assertGreater(item.published_at, timezone.now() - timedelta(minutes=1))

    def test_agent_draft_then_publish(self):
        self.client.force_login(self.agent)
        result = self.post_json('api_create', **self.story_data())
        self.assertEqual(result.status_code, 201, result.content)
        item = NewsItem.objects.get(pk=result.json()['id'])
        self.assertIsNone(item.published_at)
        self.assertEqual(self.client.get(self.url('api_detail', item.pk)).status_code, 404)
        result = self.post_json('api_edit', item.pk, **self.story_data(status='published'))
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(self.client.get(self.url('api_detail', item.pk)).status_code, 200)

    def test_republishing_and_edits_do_not_restart_comment_clock(self):
        original = timezone.now() - timedelta(days=8)
        NewsItem.objects.filter(pk=self.item.pk).update(published_at=original)
        self.client.force_login(self.agent)
        self.assertEqual(self.post_json('api_edit', self.item.pk, **self.story_data()).status_code, 200)
        self.assertEqual(self.post_json('api_edit', self.item.pk, **self.story_data(status='published')).status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.published_at, original)
        self.assertFalse(self.item.comments_open)

    def test_deactivated_or_reassigned_agent_loses_old_scope(self):
        self.client.force_login(self.agent)
        self.assignment.is_active = False
        self.assignment.save()
        self.assertEqual(self.client.get(self.url('api_manage')).status_code, 403)
        self.assignment.is_active = True
        self.assignment.pincode = self.other_pin
        self.assignment.save()
        self.assertEqual(self.client.get(self.url('api_edit', self.item.pk)).status_code, 404)

    def test_agent_cannot_change_existing_pincode_even_admin(self):
        self.client.force_login(self.admin)
        result = self.post_json('api_edit', self.item.pk, **self.story_data(pincode=self.other_pin.pk))
        self.assertEqual(result.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.pincode, self.pin)

    def test_admin_can_assign_update_and_disable_agent(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url('agents'), {'user': self.resident.pk, 'pincode': self.pin.pk, 'is_active': True})
        self.assertEqual(response.status_code, 302)
        obj = NewsAgent.objects.get(user=self.resident)
        response = self.client.post(self.url('agent_edit', obj.pk), {'user': self.resident.pk, 'pincode': self.other_pin.pk})
        self.assertEqual(response.status_code, 302)
        obj.refresh_from_db()
        self.assertFalse(obj.is_active)
        self.assertEqual(obj.pincode, self.other_pin)

    def test_all_categories_allowed_unknown_rejected(self):
        for category in NewsItem.Category.values:
            item = services.save_item(self.agent, self.story_data(category=category))
            self.assertEqual(item.category, category)
        with self.assertRaises(ValidationError):
            services.save_item(self.agent, self.story_data(category='unknown'))

    def test_event_requires_start_and_venue_and_valid_end(self):
        self.client.force_login(self.agent)
        self.assertEqual(self.post_json('api_create', **self.story_data(kind='event')).status_code, 400)
        start = timezone.now() + timedelta(days=1)
        data = self.story_data(kind='event', venue='Community ground', event_start=start.isoformat())
        self.assertEqual(self.post_json('api_create', **data).status_code, 201)
        data['event_end'] = (start - timedelta(hours=1)).isoformat()
        self.assertEqual(self.post_json('api_create', **data).status_code, 400)

    def test_comments_exact_seven_day_cutoff_and_existing_visibility(self):
        published = self.item.published_at
        with patch('newsdesk.models.timezone.now', return_value=published + timedelta(days=7) - timedelta(microseconds=1)):
            response = self.post_json('api_comment', self.item.pk, text='Just in time')
            self.assertEqual(response.status_code, 201)
        with patch('newsdesk.models.timezone.now', return_value=published + timedelta(days=7)):
            self.assertEqual(self.post_json('api_comment', self.item.pk, text='Too late').status_code, 400)
            response = self.client.get(self.url('api_detail', self.item.pk))
            self.assertFalse(response.json()['comments_open'])
            self.assertEqual(response.json()['comments']['results'][0]['text'], 'Just in time')
            self.assertContains(self.client.get(self.url('detail', self.item.pk)), 'Comments closed seven days')

    def test_comment_length_whitespace_and_unicode(self):
        for value in ['', '   ', 'a' * 161]:
            self.assertEqual(self.post_json('api_comment', self.item.pk, text=value).status_code, 400)
        self.assertEqual(self.post_json('api_comment', self.item.pk, text='🏏' * 160).status_code, 201)
        self.assertEqual(Comment.objects.get().user, self.resident)

    def test_drafts_cannot_receive_comments_ratings_or_reports(self):
        self.assertEqual(self.post_json('api_comment', self.draft.pk, text='hello').status_code, 404)
        self.assertEqual(self.post_json('api_rate', self.draft.pk, stars=5).status_code, 404)
        comment = Comment.objects.create(item=self.draft, user=self.resident, text='private')
        self.assertEqual(self.post_json('api_report', comment.pk, reason='test').status_code, 404)

    def test_rating_upsert_and_range_validation(self):
        for stars in [0, 6, 'bad', 2.5]:
            self.assertEqual(self.post_json('api_rate', self.item.pk, stars=stars).status_code, 400)
        self.assertEqual(self.post_json('api_rate', self.item.pk, stars=1).status_code, 200)
        self.assertEqual(self.post_json('api_rate', self.item.pk, stars=5).status_code, 200)
        self.assertEqual(Rating.objects.count(), 1)
        self.assertEqual(Rating.objects.get().stars, 5)
        self.assertEqual(self.client.get(self.url('api_detail', self.item.pk)).json()['ratings'], {'average': 5.0, 'total': 1})

    def test_rating_database_constraints(self):
        Rating.objects.create(item=self.item, user=self.resident, stars=3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Rating.objects.create(item=self.item, user=self.resident, stars=4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Rating.objects.create(item=self.item, user=self.agent, stars=6)

    def test_report_duplicate_prevention_and_moderation(self):
        obj = services.add_comment(self.resident, self.item.pk, {'text': 'A comment'})
        self.assertEqual(self.post_json('api_report', obj.pk, reason='Not helpful').status_code, 201)
        self.assertEqual(self.post_json('api_report', obj.pk, reason='Again').status_code, 200)
        self.assertEqual(CommentReport.objects.count(), 1)
        self.client.force_login(self.agent)
        self.assertEqual(self.post_json('api_moderate', obj.pk, action='hide').status_code, 200)
        obj.refresh_from_db()
        self.assertTrue(obj.is_hidden)
        self.assertEqual(obj.moderated_by, self.agent)
        self.assertTrue(CommentReport.objects.get().resolved)
        self.assertEqual(self.client.get(self.url('api_detail', self.item.pk)).json()['comments']['total'], 0)
        self.assertEqual(self.post_json('api_moderate', obj.pk, action='restore').status_code, 200)
        self.assertEqual(self.client.get(self.url('api_detail', self.item.pk)).json()['comments']['total'], 1)

    def test_moderation_and_report_queue_are_pincode_scoped(self):
        obj = services.add_comment(self.resident, self.item.pk, {'text': 'A comment'})
        services.report_comment(self.resident, obj.pk, {'reason': 'Check this'})
        self.assertEqual(self.post_json('api_moderate', obj.pk, action='hide').status_code, 403)
        self.client.force_login(self.other_agent)
        self.assertEqual(self.post_json('api_moderate', obj.pk, action='hide').status_code, 404)
        self.assertEqual(self.client.get(self.url('api_manage'), {'tab': 'reports'}).json()['total'], 0)
        self.client.force_login(self.agent)
        self.assertEqual(self.client.get(self.url('api_manage'), {'tab': 'reports'}).json()['total'], 1)

    def test_dismiss_report_keeps_comment_visible(self):
        obj = services.add_comment(self.resident, self.item.pk, {'text': 'A comment'})
        services.report_comment(self.resident, obj.pk, {'reason': 'Check this'})
        services.moderate_comment(self.agent, obj.pk, 'resolve')
        obj.refresh_from_db()
        self.assertFalse(obj.is_hidden)
        self.assertTrue(obj.reports.get().resolved)

    def test_csrf_and_auth_required_for_writes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.resident)
        self.assertEqual(client.post(self.url('api_comment', self.item.pk), {'text': 'hi'}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.post_json('api_comment', self.item.pk, text='hi').status_code, 401)
        self.assertEqual(self.client.post(self.url('comment', self.item.pk), {'text': 'hi'}).status_code, 302)
        self.assertEqual(self.client.get(self.url('comment', self.item.pk)).status_code, 405)

    def test_malformed_json_is_a_validation_error(self):
        for value in ['{', '[]', '{"text":["x"]}']:
            self.assertEqual(self.client.post(self.url('api_comment', self.item.pk), value, content_type='application/json').status_code, 400)

    def test_public_content_escaped_and_phone_username_hidden(self):
        services.add_comment(self.resident, self.item.pk, {'text': '<script>alert(1)</script>'})
        self.client.logout()
        response = self.client.get(self.url('detail', self.item.pk))
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, self.resident.username)

    def test_html_pages_render_for_each_role(self):
        for name, args in [('feed', []), ('detail', [self.item.pk])]:
            self.assertEqual(self.client.get(self.url(name, *args)).status_code, 200)
        self.client.force_login(self.agent)
        for name, args in [('manage', []), ('create', []), ('edit', [self.draft.pk])]:
            self.assertEqual(self.client.get(self.url(name, *args)).status_code, 200)
        for tab in ['stories', 'comments', 'reports']:
            self.assertEqual(self.client.get(self.url('manage'), {'tab': tab}).status_code, 200)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url('manage')).status_code, 200)
        self.assertEqual(self.client.get(self.url('agents')).status_code, 200)
        self.assertEqual(self.client.get('/admin/newsdesk/newsitem/add/').status_code, 200)
        self.assertEqual(self.client.get(f'/admin/newsdesk/newsitem/{self.item.pk}/change/').status_code, 200)

    def test_pagination_does_not_leak_other_pincodes(self):
        for n in range(14):
            NewsItem.objects.create(title=f'News {n}', body='Story', pincode=self.pin, author=self.agent, status='published')
        data = self.client.get(self.url('api_feed'), {'pincode': self.pin.code, 'page': 2}).json()
        self.assertEqual(data['total'], 15)
        self.assertEqual(len(data['results']), 3)
        self.assertTrue(all(row['pincode'] == self.pin.code for row in data['results']))

    def test_photo_video_upload_validation_private_draft_and_publish(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(NEWSDESK_MEDIA_ROOT=directory):
            photo = io.BytesIO()
            Image.new('RGB', (10, 10)).save(photo, format='PNG')
            item = services.save_item(self.agent, self.story_data(), {'photo': SimpleUploadedFile('photo.png', photo.getvalue(), 'image/png')})
            self.assertTrue(Path(item.photo.path).is_file())
            self.assertFalse(item.photo.name.startswith('photo'))
            self.assertEqual(self.client.get(self.url('media', item.pk, 'photo')).status_code, 403)
            self.client.force_login(self.other_agent)
            self.assertEqual(self.client.get(self.url('media', item.pk, 'photo')).status_code, 404)
            self.client.force_login(self.agent)
            response = self.client.get(self.url('media', item.pk, 'photo'))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(b''.join(response.streaming_content))
            services.save_item(self.agent, self.story_data(status='published'), pk=item.pk)
            self.client.logout()
            response = self.client.get(self.url('media', item.pk, 'photo'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
            self.assertTrue(b''.join(response.streaming_content))
            for name, content in [('bad.mp4', b'<html>'), ('x.html', b'0000ftypisom')]:
                with self.assertRaises(ValidationError):
                    services.save_item(self.agent, self.story_data(), {'video': SimpleUploadedFile(name, content)})
            with self.assertRaises(ValidationError):
                services.save_item(self.agent, self.story_data(), {'photo': SimpleUploadedFile('x.png', b'<script>bad</script>')})
            with self.assertRaises(ValidationError):
                services.save_item(self.agent, self.story_data(), {'video': SimpleUploadedFile('large.mp4', b'0000ftypisom' + b'0' * (25 * 1024 * 1024))})

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_birthday_cards_private_by_default_and_download_escaped(self):
        response = self.post_json('api_birthday', recipient='<script>bad</script>', message='Have a wonderful day & year', theme='sunshine')
        self.assertEqual(response.status_code, 201, response.content)
        card = BirthdayCard.objects.get()
        self.assertFalse(card.is_public)
        self.assertEqual(card.user, self.resident)
        response = self.client.get(self.url('card', card.pk), {'download': 1})
        self.assertContains(response, '&lt;script&gt;bad&lt;/script&gt;')
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertIn('attachment', response['Content-Disposition'])
        self.client.logout()
        self.assertEqual(self.client.get(self.url('card', card.pk)).status_code, 404)
        self.assertEqual(self.client.get(self.url('card', card.pk), {'download': 1}).status_code, 404)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_public_card_share_and_owner_delete(self):
        card = BirthdayCard.objects.create(user=self.resident, recipient='Friend', message='Happy birthday!', is_public=True)
        self.client.force_login(self.agent)
        self.assertEqual(self.client.post(self.url('remove_card', card.pk)).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url('card', card.pk)).status_code, 200)
        self.client.force_login(self.resident)
        self.assertEqual(self.client.post(self.url('remove_card', card.pk)).status_code, 302)
        self.assertEqual(self.client.get(self.url('card', card.pk)).status_code, 404)

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_birthday_validation_and_auth(self):
        for changes in [{'recipient': ''}, {'message': 'a' * 161}, {'theme': 'bad'}]:
            data = {'recipient': 'Friend', 'message': 'Have a great day', 'theme': 'sky', **changes}
            self.assertEqual(self.post_json('api_birthday', **data).status_code, 400)
        self.client.logout()
        self.assertEqual(self.post_json('api_birthday', recipient='Friend', message='Hi').status_code, 401)

    def test_admin_api_assignments_and_public_pincode_search(self):
        self.assertEqual(self.client.get(self.url('api_agents')).status_code, 403)
        self.assertEqual(self.client.get(self.url('api_pincodes'), {'q': '60000'}).json()['total'], 2)
        self.assertEqual(self.client.get(self.url('api_pincodes'), {'q': 'bad'}).status_code, 400)
        self.client.force_login(self.admin)
        result = self.post_json('api_agents', user=self.resident.pk, pincode=self.pin.pk, is_active=True)
        self.assertEqual(result.status_code, 201, result.content)
        result = self.post_json('api_agent_edit', result.json()['id'], user=self.resident.pk, pincode=self.other_pin.pk, is_active=False)
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json()['is_active'])
        self.assertEqual(self.client.get(self.url('api_agents')).json()['total'], 3)

    def test_staff_flag_alone_does_not_grant_news_admin(self):
        self.resident.is_staff = True
        self.resident.save()
        self.assertEqual(self.client.get(self.url('api_agents')).status_code, 403)
        self.assertEqual(self.client.get('/admin/newsdesk/newsitem/').status_code, 403)

    def test_portal_super_admin_has_desk_access_without_staff(self):
        self.resident.admin_role = 'super_admin'
        self.resident.save()
        self.assertEqual(self.client.get(self.url('api_agents')).status_code, 200)
        self.assertEqual(self.post_json('api_create', **self.story_data(pincode=self.other_pin.pk)).status_code, 201)

    def test_html_validation_retains_story_input(self):
        self.client.force_login(self.agent)
        response = self.client.post(self.url('create'), self.story_data(kind='event'))
        self.assertContains(response, 'A new local story', status_code=400)
        self.assertContains(response, 'Events require a start time and venue.', status_code=400)
        self.assertFalse(NewsItem.objects.filter(title='A new local story').exists())

    @skip('Retired feature; absence and data preservation covered by jobs.test_feature_scope')
    def test_birthday_api_lists_only_own_cards(self):
        BirthdayCard.objects.create(user=self.agent, recipient='Private', message='Secret')
        BirthdayCard.objects.create(user=self.resident, recipient='Friend', message='Hi')
        result = self.client.get(self.url('api_birthday')).json()['results']
        self.assertEqual([card['recipient'] for card in result], ['Friend'])

    def test_missing_and_invalid_moderation_actions_rejected(self):
        obj = services.add_comment(self.resident, self.item.pk, {'text': 'A comment'})
        self.client.force_login(self.agent)
        for action in ['', 'delete', None]:
            self.assertEqual(self.post_json('api_moderate', obj.pk, action=action).status_code, 400)
        obj.refresh_from_db()
        self.assertFalse(obj.is_hidden)
