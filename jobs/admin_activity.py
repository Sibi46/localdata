"""Activity history stores names and moderation changes, never credentials."""
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import AdminActivity


def record_activity(user, section, action, target_id='', target_name='', details=None, state_name=None):
    if state_name is None:
        profile = getattr(user, 'admin_profile', None)
        state_name = (profile.state.name if profile and profile.state_id and not profile.all_states else 'All states')
    return AdminActivity.objects.create(
        actor=user, actor_name=user.username, section=section, action=action,
        target_id=str(target_id), target_name=str(target_name)[:250],
        state_name=state_name, details=details or {},
    )


@receiver(user_logged_in, dispatch_uid='assigned_admin_login_activity')
def admin_logged_in(sender, request, user, **kwargs):
    if user.admin_role in ('super_admin', 'scoped_admin') and user.is_active:
        record_activity(user, 'account', 'login')
