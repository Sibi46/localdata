from django.db import migrations


RETIRED_MODELS = [
    'OfferLetter', 'Interview', 'JobApplication', 'SavedJob', 'Job',
    'ReviewVoucher', 'SeekerCertificate', 'JobRole', 'MarketingAccess',
    'EmployerSubscription', 'PaymentPlan', 'SavedCandidate', 'BillingRecord',
    'WalletTransaction', 'Wallet', 'PointsTransaction', 'PointsWallet',
    'Referral', 'UserSpin', 'SpinGift',
]


def remove_retired_permissions(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ContentType.objects.using(schema_editor.connection.alias).filter(
        app_label='jobs', model__in=[name.lower() for name in RETIRED_MODELS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('jobs', '0063_shop_catalog'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    # Clear retained-table references first. Drop child tables before parents;
    # removing each retired table's fields first breaks SQLite table rebuilds
    # when those fields participate in unique constraints.
    operations = [
        migrations.AlterUniqueTogether(name='conversation', unique_together=set()),
        migrations.RemoveField(model_name='conversation', name='job'),
        migrations.RemoveField(model_name='message', name='job'),
        migrations.RemoveField(model_name='companyprofile', name='review_reward_percent'),
        *[migrations.DeleteModel(name=name) for name in RETIRED_MODELS],
        migrations.RunPython(remove_retired_permissions, migrations.RunPython.noop),
    ]
