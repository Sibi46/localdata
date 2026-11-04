import random
import string
from django.db import migrations, models
import django.db.models.deletion


def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def assign_referral_codes(apps, schema_editor):
    User = apps.get_model('jobs', 'User')
    used = set()
    for user in User.objects.all():
        if not user.referral_code:
            code = generate_code()
            while code in used or User.objects.filter(referral_code=code).exists():
                code = generate_code()
            user.referral_code = code
            user.save(update_fields=['referral_code'])
            used.add(code)


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0021_job_plan_paid_pending'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='referral_code',
            field=models.CharField(blank=True, max_length=12, null=True, unique=True),
        ),
        migrations.RunPython(assign_referral_codes, migrations.RunPython.noop),
        migrations.CreateModel(
            name='PointsWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.IntegerField(default=0)),
                ('total_earned', models.IntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='points_wallet', to='jobs.user')),
            ],
        ),
        migrations.CreateModel(
            name='PointsTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField()),
                ('txn_type', models.CharField(choices=[('referral_signup', 'Referral Signup Bonus'), ('referral_job', 'Referral Job Posted Bonus'), ('referral_apply', 'Referral Application Bonus'), ('redeemed', 'Points Redeemed')], max_length=20)),
                ('description', models.CharField(max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='jobs.pointswallet')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Referral',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bonus_signup', models.BooleanField(default=False)),
                ('bonus_action', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('referrer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referrals_made', to='jobs.user')),
                ('referred', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='referred_by', to='jobs.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
