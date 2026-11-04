from django.apps import apps
from django.db import connection
from django.test import TestCase
from .models import Conversation, Message, User


RETIRED = {'marketingaccess', 'reviewvoucher', 'seekercertificate', 'job', 'jobapplication',
           'savedjob', 'interview', 'offerletter', 'jobrole', 'paymentplan', 'savedcandidate',
           'wallet', 'wallettransaction', 'employersubscription', 'billingrecord',
           'pointswallet', 'pointstransaction', 'referral', 'spingift', 'userspin'}


class RetiredSchemaTests(TestCase):
    def test_removed_models_and_tables_are_absent(self):
        models = {model._meta.model_name for model in apps.get_app_config('jobs').get_models()}
        self.assertFalse(models & RETIRED)
        self.assertFalse(set(connection.introspection.table_names()) & {'jobs_' + name for name in RETIRED})

    def test_general_messages_do_not_depend_on_jobs(self):
        first = User.objects.create_user('first')
        second = User.objects.create_user('second')
        conversation = Conversation.objects.create(user_a=first, user_b=second)
        Message.objects.create(conversation=conversation, sender=first, receiver=second, content='Hello shop')
        self.client.force_login(first)
        response = self.client.get('/messages/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(conversation.messages.get().content, 'Hello shop')
