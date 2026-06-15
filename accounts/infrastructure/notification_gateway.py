# accounts/infrastructure/notification_gateway.py
"""
Gateway to the eygarnotification microservice.
All verification codes, password resets, and transactional notifications
are sent as SNS events that eygarnotification subscribes to.

This service NEVER sends SMS or email directly.

Each published message is a self-contained NotificationEnvelope so the
Notification Service can process it without calling back to the Auth Service.
"""
import json
import logging

import boto3
from django.conf import settings

from accounts.domain.notification_events import (
    NotificationConfig,
    NotificationEnvelope,
    RecipientInfo,
)
from accounts.domain.notification_templates import (
    NotificationTemplate,
    get_template_defaults,
)

logger = logging.getLogger(__name__)

# App name included in every notification for template branding
APP_NAME = 'EYGAR'


def _channel_for_identifier(channel: str) -> tuple[str, ...]:
    """Map a legacy 'email'/'phone' channel string to uppercase tuple."""
    if channel == 'email':
        return ('EMAIL',)
    if channel == 'phone':
        return ('SMS',)
    return ('EMAIL',)


def _purpose_to_template(purpose: str) -> str:
    """Map a legacy purpose string to a NotificationTemplate constant."""
    mapping = {
        'registration': NotificationTemplate.SIGNUP_OTP,
        'login': NotificationTemplate.LOGIN_OTP,
        'email_verification': NotificationTemplate.EMAIL_VERIFICATION_OTP,
        'phone_verification': NotificationTemplate.PHONE_VERIFICATION_OTP,
        'password_reset': NotificationTemplate.PASSWORD_RESET_OTP,
    }
    return mapping.get(purpose, NotificationTemplate.SIGNUP_OTP)


# Maps each notification template to a human-readable event type that is
# surfaced in the SNS envelope and MessageAttribute for filter policies.
_TEMPLATE_EVENT_TYPE: dict[str, str] = {
    NotificationTemplate.SIGNUP_OTP: 'UserRegistration',
    NotificationTemplate.LOGIN_OTP: 'UserLogin',
    NotificationTemplate.EMAIL_VERIFICATION_OTP: 'EmailVerification',
    NotificationTemplate.PHONE_VERIFICATION_OTP: 'PhoneVerification',
    NotificationTemplate.PASSWORD_RESET_OTP: 'PasswordResetRequested',
    NotificationTemplate.GENERIC_TRANSACTIONAL: 'TransactionalNotification',
}


def _template_to_event_type(template: str) -> str:
    """Return the semantic event type for a given notification template."""
    return _TEMPLATE_EVENT_TYPE.get(template, 'SendNotification')


class NotificationGateway:
    """
    Publishes notification-request events to an SNS topic
    that the eygarnotification service subscribes to.
    """

    def __init__(self, topic_arn: str | None = None):
        self._topic_arn = (
            topic_arn
            or getattr(settings, 'SNS_NOTIFICATION_TOPIC_ARN', None)
            or getattr(settings, 'SNS_TOPIC_ARN', None)
        )
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                'sns',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION_NAME,
            )
        return self._client

    # ----- Core publish method -----

    def _publish(self, envelope: NotificationEnvelope) -> dict | None:
        """
        Serialise a NotificationEnvelope and publish to SNS.

        Sets MessageAttributes for event_type and template so the
        Notification Service can use SNS subscription filter policies.
        """
        if not self._topic_arn:
            logger.warning(
                "SNS notification topic ARN not configured — '%s/%s' not sent.",
                envelope.event_type,
                envelope.notification.template,
            )
            return None

        try:
            response = self.client.publish(
                TopicArn=self._topic_arn,
                Message=json.dumps(envelope.to_dict()),
                MessageAttributes={
                    'event_type': {
                        'DataType': 'String',
                        'StringValue': envelope.event_type,
                    },
                    'template': {
                        'DataType': 'String',
                        'StringValue': envelope.notification.template,
                    },
                },
            )
            logger.info(
                "Published notification '%s' (template=%s) to SNS. MessageId=%s",
                envelope.event_type,
                envelope.notification.template,
                response.get('MessageId'),
            )
            return response
        except Exception:
            logger.exception(
                "Failed to publish notification '%s' (template=%s) to SNS.",
                envelope.event_type,
                envelope.notification.template,
            )
            return None

    # ----- Public API -----

    def send_verification_code(
        self,
        channel: str,
        recipient: str,
        code: str,
        purpose: str = 'registration',
        *,
        user_id: str = '',
        user_name: str = '',
        correlation_id: str | None = None,
    ) -> dict | None:
        """
        Request eygarnotification to deliver a verification code.

        Parameters
        ----------
        channel : str
            'email' or 'phone'
        recipient : str
            Email address or phone number
        code : str
            The 6-digit verification code
        purpose : str
            'registration', 'login', 'email_verification', 'phone_verification'
        user_id : str
            UUID of the user (included in variables for tracking)
        user_name : str
            Display name of the user (for template personalisation)
        """
        template = _purpose_to_template(purpose)
        event_type = _template_to_event_type(template)
        defaults = get_template_defaults(template)
        channels = _channel_for_identifier(channel)

        expiry_minutes = getattr(
            settings, 'VERIFICATION_CODE_EXPIRY_MINUTES', 10
        )

        envelope = NotificationEnvelope(
            event_type=event_type,
            notification=NotificationConfig(
                template=template,
                channels=channels,
            ),
            recipient=RecipientInfo(
                email=recipient if channel == 'email' else None,
                phone=recipient if channel == 'phone' else None,
            ),
            variables={
                'otp': code,
                'expiry_minutes': expiry_minutes,
                'app_name': APP_NAME,
                'user_name': user_name or '',
                'user_id': user_id,
            },
        )

        return self._publish(envelope)

    def send_password_reset(
        self,
        channel: str,
        recipient: str,
        code: str,
        reset_url: str | None = None,
        *,
        user_id: str = '',
        user_name: str = '',
        correlation_id: str | None = None,
    ) -> dict | None:
        """
        Request eygarnotification to deliver a password-reset code/link.
        """
        channels = _channel_for_identifier(channel)
        event_type = _template_to_event_type(NotificationTemplate.PASSWORD_RESET_OTP)

        envelope = NotificationEnvelope(
            event_type=event_type,
            notification=NotificationConfig(
                template=NotificationTemplate.PASSWORD_RESET_OTP,
                channels=channels,
            ),
            recipient=RecipientInfo(
                email=recipient if channel == 'email' else None,
                phone=recipient if channel == 'phone' else None,
            ),
            variables={
                'otp': code,
                'expiry_minutes': 15,
                'reset_url': reset_url or '',
                'app_name': APP_NAME,
                'user_name': user_name or '',
                'user_id': user_id,
            },
        )

        return self._publish(envelope)

    def send_transactional_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        html_message: str | None = None,
        *,
        template: str = '',
        user_id: str = '',
        user_name: str = '',
        correlation_id: str | None = None,
    ) -> dict | None:
        """
        Request eygarnotification to send a generic transactional email.
        Used for host profile status updates, welcome emails, etc.
        """
        resolved_template = template or NotificationTemplate.GENERIC_TRANSACTIONAL
        event_type = _template_to_event_type(resolved_template)
        defaults = get_template_defaults(resolved_template)

        envelope = NotificationEnvelope(
            event_type=event_type,
            notification=NotificationConfig(
                template=resolved_template,
                channels=tuple(defaults.get('channels', ('EMAIL',))),
            ),
            recipient=RecipientInfo(
                email=to_email,
            ),
            variables={
                'subject': subject,
                'body': message,
                'html_body': html_message or '',
                'app_name': APP_NAME,
                'user_name': user_name or '',
                'user_id': user_id,
            },
        )

        return self._publish(envelope)

    def send_notification(self, envelope: NotificationEnvelope) -> dict | None:
        """
        Publish a pre-built NotificationEnvelope directly.
        Use this for custom / future notification types.
        """
        return self._publish(envelope)


# Module-level singleton
_default_gateway = None


def get_notification_gateway() -> NotificationGateway:
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = NotificationGateway()
    return _default_gateway
