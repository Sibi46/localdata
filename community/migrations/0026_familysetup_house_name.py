from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0025_family_account_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='familysetup',
            name='house_name',
            field=models.CharField(blank=True, max_length=150),
        ),
    ]
