"""Private registration overview for the Local From pilot."""
from functools import wraps
from hashlib import sha256
import re

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import AdPost, CompanyProfile, Product, User


def is_superadmin(user):
    return user.is_authenticated and user.is_active and user.admin_role == 'super_admin'


def private(view):
    @never_cache
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('pilot_admin_login')
        if not is_superadmin(request.user):
            raise PermissionDenied('Superadmin access is required.')
        return view(request, *args, **kwargs)
    return wrapped


class AdminLoginForm(forms.Form):
    phone = forms.CharField(label='Phone number',max_length=24,widget=forms.TextInput(attrs={'type':'tel','inputmode':'tel','autocomplete':'username','placeholder':'10-digit phone number'}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Your password'}))

    def clean_phone(self):
        phone=re.sub(r'[\s()-]','',self.cleaned_data['phone'])
        if phone.startswith('+91') and len(phone)==13:
            phone=phone[3:]
        elif phone.startswith('91') and len(phone)==12:
            phone=phone[2:]
        if not re.fullmatch(r'[6-9][0-9]{9}',phone):
            raise forms.ValidationError('Enter your 10-digit phone number, optionally with +91.')
        return phone


@never_cache
@sensitive_post_parameters('password')
@require_http_methods(['GET', 'POST'])
def sign_in(request):
    if is_superadmin(request.user):
        return redirect('super_admin_dashboard')
    form = AdminLoginForm(request.POST if request.method == 'POST' else None)
    status = 200
    if request.method == 'POST' and form.is_valid():
        key = 'pilot-admin-login:' + sha256(form.cleaned_data['phone'].encode()).hexdigest()
        attempts = cache.get(key, 0)
        if attempts >= 5:
            form.add_error(None, 'Too many attempts. Try again in 15 minutes.')
            status = 429
        else:
            user = authenticate(request, username=form.cleaned_data['phone'], password=form.cleaned_data['password'])
            # Copying credentials can include surrounding spaces. Try the exact
            # password first so existing passwords containing spaces still work.
            password=form.cleaned_data['password']
            if user is None and password != password.strip():
                user=authenticate(request,username=form.cleaned_data['phone'],password=password.strip())
            if user and is_superadmin(user):
                cache.delete(key)
                login(request, user)
                return redirect('super_admin_dashboard')
            cache.set(key, attempts + 1, 900)
            form.add_error(None, 'Invalid superadmin phone number or password.')
    return render(request, 'pilot_admin/login.html', {'form': form}, status=status)


@private
@require_POST
def sign_out(request):
    logout(request)
    return redirect('pilot_admin_login')


def overview(request, tab):
    query = request.GET.get('q', '').strip()[:150]
    if tab == 'shops':
        records = CompanyProfile.objects.select_related('user', 'user__shop').order_by('-pk')
        if query:
            records = records.filter(Q(company_name__icontains=query) | Q(company_id__icontains=query) | Q(user__phone__icontains=query) | Q(user__business_phone__icontains=query) | Q(user__city__icontains=query) | Q(user__pincode__icontains=query))
    else:
        records = User.objects.select_related('company').order_by('-date_joined', '-pk')
        if query:
            records = records.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(username__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query) | Q(city__icontains=query) | Q(pincode__icontains=query))
    page = Paginator(records, 20).get_page(request.GET.get('page'))
    return render(request, 'pilot_admin/overview.html', {
        'tab': tab, 'q': query, 'page': page,
        'user_count': User.objects.count(), 'shop_count': CompanyProfile.objects.count(),
        'product_count': Product.objects.count(),
    })


@private
@require_GET
def shops(request):
    return overview(request, 'shops')


@private
@require_GET
def users(request):
    return overview(request, 'users')


@private
@require_GET
def shop_detail(request, pk):
    company = get_object_or_404(CompanyProfile.objects.select_related('user', 'user__shop'), pk=pk)
    return render(request,'pilot_admin/shop_detail.html',shop_detail_context(company))


def shop_detail_context(company,access_form=None):
    from .product_access import ProductAccessReviewForm
    if access_form is None:
        access_form=ProductAccessReviewForm(initial={'decision':'approve','product_limit':max(company.requested_product_limit or company.product_limit+5,company.product_limit+1)})
    return {
        'company': company, 'owner': company.user,
        'products': company.products.prefetch_related('images').all(),
        'product_count':company.products.count(),'access_form':access_form,
        'offers': company.user.local_offers.all(), 'videos': company.videos.all(),
        'photos': company.user.gallery_images.all(),
    }


@private
@require_GET
def user_detail(request, pk):
    member = get_object_or_404(User.objects.select_related('company', 'shop'), pk=pk)
    return render(request, 'pilot_admin/user_detail.html', {'member': member})


@private
@require_GET
def ads(request):
    status = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()[:150]
    records = AdPost.objects.select_related('user').order_by('-created_at','-pk')
    if status in dict(AdPost.STATUS):
        records = records.filter(status=status)
    else:
        status = ''
    if query:
        records = records.filter(Q(company_name__icontains=query)|Q(title__icontains=query)|Q(contact_phone__icontains=query)|Q(user__phone__icontains=query))
    return render(request,'pilot_admin/ads.html',{'tab':'ads','page':Paginator(records,20).get_page(request.GET.get('page')),'q':query,'status':status,'pending_count':AdPost.objects.filter(status='pending').count()})


class AdReviewForm(forms.Form):
    decision = forms.ChoiceField(choices=[('approve','Approve and publish'),('reject','Request changes')])
    note = forms.CharField(required=False,max_length=2000,widget=forms.Textarea(attrs={'rows':3,'placeholder':'Explain any changes needed before approval.'}))

    creative_image = forms.ImageField(required=False, label='Designed homepage banner', widget=forms.FileInput(attrs={'accept':'image/jpeg,image/png,image/webp'}), help_text='Upload your finished design (JPG, PNG or WebP, up to 5 MB). A wide 1600 × 700 banner works well. The applicant image is kept separately.')
    starts_at = forms.DateField(required=False, label='Start date', widget=forms.DateInput(attrs={'type':'date'}, format='%Y-%m-%d'))
    ends_at = forms.DateField(required=False, label='End date', widget=forms.DateInput(attrs={'type':'date'}, format='%Y-%m-%d'))

    def clean_creative_image(self):
        from .shop_forms import check_image
        return check_image(self.cleaned_data.get('creative_image'))

    def clean(self):
        data=super().clean()
        if data.get('decision')=='reject' and not data.get('note'):
            self.add_error('note','Add a reason so the applicant knows what to change.')
        start, end = data.get('starts_at'), data.get('ends_at')
        if data.get('decision') == 'approve':
            if bool(start) != bool(end):
                self.add_error('ends_at', 'Enter both a start date and an end date.')
            if start and start < timezone.localdate():
                self.add_error('starts_at', 'Choose today or a future start date.')
            if start and end and end < start:
                self.add_error('ends_at', 'End date must be on or after the start date.')
        return data


@private
@require_http_methods(['GET','POST'])
def ad_detail(request, pk):
    ad=get_object_or_404(AdPost.objects.select_related('user'),pk=pk)
    form=AdReviewForm(request.POST if request.method=='POST' else None, request.FILES if request.method=='POST' else None)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            ad=AdPost.objects.select_for_update().get(pk=pk)
            if ad.status != 'pending':
                messages.info(request,'This application has already been reviewed.')
                return redirect('pilot_admin_ad',pk=pk)
            if form.cleaned_data['decision']=='approve':
                ad.status='approved'
                ad.approved_at=timezone.now()
                ad.starts_at=form.cleaned_data.get('starts_at') or timezone.localdate()
                ad.expires_at=form.cleaned_data.get('ends_at') or ad.starts_at+timedelta(days=ad.requested_days-1)
                if form.cleaned_data.get('creative_image'):
                    ad.creative_image=form.cleaned_data['creative_image']
                ad.reject_note=''
            else:
                ad.status='rejected'
                ad.reject_note=form.cleaned_data['note']
                ad.approved_at=None
                ad.expires_at=None
            ad.save(update_fields=['status','approved_at','expires_at','reject_note','starts_at','creative_image'])
            from .admin_messages import send_review_message
            send_review_message(request.user,ad.user,
                title='Your ad is approved' if ad.status=='approved' else 'Your ad needs changes',
                body=f'{ad.title or ad.company_name}: '+(f'Your ad is approved to run from {ad.starts_at:%d %b %Y} to {ad.expires_at:%d %b %Y}.' if ad.status=='approved' else ad.reject_note),
                notif_type='success' if ad.status=='approved' else 'warning',link='/advertise/applications/')
        messages.success(request,('Ad approved and scheduled.' if ad.is_scheduled else 'Ad approved and published.') if ad.status=='approved' else 'Application returned with feedback.')
        return redirect('pilot_admin_ad',pk=pk)
    return render(request,'pilot_admin/ad_detail.html',{'tab':'ads','ad':ad,'form':form})
