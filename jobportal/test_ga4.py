from pathlib import Path
import re

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils.html import escapejs
from .context_processors import site_branding


class GA4Tests(SimpleTestCase):
    def render_tag(self):
        return render_to_string('includes/ga4.html', site_branding(RequestFactory().get('/')))

    @override_settings(GA4_MEASUREMENT_ID='')
    def test_disabled_without_id(self):
        self.assertEqual(self.render_tag().strip(), '')

    @override_settings(GA4_MEASUREMENT_ID='G-TEST123456')
    def test_enabled_with_environment_setting(self):
        html = self.render_tag()
        self.assertEqual(html.count('googletagmanager.com/gtag/js?id=G-TEST123456'), 1)
        self.assertEqual(html.count("gtag('config', '%s')" % escapejs('G-TEST123456')), 1)

    @override_settings(GA4_MEASUREMENT_ID="</script><script>alert('x')</script>")
    def test_id_cannot_inject_scripts(self):
        self.assertNotIn("<script>alert('x')", self.render_tag())

    def test_layout_coverage_and_no_duplicate_tags(self):
        for path in (Path(settings.BASE_DIR) / 'templates').rglob('*.html'):
            source = path.read_text(encoding='utf-8')
            with self.subTest(template=str(path)):
                if re.search(r'<head(?:\s[^>]*)?>', source):
                    self.assertEqual(len(re.findall(r"{%\s*include\s+[\"']includes/ga4\.html[\"']\s*%}", source)), 1)
                if path.name != 'ga4.html':
                    self.assertNotIn('googletagmanager.com/gtag/js', source)
                    self.assertNotIn("gtag('config'", source)

    @override_settings(GA4_MEASUREMENT_ID='G-TEST123456')
    def test_account_layout_includes_tracking_once(self):
        request = RequestFactory().get('/login/')
        request.user = AnonymousUser()
        html = render_to_string('accounts/base.html', site_branding(request))
        self.assertEqual(html.count('googletagmanager.com/gtag/js?id=G-TEST123456'), 1)
        self.assertEqual(html.count("gtag('config', '%s')" % escapejs('G-TEST123456')), 1)

    @override_settings(GA4_MEASUREMENT_ID='')
    def test_account_layout_disables_tracking_without_environment_id(self):
        request = RequestFactory().get('/register/')
        request.user = AnonymousUser()
        html = render_to_string('accounts/base.html', site_branding(request))
        self.assertNotIn('googletagmanager.com/gtag/js', html)
