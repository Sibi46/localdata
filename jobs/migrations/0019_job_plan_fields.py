from django.db import migrations, models
import datetime


def grandfather_existing_jobs(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    Job.objects.filter(is_approved=True, status='active').update(
        job_plan='free',
        plan_expires_at=datetime.date(2099, 12, 31),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0018_job_is_approved'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='job_plan',
            field=models.CharField(blank=True, choices=[('', 'No Plan'), ('free', '1 Week Free'), ('paid', '12 Weeks Paid')], default='', max_length=10),
        ),
        migrations.AddField(
            model_name='job',
            name='payment_screenshot',
            field=models.ImageField(blank=True, null=True, upload_to='payment_proofs/'),
        ),
        migrations.AddField(
            model_name='job',
            name='plan_expires_at',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(grandfather_existing_jobs, migrations.RunPython.noop),
    ]
