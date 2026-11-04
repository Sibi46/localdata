from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0020_job_plan_free_expired'),
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
                    ('paid_pending', 'Payment Under Review'),
                    ('paid', '12 Weeks Paid'),
                    ('free_expired', 'Free Plan Expired'),
                ],
                default='',
                max_length=15,
            ),
        ),
    ]
