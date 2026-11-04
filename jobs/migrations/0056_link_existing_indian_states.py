"""Populate the country relationship omitted when the hierarchy was introduced."""
from django.db import migrations

# Frozen names from the existing seed_states command; preserve unknown locations.
INDIAN_STATE_NAMES = ('Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu', 'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry')


def link_indian_states(apps, schema_editor):
    Country = apps.get_model('jobs', 'Country')
    State = apps.get_model('jobs', 'State')
    alias = schema_editor.connection.alias
    countries = Country.objects.using(alias)
    india = countries.filter(code__iexact='IN', name__iexact='India').first()
    if india is None:
        if countries.filter(code__iexact='IN').exists() or countries.filter(name__iexact='India').exists():
            # Conflicting manually configured country: leave it for explicit mapping.
            return
        india = countries.create(name='India', code='IN')
    for name in INDIAN_STATE_NAMES:
        State.objects.using(alias).filter(country__isnull=True, name__iexact=name).update(country_id=india.pk)


class Migration(migrations.Migration):
    dependencies = [('jobs', '0055_country_adminprofile_area_and_more')]
    operations = [migrations.RunPython(link_indian_states, migrations.RunPython.noop)]
