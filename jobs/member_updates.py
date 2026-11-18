"""Account announcements, aggregate product views and audited shop-chat review."""
import uuid
from itertools import islice
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from .models import (AdminAnnouncement, CompanyProfile, Conversation,
    ConversationAdminAccess, Product, ProductVisit, User, UserNotification)
from .pilot_admin import private


class AnnouncementForm(forms.Form):
    title = forms.CharField(max_length=160)
    message = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={'rows': 5}))
    submission_id = forms.UUIDField(widget=forms.HiddenInput)


@private
@require_http_methods(['GET', 'POST'])
def announcements(request):
    form = AnnouncementForm(request.POST if request.method == 'POST' else None,
                            initial={'submission_id': uuid.uuid4()})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            item, created = AdminAnnouncement.objects.get_or_create(
                submission_id=form.cleaned_data['submission_id'], defaults={
                    'author': request.user, 'title': form.cleaned_data['title'],
                    'message': form.cleaned_data['message']})
            if created:
                members = User.objects.filter(is_active=True, is_staff=False,
                    is_superuser=False, admin_role='').values_list('pk', flat=True).iterator(chunk_size=500)
                while batch := list(islice(members, 500)):
                    UserNotification.objects.bulk_create([UserNotification(
                        user_id=pk, title=item.title, message=item.message,
                        announcement=item, link=reverse('member_announcement', args=[item.pk]))
                        for pk in batch], batch_size=500)
        return redirect('admin_announcement', pk=item.pk)
    records = AdminAnnouncement.objects.annotate(sent=Count('notifications'),
        opened=Count('notifications', filter=Q(notifications__opened_at__isnull=False))).order_by('-pk')
    return render(request, 'member_updates/announcements.html', {'form': form,
        'page': Paginator(records, 20).get_page(request.GET.get('page')), 'tab': 'announcements'})


@private
@require_GET
def announcement_report(request, pk):
    item = get_object_or_404(AdminAnnouncement, pk=pk)
    records = item.notifications.select_related('user').order_by('user_id')
    sent = records.count()
    opened = records.filter(opened_at__isnull=False).count()
    return render(request, 'member_updates/announcement_report.html', {'item': item,
        'sent': sent, 'opened': opened, 'unopened': sent-opened, 'tab': 'announcements',
        'page': Paginator(records, 50).get_page(request.GET.get('page'))})


@never_cache
@login_required
@require_GET
def member_announcement(request, pk):
    notice = get_object_or_404(UserNotification.objects.select_related('announcement'),
                             user=request.user, announcement_id=pk)
    UserNotification.objects.filter(pk=notice.pk, opened_at__isnull=True).update(
        opened_at=timezone.now(), is_read=True)
    UserNotification.objects.filter(pk=notice.pk, is_read=False).update(is_read=True)
    return render(request, 'member_updates/announcement.html', {'item': notice.announcement})


def record_product_view(request, product):
    user = request.user
    if (request.method != 'GET' or not user.is_authenticated or not user.is_active
        or user.pk == product.shop.user_id or user.is_staff or user.is_superuser or user.admin_role
        or request.headers.get('DNT') == '1' or request.headers.get('Sec-GPC') == '1'):
        return
    visit, created = ProductVisit.objects.get_or_create(product=product, viewer=user)
    if not created:
        ProductVisit.objects.filter(pk=visit.pk).update(view_count=F('view_count')+1,
                                                       last_seen=timezone.now())


@never_cache
@login_required
@require_GET
def product_insights(request):
    shop = get_object_or_404(CompanyProfile, user=request.user)
    return insights(request, shop, False)


def insights(request, shop, admin):
    products = Product.objects.filter(shop=shop).annotate(
        members=Count('member_visits'), opens=Sum('member_visits__view_count')).order_by('-opens', '-pk')
    totals = ProductVisit.objects.filter(product__shop=shop).aggregate(
        members=Count('viewer', distinct=True), opens=Sum('view_count'))
    return render(request, 'member_updates/product_insights.html', {'shop': shop,
        'totals': totals, 'admin_view': admin, 'tab': 'insights',
        'page': Paginator(products, 30).get_page(request.GET.get('page'))})


@private
@require_GET
def shop_insights(request):
    shops = CompanyProfile.objects.select_related('user').annotate(
        members=Count('products__member_visits__viewer', distinct=True),
        opens=Sum('products__member_visits__view_count')).order_by('-opens', '-pk')
    return render(request, 'member_updates/shop_insights.html', {'tab': 'insights',
        'page': Paginator(shops, 30).get_page(request.GET.get('page'))})


@private
@require_GET
def admin_product_insights(request, pk):
    return insights(request, get_object_or_404(CompanyProfile, pk=pk), True)


def shop_threads():
    return Conversation.objects.filter(Q(user_a__company__isnull=False) |
        Q(user_b__company__isnull=False)).select_related('user_a', 'user_b').distinct()


@private
@require_GET
def conversations(request):
    records = shop_threads().annotate(message_count=Count('messages')).order_by('-updated_at', '-pk')
    return render(request, 'member_updates/conversations.html', {'tab': 'conversations',
        'page': Paginator(records, 30).get_page(request.GET.get('page'))})


@private
@require_GET
def conversation_review(request, pk):
    thread = get_object_or_404(shop_threads(), pk=pk)
    ConversationAdminAccess.objects.create(admin=request.user, conversation=thread)
    records = thread.messages.select_related('sender').order_by('-sent_at', '-pk')
    return render(request, 'member_updates/conversation.html', {'thread': thread,
        'tab': 'conversations', 'page': Paginator(records, 50).get_page(request.GET.get('page'))})
