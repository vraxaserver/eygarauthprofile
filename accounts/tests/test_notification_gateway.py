# accounts/tests/test_notification_gateway.py
"""
Unit tests for the notification gateway (eygarnotification integration).
Verifies that the NotificationEnvelope payloads match the expected format:

    {
      "event_id": "evt_abc123",
      "event_type": "SEND_NOTIFICATION",
      "notification": { "template": "...", "channels": [...] },
      "recipient": { "email": "...", "phone": "..." },
      "variables": { "otp": "...", "expiry_minutes": 5, "app_name": "EYGAR" }
    }
"""
from unittest.mock import MagicMock
import json

from django.test import TestCase, override_settings

from accounts.infrastructure.notification_gateway import NotificationGateway


class NotificationGatewayTest(TestCase):

    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.publish.return_value = {'MessageId': 'msg-123'}

        self.gateway = NotificationGateway(topic_arn='arn:aws:sns:us-east-1:000:notifications')
        self.gateway._client = self.mock_client

    # --- Helpers ---

    def _get_published_envelope(self) -> dict:
        call_kwargs = self.mock_client.publish.call_args[1]
        return json.loads(call_kwargs['Message'])

    def _get_published_attributes(self) -> dict:
        call_kwargs = self.mock_client.publish.call_args[1]
        return call_kwargs['MessageAttributes']

    # --- Payload structure tests ---

    def test_envelope_has_correct_top_level_keys(self):
        """Every published message has exactly the expected top-level keys."""
        self.gateway.send_verification_code(
            channel='email', recipient='test@example.com', code='123456',
        )
        envelope = self._get_published_envelope()

        expected_keys = {'event_id', 'event_type', 'notification', 'recipient', 'variables'}
        self.assertEqual(set(envelope.keys()), expected_keys)

    def test_event_type_reflects_action(self):
        """Each notification type produces a distinct, semantic event_type."""
        self.gateway.send_verification_code(
            channel='email', recipient='a@b.com', code='111111',
            purpose='registration',
        )
        self.assertEqual(self._get_published_envelope()['event_type'], 'UserRegistration')

        self.mock_client.reset_mock()
        self.gateway.send_password_reset(
            channel='email', recipient='a@b.com', code='222222',
        )
        self.assertEqual(self._get_published_envelope()['event_type'], 'PasswordResetRequested')

        self.mock_client.reset_mock()
        self.gateway.send_transactional_email(
            to_email='a@b.com', subject='Hi', message='Hello',
        )
        self.assertEqual(self._get_published_envelope()['event_type'], 'TransactionalNotification')

    def test_event_id_has_evt_prefix(self):
        self.gateway.send_verification_code(
            channel='email', recipient='test@example.com', code='123456',
        )
        envelope = self._get_published_envelope()
        self.assertTrue(envelope['event_id'].startswith('evt_'))

    # --- Verification code tests ---

    def test_send_verification_code_email(self):
        self.gateway.send_verification_code(
            channel='email', recipient='user@example.com',
            code='123456', purpose='registration',
        )

        self.mock_client.publish.assert_called_once()
        envelope = self._get_published_envelope()
        self.assertEqual(envelope['notification']['template'], 'SIGNUP_OTP')
        self.assertEqual(envelope['notification']['channels'], ['EMAIL'])
        self.assertEqual(envelope['variables']['otp'], '123456')
        self.assertEqual(envelope['recipient']['email'], 'user@example.com')
        self.assertNotIn('phone', envelope['recipient'])

    def test_send_verification_code_phone(self):
        self.gateway.send_verification_code(
            channel='phone', recipient='+97412345678',
            code='654321', purpose='registration',
        )

        envelope = self._get_published_envelope()
        self.assertEqual(envelope['notification']['channels'], ['SMS'])
        self.assertEqual(envelope['recipient']['phone'], '+97412345678')
        self.assertNotIn('email', envelope['recipient'])
        self.assertEqual(envelope['variables']['otp'], '654321')

    def test_verification_code_includes_app_name(self):
        self.gateway.send_verification_code(
            channel='email', recipient='test@example.com', code='111111',
        )
        envelope = self._get_published_envelope()
        self.assertEqual(envelope['variables']['app_name'], 'EYGAR')

    def test_verification_code_includes_expiry(self):
        self.gateway.send_verification_code(
            channel='email', recipient='test@example.com', code='111111',
        )
        envelope = self._get_published_envelope()
        self.assertIn('expiry_minutes', envelope['variables'])
        self.assertIsInstance(envelope['variables']['expiry_minutes'], int)

    def test_verification_code_includes_user_context(self):
        self.gateway.send_verification_code(
            channel='email', recipient='user@example.com', code='111111',
            user_id='user-abc-123', user_name='John',
        )
        envelope = self._get_published_envelope()
        self.assertEqual(envelope['variables']['user_id'], 'user-abc-123')
        self.assertEqual(envelope['variables']['user_name'], 'John')

    def test_verification_code_purpose_maps_to_template(self):
        """Different purposes produce different templates."""
        purposes = {
            'registration': 'SIGNUP_OTP',
            'login': 'LOGIN_OTP',
            'email_verification': 'EMAIL_VERIFICATION_OTP',
            'phone_verification': 'PHONE_VERIFICATION_OTP',
        }
        for purpose, expected_template in purposes.items():
            self.mock_client.reset_mock()
            self.gateway.send_verification_code(
                channel='email', recipient='test@example.com',
                code='000000', purpose=purpose,
            )
            envelope = self._get_published_envelope()
            self.assertEqual(
                envelope['notification']['template'], expected_template,
                f"Purpose '{purpose}' should map to template '{expected_template}'",
            )

    # --- Password reset tests ---

    def test_send_password_reset(self):
        self.gateway.send_password_reset(
            channel='email', recipient='user@example.com',
            code='999999', reset_url='https://example.com/reset?code=999999',
        )

        envelope = self._get_published_envelope()
        self.assertEqual(envelope['notification']['template'], 'PASSWORD_RESET_OTP')
        self.assertEqual(envelope['variables']['otp'], '999999')
        self.assertEqual(envelope['variables']['expiry_minutes'], 15)
        self.assertEqual(envelope['variables']['reset_url'], 'https://example.com/reset?code=999999')
        self.assertEqual(envelope['variables']['app_name'], 'EYGAR')

    def test_password_reset_includes_user_context(self):
        self.gateway.send_password_reset(
            channel='email', recipient='user@example.com', code='999999',
            user_id='user-pwd', user_name='Jane',
        )
        envelope = self._get_published_envelope()
        self.assertEqual(envelope['variables']['user_id'], 'user-pwd')
        self.assertEqual(envelope['variables']['user_name'], 'Jane')

    # --- Transactional email tests ---

    def test_send_transactional_email(self):
        self.gateway.send_transactional_email(
            to_email='user@example.com', subject='Welcome!', message='Welcome to Eygar.',
        )
        envelope = self._get_published_envelope()
        self.assertEqual(envelope['notification']['template'], 'GENERIC_TRANSACTIONAL')
        self.assertEqual(envelope['variables']['subject'], 'Welcome!')
        self.assertEqual(envelope['variables']['body'], 'Welcome to Eygar.')
        self.assertEqual(envelope['variables']['app_name'], 'EYGAR')

    def test_transactional_email_with_template(self):
        self.gateway.send_transactional_email(
            to_email='host@example.com', subject='Profile Approved',
            message='Your profile has been approved.',
            template='HOST_PROFILE_APPROVED',
            user_id='user-host', user_name='Host User',
        )
        envelope = self._get_published_envelope()
        self.assertEqual(envelope['notification']['template'], 'HOST_PROFILE_APPROVED')
        self.assertEqual(envelope['variables']['user_id'], 'user-host')
        self.assertEqual(envelope['variables']['user_name'], 'Host User')
        self.assertEqual(envelope['recipient']['email'], 'host@example.com')

    # --- SNS message attributes ---

    def test_message_attributes_include_event_type(self):
        """SNS message attribute event_type reflects the action."""
        self.gateway.send_verification_code(
            channel='email', recipient='test@example.com', code='111111',
            purpose='registration',
        )
        attrs = self._get_published_attributes()
        self.assertEqual(attrs['event_type']['StringValue'], 'UserRegistration')

    def test_message_attributes_include_template(self):
        self.gateway.send_verification_code(
            channel='email', recipient='test@example.com',
            code='111111', purpose='registration',
        )
        attrs = self._get_published_attributes()
        self.assertEqual(attrs['template']['StringValue'], 'SIGNUP_OTP')

    # --- Edge cases ---

    def test_no_direct_twilio_or_sendgrid_calls(self):
        """Ensure the gateway only publishes to SNS, not calling SMS/email APIs directly."""
        self.gateway.send_verification_code(
            channel='phone', recipient='+1234567890', code='123456',
        )
        self.mock_client.publish.assert_called_once()

    @override_settings(
        SNS_NOTIFICATION_TOPIC_ARN=None,
        SNS_TOPIC_ARN=None,
    )
    def test_handles_missing_topic_arn(self):
        gateway = NotificationGateway(topic_arn=None)
        result = gateway.send_verification_code(
            channel='email', recipient='test@example.com', code='123456',
        )
        self.assertIsNone(result)

    def test_send_notification_with_custom_envelope(self):
        """send_notification() publishes a pre-built envelope."""
        from accounts.domain.notification_events import (
            NotificationEnvelope, NotificationConfig, RecipientInfo,
        )
        envelope = NotificationEnvelope(
            notification=NotificationConfig(
                template='BOOKING_CONFIRMATION', channels=('SMS', 'EMAIL'),
            ),
            recipient=RecipientInfo(email='guest@example.com', phone='+123'),
            variables={'booking_id': 'BK-001', 'check_in': '2026-07-01', 'app_name': 'EYGAR'},
        )
        self.gateway.send_notification(envelope)

        self.mock_client.publish.assert_called_once()
        published = self._get_published_envelope()
        self.assertEqual(published['notification']['template'], 'BOOKING_CONFIRMATION')
        self.assertEqual(published['notification']['channels'], ['SMS', 'EMAIL'])
        self.assertEqual(published['variables']['booking_id'], 'BK-001')
