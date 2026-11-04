from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0033_spin_to_win'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocalOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_name', models.CharField(max_length=150)),
                ('title', models.CharField(max_length=200)),
                ('discount_text', models.CharField(help_text='e.g. 20% OFF, Buy 1 Get 1, Free Delivery', max_length=60)),
                ('category', models.CharField(choices=[('food', 'Food & Drinks'), ('salon', 'Salon & Beauty'), ('health', 'Health & Pharmacy'), ('shop', 'Shopping'), ('services', 'Services'), ('other', 'Other')], default='other', max_length=20)),
                ('image', models.ImageField(blank=True, null=True, upload_to='offers/')),
                ('description', models.TextField(blank=True)),
                ('valid_until', models.DateField(blank=True, null=True)),
                ('link_url', models.URLField(blank=True)),
                ('is_flash', models.BooleanField(default=False, help_text='Show in Flash Deals with countdown')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
