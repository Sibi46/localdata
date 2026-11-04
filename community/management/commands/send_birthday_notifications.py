"""Compatibility command for the retired family birthday feature."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Retired: family birthday notifications are no longer part of LOCALFROM.'

    def handle(self, *args, **options):
        raise CommandError('Family birthday notifications have been retired. Remove this command from any scheduler. Existing family records have been preserved.')
