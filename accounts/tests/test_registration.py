# accounts/tests/test_registration.py
"""
Unit tests for user registration flow.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from accounts.application.dto import RegisterDTO
from accounts.application.services.registration_service import RegistrationService, detect_identifier_type
from accounts.domain.exceptions import (
    InvalidInputError,
    PasswordMismatchError,
    UserAlreadyExistsError,
)
from accounts.models import VerificationCode
from accounts.tests.factories import create_user


class DetectIdentifierTypeTest(TestCase):

    def test_detects_email(self):
        self.assertEqual(detect_identifier_type('user@example.com'), 'email')

    def test_detects_phone(self):
        self.assertEqual(detect_identifier_type('+1234567890'), 'phone')
        self.assertEqual(detect_identifier_type('1234567890123'), 'phone')

    def test_rejects_invalid_input(self):
        with self.assertRaises(InvalidInputError):
            detect_identifier_type('not-email-or-phone')

    def test_rejects_empty_string(self):
        with self.assertRaises(InvalidInputError):
            detect_identifier_type('')


class RegistrationServiceTest(TestCase):

    def setUp(self):
        self.mock_notification = MagicMock()
        self.mock_sns = MagicMock()
        self.service = RegistrationService(
            notification_gateway=self.mock_notification,
            sqs_publisher=self.mock_sns,
        )

    def test_register_with_valid_email(self):
        dto = RegisterDTO(
            email_or_phone='newuser@example.com',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        result = self.service.register(dto)

        self.assertIn('user_id', result)
        self.assertEqual(result['identifier_type'], 'email')
        self.mock_notification.send_verification_code.assert_called_once()
        self.mock_sns.publish_event.assert_called_once()

    def test_register_with_valid_phone(self):
        dto = RegisterDTO(
            email_or_phone='+1234567890',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        result = self.service.register(dto)

        self.assertIn('user_id', result)
        self.assertEqual(result['identifier_type'], 'phone')
        self.mock_notification.send_verification_code.assert_called_once()

    def test_register_creates_inactive_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        dto = RegisterDTO(
            email_or_phone='inactive@example.com',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        self.service.register(dto)

        user = User.objects.get(email='inactive@example.com')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)

    def test_register_creates_verification_code(self):
        dto = RegisterDTO(
            email_or_phone='codegen@example.com',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        self.service.register(dto)

        codes = VerificationCode.objects.filter(user__email='codegen@example.com')
        self.assertEqual(codes.count(), 1)
        self.assertEqual(len(codes.first().code), 6)
        self.assertTrue(codes.first().code.isdigit())

    def test_register_rejects_password_mismatch(self):
        dto = RegisterDTO(
            email_or_phone='mismatch@example.com',
            password='StrongPass123!',
            confirm_password='DifferentPass456!',
        )
        with self.assertRaises(PasswordMismatchError):
            self.service.register(dto)

    def test_register_rejects_duplicate_email(self):
        create_user(email='dup@example.com')

        dto = RegisterDTO(
            email_or_phone='dup@example.com',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        with self.assertRaises(UserAlreadyExistsError):
            self.service.register(dto)

    def test_register_rejects_duplicate_phone(self):
        create_user(email=None, phone_number='+9876543210')

        dto = RegisterDTO(
            email_or_phone='+9876543210',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        with self.assertRaises(UserAlreadyExistsError):
            self.service.register(dto)

    def test_register_rejects_invalid_identifier(self):
        dto = RegisterDTO(
            email_or_phone='not-valid',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        with self.assertRaises(InvalidInputError):
            self.service.register(dto)

    def test_register_publishes_user_registered_event(self):
        dto = RegisterDTO(
            email_or_phone='event@example.com',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        self.service.register(dto)

        call_args = self.mock_sns.publish_event.call_args
        event = call_args[0][0]
        self.assertEqual(event.event_type, 'UserRegistration')
        self.assertEqual(event.email, 'event@example.com')

    def test_register_sends_verification_code_notification(self):
        dto = RegisterDTO(
            email_or_phone='notif@example.com',
            password='StrongPass123!',
            confirm_password='StrongPass123!',
        )
        self.service.register(dto)

        self.mock_notification.send_verification_code.assert_called_once()
        call_kwargs = self.mock_notification.send_verification_code.call_args[1]
        self.assertEqual(call_kwargs['channel'], 'email')
        self.assertEqual(call_kwargs['recipient'], 'notif@example.com')
        self.assertEqual(call_kwargs['purpose'], 'registration')
        self.assertEqual(len(call_kwargs['code']), 6)
        # New enriched fields
        self.assertIn('user_id', call_kwargs)
        self.assertIn('user_name', call_kwargs)
