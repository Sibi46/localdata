"""Instagram profile link and the optional follow invitation preference."""
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET,require_POST
from .models import LocalFromFollow


@never_cache
@require_GET
def profile(request):
    return redirect(settings.LOCAL_FROM_INSTAGRAM_URL)


@login_required
@require_POST
def follow(request):
    action=request.POST.get('action')
    if action=='follow':
        # Opening Instagram does not confirm that someone followed the account.
        return redirect(settings.LOCAL_FROM_INSTAGRAM_URL)
    if action!='dismiss':return HttpResponseBadRequest('Choose follow or not now.')
    with transaction.atomic():
        preference,_=LocalFromFollow.objects.get_or_create(user=request.user)
        LocalFromFollow.objects.filter(pk=preference.pk).update(prompt_dismissed=True)
    target=request.POST.get('next','/')
    if not url_has_allowed_host_and_scheme(target,allowed_hosts={request.get_host()},require_https=request.is_secure()):target='/'
    return redirect(target)
