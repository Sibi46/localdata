"""Explicit, audited deletion of shop listings; owner accounts are preserved."""
from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .admin_activity import record_activity
from .models import CompanyProfile, Product
from .pilot_admin import private


class DeleteForm(forms.Form):
    reason = forms.CharField(max_length=500, label='Reason for deletion',
                             widget=forms.Textarea(attrs={'rows': 3}))
    confirmation = forms.CharField(label='Type DELETE to confirm', max_length=6)

    def clean_confirmation(self):
        value = self.cleaned_data['confirmation']
        if value != 'DELETE':
            raise forms.ValidationError('Type DELETE to confirm this permanent deletion.')
        return value


@private
@require_http_methods(['GET', 'POST'])
def product_delete(request, pk):
    product = get_object_or_404(Product.objects.select_related('shop'), pk=pk)
    form = DeleteForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            shop = get_object_or_404(CompanyProfile.objects.select_for_update(), pk=product.shop_id)
            product = get_object_or_404(Product.objects.select_for_update(), pk=pk, shop=shop)
            record_activity(request.user, 'products', 'delete', product.pk, product.name,
                details={'shop_id': shop.pk, 'reason': form.cleaned_data['reason']})
            product.delete()
        messages.success(request, 'Product deleted. The shop and its other products are unchanged.')
        return redirect('pilot_admin_shop', pk=shop.pk)
    return render(request, 'pilot_admin/delete_listing.html', {
        'form': form, 'product': product, 'company': product.shop, 'kind': 'product'})


@private
@require_http_methods(['GET', 'POST'])
def shop_delete(request, pk):
    company = get_object_or_404(CompanyProfile.objects.select_related('user'), pk=pk)
    form = DeleteForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            company = get_object_or_404(CompanyProfile.objects.select_for_update(), pk=pk)
            owner = company.user
            counts = {'products': company.products.count(), 'videos': company.videos.count(),
                      'offers': owner.local_offers.count(), 'photos': owner.gallery_images.count()}
            record_activity(request.user, 'shops', 'delete', company.pk, company.company_name,
                details={'owner_id': owner.pk, 'reason': form.cleaned_data['reason'], **counts})
            owner.local_offers.all().delete()
            owner.gallery_images.all().delete()
            company.delete()
        messages.success(request, 'Shop listing and its products, offers and gallery deleted. Owner account and conversations retained.')
        return redirect('super_admin_dashboard')
    return render(request, 'pilot_admin/delete_listing.html', {
        'form': form, 'company': company, 'kind': 'shop',
        'product_count': company.products.count(), 'video_count': company.videos.count(),
        'offer_count': company.user.local_offers.count(), 'photo_count': company.user.gallery_images.count()})
