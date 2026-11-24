"""Owner-only sharing tools using the configured canonical shop URL."""
from io import BytesIO
from urllib.parse import quote
import qrcode
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .models import CompanyProfile


def owner_shop(request):
    return get_object_or_404(CompanyProfile, user=request.user, user__is_active=True)


def shop_url(company):
    return settings.SITE_URL.rstrip('/') + company.get_absolute_url()


@never_cache
@login_required
@require_GET
def share(request):
    company = owner_shop(request)
    url = shop_url(company)
    text = f'{company.company_name} on Local From: {url}'
    return render(request, 'shop/share.html', {'company': company, 'share_url': url,
        'whatsapp_url': 'https://wa.me/?text=' + quote(text, safe='')})


@never_cache
@login_required
@require_GET
def qr(request):
    company = owner_shop(request)
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    code.add_data(shop_url(company))
    code.make(fit=True)
    image = code.make_image(fill_color='black', back_color='white')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    filename = f'localfrom-{slugify(company.company_id) or company.pk}-qr.png'
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
