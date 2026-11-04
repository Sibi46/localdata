from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from jobs.models import Country, State


# State/UT names: https://knowindia.india.gov.in/states-uts/
STATES = (
    ('AP', 'Andhra Pradesh'), ('AR', 'Arunachal Pradesh'), ('AS', 'Assam'),
    ('BR', 'Bihar'), ('CG', 'Chhattisgarh'), ('GA', 'Goa'), ('GJ', 'Gujarat'),
    ('HR', 'Haryana'), ('HP', 'Himachal Pradesh'), ('JH', 'Jharkhand'),
    ('KA', 'Karnataka'), ('KL', 'Kerala'), ('MP', 'Madhya Pradesh'),
    ('MH', 'Maharashtra'), ('MN', 'Manipur'), ('ML', 'Meghalaya'),
    ('MZ', 'Mizoram'), ('NL', 'Nagaland'), ('OD', 'Odisha'), ('PB', 'Punjab'),
    ('RJ', 'Rajasthan'), ('SK', 'Sikkim'), ('TN', 'Tamil Nadu'),
    ('TS', 'Telangana'), ('TR', 'Tripura'), ('UP', 'Uttar Pradesh'),
    ('UK', 'Uttarakhand'), ('WB', 'West Bengal'),
    ('AN', 'Andaman and Nicobar Islands'), ('CH', 'Chandigarh'),
    ('DN', 'Dadra and Nagar Haveli and Daman and Diu'), ('DL', 'Delhi'),
    ('JK', 'Jammu and Kashmir'), ('LA', 'Ladakh'), ('LD', 'Lakshadweep'),
    ('PY', 'Puducherry'),
)


class Command(BaseCommand):
    help = 'Add missing Indian states and union territories without changing existing geography.'

    @transaction.atomic
    def handle(self, *args, **options):
        india = Country.objects.filter(code__iexact='IN', name__iexact='India').first()
        created = 0
        for code, name in STATES:
            # Preserve IDs, alternative codes, inactive states and existing assignments.
            if State.objects.filter(Q(code__iexact=code) | Q(name__iexact=name)).exists():
                continue
            State.objects.create(code=code, name=name, is_active=True, country=india)
            created += 1
        self.stdout.write(self.style.SUCCESS(f'Added {created} states/union territories. Existing records unchanged.'))
