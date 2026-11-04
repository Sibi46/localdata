from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0032_flick_category'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpinGift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('image', models.ImageField(upload_to='spin_gifts/')),
                ('address', models.TextField(blank=True)),
                ('win_pct', models.FloatField(default=10.0, help_text='Chance of winning (0-100)')),
                ('code', models.CharField(help_text='6-digit claim code', max_length=6)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserSpin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('won', models.BooleanField(default=False)),
                ('code_shown', models.CharField(blank=True, max_length=6)),
                ('spun_at', models.DateTimeField(auto_now_add=True)),
                ('gift', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='jobs.spingift')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='spins', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-spun_at'],
                'unique_together': {('user', 'date')},
            },
        ),
    ]
