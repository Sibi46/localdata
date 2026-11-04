from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0004_event_rsvp_question_answer'),
    ]

    operations = [
        migrations.RemoveField(model_name='event', name='rsvp_question'),
        migrations.RemoveField(model_name='eventparticipant', name='rsvp_answer'),
        migrations.AddField(
            model_name='event',
            name='rsvp_questions',
            field=models.JSONField(blank=True, default=list, help_text='List of yes/no questions shown to attendees when they RSVP'),
        ),
        migrations.AddField(
            model_name='eventparticipant',
            name='rsvp_answers',
            field=models.JSONField(blank=True, default=dict, help_text='Dict of {question_index: yes/no}'),
        ),
    ]
