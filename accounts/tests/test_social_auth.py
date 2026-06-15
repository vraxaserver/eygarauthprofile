# accounts/tests/test_social_auth.py
"""
Unit tests for social authentication (Google, Facebook).
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from accounts.application.dto import SocialAuthDTO
from accounts.application.services.social_auth_service import SocialAuthService
from accounts.domain.exceptions import SocialAuthError
from accounts.models import GuestProfile, SocialAccount
from accounts.tests.factories import create_active_user


MOCK_GOOGLE_PROFILE = {
    'sub': 'google-uid-123',
    'email': 'google@example.com',
    'given_name': 'Google',
    'family_name': 'User',
    'picture': 'https://lh3.google.com/avatar.jpg',
    'email_verified': True,
}

MOCK_FACEBOOK_PROFILE = {
    'id': 'fb-uid-456',
    'email': 'facebook@example.com',
    'first_name': 'Facebook',
    'last_name': 'User',
    'picture': {'data': {'url': 'https://graph.facebook.com/pic.jpg'}},
}


class SocialAuthServiceTest(TestCase):

    def setUp(self):
        self.mock_sns = MagicMock()
        self.service = SocialAuthService(sns_publisher=self.mock_sns)

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_google_login_creates_new_user(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_PROFILE
        mock_get.return_value = mock_resp

        dto = SocialAuthDTO(provider='google', access_token='valid-google-token')
        result = self.service.authenticate(dto)

        self.assertIn('tokens', result)
        self.assertTrue(result['is_new_user'])
        self.assertEqual(result['user']['email'], 'google@example.com')

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_google_login_existing_user_by_email(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_PROFILE
        mock_get.return_value = mock_resp

        # Pre-create user with same email
        create_active_user(email='google@example.com')

        dto = SocialAuthDTO(provider='google', access_token='valid-google-token')
        result = self.service.authenticate(dto)

        self.assertFalse(result['is_new_user'])

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_facebook_login_creates_new_user(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_FACEBOOK_PROFILE
        mock_get.return_value = mock_resp

        dto = SocialAuthDTO(provider='facebook', access_token='valid-fb-token')
        result = self.service.authenticate(dto)

        self.assertTrue(result['is_new_user'])
        self.assertEqual(result['user']['email'], 'facebook@example.com')

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_social_login_creates_guest_profile(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_PROFILE
        mock_get.return_value = mock_resp

        dto = SocialAuthDTO(provider='google', access_token='valid-token')
        result = self.service.authenticate(dto)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(email='google@example.com')
        self.assertTrue(GuestProfile.objects.filter(user=user).exists())

        profile = GuestProfile.objects.get(user=user)
        self.assertEqual(profile.first_name, 'Google')
        self.assertEqual(profile.last_name, 'User')

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_social_login_marks_email_verified(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_PROFILE
        mock_get.return_value = mock_resp

        dto = SocialAuthDTO(provider='google', access_token='valid-token')
        self.service.authenticate(dto)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(email='google@example.com')
        self.assertTrue(user.is_email_verified)
        self.assertTrue(user.is_active)

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_social_login_publishes_events_for_new_user(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_PROFILE
        mock_get.return_value = mock_resp

        dto = SocialAuthDTO(provider='google', access_token='valid-token')
        self.service.authenticate(dto)

        events = [call[0][0] for call in self.mock_sns.publish_event.call_args_list]
        event_types = [e.event_type for e in events]
        self.assertIn('UserRegistered', event_types)
        self.assertIn('GuestProfileCreated', event_types)

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_social_login_creates_social_account(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_PROFILE
        mock_get.return_value = mock_resp

        dto = SocialAuthDTO(provider='google', access_token='valid-token')
        self.service.authenticate(dto)

        self.assertTrue(
            SocialAccount.objects.filter(provider='google', provider_user_id='google-uid-123').exists()
        )

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_social_login_rejects_invalid_token(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        dto = SocialAuthDTO(provider='google', access_token='invalid-token')
        with self.assertRaises(SocialAuthError):
            self.service.authenticate(dto)

    def test_social_login_rejects_unsupported_provider(self):
        dto = SocialAuthDTO(provider='twitter', access_token='some-token')
        with self.assertRaises(SocialAuthError):
            self.service.authenticate(dto)

    @patch('accounts.application.services.social_auth_service.requests.get')
    def test_social_login_existing_social_account(self, mock_get):
        """Second login via same social account should reuse existing user."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_GOOGLE_PROFILE
        mock_get.return_value = mock_resp

        # First login
        dto = SocialAuthDTO(provider='google', access_token='valid-token')
        result1 = self.service.authenticate(dto)

        # Second login
        result2 = self.service.authenticate(dto)

        self.assertEqual(result1['user']['id'], result2['user']['id'])
        self.assertFalse(result2['is_new_user'])
