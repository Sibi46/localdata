from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0031_merge_20260717_1630'),
    ]

    operations = [
        migrations.AddField(
            model_name='flick',
            name='category',
            field=models.CharField(
                choices=[('general', 'General'), ('health', 'Health'), ('job', 'Job'), ('business', 'Business')],
                default='general',
                max_length=20,
            ),
        ),
    ]
