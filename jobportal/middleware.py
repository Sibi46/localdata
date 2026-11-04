from urllib.parse import urlencode
from django.shortcuts import redirect


# Authentication, onboarding, legal information, and assets remain reachable.
PUBLIC_PREFIXES = (
    '/about/','/terms/','/privacy/','/register/','/login/','/logout/',
    '/forgot-password/','/reset-password/','/super-admin/login/','/admin-workspace/login/',
    '/admin/','/static/','/api/pincode/','/api/send-otp/','/api/verify-otp/',
    '/api/quick-register/','/api/phone-login/','/api/check-phone/','/api/reset-password/',
    '/api/send-register-otp/','/api/verify-register-otp/',
    '/media/products/',
    '/analytics/collect/',
)


class LoginRequiredMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        from django.conf import settings
        from django.http import HttpResponseNotFound
        import posixpath
        from urllib.parse import urlsplit
        normalized = posixpath.normpath(request.path_info.replace('\\', '/')).casefold()
        prefix = posixpath.normpath(urlsplit(settings.MEDIA_URL).path + '/chat_files').casefold()
        if normalized == prefix or normalized.startswith(prefix + '/'):
            return HttpResponseNotFound()
        from django.urls import resolve,Resolver404
        try:resolve(request.path_info)
        except Resolver404:return self.get_response(request)
        if not request.user.is_authenticated:
            path=request.path
            if path in {'/','/favicon.ico','/robots.txt','/sitemap.xml'} or path.startswith('/sitemaps/'):
                return self.get_response(request)
            if any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
                return self.get_response(request)
            if path.startswith('/super-admin/'):
                return redirect('pilot_admin_login')
            return redirect('/register/?'+urlencode({'next':request.get_full_path()}))
        return self.get_response(request)
