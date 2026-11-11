from django.db import migrations, models


def upgrade_free_allowance(apps, schema_editor):
    company = apps.get_model('jobs', 'CompanyProfile')
    company.objects.using(schema_editor.connection.alias).filter(
        product_limit__lt=20,
    ).update(product_limit=20)


class Migration(migrations.Migration):
    dependencies = [('jobs', '0075_local_ride')]

    operations = [
        migrations.AlterField(
            model_name='companyprofile',
            name='product_limit',
            field=models.PositiveIntegerField(default=20),
        ),
        # Keep products, uploads, request metadata and higher approved limits.
        # Reversing the release must not reduce a shop's existing allowance.
        migrations.RunPython(upgrade_free_allowance, migrations.RunPython.noop),
    ]
