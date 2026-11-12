"""Owner-only aggregate promotion statistics and bounded browser event intake."""
import json
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import caches
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import AdPost, Advertisement, LocalOffer, PromotionEvent
from .shop import owner_shop


@require_POST
def collect(request):
    if request.headers.get('Sec-GPC') == '1' or request.headers.get('DNT') == '1':
        return HttpResponse(status=204)
    if len(request.body) > 20000:
        return HttpResponse(status=413)
    try:
        events = json.loads(request.POST.get('events', '[]'))
        if not isinstance(events, list) or len(events) > 20:
            raise ValueError
    except (ValueError, TypeError):
        return HttpResponse(status=400)
    if getattr(request.user, 'admin_role', ''):
        return HttpResponse(status=204)
    from .analytics import visitor_id
    visitor = visitor_id(request)
    if visitor is None:
        try:
            visitor = uuid.UUID(request.session.get('promotion_visitor', ''))
        except (ValueError, TypeError, AttributeError):
            visitor = uuid.uuid4()
            request.session['promotion_visitor'] = str(visitor)
    cache = caches[settings.OTP_CACHE_ALIAS]
    key = f'promotion-rate:{visitor}'
    if not cache.add(key, len(events), timeout=60):
        try:
            if cache.incr(key, len(events)) > 120:
                return HttpResponse(status=429)
        except ValueError:
            return HttpResponse(status=429)
    user = request.user if request.user.is_authenticated else None
    today = timezone.localdate()
    offers = LocalOffer.objects.filter(is_active=True).filter(Q(owner__isnull=True) | Q(owner__is_active=True)).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
    ads = AdPost.objects.filter(status='approved', user__is_active=True).filter(Q(expires_at__isnull=True) | Q(expires_at__gte=today)).filter(Q(starts_at__isnull=True) | Q(starts_at__lte=today))
    # Resolve only submitted IDs; never trust an owner or visibility flag from JS.
    valid = []
    for event in events:
        try:
            if not isinstance(event, dict) or event.get('action') not in ('view', 'click') or event.get('kind') not in ('offer', 'ad'):
                continue
            event_id = uuid.UUID(str(event['id']))
            pk = int(event['object'])
            if pk <= 0 or pk > 9223372036854775807:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        valid.append((event_id, event['kind'], pk, event['action']))
    offer_ids = dict(offers.filter(pk__in=[pk for _, kind, pk, _ in valid if kind == 'offer']).values_list('pk', 'owner_id'))
    ad_ids = dict(ads.filter(pk__in=[pk for _, kind, pk, _ in valid if kind == 'ad']).values_list('pk', 'user_id'))
    rows = []
    for event_id, kind, pk, action in valid:
        owners = offer_ids if kind == 'offer' else ad_ids
        if pk not in owners or (user and owners[pk] == user.pk):
            continue
        rows.append(PromotionEvent(id=event_id, visitor=visitor, user=user, action=action,
                                   **{kind + '_id': pk}))
    PromotionEvent.objects.bulk_create(rows, ignore_conflicts=True)
    return HttpResponse(status=204)


def summarize(queryset):
    return queryset.annotate(
        measured_views=Count('engagement_events', filter=Q(engagement_events__action='view')),
        measured_clicks=Count('engagement_events', filter=Q(engagement_events__action='click')),
        member_reach=Count('engagement_events__user', distinct=True),
        browser_reach=Count('engagement_events__visitor', distinct=True),
    )


@login_required
@require_GET
def dashboard(request):
    company = owner_shop(request)
    return render(request, 'shop/promotion_metrics.html', {
        'company': company,
        'offers': summarize(LocalOffer.objects.filter(owner=request.user)),
        'ads': summarize(AdPost.objects.filter(user=request.user)),
        'legacy_ads': Advertisement.objects.filter(advertiser__user=request.user),
    })
