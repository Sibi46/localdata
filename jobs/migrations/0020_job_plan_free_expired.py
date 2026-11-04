from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0019_job_plan_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job',
            name='job_plan',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'No Plan'),
                    ('free', '1 Week Free'),
                    ('paid', '12 Weeks Paid'),
                    ('free_expired', 'Free Plan Expired'),
                ],
                default='',
                max_length=15,
            ),
        ),
    ]
