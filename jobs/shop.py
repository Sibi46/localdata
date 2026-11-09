"""Public product discovery and owner-scoped shop management."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .account import selected_area
from .models import BusinessGalleryImage, CompanyProfile, LocalOffer, Product, ProductImage, ShopVideo
from .shop_forms import ProductForm, ShopOfferForm, ShopPhotosForm, ShopVideoForm


def public_products():
    return Product.objects.filter(is_active=True, shop__user__is_active=True).exclude(shop__company_name='').select_related('shop', 'shop__user')


def product_list(request):
    pincode = selected_area(request)
    query = request.GET.get('q', '').strip()[:150]
    category = request.GET.get('category', '').strip()[:80]
    products = public_products()
    shops = CompanyProfile.objects.filter(user__is_active=True).exclude(company_name='').select_related('user')
    if pincode:
        products = products.filter(shop__user__pincode=pincode)
        shops = shops.filter(user__pincode=pincode)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__icontains=query) | Q(shop__company_name__icontains=query))
        shops = shops.filter(company_name__icontains=query)
    if category:
        products = products.filter(category__iexact=category)
    sort = request.GET.get('sort', 'newest')
    # Sort by the actual discounted price, rather than the original price.
    from django.db.models import DecimalField, ExpressionWrapper, F, Value
    products = products.annotate(current_price=ExpressionWrapper(F('price') * (Value(100) - F('discount_percent')) / Value(100.0), output_field=DecimalField(max_digits=12, decimal_places=2)))
    ordering = {'price_low': ['current_price', '-pk'], 'price_high': ['-current_price', '-pk']}.get(sort, ['-created_at', '-pk'])
    page = Paginator(products.order_by(*ordering), 24).get_page(request.GET.get('page'))
    return render(request, 'shop/products.html', {'products': page, 'query': query, 'category': category, 'sort': sort,
                  'matching_shops': shops[:6] if query else [], 'product_count': page.paginator.count,
                  'owns_shop': request.user.is_authenticated and CompanyProfile.objects.filter(user=request.user, user__is_active=True).exists()})


def owner_shop(request):
    return get_object_or_404(CompanyProfile, user=request.user, user__is_active=True)


def product_detail(request, pk):
    product = get_object_or_404(public_products().prefetch_related('images'), pk=pk)
    gallery = ([product.image] if product.image else []) + [item.image for item in product.images.all()]
    return render(request, 'shop/product_detail.html', {'product': product, 'gallery': gallery,
                  'related_products': public_products().filter(shop=product.shop).exclude(pk=product.pk)[:4]})


@login_required
def product_form(request, pk=None):
    shop = owner_shop(request)
    product = get_object_or_404(Product, pk=pk, shop=shop) if pk else Product(shop=shop)
    if pk is None and shop.products.count()>=shop.product_limit:
        from .product_access import limit_page
        return limit_page(request,shop,status=403 if request.method=='POST' else 200)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        uploads = form.cleaned_data.get('images', [])
        old_files = []
        with transaction.atomic():
            locked_shop=CompanyProfile.objects.select_for_update().get(pk=shop.pk)
            if pk is None and locked_shop.products.count()>=locked_shop.product_limit:
                from .product_access import limit_page
                return limit_page(request,locked_shop,status=403)
            if uploads:
                if product.pk:
                    old_files = [(item.image.storage, item.image.name) for item in product.images.all()]
                    if product.image:
                        old_files.append((product.image.storage, product.image.name))
                    product.images.all().delete()
                product = form.save(commit=False)
                product.image = uploads[0]
                product.save()
                for position, upload in enumerate(uploads[1:], start=1):
                    ProductImage.objects.create(product=product, image=upload, position=position)
                transaction.on_commit(lambda: [storage.delete(name) for storage, name in old_files if name])
            else:
                form.save()
        messages.success(request, 'Product updated.' if pk else 'Your product has been added to LOCALFROM.')
        return redirect('/employer/dashboard/#products')
    current_images = ([product.image] if product.image else []) + ([item.image for item in product.images.all()] if product.pk else [])
    return render(request, 'shop/manage_form.html', {'company': shop, 'form': form, 'kind': 'product', 'editing': bool(pk), 'current_images': current_images, 'form_title': 'Edit product' if pk else 'Add a product'})


@login_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, shop=owner_shop(request))
    for item in product.images.all():
        item.image.delete(save=False)
    product.image.delete(save=False)
    product.delete()
    messages.success(request, 'Product deleted.')
    return redirect('/employer/dashboard/#products')


@login_required
def video_form(request, pk=None):
    shop = owner_shop(request)
    video = get_object_or_404(ShopVideo, pk=pk, shop=shop) if pk else ShopVideo(shop=shop)
    form = ShopVideoForm(request.POST or None, request.FILES or None, instance=video)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Video saved.')
        return redirect('/employer/dashboard/#videos')
    return render(request, 'shop/manage_form.html', {'company': shop, 'form': form, 'kind': 'video', 'editing': bool(pk), 'form_title': 'Edit video' if pk else 'Add a shop video'})


@login_required
@require_POST
def video_delete(request, pk):
    video = get_object_or_404(ShopVideo, pk=pk, shop=owner_shop(request))
    video.video.delete(save=False)
    video.thumbnail.delete(save=False)
    video.delete()
    messages.success(request, 'Video deleted.')
    return redirect('/employer/dashboard/#videos')


@login_required
def offer_form(request, pk=None):
    shop = owner_shop(request)
    offer = get_object_or_404(LocalOffer, pk=pk, owner=request.user) if pk else LocalOffer(owner=request.user)
    form = ShopOfferForm(request.POST or None, request.FILES or None, instance=offer)
    if request.method == 'POST' and form.is_valid():
        offer = form.save(commit=False)
        offer.owner = request.user
        offer.business_name = shop.company_name
        offer.is_active = False  # Keep the existing offer moderation policy.
        offer.save()
        messages.success(request, 'Offer sent for review. It will appear publicly after approval.')
        return redirect('/employer/dashboard/#offers')
    return render(request, 'shop/manage_form.html', {'company': shop, 'form': form, 'kind': 'offer', 'editing': bool(pk), 'form_title': 'Edit offer' if pk else 'Create a shop offer'})


@login_required
@require_POST
def offer_delete(request, pk):
    offer = get_object_or_404(LocalOffer, pk=pk, owner=owner_shop(request).user)
    offer.image.delete(save=False)
    offer.delete()
    messages.success(request, 'Offer deleted.')
    return redirect('/employer/dashboard/#offers')


@login_required
@require_POST
def gallery_upload(request):
    owner_shop(request)
    form = ShopPhotosForm(request.POST, request.FILES)
    if form.is_valid():
        for image in form.cleaned_data['gallery_images']:
            BusinessGalleryImage.objects.create(user=request.user, image=image, caption=form.cleaned_data['caption'])
        messages.success(request, 'Shop photos uploaded.')
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect('/employer/dashboard/#gallery')


@login_required
@require_POST
def gallery_delete(request, pk):
    owner_shop(request)
    image = get_object_or_404(BusinessGalleryImage, pk=pk, user=request.user)
    image.image.delete(save=False)
    image.delete()
    messages.success(request, 'Photo deleted.')
    return redirect('/employer/dashboard/#gallery')
