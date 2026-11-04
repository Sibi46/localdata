import math
import time
import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_nominatim_last_call = 0   # enforce 1-req/sec for Nominatim ToS


def geocode_pincode(pincode: str) -> tuple[float | None, float | None]:
    """
    Return (latitude, longitude) for an Indian pincode.
    Tries Google Maps first (if GOOGLE_MAPS_KEY is set), then Nominatim.
    Results are cached for 30 days.
    """
    if not pincode or len(pincode) != 6 or not pincode.isdigit():
        return None, None

    cache_key = f"geocode_pin_{pincode}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    lat, lng = _geocode_google(pincode) or (None, None)
    if lat is None:
        lat, lng = _geocode_nominatim(pincode)

    if lat is not None:
        cache.set(cache_key, (lat, lng), timeout=60 * 60 * 24 * 30)

    return lat, lng


def _geocode_google(pincode: str) -> tuple[float, float] | None:
    key = getattr(settings, "GOOGLE_MAPS_KEY", "")
    if not key or key in ("YOUR_API_KEY", ""):
        return None
    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": f"{pincode},India", "key": key},
            timeout=5,
        )
        data = resp.json()
        if data.get("status") == "OK":
            loc = data["results"][0]["geometry"]["location"]
            return float(loc["lat"]), float(loc["lng"])
    except Exception as e:
        logger.warning("Google geocode failed for %s: %s", pincode, e)
    return None


def _geocode_nominatim(pincode: str) -> tuple[float | None, float | None]:
    global _nominatim_last_call
    # Nominatim ToS: max 1 request/second
    gap = time.time() - _nominatim_last_call
    if gap < 1.1:
        time.sleep(1.1 - gap)
    _nominatim_last_call = time.time()

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{pincode}, India", "format": "json", "limit": 1,
                    "countrycodes": "in"},
            headers={"User-Agent": "PincodeJobPortal/1.0"},
            timeout=8,
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        logger.warning("Nominatim geocode failed for %s: %s", pincode, e)
    return None, None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance between two lat/lng points in kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))




def generate_referral_code():
    """Generate a unique 8-character referral code."""
    import random
    import string
    from .models import User
    chars = string.ascii_uppercase + string.digits
    for _ in range(20):
        code = ''.join(random.choices(chars, k=8))
        if not User.objects.filter(referral_code=code).exists():
            return code
    return ''.join(random.choices(chars, k=12))


def ensure_referral_code(user):
    """Repair legacy accounts before displaying a share link, preserving existing codes."""
    from django.db import transaction
    from .models import User
    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        if not locked.referral_code:
            locked.referral_code = generate_referral_code()
            locked.save(update_fields=['referral_code'])
        user.referral_code = locked.referral_code
    return user.referral_code


def generate_biz_id():
    """Generate a unique BIZXXXXXX salesman business ID (no hyphens)."""
    import random
    import string
    from .models import User
    digits = string.digits
    for _ in range(30):
        code = 'BIZ' + ''.join(random.choices(digits, k=6))
        if not User.objects.filter(salesman_biz_id=code).exists():
            return code
    return 'BIZ' + ''.join(random.choices(digits, k=8))
