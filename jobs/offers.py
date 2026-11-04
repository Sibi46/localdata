"""Public offer feed with shop follows and direct conversations."""
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone

from .account import selected_area
from .models import Advertisement, BusinessFollow, LocalOffer
from .offer_links import attach_offer_links, business_directory


def gallery(request):
    today = timezone.localdate()
    pincode = selected_area(request)
    query = request.GET.get('q', '').strip()[:150]
    category = request.GET.get('cat', '').strip().lower()
    if category not in dict(LocalOffer.CATEGORY_CHOICES):
        category = ''
    following = request.GET.get('following') == '1'
    followed = set(BusinessFollow.objects.filter(user=request.user).values_list('company_id', flat=True)) if request.user.is_authenticated else set()
    offers = LocalOffer.objects.filter(is_active=True).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today)).filter(Q(owner__isnull=True) | Q(owner__is_active=True)).select_related('owner__company')
    if category:
        offers = offers.filter(category=category)
    if query:
        offers = offers.filter(Q(title__icontains=query) | Q(business_name__icontains=query) | Q(description__icontains=query))
    # Resolve legacy offers as well, so pincode/follow filters use the actual shop.
    directory = business_directory()
    matches = []
    for offer in offers.order_by('-is_flash', '-created_at'):
        attach_offer_links(offer, directory)
        offer.category_label = dict(LocalOffer.CATEGORY_CHOICES).get(offer.category, offer.category)
        shop = offer.store_profile
        offer.is_following = bool(shop and shop.pk in followed)
        if pincode and (not shop or shop.user.pincode != pincode):
            continue
        if following and not offer.is_following:
            continue
        matches.append(offer)
    page = Paginator(matches, 18).get_page(request.GET.get('page'))
    offer_data = {str(offer.pk): {
        'name': offer.business_name, 'title': offer.title, 'discount': offer.discount_text,
        'category': offer.category_label, 'description': offer.description,
        'phone': offer.whatsapp_phone, 'whatsapp': offer.whatsapp_url, 'store': offer.store_url,
        'valid_until': offer.valid_until.strftime('%d %b %Y') if offer.valid_until else '',
        'valid_days': offer.valid_days, 'image': offer.image.url if offer.image else '',
    } for offer in page}
    results = {'flash_offers': [o for o in page if o.is_flash], 'normal_offers': [o for o in page if not o.is_flash]}
    context = {**results, 'offers': page, 'offer_count': len(matches), 'query': query, 'pincode': pincode,
               'active_cat': category, 'following_only': following, 'offer_categories': LocalOffer.CATEGORY_CHOICES}
    if request.GET.get('format') == 'json':
        return JsonResponse({'html': render_to_string('includes/offer_results.html', results, request=request), 'offers': offer_data, 'category': category, 'count': len(matches)})
    context['sponsored_ads'] = Advertisement.objects.filter(status='active', advertiser__status='approved').filter(Q(start_date__isnull=True) | Q(start_date__lte=today)).filter(Q(end_date__isnull=True) | Q(end_date__gte=today)).select_related('advertiser')[:3]
    return render(request, 'ads_gallery.html', context)
