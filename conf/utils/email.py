from django.conf import settings
from django.core.mail import send_mail

from .aws_utils import publish_to_sqs  # adjust import path if needed


def send_app_email(
    *,
    to_email: str,
    subject: str,
    message: str,
    html_message: str | None = None,
    from_email: str | None = None,
    extra_payload: dict | None = None,
):
    """
    Unified email sender for all environments.

    Local / DEBUG:
        - Uses Django send_mail (console or SMTP based on EMAIL_BACKEND)

    Non-local:
        - Publishes email payload to SQS for async processing

    Parameters
    ----------
    to_email : str
        Recipient email address
    subject : str
        Email subject
    message : str
        Plain text body
    html_message : str | None
        Optional HTML body
    from_email : str | None
        Overrides DEFAULT_FROM_EMAIL
    extra_payload : dict | None
        Additional metadata for SQS consumers
    """

    payload = {
        "to": [to_email],
        "subject": subject,
        "message": message,
        "html_message": html_message,
        "from_email": from_email or settings.DEFAULT_FROM_EMAIL,
    }

    if extra_payload:
        payload.update(extra_payload)

    # Local / debug mode → send directly
    if settings.DEBUG and getattr(settings, "ENV", "local") == "local":
        send_mail(
            subject=subject,
            message=message,
            from_email=payload["from_email"],
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        return {"status": "sent", "mode": "direct"}

    # Non-local → async via SQS
    publish_to_sqs(payload)
    return {"status": "queued", "mode": "sqs"}
