from django.conf import settings
from django.core.mail import send_mail

from accounts.infrastructure.notification_gateway import get_notification_gateway

import logging
logger = logging.getLogger(__name__)


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

    # Non-local:
        - Publishes email to SQS for processing by eygarnotification service

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
        Additional metadata for consumers
    """

    # Local / debug mode → send directly via Django email backend
    if settings.DEBUG and getattr(settings, "ENV", "local") == "local":
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        return {"status": "sent", "mode": "direct"}

    # Non-local → delegate to eygarnotification via SQS
    gateway = get_notification_gateway()
    gateway.send_transactional_email(
        to_email=to_email,
        subject=subject,
        message=message,
        html_message=html_message,
    )
    return {"status": "queued", "mode": "sqs"}
