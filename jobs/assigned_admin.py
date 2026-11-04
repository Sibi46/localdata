"""Explicitly scoped admin workspace; never grants global staff permissions."""
from datetime import timedelta
from functools import wraps

from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AdminActivity, AdminProfile, PinCode, State, User, UserNotification
from .admin_activity import record_activity

# Model, geographic lookup, title, permitted moderation actions.
SECTIONS = {
    'news': ('News', 'newsdesk.NewsItem', 'pincode__code', 'title', ('publish', 'unpublish')),
    'offers': ('Offers', 'jobs.LocalOffer', 'owner__pincode', 'title', ('activate', 'suspend')),
    'ads': ('Ads', 'jobs.AdPost', 'pincode', 'company_name', ('approve', 'reject')),
    'flicks': ('Flicks', 'jobs.Flick', 'user__pincode', 'title', ('delete',)),
}
SECTION_CHOICES = [(key, value[0]) for key, value in SECTIONS.items()]


class AssignedAdminMiddleware:
    """Fail closed: legacy admin endpoints must not bypass assigned permissions."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated or request.user.admin_role != 'scoped_admin':
            return None
        name = request.resolver_match.url_name
        if getattr(getattr(request.user, 'admin_profile', None), 'hierarchy_level', ''):
            from .admin_hierarchy import authority
            authority(request.user)
            if name not in {'hierarchy_workspace', 'hierarchy_geography', 'hierarchy_toggle', 'hierarchy_support', 'hierarchy_password', 'assigned_dashboard', 'dashboard', 'logout'}:
                if request.method in ('GET', 'HEAD'):
                    return redirect('hierarchy_workspace')
                raise PermissionDenied
            return None
        allowed = {'assigned_dashboard', 'assigned_section', 'assigned_action', 'dashboard', 'logout'}
        if name not in allowed:
            if request.method in ('GET', 'HEAD'):
                return redirect('assigned_dashboard')
            raise PermissionDenied('Use your assigned admin workspace.')


def main_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active or request.user.admin_role != 'super_admin':
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def profile_for(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied
    if user.admin_role == 'super_admin':
        return None
    if user.admin_role != 'scoped_admin':
        raise PermissionDenied
    profile = get_object_or_404(AdminProfile.objects.select_related('state'), user=user, role='scoped_admin', is_active=True)
    if profile.hierarchy_level:
        raise PermissionDenied
    if not profile.all_states and (not profile.state_id or not profile.state.is_active):
        raise PermissionDenied('Your state assignment is unavailable. Contact the Main Super Admin.')
    return profile


def scoped_records(user, section):
    profile = profile_for(user)
    if section not in SECTIONS or (profile and section not in profile.sections):
        raise PermissionDenied('This section has not been assigned to you.')
    _, model, location, _, _ = SECTIONS[section]
    records = apps.get_model(model).objects.all()
    if profile and not profile.all_states:
        pins = PinCode.objects.filter(district__state_id=profile.state_id).values('code')
        records = records.filter(**{location + '__in': pins})
    return records


class ScopeForm(forms.ModelForm):
    sections = forms.MultipleChoiceField(choices=SECTION_CHOICES, required=False, widget=forms.CheckboxSelectMultiple)
    class Meta:
        model = AdminProfile
        fields = ('all_states', 'state', 'sections')
        labels = {'all_states': 'All states / national section admin', 'state': 'Assigned state'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['state'].queryset = State.objects.filter(is_active=True).exclude(code='UNASN')
        self.fields['state'].required = False

    def clean(self):
        data = super().clean()
        if not self.instance.pk and not data.get('sections'):
            self.add_error('sections', 'Enable at least one section for a new admin.')
        if not data.get('all_states') and not data.get('state'):
            self.add_error('state', 'Select a state, or choose all states.')
        if data.get('all_states'):
            data['state'] = None
        return data


class AdminAccountForm(UserCreationForm):
    phone = forms.RegexField(r'^[0-9]{10}$', label='Mobile number (optional)', max_length=10, required=False)
    first_name = forms.CharField(label='Name', max_length=150)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'username', 'phone')

    def clean_username(self):
        username = super().clean_username()
        if User.objects.filter(Q(username__iexact=username) | Q(phone=username) | Q(email__iexact=username) | Q(business_phone=username)).exists():
            raise forms.ValidationError('This username is already used. Choose another one.')
        return username

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if phone and User.objects.filter(Q(username=phone) | Q(phone=phone) | Q(business_phone=phone)).exists():
            raise forms.ValidationError('This mobile number already belongs to an account.')
        return phone


class AdminLoginForm(AuthenticationForm):
    username = forms.CharField(label='Phone number / existing username', widget=forms.TextInput(attrs={'autocomplete': 'username'}))
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.admin_role not in ('super_admin', 'scoped_admin'):
            raise forms.ValidationError('This account does not have access to the admin workspace.')
        if user.admin_role == 'scoped_admin':
            profile = getattr(user, 'admin_profile', None)
            if profile and profile.hierarchy_level:
                from .admin_hierarchy import authority
                try:
                    authority(user)
                except PermissionDenied:
                    raise forms.ValidationError('Your team assignment is unavailable.')
            if not profile or not profile.is_active:
                raise forms.ValidationError('Your admin access is suspended. Contact the Main Super Admin.')


def admin_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = AdminLoginForm(request, data=request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        from .views import _rate_limit, _get_client_ip
        if not _rate_limit(f'assigned_login_{_get_client_ip(request)}', 5, 300):
            form = AdminLoginForm(request, data={})
            form.add_error(None, 'Too many attempts. Please try again in five minutes.')
        elif form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    return render(request, 'assigned_admin/login.html', {'form': form})


def scope_snapshot(profile):
    return {'state': profile.state.name if profile.state_id else '', 'all_states': profile.all_states, 'sections': list(profile.sections), 'active': profile.is_active}


@main_admin_required
def manage_admins(request):
    account_form = AdminAccountForm(request.POST if request.method == 'POST' else None)
    scope_form = ScopeForm(request.POST if request.method == 'POST' else None, initial={'sections': list(SECTIONS)})
    if request.method == 'POST':
        valid_account = account_form.is_valid()
        valid_scope = scope_form.is_valid()
        if valid_account and valid_scope:
            with transaction.atomic():
                user = account_form.save(commit=False)
                user.admin_role = 'scoped_admin'
                user.is_staff = user.is_superuser = False
                user.save()
                profile = scope_form.save(commit=False)
                profile.user = user
                profile.role = 'scoped_admin'
                profile.appointed_by = request.user
                profile.save()
                UserNotification.objects.create(user=user, title='Your admin access is ready', message='Sign in with your username and password to manage your assigned sections.')
                record_activity(request.user, 'team', 'create_admin', user.pk, user.username, {'after': scope_snapshot(profile)})
            messages.success(request, f'Admin created. Login username: {user.username}.')
            return redirect('manage_assigned_admins')
    admins = AdminProfile.objects.filter(role='scoped_admin', hierarchy_level='').select_related('user', 'state')
    for admin in admins:
        admin.section_labels = ', '.join(SECTIONS[s][0] for s in admin.sections if s in SECTIONS)
    return render(request, 'assigned_admin/manage.html', {'account_form': account_form, 'scope_form': scope_form, 'admins': admins})


@main_admin_required
def edit_admin(request, pk):
    profile = get_object_or_404(AdminProfile, pk=pk, hierarchy_level='', role='scoped_admin', user__admin_role='scoped_admin')
    before = scope_snapshot(profile)
    form = ScopeForm(request.POST if request.method == 'POST' else None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
            record_activity(request.user, 'team', 'change_access', profile.user_id, profile.user.username, {'before': before, 'after': scope_snapshot(profile)})
        messages.success(request, 'Admin permissions updated. They apply immediately.')
        return redirect('manage_assigned_admins')
    return render(request, 'assigned_admin/edit.html', {'scope_form': form, 'profile': profile})


@main_admin_required
@require_POST
def toggle_assigned_admin(request, pk):
    with transaction.atomic():
        profile = get_object_or_404(AdminProfile.objects.select_for_update(), pk=pk, hierarchy_level='', role='scoped_admin', user__admin_role='scoped_admin')
        profile.is_active = not profile.is_active
        profile.save(update_fields=['is_active'])
        User.objects.filter(pk=profile.user_id).update(is_active=profile.is_active)
        record_activity(request.user, 'team', 'activate_admin' if profile.is_active else 'suspend_admin', profile.user_id, profile.user.username)
    messages.success(request, 'Admin access updated.')
    return redirect('manage_assigned_admins')


@login_required
def assigned_dashboard(request):
    if getattr(getattr(request.user, 'admin_profile', None), 'hierarchy_level', ''):
        return redirect('hierarchy_workspace')
    profile = profile_for(request.user)
    sections = []
    pending_filters = {'news': {'status': 'draft'}, 'offers': {'is_active': False}, 'ads': {'status': 'pending'}}
    for key, value in SECTIONS.items():
        enabled = profile is None or key in profile.sections
        records = scoped_records(request.user, key) if enabled else None
        sections.append({'key': key, 'name': value[0], 'enabled': enabled,
                         'count': records.count() if enabled else None,
                         'pending': records.filter(**pending_filters[key]).count() if enabled and key in pending_filters else 0})
    recent_activity = AdminActivity.objects.filter(actor=request.user)
    if profile:
        recent_activity = recent_activity.filter(section__in=list(profile.sections) + ['account'])
        recent_activity = recent_activity.filter(state_name=profile.state.name if profile.state_id and not profile.all_states else 'All states')
    return render(request, 'assigned_admin/dashboard.html', {
        'profile': profile, 'sections': sections,
        'enabled_count': sum(item['enabled'] for item in sections),
        'record_count': sum(item['count'] or 0 for item in sections),
        'pending_count': sum(item['pending'] for item in sections),
        'recent_activity': recent_activity[:8],
        'section_nav': [item for item in sections if item['enabled']],
        'notifications': UserNotification.objects.filter(user=request.user)[:5],
    })


@login_required
def assigned_section(request, section):
    records = scoped_records(request.user, section)
    label, _, _, title, actions = SECTIONS[section]
    search = request.GET.get('q', '').strip()[:150]
    if search:
        records = records.filter(**{title + '__icontains': search})
    page = Paginator(records.order_by('-pk'), 25).get_page(request.GET.get('page'))
    for obj in page:
        obj.admin_title = getattr(obj, title) or f'{label} #{obj.pk}'
        obj.admin_status = getattr(obj, 'status', None)
        if obj.admin_status is None:
            obj.admin_status = 'Active' if getattr(obj, 'is_active', True) else 'Suspended'
        obj.admin_detail = getattr(obj, 'body', '') or getattr(obj, 'description', '') or getattr(obj, 'caption', '')
    profile = profile_for(request.user)
    section_nav = [{'key': key, 'name': value[0]} for key, value in SECTIONS.items() if profile is None or key in profile.sections]
    return render(request, 'assigned_admin/section.html', {'page': page, 'section': section, 'label': label, 'actions': actions, 'search': search, 'section_nav': section_nav})


@login_required
@require_POST
@transaction.atomic
def assigned_action(request, section, pk):
    records = scoped_records(request.user, section)
    obj = get_object_or_404(records.select_for_update(), pk=pk)
    action = request.POST.get('action')
    if action not in SECTIONS[section][4]:
        raise PermissionDenied('Unsupported action.')
    target_name = getattr(obj, SECTIONS[section][3]) or f'#{obj.pk}'
    before = {name: getattr(obj, name) for name in ('status', 'is_active', 'is_approved', 'is_verified') if hasattr(obj, name)}
    if section == 'news':
        obj.status = 'published' if action == 'publish' else 'draft'
        try:
            obj.clean()
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
            return redirect('assigned_section', section=section)
        obj.save(update_fields=['status', 'updated_at'])
    elif section == 'ads':
        if obj.status!='pending':
            messages.info(request,'This application has already been reviewed.')
            return redirect('assigned_section',section=section)
        obj.status = 'approved' if action == 'approve' else 'rejected'
        if action == 'approve':
            from .models import AdSettings
            obj.approved_at = timezone.now()
            obj.expires_at = timezone.localdate() + timedelta(days=AdSettings.get().renewal_days)
            obj.reject_note = ''
        obj.save()
        from .admin_messages import send_review_message
        send_review_message(request.user,obj.user,f'Ad {obj.status}',
            f'Your ad "{obj.title or obj.company_name}" has been {obj.status} by an administrator.',
            '/advertise/applications/',notif_type='success' if action=='approve' else 'warning')
    elif section == 'flicks':
        if request.POST.get('confirm') != 'yes':
            raise PermissionDenied('Confirm deletion first.')
        obj.delete()
    else:
        obj.is_active = action in ('activate', 'approve')
        obj.save()
        if section=='offers' and obj.is_active and not before.get('is_active'):
            from .admin_messages import send_review_message
            send_review_message(request.user,obj.owner,'Your offer is approved',
                f'Your offer "{obj.title}" for {obj.business_name} has been approved and is now published.',
                '/employer/dashboard/#offers')
    after = {'deleted': True} if action == 'delete' else {name: getattr(obj, name) for name in before}
    record_activity(request.user, section, action, pk, target_name, {'before': before, 'after': after})
    messages.success(request, 'Saved successfully.')
    return redirect('assigned_section', section=section)


@main_admin_required
def admin_activity(request):
    logs = AdminActivity.objects.all()
    actor = request.GET.get('actor', '').strip()[:150]
    section = request.GET.get('section', '')
    if actor:
        logs = logs.filter(actor_name__icontains=actor)
    if section in SECTIONS or section in ('team', 'account'):
        logs = logs.filter(section=section)
    return render(request, 'assigned_admin/activity.html', {
        'page': Paginator(logs, 40).get_page(request.GET.get('page')),
        'actor_filter': actor, 'section_filter': section,
        'section_choices': [('team', 'Admin permissions'), ('account', 'Sign-ins')] + SECTION_CHOICES,
    })


urlpatterns = [
    path('admin-workspace/login/', admin_login, name='assigned_login'),
    path('super-admin/team/activity/', admin_activity, name='admin_activity'),
    path('super-admin/team/', manage_admins, name='manage_assigned_admins'),
    path('super-admin/team/<int:pk>/edit/', edit_admin, name='edit_assigned_admin'),
    path('super-admin/team/<int:pk>/toggle/', toggle_assigned_admin, name='toggle_assigned_admin'),
    path('admin-workspace/', assigned_dashboard, name='assigned_dashboard'),
    path('admin-workspace/<slug:section>/', assigned_section, name='assigned_section'),
    path('admin-workspace/<slug:section>/<int:pk>/action/', assigned_action, name='assigned_action'),
]
