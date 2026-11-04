"""Private notification inbox and header bell feed."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from .models import UserNotification


@never_cache
@login_required
@require_GET
def inbox(request):
    records=UserNotification.objects.filter(user=request.user).order_by('-created_at','-pk')
    unread_only=request.GET.get('unread')=='1'
    unread_count=records.filter(is_read=False).count()
    if unread_only:
        records=records.filter(is_read=False)
    return render(request,'notifications/inbox.html',{'page':Paginator(records,20).get_page(request.GET.get('page')),'unread_count':unread_count,'unread_only':unread_only})


@never_cache
@login_required
@require_GET
def feed(request):
    records=UserNotification.objects.filter(user=request.user)
    return JsonResponse({'unread_count':records.filter(is_read=False).count(),'items':[{
        'id':item.pk,'title':item.title,'message':item.message,'is_read':item.is_read,
        'created_at':item.created_at.isoformat(),'open_url':reverse('notification_open',args=[item.pk]),
    } for item in records.order_by('-created_at','-pk')[:8]]})


@login_required
@require_POST
def open_notification(request, pk):
    item=get_object_or_404(UserNotification,pk=pk,user=request.user)
    if not item.is_read:
        item.is_read=True
        item.save(update_fields=['is_read'])
    target=item.link
    if not target.startswith('/') or not url_has_allowed_host_and_scheme(target,allowed_hosts={request.get_host()},require_https=request.is_secure()):
        target=reverse('notifications')
    return redirect(target)


@login_required
@require_POST
def mark_all_read(request):
    UserNotification.objects.filter(user=request.user,is_read=False).update(is_read=True)
    if request.headers.get('X-Requested-With')=='XMLHttpRequest':
        return JsonResponse({'ok':True,'unread_count':0})
    return redirect('notifications')
