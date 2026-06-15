# accounts/tests/test_sns_publisher.py
"""
Unit tests for SNS event publisher.
Verifies that domain events are published in the standard envelope format.
"""
import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from accounts.domain.events import UserRegistered, GuestProfileCreated
from accounts.domain.notification_events import RecipientInfo
from accounts.infrastructure.sns_publisher import SNSEventPublisher


class SNSEventPublisherTest(TestCase):

    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.publish.return_value = {'MessageId': 'msg-123'}
        self.publisher = SNSEventPublisher(topic_arn='arn:aws:sns:us-east-1:000:test')
        self.publisher._client = self.mock_client

    def _get_published_envelope(self) -> dict:
        call_kwargs = self.mock_client.publish.call_args[1]
        return json.loads(call_kwargs['Message'])

    def test_publish_with_correct_topic(self):
        result = self.publisher.publish('SIGNUP_OTP', {'user_id': '123'})

        self.assertIsNotNone(result)
        self.mock_client.publish.assert_called_once()
        call_kwargs = self.mock_client.publish.call_args[1]
        self.assertEqual(call_kwargs['TopicArn'], 'arn:aws:sns:us-east-1:000:test')

    def test_publish_produces_envelope_format(self):
        """Published messages follow the standard envelope structure."""
        self.publisher.publish(
            'SIGNUP_OTP',
            {'user_id': '123'},
            recipient=RecipientInfo(email='test@example.com'),
        )

        envelope = self._get_published_envelope()
        # When no explicit event_type is given, it defaults to "SendNotification"
        self.assertEqual(envelope['event_type'], 'SendNotification')
        self.assertEqual(envelope['notification']['template'], 'SIGNUP_OTP')
        self.assertIn('channels', envelope['notification'])
        self.assertEqual(envelope['recipient']['email'], 'test@example.com')
        self.assertIn('app_name', envelope['variables'])
        self.assertEqual(envelope['variables']['app_name'], 'EYGAR')
        self.assertTrue(envelope['event_id'].startswith('evt_'))

    def test_publish_includes_message_attributes(self):
        self.publisher.publish('SIGNUP_OTP', {'user_id': '123'})

        call_kwargs = self.mock_client.publish.call_args[1]
        self.assertIn('MessageAttributes', call_kwargs)
        self.assertEqual(
            call_kwargs['MessageAttributes']['event_type']['StringValue'],
            'SendNotification',   # default when no event_type kwarg is passed
        )
        self.assertEqual(
            call_kwargs['MessageAttributes']['template']['StringValue'],
            'SIGNUP_OTP',
        )

    def test_publish_event_user_registered(self):
        """publish_event() correctly converts a UserRegistered domain event."""
        event = UserRegistered(
            user_id='user-1',
            email='test@example.com',
            phone_number='+1234567890',
            otp='987654',
        )
        self.publisher.publish_event(event)

        envelope = self._get_published_envelope()
        # event_type is derived from the domain event class
        self.assertEqual(envelope['event_type'], 'UserRegistration')
        self.assertEqual(envelope['notification']['template'], 'SIGNUP_OTP')
        self.assertEqual(envelope['recipient']['email'], 'test@example.com')
        self.assertEqual(envelope['recipient']['phone'], '+1234567890')
        self.assertEqual(envelope['variables']['user_id'], 'user-1')
        self.assertEqual(envelope['variables']['otp'], '987654')
        self.assertEqual(envelope['variables']['app_name'], 'EYGAR')

    def test_publish_event_guest_profile_created(self):
        event = GuestProfileCreated(
            user_id='user-2',
            guest_profile_id='gp-1',
            email='guest@example.com',
        )
        self.publisher.publish_event(event)

        envelope = self._get_published_envelope()
        self.assertEqual(envelope['notification']['template'], 'GUEST_PROFILE_CREATED')
        self.assertEqual(envelope['variables']['guest_profile_id'], 'gp-1')

    @override_settings(
        SNS_AUTH_EVENTS_TOPIC_ARN=None,
        SNS_TOPIC_ARN=None,
    )
    def test_publish_handles_missing_topic(self):
        publisher = SNSEventPublisher(topic_arn=None)
        result = publisher.publish('SIGNUP_OTP', {'key': 'value'})
        self.assertIsNone(result)

    def test_publish_handles_sns_error(self):
        self.mock_client.publish.side_effect = Exception("SNS Error")
        result = self.publisher.publish('SIGNUP_OTP', {'key': 'value'})
        self.assertIsNone(result)  # Should not raise

    @override_settings(AWS_ACCESS_KEY_ID=None, AWS_SECRET_ACCESS_KEY=None)
    def test_publish_handles_missing_aws_credentials(self):
        publisher = SNSEventPublisher(topic_arn='arn:aws:sns:us-east-1:000:test')
        result = publisher.publish('SIGNUP_OTP', {'key': 'value'})
        self.assertIsNone(result)

    def test_publish_recipient_none_fields_stripped(self):
        """Recipient with None fields produces a clean payload."""
        self.publisher.publish(
            'SIGNUP_OTP',
            {'user_id': '123'},
            recipient=RecipientInfo(email='test@example.com', phone=None),
        )

        envelope = self._get_published_envelope()
        self.assertIn('email', envelope['recipient'])
        self.assertNotIn('phone', envelope['recipient'])

    def test_envelope_top_level_keys(self):
        """Every published message has exactly the expected top-level keys."""
        self.publisher.publish('SIGNUP_OTP', {'user_id': '123'})
        envelope = self._get_published_envelope()
        expected_keys = {'event_id', 'event_type', 'notification', 'recipient', 'variables'}
        self.assertEqual(set(envelope.keys()), expected_keys)
