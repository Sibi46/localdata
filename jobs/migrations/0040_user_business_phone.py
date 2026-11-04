from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0039_localoffer_category_maxlength'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='business_phone',
            field=models.CharField(blank=True, max_length=10, help_text='Business/shop phone — can also be used to login'),
        ),
    ]
