from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0026_familysetup_house_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='familysetup',
            name='partner_gender',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='partner_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='partner_password',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
