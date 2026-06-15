# accounts/tests/test_login.py
"""
Unit tests for authentication (login) flow.
"""
from django.test import TestCase
from unittest.mock import MagicMock

from accounts.application.dto import LoginDTO
from accounts.application.services.auth_service import AuthService
from accounts.domain.exceptions import InvalidCredentialsError, UserNotActiveError
from accounts.tests.factories import create_user, create_active_user


class AuthServiceTest(TestCase):

    def setUp(self):
        self.service = AuthService()

    def test_login_with_email_success(self):
        create_active_user(email='login@example.com', password='TestPass123!')

        dto = LoginDTO(email_or_phone='login@example.com', password='TestPass123!')
        result = self.service.login(dto)

        self.assertIn('tokens', result)
        self.assertIn('access', result['tokens'])
        self.assertIn('refresh', result['tokens'])
        self.assertEqual(result['user']['email'], 'login@example.com')

    def test_login_with_phone_success(self):
        create_active_user(
            email=None,
            phone_number='+1234567890',
            password='TestPass123!',
            is_phone_verified=True,
        )

        dto = LoginDTO(email_or_phone='+1234567890', password='TestPass123!')
        result = self.service.login(dto)

        self.assertIn('tokens', result)
        self.assertEqual(result['user']['phone_number'], '+1234567890')

    def test_login_rejects_inactive_user(self):
        create_user(email='inactive@example.com', password='TestPass123!', is_active=False)

        dto = LoginDTO(email_or_phone='inactive@example.com', password='TestPass123!')
        with self.assertRaises(UserNotActiveError):
            self.service.login(dto)

    def test_login_rejects_wrong_password(self):
        create_active_user(email='wrongpw@example.com', password='TestPass123!')

        dto = LoginDTO(email_or_phone='wrongpw@example.com', password='WrongPassword!')
        with self.assertRaises(InvalidCredentialsError):
            self.service.login(dto)

    def test_login_rejects_nonexistent_user(self):
        dto = LoginDTO(email_or_phone='nobody@example.com', password='TestPass123!')
        with self.assertRaises(InvalidCredentialsError):
            self.service.login(dto)

    def test_login_returns_user_data(self):
        user = create_active_user(
            email='data@example.com',
            password='TestPass123!',
            first_name='John',
            last_name='Doe',
        )

        dto = LoginDTO(email_or_phone='data@example.com', password='TestPass123!')
        result = self.service.login(dto)

        self.assertEqual(result['user']['first_name'], 'John')
        self.assertEqual(result['user']['last_name'], 'Doe')
        self.assertTrue(result['user']['is_email_verified'])
