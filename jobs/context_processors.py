from django.utils import timezone
from django.conf import settings
from .models import Advertisement


def site_ads(request):
    from .account import selected_area
    from .features import FEATURES, search_features
    photo_url = ''
    if request.user.is_authenticated:
        seeker = getattr(request.user, 'seeker', None)
        company = getattr(request.user, 'company', None)
        photo = getattr(seeker, 'photo', None) or getattr(company, 'logo', None)
        if photo:
            photo_url = photo.url
    today = timezone.now().date()
    ads = (Advertisement.objects
           .filter(status='active', start_date__lte=today, end_date__gte=today)
           .exclude(image='')
           .select_related('advertiser', 'package')[:30])

    by_type = {}
    for ad in ads:
        t = ad.package.ad_type
        by_type.setdefault(t, []).append(ad)

    pending_ad_posts = 0
    if request.user.is_authenticated and getattr(request.user, 'admin_role', '') == 'super_admin':
        from .models import AdPost
        pending_ad_posts = AdPost.objects.filter(status='pending').count()

    active_area=selected_area(request)
    from .locations import lookup_pincode
    area_data=lookup_pincode(active_area,remote=False)
    area_label=area_data.get('city',area_data.get('area','')) if area_data else request.user.city if request.user.is_authenticated and request.user.pincode==active_area else ''
    show_follow_prompt=False
    if request.user.is_authenticated and not request.user.admin_role and request.path in ('/','/account/'):
        from .models import LocalFromFollow
        preference=LocalFromFollow.objects.filter(user=request.user).values('is_following','prompt_dismissed').first()
        show_follow_prompt=not preference or not preference['prompt_dismissed']
    return {
        'local_from_instagram_url':settings.LOCAL_FROM_INSTAGRAM_URL,
        'show_local_from_follow_prompt':show_follow_prompt,
        'notification_unread_count': request.user.notifications.filter(is_read=False).count() if request.user.is_authenticated else 0,
        'active_area': active_area, 'active_area_label':area_label,
        'saved_areas': list(dict.fromkeys(value for value in (
            request.user.pincode, request.user.preferred_pincode_1, request.user.preferred_pincode_2) if value)) if request.user.is_authenticated else [],
        'site_ads': ads,
        'profile_photo_url': photo_url,
        'ads_by_type': by_type,
        'pending_ad_posts': pending_ad_posts,
        'feature_catalog': FEATURES if request.path == '/' else [],
        'feature_query': request.GET.get('feature', '').strip() if request.path == '/' else '',
        'feature_matches': search_features(request.GET.get('feature', '')) if request.path == '/' else [],
    }
