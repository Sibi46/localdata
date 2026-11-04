import uuid
from django.conf import settings
from django.middleware.csrf import get_token
from django.templatetags.static import static
from django.utils.cache import patch_cache_control,patch_vary_headers
from django.utils.html import format_html
from .analytics import COOKIE,SALT,excluded,visitor_id


class AnalyticsMiddleware:
    def __init__(self,get_response):self.get_response=get_response

    def __call__(self,request):
        response=self.get_response(request)
        if not getattr(settings,'LOCAL_ANALYTICS_ENABLED',True) or excluded(request):return response
        if request.headers.get('DNT')=='1' or request.headers.get('Sec-GPC')=='1':return response
        if response.status_code!=200 or response.streaming or 'text/html' not in response.get('Content-Type','') or response.get('Content-Encoding'):return response
        content=response.content.decode(response.charset)
        if '</head>' not in content.lower():return response
        script=format_html('<script src="{}" data-local-analytics data-endpoint="/analytics/collect/" data-csrf="{}" data-csrf-cookie="{}" defer></script>',static('js/site-analytics.js')+'?v=1',get_token(request),settings.CSRF_COOKIE_NAME)
        position=content.lower().index('</head>')
        response.content=(content[:position]+str(script)+content[position:]).encode(response.charset)
        for header in ('Content-Length','ETag'):
            if header in response:del response[header]
        patch_cache_control(response,private=True)
        patch_vary_headers(response,('Cookie',))
        if visitor_id(request) is None:
            response.set_signed_cookie(COOKIE,str(uuid.uuid4()),salt=SALT,max_age=31536000,httponly=True,secure=request.is_secure() or settings.SESSION_COOKIE_SECURE,samesite='Lax')
        return response
