"""Pincode locality lookup shared by onboarding, shops, and area labels."""
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.request import urlopen
from django.core.cache import cache
from .models import PinCode


class PincodeLookupUnavailable(Exception):
    """The postal service could not confirm whether a pincode exists."""


@lru_cache(maxsize=1)
def pilot_pincodes():
    return json.loads((Path(__file__).parent/'data'/'pilot-pincodes.json').read_text(encoding='utf-8'))


def lookup_pincode(pin,remote=True):
    if not re.fullmatch(r'[1-9][0-9]{5}',pin or ''):return None
    key='local-from-pincode:'+pin
    cached=cache.get(key)
    if cached:return cached
    local=PinCode.objects.select_related('district__state').filter(code=pin).first()
    if local:
        area=local.area_name or local.district.name
        data={'success':True,'area':area,'city':area,'district':local.district.name,'state':local.district.state.name}
        cache.set(key,data,86400)
        return data
    pilot=pilot_pincodes().get(pin)
    if pilot:
        data={'success':True,**pilot}
        cache.set(key,data,86400)
        return data
    if not remote:return None
    try:
        with urlopen(f'https://api.postalpincode.in/pincode/{pin}',timeout=6) as response:
            payload=json.loads(response.read())
        if not isinstance(payload,list) or not payload or not isinstance(payload[0],dict):
            raise PincodeLookupUnavailable()
        if payload[0].get('Status') not in ('Success','Error'):
            raise PincodeLookupUnavailable()
        offices=payload[0].get('PostOffice') if payload[0].get('Status')=='Success' else None
        if not offices:return None
        office=next((item for item in offices if item.get('BranchType')=='Head Post Office'),None) or next((item for item in offices if item.get('BranchType')=='Sub Post Office'),offices[0])
        area=office.get('Name','')
        data={'success':True,'area':area,'city':area,'district':office.get('District',''),'state':office.get('State','')}
        cache.set(key,data,86400)
        return data
    except (OSError,ValueError,KeyError,TypeError,IndexError) as error:
        raise PincodeLookupUnavailable() from error
