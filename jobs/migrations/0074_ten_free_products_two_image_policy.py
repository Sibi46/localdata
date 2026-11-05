from django.db import migrations, models


def upgrade_free_allowance(apps, schema_editor):
    company = apps.get_model('jobs', 'CompanyProfile')
    company.objects.using(schema_editor.connection.alias).filter(
        product_limit__lt=10,
    ).update(product_limit=10)


class Migration(migrations.Migration):
    dependencies = [('jobs', '0073_directory_phone_review')]

    operations = [
        migrations.AlterField(
            model_name='companyprofile',
            name='product_limit',
            field=models.PositiveIntegerField(default=10),
        ),
        # Preserve products, galleries, request metadata and higher allowances.
        migrations.RunPython(upgrade_free_allowance, migrations.RunPython.noop),
    ]
