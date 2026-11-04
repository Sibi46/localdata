"""Fail-closed geography and target policy for retained state-admin routes."""
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Complaint, District, PinCode, User


def state_for(actor):
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied
    if actor.admin_role == 'super_admin':
        return None
    profile = getattr(actor, 'admin_profile', None)
    if (actor.admin_role != 'state_admin' or not profile or not profile.is_active
            or profile.role != 'state_admin' or not profile.state_id or not profile.state.is_active):
        raise PermissionDenied('An active state assignment is required.')
    return profile.state


def manageable_users(actor):
    state = state_for(actor)
    users = User.objects.exclude(pk=actor.pk).filter(is_staff=False, is_superuser=False)
    if state is None:
        return users.exclude(admin_role='super_admin')
    pins = PinCode.objects.filter(district__state=state).values('code')
    return users.filter(
        Q(admin_role='', pincode__in=pins)
        | Q(admin_role='district_admin', admin_profile__role='district_admin',
            admin_profile__state=state, admin_profile__district__state=state)
    ).distinct()


def district_scope(actor):
    if actor.admin_role in {'super_admin', 'state_admin'}:
        return state_for(actor), None
    profile = getattr(actor, 'admin_profile', None)
    if (not actor.is_active or actor.admin_role != 'district_admin' or not profile
            or not profile.is_active or profile.role != 'district_admin'
            or not profile.district_id or not profile.district.is_active
            or profile.state_id != profile.district.state_id or not profile.state.is_active):
        raise PermissionDenied('An active district assignment is required.')
    return profile.state, profile.district


def district_users(actor):
    state, district = district_scope(actor)
    users = User.objects.filter(admin_role='', is_staff=False, is_superuser=False)
    if district:
        users = users.filter(pincode__in=PinCode.objects.filter(district=district).values('code'))
    elif state:
        users = users.filter(pincode__in=PinCode.objects.filter(district__state=state).values('code'))
    return users


def district_complaints(actor):
    state, district = district_scope(actor)
    complaints = Complaint.objects.all()
    if district:
        return complaints.filter(district=district)
    if state:
        return complaints.filter(district__state=state)
    return complaints
