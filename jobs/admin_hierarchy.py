"""Location-scoped admin team hierarchy. Legacy scoped permissions remain separate."""
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Country, State, District, PinCode, AdminProfile, User, Complaint, AdminActivity, UserNotification
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q, Count
from .admin_activity import record_activity

NEXT = {'country': ['state'], 'state': ['district'], 'district': ['area'], 'area': ['salesman'], 'it': [], 'salesman': []}


def authority(user):
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied
    if user.admin_role == 'super_admin':
        return None
    profile = AdminProfile.objects.filter(user=user).first()
    if user.admin_role != 'scoped_admin' or not profile or not profile.hierarchy_level:
        raise PermissionDenied
    current = profile
    seen = set()
    while current:
        if current.pk in seen or not current.is_active or not current.user.is_active or current.user.admin_role != 'scoped_admin' or current.hierarchy_level not in NEXT:
            raise PermissionDenied('This team assignment is suspended.')
        seen.add(current.pk)
        if not current.country_id or not current.country.is_active:
            raise PermissionDenied('Country assignment unavailable.')
        if current.hierarchy_level != 'country':
            if not current.state_id or not current.state.is_active or current.state.country_id != current.country_id:
                raise PermissionDenied('State assignment unavailable.')
        if current.hierarchy_level in ('district', 'area', 'salesman'):
            if not current.district_id or not current.district.is_active or current.district.state_id != current.state_id:
                raise PermissionDenied('District assignment unavailable.')
        if current.hierarchy_level in ('area', 'salesman'):
            if not current.area_id or not current.area.is_active or current.area.district_id != current.district_id:
                raise PermissionDenied('Area assignment unavailable.')
        parent = current.appointed_by
        if not parent or not parent.is_active:
            raise PermissionDenied('Parent admin unavailable.')
        if parent.admin_role == 'super_admin':
            break
        ancestor = getattr(parent, 'admin_profile', None)
        if not ancestor or current.hierarchy_level not in NEXT.get(ancestor.hierarchy_level, []):
            raise PermissionDenied('Invalid admin hierarchy.')
        for field in ('country_id', 'state_id', 'district_id', 'area_id'):
            value = getattr(ancestor, field)
            if value and value != getattr(current, field):
                raise PermissionDenied('Assignment is outside the parent area.')
        current = ancestor
    return profile


def visible_team(user):
    profile = authority(user)
    qs = AdminProfile.objects.exclude(hierarchy_level='').select_related('user', 'country', 'state', 'district', 'area', 'appointed_by')
    if profile is None:
        return qs
    if profile.hierarchy_level in ('it', 'salesman'):
        return qs.none()
    # Traverse actual appointment ancestry, not merely coincident locations.
    ids, frontier = [], [user.pk]
    for _ in range(5):
        children = list(qs.filter(appointed_by_id__in=frontier).values_list('pk', 'user_id'))
        ids.extend(pk for pk, uid in children)
        frontier = [uid for pk, uid in children]
        if not frontier:
            break
    qs = qs.filter(pk__in=ids)
    for field in ('country_id', 'state_id', 'district_id', 'area_id'):
        if getattr(profile, field):
            qs = qs.filter(**{field: getattr(profile, field)})
    return qs


class PhoneAccountForm(forms.Form):
    phone = forms.RegexField(r'^[0-9]{10}$', label='Phone number', max_length=10,
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'off'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if User.objects.filter(Q(phone=phone) | Q(username__iexact=phone) | Q(business_phone=phone) | Q(email__iexact=phone)).exists():
            raise forms.ValidationError('This phone number already belongs to an account.')
        return phone

    def clean(self):
        data = super().clean()
        if data.get('password'):
            validate_password(data['password'], User(username=data.get('phone', ''), phone=data.get('phone', ''), email=data.get('email', '')))
        return data

    def save(self, commit=True):
        user = User(username=self.cleaned_data['phone'], phone=self.cleaned_data['phone'], email=self.cleaned_data.get('email', ''))
        user.set_password(self.cleaned_data['password'])
        if commit: user.save()
        return user


class CountryAccountForm(PhoneAccountForm):
    email = forms.EmailField(label='Email address', max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    field_order = ['phone', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            raise forms.ValidationError('This email address already belongs to an account.')
        return email


class TeamFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Search country or phone', max_length=100)
    country = forms.ModelChoiceField(Country.objects.all().order_by('name'), required=False, empty_label='All countries')
    state = forms.ModelChoiceField(State.objects.none(), required=False, empty_label='All states')
    district = forms.ModelChoiceField(District.objects.none(), required=False, empty_label='All districts')
    area = forms.RegexField(r'^[1-9][0-9]{5}$', required=False, label='PIN code',
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'maxlength': '6', 'placeholder': 'Enter 6-digit PIN code'}),
        error_messages={'invalid': 'Enter a valid 6-digit PIN code.'})

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        profile = authority(actor)
        for name, parent, lookup in [('country', None, None), ('state', 'country', 'country_id'), ('district', 'state', 'state_id')]:
            field = self.fields[name]
            if profile and getattr(profile, name + '_id'):
                field.queryset = field.queryset.model.objects.filter(pk=getattr(profile, name + '_id'))
                field.initial = getattr(profile, name + '_id')
                field.disabled = True
            elif parent:
                parent_id = getattr(profile, parent + '_id', None) if profile else None
                raw = parent_id or self.data.get(parent, '')
                if str(raw).isdigit() and self.fields[parent].queryset.filter(pk=raw).exists():
                    field.queryset = field.queryset.model.objects.filter(**{lookup: raw}).order_by('code' if name == 'area' else 'name')

        self.fields['state'].queryset = self.fields['state'].queryset.exclude(code='UNASN')
        self.fields['district'].queryset = self.fields['district'].queryset.exclude(state__code='UNASN').exclude(name='Unassigned district')
        if profile and profile.area_id:
            self.fields['area'].initial = profile.area.code
            self.fields['area'].disabled = True



def team_overview(request):
    form = TeamFilterForm(request.GET, actor=request.user, auto_id='filter_%s')
    team = visible_team(request.user)
    if form.is_valid():
        for name in ('country', 'state', 'district'):
            if form.cleaned_data.get(name):
                team = team.filter(**{name: form.cleaned_data[name]})
        if form.cleaned_data.get('area'):
            team = team.filter(area__code=form.cleaned_data['area'])
        q = form.cleaned_data.get('q')
        if q: team = team.filter(Q(country__name__icontains=q) | Q(user__phone__icontains=q) | Q(user__username__icontains=q))
    else:
        team = team.none()
    totals = dict(team.values('hierarchy_level').annotate(total=Count('pk')).values_list('hierarchy_level', 'total'))
    return form, team, [{'label': label, 'total': totals.get(key, 0)} for key, label in AdminProfile.HIERARCHY_CHOICES]


class AssignmentForm(forms.Form):
    level = forms.ChoiceField(label='Role')
    country = forms.ModelChoiceField(queryset=Country.objects.filter(is_active=True).order_by('name'), required=False)
    state = forms.ModelChoiceField(queryset=State.objects.filter(is_active=True).exclude(code='UNASN'), required=False)
    district = forms.ModelChoiceField(queryset=District.objects.filter(is_active=True).exclude(state__code='UNASN').exclude(name='Unassigned district'), required=False)
    area = forms.ModelChoiceField(
        queryset=PinCode.objects.filter(is_active=True).exclude(district__state__code='UNASN').exclude(district__name='Unassigned district'),
        required=False, label='Area / PIN code', to_field_name='code',
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'maxlength': '6', 'placeholder': 'Enter 6-digit PIN code'}),
        error_messages={'invalid_choice': 'Enter an active PIN code mapped to your assigned district. Unmapped PIN codes need location mapping first.'})

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.parent = authority(actor)
        levels = NEXT[self.parent.hierarchy_level] if self.parent else ['country', 'it']
        self.fields['level'].choices = [(k, v) for k, v in AdminProfile.HIERARCHY_CHOICES if k in levels]
        if self.parent:
            for field in ('country', 'state', 'district', 'area'):
                obj = getattr(self.parent, field)
                if obj:
                    self.fields[field].queryset = self.fields[field].queryset.filter(pk=obj.pk)
                    self.fields[field].initial = obj
                    self.fields[field].disabled = True
            self.fields['state'].queryset = self.fields['state'].queryset.filter(country_id=self.parent.country_id)
            self.fields['district'].queryset = self.fields['district'].queryset.filter(state__country_id=self.parent.country_id)
            self.fields['area'].queryset = self.fields['area'].queryset.filter(district__state__country_id=self.parent.country_id)
            if self.parent.state_id:
                self.fields['district'].queryset = self.fields['district'].queryset.filter(state_id=self.parent.state_id)
                self.fields['area'].queryset = self.fields['area'].queryset.filter(district__state_id=self.parent.state_id)
            if self.parent.district_id:
                self.fields['area'].queryset = self.fields['area'].queryset.filter(district_id=self.parent.district_id)

    def clean(self):
        d = super().clean()
        level = d.get('level')
        required = ['country']
        if level != 'country': required += ['state']
        if level in ('district', 'area', 'salesman'): required += ['district']
        if level in ('area', 'salesman'): required += ['area']
        for name in required:
            if not d.get(name): self.add_error(name, 'Choose the assigned location.')
        for name in ('state', 'district', 'area'):
            if name not in required: d[name] = None
        if d.get('state') and d['state'].country_id != getattr(d.get('country'), 'pk', None):
            self.add_error('state', 'State must belong to the selected country.')
        if d.get('district') and d['district'].state_id != getattr(d.get('state'), 'pk', None):
            self.add_error('district', 'District must belong to the selected state.')
        if d.get('area') and d['area'].district_id != getattr(d.get('district'), 'pk', None):
            self.add_error('area', 'PIN code must belong to the selected district.')
        if level == 'it' and d.get('state') and AdminProfile.objects.filter(hierarchy_level='it', state=d['state']).exists():
            self.add_error('state', 'This state already has an IT admin. Manage that existing account.')
        return d


@login_required
def state_choices(request):
    from django.http import JsonResponse
    if authority(request.user) is not None:
        raise PermissionDenied
    country = request.GET.get('country', '')
    states = State.objects.filter(country_id=country, country__is_active=True, is_active=True).exclude(code='UNASN').order_by('name') if country.isdigit() else State.objects.none()
    return JsonResponse({'states': list(states.values('id', 'name'))})


@login_required
def workspace(request):
    profile = authority(request.user)
    can_create = profile is None or bool(NEXT[profile.hierarchy_level])
    country_creation = profile is None and (request.POST.get('level') == 'country' if request.method == 'POST' else request.GET.get('create') != 'it')
    account = (CountryAccountForm if country_creation else PhoneAccountForm)(request.POST or None)
    assignment = AssignmentForm(request.POST or None, actor=request.user)
    level = NEXT[profile.hierarchy_level][0] if profile and can_create else ('it' if request.GET.get('create') == 'it' else 'country')
    create_label = 'Create ' + dict(AdminProfile.HIERARCHY_CHOICES)[level]
    assignment.fields['level'].initial = level
    assignment.fields['level'].widget = forms.HiddenInput()
    needed = {'country': ['country'], 'state': ['state'], 'district': ['district'], 'area': ['area'], 'salesman': [], 'it': ['country', 'state']}[level]
    for name in ('country', 'state', 'district', 'area'):
        if name not in needed:
            assignment.fields[name].widget = forms.HiddenInput()
    # IT state choices follow the selected country on POST, validated again in clean().
    if level == 'it':
        raw_country = request.POST.get('country') if request.method == 'POST' else request.GET.get('country')
        assignment.fields['state'].queryset = State.objects.filter(is_active=True, country_id=raw_country).exclude(code='UNASN') if str(raw_country).isdigit() else State.objects.none()
    filter_form, team, counts = team_overview(request)
    if request.method == 'POST':
        if not can_create: raise PermissionDenied
        if account.is_valid() and assignment.is_valid():
            with transaction.atomic():
                # Serialize team creation and recheck parent authority after locking.
                User.objects.select_for_update().get(pk=request.user.pk)
                authority(request.user)
                d = assignment.cleaned_data
                if d['level'] == 'it':
                    State.objects.select_for_update().get(pk=d['state'].pk)
                    if AdminProfile.objects.filter(hierarchy_level='it', state=d['state']).exists():
                        assignment.add_error('state', 'This state already has an IT admin.')
                        return render(request, 'assigned_admin/hierarchy.html', {'profile': profile, 'account_form': account, 'assignment_form': assignment, 'can_create': can_create, 'team': team, 'filter_form': filter_form, 'counts': counts, 'create_label': create_label, 'unmapped_states': State.objects.filter(country__isnull=True).exclude(code='UNASN').count() if profile is None else 0})
                user = account.save(commit=False)
                user.admin_role = 'scoped_admin'; user.is_staff = user.is_superuser = False
                user.save()
                created = AdminProfile.objects.create(user=user, role='scoped_admin', hierarchy_level=d['level'],
                    country=d['country'], state=d['state'], district=d['district'], area=d['area'], appointed_by=request.user,
                    sections=[], all_states=False)
                record_activity(request.user, 'team', 'create_hierarchy', user.pk, user.username, {'level': d['level']})
                UserNotification.objects.create(user=user, title='Admin assignment created', message='Sign in to your assigned admin workspace.')
            messages.success(request, 'Admin created. They can sign in with their phone number and password.')
            return redirect('hierarchy_workspace')
    logs = AdminActivity.objects.filter(actor_id__in=[request.user.pk] + list(team.values_list('user_id', flat=True)))[:30]
    tickets = Complaint.objects.none()
    if profile and profile.hierarchy_level == 'it':
        tickets = Complaint.objects.filter(assigned_to=request.user, district__state_id=profile.state_id)
    return render(request, 'assigned_admin/hierarchy.html', {'profile': profile, 'can_create': can_create,
        'account_form': account, 'assignment_form': assignment, 'team': team, 'logs': logs, 'tickets': tickets, 'filter_form': filter_form, 'counts': counts, 'create_label': create_label, 'unmapped_states': State.objects.filter(country__isnull=True).exclude(code='UNASN').count() if profile is None else 0})


@login_required
@require_POST
@transaction.atomic
def toggle(request, pk):
    User.objects.select_for_update().get(pk=request.user.pk)
    target = get_object_or_404(visible_team(request.user).select_related(None).select_for_update(), pk=pk)
    target.is_active = not target.is_active
    target.save(update_fields=['is_active'])
    User.objects.filter(pk=target.user_id).update(is_active=target.is_active)
    record_activity(request.user, 'team', 'activate' if target.is_active else 'suspend', target.user_id, target.user.username)
    return redirect('hierarchy_workspace')


class GeographyForm(forms.Form):
    country_name = forms.CharField(max_length=100, required=False)
    country_code = forms.RegexField(r'^[A-Za-z]{2}$', max_length=2, required=False, help_text='Two-letter country code')
    country = forms.ModelChoiceField(queryset=Country.objects.filter(is_active=True).order_by('name'), required=False)
    states = forms.ModelMultipleChoiceField(queryset=State.objects.filter(country__isnull=True).exclude(code='UNASN'), required=False)


@login_required
def geography(request):
    if authority(request.user) is not None: raise PermissionDenied
    form = GeographyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            country = d['country']
            if not country and d['country_name'] and d['country_code']:
                if Country.objects.filter(code=d['country_code'].upper()).exists() or Country.objects.filter(name=d['country_name']).exists():
                    form.add_error(None, 'Country already exists. Select it instead.')
                else:
                    country = Country.objects.create(name=d['country_name'], code=d['country_code'].upper())
            if not country: form.add_error(None, 'Select a country or enter its name and code.')
            if not form.errors:
                State.objects.filter(pk__in=d['states'], country__isnull=True).update(country=country)
                record_activity(request.user, 'team', 'country_mapping', country.pk, country.name)
                return redirect('hierarchy_workspace')
    return render(request, 'assigned_admin/hierarchy_form.html', {'form': form, 'heading': 'Countries and state mapping'})


@login_required
def support(request, pk):
    profile = authority(request.user)
    if not profile or profile.hierarchy_level != 'it': raise PermissionDenied
    ticket = get_object_or_404(Complaint, pk=pk, assigned_to=request.user, district__state_id=profile.state_id)
    class SupportForm(forms.ModelForm):
        class Meta:
            model = Complaint
            fields = ['status', 'resolution']
    form = SupportForm(request.POST or None, instance=ticket)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            authority(request.user)
            get_object_or_404(Complaint.objects.select_for_update(), pk=pk, assigned_to=request.user, district__state_id=profile.state_id)
            obj = form.save(commit=False)
            obj.resolved_at = timezone.now() if obj.status in ('resolved', 'closed') else None
            obj.save(update_fields=['status', 'resolution', 'resolved_at'])
            record_activity(request.user, 'support', 'update', ticket.pk, ticket.subject)
        return redirect('hierarchy_workspace')
    return render(request, 'assigned_admin/hierarchy_form.html', {'form': form, 'heading': ticket.subject})

@login_required
def assign_support(request):
    if authority(request.user) is not None:
        raise PermissionDenied
    class AssignForm(forms.Form):
        ticket = forms.ModelChoiceField(queryset=Complaint.objects.filter(district__isnull=False))
        admin = forms.ModelChoiceField(queryset=AdminProfile.objects.filter(hierarchy_level='it', is_active=True, user__is_active=True))
        def clean(self):
            data = super().clean()
            ticket, admin = data.get('ticket'), data.get('admin')
            if ticket and admin:
                authority(admin.user)
                if ticket.district.state_id != admin.state_id:
                    self.add_error('admin', 'Choose the IT admin assigned to this state.')
            return data
    form = AssignForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ticket, admin = form.cleaned_data['ticket'], form.cleaned_data['admin']
        ticket.assigned_to = admin.user
        ticket.save(update_fields=['assigned_to'])
        record_activity(request.user, 'support', 'assign', ticket.pk, ticket.subject)
        UserNotification.objects.create(user=admin.user, title='Support request assigned', message='A support request is available in your admin workspace.')
        return redirect('hierarchy_workspace')
    return render(request, 'assigned_admin/hierarchy_form.html', {'form': form, 'heading': 'Assign state IT support'})


@login_required
def password(request, pk):
    from django.contrib.auth.forms import SetPasswordForm
    target = get_object_or_404(visible_team(request.user), pk=pk)
    form = SetPasswordForm(target.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            get_object_or_404(visible_team(request.user).select_related(None).select_for_update(), pk=pk)
            form.save()
            record_activity(request.user, 'team', 'password_reset', target.user_id, target.user.username)
        return redirect('hierarchy_workspace')
    return render(request, 'assigned_admin/hierarchy_form.html', {'form': form, 'heading': 'Reset account password'})


urlpatterns = [path("admin-team/states/", state_choices, name="hierarchy_states"), path("admin-team/support/assign/", assign_support, name="hierarchy_assign_support"), path('admin-team/<int:pk>/password/', password, name='hierarchy_password'), path('admin-team/', workspace, name='hierarchy_workspace'),
    path('admin-team/geography/', geography, name='hierarchy_geography'),
    path('admin-team/<int:pk>/toggle/', toggle, name='hierarchy_toggle'),
    path('admin-team/support/<int:pk>/', support, name='hierarchy_support')]
