from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0023_family_wife_side'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # FamilySetup new fields
        migrations.AddField(
            model_name='familysetup',
            name='family_email',
            field=models.EmailField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='family_password',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='self_full_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='self_dob',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='self_village',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='self_occupation',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='self_photo',
            field=models.ImageField(blank=True, null=True, upload_to='family/self/'),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='partner_full_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='partner_dob',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='partner_village',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='partner_occupation',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='familysetup',
            name='partner_photo',
            field=models.ImageField(blank=True, null=True, upload_to='family/partner/'),
        ),
        # FamilyMember child login fields
        migrations.AddField(
            model_name='familymember',
            name='child_email',
            field=models.EmailField(blank=True),
        ),
        migrations.AddField(
            model_name='familymember',
            name='child_password',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='familymember',
            name='child_linked_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='family_child_profile',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
