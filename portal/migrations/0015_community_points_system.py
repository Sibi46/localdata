from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0014_community_gallery_event_date'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PointConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=50, unique=True, choices=[('attend_event','Attend Event'),('volunteer_event','Volunteer at Event'),('organise_event','Organise Event'),('complete_activity','Complete Activity'),('volunteer_activity','Volunteer Activity'),('support_cause','Support Cause'),('upload_contribution','Upload Contribution'),('financial_contribution','Financial Contribution'),('other','Other')])),
                ('label', models.CharField(max_length=100)),
                ('points', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='MemberPoints',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_points', models.PositiveIntegerField(default=0)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='member_points', to=settings.AUTH_USER_MODEL)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='member_points', to='portal.community')),
            ],
            options={'unique_together': {('user', 'community')}},
        ),
        migrations.CreateModel(
            name='Participation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(max_length=15, choices=[('attendee','Attendee'),('organiser','Organiser'),('volunteer','Volunteer'),('contributor','Contributor'),('guest','Guest'),('sponsor','Sponsor')], default='attendee')),
                ('status', models.CharField(max_length=10, choices=[('pending','Pending'),('confirmed','Confirmed'),('rejected','Rejected')], default='pending')),
                ('points_awarded', models.PositiveIntegerField(default=0)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participations', to=settings.AUTH_USER_MODEL)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participations', to='portal.community')),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='participations', to='portal.event')),
                ('activity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='participations', to='portal.activity')),
                ('cause', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='participations', to='portal.cause')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_participations', to=settings.AUTH_USER_MODEL)),
            ],
            options={'unique_together': {('user', 'event', 'activity', 'cause', 'role')}},
        ),
        migrations.CreateModel(
            name='Contribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contribution_type', models.CharField(max_length=20, choices=[('financial','Financial'),('food','Food'),('equipment','Equipment'),('materials','Materials'),('books','Books'),('clothing','Clothing'),('transport','Transport'),('professional','Professional Service'),('sponsorship','Sponsorship'),('venue','Venue Support'),('other','Other')])),
                ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('description', models.TextField()),
                ('estimated_value', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('status', models.CharField(max_length=10, choices=[('pending','Pending'),('approved','Approved'),('rejected','Rejected')], default='pending')),
                ('points_awarded', models.PositiveIntegerField(default=0)),
                ('transaction_ref', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contributions', to=settings.AUTH_USER_MODEL)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contributions', to='portal.community')),
                ('event', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contributions', to='portal.event')),
                ('activity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contributions', to='portal.activity')),
                ('cause', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='contributions', to='portal.cause')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_contributions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('icon', models.CharField(default='🏅', max_length=10)),
                ('criteria_type', models.CharField(max_length=30, choices=[('points','Points Threshold'),('events','Events Attended'),('organised','Events Organised'),('volunteer','Volunteer Activities'),('causes','Causes Supported'),('manual','Manual Award')], default='manual')),
                ('criteria_value', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('community', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='badges', to='portal.community')),
            ],
        ),
        migrations.CreateModel(
            name='MemberBadge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('awarded_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='badges', to=settings.AUTH_USER_MODEL)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='awarded_badges', to='portal.community')),
                ('badge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='awards', to='portal.badge')),
                ('awarded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='badges_awarded', to=settings.AUTH_USER_MODEL)),
            ],
            options={'unique_together': {('user', 'community', 'badge')}},
        ),
        migrations.CreateModel(
            name='Recognition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('award_name', models.CharField(max_length=200)),
                ('year', models.PositiveSmallIntegerField()),
                ('description', models.TextField(blank=True)),
                ('awarded_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recognitions', to=settings.AUTH_USER_MODEL)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recognitions', to='portal.community')),
                ('awarded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recognitions_given', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PointAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=100)),
                ('points_before', models.IntegerField(default=0)),
                ('points_after', models.IntegerField(default=0)),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('community', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='portal.community')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='point_audit_logs', to=settings.AUTH_USER_MODEL)),
                ('done_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_actions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        # Seed default PointConfig rows
        migrations.RunPython(
            code=lambda apps, schema_editor: _seed_point_configs(apps, schema_editor),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def _seed_point_configs(apps, schema_editor):
    PointConfig = apps.get_model('portal', 'PointConfig')
    defaults = [
        ('attend_event', 'Attend Event', 10),
        ('volunteer_event', 'Volunteer at Event', 20),
        ('organise_event', 'Organise Event', 50),
        ('complete_activity', 'Complete Activity', 30),
        ('volunteer_activity', 'Volunteer Activity', 20),
        ('support_cause', 'Support Cause', 10),
        ('upload_contribution', 'Upload Contribution', 5),
        ('financial_contribution', 'Financial Contribution', 10),
    ]
    for action, label, points in defaults:
        PointConfig.objects.get_or_create(action=action, defaults={'label': label, 'points': points})
