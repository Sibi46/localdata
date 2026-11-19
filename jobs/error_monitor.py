"""Superadmin incidents. Never persist exception messages or request payloads."""
import hashlib
import logging
from django.db.models import F, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from .pilot_admin import private, is_superadmin

logger = logging.getLogger(__name__)
KINDS = {'server_exception', 'server_response', 'otp_delivery', 'otp_issue', 'otp_verify', 'otp_consume'}


def record(request, kind, exception=None, status=500):
    """Only server-owned labels: no URL parameters, user IDs, text or stack locals."""
    if kind not in KINDS:
        return
    match = getattr(request, 'resolver_match', None)
    route = (getattr(match, 'view_name', None) or 'unmatched')[:160]
    method = request.method if request.method in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'} else 'OTHER'
    category = type(exception).__name__[:80] if exception is not None else 'ServiceFailure'
    from django.db import connection
    if connection.in_atomic_block:
        # Save after signup's transaction exits, including when it rolls back.
        pending = getattr(request, '_pending_incidents', [])
        pending.append((kind, route, method, category, status))
        request._pending_incidents = pending
        return
    _persist(kind, route, method, category, status)


def _persist(kind, route, method, category, status):
    fingerprint = hashlib.sha256(f'{kind}:{route}:{method}:{category}:{status}'.encode()).hexdigest()
    try:
        from .models import SiteIncident
        now = timezone.now()
        item, created = SiteIncident.objects.get_or_create(fingerprint=fingerprint, defaults={
            'kind': kind, 'route': route, 'method': method, 'exception_type': category,
            'status_code': status, 'first_seen': now, 'last_seen': now})
        if not created:
            SiteIncident.objects.filter(pk=item.pk).update(count=F('count')+1,
                last_seen=now, resolved_at=None, resolved_by=None)
    except Exception:
        # A database outage must not replace the original response or recurse.
        logger.error('Incident storage unavailable; kind=%s route=%s category=%s', kind, route, category)


class ErrorMonitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code >= 500 and not getattr(request, '_incident_exception', False):
            record(request, 'server_response', status=response.status_code)
        for kind, route, method, category, status in getattr(request, '_pending_incidents', []):
            _persist(kind, route, method, category, status)
        return response

    def process_exception(self, request, exception):
        from django.core.exceptions import PermissionDenied, SuspiciousOperation
        from django.http import Http404
        if isinstance(exception, (Http404, PermissionDenied, SuspiciousOperation)):
            return None
        request._incident_exception = True
        record(request, 'server_exception', exception)
        return None


def indicator(request):
    user = getattr(request, 'user', None)
    if not user or not is_superadmin(user) or not request.path.startswith('/super-admin/'):
        return {}
    try:
        from .models import SiteIncident
        return {'open_incident_count': SiteIncident.objects.filter(resolved_at__isnull=True).count()}
    except Exception:
        return {'incident_monitor_unavailable': True}


@private
@require_GET
def dashboard(request):
    from .models import SiteIncident
    records = SiteIncident.objects.all().order_by('-last_seen', '-pk')
    if request.GET.get('status') != 'all':
        records = records.filter(resolved_at__isnull=True)
    return render(request, 'pilot_admin/errors.html', {'tab': 'errors',
        'show_all': request.GET.get('status') == 'all',
        'page': Paginator(records, 30).get_page(request.GET.get('page'))})


@private
@require_GET
def feed(request):
    from .models import SiteIncident
    records = SiteIncident.objects.filter(resolved_at__isnull=True)
    return JsonResponse({'open_count': records.count(),
                         'occurrences': records.aggregate(total=Sum('count'))['total'] or 0})


@private
@require_POST
def resolve(request, pk):
    from .models import SiteIncident
    item = get_object_or_404(SiteIncident, pk=pk)
    # A fresh occurrence after the displayed version must remain open.
    try:
        count = int(request.POST.get('count', ''))
    except ValueError:
        count = -1
    SiteIncident.objects.filter(pk=item.pk, count=count, resolved_at__isnull=True).update(
        resolved_at=timezone.now(), resolved_by=request.user)
    return redirect('admin_errors')
