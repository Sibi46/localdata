from unittest.mock import patch
from django.test import AsyncClient, RequestFactory, SimpleTestCase, override_settings
from django.urls import Resolver404
from jobportal.error_views import not_found


@override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False)
class MissingPageTests(SimpleTestCase):
    def test_missing_pages_return_404_without_database_queries(self):
        for path in ['/aw.php', '/wp-content/plugins/hellopress/wp_filemanager.php',
                     '/md5.php3', '/not-a-real-localfrom-page/']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertContains(response, 'Page not found', status_code=404)
            self.assertNotContains(response, path, status_code=404)
            self.assertEqual(response['X-Robots-Tag'], 'noindex, follow')

    def test_context_processors_are_not_used(self):
        with patch('jobs.context_processors.site_ads', side_effect=RuntimeError('Unavailable')):
            response = not_found(RequestFactory().get('/missing/'), Resolver404('private'))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(b'private', response.content)

    async def test_missing_page_under_asgi(self):
        response = await AsyncClient().get('/aw.php')
        self.assertEqual(response.status_code, 404)
