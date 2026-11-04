"""Account settings, saved discovery areas and business follows."""
import re

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import BusinessFollow, CompanyProfile, User

PIN = re.compile(r'[1-9][0-9]{5}')


class LocationPreferencesForm(forms.Form):
    pincode = forms.RegexField(PIN, required=False, max_length=6, label='Main pincode')
    preferred_pincode_1 = forms.RegexField(PIN, required=False, max_length=6, label='Preferred area 1')
    preferred_pincode_2 = forms.RegexField(PIN, required=False, max_length=6, label='Preferred area 2')

    def clean(self):
        data = super().clean()
        pins = [value for value in data.values() if value]
        if len(pins) != len(set(pins)):
            raise forms.ValidationError('Choose different pincodes for your main and preferred areas.')
        if any(data.get(key) for key in ('preferred_pincode_1', 'preferred_pincode_2')) and not data.get('pincode'):
            self.add_error('pincode', 'Add your main pincode before saving preferred areas.')
        return data


class BusinessDetailsForm(forms.ModelForm):

    class Meta:
        model = CompanyProfile
        fields = ['company_name', 'description', 'industry', 'company_size', 'website', 'logo', 'banner_image']
        widgets = {
            'logo': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'data-image-preview': 'profile-logo-preview', 'data-image-crop': 'logo'}),
            'banner_image': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'data-image-preview': 'profile-banner-preview', 'data-image-crop': 'banner'}),
        }


class DashboardPersonalForm(forms.ModelForm):
    photo = forms.ImageField(required=False, label='Personal profile photo')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'whatsapp', 'city', 'address', 'photo']


def dashboard_profile_context(user, company):
    seeker = getattr(user, 'seeker', None)
    return {'company': company, 'business_form': BusinessDetailsForm(instance=company) if company else None,
            'personal_form': DashboardPersonalForm(instance=user),

            'location_form': LocationPreferencesForm(initial={field: getattr(user, field) for field in LocationPreferencesForm.base_fields}),
            'account_features': profile_features(user), 'following_count': user.business_follows.count(),
            'business_follower_count': company.followers.count() if company else 0}


def selected_area(request):
    """An explicit filter wins; otherwise use the chosen area or resident pincode."""
    explicit = request.GET.get('pincode')
    if explicit is not None:
        explicit = explicit.strip()
        if not explicit or PIN.fullmatch(explicit):
            request.session['active_pincode'] = explicit
            request.session['offers_pincode'] = explicit
            request.session['news_pincode'] = explicit
            return explicit
    user = request.user
    return request.session.get('active_pincode', user.pincode if user.is_authenticated else '')


def safe_return(request, default='/profile/edit/'):
    target = request.POST.get('next') or request.GET.get('next', '')
    return target if target.startswith('/') and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()) else default


@require_POST
def select_area(request):
    code = request.POST.get('pincode', '').strip()
    if not PIN.fullmatch(code):
        messages.error(request, 'Enter a valid six-digit pincode.')
        return redirect(safe_return(request, '/'))
    request.session['active_pincode'] = code
    request.session['offers_pincode'] = code
    request.session['news_pincode'] = code
    if request.user.is_authenticated and not request.user.pincode:
        request.user.pincode = code
        request.user.save(update_fields=['pincode'])
    return redirect(safe_return(request, '/'))


@login_required
@require_POST
def follow_business(request, company_id):
    company = get_object_or_404(CompanyProfile, company_id=company_id, user__is_active=True)
    if company.user_id == request.user.pk:
        return JsonResponse({'error': 'You cannot follow your own business.'}, status=400)
    action = request.POST.get('action')
    if action not in ('follow', 'unfollow'):
        return JsonResponse({'error': 'Choose follow or unfollow.'}, status=400)
    if action == 'follow':
        BusinessFollow.objects.get_or_create(company=company, user=request.user)
    else:
        BusinessFollow.objects.filter(company=company, user=request.user).delete()
    data = {'following': action == 'follow', 'followers': company.followers.count()}
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(data)
    return redirect(safe_return(request, company.get_absolute_url()))


def profile_features(user):
    from .features import FEATURES
    links = [{'name': 'My dashboard', 'url': '/dashboard/'},
             {'name': 'Create business / shop', 'url': '/business/create/'},
             {'name': 'Following businesses', 'url': '/businesses/?following=1&pincode='},
             {'name': 'My accounts', 'url': '/my-accounts/'}]
    if CompanyProfile.objects.filter(user=user, user__is_active=True).exists():
        links += [{'name': 'Business dashboard', 'url': '/employer/dashboard/'},
                  {'name': 'My products', 'url': '/employer/dashboard/#products'},
                  {'name': 'Shop videos', 'url': '/employer/dashboard/#videos'},
                  {'name': 'Business gallery', 'url': '/employer/dashboard/#gallery'},
                  {'name': 'My offers', 'url': '/offers/mine/'}]
    links += [{'name': item['name'], 'url': item['url']} for item in FEATURES if item['name'] != 'My Profile']
    return links
