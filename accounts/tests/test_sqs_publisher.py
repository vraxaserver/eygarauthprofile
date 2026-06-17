# accounts/tests/test_sqs_publisher.py
"""
Unit tests for SQS event publisher.
Verifies that SQSEventPublisher acts as a no-op publisher.
"""
from django.test import TestCase

from accounts.domain.events import UserRegistered
from accounts.domain.notification_events import RecipientInfo
from accounts.infrastructure.sqs_publisher import SQSEventPublisher, get_sqs_publisher


class SQSEventPublisherTest(TestCase):

    def setUp(self):
        self.publisher = SQSEventPublisher(queue_url='https://sqs.us-east-1.amazonaws.com/000/test-queue')

    def test_publish_returns_none(self):
        result = self.publisher.publish(
            'SIGNUP_OTP',
            {'user_id': '123'},
            recipient=RecipientInfo(email='test@example.com'),
        )
        self.assertIsNone(result)

    def test_publish_event_returns_none(self):
        event = UserRegistered(
            user_id='user-1',
            email='test@example.com',
            phone_number='+1234567890',
            otp='987654',
        )
        result = self.publisher.publish_event(event)
        self.assertIsNone(result)

    def test_get_sqs_publisher_singleton(self):
        pub1 = get_sqs_publisher()
        pub2 = get_sqs_publisher()
        self.assertIs(pub1, pub2)
