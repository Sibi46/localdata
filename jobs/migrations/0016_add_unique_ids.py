from django.db import migrations, models


def populate_ids(apps, schema_editor):
    CompanyProfile = apps.get_model('jobs', 'CompanyProfile')
    for obj in CompanyProfile.objects.all():
        obj.company_id = f'CO-{obj.pk:06d}'
        obj.save(update_fields=['company_id'])

    Job = apps.get_model('jobs', 'Job')
    for obj in Job.objects.all():
        obj.job_id = f'JOB-{obj.pk:06d}'
        obj.save(update_fields=['job_id'])

    JobSeekerProfile = apps.get_model('jobs', 'JobSeekerProfile')
    for obj in JobSeekerProfile.objects.all():
        obj.seeker_id = f'JS-{obj.pk:06d}'
        obj.save(update_fields=['seeker_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0015_user_whatsapp'),
    ]

    operations = [
        # Add fields WITHOUT unique first
        migrations.AddField(
            model_name='companyprofile',
            name='company_id',
            field=models.CharField(blank=True, max_length=20, default=''),
        ),
        migrations.AddField(
            model_name='job',
            name='job_id',
            field=models.CharField(blank=True, max_length=20, default=''),
        ),
        migrations.AddField(
            model_name='jobseekerprofile',
            name='seeker_id',
            field=models.CharField(blank=True, max_length=20, default=''),
        ),
        # Populate IDs for existing rows
        migrations.RunPython(populate_ids, migrations.RunPython.noop),
        # Now add unique + index constraints
        migrations.AlterField(
            model_name='companyprofile',
            name='company_id',
            field=models.CharField(blank=True, db_index=True, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='job',
            name='job_id',
            field=models.CharField(blank=True, db_index=True, max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='jobseekerprofile',
            name='seeker_id',
            field=models.CharField(blank=True, db_index=True, max_length=20, unique=True),
        ),
    ]
