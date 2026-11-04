from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('jobs', '0058_district_geonames_id_state_geonames_id_and_more')]

    operations = [
        migrations.AddField(
            model_name='companyprofile', name='description',
            field=models.TextField(blank=True, max_length=1000),
        ),
    ]
