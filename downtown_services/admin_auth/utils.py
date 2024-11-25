from accounts.tasks import send_mail_task
from django.conf import settings




def send_email_for_worker_reject(email, reason, params):
    link = f'http://localhost:3000/worker/resubmit/?{params}'
    message = (
        f"""
        Dear {email},

        We regret to inform you that your registration with DownTown Services has been rejected by our admin team.

        Reason for rejection:
        {reason}

        Click this link to reupload the files : {link}

        If you believe this decision was made in error or have any questions, please feel free to contact us.

        Best regards,  
        The DownTown Services Team
        """
    )
    send_mail_task.delay(
        "Update on Your Registration with DownTown Services",
        message,
        settings.EMAIL_HOST_USER,
        [email]
    )