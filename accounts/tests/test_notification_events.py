# accounts/tests/test_notification_events.py
"""
Unit tests for NotificationEnvelope dataclass and template registry.
"""
from django.test import TestCase

from accounts.domain.notification_events import (
    NotificationConfig,
    NotificationEnvelope,
    RecipientInfo,
)
from accounts.domain.notification_templates import (
    NotificationTemplate,
    TEMPLATE_DEFAULTS,
    get_template_defaults,
)


class NotificationEnvelopeTest(TestCase):

    def test_envelope_serialization_roundtrip(self):
        """Envelope.to_dict() produces a JSON-serialisable dict."""
        envelope = NotificationEnvelope(
            notification=NotificationConfig(
                template=NotificationTemplate.SIGNUP_OTP,
                channels=('SMS', 'EMAIL'),
            ),
            recipient=RecipientInfo(
                email='test@example.com',
                phone='+1234567890',
            ),
            variables={'otp': '123456', 'expiry_minutes': 10, 'app_name': 'EYGAR'},
        )

        result = envelope.to_dict()

        self.assertEqual(result['event_type'], 'SendNotification')
        self.assertEqual(result['notification']['template'], 'SIGNUP_OTP')
        self.assertIsInstance(result['notification']['channels'], list)
        self.assertEqual(result['notification']['channels'], ['SMS', 'EMAIL'])
        self.assertEqual(result['recipient']['email'], 'test@example.com')
        self.assertEqual(result['recipient']['phone'], '+1234567890')
        self.assertEqual(result['variables']['otp'], '123456')
        self.assertEqual(result['variables']['expiry_minutes'], 10)
        self.assertEqual(result['variables']['app_name'], 'EYGAR')

    def test_envelope_channels_converted_to_list(self):
        """Channels tuple is serialised as a JSON-compatible list."""
        envelope = NotificationEnvelope(
            notification=NotificationConfig(channels=('EMAIL',)),
        )
        result = envelope.to_dict()
        self.assertIsInstance(result['notification']['channels'], list)
        self.assertEqual(result['notification']['channels'], ['EMAIL'])

    def test_envelope_defaults(self):
        """Default envelope has sensible values."""
        envelope = NotificationEnvelope()
        result = envelope.to_dict()

        self.assertIn('event_id', result)
        self.assertTrue(result['event_id'].startswith('evt_'))
        self.assertEqual(result['event_type'], 'SendNotification')
        self.assertEqual(result['notification']['template'], '')
        self.assertEqual(result['notification']['channels'], ['EMAIL'])

    def test_envelope_has_unique_event_ids(self):
        """Each envelope gets a unique event_id."""
        e1 = NotificationEnvelope()
        e2 = NotificationEnvelope()
        self.assertNotEqual(e1.event_id, e2.event_id)

    def test_envelope_event_id_format(self):
        """Event IDs start with 'evt_' prefix."""
        envelope = NotificationEnvelope()
        self.assertTrue(envelope.event_id.startswith('evt_'))

    def test_envelope_immutable(self):
        """Frozen dataclass prevents accidental mutation."""
        envelope = NotificationEnvelope()
        with self.assertRaises(AttributeError):
            envelope.event_type = 'MODIFIED'

    def test_envelope_omits_none_recipient_fields(self):
        """to_dict() strips None values from recipient for cleaner payload."""
        envelope = NotificationEnvelope(
            recipient=RecipientInfo(email='test@example.com', phone=None),
        )
        result = envelope.to_dict()
        self.assertIn('email', result['recipient'])
        self.assertNotIn('phone', result['recipient'])

    def test_envelope_includes_both_recipient_fields_when_set(self):
        """to_dict() includes both email and phone when both are provided."""
        envelope = NotificationEnvelope(
            recipient=RecipientInfo(email='test@example.com', phone='+123'),
        )
        result = envelope.to_dict()
        self.assertEqual(result['recipient']['email'], 'test@example.com')
        self.assertEqual(result['recipient']['phone'], '+123')

    def test_recipient_info_defaults(self):
        """RecipientInfo defaults to None values."""
        r = RecipientInfo()
        self.assertIsNone(r.email)
        self.assertIsNone(r.phone)


class NotificationTemplateRegistryTest(TestCase):

    def test_all_templates_have_defaults(self):
        """Every template constant has an entry in TEMPLATE_DEFAULTS."""
        template_constants = [
            v for k, v in NotificationTemplate.__dict__.items()
            if not k.startswith('_')
        ]
        for template in template_constants:
            defaults = get_template_defaults(template)
            self.assertIn('channels', defaults)

    def test_otp_templates_have_sms_channel(self):
        """All OTP templates (except email-only) include SMS."""
        sms_otp_templates = [
            NotificationTemplate.SIGNUP_OTP,
            NotificationTemplate.LOGIN_OTP,
            NotificationTemplate.PASSWORD_RESET_OTP,
        ]
        for template in sms_otp_templates:
            defaults = get_template_defaults(template)
            self.assertIn('SMS', defaults['channels'], f"{template} should include SMS")

    def test_unknown_template_returns_safe_fallback(self):
        """Unknown template names fall back to EMAIL."""
        defaults = get_template_defaults('NONEXISTENT_TEMPLATE')
        self.assertEqual(defaults['channels'], ('EMAIL',))

    def test_signup_otp_defaults(self):
        defaults = get_template_defaults(NotificationTemplate.SIGNUP_OTP)
        self.assertIn('SMS', defaults['channels'])
        self.assertIn('EMAIL', defaults['channels'])

    def test_login_otp_defaults(self):
        defaults = get_template_defaults(NotificationTemplate.LOGIN_OTP)
        self.assertIn('SMS', defaults['channels'])
        self.assertIn('EMAIL', defaults['channels'])

    def test_password_reset_otp_defaults(self):
        defaults = get_template_defaults(NotificationTemplate.PASSWORD_RESET_OTP)
        self.assertIn('SMS', defaults['channels'])
        self.assertIn('EMAIL', defaults['channels'])

    def test_host_profile_templates_are_email_only(self):
        """Host profile notifications should only go via email."""
        host_templates = [
            NotificationTemplate.HOST_PROFILE_SUBMITTED,
            NotificationTemplate.HOST_PROFILE_APPROVED,
            NotificationTemplate.HOST_PROFILE_REJECTED,
        ]
        for template in host_templates:
            defaults = get_template_defaults(template)
            self.assertEqual(defaults['channels'], ('EMAIL',))

    def test_future_templates_exist(self):
        """Verify future template constants are registered."""
        self.assertEqual(NotificationTemplate.BOOKING_CONFIRMATION, 'BOOKING_CONFIRMATION')
        self.assertEqual(NotificationTemplate.PAYMENT_CONFIRMATION, 'PAYMENT_CONFIRMATION')
        self.assertEqual(NotificationTemplate.PAYMENT_FAILED, 'PAYMENT_FAILED')
