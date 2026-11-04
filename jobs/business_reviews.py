"""Customer reviews and monthly review snapshots."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import BusinessReview, CompanyProfile


def snapshot(reviews):
    stats = reviews.aggregate(count=Count('pk'), average=Avg('rating'))
    if not stats['count']:
        return 'No customer reviews yet.'
    positive = reviews.filter(rating__gte=4).count()
    critical = reviews.filter(rating__lte=2).count()
    return (f"{stats['count']} customer reviews; average {stats['average']:.1f}/5. "
            f"{positive} rated 4 or 5 stars; {critical} rated 1 or 2 stars.")


def badge(user):
    count = BusinessReview.objects.filter(user=user).count()
    return 'Community Expert' if count >= 10 else 'Local Guide' if count >= 3 else 'Community Reviewer'


@login_required
@require_POST
def submit_review(request, company_id):
    company = get_object_or_404(CompanyProfile, company_id=company_id, user__is_active=True)
    target = company.get_absolute_url() + '#customer-reviews'
    if company.user_id == request.user.pk:
        messages.error(request, 'You cannot review your own business.')
        return redirect(target)
    try:
        rating = int(request.POST.get('rating', ''))
    except (TypeError, ValueError):
        rating = 0
    text = request.POST.get('text', '').strip()
    if rating not in range(1, 6) or not 10 <= len(text) <= 2000:
        messages.error(request, 'Choose 1–5 stars and write a review of 10–2000 characters.')
        return redirect(target)
    with transaction.atomic():
        review, created = BusinessReview.objects.update_or_create(
            company=company, user=request.user, defaults={'rating': rating, 'text': text})
    messages.success(request, f'Review saved. Your badge: {badge(request.user)}.')
    return redirect(target)
