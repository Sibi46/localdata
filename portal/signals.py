from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import PortalNotification



@receiver(post_save, sender=PortalNotification)
def push_notification(sender, instance, created, **kwargs):
    if not created:
        return
    channel_layer = get_channel_layer()
    group_name = f'notif_user_{instance.user_id}'
    async_to_sync(channel_layer.group_send)(group_name, {
        'type': 'send_notification',
        'message': instance.message,
        'link': instance.link or '',
        'notif_type': instance.notif_type,
    })
