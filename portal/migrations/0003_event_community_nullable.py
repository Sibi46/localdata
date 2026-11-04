from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0002_event_meetup_features'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='community',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='events',
                to='portal.community',
            ),
        ),
    ]
