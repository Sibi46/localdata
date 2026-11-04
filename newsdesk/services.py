from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
import re
from jobs.models import State, District, PinCode

from .forms import CommentForm, NewsItemForm, RatingForm, ReportForm
from .models import Comment, CommentReport, NewsItem, Rating
from .permissions import active_pincodes, agent_for, is_admin, managed_items, published_items


def valid(form):
    if not form.is_valid():
        raise ValidationError({key: list(errors) for key, errors in form.errors.items()})
    return form.cleaned_data


@transaction.atomic
def save_item(user, data, files=None, pk=None, *, pincode_as_code=False):
    scope = managed_items(user, lock=True)
    item = get_object_or_404(scope.select_for_update(), pk=pk) if pk else NewsItem(author=user)
    original_pin = item.pincode_id
    if pincode_as_code and is_admin(user):
        code = str(data.get('pincode', '')).strip()
        if not re.fullmatch(r'[1-9][0-9]{5}', code):
            raise ValidationError('Enter a valid 6-digit pincode.')
        if not PinCode.objects.filter(code=code).exists():
            # Keep unknown geography explicitly unassigned, rather than inventing a location.
            state, _ = State.objects.get_or_create(code='UNASN', defaults={'name': 'Unassigned geography'})
            district, _ = District.objects.get_or_create(state=state, name='Unassigned district')
            PinCode.objects.get_or_create(code=code, defaults={'district': district})
    form = NewsItemForm(data, files, instance=item, user=user, pincode_as_code=pincode_as_code)
    valid(form)
    item = form.save(commit=False)
    if not is_admin(user):
        item.pincode_id = agent_for(user, lock=True).pincode_id
    if original_pin and original_pin != item.pincode_id:
        raise ValidationError('An existing story cannot be moved to a different pincode.')
    if not active_pincodes().filter(pk=item.pincode_id).exists():
        raise ValidationError('Select an active pincode.')
    if item.status == NewsItem.Status.PUBLISHED and not item.published_at:
        item.published_at = timezone.now()
    item.full_clean()
    item.save()
    return item


def require_resident(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied('Sign in to continue.')


@transaction.atomic
def add_comment(user, pk, data):
    require_resident(user)
    item = get_object_or_404(published_items().select_for_update(), pk=pk)
    if not item.comments_open:
        raise ValidationError('Comments close seven days after publication. Existing comments are still visible.')
    values = valid(CommentForm(data))
    return Comment.objects.create(item=item, user=user, text=values['text'])


@transaction.atomic
def rate_item(user, pk, data):
    require_resident(user)
    item = get_object_or_404(published_items().select_for_update(), pk=pk)
    values = valid(RatingForm(data))
    rating, _ = Rating.objects.update_or_create(item=item, user=user, defaults={'stars': values['stars']})
    return rating


@transaction.atomic
def report_comment(user, pk, data):
    require_resident(user)
    values = valid(ReportForm(data))
    comment = get_object_or_404(Comment, pk=pk, is_hidden=False, item__in=published_items())
    report, created = CommentReport.objects.get_or_create(comment=comment, reporter=user, defaults={'reason': values['reason']})
    return report, created


@transaction.atomic
def moderate_comment(user, pk, action):
    scope = managed_items(user, lock=True)
    comment = get_object_or_404(Comment, pk=pk, item__in=scope)
    # Same locking order as resident writes: item, then comment.
    NewsItem.objects.select_for_update().get(pk=comment.item_id)
    comment = Comment.objects.select_for_update().get(pk=pk)
    if action not in {'hide', 'restore', 'resolve'}:
        raise ValidationError('Choose hide, restore or resolve.')
    if action != 'resolve':
        comment.is_hidden = action == 'hide'
    comment.moderated_by = user
    comment.moderated_at = timezone.now()
    comment.save(update_fields=['is_hidden', 'moderated_by', 'moderated_at'])
    if action in {'hide', 'resolve'}:
        comment.reports.filter(resolved=False).update(resolved=True)
    return comment
