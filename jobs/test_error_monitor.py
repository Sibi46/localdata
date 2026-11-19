from unittest.mock import patch
from django.db import OperationalError, transaction
from django.http import HttpResponse, Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse, resolve
from .error_monitor import ErrorMonitorMiddleware, record
from .models import SiteIncident, User


class ErrorMonitorTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('error-admin', admin_role='super_admin')
        self.member = User.objects.create_user('error-member')

    def request(self):
        request = RequestFactory().post('/register/?otp=123456', {'password': 'PRIVATE', 'phone': '9876543210'})
        request.resolver_match = resolve('/register/')
        return request

    def flush(self, request, status=200):
        ErrorMonitorMiddleware(lambda request: HttpResponse(status=status))(request)

    def test_sensitive_values_not_saved_and_repeats_grouped(self):
        for _ in range(2):
            request = self.request()
            record(request, 'otp_issue', RuntimeError('secret PRIVATE 123456 token'), 503)
            self.flush(request)
        item = SiteIncident.objects.get()
        self.assertEqual(item.count, 2)
        self.assertEqual(item.route, 'register')
        self.assertEqual(item.exception_type, 'RuntimeError')
        text = str(SiteIncident.objects.values().get())
        for secret in ['PRIVATE', '123456', '9876543210', 'token']:
            self.assertNotIn(secret, text)

    def test_exception_captured_once_and_expected_404_ignored(self):
        request = self.request()
        middleware = ErrorMonitorMiddleware(lambda request: HttpResponse(status=500))
        middleware.process_exception(request, RuntimeError('secret'))
        middleware(request)
        self.assertEqual(SiteIncident.objects.get().count, 1)
        request = self.request()
        middleware.process_exception(request, Http404())
        self.flush(request, 404)
        self.assertEqual(SiteIncident.objects.count(), 1)

    def test_explicit_500_response_and_storage_outage_preserve_response(self):
        request = self.request()
        self.flush(request, 503)
        self.assertEqual(SiteIncident.objects.get().status_code, 503)
        with patch('jobs.models.SiteIncident.objects.get_or_create', side_effect=OperationalError('secret DB password')):
            with self.assertLogs('jobs.error_monitor', level='ERROR') as logs:
                response = ErrorMonitorMiddleware(lambda request: HttpResponse(status=503))(self.request())
            self.assertNotIn('password', ' '.join(logs.output))
            self.assertEqual(response.status_code, 503)

    def test_resolution_recurrence_and_stale_resolution(self):
        request = self.request(); record(request, 'otp_delivery', status=503); self.flush(request)
        item = SiteIncident.objects.get()
        self.client.force_login(self.admin)
        path = reverse('admin_error_resolve', args=[item.pk])
        self.assertEqual(self.client.get(path).status_code, 405)
        self.client.post(path, {'count': 0})
        item.refresh_from_db(); self.assertIsNone(item.resolved_at)
        self.client.post(path, {'count': 1})
        item.refresh_from_db(); self.assertIsNotNone(item.resolved_at)
        request = self.request(); record(request, 'otp_delivery', status=503); self.flush(request)
        item.refresh_from_db(); self.assertIsNone(item.resolved_at)
        self.assertEqual(item.count, 2)

    def test_dashboard_indicator_feed_permissions_and_csrf(self):
        request = self.request(); record(request, 'otp_delivery', status=503); self.flush(request)
        self.client.force_login(self.member)
        for name in ['admin_errors', 'admin_error_feed']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('admin_error_feed')).json()['open_count'], 1)
        self.assertContains(self.client.get(reverse('admin_errors')), '1 unresolved')
        from django.test import Client
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.admin)
        self.assertEqual(csrf.post(reverse('admin_error_resolve', args=[SiteIncident.objects.get().pk]), {'count': 1}).status_code, 403)

    def test_rollback_does_not_erase_handled_incident(self):
        request = self.request()
        try:
            with transaction.atomic():
                record(request, 'otp_consume', RuntimeError('private'), 503)
                raise ValueError()
        except ValueError:
            pass
        self.flush(request)
        self.assertEqual(SiteIncident.objects.get().kind, 'otp_consume')
