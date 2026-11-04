from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0040_user_business_phone'),
    ]

    operations = [
        migrations.AddField(model_name='jobapplication', name='expected_salary',    field=models.CharField(max_length=100, blank=True, default=''), preserve_default=False),
        migrations.AddField(model_name='jobapplication', name='notice_period',      field=models.CharField(max_length=50, blank=True, default=''), preserve_default=False),
        migrations.AddField(model_name='jobapplication', name='employment_type',    field=models.CharField(max_length=20, blank=True, default=''), preserve_default=False),
        migrations.AddField(model_name='jobapplication', name='why_join',           field=models.TextField(blank=True, default=''), preserve_default=False),
        migrations.AddField(model_name='jobapplication', name='why_suitable',       field=models.TextField(blank=True, default=''), preserve_default=False),
        migrations.AddField(model_name='jobapplication', name='currently_employed', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='jobapplication', name='how_heard',          field=models.CharField(max_length=100, blank=True, default=''), preserve_default=False),
        migrations.AddField(model_name='jobapplication', name='application_resume', field=models.FileField(upload_to='application_resumes/', blank=True, null=True)),
        migrations.AddField(model_name='jobapplication', name='cover_letter_file',  field=models.FileField(upload_to='cover_letters/', blank=True, null=True)),
        migrations.AddField(model_name='jobapplication', name='declared',           field=models.BooleanField(default=False)),
    ]
