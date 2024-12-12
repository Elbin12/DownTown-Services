from celery import shared_task
from django.core.mail import send_mail
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@shared_task
def send_mail_task(subject, message, email_from, recipient_list):
    print("Task started")
    try:
        send_mail(subject, message, email_from, recipient_list, fail_silently=False)
        print(f"Email sent successfully to {recipient_list}")
    except Exception as e:
        print(f"Error sending email to {recipient_list}: {str(e)}") 

@shared_task
def send_notification(user_id, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notification_{user_id}",  
        {
            "type": "send_notification",
            "notification": message,
            'notification_type':'notification'
        }
    )