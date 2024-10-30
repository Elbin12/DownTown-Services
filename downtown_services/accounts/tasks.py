from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from celery.utils.log import get_task_logger
from django.core.mail import EmailMessage

@shared_task
def send_mail_task(subject, message, email_from, recipient_list):
    print("Task started")
    try:
        send_mail(subject, message, email_from, recipient_list, fail_silently=False)
        print(f"Email sent successfully to {recipient_list}")
    except Exception as e:
        print(f"Error sending email to {recipient_list}: {str(e)}") 