from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from jobs.assigned_admin import ScopeForm
from jobs.models import State


class SeedStatesTests(TestCase):
    def test_populates_dropdown_and_can_run_twice(self):
        State.objects.create(name='Unassigned geography', code='UNASN')
        call_command('seed_states', stdout=StringIO())
        call_command('seed_states', stdout=StringIO())
        choices = ScopeForm().fields['state'].queryset
        self.assertEqual(choices.count(), 36)
        self.assertTrue(choices.filter(name='Tamil Nadu').exists())
        self.assertTrue(choices.filter(name='Delhi').exists())
        self.assertFalse(choices.filter(code='UNASN').exists())

    def test_preserves_existing_state_and_disabled_status(self):
        state = State.objects.create(name='Tamil Nadu', code='TAMIL', is_active=False)
        call_command('seed_states', stdout=StringIO())
        state.refresh_from_db()
        self.assertEqual(state.code, 'TAMIL')
        self.assertFalse(state.is_active)
        self.assertEqual(State.objects.filter(name='Tamil Nadu').count(), 1)
