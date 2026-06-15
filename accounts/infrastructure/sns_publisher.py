# accounts/infrastructure/sns_publisher.py
"""
Publishes domain events to AWS SNS topics using the standard
NotificationEnvelope format.

Every message follows the structure:
    {
      "event_id": "evt_...",
      "event_type": "UserRegistration",   # semantic name of the event
      "notification": { "template": "SIGNUP_OTP", "channels": [...] },
      "recipient": { "email": "...", "phone": "..." },
      "variables": { "otp": "123456", ... }
    }
"""
import json
import logging
import uuid

import boto3
from django.conf import settings

from accounts.domain.notification_events import (
    NotificationConfig,
    NotificationEnvelope,
    RecipientInfo,
)
from accounts.domain.notification_templates import get_template_defaults

logger = logging.getLogger(__name__)

APP_NAME = 'EYGAR'


class SNSEventPublisher:
    """
    Publishes structured domain events to an SNS topic.
    All domain events flow through this single publisher,
    formatted as NotificationEnvelopes.
    """

    def __init__(self, topic_arn: str | None = None):
        self._topic_arn = (
            topic_arn
            or getattr(settings, 'SNS_AUTH_EVENTS_TOPIC_ARN', None)
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

    def publish(
        self,
        template: str,
        variables: dict,
        recipient: RecipientInfo | None = None,
        event_type: str = "SendNotification",
    ) -> dict | None:
        """
        Publish a domain event to SNS in the standard envelope format.

        Parameters
        ----------
        template : str
            The notification template, e.g. 'SIGNUP_OTP'.
        variables : dict
            Template variables (serialisable).
        recipient : RecipientInfo, optional
            Recipient info. Defaults to empty recipient.
        event_type : str
            Semantic event name used in the SNS MessageAttribute and
            envelope payload, e.g. 'UserRegistration'. Defaults to
            'SendNotification'.

        Returns
        -------
        dict or None
            SNS publish response, or None on failure / missing config.
        """
        if not self._topic_arn:
            logger.warning(
                "SNS topic ARN not configured — template '%s' not published.",
                template,
            )
            return None

        if not all([settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY]):
            logger.warning(
                "AWS credentials not configured — template '%s' not published.",
                template,
            )
            return None

        defaults = get_template_defaults(template)
        recipient = recipient or RecipientInfo()

        envelope = NotificationEnvelope(
            event_type=event_type,
            notification=NotificationConfig(
                template=template,
                channels=tuple(defaults.get('channels', ('EMAIL',))),
            ),
            recipient=recipient,
            variables={**variables, 'app_name': APP_NAME},
        )

        try:
            response = self.client.publish(
                TopicArn=self._topic_arn,
                Message=json.dumps(envelope.to_dict()),
                MessageAttributes={
                    'event_type': {
                        'DataType': 'String',
                        'StringValue': event_type,
                    },
                    'template': {
                        'DataType': 'String',
                        'StringValue': template,
                    },
                },
            )
            logger.info(
                "Published event '%s' (template=%s) to SNS. MessageId=%s",
                event_type,
                template,
                response.get('MessageId'),
            )
            return response
        except Exception:
            logger.exception(
                "Failed to publish event '%s' (template=%s) to SNS.",
                event_type,
                template,
            )
            return None

    def publish_event(self, event) -> dict | None:
        """
        Convenience method: publish a DomainEvent dataclass directly.
        Extracts event_type, template, variables, and recipient from the event.
        """
        return self.publish(
            template=event.template,
            variables=event.to_variables(),
            recipient=event.to_recipient(),
            event_type=event.event_type,
        )


# Module-level singleton for convenience
_default_publisher = None


def get_sns_publisher() -> SNSEventPublisher:
    global _default_publisher
    if _default_publisher is None:
        _default_publisher = SNSEventPublisher()
    return _default_publisher
