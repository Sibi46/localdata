"""Signed-in readers submit private drafts; existing editors retain publishing rights."""
import uuid

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import caches
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from jobs.models import User, UserNotification
from .models import NewsAgent, NewsItem
from .permissions import active_pincodes, is_admin, published_items
from .public_forms import clean_story
from .uploads import validate_photo


class AccountNewsForm(forms.Form):
    token = forms.UUIDField(widget=forms.HiddenInput)
    body = forms.CharField(label='Your news', max_length=12000, widget=forms.Textarea(attrs={'rows': 7}), help_text='Up to 200 words. An editor will review it before publication.')
    photo = forms.ImageField(label='Photo (optional)', required=False, validators=[validate_photo], widget=forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}))
    accuracy = forms.BooleanField(label='I confirm this news is accurate and I have permission to share it.')

    def clean_body(self):
        return clean_story(self.cleaned_data['body'])


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def share(request):
    pin = active_pincodes().filter(code=request.user.pincode).first()
    tokens = request.session.get('account_news_tokens', [])
    token = str(uuid.uuid4()) if request.method == 'GET' else request.POST.get('token', '')
    if request.method == 'GET':
        tokens = (tokens + [token])[-5:]
        request.session['account_news_tokens'] = tokens
    cache = caches[settings.OTP_CACHE_ALIAS]
    key = f'account-news:{request.user.pk}:{token}'
    if request.method == 'POST' and token in tokens:
        existing = cache.get(key)
        if isinstance(existing, int):
            return redirect('newsdesk:account_submission', pk=existing)
    form = AccountNewsForm(request.POST if request.method == 'POST' else None, request.FILES or None, initial={'token': token})
    if request.method == 'POST' and form.is_valid():
        if not pin:
            form.add_error(None, 'Update your account to an active Local News pincode before submitting.')
        elif token not in tokens:
            form.add_error(None, 'This form has expired. Reload this page before submitting.')
        else:
            existing = cache.get(key)
            if isinstance(existing, int):
                return redirect('newsdesk:account_submission', pk=existing)
            if not cache.add(key, 'processing', timeout=604800):
                form.add_error(None, 'This submission may already be saved. Check your submissions below before retrying.')
            else:
                rate_key = f'account-news-rate:{request.user.pk}'
                allowed = cache.add(rate_key, 1, timeout=3600)
                if not allowed:
                    try:
                        allowed = cache.incr(rate_key) <= 10
                    except ValueError:
                        allowed = False
                if not allowed:
                    cache.delete(key)
                    form.add_error(None, 'You have reached the hourly submission limit. Try again later.')
                    return render(request, 'newsdesk/account_share.html', {
                        'form': form, 'active_pin': pin,
                        'submissions': NewsItem.objects.filter(author=request.user).order_by('-created_at')[:20],
                    }, status=400)
                item = NewsItem(author=request.user, pincode=pin, status=NewsItem.Status.DRAFT,
                                title=form.cleaned_data['body'].splitlines()[0][:180], body=form.cleaned_data['body'])
                saved = False
                try:
                    with transaction.atomic():
                        if form.cleaned_data['photo']:
                            upload = form.cleaned_data['photo']
                            item.photo.save(upload.name, upload, save=False)
                        item.save()
                        agents = set(NewsAgent.objects.filter(pincode=pin, is_active=True, user__is_active=True).values_list('user_id', flat=True))
                        agents.update(user.pk for user in User.objects.filter(is_active=True).filter(
                            Q(is_staff=True) | Q(is_superuser=True) | Q(admin_role='super_admin')) if is_admin(user))
                        UserNotification.objects.bulk_create([UserNotification(user_id=user_id, title='Reader news awaiting review',
                            message='A signed-in reader submitted a private draft. Review it before publishing.',
                            link=reverse('newsdesk:edit', args=[item.pk])) for user_id in agents])
                    saved = True
                    cache.set(key, item.pk, timeout=604800)
                except Exception:
                    if not saved:
                        if item.photo:
                            item.photo.delete(save=False)
                        cache.delete(key)
                    raise
                messages.success(request, 'Your news was sent for review. It will appear publicly only after editor approval.')
                return redirect('newsdesk:account_submission', pk=item.pk)
    return render(request, 'newsdesk/account_share.html', {
        'form': form, 'active_pin': pin,
        'submissions': NewsItem.objects.filter(author=request.user).order_by('-created_at')[:20],
    }, status=400 if request.method == 'POST' and form.errors else 200)


@never_cache
@login_required
@require_GET
def status(request, pk):
    item = get_object_or_404(NewsItem, pk=pk, author=request.user)
    public = published_items().filter(pk=item.pk).exists()
    return render(request, 'newsdesk/account_submission.html', {'item': item, 'public': public})
