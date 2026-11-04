from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0003_event_community_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='rsvp_question',
            field=models.CharField(blank=True, help_text='Optional yes/no question shown to attendees when they RSVP', max_length=300),
        ),
        migrations.AddField(
            model_name='eventparticipant',
            name='rsvp_answer',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No')], max_length=3),
        ),
    ]
