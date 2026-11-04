from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0020_school_admin_phone'),
    ]

    operations = [
        # Wife-side counts on FamilySetup
        migrations.AddField(model_name='familysetup', name='w_grandfather_count', field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='familysetup', name='w_grandmother_count', field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='familysetup', name='w_father_count',      field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='familysetup', name='w_mother_count',      field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='familysetup', name='w_uncle_count',       field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='familysetup', name='w_aunt_count',        field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='familysetup', name='w_cousin_count',      field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='familysetup', name='w_brother_count',     field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name='familysetup', name='w_sister_count',      field=models.PositiveSmallIntegerField(default=0)),
        # Side field on FamilyMember
        migrations.AddField(
            model_name='familymember',
            name='side',
            field=models.CharField(
                blank=True, default='husband', max_length=10,
                choices=[('husband', 'Husband Side'), ('wife', 'Wife Side')],
            ),
        ),
    ]
