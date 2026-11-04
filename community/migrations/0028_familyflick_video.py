from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0029_flick_post'),
    ]

    operations = [
        migrations.AddField(
            model_name='familyflick',
            name='video',
            field=models.FileField(blank=True, null=True, upload_to='family_flick_videos/'),
        ),
        migrations.AlterField(
            model_name='familyflick',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='family_flicks/'),
        ),
    ]
