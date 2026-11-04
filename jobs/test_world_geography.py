from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from .models import Country, State, District, PinCode
from .world_geography import import_world_geography, load_snapshot


class WorldGeographyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.india = Country.objects.get(code='IN')
        cls.state = State.objects.create(name='Tamil Nadu', code='TN', country=cls.india, is_active=False)
        cls.district = District.objects.create(name='Chennai', state=cls.state, is_active=False)
        cls.pin = PinCode.objects.create(code='600001', district=cls.district)

    def small_data(self):
        return {'states': [['IN.25','Tamil Nadu','Tamil Nadu','100'], ['US.CA','California','California','101']],
                'districts': [['IN.25.01','Chennai District','Chennai District','200'], ['US.CA.001','County','County','201']]}

    def test_preview_does_not_write(self):
        before = (State.objects.count(), District.objects.count())
        report = import_world_geography(data=self.small_data())
        self.assertEqual(report['states_linked'], 1)
        self.assertEqual(report['districts_linked'], 1)
        self.assertEqual(before, (State.objects.count(), District.objects.count()))
        self.state.refresh_from_db()
        self.assertIsNone(self.state.geonames_id)

    def test_apply_preserves_links_status_names_and_is_repeatable(self):
        report = import_world_geography(data=self.small_data(), dry_run=False)
        self.assertEqual(report['states_created'], 1)
        self.assertEqual(report['districts_created'], 1)
        self.state.refresh_from_db(); self.district.refresh_from_db(); self.pin.refresh_from_db()
        self.assertEqual(self.state.code, 'TN')
        self.assertFalse(self.state.is_active)
        self.assertFalse(self.district.is_active)
        self.assertEqual(self.district.name, 'Chennai')
        self.assertEqual(self.pin.district_id, self.district.pk)
        again = import_world_geography(data=self.small_data(), dry_run=False)
        self.assertEqual(again['states_created'] + again['districts_created'], 0)

    def test_unknown_country_orphan_and_conflicting_parent_reported(self):
        data = self.small_data()
        data['states'] += [['ZZ.1','Unknown','Unknown','102']]
        data['districts'] += [['US.NONE.1','Orphan','Orphan','202']]
        report = import_world_geography(data=data, dry_run=False)
        self.assertEqual(report['skipped']['unknown_country'], ['ZZ.1'])
        self.assertEqual(report['skipped']['missing_state'], ['US.NONE.1'])
        data['states'][0][0] = 'US.WRONG'
        report = import_world_geography(data=data)
        self.assertIn('US.WRONG', report['skipped']['state_parent_conflict'])

    def test_same_state_name_in_different_countries_is_not_merged(self):
        data = {'states': [['US.A','Central','Central','301'],['CA.A','Central','Central','302']], 'districts': []}
        import_world_geography(data=data, dry_run=False)
        first, second = State.objects.get(geonames_id=301), State.objects.get(geonames_id=302)
        self.assertNotEqual(first.country_id, second.country_id)
        self.assertNotEqual(first.name, second.name)

    def test_import_rolls_back_on_database_failure(self):
        with patch('jobs.world_geography.District.objects.bulk_create', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                import_world_geography(data=self.small_data(), dry_run=False)
        self.assertFalse(State.objects.filter(geonames_id=101).exists())
        self.state.refresh_from_db()
        self.assertIsNone(self.state.geonames_id)

    def test_full_bundled_snapshot_and_repeat_import(self):
        data = load_snapshot()
        self.assertEqual(len(data['states']), 3865)
        self.assertEqual(len(data['districts']), 47642)
        report = import_world_geography(dry_run=False)
        self.assertGreater(report['states_created'], 3500)
        self.assertGreater(report['districts_created'], 45000)
        self.assertTrue(State.objects.filter(country__code='US', name='California').exists())
        self.assertTrue(District.objects.filter(state__country__code='IN').exists())
        repeat = import_world_geography(dry_run=False)
        self.assertEqual(repeat['states_created'] + repeat['districts_created'], 0)

    def test_command_defaults_to_preview(self):
        with patch('jobs.management.commands.import_world_geography.import_world_geography', return_value={'dry_run':True,'skipped':{}}) as importer:
            output = StringIO()
            call_command('import_world_geography', stdout=output)
            importer.assert_called_once_with(dry_run=True)
            self.assertIn('PREVIEW ONLY', output.getvalue())
