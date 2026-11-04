from django.core.exceptions import PermissionDenied

from jobs.models import PinCode
from .models import NewsAgent, NewsItem


def active_pincodes():
    return PinCode.objects.filter(is_active=True, district__is_active=True, district__state__is_active=True).order_by('code')


def is_admin(user):
    return bool(user.is_authenticated and user.is_active and (
        user.is_superuser or user.admin_role == 'super_admin' or
        (user.is_staff and user.has_perm('newsdesk.manage_newsdesk'))))


def agent_for(user, lock=False):
    if not user.is_authenticated or not user.is_active:
        return None
    query = NewsAgent.objects.select_for_update() if lock else NewsAgent.objects.all()
    return query.filter(user=user, is_active=True, pincode__in=active_pincodes()).first()


def managed_items(user, lock=False):
    if is_admin(user):
        return NewsItem.objects.all()
    agent = agent_for(user, lock=lock)
    if not agent:
        raise PermissionDenied('An active News Agent assignment is required.')
    return NewsItem.objects.filter(pincode_id=agent.pincode_id)


def published_items():
    from django.utils import timezone
    return NewsItem.objects.filter(status=NewsItem.Status.PUBLISHED, published_at__lte=timezone.now(), pincode__in=active_pincodes())
