from channels.generic.websocket import AsyncWebsocketConsumer
import json
from asgiref.sync import sync_to_async
from django.core.cache import cache
from datetime import datetime
from accounts.utils import create_presigned_url

def get_custom_user_model():
    from accounts.models import CustomUser
    return CustomUser

def get_custom_worker_model():
    from worker.models import CustomWorker
    return CustomWorker

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f"notification_{self.user_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

        notifications = await sync_to_async(self.get_pending_notifications)()
        for notification in notifications:
            if isinstance(notification['sender']['profile_pic'], str):
                profile_pic = notification['sender']['profile_pic']
            else:
                profile_pic = notification['sender']['profile_pic'].url

            print(profile_pic, 'profile_pic', notification['sender']['profile_pic'])

            await self.send(text_data=json.dumps({
                "type": "notification",
                "notification": {
                    **notification,
                    "sender": {
                        **notification['sender'],
                        'profile_pic': create_presigned_url(profile_pic)
                    }
                },
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        notification = text_data_json['notification']

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'send_notification',
                'notification': notification
            }
        )

    async def send_notification(self, event):
        notification = event["notification"]

        if notification.get("sender", {}).get("profile_pic"):
            profile_pic_url = str(notification["sender"]["profile_pic"])
            print(f"Profile Pic URL: {profile_pic_url}")
            notification["sender"]["profile_pic"] = create_presigned_url(profile_pic_url)
            
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": notification
        }))
    
    def get_pending_notifications(self):
        """Retrieve pending notifications from Redis."""
        notifications = cache.get(f"notifications_{self.user_id}", [])
        print(notifications, 'notifications')
        return notifications

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.role = self.scope['url_route']['kwargs']['role']
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.worker_id = self.scope['url_route']['kwargs']['worker_id']

        self.notification_user_group_name = f"notification_{self.user_id}"
        await self.channel_layer.group_add(
            self.notification_user_group_name,
            self.channel_name
        )

        self.notification_worker_group_name = f"notification_{self.worker_id}"
        await self.channel_layer.group_add(
            self.notification_worker_group_name,
            self.channel_name
        )

        self.room_group_name = f"chat_user_{self.user_id}_worker_{self.worker_id}"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()


        print(self.role, 'role')
        if self.role == 'user':
            notification_key = f"notifications_{self.user_id}"
        elif self.role == 'worker':
            notification_key = f"notifications_{self.worker_id}"
        else:
            notification_key = None

        if notification_key:
            print(notification_key, 'notificatation_key')
            notifications = cache.get(notification_key, [])
            non_chat_notifications = [
                notification for notification in notifications if notification.get("type") != "chat"
            ]

            print(non_chat_notifications, 'non_chat_notifications')

            cache.set(notification_key, non_chat_notifications, timeout=3600)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        from accounts.models import ChatMessage
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        sender_type = text_data_json.get('sender_type')
        recipient_type = 'worker' if sender_type == 'user' else 'user'
        sender_id = self.user_id if sender_type == 'user' else self.worker_id
        recipient_id = self.worker_id if sender_type == 'user' else self.user_id

        await sync_to_async(ChatMessage.objects.create)(
            sender_id=sender_id,
            sender_type=sender_type,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            message=message
        )
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': sender_id,
                'recipient_id': recipient_id,
                'sender_type': sender_type,
            }
        )

        recipient_group_name = (
            self.notification_worker_group_name if recipient_type == 'worker' 
            else self.notification_user_group_name)

        if sender_type == 'user':
            model = get_custom_user_model()
            sender = await sync_to_async(model.objects.get)(id=sender_id)
            user_profile = await sync_to_async(lambda: sender.user_profile)()
            notification_data = {
                'type':'chat',
                "message": message[:30],
                "sender": {
                    "id": sender.id,
                    "first_name": user_profile.first_name,
                    "profile_pic": str(user_profile.profile_pic) if user_profile.profile_pic else None,
                },
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        elif sender_type == 'worker':
            model = get_custom_worker_model()
            sender = await sync_to_async(model.objects.get)(id=sender_id)
            worker_profile = await sync_to_async(lambda: sender.worker_profile)()
            notification_data = {
                'type':'chat',
                "message": message[:30],
                "sender": {
                    "id": sender.id,
                    "first_name": worker_profile.first_name,
                    "profile_pic": str(worker_profile.profile_pic) if worker_profile.profile_pic else None,
                },
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        
        await sync_to_async(self.store_notification_in_redis)(
            recipient_id,
            notification_data
        )

        await self.channel_layer.group_send(
            recipient_group_name,
            {
                'type': 'send_notification',
                "notification": notification_data,
            }
        )

    async def send_notification(self, event):
        notification = event["notification"]
        await self.send(text_data=json.dumps({
                "type": "notification",
                "notification": {
                    **notification,
                    "sender": {
                        **notification['sender'],
                        'profile_pic': create_presigned_url(notification['sender']['profile_pic'])
                    }
                },
            }))
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type':'chat',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'recipient_id': event['recipient_id'],
            'sender_type': event['sender_type'],
        }))

    def store_notification_in_redis(self, recipient_id, notification_data):
        """Store notification in Redis with TTL."""
        key = f"notifications_{recipient_id}"
        notifications = cache.get(key, [])
        notifications.append(notification_data)
        cache.set(key, notifications, timeout=3600)