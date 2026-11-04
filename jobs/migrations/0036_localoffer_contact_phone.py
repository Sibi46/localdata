from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0034_localoffer'),
    ]

    operations = [
        migrations.AddField(
            model_name='localoffer',
            name='contact_phone',
            field=models.CharField(blank=True, max_length=15),
        ),
    ]
