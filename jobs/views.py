import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import Q, F, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.debug import sensitive_post_parameters
from .admin_messages import send_review_message

logger = logging.getLogger(__name__)


from .models import CompanyProfile, ShopProfile, JobSeekerProfile, Conversation, Message, Advertiser, AdPackage, Advertisement, AdPayment, State, District, AdminProfile, Industry, Discount, Complaint, SystemNotification, PinCode, UserNotification, LocalOffer, AdPost

User = get_user_model()


# ── PINCODE LOOKUP API ────────────────────────────────────────────────────────
def api_pincode_lookup(request,pin):
    from .locations import lookup_pincode,PincodeLookupUnavailable
    try:
        data=lookup_pincode(pin)
    except PincodeLookupUnavailable:
        return JsonResponse({'success':False,'error':'City lookup is temporarily unavailable. Please enter your city / town below.','code':'lookup_unavailable'},status=503)
    return JsonResponse(data or {'success':False,'error':'Area not found. Enter your city / town manually.'})


@never_cache
def home(request):
    from .account import selected_area
    from .shop import public_products
    import random
    area=selected_area(request)
    products=public_products()
    businesses=CompanyProfile.objects.filter(user__is_active=True).exclude(company_name='').select_related('user')
    if area:
        products=products.filter(shop__user__pincode=area)
        businesses=businesses.filter(user__pincode=area)
    today=timezone.localdate()
    live_ads=list(AdPost.objects.filter(status='approved',user__is_active=True).filter(Q(expires_at__isnull=True)|Q(expires_at__gte=today))[:60])
    random.shuffle(live_ads)
    live_ads=live_ads[:12]
    AdPost.objects.filter(pk__in=[ad.pk for ad in live_ads]).update(views=F('views')+1)
    banners=Advertiser.objects.filter(status='approved').exclude(banner_image='').exclude(banner_image__isnull=True)
    from jobportal.seo import metadata
    return render(request,'index.html',{'seo':metadata(request),'home_products':products[:8],'business_logos':businesses.order_by('-pk')[:12],
        'live_ads':live_ads,'advertiser_banners':banners[:6],'query':request.GET.get('q','')})


@sensitive_post_parameters('password', 'confirm_password', 'otp')
def register_process(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def err(msg):
        if is_ajax:
            return JsonResponse({'success': False, 'error': msg})
        messages.error(request, msg)
        return redirect('register')

    user_type  = request.POST.get('user_type', '').strip()
    if user_type not in User.EMPLOYER_TYPES:
        user_type = 'individual'
    password   = request.POST.get('password', '')
    phone      = request.POST.get('phone', '').strip()
    email      = request.POST.get('email', '').strip()
    first_name = (request.POST.get('first_name', '') or request.POST.get('owner_name', '')).strip()
    last_name  = request.POST.get('last_name', '').strip()
    address    = request.POST.get('address', '').strip()
    city       = request.POST.get('city', '').strip()
    pincode    = (request.POST.get('pincode', '') or request.POST.get('emp_pincode', '')).strip()
    whatsapp   = request.POST.get('whatsapp', '').strip()
    ref_code   = request.POST.get('ref_code', '').strip().upper()

    from django.db import IntegrityError as _IntegrityError

    # If already logged in and registering a business — link to existing account
    if request.user.is_authenticated and user_type in User.EMPLOYER_TYPES:
        user = request.user
        if phone and phone != user.phone:
            return err('Use your registered phone number for this business.')
        user.user_type = user_type
        if pincode: user.pincode = pincode
        # Save business phone if provided and not already taken
        if phone and phone != user.phone:
            if not User.objects.filter(business_phone=phone).exclude(pk=user.pk).exists():
                user.business_phone = phone
        if password:
            user.set_password(password)
        try:
            user.save()
        except Exception:
            logger.exception('register_process: user.save() failed (authenticated link) user=%s', user.pk)
            return err('Registration failed. Please try again.')
    else:
        username = phone if phone else email
        if not username:
            return err('Phone or email is required.')

        if not password:
            return err('Password is required.')

        existing_accounts = Q(username__iexact=username)
        if phone:
            existing_accounts |= Q(phone=phone) | Q(business_phone=phone)
        if email:
            existing_accounts |= Q(email__iexact=email)
        if User.objects.filter(existing_accounts).exists():
            return err('An account already exists with these details. Please login before registering a business.')
        else:
            from .otp_security import consume, OTPError
            try:
                if len(password) < 8:
                    return err('Use at least 8 characters.')
                consume(request, phone, 'signup')
            except OTPError as error:
                return err(str(error))
            try:
                from .utils import generate_referral_code
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    whatsapp=whatsapp,
                    user_type=user_type,
                    address=address,
                    city=city,
                    pincode=pincode,
                    referral_code=generate_referral_code(),
                )
            except _IntegrityError:
                logger.exception('register_process: create_user IntegrityError phone=%s', phone)
                return err('An account already exists with this phone or email. Please login instead.')
            except Exception:
                logger.exception('register_process: create_user failed phone=%s', phone)
                return err('Registration failed. Please try again.')

    org_name = (
        request.POST.get('org_name', '').strip()
        or request.POST.get('company_name', '').strip()
        or f"{first_name} {last_name}".strip()
    )

    try:
        if user_type in User.EMPLOYER_TYPES:
            logo_file = request.FILES.get('logo') or None
            banner_file = request.FILES.get('banner_image') or None
            cp_defaults = dict(
                company_name=org_name,
                industry=request.POST.get('industry', '').strip(),
                website=request.POST.get('website', '').strip(),
                company_size=request.POST.get('company_size', '').strip(),
            )
            if logo_file:
                cp_defaults['logo'] = logo_file
            if banner_file:
                cp_defaults['banner_image'] = banner_file
            CompanyProfile.objects.update_or_create(user=user, defaults=cp_defaults)
            # Generate salesman BIZ ID if not already set
            if not user.salesman_biz_id:
                from .utils import generate_biz_id
                user.salesman_biz_id = generate_biz_id()
                User.objects.filter(pk=user.pk).update(salesman_biz_id=user.salesman_biz_id)
            if user_type == 'shop':
                sp_defaults = dict(
                    shop_name=org_name,
                    shop_type=request.POST.get('shop_type', '').strip(),
                    owner_name=first_name,
                    website=request.POST.get('website', '').strip(),
                )
                if logo_file:
                    sp_defaults['logo'] = logo_file
                if banner_file:
                    sp_defaults['banner_image'] = banner_file
                ShopProfile.objects.update_or_create(user=user, defaults=sp_defaults)
        elif user_type in ('employee', 'individual', 'freelancer'):
            seeker_defaults = dict(
                job_category=request.POST.get('job_category', ''),
                primary_skill=request.POST.get('primary_skill', ''),
                rate=request.POST.get('rate', ''),
            )
            seeker, _ = JobSeekerProfile.objects.get_or_create(user=user, defaults=seeker_defaults)
            if not _:
                # existing — update collar and skill
                if request.POST.get('job_category'):
                    seeker.job_category = request.POST.get('job_category')
                if request.POST.get('primary_skill'):
                    seeker.primary_skill = request.POST.get('primary_skill')
            if request.FILES.get('photo'):
                seeker.photo = request.FILES['photo']
            if request.FILES.get('resume'):
                seeker.resume = request.FILES['resume']
            seeker.save()
    except Exception:
        logger.exception('register_process: profile create failed for user %s type=%s', user.pk, user_type)
        # User account was created — log them in; profile can be completed later.

    login(request, user, backend='jobs.backends.PhoneOrEmailBackend')

    if user_type in User.EMPLOYER_TYPES:
        redirect_url = '/employer/dashboard/'
    else:
        redirect_url = '/'

    if is_ajax:
        return JsonResponse({'success': True, 'redirect': redirect_url})
    return redirect(redirect_url)


# ── AUTH ──────────────────────────────────────────────────────────────────────
def login_view(request):
    from django.utils.http import url_has_allowed_host_and_scheme
    raw_next = request.GET.get('next', '') or request.POST.get('next', '')
    next_url = raw_next if url_has_allowed_host_and_scheme(
        raw_next, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ) else ''

    if request.user.is_authenticated:
        return redirect(next_url or 'dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse as _JR
                return _JR({'success': True, 'redirect': next_url or '/'})
            return redirect(next_url or 'dashboard')
        # Check if the user exists at all
        user_exists = User.objects.filter(phone=username).exists() or \
                      User.objects.filter(email=username).exists() or \
                      User.objects.filter(username=username).exists()
        if not user_exists:
            error_msg = 'No account found. Please register first.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                from django.http import JsonResponse as _JR
                return _JR({'success': False, 'error': error_msg, 'not_registered': True})
            messages.error(request, error_msg)
            return render(request, 'accounts/login.html', {'next': next_url, 'not_registered': True, 'tried_username': username})
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse as _JR
            return _JR({'success': False, 'error': 'Invalid phone/email or password.'})
        messages.error(request, 'Invalid phone/email or password.')

    return render(request, 'accounts/login.html', {'next': next_url})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    role = request.user.admin_role
    if role == 'scoped_admin':
        return redirect('assigned_dashboard')
    if role == 'super_admin':
        return redirect('super_admin_dashboard')
    if role == 'state_admin':
        return redirect('state_admin_dashboard')
    if role == 'district_admin':
        return redirect('district_admin_dashboard')
    if CompanyProfile.objects.filter(user=request.user).exists():
        return redirect('employer_dashboard')
    if request.user.user_type == 'advertiser' or hasattr(request.user, 'advertiser'):
        return redirect('advertiser_dashboard')

    return redirect('personal_account')


def business_list(request):
    from .account import selected_area
    from .models import BusinessFollow
    from django.core.paginator import Paginator
    from django.db.models import Avg
    from datetime import timedelta
    businesses = CompanyProfile.objects.filter(user__is_active=True).exclude(company_name='').select_related('user')
    pincode = selected_area(request)
    query = request.GET.get('q', '').strip()
    following_only = request.GET.get('following') == '1'
    if following_only:
        businesses = businesses.filter(followers__user=request.user) if request.user.is_authenticated else businesses.none()
    if pincode:
        businesses = businesses.filter(user__pincode=pincode)
    if query:
        businesses = businesses.filter(company_name__icontains=query)
    businesses = businesses.annotate(review_count=Count('reviews', distinct=True), average_rating=Avg('reviews__rating'),
        recent_reviews=Count('reviews', filter=Q(reviews__created_at__gte=timezone.now() - timedelta(days=30)), distinct=True), follower_count=Count('followers', distinct=True), product_count=Count('products', filter=Q(products__is_active=True), distinct=True))
    sort = request.GET.get('sort', 'name')
    ordering = {'popular': ['-review_count', '-average_rating', 'company_name'],
                'trending': ['-recent_reviews', '-average_rating', 'company_name'],
                'rating': ['-average_rating', '-review_count', 'company_name']}.get(sort, ['company_name'])
    return render(request, 'business_list.html', {
        'sort': sort, 'following_only': following_only,
        'followed_business_ids': set(BusinessFollow.objects.filter(user=request.user).values_list('company_id', flat=True)) if request.user.is_authenticated else set(),
        'businesses': Paginator(businesses.order_by(*ordering), 30).get_page(request.GET.get('page')),
        'pincode': pincode, 'query': query,
    })


@login_required
def my_offers(request):
    if request.method == 'POST':
        offer = get_object_or_404(LocalOffer, pk=request.POST.get('offer_id'), owner=request.user)
        offer.is_active = False
        offer.save(update_fields=['is_active'])
        messages.success(request, 'Offer withdrawn.')
        return redirect('my_offers')
    return render(request, 'my_offers.html', {
        'offers': LocalOffer.objects.filter(owner=request.user).order_by('-created_at'),
    })


def business_profile(request, company_id):
    from .business_reviews import snapshot, badge
    from .models import BusinessGalleryImage, Flick, FlickLike
    from django.core.paginator import Paginator
    from django.db.models import Avg
    profile = get_object_or_404(CompanyProfile.objects.select_related('user'), company_id=company_id, user__is_active=True)
    owner = profile.user
    today = timezone.localdate()
    offers = LocalOffer.objects.filter(owner=owner, is_active=True).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).order_by('-created_at')
    products = profile.products.filter(is_active=True)
    page_number = request.GET.get('product_page')
    selected_id = request.GET.get('product', '')
    if selected_id.isascii() and selected_id.isdigit() and len(selected_id) < 19:
        selected = products.filter(pk=selected_id).first()
        if selected:
            preceding = products.filter(Q(created_at__gt=selected.created_at) | Q(created_at=selected.created_at, pk__gt=selected.pk)).count()
            page_number = preceding // 24 + 1
    product_page = Paginator(products, 24).get_page(page_number)
    reviews = profile.reviews.select_related('user')
    own_review = reviews.filter(user=request.user).first() if request.user.is_authenticated else None
    review_page = Paginator(reviews, 10).get_page(request.GET.get('review_page'))
    for review in review_page:
        review.badge_label = badge(review.user)
    return render(request, 'business_profile.html', {
        'profile': profile, 'owner': owner, 'user_type': owner.user_type,
        'products': product_page, 'product_count': products.count(),
        'offers': offers, 'offers_count': offers.count(),
        'gallery_images': BusinessGalleryImage.objects.filter(user=owner).order_by('-created_at'),
        'shop_videos': profile.videos.filter(is_published=True),
        'flicks': Flick.objects.filter(user=owner).order_by('-created_at')[:12],
        'reviews': review_page, 'review_count': reviews.count(), 'review_average': reviews.aggregate(value=Avg('rating'))['value'],
        'review_snapshot': snapshot(reviews), 'own_review': own_review,
        'review_reports': profile.review_reports.all()[:12] if request.user == owner else [],
        'latest_ai_report': profile.review_reports.filter(ai_generated=True).first(),
        'liked_flick_ids': set(FlickLike.objects.filter(user=request.user).values_list('flick_id', flat=True)) if request.user.is_authenticated else set(),
        'follower_count': profile.followers.count(),
        'is_following': profile.followers.filter(user=request.user).exists() if request.user.is_authenticated else False,
    })


# ── DASHBOARDS ────────────────────────────────────────────────────────────────
@login_required
def employer_dashboard(request, profile_editor=None):
    if not CompanyProfile.objects.filter(user=request.user, user__is_active=True).exists():
        return redirect('personal_account')
    if request.method == 'POST' and profile_editor is None:
        return profile_edit(request)
    from .account import dashboard_profile_context
    from .models import BusinessGalleryImage
    from .shop_forms import ShopPhotosForm
    company = getattr(request.user, 'company', None)
    if not company:
        return redirect('personal_account')
    context = dashboard_profile_context(request.user, company)
    products = company.products.all()
    videos = company.videos.all()
    offers = LocalOffer.objects.filter(owner=request.user).order_by('-created_at')
    photos = BusinessGalleryImage.objects.filter(user=request.user).order_by('-created_at')
    context.update({
        'products': products, 'shop_videos': videos, 'offers': offers, 'gallery_images': photos,
        'product_count': products.count(), 'video_count': videos.count(), 'offer_count': offers.count(), 'photo_count': photos.count(),
        'gallery_form': ShopPhotosForm(),
        'notifications': UserNotification.objects.filter(user=request.user).order_by('-created_at')[:20],
    })
    context.update(profile_editor or {})
    return render(request, 'employer_dashboard.html', context)


@login_required
def gallery_upload(request):
    if request.method != 'POST':
        return redirect('employer_dashboard')
    from .models import BusinessGalleryImage
    images = request.FILES.getlist('gallery_images')
    for img in images[:10]:
        BusinessGalleryImage.objects.create(
            user=request.user,
            image=img,
            caption=request.POST.get('caption', '').strip()[:200],
        )
    from django.contrib import messages as dj_messages
    dj_messages.success(request, f'{len(images)} image(s) uploaded to your gallery.')
    return redirect('/employer/dashboard/#gallery')


@login_required
def gallery_delete(request, pk):
    from .models import BusinessGalleryImage
    img = get_object_or_404(BusinessGalleryImage, pk=pk, user=request.user)
    img.image.delete(save=False)
    img.delete()
    return redirect('/employer/dashboard/#gallery')


# ── Rate limiting helpers ─────────────────────────────────────────────────────
def _rate_limit(cache_key, max_attempts, window_seconds):
    """Returns True if the action is allowed, False if rate limit exceeded."""
    from django.core.cache import cache
    count = cache.get(cache_key, 0)
    if count >= max_attempts:
        return False
    cache.set(cache_key, count + 1, window_seconds)
    return True


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ── OTP via 2Factor.in ────────────────────────────────────────────────────────
def _account_payload(request):
    import json
    if len(request.body) > 16384:
        raise ValueError('Invalid request.')
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except (ValueError, UnicodeError):
            raise ValueError('Invalid request.') from None
        if not isinstance(data, dict) or any(isinstance(v, (list, dict)) for v in data.values()):
            raise ValueError('Invalid request.')
        return data
    return request.POST


def _quick_register_data(request, data, password_hash=None):
    from .otp_security import consume, response_metadata, OTPError, PHONE
    from .simple_accounts import PasswordForm
    import re
    name = str(data.get('name', '')).strip()
    phone = str(data.get('phone', '')).strip()
    pincode = str(data.get('pincode', '')).strip()
    password = data.get('password', '')
    if not name or not PHONE.fullmatch(phone) or not re.fullmatch(r'[1-9][0-9]{5}', pincode):
        raise ValueError('Enter a name, valid phone number and pincode.')
    form = PasswordForm({'password': password, 'confirm_password': data.get('confirm_password', password)})
    if password_hash is None and not form.is_valid():
        raise ValueError('Use matching passwords of at least 8 characters.')
    if User.objects.filter(Q(phone=phone) | Q(username=phone) | Q(business_phone=phone)).exists():
        raise ValueError('This phone number is already registered. Please sign in.')
    try:
        with transaction.atomic():
            consume(request, phone, 'signup')
            user = User.objects.create_user(username=phone, phone=phone, first_name=name,
                pincode=pincode, user_type='individual', password=password if password_hash is None else None)
            if password_hash is not None:
                user.password = password_hash
                user.save(update_fields=['password'])
    except OTPError as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)
    except IntegrityError:
        return JsonResponse({'success': False, 'error': 'This phone number is already registered.'}, status=400)
    request.session.pop('reg_data', None)
    login(request, user, backend='jobs.backends.PhoneOrEmailBackend')
    return JsonResponse({'success': True, 'redirect': '/', **response_metadata()})


@never_cache
@sensitive_post_parameters('password', 'confirm_password', 'otp')
@require_POST
def send_otp(request):
    from .otp_security import issue, response_metadata, OTPError
    try:
        data = _account_payload(request)
        phone = str(data.get('phone', '')).strip()
        purpose = data.get('purpose', 'reset' if data.get('allow_existing') is True else 'signup')
        if purpose == 'reset':
            from .password_recovery import recoverable
            matches = list(User.objects.filter(phone=phone)[:2])
            if len(matches) != 1 or not recoverable(matches[0]):
                return JsonResponse({'success': False, 'error': 'Invalid request. Please restart the process.'}, status=400)
        elif purpose != 'signup':
            raise OTPError('Invalid verification purpose.')
        elif User.objects.filter(Q(phone=phone) | Q(username=phone) | Q(business_phone=phone)).exists():
            return JsonResponse({'success': False, 'error': 'This phone number is already registered. Please sign in.'}, status=400)
        pending = issue(request, phone, purpose)
        # Visible codes are limited to development or explicit public demo signup.
        return JsonResponse({'success': True, **response_metadata(pending)})
    except (OTPError, ValueError) as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)



@never_cache
@sensitive_post_parameters('password', 'confirm_password', 'otp')
@require_POST
def verify_otp(request):
    from .otp_security import verify, response_metadata, OTPError
    try:
        data = _account_payload(request)
        # No fallback between purposes: legacy callers default to reset only.
        purpose = data.get('purpose', request.session.get('account_otp_purpose', 'reset'))
        pending = request.session.get('account_otp_' + str(purpose), {})
        phone = str(data.get('phone', pending.get('phone', ''))).strip()
        verify(request, phone, purpose, str(data.get('otp', '')).strip())
        return JsonResponse({'success': True, **response_metadata()})
    except (OTPError, ValueError) as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)



def check_phone(request):
    """Check if a phone number is already registered."""
    if request.method != 'POST':
        return JsonResponse({'exists': False})
    import json
    try:
        data = json.loads(request.body)
        phone = str(data.get('phone', '')).strip()
    except (ValueError, AttributeError, TypeError):
        return JsonResponse({'exists': False, 'error': 'Enter a valid 10-digit mobile number.'}, status=400)
    if len(phone) != 10 or not phone.isascii() or not phone.isdigit():
        return JsonResponse({'exists': False, 'error': 'Enter a valid 10-digit mobile number.'}, status=400)
    User  = get_user_model()
    user  = User.objects.filter(phone=phone).first()
    if user:
        return JsonResponse({'exists': True, 'name': user.first_name or user.username})
    return JsonResponse({'exists': False})


def forgot_password(request):
    phone = request.GET.get('phone', '')
    return render(request, 'forgot_password.html', {'prefill_phone': phone})


@never_cache
@sensitive_post_parameters('password', 'confirm_password', 'otp')
@require_POST
def reset_password(request):
    from .otp_security import consume, OTPError
    from .password_recovery import recoverable
    try:
        data = _account_payload(request)
        phone = str(data.get('phone', '')).strip()
        password = data.get('password', '')
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError('Use at least 8 characters.')
        with transaction.atomic():
            matches = list(User.objects.select_for_update().filter(phone=phone)[:2])
            if len(matches) != 1 or not recoverable(matches[0]):
                raise ValueError('Invalid request. Please restart the process.')
            consume(request, phone, 'reset')
            user = matches[0]
            user.set_password(password)
            user.save(update_fields=['password'])
        logout(request)
        return JsonResponse({'success': True, 'redirect': '/login/'})
    except (OTPError, ValueError) as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)



def phone_login(request):
    """Login with personal phone or business phone + password."""
    if request.method != 'POST':
        return JsonResponse({'success': False})
    import json
    data     = json.loads(request.body)
    phone    = data.get('phone', '').strip()
    password = data.get('password', '')

    # Rate limit: max 5 login attempts per IP per 5 minutes
    ip = _get_client_ip(request)
    if not _rate_limit(f'login_ip_{ip}', max_attempts=5, window_seconds=300):
        return JsonResponse({'success': False, 'error': 'Too many login attempts. Please wait 5 minutes.'}, status=429)

    User     = get_user_model()
    # Try personal phone first, then business phone
    user = User.objects.filter(phone=phone).first() or \
           User.objects.filter(business_phone=phone).first()
    if user and user.is_active and user.check_password(password):
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        if user.is_employer() or CompanyProfile.objects.filter(user=user).exists():
            redirect_url = '/employer/dashboard/'
        else:
            redirect_url = '/'
        return JsonResponse({'success': True, 'redirect': redirect_url})
    return JsonResponse({'success': False, 'error': 'Wrong phone number or password. Try again.'})


@never_cache
@sensitive_post_parameters('password', 'confirm_password', 'otp')
@require_POST
def send_register_otp(request):
    from .otp_security import issue, response_metadata, OTPError
    try:
        data = _account_payload(request)
        phone = str(data.get('phone', '')).strip()
        if User.objects.filter(Q(phone=phone) | Q(username=phone) | Q(business_phone=phone)).exists():
            raise ValueError('This phone number is already registered. Please sign in.')
        pending = issue(request, phone, 'signup')
        # Do not store a submitted plaintext password in the session.
        request.session['reg_data'] = {key: str(data.get(key, '')).strip() for key in ('name', 'phone', 'pincode')}
        if data.get('password'):
            from .simple_accounts import PasswordForm
            from django.contrib.auth.hashers import make_password
            form = PasswordForm({'password': data['password'], 'confirm_password': data.get('confirm_password', data['password'])})
            if not form.is_valid():
                raise ValueError('Use matching passwords of at least 8 characters.')
            request.session['reg_data']['password_hash'] = make_password(form.cleaned_data['password'])
        return JsonResponse({'success': True, 'otp_sent': True, **response_metadata(pending)})
    except (OTPError, ValueError) as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)



@never_cache
@sensitive_post_parameters('password', 'confirm_password', 'otp')
@require_POST
def verify_register_otp(request):
    from .otp_security import verify, response_metadata, OTPError
    try:
        data = _account_payload(request)
        pending = request.session.get('account_otp_signup', {})
        phone = str(data.get('phone', pending.get('phone', ''))).strip()
        verify(request, phone, 'signup', str(data.get('otp', '')).strip())
        # Existing endpoint can still create an account when a password is
        # supplied at verification; otherwise it grants proof for quick-register.
        if data.get('password'):
            return _quick_register_data(request, {**request.session.get('reg_data', {}), **data, 'phone': phone})
        staged = request.session.get('reg_data', {})
        if staged.get('phone') == phone and staged.get('password_hash'):
            return _quick_register_data(request, staged, password_hash=staged['password_hash'])
        return JsonResponse({'success': True, **response_metadata()})
    except (OTPError, ValueError) as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)



@never_cache
@sensitive_post_parameters('password', 'confirm_password', 'otp')
@require_POST
def quick_register(request):
    try:
        return _quick_register_data(request, _account_payload(request))
    except ValueError as error:
        return JsonResponse({'success': False, 'error': str(error)}, status=400)



# ── MESSAGING ─────────────────────────────────────────────────────────────────
def _get_or_create_conv(user1, user2):
    a, b = (user1, user2) if user1.pk < user2.pk else (user2, user1)
    conv, _ = Conversation.objects.get_or_create(user_a=a, user_b=b)
    return conv


def _render_bubble(msg, me):
    from django.template.loader import render_to_string
    return render_to_string('partials/msg_bubble.html', {'msg': msg, 'me': me})


def _msg_to_dict(msg, me):
    d = {
        'id':      msg.pk,
        'sender':  msg.sender_id,
        'mine':    msg.sender_id == me.id,
        'type':    msg.msg_type,
        'content': msg.content,
        'time':    msg.sent_at.strftime('%I:%M %p'),
        'is_read': msg.is_read,
        'html':    _render_bubble(msg, me),
    }
    if msg.file:
        from django.urls import reverse
        d['file_url'] = reverse('chat_attachment', args=[msg.pk])
        d['file_name'] = msg.file_name
    if msg.msg_type == 'interview_invite':
        d['invite'] = {
            'date':     str(msg.invite_date) if msg.invite_date else '',
            'time':     str(msg.invite_time) if msg.invite_time else '',
            'mode':     msg.invite_mode,
            'location': msg.invite_location,
            'link':     msg.invite_link,
            'notes':    msg.invite_notes,
            'status':   msg.invite_status,
        }
    return d


def _sidebar_data(user):
    convs = Conversation.objects.filter(
        Q(user_a=user) | Q(user_b=user)
    ).select_related('user_a', 'user_b').order_by('-updated_at')
    rows = []
    for c in convs:
        last = c.messages.order_by('-sent_at').first()
        rows.append({'conv': c, 'other': c.other_user(user),
                     'last': last, 'unread': c.unread_for(user)})
    return rows


@never_cache
@login_required
def chat_list(request):
    sidebar      = _sidebar_data(request.user)
    total_unread = sum(d['unread'] for d in sidebar)
    return render(request, 'messages.html', {
        'conversations': sidebar,
        'total_unread':  total_unread,
        'active_conv':   None,
    })


@never_cache
@login_required
def chat_room(request, conv_id, **_):
    conv = get_object_or_404(Conversation, pk=conv_id)
    me   = request.user
    if conv.user_a != me and conv.user_b != me:
        return redirect('chat_list')
    conv.messages.filter(is_read=False).exclude(sender=me).update(
        is_read=True, read_at=timezone.now()
    )
    UserNotification.objects.filter(user=me,link=f'/messages/{conv.pk}/',is_read=False).update(is_read=True)
    sidebar = _sidebar_data(me)
    msgs    = conv.messages.select_related('sender').order_by('sent_at')
    return render(request, 'messages.html', {
        'conversations': sidebar,
        'active_conv':   conv,
        'other':         conv.other_user(me),
        'msgs':          msgs,
        'total_unread':  sum(d['unread'] for d in sidebar),
    })


@login_required
def send_message(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False})
    conv = get_object_or_404(Conversation, pk=request.POST.get('conv_id'))
    me   = request.user
    if conv.user_a != me and conv.user_b != me:
        return JsonResponse({'ok': False}, status=403)

    other    = conv.other_user(me)
    msg_type = request.POST.get('msg_type', 'text')
    if msg_type not in ('text', 'image', 'file'):
        return JsonResponse({'ok': False, 'error': 'Unsupported message type.'}, status=400)
    content  = request.POST.get('content', '').strip()
    f        = request.FILES.get('file')
    if not content and not f:
        return JsonResponse({'ok':False,'error':'Write a message or choose an attachment.'},status=400)
    if len(content)>5000:
        return JsonResponse({'ok':False,'error':'Keep your message within 5,000 characters.'},status=400)
    if msg_type in ('image','file') and not f:
        return JsonResponse({'ok':False,'error':'Choose an attachment first.'},status=400)

    msg = Message(conversation=conv, sender=me, receiver=other,
                  msg_type=msg_type, content=content)

    if f:
        if f.size>10*1024*1024:
            return JsonResponse({'ok':False,'error':'Choose a file smaller than 10 MB.'},status=400)
        ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else ''
        if ext not in ('jpg','jpeg','png','gif','webp','pdf','doc','docx','xls','xlsx','zip','txt'):
            return JsonResponse({'ok':False,'error':'Choose a photo, PDF, document, spreadsheet, ZIP, or text file.'},status=400)
        if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
            try:
                from PIL import Image as _PILImage
                import io as _io
                _img = _PILImage.open(_io.BytesIO(f.read()))
                _img.verify()
                f.seek(0)
            except Exception:
                return JsonResponse({'ok': False, 'error': 'Invalid image file.'}, status=400)
            msg.msg_type = 'image'
        else:
            msg.msg_type = 'file'
        msg.file      = f
        from .chat_attachments import private_storage
        msg.file.storage = private_storage()
        msg.file_name = f.name

    msg.save()
    conv.save()   # bumps updated_at

    UserNotification.objects.create(
        user=other,
        title=f'New message from {getattr(getattr(me,"company",None),"company_name","") or me.get_full_name() or me.username}'[:200],
        message=(content or (f.name if f else ''))[:80],
        notif_type='info',
        link=f'/messages/{conv.pk}/',
    )
    return JsonResponse({'ok': True, 'msg_id': msg.pk, 'html': _render_bubble(msg, me)})


@never_cache
@login_required
def poll_messages(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id)
    me   = request.user
    if conv.user_a != me and conv.user_b != me:
        return JsonResponse({'ok': False}, status=403)
    try:
        after=max(0,int(request.GET.get('after',0)))
    except (ValueError,TypeError):
        return JsonResponse({'ok':False,'error':'Invalid message cursor.'},status=400)
    new_msgs = conv.messages.filter(pk__gt=after).exclude(sender=me)
    new_msgs.filter(is_read=False).update(is_read=True, read_at=timezone.now())
    UserNotification.objects.filter(user=me,link=f'/messages/{conv.pk}/',is_read=False).update(is_read=True)
    return JsonResponse({'ok': True, 'messages': [_msg_to_dict(m, me) for m in new_msgs]})


# ==============================================================
# ADVERTISER MODULE
# ==============================================================


def ads_gallery(request):
    from .offers import gallery
    return gallery(request)


@login_required
def offer_post(request):
    """Only registered employers/companies can post offers."""
    user = request.user
    if not user.is_employer():
        from django.contrib import messages
        messages.error(request, 'Only registered companies can post offers. Please register as an employer.')
        return redirect('/register/')
    if request.method == 'POST':
        phone = request.POST.get('contact_phone', '').strip().replace(' ', '')
        # Build WhatsApp link from phone number
        wa_url = f"https://wa.me/91{phone}" if phone else ''
        obj = LocalOffer(
            owner=user,
            business_name = request.POST.get('business_name', '').strip(),
            title         = request.POST.get('title', '').strip(),
            discount_text = request.POST.get('discount_text', '').strip(),
            category      = request.POST.get('category', 'other'),
            description   = request.POST.get('description', '').strip(),
            contact_phone = phone,
            link_url      = wa_url,
            is_flash      = request.POST.get('is_flash') == '1',
            is_active     = False,  # pending admin approval
        )
        valid_until = request.POST.get('valid_until', '').strip()
        if valid_until:
            obj.valid_until = valid_until
        valid_days = request.POST.get('valid_days', '').strip()
        if valid_days:
            obj.valid_days = valid_days
        if request.FILES.get('image'):
            obj.image = request.FILES['image']
        obj.save()
        return redirect('/offers/post/success/')
    profile = CompanyProfile.objects.filter(user=user).first()
    return render(request, 'offer_post.html', {
        'categories': LocalOffer.CATEGORY_CHOICES,
        'company_profile': profile,
    })


def offer_post_success(request):
    return render(request, 'offer_post_success.html')


def offer_store(request, pk):
    from .offer_links import attach_offer_links
    offer = attach_offer_links(get_object_or_404(LocalOffer.objects.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.localdate())
    ), pk=pk, is_active=True))
    if offer.store_profile:
        return redirect(offer.store_url)
    return render(request, 'offer_store.html', {'offer': offer})


def advertiser_register(request):
    from .ad_applications import apply
    return apply(request)


def advertiser_register_success(request):
    return redirect('ad_applications')


@login_required
def advertiser_dashboard(request):
    try:
        adv = request.user.advertiser
    except Advertiser.DoesNotExist:
        messages.info(request, 'Please register as an advertiser first.')
        return redirect('advertiser_register')
    from .models import AdPost, AdSettings
    simple_ads   = AdPost.objects.filter(user=request.user).prefetch_related('renewals').order_by('-created_at')
    ad_settings  = AdSettings.get()
    total_views  = sum(a.views or 0 for a in simple_ads)
    total_clicks = sum(getattr(a, 'clicks', 0) or 0 for a in simple_ads)
    active_count = sum(1 for a in simple_ads if a.is_live)
    packages     = AdPackage.objects.filter(is_active=True)
    return render(request, 'advertiser_dashboard.html', {
        'adv': adv, 'ads': simple_ads,
        'total_views': total_views, 'total_clicks': total_clicks,
        'active_count': active_count, 'expiring': [],
        'packages': packages, 'settings': ad_settings,
    })


@login_required
def create_advertisement(request):
    return redirect('post_simple_ad')


@login_required
def ad_payment(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id, advertiser__user=request.user)
    payment = ad.payment
    if request.method == 'POST':
        method = request.POST.get('method', 'upi')
        import uuid
        from django.utils import timezone as tz
        payment.status         = 'paid'
        payment.payment_method = method
        payment.transaction_id = str(uuid.uuid4())[:18].upper()
        payment.paid_at        = tz.now()
        payment.save()
        from datetime import date, timedelta
        ad.status     = 'pending_review'
        ad.start_date = date.today()
        ad.end_date   = date.today() + timedelta(days=ad.package.duration_days)
        ad.save()
        messages.success(request, f'Payment successful! Ad is under review and will go live soon.')
        return redirect('ad_payment_success', ad_id=ad.pk)
    return render(request, 'ad_payment.html', {'ad': ad, 'payment': payment})


@login_required
def ad_payment_success(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id, advertiser__user=request.user)
    return render(request, 'ad_payment_success.html', {'ad': ad})


@login_required
def ad_performance(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id, advertiser__user=request.user)
    return render(request, 'ad_performance.html', {'ad': ad})


@login_required
def advertiser_renew_ad(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id, advertiser__user=request.user)
    if request.method == 'POST':
        import decimal
        pkg   = ad.package
        gst   = (pkg.price * decimal.Decimal('0.18')).quantize(decimal.Decimal('0.01'))
        total = pkg.price + gst
        import random, string
        inv   = ''.join(random.choices(string.digits, k=8))
        new_ad = Advertisement.objects.create(
            advertiser = ad.advertiser,
            package    = pkg,
            title      = ad.title,
            image      = ad.image,
            link_url   = ad.link_url,
            content    = ad.content,
            district   = ad.district,
            state      = ad.state,
            status     = 'pending_payment',
        )
        AdPayment.objects.create(
            advertisement  = new_ad,
            amount         = pkg.price,
            gst_amount     = gst,
            total_amount   = total,
            invoice_number = inv,
        )
        return redirect('ad_payment', ad_id=new_ad.pk)
    return render(request, 'renew_ad.html', {'ad': ad})


def _safe_ad_url(url):
    """Return url only if it uses http/https scheme; otherwise return None."""
    if url and isinstance(url, str):
        stripped = url.strip()
        if stripped.lower().startswith(('http://', 'https://')):
            return stripped
    return None


def ad_click_track(request, ad_id):
    """Tracks click and redirects to destination."""
    try:
        ad = Advertisement.objects.get(pk=ad_id, status='active')
        Advertisement.objects.filter(pk=ad_id).update(clicks=F('clicks') + 1)
        safe_url = _sponsor_website(request, ad.link_url)
        if safe_url:
            return redirect(safe_url)
        return redirect('sponsored_ad_detail', ad_id=ad.pk)
    except Advertisement.DoesNotExist:
        pass
    return redirect('ads_gallery')


def adpost_click_track(request, ad_id):
    """Tracks click on an AdPost and redirects to its website."""
    from .models import AdPost
    try:
        ad = AdPost.objects.get(pk=ad_id, status='approved')
        AdPost.objects.filter(pk=ad_id).update(clicks=F('clicks') + 1)
        safe_url = _sponsor_website(request, ad.website)
        if safe_url:
            return redirect(safe_url)
        return redirect('sponsored_post_detail', ad_id=ad.pk)
    except AdPost.DoesNotExist:
        pass
    return redirect('ads_gallery')


def _sponsor_website(request, value):
    """Use valid websites while avoiding circular homepage ad destinations."""
    from urllib.parse import urlsplit
    safe = _safe_ad_url(value)
    if safe:
        destination = urlsplit(safe)
        current_host = request.get_host().split(':')[0].removeprefix('www.')
        if (destination.hostname or '').removeprefix('www.') == current_host and destination.path in ('', '/'):
            return None
    return safe


def sponsored_detail(request, ad_id, kind):
    if kind == 'post':
        ad = get_object_or_404(AdPost.objects.select_related('user__company'), pk=ad_id, status='approved')
        title, description, image, owner, website = ad.title or ad.company_name, ad.description, ad.image, ad.user, ad.website
        phone = ad.contact_phone or getattr(owner, 'phone', '')
    elif kind == 'banner':
        ad = get_object_or_404(Advertiser.objects.select_related('user__company'), pk=ad_id, status='approved')
        title, description, image, owner, website = ad.business_name, ad.description, ad.banner_image, ad.user, ad.website
        phone = ad.phone
    else:
        ad = get_object_or_404(Advertisement.objects.select_related('advertiser__user__company'), pk=ad_id, status='active')
        title, description, image, owner, website = ad.title, ad.content, ad.image, ad.advertiser.user, ad.link_url
        phone = ad.advertiser.phone
    return render(request, 'sponsored_detail.html', {
        'sponsor_title': title, 'sponsor_description': description, 'sponsor_image': image,
        'promotion_ad_id': ad.pk if kind == 'post' else None,
        'sponsor_company': getattr(owner, 'company', None),
        'sponsor_website': _sponsor_website(request, website), 'sponsor_phone': phone,
    })


# ── ADMIN: Advertiser Management ─────────────────────────────────────────────

def admin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_advertisers(request):
    from urllib.parse import quote
    status_filter = request.GET.get('status', 'pending')
    advs = Advertiser.objects.filter(status=status_filter).order_by('-created_at')
    counts = {s: Advertiser.objects.filter(status=s).count()
              for s in ('pending', 'approved', 'rejected', 'suspended')}
    for adv in advs:
        phone = ''.join(ch for ch in (adv.phone or '') if ch.isdigit())
        if phone and not phone.startswith('91'):
            phone = '91' + phone
        name = adv.contact_person or adv.business_name
        msg_inquiry = f"Hi {name}, we received your advertiser registration ({adv.business_name}) on Local From. Are you interested in proceeding? Please confirm."
        msg_reject  = (
            f"Hi {name}, we received your advertiser registration ({adv.business_name}) on Local From. "
            f"Unfortunately, we are unable to approve this ad account creation. "
            f"Please make necessary edits and re-apply. "
            f"If you feel everything is correct, reach us at +91 9361240355, or email localfrom8@gmail.com. Thanks"
        )
        adv.wa_link        = f"https://wa.me/{phone}?text={quote(msg_inquiry)}" if phone else ''
        adv.wa_link_reject = f"https://wa.me/{phone}?text={quote(msg_reject)}"  if phone else ''
    return render(request, 'admin_advertisers.html', {
        'advs': advs, 'status_filter': status_filter, 'counts': counts,
    })


@admin_required
@require_POST
@transaction.atomic
def admin_approve_advertiser(request, adv_id):
    adv = get_object_or_404(Advertiser.objects.select_for_update(), pk=adv_id)
    if adv.status=='approved':
        return redirect('admin_advertisers')
    adv.status      = 'approved'
    adv.approved_at = timezone.now()
    adv.save()
    send_review_message(request.user,adv.user,'Your advertiser account is approved',
        f'Your advertiser account for {adv.business_name} has been approved. You can now manage your advertising.',
        '/advertiser/dashboard/')
    messages.success(request, f'{adv.business_name} approved!')
    return redirect('admin_advertisers')


@admin_required
def admin_reject_advertiser(request, adv_id):
    adv = get_object_or_404(Advertiser, pk=adv_id)
    adv.status         = 'rejected'
    adv.rejection_note = request.POST.get('note', '')
    adv.save()
    messages.info(request, f'{adv.business_name} rejected.')
    return redirect('admin_advertisers')


@admin_required
def admin_remove_advertiser(request, adv_id):
    if request.method == 'POST':
        adv = get_object_or_404(Advertiser, pk=adv_id)
        name = adv.business_name
        adv.delete()
        messages.success(request, f'{name} removed.')
    return redirect('admin_advertisers')


@admin_required
def admin_upload_advertiser_banner(request, adv_id):
    if request.method == 'POST':
        adv = get_object_or_404(Advertiser, pk=adv_id)
        if 'banner_image' in request.FILES:
            adv.banner_image = request.FILES['banner_image']
            adv.save()
            messages.success(request, f'Banner uploaded for {adv.business_name}.')
    return redirect(f'/admin-panel/advertisers/?status={request.POST.get("status", "approved")}')


@admin_required
def admin_ad_list(request):
    from urllib.parse import quote
    status_filter = request.GET.get('status', 'pending_review')
    ads = Advertisement.objects.filter(status=status_filter).select_related('advertiser', 'package').order_by('-created_at')
    for ad in ads:
        phone = ''.join(ch for ch in (ad.advertiser.phone or '') if ch.isdigit())
        if phone and not phone.startswith('91'):
            phone = '91' + phone
        name = ad.advertiser.contact_person or ad.advertiser.business_name
        msg = f"Hi {name}, we received your ad '{ad.title}' on Pincode Job Portal. Are you interested in proceeding? Please confirm."
        ad.wa_link = f"https://wa.me/{phone}?text={quote(msg)}" if phone else ''
    return render(request, 'admin_ad_list.html', {'ads': ads, 'status_filter': status_filter})


@admin_required
def admin_set_ad_image(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id)
    if request.method == 'POST' and 'image' in request.FILES:
        ad.image = request.FILES['image']
        ad.save()
        messages.success(request, f'Image updated for "{ad.title}".')
    status_filter = request.POST.get('status_filter', 'pending_review')
    return redirect(f"/admin-panel/ads/?status={status_filter}")


@admin_required
@require_POST
@transaction.atomic
def admin_activate_ad(request, ad_id):
    ad = get_object_or_404(Advertisement.objects.select_for_update().select_related('advertiser__user'), pk=ad_id)
    if ad.status=='active':
        return redirect('admin_ad_list')
    ad.status = 'active'
    ad.save()
    Advertisement.objects.filter(pk=ad_id).update(views=ad.views)
    send_review_message(request.user,ad.advertiser.user,'Your advertisement is approved',
        f'Your advertisement "{ad.title}" has been approved and is now live.',
        '/advertiser/dashboard/')
    messages.success(request, f'Ad "{ad.title}" is now live!')
    return redirect('admin_ad_list')


@admin_required
def admin_reject_ad(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id)
    ad.status = 'rejected'
    ad.save()
    messages.info(request, f'Ad "{ad.title}" rejected.')
    return redirect('admin_ad_list')


@admin_required
def admin_delete_ad(request, ad_id):
    ad = get_object_or_404(Advertisement, pk=ad_id)
    title = ad.title
    status_filter = request.POST.get('status_filter', 'pending_review')
    ad.delete()
    messages.success(request, f'Ad "{title}" deleted.')
    return redirect(f'/admin-panel/ads/?status={status_filter}')


# ── ADMIN USERS LIST ────────────────────────────────────────────────────────
@admin_required
def admin_users(request):
    return _users_list(request)


def super_admin_users(request):
    if not request.user.is_authenticated or request.user.admin_role != 'super_admin':
        messages.error(request, 'Super Admin access required.')
        return redirect('login')
    return _users_list(request)


def super_admin_delete_user(request, user_id):
    if not request.user.is_authenticated or request.user.admin_role != 'super_admin':
        messages.error(request, 'Super Admin access required.')
        return redirect('login')
    if request.method != 'POST':
        return redirect('super_admin_users')
    target = get_object_or_404(User, pk=user_id)
    if target.admin_role == 'super_admin':
        messages.error(request, 'Cannot delete another Super Admin.')
        return redirect('super_admin_users')
    name = target.get_full_name() or target.username
    target.delete()
    messages.success(request, f'User "{name}" deleted.')
    return redirect('super_admin_users')


def _users_list(request):
    from django.db.models import Q
    search   = request.GET.get('q', '').strip()
    utype    = request.GET.get('type', '')

    qs = User.objects.exclude(user_type='advertiser').order_by('-date_joined')

    if utype == 'employer':
        qs = qs.filter(user_type__in=User.EMPLOYER_TYPES)
    elif utype == 'personal':
        qs = qs.filter(user_type__in=['employee', 'individual', 'freelancer'])
    elif utype == 'admin':
        qs = qs.exclude(admin_role='')

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search) |
            Q(phone__icontains=search) | Q(email__icontains=search) |
            Q(pincode__icontains=search) | Q(city__icontains=search)
        )

    employer_count  = User.objects.filter(user_type__in=User.EMPLOYER_TYPES).count()
    jobseeker_count = User.objects.filter(user_type__in=['employee','individual','freelancer']).count()
    admin_count     = User.objects.exclude(admin_role='').count()

    return render(request, 'admin_users.html', {
        'users': qs,
        'search': search,
        'utype': utype,
        'employer_count': employer_count,
        'jobseeker_count': jobseeker_count,
        'admin_count': admin_count,
        'total_count': User.objects.exclude(user_type='advertiser').count(),
    })


# ── ADMIN PANEL LOGIN ────────────────────────────────────────────────────────
def admin_panel_login(request):
    if request.method != 'POST':
        return redirect('home')
    if not _rate_limit(f'admin_login_{_get_client_ip(request)}', max_attempts=5, window_seconds=300):
        messages.error(request, 'Too many login attempts. Please wait 5 minutes.')
        return redirect('home')
    phone    = request.POST.get('phone', '').strip()
    password = request.POST.get('password', '').strip()
    user = authenticate(request, username=phone, password=password)
    if user and getattr(user, 'admin_role', None):
        login(request, user, backend='jobs.backends.PhoneOrEmailBackend')
        role = user.admin_role
        if role == 'scoped_admin':
            return redirect('assigned_dashboard')
        if role == 'super_admin':
            return redirect('/super-admin/')
        elif role == 'state_admin':
            return redirect('/state-admin/')
        else:
            return redirect('/district-admin/')
    messages.error(request, 'Invalid phone number / password, or not an admin account.')
    return redirect('home')


# ==============================================================
# ADMIN HIERARCHY MODULE  (Super → State → District)
# ==============================================================
from functools import wraps

def super_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.admin_role != 'super_admin':
            messages.error(request, 'Super Admin access required.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper



def state_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.admin_role not in ('super_admin', 'state_admin'):
            messages.error(request, 'State Admin access required.')
            return redirect('login')
        from .legacy_admin_security import state_for
        state_for(request.user)
        return view_func(request, *args, **kwargs)
    return wrapper

def district_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.admin_role not in ('super_admin', 'state_admin', 'district_admin'):
            messages.error(request, 'District Admin access required.')
            return redirect('login')
        from .legacy_admin_security import district_scope
        district_scope(request.user)
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── SUPER ADMIN ──────────────────────────────────────────────────────────────

@login_required
def post_simple_ad(request):
    from .models import AdPost, AdSettings
    if not request.user.is_authenticated:
        return redirect(f'/login/?next=/ads/post/')
    adv = getattr(request.user, 'advertiser', None)
    if not adv:
        messages.error(request, 'Please register as an advertiser first.')
        return redirect('advertiser_register')
    if adv.status != 'approved':
        messages.error(request, 'Your advertiser account is pending admin approval. You can create ads once approved.')
        return redirect('advertiser_dashboard')
    if request.method == 'POST':
        import base64, io
        from django.core.files.base import ContentFile
        company_name = request.POST.get('company_name', '').strip()
        pincode      = request.POST.get('pincode', '').strip()
        description  = request.POST.get('description', '').strip()[:160]
        website      = request.POST.get('website', '').strip()
        image_data   = request.POST.get('image_data', '').strip()
        image        = request.FILES.get('image')
        # Prefer cropped base64 data over raw file
        if image_data and image_data.startswith('data:image'):
            fmt, b64 = image_data.split(';base64,', 1)
            ext = fmt.split('/')[-1].replace('jpeg', 'jpg')
            image = ContentFile(base64.b64decode(b64), name=f'ad_{request.user.pk}.{ext}')
        if not company_name or not description or not image:
            messages.error(request, 'Company name, description and image are required.')
            return redirect('post_simple_ad')
        AdPost.objects.create(
            user=request.user,
            company_name=company_name,
            pincode=pincode,
            description=description,
            website=website,
            image=image,
        )
        messages.success(request, 'Ad submitted! Admin will review and publish it shortly.')
        return redirect('my_simple_ads')
    ads      = AdPost.objects.filter(user=request.user).prefetch_related('renewals')
    settings = AdSettings.get()
    return render(request, 'post_simple_ad.html', {'ads': ads, 'settings': settings})


@login_required
def my_simple_ads(request):
    from .models import AdPost, AdSettings
    ads      = AdPost.objects.filter(user=request.user).prefetch_related('renewals')
    settings = AdSettings.get()
    return render(request, 'my_simple_ads.html', {'ads': ads, 'settings': settings})


@login_required
def renew_ad(request, pk):
    from .models import AdPost, AdRenewal, AdSettings
    ad = get_object_or_404(AdPost, pk=pk, user=request.user)
    settings = AdSettings.get()
    if request.method == 'POST':
        transaction_id = request.POST.get('transaction_id', '').strip()
        screenshot     = request.FILES.get('screenshot')
        if not transaction_id or not screenshot:
            messages.error(request, 'Transaction ID and screenshot are required.')
            return redirect('renew_ad', pk=pk)
        AdRenewal.objects.create(
            ad=ad,
            transaction_id=transaction_id,
            screenshot=screenshot,
            amount=settings.renewal_price,
        )
        messages.success(request, 'Renewal request submitted! Admin will verify and extend your ad.')
        return redirect('my_simple_ads')
    return render(request, 'renew_ad.html', {'ad': ad, 'settings': settings})


@super_admin_required
@transaction.atomic
def admin_ad_posts(request):
    from .models import AdPost, AdRenewal, AdSettings
    from django.utils import timezone
    import datetime
    settings = AdSettings.get()
    if request.method == 'POST':
        action = request.POST.get('action')
        # ── renewal actions ──────────────────────────────────────────────
        if action in ('approve_renewal', 'reject_renewal'):
            renewal = get_object_or_404(AdRenewal.objects.select_for_update(), pk=request.POST.get('renewal_id'))
            if renewal.status!='pending':
                messages.info(request,'This renewal has already been reviewed.')
                return redirect('admin_ad_posts')
            if action == 'approve_renewal':
                renewal.status      = 'approved'
                renewal.approved_at = timezone.now()
                renewal.save()
                ad = renewal.ad
                today = timezone.now().date()
                base = max(ad.expires_at, today) if ad.expires_at else today
                ad.expires_at = base + datetime.timedelta(days=settings.renewal_days)
                ad.status     = 'approved'
                ad.save()
                send_review_message(request.user,ad.user,'Your ad renewal is approved',
                    f'Your ad renewal for {ad.company_name} has been approved. Your ad is live until {ad.expires_at:%d %b %Y}.',
                    '/ads/my-ads/')
                messages.success(request, f'Renewal approved. Ad live until {ad.expires_at}.')
            else:
                renewal.status      = 'rejected'
                renewal.reject_note = request.POST.get('reject_note', '').strip()
                renewal.save()
                messages.success(request, 'Renewal rejected.')
            return redirect('admin_ad_posts')
        # ── ad actions ───────────────────────────────────────────────────
        ad = get_object_or_404(AdPost.objects.select_for_update(), pk=request.POST.get('ad_id'))
        if action in ('approve','reject') and ad.status!='pending':
            messages.info(request,'This application has already been reviewed.')
            return redirect('admin_ad_posts')
        if action == 'approve':
            ad.status      = 'approved'
            ad.approved_at = timezone.now()
            ad.expires_at  = timezone.now().date() + datetime.timedelta(days=settings.renewal_days)
            ad.reject_note = ''
            ad.save()
            send_review_message(
                sender=request.user,owner=ad.user,
                title='Your ad is LIVE!',
                body=f'Your ad "{ad.company_name}" has been approved and is now live until {ad.expires_at.strftime("%d %b %Y")}. Check My Ads to view it.',
                notif_type='success',link='/ads/my-ads/',
            )
            messages.success(request, f'"{ad.company_name}" approved — live for {settings.renewal_days} days.')
        elif action == 'reject':
            ad.status      = 'rejected'
            ad.reject_note = request.POST.get('reject_note', '').strip()
            ad.save()
            UserNotification.objects.create(
                user=ad.user,
                title='Ad not approved',
                message=f'Your ad "{ad.company_name}" was not approved.{" Reason: " + ad.reject_note if ad.reject_note else " Please review and resubmit."}',
                notif_type='warning',
            )
            messages.success(request, f'"{ad.company_name}" rejected.')
        elif action == 'delete':
            ad.delete()
            messages.success(request, 'Ad deleted.')
        return redirect('admin_ad_posts')

    ads = AdPost.objects.select_related('user').prefetch_related('renewals').order_by('-created_at')
    renewals       = AdRenewal.objects.select_related('ad__user').filter(status='pending').order_by('-created_at')
    pending_count  = ads.filter(status='pending').count()
    approved_count = ads.filter(status='approved').count()
    renewal_count  = renewals.count()
    status_filter  = request.GET.get('status', '')
    tab            = request.GET.get('tab', 'ads')
    if status_filter:
        ads = ads.filter(status=status_filter)
    return render(request, 'admin_ad_posts.html', {
        'ads': ads,
        'renewals': renewals,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'renewal_count': renewal_count,
        'status_filter': status_filter,
        'tab': tab,
        'settings': settings,
    })


@super_admin_required
def admin_ad_settings(request):
    from .models import AdSettings
    settings = AdSettings.get()
    if request.method == 'POST':
        settings.upi_id        = request.POST.get('upi_id', '').strip()
        settings.renewal_price = int(request.POST.get('renewal_price') or 199)
        settings.renewal_days  = int(request.POST.get('renewal_days') or 30)
        settings.save()
        messages.success(request, 'Ad settings saved.')
        return redirect('admin_ad_posts')
    return redirect('admin_ad_posts')


def admin_feedback(request):
    if request.method == 'POST':
        complaint_id = request.POST.get('complaint_id')
        complaint = get_object_or_404(Complaint, pk=complaint_id)
        complaint.status     = request.POST.get('status', complaint.status)
        complaint.resolution = request.POST.get('resolution', '').strip()
        complaint.save()
        messages.success(request, 'Feedback updated.')
        return redirect('admin_feedback')
    status_filter = request.GET.get('status', '')
    qs = Complaint.objects.select_related('submitted_by').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'admin_feedback.html', {
        'complaints': qs,
        'status_filter': status_filter,
        'open_count':       Complaint.objects.filter(status='open').count(),
        'in_review_count':  Complaint.objects.filter(status='in_review').count(),
        'resolved_count':   Complaint.objects.filter(status='resolved').count(),
    })


@super_admin_required
@transaction.atomic
def admin_flicks(request):
    from .models import Flick, FlickAdPayment, FlickAdSettings
    from django.utils import timezone
    flicks   = Flick.objects.select_related('user').order_by('-created_at')
    payments = FlickAdPayment.objects.select_related('flick', 'user').filter(status='pending').order_by('-created_at')
    settings = FlickAdSettings.get()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_settings':
            settings.upi_id        = request.POST.get('upi_id', settings.upi_id).strip()
            settings.price         = request.POST.get('price', settings.price)
            settings.duration_days = request.POST.get('duration_days', settings.duration_days)
            settings.save()
            messages.success(request, 'Settings saved.')
            return redirect('admin_flicks')

        if action in ('approve_payment', 'reject_payment'):
            pay = get_object_or_404(FlickAdPayment.objects.select_for_update(), pk=request.POST.get('payment_id'))
            if pay.status!='pending':
                messages.info(request,'This payment has already been reviewed.')
                return redirect('admin_flicks')
            if action == 'approve_payment':
                pay.status      = 'approved'
                pay.approved_at = timezone.now()
                pay.save()
                flick = pay.flick
                flick.is_promoted    = True
                flick.advertise_plan = 'basic'
                flick.promoted_until = (timezone.now().date() +
                                        timezone.timedelta(days=pay.duration_days))
                flick.save()
                send_review_message(request.user,pay.user,'Your video promotion is approved',
                    f'Your video promotion payment has been approved. Your video is promoted until {flick.promoted_until:%d %b %Y}.',
                    '/flicks/')
                messages.success(request, f'Payment approved. Flick promoted until {flick.promoted_until}.')
            else:
                pay.status = 'rejected'
                pay.save()
                messages.success(request, 'Payment rejected.')
            return redirect('admin_flicks')

        flick_id = request.POST.get('flick_id')
        flick = get_object_or_404(Flick, pk=flick_id)
        if action == 'delete':
            flick.delete()
            messages.success(request, 'Flick deleted.')
        elif action == 'set_plan':
            flick.advertise_plan = request.POST.get('plan', '')
            flick.is_promoted    = (flick.advertise_plan != '')
            flick.save()
            messages.success(request, f'Plan updated to "{flick.advertise_plan or "No Plan"}".')
        return redirect('admin_flicks')

    return render(request, 'admin_flicks.html', {
        'flicks': flicks,
        'payments': payments,
        'settings': settings,
    })


@login_required
def report_flick(request, pk):
    from .models import Flick, FlickReport
    if request.method != 'POST':
        return JsonResponse({'success': False})
    flick  = get_object_or_404(Flick, pk=pk)
    reason = request.POST.get('reason', '').strip()
    note   = request.POST.get('note', '').strip()
    if not reason:
        return JsonResponse({'success': False, 'error': 'Reason required'})
    if flick.user == request.user:
        return JsonResponse({'success': False, 'error': 'Cannot report your own flick'})
    obj, created = FlickReport.objects.get_or_create(
        flick=flick, user=request.user,
        defaults={'reason': reason, 'note': note}
    )
    if not created:
        return JsonResponse({'success': False, 'already': True, 'error': 'Already reported'})
    return JsonResponse({'success': True})


@super_admin_required
def admin_flick_reports(request):
    from .models import FlickReport, Flick
    if request.method == 'POST':
        action    = request.POST.get('action')
        report_id = request.POST.get('report_id')
        report    = get_object_or_404(FlickReport, pk=report_id)
        if action == 'delete_flick':
            report.flick.delete()
            messages.success(request, 'Flick deleted.')
        elif action == 'dismiss':
            report.status = 'dismissed'
            report.save()
            messages.success(request, 'Report dismissed.')
        elif action == 'reviewed':
            report.status = 'reviewed'
            report.save()
            messages.success(request, 'Marked as reviewed.')
        return redirect('admin_flick_reports')

    status_filter = request.GET.get('status', 'pending')
    qs = FlickReport.objects.select_related('flick', 'flick__user', 'user').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'admin_flick_reports.html', {
        'reports':       qs,
        'status_filter': status_filter,
        'pending_count': FlickReport.objects.filter(status='pending').count(),
    })


@login_required
def flick_advertise(request, pk):
    from .models import Flick, FlickAdPayment, FlickAdSettings
    flick    = get_object_or_404(Flick, pk=pk, user=request.user)
    settings = FlickAdSettings.get()
    pending  = FlickAdPayment.objects.filter(flick=flick, status='pending').exists()

    if request.method == 'POST':
        txn_id = request.POST.get('transaction_id', '').strip()
        if not txn_id:
            messages.error(request, 'Please enter the UPI Transaction ID.')
            return redirect('flick_advertise', pk=pk)
        if pending:
            messages.error(request, 'You already have a pending payment for this flick.')
            return redirect('flicks_feed')
        FlickAdPayment.objects.create(
            flick=flick,
            user=request.user,
            transaction_id=txn_id,
            amount=settings.price,
            duration_days=settings.duration_days,
        )
        messages.success(request, 'Payment submitted! Admin will verify and activate your promotion shortly.')
        return redirect('flicks_feed')

    return render(request, 'flick_advertise.html', {
        'flick': flick,
        'settings': settings,
        'pending': pending,
    })


@super_admin_required
def super_admin_dashboard(request):
    from .models import AdminActivity
    return render(request, 'super_admin_dashboard.html', {
        'total_users': User.objects.count(), 'total_businesses': CompanyProfile.objects.count(),
        'pending_adverts': Advertiser.objects.filter(status='pending').count(),
        'pending_ad_posts': AdPost.objects.filter(status='pending').count(),
        'pending_offers_count': LocalOffer.objects.filter(is_active=False).count(),
        'recent_admin_activity': AdminActivity.objects.all()[:10],
    })


@super_admin_required
def manage_states(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        if name and code:
            State.objects.get_or_create(name=name, defaults={'code': code, 'created_by': request.user})
            messages.success(request, f'State "{name}" created.')
        return redirect('manage_states')
    states = State.objects.annotate(d_count=Count('districts')).order_by('name')
    return render(request, 'manage_states.html', {'states': states})


@super_admin_required
def toggle_state(request, pk):
    state = get_object_or_404(State, pk=pk)
    state.is_active = not state.is_active
    state.save()
    messages.success(request, f'State "{state.name}" {"activated" if state.is_active else "deactivated"}.')
    return redirect('manage_states')


@super_admin_required
def manage_districts(request, state_id):
    state = get_object_or_404(State, pk=state_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            District.objects.get_or_create(state=state, name=name)
            messages.success(request, f'District "{name}" created.')
        return redirect('manage_districts', state_id=state_id)
    districts = state.districts.all()
    return render(request, 'manage_districts.html', {'state': state, 'districts': districts})


@super_admin_required
def create_state_admin(request):
    states = State.objects.filter(is_active=True)
    if request.method == 'POST':
        fullname = request.POST.get('fullname', '').strip()
        phone    = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        state_id = request.POST.get('state_id')
        state    = get_object_or_404(State, pk=state_id)
        if not phone or not phone.isdigit() or len(phone) != 10:
            messages.error(request, 'Enter a valid 10-digit mobile number.')
        elif User.objects.filter(username=phone).exists():
            messages.error(request, 'A login already exists with this mobile number.')
        else:
            parts = fullname.split(' ', 1)
            user  = User.objects.create_user(
                username=phone, password=password,
                first_name=parts[0], last_name=parts[1] if len(parts) > 1 else '',
                phone=phone, admin_role='state_admin'
            )
            AdminProfile.objects.create(user=user, role='state_admin', state=state, appointed_by=request.user)
            messages.success(request, f'State Admin "{fullname}" created for {state.name}. Login with mobile {phone}.')
            return redirect('manage_state_admins')
    return render(request, 'create_state_admin.html', {'states': states})


@super_admin_required
def manage_state_admins(request):
    admins = AdminProfile.objects.filter(role='state_admin').select_related('user', 'state').order_by('state__name')
    return render(request, 'manage_state_admins.html', {'admins': admins})


@super_admin_required
def toggle_admin(request, pk):
    profile = get_object_or_404(AdminProfile, pk=pk)
    profile.is_active = not profile.is_active
    profile.user.is_active = profile.is_active
    profile.user.save()
    profile.save()
    messages.success(request, f'Admin {"activated" if profile.is_active else "suspended"}.')
    return redirect(request.META.get('HTTP_REFERER', 'super_admin_dashboard'))


@super_admin_required
def manage_industries(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            name   = request.POST.get('name', '').strip()
            collar = request.POST.get('collar', 'both')
            icon   = request.POST.get('icon', 'fas fa-industry').strip()
            if name:
                Industry.objects.get_or_create(name=name, defaults={'collar': collar, 'icon': icon})
                messages.success(request, f'Industry "{name}" added.')
        elif action == 'toggle':
            pk = request.POST.get('pk')
            ind = get_object_or_404(Industry, pk=pk)
            ind.is_active = not ind.is_active
            ind.save()
        return redirect('manage_industries')
    industries = Industry.objects.annotate(role_count=Count('roles'))
    return render(request, 'manage_industries.html', {'industries': industries})


@super_admin_required
def manage_ad_packages(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            AdPackage.objects.create(
                name          = request.POST.get('name', '').strip(),
                ad_type       = request.POST.get('ad_type', 'homepage_banner'),
                duration_days = request.POST.get('duration_days', 30),
                price         = request.POST.get('price', 0),
                description   = request.POST.get('description', '').strip(),
                size_specs    = request.POST.get('size_specs', '').strip(),
                is_active     = True,
            )
            messages.success(request, 'Package created.')
        elif action == 'toggle':
            pkg = get_object_or_404(AdPackage, pk=request.POST.get('pk'))
            pkg.is_active = not pkg.is_active
            pkg.save()
        elif action == 'delete':
            pkg = get_object_or_404(AdPackage, pk=request.POST.get('pk'))
            pkg.delete()
            messages.success(request, 'Package deleted.')
        elif action == 'edit':
            pkg = get_object_or_404(AdPackage, pk=request.POST.get('pk'))
            pkg.name          = request.POST.get('name', pkg.name).strip()
            pkg.ad_type       = request.POST.get('ad_type', pkg.ad_type)
            pkg.duration_days = request.POST.get('duration_days', pkg.duration_days)
            pkg.price         = request.POST.get('price', pkg.price)
            pkg.description   = request.POST.get('description', pkg.description).strip()
            pkg.size_specs    = request.POST.get('size_specs', pkg.size_specs).strip()
            pkg.save()
            messages.success(request, 'Package updated.')
        return redirect('manage_ad_packages')
    packages = AdPackage.objects.order_by('ad_type', 'price')
    return render(request, 'manage_ad_packages.html', {'packages': packages})


@super_admin_required
def manage_discounts(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            Discount.objects.create(
                code          = request.POST.get('code', '').strip().upper(),
                description   = request.POST.get('description', '').strip(),
                discount_type = request.POST.get('discount_type', 'percent'),
                value         = request.POST.get('value', 0),
                min_amount    = request.POST.get('min_amount', 0),
                max_uses      = request.POST.get('max_uses', 0),
                valid_from    = request.POST.get('valid_from') or None,
                valid_until   = request.POST.get('valid_until') or None,
            )
            messages.success(request, 'Discount code created.')
        elif action == 'toggle':
            d = get_object_or_404(Discount, pk=request.POST.get('pk'))
            d.is_active = not d.is_active
            d.save()
        return redirect('manage_discounts')
    discounts = Discount.objects.all().order_by('-created_at')
    return render(request, 'manage_discounts.html', {'discounts': discounts})


@super_admin_required
def manage_pincodes(request, district_id=None):
    states = State.objects.all().order_by('name')
    district_id = district_id or request.GET.get('district_id')
    if district_id and not str(district_id).isdigit():
        district_id = None
    selected = get_object_or_404(District.objects.select_related('state'), pk=district_id) if district_id else None
    state_id = str(selected.state_id) if selected else request.GET.get('state_filter', '')
    if state_id and not state_id.isdigit():
        state_id = ''
    districts = District.objects.select_related('state').order_by('state__name', 'name')
    if state_id:
        districts = districts.filter(state_id=state_id)
    if request.method == 'POST' and selected:
        code      = request.POST.get('code', '').strip()
        area_name = request.POST.get('area_name', '').strip()
        if code:
            PinCode.objects.get_or_create(district=selected, code=code, defaults={'area_name': area_name})
            messages.success(request, f'PIN {code} added.')
        return redirect('manage_pincodes', district_id=selected.pk)
    pincodes = selected.pincodes.all() if selected else []
    return render(request, 'manage_pincodes.html', {'states': states, 'state_filter': state_id, 'districts': districts, 'selected': selected, 'pincodes': pincodes})


@super_admin_required
def manage_notifications(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            SystemNotification.objects.create(
                title       = request.POST.get('title', '').strip(),
                message     = request.POST.get('message', '').strip(),
                notif_type  = request.POST.get('notif_type', 'info'),
                target_role = request.POST.get('target_role', '').strip(),
                created_by  = request.user,
            )
            messages.success(request, 'Notification created.')
        elif action == 'toggle':
            n = get_object_or_404(SystemNotification, pk=request.POST.get('pk'))
            n.is_active = not n.is_active
            n.save()
        return redirect('manage_notifications')
    notifs = SystemNotification.objects.all()
    return render(request, 'manage_notifications.html', {'notifs': notifs})


@login_required
def mark_all_notifications_read(request):
    from .notifications import mark_all_read
    return mark_all_read(request)


def terms(request):
    return render(request, 'terms.html')


def privacy(request):
    return render(request, 'privacy.html')


def about_page(request):
    return render(request, 'about.html')


def favicon(request):
    from django.contrib.staticfiles import finders
    from django.http import FileResponse
    return FileResponse(open(finders.find('images/favicon.ico'), 'rb'), content_type='image/x-icon')


# ── FLICKS ────────────────────────────────────────────────────────────────────

def flicks_feed(request):
    from .models import Flick, FlickLike
    from django.utils import timezone
    today = timezone.now().date()
    cat = request.GET.get('cat', '')
    flicks = Flick.objects.select_related('user').prefetch_related('likes', 'comments').extra(
        select={'is_paid_active': "CASE WHEN promoted_until >= %s THEN 1 ELSE 0 END"},
        select_params=[today],
        order_by=['-is_paid_active', '-created_at'],
    )
    if cat:
        flicks = flicks.filter(category=cat)
    liked_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(FlickLike.objects.filter(user=request.user).values_list('flick_id', flat=True))
    return render(request, 'flicks.html', {'flicks': flicks, 'liked_ids': liked_ids, 'today': today, 'active_cat': cat})


@login_required
def post_flick(request):
    from .models import Flick
    if request.method == 'POST':
        title    = request.POST.get('title', '').strip()
        caption  = request.POST.get('caption', '').strip()
        category = request.POST.get('category', 'general')
        video    = request.FILES.get('video')
        image    = request.FILES.get('image')
        if not caption and not video and not image:
            messages.error(request, 'Add a caption, image, or video.')
            return redirect('post_flick')
        Flick.objects.create(user=request.user, title=title, caption=caption,
                             category=category, video=video, image=image)
        messages.success(request, 'Flick posted!')
        return redirect('flicks_feed')
    return render(request, 'post_flick.html')


@login_required
def like_flick(request, pk):
    from .models import Flick, FlickLike
    if request.method != 'POST':
        return JsonResponse({'success': False})
    flick = get_object_or_404(Flick, pk=pk)
    like, created = FlickLike.objects.get_or_create(flick=flick, user=request.user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    return JsonResponse({'success': True, 'liked': liked, 'count': flick.like_count()})


@login_required
def comment_flick(request, pk):
    from .models import Flick, FlickComment
    if request.method != 'POST':
        return JsonResponse({'success': False})
    import json
    data = json.loads(request.body)
    text = data.get('text', '').strip()
    if not text:
        return JsonResponse({'success': False, 'error': 'Empty comment'})
    flick = get_object_or_404(Flick, pk=pk)
    c = FlickComment.objects.create(flick=flick, user=request.user, text=text)
    return JsonResponse({
        'success': True,
        'name': request.user.get_full_name() or request.user.username,
        'text': c.text,
        'time': c.created_at.strftime('%d %b %Y'),
    })


@login_required
def delete_flick(request, pk):
    from .models import Flick
    flick = get_object_or_404(Flick, pk=pk, user=request.user)
    flick.delete()
    messages.success(request, 'Flick deleted.')
    return redirect('flicks_feed')


@super_admin_required
def national_analytics(request):
    profile = getattr(request.user, 'admin_profile', None)
    businesses = CompanyProfile.objects.select_related('user').all()
    complaints = Complaint.objects.all()
    if request.user.admin_role == 'district_admin':
        district = profile.district if profile else None
        pins = district.pincodes.values_list('code', flat=True) if district else []
        businesses = businesses.filter(user__pincode__in=pins)
        complaints = complaints.filter(district=district)
    elif request.user.admin_role == 'state_admin':
        state = profile.state if profile else None
        pins = PinCode.objects.filter(district__state=state).values_list('code', flat=True)
        businesses = businesses.filter(user__pincode__in=pins)
        complaints = complaints.filter(district__state=state)
    return render(request, 'national_analytics.html', {'report_title': 'National analytics', 'business_count': businesses.count(),
        'open_complaints': complaints.filter(status='open').count(), 'businesses': businesses[:20]})


# ─── STATE ADMIN ──────────────────────────────────────────────────────────────

@state_admin_required
def state_admin_dashboard(request):
    from .legacy_admin_security import state_for, manageable_users
    profile  = getattr(request.user, 'admin_profile', None)
    state = state_for(request.user)
    districts= state.districts.all() if state else District.objects.all()
    pending_employers = manageable_users(request.user).filter(
        user_type__in=User.EMPLOYER_TYPES, is_active=True
    ).count()
    complaints = Complaint.objects.filter(status='open')
    if state is not None:
        complaints = complaints.filter(district__state=state)
    open_complaints = complaints.count()
    district_admins = AdminProfile.objects.filter(role='district_admin')
    if state is not None:
        district_admins = district_admins.filter(state=state)
    return render(request, 'state_admin_dashboard.html', {
        'state': state, 'districts': districts,
        'pending_employers': pending_employers,
        'open_complaints': open_complaints,
        'district_admins': district_admins,
        'district_count': districts.count(),
    })


@state_admin_required
def create_district_admin(request):
    from .legacy_admin_security import state_for
    state = state_for(request.user)
    districts= state.districts.all() if state else District.objects.all()
    if request.method == 'POST':
        fullname    = request.POST.get('fullname', '').strip()
        phone       = request.POST.get('phone', '').strip()
        password    = request.POST.get('password', '').strip()
        district_id = request.POST.get('district_id')
        district    = get_object_or_404(districts.filter(is_active=True), pk=district_id)
        if not phone or not phone.isdigit() or len(phone) != 10:
            messages.error(request, 'Enter a valid 10-digit mobile number.')
        elif User.objects.filter(Q(username=phone) | Q(phone=phone) | Q(business_phone=phone)).exists():
            messages.error(request, 'A login already exists with this mobile number.')
        elif len(password) < 8:
            messages.error(request, 'Use at least 8 characters for the admin password.')
        else:
            parts = fullname.split(' ', 1)
            user  = User.objects.create_user(
                username=phone, password=password,
                first_name=parts[0], last_name=parts[1] if len(parts) > 1 else '',
                phone=phone, admin_role='district_admin'
            )
            AdminProfile.objects.create(
                user=user, role='district_admin',
                state=district.state, district=district,
                appointed_by=request.user
            )
            messages.success(request, f'District Admin created for {district.name}. Login with mobile {phone}.')
            return redirect('state_admin_dashboard')
    return render(request, 'create_district_admin.html', {'districts': districts, 'state': state})


@state_admin_required
def verify_employers(request):
    from .legacy_admin_security import manageable_users
    employers = manageable_users(request.user).filter(
        user_type__in=User.EMPLOYER_TYPES
    ).order_by('-date_joined')
    return render(request, 'verify_employers.html', {'employers': employers})


@state_admin_required
@require_POST
@transaction.atomic
def suspend_user(request, user_id):
    from .legacy_admin_security import manageable_users
    from .account import safe_return
    target = get_object_or_404(manageable_users(request.user).select_for_update(), pk=user_id)
    target.is_active = not target.is_active
    target.save()
    action = 'activated' if target.is_active else 'suspended'
    messages.success(request, f'User "{target.username}" {action}.')
    return redirect(safe_return(request, '/state-admin/employers/'))


@state_admin_required
def state_reports(request):
    profile = getattr(request.user, 'admin_profile', None)
    businesses = CompanyProfile.objects.select_related('user').all()
    complaints = Complaint.objects.all()
    if request.user.admin_role == 'district_admin':
        district = profile.district if profile else None
        pins = district.pincodes.values_list('code', flat=True) if district else []
        businesses = businesses.filter(user__pincode__in=pins)
        complaints = complaints.filter(district=district)
    elif request.user.admin_role == 'state_admin':
        state = profile.state if profile else None
        pins = PinCode.objects.filter(district__state=state).values_list('code', flat=True)
        businesses = businesses.filter(user__pincode__in=pins)
        complaints = complaints.filter(district__state=state)
    return render(request, 'state_reports.html', {'report_title': 'State report', 'business_count': businesses.count(),
        'open_complaints': complaints.filter(status='open').count(), 'businesses': businesses[:20]})


# ─── DISTRICT ADMIN ───────────────────────────────────────────────────────────

@district_admin_required
def district_admin_dashboard(request):
    from .legacy_admin_security import district_users, district_complaints
    profile  = getattr(request.user, 'admin_profile', None)
    district = profile.district if profile else None
    users = district_users(request.user)
    complaints = district_complaints(request.user)
    pending_employers = Advertiser.objects.filter(status='pending', user__in=users).count()
    pending_ads = Advertisement.objects.filter(status='pending_review', advertiser__user__in=users).count()
    open_complaints = complaints.filter(status='open').count()
    recent_complaints = complaints.order_by('-created_at')[:5]
    return render(request, 'district_admin_dashboard.html', {
        'district': district, 'pending_employers': pending_employers,
        'pending_ads': pending_ads, 'open_complaints': open_complaints,
        'recent_complaints': recent_complaints,
    })


@district_admin_required
@transaction.atomic
def approve_employers_district(request):
    from .legacy_admin_security import district_users
    employers = district_users(request.user).filter(user_type__in=User.EMPLOYER_TYPES).order_by('-date_joined')
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action  = request.POST.get('action')
        target  = get_object_or_404(employers.select_for_update(), pk=user_id)
        if action == 'approve':
            was_active=target.is_active
            target.is_active = True
            target.save()
            if not was_active:
                send_review_message(request.user,target,'Your business account is approved',
                    'Your business account has been approved. You can now sign in and manage your shop.',
                    '/employer/dashboard/')
            messages.success(request, f'{target.username} approved.')
        elif action == 'block':
            target.is_active = False
            target.save()
            messages.info(request, f'{target.username} blocked.')
        return redirect('approve_employers_district')
    return render(request, 'approve_employers_district.html', {'employers': employers})


@district_admin_required
def handle_complaints(request):
    from .legacy_admin_security import district_complaints
    profile  = getattr(request.user, 'admin_profile', None)
    district = profile.district if profile else None
    complaints = district_complaints(request.user).order_by('-created_at')
    return render(request, 'handle_complaints.html', {'complaints': complaints, 'district': district})


@district_admin_required
def resolve_complaint(request, complaint_id):
    from .legacy_admin_security import district_complaints
    complaint = get_object_or_404(district_complaints(request.user), pk=complaint_id)
    if request.method == 'POST':
        complaint.resolution  = request.POST.get('resolution', '').strip()
        complaint.status      = request.POST.get('status', 'resolved')
        complaint.assigned_to = request.user
        complaint.resolved_at = timezone.now()
        complaint.save()
        messages.success(request, 'Complaint updated.')
        return redirect('handle_complaints')
    return render(request, 'resolve_complaint.html', {'complaint': complaint})


@district_admin_required
def district_reports(request):
    profile = getattr(request.user, 'admin_profile', None)
    businesses = CompanyProfile.objects.select_related('user').all()
    complaints = Complaint.objects.all()
    if request.user.admin_role == 'district_admin':
        district = profile.district if profile else None
        pins = district.pincodes.values_list('code', flat=True) if district else []
        businesses = businesses.filter(user__pincode__in=pins)
        complaints = complaints.filter(district=district)
    elif request.user.admin_role == 'state_admin':
        state = profile.state if profile else None
        pins = PinCode.objects.filter(district__state=state).values_list('code', flat=True)
        businesses = businesses.filter(user__pincode__in=pins)
        complaints = complaints.filter(district__state=state)
    return render(request, 'district_reports.html', {'report_title': 'District report', 'business_count': businesses.count(),
        'open_complaints': complaints.filter(status='open').count(), 'businesses': businesses[:20]})


# ─── PUBLIC: Submit Complaint ──────────────────────────────────────────────────
@login_required
def submit_complaint(request):
    if request.method == 'POST':
        Complaint.objects.create(
            submitted_by   = request.user,
            complaint_type = request.POST.get('complaint_type', 'other'),
            subject        = request.POST.get('subject', '').strip(),
            description    = request.POST.get('description', '').strip(),
        )
        messages.success(request, 'Complaint submitted. Our team will review it shortly.')
        return redirect('dashboard')
    return render(request, 'submit_complaint.html', {})


# ── PROFILE REDIRECT ──────────────────────────────────────────────────────────
@login_required
def profile_redirect(request):
    return redirect('profile_edit')


@login_required
def my_accounts(request):
    return render(request, 'my_accounts.html', {
        'company': getattr(request.user, 'company', None),
    })


@login_required
@transaction.atomic
def profile_edit(request):
    from .account import LocationPreferencesForm, BusinessDetailsForm, DashboardPersonalForm, profile_features, safe_return
    user = request.user
    company = getattr(user, 'company', None)
    business_user = company is not None
    if request.method == 'GET' and business_user:
        return redirect('/employer/dashboard/#my-profile')
    personal_form = DashboardPersonalForm(request.POST or None, request.FILES or None, instance=user)
    location_form = LocationPreferencesForm(request.POST or None, initial={field: getattr(user, field) for field in LocationPreferencesForm.base_fields})
    business_form = BusinessDetailsForm(request.POST or None, request.FILES or None, instance=company) if company else None
    context = {'personal_form': personal_form, 'location_form': location_form, 'business_form': business_form,
               'company': company, 'account_features': profile_features(user),
               'following_count': user.business_follows.count(),
               'business_follower_count': company.followers.count() if company else 0}
    if request.method == 'POST':
        valid = personal_form.is_valid()
        valid = location_form.is_valid() and valid
        valid = (business_form.is_valid() if business_form else True) and valid
        business_phone = request.POST.get('business_phone', user.business_phone).strip()
        if business_phone:
            import re
            if not re.fullmatch(r'[0-9]{10}', business_phone) or User.objects.exclude(pk=user.pk).filter(business_phone=business_phone).exists():
                location_form.add_error(None, 'Enter a unique 10-digit business phone number.')
                valid = False
        if valid:
            personal_form.save()
            for field, value in location_form.cleaned_data.items():
                setattr(user, field, value)
            user.business_phone = business_phone
            user.save()
            if personal_form.cleaned_data.get('photo'):
                seeker, _ = JobSeekerProfile.objects.get_or_create(user=user)
                seeker.photo = personal_form.cleaned_data['photo']
                seeker.save(update_fields=['photo'])
            if business_form:
                business_form.save()
            for key in ('active_pincode', 'offers_pincode', 'news_pincode'):
                request.session[key] = user.pincode
            messages.success(request, 'Profile updated successfully.')
            return redirect(safe_return(request, '/employer/dashboard/#my-profile' if business_user else '/profile/edit/'))
        if business_user:
            response = employer_dashboard(request, profile_editor=context)
            response.status_code = 400
            return response
        return render(request, 'profile_edit.html', context, status=400)
    return render(request, 'profile_edit.html', context)


# ── SUPER ADMIN: OFFERS ────────────────────────────────────────────────────────
@super_admin_required
def manage_offers(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        if action in ('approve','deactivate'):
            pk = request.POST.get('pk')
            review_offer(request,pk,active=action=='approve')
            return redirect('manage_offers')
        if action == 'delete':
            pk = request.POST.get('pk')
            LocalOffer.objects.filter(pk=pk).delete()
            return redirect('manage_offers')
        # action == 'add'
        obj = LocalOffer(
            business_name = request.POST.get('business_name', '').strip(),
            title         = request.POST.get('title', '').strip(),
            discount_text = request.POST.get('discount_text', '').strip(),
            category      = request.POST.get('category', 'other'),
            description   = request.POST.get('description', '').strip(),
            is_flash      = 'is_flash' in request.POST,
            is_active     = True,
        )
        phone = request.POST.get('contact_phone', '').strip()
        if phone:
            obj.contact_phone = phone
            obj.link_url = f"https://wa.me/91{phone}"
        if request.POST.get('valid_until'):
            obj.valid_until = request.POST.get('valid_until')
        if request.FILES.get('image'):
            obj.image = request.FILES['image']
        obj.save()
        return redirect('manage_offers')

    pending = LocalOffer.objects.filter(is_active=False).order_by('-created_at')
    active  = LocalOffer.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'super_admin_offers.html', {
        'pending': pending,
        'active':  active,
        'categories': LocalOffer.CATEGORY_CHOICES,
    })


@super_admin_required
@require_POST
def offer_approve(request, pk):
    review_offer(request,pk,active=request.POST.get('action')!='deactivate')
    return redirect('manage_offers')


@transaction.atomic
def review_offer(request,pk,active=True):
    offer=get_object_or_404(LocalOffer.objects.select_for_update().select_related('owner'),pk=pk)
    if offer.is_active==active:
        return
    offer.is_active=active
    offer.save(update_fields=['is_active'])
    if active:
        send_review_message(request.user,offer.owner,'Your offer is approved',
            f'Your offer "{offer.title}" for {offer.business_name} has been approved and is now published.',
            '/employer/dashboard/#offers')


@super_admin_required
def offer_delete(request, pk):
    LocalOffer.objects.filter(pk=pk).delete()
    return redirect('manage_offers')


@login_required
def start_conversation(request, user_id):
    other = get_object_or_404(User, pk=user_id, is_active=True)
    if other == request.user:
        return redirect('chat_list')
    conv = _get_or_create_conv(request.user, other)
    return redirect('chat_room', conv_id=conv.pk)
