from django.db import migrations, models


def upgrade_free_allowance(apps, schema_editor):
    # Raise legacy allowances only. Never lower an admin-approved larger limit
    # or change products, messages, pending requests or their review history.
    CompanyProfile = apps.get_model('jobs', 'CompanyProfile')
    CompanyProfile.objects.using(schema_editor.connection.alias).filter(
        product_limit__lt=10,
    ).update(product_limit=10)


class Migration(migrations.Migration):
    dependencies = [('jobs', '0070_site_analytics')]

    operations = [
        migrations.AlterField(
            model_name='companyprofile', name='product_limit',
            field=models.PositiveIntegerField(default=10),
        ),
        # Deliberately do not lower existing limits on rollback.
        migrations.RunPython(upgrade_free_allowance, migrations.RunPython.noop),
    ]
