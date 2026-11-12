from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('jobs', '0076_twenty_free_products')]

    operations = [
        migrations.AddField(
            model_name='adpost', name='creative_image',
            field=models.ImageField(blank=True, upload_to='ad_creatives/'),
        ),
        migrations.AddField(
            model_name='adpost', name='starts_at',
            field=models.DateField(blank=True, null=True),
        ),
    ]
