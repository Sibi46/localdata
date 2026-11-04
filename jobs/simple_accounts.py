"""Small personal-account onboarding, followed by optional shop setup."""
import time
import unicodedata

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from .models import CompanyProfile, ShopProfile, User
from .otp_security import issue, verify, consume, demo_enabled, OTPError


class DetailsForm(forms.Form):
    name = forms.CharField(label='Your name', max_length=150, help_text='Letters and spaces only.', widget=forms.TextInput(attrs={'autocomplete':'name','placeholder':'Your full name','inputmode':'text','data-text-only-name':'','pattern':r'[\p{L}\p{M}\s]+'}))
    phone = forms.RegexField(r'^[6-9][0-9]{9}$', label='Phone number', error_messages={'invalid': 'Enter a valid 10-digit mobile number.'}, widget=forms.TextInput(attrs={'type': 'tel', 'inputmode': 'numeric', 'maxlength': '10', 'autocomplete': 'tel-national', 'placeholder': '10-digit mobile number'}))
    pincode=forms.RegexField(r'^[1-9][0-9]{5}$',label='Your pincode',widget=forms.TextInput(attrs={'inputmode':'numeric','maxlength':'6','autocomplete':'postal-code','data-account-pincode':''}))
    city=forms.CharField(label='City / town',max_length=100,required=False,help_text='Filled from your pincode. You can correct it if needed.',widget=forms.TextInput(attrs={'data-account-city':'','autocomplete':'address-level2'}))

    def clean_name(self):
        name=unicodedata.normalize('NFC',' '.join(self.cleaned_data['name'].split()))
        if not any(unicodedata.category(char).startswith('L') for char in name) or any(not(char.isspace() or unicodedata.category(char)[0] in ('L','M')) for char in name):
            raise forms.ValidationError('Enter your name using letters and spaces only.')
        return name

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if User.objects.filter(Q(phone=phone) | Q(username=phone) | Q(business_phone=phone)).exists():
            raise forms.ValidationError('This phone is already registered. Sign in with your password.')
        return phone


class OTPForm(forms.Form):
    otp = forms.RegexField(r'^[0-9]{6}$', label='Enter OTP', error_messages={'invalid': 'Enter the six-digit OTP shown above.'}, widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'one-time-code', 'maxlength': '6', 'placeholder': '6-digit OTP'}))


class PasswordForm(forms.Form):
    password = forms.CharField(label='Create password', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}), help_text='Use at least 8 characters. You will use this with your phone number to sign in.')
    confirm_password = forms.CharField(label='Confirm password', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data['password']
        if len(password) < 8:
            raise forms.ValidationError('Use at least 8 characters.')
        return password

    def clean(self):
        data = super().clean()
        if data.get('password') and data.get('password') != data.get('confirm_password'):
            self.add_error('confirm_password', 'Passwords do not match.')
        return data


def valid_pending(pending):
    return pending and time.time() - pending.get('created', 0) < 600


@never_cache
@sensitive_post_parameters('password', 'confirm_password', 'otp')
@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.user.is_authenticated:
        return redirect('business_create' if request.GET.get('type') in ('company', 'shop') else 'personal_account')
    if request.GET.get('type') in ('company', 'shop'):
        request.session['signup_business_type'] = request.GET['type']
    pending = request.session.get('simple_signup')
    if pending and not demo_enabled('signup'):
        pending.pop('code', None)
        request.session['simple_signup'] = pending
    if pending and not valid_pending(pending):
        request.session.pop('simple_signup', None)
        pending = None
        messages.info(request, 'Your OTP expired. Start again to get a new OTP.')
    step = 'password' if pending and pending.get('verified') else ('otp' if pending else 'details')
    if request.method == 'POST' and request.POST.get('action') == 'restart':
        request.session.pop('simple_signup', None)
        return redirect('register')
    form_class = {'details': DetailsForm, 'otp': OTPForm, 'password': PasswordForm}[step]
    candidate = User(username=pending['phone'], phone=pending['phone'], first_name=pending['name']) if pending else None
    form = form_class(request.POST if request.method == 'POST' else None, **({'user': candidate} if step == 'password' else {}))
    if request.method == 'POST' and form.is_valid():
        if step == 'details':
            try:
                challenge = issue(request, form.cleaned_data['phone'], 'signup')
                request.session['simple_signup'] = {**form.cleaned_data, **challenge, 'attempts': 0}
                return redirect('register')
            except OTPError as error:
                form.add_error(None, 'Registration is unavailable. ' + str(error))
        elif step == 'otp':
            pending['attempts'] += 1
            if pending['attempts'] > 5:
                request.session.pop('simple_signup', None)
                messages.error(request, 'Too many incorrect attempts. Start again for a new code.')
                return redirect('register')
            try:
                verify(request, pending['phone'], 'signup', form.cleaned_data['otp'])
            except OTPError:
                request.session['simple_signup'] = pending
                form.add_error('otp', 'That code is incorrect or expired. Request a new OTP.')
            else:
                pending['verified'] = True
                pending.pop('code', None)
                request.session['simple_signup'] = pending
                return redirect('register')
        else:
            phone = pending['phone']
            try:
                with transaction.atomic():
                    if User.objects.filter(Q(phone=phone) | Q(username=phone) | Q(business_phone=phone)).exists():
                        raise IntegrityError('Phone already registered')
                    consume(request, phone, 'signup')
                    user = User.objects.create_user(username=phone, phone=phone, first_name=pending['name'],pincode=pending.get('pincode',''),city=pending.get('city',''), user_type='individual', password=form.cleaned_data['password'])
            except OTPError as error:
                request.session.pop('simple_signup', None)
                form.add_error(None, str(error))
                return render(request, 'accounts/signup.html', {'form': form, 'step': step, 'pending': None}, status=400)
            except IntegrityError:
                request.session.pop('simple_signup', None)
                messages.error(request, 'This phone is already registered. Please sign in.')
                return redirect('login')
            request.session['active_pincode']=user.pincode
            request.session.pop('simple_signup', None)
            business_type = request.session.pop('signup_business_type', '')
            login(request, user, backend='jobs.backends.PhoneOrEmailBackend')
            messages.success(request, 'Your personal account is ready.')
            return redirect('/business/create/?type=' + business_type if business_type else 'personal_account')
    return render(request, 'accounts/signup.html', {'form': form, 'step': step, 'pending': pending})


class BusinessForm(forms.Form):
    directory_entry=forms.IntegerField(required=False,widget=forms.HiddenInput)
    owner_name=forms.CharField(label='Owner name',disabled=True,required=False)
    phone=forms.CharField(label='Registered phone number',disabled=True,required=False,help_text='Your shop uses your personal account phone and password.')
    account_type = forms.ChoiceField(label='Account type', choices=[('shop', 'Shop'), ('company', 'Business')])
    name = forms.CharField(label='Shop / business name', max_length=150)
    category = forms.CharField(label='Category (optional)', max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': 'For example: groceries, clothing, jewellery'}))
    pincode = forms.RegexField(r'^[1-9][0-9]{5}$', label='Pincode', widget=forms.TextInput(attrs={'inputmode': 'numeric', 'maxlength': '6','data-account-pincode':''}))
    city = forms.CharField(label='City / town', max_length=100,widget=forms.TextInput(attrs={'data-account-city':''}))
    address = forms.CharField(label='Shop address (optional)', required=False, max_length=500, widget=forms.Textarea(attrs={'rows': 2}))
    logo = forms.ImageField(label='Shop logo (optional)', required=False, help_text='JPG, PNG, or WebP, up to 5 MB.', widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'data-image-preview': 'shop-logo-preview', 'data-image-crop': 'logo'}))
    banner_image = forms.ImageField(label='Shop banner (optional)', required=False, help_text='A wide photo for the top of your shop profile. Up to 5 MB.', widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'data-image-preview': 'shop-banner-preview', 'data-image-crop': 'banner'}))

    def __init__(self,*args,user=None,**kwargs):
        self.user=user
        super().__init__(*args,**kwargs)

    def clean(self):
        data=super().clean()
        if data.get('directory_entry'):
            from .models import ShopDirectoryEntry
            from .shop_directory import normalize_phone
            entry=ShopDirectoryEntry.objects.filter(pk=data['directory_entry']).first()
            if not entry or entry.registered_shop_id or not self.user or entry.phone!=normalize_phone(self.user.phone):
                raise forms.ValidationError('This listed shop is unavailable for your account. Search again using your account phone number.')
            data['name']=entry.name
        return data

    def clean_logo(self):
        from .shop_forms import check_image
        return check_image(self.cleaned_data.get('logo'))

    def clean_banner_image(self):
        from .shop_forms import check_image
        return check_image(self.cleaned_data.get('banner_image'))


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def business_create(request):
    if CompanyProfile.objects.filter(user=request.user).exists():
        return redirect('employer_dashboard')
    form = BusinessForm(request.POST if request.method == 'POST' else None, request.FILES if request.method == 'POST' else None, user=request.user,initial={'owner_name':request.user.get_full_name() or request.user.username,'phone':request.user.phone,'account_type': 'company' if request.GET.get('type') == 'company' else 'shop', 'pincode': request.user.pincode, 'city': request.user.city})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            if not CompanyProfile.objects.filter(user=user).exists():
                data = form.cleaned_data
                entry=None
                if data.get('directory_entry'):
                    from .models import ShopDirectoryEntry
                    from .shop_directory import normalize_phone
                    entry=ShopDirectoryEntry.objects.select_for_update().filter(pk=data['directory_entry'],phone=normalize_phone(user.phone),registered_shop__isnull=True).first()
                    if entry is None:
                        form.add_error(None,'This listed shop is no longer available. Please search again.')
                        return render(request,'accounts/business_create.html',{'form':form})
                    data['name']=entry.name
                company = CompanyProfile.objects.create(user=user, company_name=data['name'], industry=data['category'], logo=data.get('logo'), banner_image=data.get('banner_image'))
                if entry:
                    entry.registered_shop=company
                    entry.save(update_fields=['registered_shop','updated_at'])
                if data['account_type'] == 'shop':
                    ShopProfile.objects.create(user=user, shop_name=data['name'], shop_type=data['category'], owner_name=user.get_full_name()[:100], logo=company.logo.name, banner_image=company.banner_image.name)
                user.user_type = data['account_type']
                user.pincode, user.city, user.address = data['pincode'], data['city'], data['address']
                user.save(update_fields=['user_type', 'pincode', 'city', 'address'])
                request.session['active_pincode']=user.pincode
        messages.success(request, 'Your shop dashboard is ready. Add your first product, offer, photo, or video.')
        return redirect('employer_dashboard')
    return render(request, 'accounts/business_create.html', {'form': form})


@never_cache
@login_required
def personal_account(request):
    from .models import AdPost
    company=CompanyProfile.objects.filter(user=request.user).first()
    form=AccountLocationForm(request.POST if request.method=='POST' else None,initial={'pincode':request.user.pincode,'city':request.user.city})
    if request.method=='POST' and form.is_valid():
        request.user.pincode=form.cleaned_data['pincode']
        request.user.city=form.cleaned_data['city']
        request.user.save(update_fields=['pincode','city'])
        request.session['active_pincode']=request.user.pincode
        messages.success(request,'Your local area is updated.')
        return redirect('personal_account')
    ads=AdPost.objects.filter(user=request.user).order_by('-created_at')
    return render(request,'accounts/account.html',{'has_business':bool(company),'company':company,'my_ads':ads[:5],'my_ad_count':ads.count(),'location_form':form})


class AccountLocationForm(forms.Form):
    pincode=forms.RegexField(r'^[1-9][0-9]{5}$',label='Your pincode',widget=forms.TextInput(attrs={'inputmode':'numeric','maxlength':'6','data-account-pincode':''}))
    city=forms.CharField(label='City / town',max_length=100,required=False,widget=forms.TextInput(attrs={'data-account-city':''}))
