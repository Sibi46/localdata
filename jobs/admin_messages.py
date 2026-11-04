"""Private messages and bell notifications for admin review results."""
from django.db import transaction
from .models import Conversation,Message,UserNotification


@transaction.atomic
def send_review_message(sender,owner,title,body,link='',notif_type='success'):
    if owner is None:
        return None
    conversation=None
    if sender.pk!=owner.pk:
        first,second=sorted([sender.pk,owner.pk])
        conversation,_=Conversation.objects.get_or_create(user_a_id=first,user_b_id=second)
        Message.objects.create(conversation=conversation,sender=sender,receiver=owner,content=body,msg_type='text')
        conversation.save(update_fields=['updated_at'])
    UserNotification.objects.create(user=owner,title=title,message=body[:200],link=link,notif_type=notif_type)
    return conversation
