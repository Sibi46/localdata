"""Services available to registered businesses."""
from .models import Advertiser, CompanyProfile

def registered_features(user):
    active, pending = [], []
    if not user.is_authenticated or not user.is_active:
        return active, pending
    if CompanyProfile.objects.filter(user=user).exclude(company_name='').exists():
        active.append({'label': 'Business profile', 'url': '#my-profile'})
    advertiser = Advertiser.objects.filter(user=user).first()
    if advertiser and advertiser.status in ('approved', 'pending'):
        (active if advertiser.status == 'approved' else pending).append({'label': 'Ads', 'url': '/advertiser/dashboard/'})
    return active, pending
