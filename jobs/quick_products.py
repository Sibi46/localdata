"""Photo-first product entry; uses existing catalog validation and shop allowance."""
import logging
from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import caches
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .models import CompanyProfile, Product, ProductImage
from .shop import owner_shop
from .shop_forms import ProductForm

logger = logging.getLogger(__name__)
RECEIPT_TTL = 7 * 24 * 60 * 60


@login_required
@require_GET
def editor(request):
    shop = owner_shop(request)
    return render(request, 'shop/easy_products.html', {
        'company': shop,
        'remaining': max(0, shop.product_limit - shop.products.count()),
    })


@login_required
@require_POST
def publish(request):
    shop = owner_shop(request)
    try:
        token = str(UUID(request.POST.get('draft_id', '')))
    except (ValueError, AttributeError, TypeError):
        return JsonResponse({'error': 'Reload this page before publishing.'}, status=400)

    # Redis is shared by production workers. A receipt allows a lost response to
    # be retried without adding the same draft again during its retention period.
    cache = caches[settings.OTP_CACHE_ALIAS]
    key = f'product-entry:{request.user.pk}:{shop.pk}:{token}'
    receipt = cache.get(key)
    if isinstance(receipt, dict):
        return JsonResponse(receipt)
    if not cache.add(key, 'processing', timeout=RECEIPT_TTL):
        return JsonResponse({'error': 'This product may already be publishing. Check My products before trying again.'}, status=409)

    data = request.POST.copy()
    data['is_active'] = 'on'
    form = ProductForm(data, request.FILES, instance=Product(shop=shop))
    if not form.is_valid():
        cache.delete(key)
        return JsonResponse({'error': 'Check the product details.', 'errors': form.errors.get_json_data()}, status=400)

    saved_files = []
    committed = False
    try:
        with transaction.atomic():
            locked = CompanyProfile.objects.select_for_update().get(pk=shop.pk)
            if locked.products.count() >= locked.product_limit:
                cache.delete(key)
                return JsonResponse({'error': 'Your shop has no product slots left. Ask Superadmin for more.', 'limit_reached': True}, status=403)
            product = form.save(commit=False)
            uploads = form.cleaned_data['images'] or [form.cleaned_data['image']]
            product.image = uploads[0]
            product.image.save(product.image.name, product.image.file, save=False)
            saved_files.append((product.image.storage, product.image.name))
            product.save()
            for position, upload in enumerate(uploads[1:], start=1):
                item = ProductImage(product=product, position=position)
                item.image.save(upload.name, upload, save=False)
                saved_files.append((item.image.storage, item.image.name))
                item.save()
        committed = True
        receipt = {'id': product.pk, 'name': product.name, 'url': product.get_absolute_url()}
        cache.set(key, receipt, timeout=RECEIPT_TTL)
        return JsonResponse(receipt)
    except Exception:
        # SQL rollback does not undo file writes. Remove only files this request
        # created, and never remove files belonging to a committed product.
        if not committed:
            for storage, name in saved_files:
                try:
                    storage.delete(name)
                except Exception:
                    logger.exception('Could not clean up an uncommitted product image')
            cache.delete(key)
        # After commit, retain the processing marker if receipt storage failed;
        # the owner must check their catalog rather than blindly duplicate it.
        raise
