"""Resolve store navigation independently from offer contact links."""
import re
from urllib.parse import urlsplit, parse_qs
from django.urls import reverse
from .models import CompanyProfile


def business_key(name):
    return ''.join(character for character in (name or '').casefold() if character.isalnum())


def whatsapp_number(value):
    value = (value or '').strip()
    if not value or re.search(r'[a-zA-Z]', value):
        return ''
    digits = re.sub(r'\D', '', value)
    explicit_country = value.startswith('+') or value.startswith('00')
    if value.startswith('00'):
        digits = digits[2:]
    if len(digits) == 10 and not explicit_country:
        return '91' + digits if re.fullmatch(r'[6-9][0-9]{9}', digits) else ''
    if digits.startswith('91') and len(digits) == 12:
        return digits if re.fullmatch(r'91[6-9][0-9]{9}', digits) else ''
    if explicit_country and re.fullmatch(r'[1-9][0-9]{7,14}', digits):
        return digits
    return ''


def whatsapp_link_number(value):
    try:
        parsed = urlsplit(value or '')
        host = (parsed.hostname or '').lower()
        if parsed.scheme != 'https':
            return ''
        if host in ('wa.me', 'www.wa.me'):
            return whatsapp_number('+' + parsed.path.strip('/'))
        if host in ('api.whatsapp.com', 'web.whatsapp.com'):
            return whatsapp_number('+' + parse_qs(parsed.query).get('phone', [''])[0].lstrip('+'))
    except ValueError:
        pass
    return ''


def business_directory():
    result = {}
    for profile in CompanyProfile.objects.filter(user__is_active=True).select_related('user'):
        key = business_key(profile.company_name)
        if key:
            result.setdefault(key, []).append(profile)
    return result


def attach_offer_links(offer, directory=None):
    directory = business_directory() if directory is None else directory
    matches = directory.get(business_key(offer.business_name), [])
    # Never send a differently named merchant to its posting account's business.
    owned_matches = [match for match in matches if match.user_id == offer.owner_id]
    profile = owned_matches[0] if len(owned_matches) == 1 else (matches[0] if len(matches) == 1 else None)
    store_url = reverse('offer_store', args=[offer.pk])
    if profile:
        store_url = reverse('business_profile', args=[profile.company_id])
    else:
        try:
            parsed = urlsplit(offer.link_url or '')
            host = (parsed.hostname or '').lower()
            if (parsed.scheme in ('https', 'http') and host and not parsed.username
                    and host not in ('wa.me', 'www.wa.me', 'whatsapp.com')
                    and not host.endswith('.whatsapp.com')):
                store_url = offer.link_url
        except ValueError:
            pass
    candidates = []
    if profile:
        # Ownerless legacy/sample offers should use the matched store's public contact.
        if offer.owner_id == profile.user_id:
            candidates.append(offer.contact_phone)
        candidates.extend([profile.user.whatsapp, profile.user.phone])
    candidates.extend([offer.contact_phone, '+' + whatsapp_link_number(offer.link_url)])
    phone = next((number for value in candidates if (number := whatsapp_number(value))), '')
    offer.store_url = store_url
    offer.store_profile = profile
    offer.whatsapp_phone = phone
    offer.whatsapp_url = 'https://wa.me/' + phone if phone else ''
    return offer
