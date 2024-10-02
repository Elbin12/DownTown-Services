from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from celery.utils.log import get_task_logger
from django.core.mail import EmailMessage

logger = get_task_logger(__name__)

@shared_task
def send_mail_task(subject, message, email_from, recipient_list):
    try:
        send_mail(subject, message, email_from, recipient_list, fail_silently=False)
        logger.info(f"Email sent successfully to {recipient_list}")
    except Exception as e:
        logger.error(f"Error sending email to {recipient_list}: {str(e)}")