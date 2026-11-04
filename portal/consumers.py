import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
            return
        self.group_name = f'notif_user_{self.scope["user"].id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receives message pushed from channel layer
    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'link':    event.get('link', ''),
            'type':    event.get('notif_type', 'info'),
        }))
