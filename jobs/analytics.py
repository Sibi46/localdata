"""First-party page and control analytics; form values and IP addresses are never stored."""
import json
import re
import uuid
import time
from contextlib import nullcontext
from threading import Lock
from datetime import timedelta
from urllib.parse import urlsplit
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.signing import BadSignature
from django.db import transaction,connection,OperationalError
from django.db.models import Count,Max,Q,Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse,JsonResponse
from django.shortcuts import render
from django.urls import Resolver404,resolve
from django.utils import timezone
from django.views.decorators.http import require_GET,require_POST
from .models import AnalyticsEvent,AnalyticsVisit,AnalyticsVisitor,CompanyProfile,User
from .pilot_admin import private

COOKIE='lf_visitor'
SALT='local-from-analytics'
SQLITE_WRITE_LOCK=Lock()
EXCLUDED=('/admin/','/super-admin/','/admin-panel/','/admin-workspace/','/district-admin/','/analytics/','/api/','/static/','/media/')
PRIVATE_PATHS=('/messages/','/notifications/','/reset-password/','/forgot-password/','/account/','/profile/')
PAGE_NAMES={'/':'Home','/products/':'Products','/businesses/':'Shops','/advertise/':'Offers','/news/':'News','/register/':'Create account','/login/':'Sign in','/account/':'My account','/employer/dashboard/':'Shop dashboard','/business/create/':'Register a shop','/flicks/':'Videos','/messages/':'Messages','/forgot-password/':'Password recovery','/reset-password/':'Set password','/profile/':'My profile','/about/':'About Local From','/privacy/':'Privacy policy','/terms/':'Terms'}


def page_name(path):
    if path in PAGE_NAMES:return PAGE_NAMES[path]
    if path.startswith('/business/'):return 'Shop profile'
    if path.startswith('/products/'):return 'Product details'
    if path.startswith('/shop/'):return 'Manage shop'
    return path


def excluded(request,include_path=True):
    return bool(getattr(request.user,'admin_role','') or (include_path and request.path.startswith(EXCLUDED)) or re.search(r'bot|spider|crawler',request.headers.get('User-Agent',''),re.I))


def visitor_id(request):
    try:return uuid.UUID(request.get_signed_cookie(COOKIE,salt=SALT,max_age=31536000))
    except (KeyError,ValueError,TypeError,BadSignature):return None


def clean_path(value):
    if not isinstance(value,str) or not value.startswith('/') or value.startswith('//'):return ''
    path=urlsplit(value).path[:200]
    if path.startswith(EXCLUDED) or any(ord(char)<32 for char in path):return ''
    for prefix in PRIVATE_PATHS:
        if path.startswith(prefix):return prefix
    try:resolve(path)
    except Resolver404:return '/unknown/'
    return path


def clean_target(value):
    if not isinstance(value,str):return ''
    if value.startswith('/') and not value.startswith('//'):return clean_path(value)
    try:
        parsed=urlsplit(value)
        if parsed.scheme in ('http','https') and parsed.hostname:return 'outbound:'+parsed.hostname[:100]
        if parsed.scheme in ('mailto','tel'):return 'contact:'+parsed.scheme
    except ValueError:pass
    return ''


def safe_label(value):
    if not isinstance(value,str):return ''
    value=' '.join(value.split())[:80]
    value=re.sub(r'\b\d{6,}\b','[number]',value)
    return re.sub(r'\S+@\S+','[email]',value)


@require_POST
def collect(request):
    if not getattr(settings,'LOCAL_ANALYTICS_ENABLED',True):return HttpResponse(status=204)
    if excluded(request,include_path=False) or request.headers.get('DNT')=='1' or request.headers.get('Sec-GPC')=='1':return HttpResponse(status=204)
    if request.content_type!='application/x-www-form-urlencoded':return HttpResponse(status=415)
    identity=visitor_id(request)
    if identity is None:return JsonResponse({'error':'Open a site page first.'},status=400)
    if len(request.body)>20000:return JsonResponse({'error':'Batch too large.'},status=413)
    try:
        payload=json.loads(request.POST.get('events','[]'))
        seconds=max(0,min(25,float(request.POST.get('seconds',0))))
        if not isinstance(payload,list) or len(payload)>30:raise ValueError()
    except (ValueError,TypeError):return JsonResponse({'error':'Invalid analytics batch.'},status=400)
    # The collector itself is excluded from page tracking, but visitors may post here.
    path=clean_path(request.POST.get('path',''))
    if not path:return JsonResponse({'error':'Invalid page.'},status=400)
    rate_key='analytics-rate:'+str(identity)
    if not cache.add(rate_key,1,60):
        try:
            if cache.incr(rate_key)>90:return HttpResponse(status=429)
        except ValueError:cache.set(rate_key,1,60)
    events=[]
    for item in payload:
        if not isinstance(item,dict) or item.get('type') not in ('pageview','click','submit'):continue
        try:event_id=uuid.UUID(str(item.get('id','')))
        except (ValueError,TypeError):continue
        event_path=clean_path(item.get('path',path))
        if not event_path or (event_path in ('/messages/','/notifications/') and item['type']!='pageview'):continue
        events.append((event_id,item['type'],event_path,safe_label(item.get('label','')),clean_target(item.get('target',''))))
    # SQLite cannot upgrade simultaneous read transactions to writes. Keep
    # analytics writes serial locally, and retry short collisions with page saves.
    lock=SQLITE_WRITE_LOCK if connection.vendor=='sqlite' else nullcontext()
    with lock:
        for attempt in range(4):
            try:
                _write_batch(request,identity,path,events,seconds)
                return HttpResponse(status=204)
            except OperationalError as error:
                if 'locked' not in str(error).lower() or attempt==3:
                    return HttpResponse(status=503)
                time.sleep(.03*(2**attempt))
    return HttpResponse(status=503)


def _write_batch(request,identity,path,events,seconds):
    now=timezone.now()
    user=request.user if request.user.is_authenticated else None
    with transaction.atomic():
        visitor,_=AnalyticsVisitor.objects.get_or_create(pk=identity,defaults={'last_seen':now})
        visitor=AnalyticsVisitor.objects.select_for_update().get(pk=visitor.pk)
        visit=visitor.visits.filter(ended_at__isnull=True,last_seen__gte=now-timedelta(minutes=30)).order_by('-last_seen').first()
        if visit and visit.user_id and visit.user_id!=getattr(user,'pk',None):
            visit.ended_at=now;visit.save(update_fields=['ended_at']);visit=None
        if visit is None:
            device=request.POST.get('device','desktop')
            if device not in ('mobile','tablet','desktop'):device='desktop'
            source='Direct'
            try:
                referrer=urlsplit(request.POST.get('referrer',''))
                if referrer.scheme in ('http','https') and referrer.hostname and referrer.hostname!=request.get_host().split(':')[0]:source=referrer.hostname[:100]
            except ValueError:pass
            visit=AnalyticsVisit.objects.create(visitor=visitor,user=user,last_seen=now,engagement_updated_at=now,device=device,source=source,current_path=path)
        else:
            if user:visit.user=user
            elapsed=max(0,(now-visit.engagement_updated_at).total_seconds())
            visit.engaged_seconds+=int(min(seconds,elapsed))
            visit.engagement_updated_at=now
            visit.last_seen=now;visit.current_path=path
            visit.save(update_fields=['user','engaged_seconds','engagement_updated_at','last_seen','current_path'])
        AnalyticsEvent.objects.bulk_create([
            AnalyticsEvent(id=event_id,visit=visit,event_type=event_type,path=event_path,label=label if event_type!='pageview' else '',target=target if event_type!='pageview' else '')
            for event_id,event_type,event_path,label,target in events
        ],ignore_conflicts=True)
        visitor.last_seen=now;visitor.save(update_fields=['last_seen'])



def live_data():
    active=AnalyticsVisit.objects.filter(last_seen__gte=timezone.now()-timedelta(seconds=60),ended_at__isnull=True)
    return {'active':active.values('visitor_id').distinct().count(),'members':active.exclude(user=None).values('user_id').distinct().count(),'guests':active.filter(user=None).values('visitor_id').distinct().count()}


@private
@require_GET
def live(request):
    data=live_data()
    active=AnalyticsVisit.objects.filter(last_seen__gte=timezone.now()-timedelta(seconds=60),ended_at__isnull=True).select_related('user').order_by('-last_seen')[:20]
    data['visitors']=[{'name':(visit.user.get_full_name() or visit.user.username) if visit.user else 'Guest browser','path':page_name(visit.current_path),'device':visit.device.title(),'last':timezone.localtime(visit.last_seen).strftime('%H:%M:%S')} for visit in active]
    return JsonResponse(data)


@private
@require_GET
def activity(request):
    period=request.GET.get('period','30')
    if period not in ('today','7','30','all'):period='30'
    events=AnalyticsEvent.objects.select_related('visit__user').order_by('-created_at')
    if period!='all':
        days=1 if period=='today' else int(period)
        start=timezone.localtime().replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=days-1)
        events=events.filter(created_at__gte=start)
    query=request.GET.get('q','').strip()[:100]
    kind=request.GET.get('type','')
    if kind not in ('pageview','click','submit'):kind=''
    if kind:events=events.filter(event_type=kind)
    if query:events=events.filter(Q(path__icontains=query)|Q(label__icontains=query)|Q(visit__user__first_name__icontains=query)|Q(visit__user__last_name__icontains=query))
    return render(request,'pilot_admin/analytics_activity.html',{'tab':'analytics','period':period,'q':query,'kind':kind,'page':Paginator(events,50).get_page(request.GET.get('page')),'filter_query':urlencode({'period':period,'q':query,'type':kind})})


@private
@require_GET
def dashboard(request):
    period=request.GET.get('period','today')
    if period not in ('today','7','30'):period='today'
    days=1 if period=='today' else int(period)
    start=timezone.localtime().replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=days-1)
    events=AnalyticsEvent.objects.filter(created_at__gte=start)
    visits=AnalyticsVisit.objects.filter(last_seen__gte=start)
    summary={
        'visitors':visits.values('visitor_id').distinct().count(),
        'members':visits.exclude(user=None).values('user_id').distinct().count(),
        'visits':visits.count(),'views':events.filter(event_type='pageview').count(),
        'clicks':events.filter(event_type='click').count(),'submits':events.filter(event_type='submit').count(),
    }
    total_seconds=visits.aggregate(total=Sum('engaged_seconds'))['total'] or 0
    average=total_seconds//max(summary['visits'],1)
    summary['average_time']=f'{average//60}m {average%60}s'
    daily={row['day']:row for row in events.annotate(day=TruncDate('created_at')).values('day').annotate(views=Count('id',filter=Q(event_type='pageview')),clicks=Count('id',filter=Q(event_type='click')))}
    chart=[]
    for offset in range(days):
        day=(start+timedelta(days=offset)).date()
        chart.append({'day':day,**daily.get(day,{'views':0,'clicks':0})})
    maximum=max([max(row['views'],row['clicks']) for row in chart]+[1])
    for row in chart:
        row['view_width']=round(row['views']/maximum*100);row['click_width']=round(row['clicks']/maximum*100)
    pages=events.values('path').annotate(views=Count('id',filter=Q(event_type='pageview')),clicks=Count('id',filter=Q(event_type='click'))).order_by('-views','-clicks')[:15]
    controls=events.filter(event_type='click').values('label','path','target').annotate(total=Count('id')).order_by('-total')[:20]
    members=events.exclude(visit__user=None).values('visit__user_id','visit__user__first_name','visit__user__last_name','visit__user__username').annotate(views=Count('id',filter=Q(event_type='pageview')),clicks=Count('id',filter=Q(event_type='click')),last=Max('created_at')).order_by('-clicks','-views')[:15]
    for member in members:member['name']=' '.join(filter(None,[member['visit__user__first_name'],member['visit__user__last_name']])) or member['visit__user__username']
    return render(request,'pilot_admin/analytics.html',{
        'tab':'analytics','period':period,'summary':summary,'live':live_data(),'chart':chart,'pages':pages,'controls':controls,'members':members,
        'devices':visits.values('device').annotate(total=Count('id')).order_by('-total'),
        'sources':visits.values('source').annotate(total=Count('id')).order_by('-total')[:10],
        'recent':events.select_related('visit__user').order_by('-created_at')[:40],
        'active_visits':AnalyticsVisit.objects.filter(last_seen__gte=timezone.now()-timedelta(seconds=60),ended_at__isnull=True).select_related('user').order_by('-last_seen')[:20],
        'registered_members':User.objects.filter(is_active=True,admin_role='').count(),
        'registered_shops':CompanyProfile.objects.filter(user__is_active=True).count(),
        'tracking_since':AnalyticsEvent.objects.order_by('created_at').values_list('created_at',flat=True).first(),
    })
