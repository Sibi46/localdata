from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0037_localoffer_valid_days'),
    ]

    operations = [
        migrations.AlterField(
            model_name='localoffer',
            name='category',
            field=models.CharField(default='other', max_length=50),
        ),
    ]
