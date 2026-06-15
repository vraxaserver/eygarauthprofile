# accounts/tests/test_password_reset.py
"""
Unit tests for forgot-password and reset-password flows.
"""
from datetime import timedelta
from unittest.mock import MagicMock

from django.test import TestCase
from django.utils import timezone

from accounts.application.dto import ForgotPasswordDTO, ResetPasswordDTO
from accounts.application.services.password_service import PasswordService
from accounts.domain.exceptions import (
    InvalidVerificationCodeError,
    PasswordMismatchError,
    UserNotFoundError,
    VerificationCodeExpiredError,
)
from accounts.models import PasswordResetToken
from accounts.tests.factories import create_active_user, create_password_reset_token


class ForgotPasswordTest(TestCase):

    def setUp(self):
        self.mock_notification = MagicMock()
        self.mock_sns = MagicMock()
        self.service = PasswordService(
            notification_gateway=self.mock_notification,
            sns_publisher=self.mock_sns,
        )

    def test_forgot_password_with_email(self):
        create_active_user(email='forgot@example.com')

        dto = ForgotPasswordDTO(email_or_phone='forgot@example.com')
        result = self.service.forgot_password(dto)

        self.assertIn('message', result)
        self.mock_notification.send_password_reset.assert_called_once()

    def test_forgot_password_with_phone(self):
        create_active_user(email=None, phone_number='+5551234567', is_phone_verified=True)

        dto = ForgotPasswordDTO(email_or_phone='+5551234567')
        result = self.service.forgot_password(dto)

        self.assertIn('message', result)
        self.mock_notification.send_password_reset.assert_called_once()

    def test_forgot_password_creates_reset_token(self):
        user = create_active_user(email='token@example.com')

        dto = ForgotPasswordDTO(email_or_phone='token@example.com')
        self.service.forgot_password(dto)

        tokens = PasswordResetToken.objects.filter(user=user)
        self.assertEqual(tokens.count(), 1)
        self.assertEqual(len(tokens.first().code), 6)

    def test_forgot_password_invalidates_old_tokens(self):
        user = create_active_user(email='oldtoken@example.com')
        create_password_reset_token(user, code='111111')

        dto = ForgotPasswordDTO(email_or_phone='oldtoken@example.com')
        self.service.forgot_password(dto)

        old_token = PasswordResetToken.objects.get(code='111111')
        self.assertTrue(old_token.is_used)

    def test_forgot_password_rejects_nonexistent_user(self):
        dto = ForgotPasswordDTO(email_or_phone='nobody@example.com')
        with self.assertRaises(UserNotFoundError):
            self.service.forgot_password(dto)

    def test_forgot_password_publishes_event(self):
        create_active_user(email='event@example.com')

        dto = ForgotPasswordDTO(email_or_phone='event@example.com')
        self.service.forgot_password(dto)

        self.mock_sns.publish_event.assert_called_once()
        event = self.mock_sns.publish_event.call_args[0][0]
        self.assertEqual(event.event_type, 'PasswordResetRequested')


class ResetPasswordTest(TestCase):

    def setUp(self):
        self.mock_notification = MagicMock()
        self.mock_sns = MagicMock()
        self.service = PasswordService(
            notification_gateway=self.mock_notification,
            sns_publisher=self.mock_sns,
        )

    def test_reset_password_success(self):
        user = create_active_user(email='reset@example.com', password='OldPass123!')
        create_password_reset_token(user, code='123456')

        dto = ResetPasswordDTO(
            email_or_phone='reset@example.com',
            code='123456',
            new_password='NewPass456!',
            confirm_password='NewPass456!',
        )
        result = self.service.reset_password(dto)

        self.assertIn('message', result)
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewPass456!'))

    def test_reset_password_rejects_invalid_code(self):
        user = create_active_user(email='badcode@example.com')
        create_password_reset_token(user, code='123456')

        dto = ResetPasswordDTO(
            email_or_phone='badcode@example.com',
            code='000000',
            new_password='NewPass456!',
            confirm_password='NewPass456!',
        )
        with self.assertRaises(InvalidVerificationCodeError):
            self.service.reset_password(dto)

    def test_reset_password_rejects_expired_token(self):
        user = create_active_user(email='expiredtoken@example.com')
        create_password_reset_token(
            user,
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        dto = ResetPasswordDTO(
            email_or_phone='expiredtoken@example.com',
            code='123456',
            new_password='NewPass456!',
            confirm_password='NewPass456!',
        )
        with self.assertRaises(VerificationCodeExpiredError):
            self.service.reset_password(dto)

    def test_reset_password_rejects_password_mismatch(self):
        user = create_active_user(email='mismatch@example.com')
        create_password_reset_token(user, code='123456')

        dto = ResetPasswordDTO(
            email_or_phone='mismatch@example.com',
            code='123456',
            new_password='NewPass456!',
            confirm_password='DifferentPass789!',
        )
        with self.assertRaises(PasswordMismatchError):
            self.service.reset_password(dto)

    def test_reset_password_marks_token_used(self):
        user = create_active_user(email='usedtoken@example.com')
        token = create_password_reset_token(user, code='123456')

        dto = ResetPasswordDTO(
            email_or_phone='usedtoken@example.com',
            code='123456',
            new_password='NewPass456!',
            confirm_password='NewPass456!',
        )
        self.service.reset_password(dto)

        token.refresh_from_db()
        self.assertTrue(token.is_used)

    def test_reset_password_rejects_nonexistent_user(self):
        dto = ResetPasswordDTO(
            email_or_phone='nobody@example.com',
            code='123456',
            new_password='NewPass456!',
            confirm_password='NewPass456!',
        )
        with self.assertRaises(UserNotFoundError):
            self.service.reset_password(dto)
