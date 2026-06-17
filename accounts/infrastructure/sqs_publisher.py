# accounts/infrastructure/sqs_publisher.py
"""
Publishes domain events to AWS SQS queue using the standard
NotificationEnvelope format.
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
from accounts.domain.notification_templates import get_template_defaults

logger = logging.getLogger(__name__)

APP_NAME = 'EYGAR'


class SQSEventPublisher:
    """
    No-op publisher for domain events.
    Domain events are no longer published to SQS to prevent duplicate messages.
    All notifications are sent directly via NotificationGateway.
    """

    def __init__(self, queue_url: str | None = None):
        self._queue_url = queue_url

    def publish(
        self,
        template: str,
        variables: dict,
        recipient: RecipientInfo | None = None,
        event_type: str = "SendNotification",
    ) -> dict | None:
        logger.info("Domain event '%s' (template=%s) publish skipped to avoid duplicates.", event_type, template)
        return None

    def publish_event(self, event) -> dict | None:
        return None


# Module-level singleton for convenience
_default_publisher = None


def get_sqs_publisher() -> SQSEventPublisher:
    global _default_publisher
    if _default_publisher is None:
        _default_publisher = SQSEventPublisher()
    return _default_publisher
