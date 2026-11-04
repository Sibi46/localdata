import io
import json
from unittest.mock import patch
from urllib.error import URLError

from django.core.cache import cache
from django.test import RequestFactory,SimpleTestCase

from .locations import lookup_pincode
from .views import api_pincode_lookup


class PincodeLookupTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.local=patch('jobs.locations.PinCode.objects.select_related')
        self.local.start().return_value.filter.return_value.first.return_value=None
        self.addCleanup(self.local.stop)
        self.addCleanup(cache.clear)

    @patch('jobs.locations.urlopen',side_effect=URLError('offline'))
    def test_vandavasi_is_available_without_network(self,remote):
        data=lookup_pincode('604408')
        self.assertEqual(data['city'],'Vandavasi')
        self.assertEqual(data['district'],'Tiruvannamalai')
        remote.assert_not_called()

    @patch('jobs.locations.urlopen',side_effect=URLError('offline'))
    def test_network_failure_is_not_reported_as_unknown_pincode(self,remote):
        response=api_pincode_lookup(RequestFactory().get('/'),'600001')
        self.assertEqual(response.status_code,503)
        self.assertEqual(json.loads(response.content)['code'],'lookup_unavailable')

    @patch('jobs.locations.urlopen')
    def test_provider_can_confirm_an_unknown_pincode(self,remote):
        remote.return_value=io.BytesIO(json.dumps([{'Status':'Error','PostOffice':None}]).encode())
        response=api_pincode_lookup(RequestFactory().get('/'),'999999')
        self.assertEqual(response.status_code,200)
        self.assertFalse(json.loads(response.content)['success'])

    @patch('jobs.locations.urlopen')
    def test_remote_lookup_prefers_the_main_post_office(self,remote):
        remote.return_value=io.BytesIO(json.dumps([{'Status':'Success','PostOffice':[
            {'Name':'Village','BranchType':'Branch Post Office'},
            {'Name':'Town','BranchType':'Sub Post Office','District':'District','State':'State'},
        ]}]).encode())
        self.assertEqual(lookup_pincode('600001')['city'],'Town')
