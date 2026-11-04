from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # New fields on Event
        migrations.AddField(model_name='event', name='end_date',     field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='event', name='end_time',     field=models.TimeField(blank=True, null=True)),
        migrations.AddField(model_name='event', name='pincode',      field=models.CharField(blank=True, max_length=10)),
        migrations.AddField(model_name='event', name='is_online',    field=models.BooleanField(default=False)),
        migrations.AddField(model_name='event', name='online_link',  field=models.URLField(blank=True)),
        migrations.AddField(model_name='event', name='ticket_price', field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
        migrations.AddField(model_name='event', name='tags',         field=models.CharField(blank=True, max_length=300)),
        migrations.AddField(model_name='event', name='contact_phone',field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name='event', name='status',       field=models.CharField(choices=[('upcoming','Upcoming'),('ongoing','Ongoing'),('completed','Completed'),('cancelled','Cancelled')], default='upcoming', max_length=12)),
        # Extend EventParticipant status choices (no DB change needed, just alter)
        migrations.AlterField(
            model_name='eventparticipant',
            name='status',
            field=models.CharField(choices=[('pending','Pending'),('approved','Approved'),('rejected','Rejected'),('waitlist','Waitlist'),('cancelled','Cancelled')], default='pending', max_length=10),
        ),
        # EventComment
        migrations.CreateModel(
            name='EventComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='portal.event')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='event_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['created_at']},
        ),
        # EventAnnouncement
        migrations.CreateModel(
            name='EventAnnouncement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to='portal.event')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        # EventPhoto
        migrations.CreateModel(
            name='EventPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('image', models.ImageField(upload_to='portal/event_photos/')),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='portal.event')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        # EventRating
        migrations.CreateModel(
            name='EventRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('rating', models.PositiveSmallIntegerField()),
                ('review', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='portal.event')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='event_ratings', to=settings.AUTH_USER_MODEL)),
            ],
            options={'unique_together': {('event', 'user')}},
        ),
    ]
