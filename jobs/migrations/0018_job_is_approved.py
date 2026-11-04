from django.db import migrations, models


def approve_existing_active_jobs(apps, schema_editor):
    Job = apps.get_model('jobs', 'Job')
    Job.objects.filter(status='active').update(is_approved=True)


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0017_add_advertiser_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='is_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(approve_existing_active_jobs, migrations.RunPython.noop),
    ]
