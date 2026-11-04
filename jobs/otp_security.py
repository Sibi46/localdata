"""Phone verification shared by all account entry points.

Production uses a dedicated Redis cache for atomic, cross-worker consumption.
No code, provider response, or credentials are logged.
"""
import re
import secrets
import time

import requests
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import caches
from django.utils.crypto import salted_hmac

TTL = 600
PHONE = re.compile(r'[6-9][0-9]{9}')


class OTPError(Exception):
    pass


def store():
    return caches[settings.OTP_CACHE_ALIAS]


def demo_enabled(purpose):
    if getattr(settings, 'PUBLIC_DEMO_SIGNUP', False):
        return purpose == 'signup'
    flag = 'DEMO_PASSWORD_RESET_OTP' if purpose == 'reset' else 'DEMO_SIGNUP_OTP'
    return settings.DEBUG and getattr(settings, flag, False)


def require_available(purpose):
    if purpose == 'reset' and getattr(settings, 'PUBLIC_DEMO_SIGNUP', False):
        raise OTPError('Password recovery is unavailable during demo signup. Sign in with your password.')


def response_metadata(pending=None):
    """Label visible codes explicitly; they never prove phone ownership."""
    pending = pending or {}
    result = {'otp': pending['code']} if 'code' in pending else {}
    if getattr(settings, 'PUBLIC_DEMO_SIGNUP', False):
        result.update({
            'demo': True,
            'phone_ownership_verified': False,
            'message': 'Testing code only. This does not verify ownership of your mobile number.',
        })
    return result


def deliver_code(phone, code):
    """2Factor's JSON API keeps secrets out of request URLs and access logs."""
    if not getattr(settings, 'OTP_DELIVERY_ENABLED', True):
        return False
    key = settings.TWO_FACTOR_API_KEY
    template = settings.TWO_FACTOR_OTP_TEMPLATE
    if not key or not template:
        return False
    try:
        response = requests.post(
            'https://2factor.in/API/V1/OTP/SEND',
            headers={'X-API-Key': key},
            json={'to': '+91' + phone, 'template_name': template, 'var1': code},
            timeout=10, allow_redirects=False,
        )
        payload = response.json()
        return response.ok and isinstance(payload, dict) and (
            payload.get('status') == 'sent' or payload.get('Status') == 'Success')
    except (requests.RequestException, ValueError, TypeError):
        return False


def _key(kind, value):
    return 'account-otp:' + kind + ':' + salted_hmac('account-otp', value).hexdigest()


def issue(request, phone, purpose):
    if purpose not in {'signup', 'reset'} or not PHONE.fullmatch(phone or ''):
        raise OTPError('Enter a valid 10-digit mobile number.')
    require_available(purpose)
    # A new challenge invalidates an earlier challenge and verified proof.
    previous = request.session.pop('account_otp_' + purpose, None)
    try:
        backend = store()
        if previous:
            backend.delete(_key('proof', previous['nonce']))
        for kind, value, limit in (
            ('phone', phone, 3),
            ('ip', request.META.get('REMOTE_ADDR', ''), 30),
        ):
            key = _key(kind, value)
            backend.add(key, 0, TTL)
            if backend.incr(key) > limit:
                raise OTPError('Too many OTP requests. Please try again in 10 minutes.')
        code = str(secrets.randbelow(900000) + 100000)
        if not demo_enabled(purpose) and not deliver_code(phone, code):
            raise OTPError('OTP delivery is unavailable. Please try again later.')
        nonce = secrets.token_urlsafe(32)
        record = {'phone': phone, 'purpose': purpose, 'created': time.time(),
                  'hash': make_password(code), 'verified': False, 'demo': demo_enabled(purpose),
                  'phone_ownership_verified': False}
        backend.set(_key('proof', nonce), record, TTL)
        backend.set(_key('latest', purpose + ':' + phone), nonce, TTL)
        pending = {'phone': phone, 'purpose': purpose, 'nonce': nonce,
                   'created': record['created'], 'verified': False}
        request.session['account_otp_' + purpose] = pending
        request.session['account_otp_purpose'] = purpose
        request.session.cycle_key()
        return {**pending, 'code_hash': record['hash'],
                **({'code': code} if demo_enabled(purpose) else {})}
    except OTPError:
        raise
    except Exception:
        raise OTPError('OTP verification is temporarily unavailable.') from None


def _record(request, phone, purpose):
    require_available(purpose)
    pending = request.session.get('account_otp_' + purpose, {})
    if (not isinstance(pending, dict) or pending.get('phone') != phone
            or pending.get('purpose') != purpose or not pending.get('nonce')):
        raise OTPError('Verify an OTP for this phone number first.')
    record = store().get(_key('proof', pending['nonce']))
    if (not record or record.get('phone') != phone or record.get('purpose') != purpose
            or store().get(_key('latest', purpose + ':' + phone)) != pending['nonce']
            or (record.get('demo') and not demo_enabled(purpose))
            or not 0 <= time.time() - record.get('created', 0) < TTL):
        raise OTPError('OTP expired. Request a new OTP.')
    return pending, record


def verify(request, phone, purpose, code):
    try:
        pending, record = _record(request, phone, purpose)
        nonce = pending['nonce']
        attempt = _key('attempts', nonce)
        store().add(attempt, 0, TTL)
        if store().incr(attempt) > 5:
            store().delete(_key('proof', nonce))
            raise OTPError('Too many incorrect attempts. Request a new OTP.')
        if (record['verified'] or not re.fullmatch(r'[0-9]{6}', code or '')
                or not check_password(code, record['hash'])):
            raise OTPError('That OTP is incorrect or already used.')
        if not store().add(_key('verified', nonce), True, TTL):
            raise OTPError('That OTP is already used.')
        record['verified'] = True
        record['phone_ownership_verified'] = not record.get('demo', False)
        store().set(_key('proof', nonce), record, max(1, int(TTL - (time.time() - record['created']))))
        request.session['account_otp_' + purpose] = {**pending, 'verified': True}
        return True
    except OTPError:
        raise
    except Exception:
        raise OTPError('OTP verification is temporarily unavailable.') from None


def consume(request, phone, purpose):
    """Atomic claim prevents replay, including requests with a stale session copy."""
    try:
        pending, record = _record(request, phone, purpose)
        if not record['verified'] or not store().add(_key('used', pending['nonce']), True, TTL):
            raise OTPError('Verify a new OTP before continuing.')
        store().delete(_key('proof', pending['nonce']))
        request.session.pop('account_otp_' + purpose, None)
    except OTPError:
        raise
    except Exception:
        raise OTPError('OTP verification is temporarily unavailable.') from None
