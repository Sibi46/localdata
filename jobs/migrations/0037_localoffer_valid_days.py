from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0036_localoffer_contact_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='localoffer',
            name='valid_days',
            field=models.CharField(blank=True, max_length=50, help_text='Comma-separated days e.g. Mon,Tue'),
        ),
    ]
