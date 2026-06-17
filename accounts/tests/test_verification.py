# accounts/tests/test_verification.py
"""
Unit tests for verification code validation and account activation.
"""
from datetime import timedelta
from unittest.mock import MagicMock

from django.test import TestCase
from django.utils import timezone

from accounts.application.dto import VerifyCodeDTO, ResendCodeDTO
from accounts.application.services.verification_service import VerificationService
from accounts.domain.exceptions import (
    InvalidVerificationCodeError,
    UserNotFoundError,
    VerificationCodeExpiredError,
)
from accounts.models import GuestProfile, VerificationCode
from accounts.tests.factories import create_user, create_verification_code


class VerifyCodeTest(TestCase):

    def setUp(self):
        self.mock_notification = MagicMock()
        self.mock_sns = MagicMock()
        self.service = VerificationService(
            notification_gateway=self.mock_notification,
            sqs_publisher=self.mock_sns,
        )

    def test_verify_correct_code_activates_user(self):
        user = create_user(email='verify@example.com')
        create_verification_code(user, code='123456', channel='email')

        dto = VerifyCodeDTO(email_or_phone='verify@example.com', code='123456')
        result = self.service.verify_code(dto)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)
        self.assertTrue(result['is_active'])

    def test_verify_creates_guest_profile(self):
        user = create_user(email='guest@example.com')
        create_verification_code(user, code='111111', channel='email')

        dto = VerifyCodeDTO(email_or_phone='guest@example.com', code='111111')
        self.service.verify_code(dto)

        self.assertTrue(GuestProfile.objects.filter(user=user).exists())
        profile = GuestProfile.objects.get(user=user)
        self.assertEqual(profile.email, 'guest@example.com')

    def test_verify_publishes_guest_profile_created_event(self):
        user = create_user(email='events@example.com')
        create_verification_code(user, code='222222', channel='email')

        dto = VerifyCodeDTO(email_or_phone='events@example.com', code='222222')
        self.service.verify_code(dto)

        # Should publish GuestProfileCreated event
        events = [call[0][0] for call in self.mock_sns.publish_event.call_args_list]
        event_types = [e.event_type for e in events]
        self.assertIn('GuestProfileCreated', event_types)

    def test_verify_phone_sets_phone_verified(self):
        user = create_user(email=None, phone_number='+1111111111')
        create_verification_code(user, code='333333', channel='phone')

        dto = VerifyCodeDTO(email_or_phone='+1111111111', code='333333')
        result = self.service.verify_code(dto)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_phone_verified)

    def test_verify_rejects_wrong_code(self):
        user = create_user(email='wrong@example.com')
        create_verification_code(user, code='123456', channel='email')

        dto = VerifyCodeDTO(email_or_phone='wrong@example.com', code='000000')
        with self.assertRaises(InvalidVerificationCodeError):
            self.service.verify_code(dto)

        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_verify_rejects_expired_code(self):
        user = create_user(email='expired@example.com')
        create_verification_code(
            user,
            code='444444',
            channel='email',
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        dto = VerifyCodeDTO(email_or_phone='expired@example.com', code='444444')
        with self.assertRaises(InvalidVerificationCodeError):
            self.service.verify_code(dto)

    def test_verify_rejects_used_code(self):
        user = create_user(email='used@example.com')
        create_verification_code(user, code='555555', channel='email', is_used=True)

        dto = VerifyCodeDTO(email_or_phone='used@example.com', code='555555')
        with self.assertRaises(InvalidVerificationCodeError):
            self.service.verify_code(dto)

    def test_verify_rejects_nonexistent_user(self):
        dto = VerifyCodeDTO(email_or_phone='nobody@example.com', code='123456')
        with self.assertRaises(UserNotFoundError):
            self.service.verify_code(dto)

    def test_verify_does_not_create_duplicate_profile(self):
        user = create_user(email='nodup@example.com')
        GuestProfile.objects.create(user=user, email='nodup@example.com')
        create_verification_code(user, code='666666', channel='email')

        dto = VerifyCodeDTO(email_or_phone='nodup@example.com', code='666666')
        self.service.verify_code(dto)

        self.assertEqual(GuestProfile.objects.filter(user=user).count(), 1)

    def test_verify_both_email_and_phone_publishes_user_verified(self):
        user = create_user(email='both@example.com', phone_number='+9999999999')
        # Simulate email already verified
        user.is_active = True
        user.is_email_verified = True
        user.save()

        # Now verify phone
        create_verification_code(user, code='777777', channel='phone', purpose='registration')

        dto = VerifyCodeDTO(email_or_phone='+9999999999', code='777777')
        self.service.verify_code(dto)

        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertTrue(user.is_phone_verified)

        events = [call[0][0] for call in self.mock_sns.publish_event.call_args_list]
        event_types = [e.event_type for e in events]
        self.assertIn('UserVerified', event_types)


class ResendCodeTest(TestCase):

    def setUp(self):
        self.mock_notification = MagicMock()
        self.mock_sns = MagicMock()
        self.service = VerificationService(
            notification_gateway=self.mock_notification,
            sqs_publisher=self.mock_sns,
        )

    def test_resend_creates_new_code(self):
        user = create_user(email='resend@example.com')
        create_verification_code(user, code='111111', channel='email')

        dto = ResendCodeDTO(email_or_phone='resend@example.com')
        self.service.resend_code(dto)

        # Old code should be invalidated
        old_codes = VerificationCode.objects.filter(user=user, code='111111')
        self.assertTrue(all(c.is_used for c in old_codes))

        # New code should exist
        new_code = VerificationCode.objects.filter(user=user, is_used=False).first()
        self.assertIsNotNone(new_code)
        self.assertNotEqual(new_code.code, '111111')

    def test_resend_sends_notification(self):
        user = create_user(email='resend2@example.com')

        dto = ResendCodeDTO(email_or_phone='resend2@example.com')
        self.service.resend_code(dto)

        self.mock_notification.send_verification_code.assert_called_once()

    def test_resend_rejects_nonexistent_user(self):
        dto = ResendCodeDTO(email_or_phone='nobody@example.com')
        with self.assertRaises(UserNotFoundError):
            self.service.resend_code(dto)
