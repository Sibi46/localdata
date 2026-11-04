import json
import re
import uuid
from datetime import timedelta
from urllib.parse import urlencode
from django.conf import settings
from django.core.cache import cache
from django.test import Client,TestCase,override_settings
from django.urls import reverse
from django.utils import timezone
from .analytics import COOKIE,live_data
from .models import AnalyticsEvent,AnalyticsVisit,AnalyticsVisitor,User


@override_settings(SESSION_COOKIE_SECURE=False,LOCAL_ANALYTICS_ENABLED=True)
class AnalyticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member=User.objects.create_user('analytics-member',first_name='Priya')
        cls.other=User.objects.create_user('analytics-other')
        cls.admin=User.objects.create_user('analytics-admin',admin_role='super_admin')

    def setUp(self):cache.clear()

    def event(self,event_type='pageview',**extra):
        return {'id':str(uuid.uuid4()),'type':event_type,'path':'/',**extra}

    def post(self,events=None,client=None,**extra):
        client=client or self.client
        if COOKIE not in client.cookies:client.get('/')
        data={'events':json.dumps(events or []),'path':'/','device':'mobile',**extra}
        return client.post(reverse('analytics_collect'),urlencode(data),content_type='application/x-www-form-urlencoded')

    def test_html_has_tracker_signed_http_only_cookie_and_no_database_write(self):
        response=self.client.get('/')
        self.assertContains(response,'data-local-analytics')
        self.assertTrue(response.cookies[COOKIE]['httponly'])
        self.assertEqual(response.cookies[COOKIE]['samesite'],'Lax')
        self.assertFalse(AnalyticsVisitor.objects.exists())
        self.assertIn('private',response['Cache-Control'])

    def test_guest_page_and_click_are_recorded_without_query_strings(self):
        response=self.post([self.event(path='/?password=secret'),self.event('click',label='Shops',target='/businesses/?q=private')])
        self.assertEqual(response.status_code,204)
        self.assertEqual(AnalyticsVisitor.objects.count(),1)
        self.assertEqual(AnalyticsVisit.objects.count(),1)
        self.assertEqual(AnalyticsEvent.objects.count(),2)
        click=AnalyticsEvent.objects.get(event_type='click')
        self.assertEqual((click.path,click.target,click.label),('/','/businesses/','Shops'))
        self.assertIsNone(click.visit.user_id)

    def test_replayed_event_ids_do_not_inflate_counts(self):
        event=self.event();self.post([event]);self.post([event])
        self.assertEqual(AnalyticsEvent.objects.count(),1)
        self.assertEqual(AnalyticsVisit.objects.count(),1)

    def test_signed_in_activity_uses_request_user_not_client_user_id(self):
        self.client.force_login(self.member)
        self.post([self.event(user_id=self.other.pk)],user_id=self.other.pk)
        self.assertEqual(AnalyticsVisit.objects.get().user_id,self.member.pk)

    def test_admin_and_known_bots_are_not_tracked(self):
        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get('/'),'data-local-analytics')
        self.assertEqual(self.post([self.event()]).status_code,204)
        self.assertFalse(AnalyticsEvent.objects.exists())
        self.client.logout()
        self.assertNotContains(self.client.get('/',HTTP_USER_AGENT='ExampleCrawler'),'data-local-analytics')

    def test_dnt_and_disabled_tracking_are_respected(self):
        self.assertNotContains(self.client.get('/',HTTP_DNT='1'),'data-local-analytics')
        self.assertNotContains(self.client.get('/',HTTP_SEC_GPC='1'),'data-local-analytics')
        with override_settings(LOCAL_ANALYTICS_ENABLED=False):
            self.assertNotContains(self.client.get('/'),'data-local-analytics')
            self.assertEqual(self.post([self.event()]).status_code,204)
        self.assertFalse(AnalyticsEvent.objects.exists())

    def test_collector_requires_valid_cookie_and_csrf(self):
        response=self.client.post(reverse('analytics_collect'),urlencode({'path':'/'}),content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code,400)
        csrf=Client(enforce_csrf_checks=True)
        response=csrf.get('/')
        self.assertEqual(self.post([self.event()],client=csrf).status_code,403)
        token=re.search(r'data-csrf="([^"]+)"',response.content.decode()).group(1)
        self.assertEqual(self.post([self.event()],client=csrf,csrfmiddlewaretoken=token).status_code,204)

    def test_private_message_clicks_and_values_are_not_stored(self):
        self.post([self.event('click',path='/messages/123/',label='private chat contents'),self.event(path='/messages/123/'),self.event('click',label='Phone 9876543210 owner@example.com',target='tel:+919876543210')],password='secret',otp='123456',q='private search')
        self.assertEqual(AnalyticsEvent.objects.count(),2)
        message=AnalyticsEvent.objects.get(event_type='pageview')
        self.assertEqual(message.path,'/messages/')
        click=AnalyticsEvent.objects.get(event_type='click')
        self.assertEqual(click.label,'Phone [number] [email]')
        self.assertEqual(click.target,'contact:tel')

    def test_bad_batches_and_invalid_events_are_bounded(self):
        self.client.get('/')
        self.assertEqual(self.post(events='not a list').status_code,400)
        self.assertEqual(self.post([self.event() for _ in range(31)]).status_code,400)
        self.post([{'id':'bad','type':'click'},self.event('password'),self.event(path='/super-admin/')])
        self.assertFalse(AnalyticsEvent.objects.exists())

    def test_heartbeat_updates_time_without_creating_events(self):
        self.post([self.event()])
        visit=AnalyticsVisit.objects.get()
        AnalyticsVisit.objects.filter(pk=visit.pk).update(engagement_updated_at=timezone.now()-timedelta(seconds=20))
        self.post(seconds='20')
        visit.refresh_from_db();self.assertEqual(visit.engaged_seconds,20)
        self.assertEqual(AnalyticsEvent.objects.count(),1)
        self.post(seconds='25');visit.refresh_from_db();self.assertEqual(visit.engaged_seconds,20)

    def test_session_expires_after_thirty_minutes(self):
        self.post([self.event()])
        AnalyticsVisit.objects.update(last_seen=timezone.now()-timedelta(minutes=31))
        self.post([self.event()])
        self.assertEqual(AnalyticsVisit.objects.count(),2)
        self.assertEqual(AnalyticsVisitor.objects.count(),1)

    def test_login_attaches_member_and_logout_closes_previous_visit(self):
        self.post([self.event()]);self.client.force_login(self.member);self.post([self.event()])
        self.assertEqual(AnalyticsVisit.objects.count(),1)
        browser_cookie=self.client.cookies[COOKIE].value
        self.client.logout();self.client.cookies[COOKIE]=browser_cookie;self.post([self.event()])
        self.assertEqual(AnalyticsVisit.objects.count(),2)
        self.assertIsNotNone(AnalyticsVisit.objects.get(user=self.member).ended_at)
        self.assertEqual(live_data(),{'active':1,'members':0,'guests':1})

    def test_live_counts_only_recent_visitors_and_distinct_members(self):
        self.client.force_login(self.member);self.post([self.event()])
        guest=Client();self.post([self.event()],client=guest)
        self.assertEqual(live_data(),{'active':2,'members':1,'guests':1})
        AnalyticsVisit.objects.filter(user=self.member).update(last_seen=timezone.now()-timedelta(seconds=61))
        self.assertEqual(live_data(),{'active':1,'members':0,'guests':1})

    def test_dashboard_is_superadmin_only_and_counts_real_events(self):
        self.client.force_login(self.member)
        self.post([self.event(),self.event('click',label='Shops',target='/businesses/')])
        url=reverse('analytics_dashboard')
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.get(reverse('analytics_live')).status_code,403)
        self.client.force_login(self.admin)
        response=self.client.get(url)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context['summary']['views'],1)
        self.assertEqual(response.context['summary']['clicks'],1)
        self.assertEqual(response.context['summary']['members'],1)
        self.assertContains(response,'Priya');self.assertContains(response,'Shops')
        self.assertNotContains(response,'data-local-analytics')
        self.assertEqual(self.client.get(reverse('analytics_live')).json()['active'],1)
        self.assertEqual(self.client.get(url,{'period':'30'}).context['period'],'30')
        self.assertEqual(self.client.get(url,{'period':'invalid'}).context['period'],'today')

    def test_all_activity_is_paginated_and_filterable(self):
        events=[self.event('click',label='Shops',target='/businesses/') for _ in range(52)]
        self.post(events[:30]);self.post(events[30:])
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse('analytics_activity')).status_code,403)
        self.client.force_login(self.admin)
        response=self.client.get(reverse('analytics_activity'),{'period':'all','type':'click','q':'Shops'})
        self.assertEqual(response.context['page'].paginator.count,52)
        self.assertEqual(len(response.context['page']),50)
        self.assertEqual(len(self.client.get(reverse('analytics_activity'),{'page':2}).context['page']),2)

    def test_dashboard_ignores_events_outside_selected_period(self):
        self.post([self.event()])
        AnalyticsEvent.objects.update(created_at=timezone.now()-timedelta(days=10))
        AnalyticsVisit.objects.update(last_seen=timezone.now()-timedelta(days=10))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('analytics_dashboard')).context['summary']['views'],0)
        self.assertEqual(self.client.get(reverse('analytics_dashboard'),{'period':'30'}).context['summary']['views'],1)

    def test_short_sqlite_lock_is_retried_without_duplicate_events(self):
        from unittest.mock import patch
        from django.db import OperationalError
        from .analytics import _write_batch
        calls=0
        def collision(*args):
            nonlocal calls
            calls+=1
            if calls==1:raise OperationalError('database is locked')
            return _write_batch(*args)
        with patch('jobs.analytics._write_batch',side_effect=collision):
            self.assertEqual(self.post([self.event()]).status_code,204)
        self.assertEqual(calls,2)
        self.assertEqual(AnalyticsEvent.objects.count(),1)

    def test_notifications_do_not_leak_private_message_previews(self):
        self.post([self.event('click',path='/notifications/',label='A private message preview'),self.event(path='/notifications/')])
        self.assertEqual(AnalyticsEvent.objects.count(),1)
        self.assertEqual(AnalyticsEvent.objects.get().event_type,'pageview')
