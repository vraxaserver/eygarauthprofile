# accounts/tests/test_guest_profile.py
"""
Unit tests for guest profile CRUD operations.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from accounts.application.dto import GuestProfileUpdateDTO
from accounts.application.services.guest_profile_service import GuestProfileService
from accounts.domain.exceptions import ProfileNotFoundError
from accounts.tests.factories import create_active_user, create_guest_profile


class GuestProfileServiceTest(TestCase):

    def setUp(self):
        self.mock_s3 = MagicMock()
        self.service = GuestProfileService(s3_storage=self.mock_s3)

    def test_get_profile_success(self):
        user = create_active_user(email='profile@example.com')
        create_guest_profile(user, first_name='Jane', last_name='Doe')

        result = self.service.get_profile(user)

        self.assertEqual(result['first_name'], 'Jane')
        self.assertEqual(result['last_name'], 'Doe')
        self.assertIn('id', result)
        self.assertIn('created_at', result)

    def test_get_profile_not_found(self):
        user = create_active_user(email='noprofile@example.com')

        with self.assertRaises(ProfileNotFoundError):
            self.service.get_profile(user)

    def test_update_profile_fields(self):
        user = create_active_user(email='update@example.com')
        create_guest_profile(user)

        dto = GuestProfileUpdateDTO(
            first_name='Updated',
            last_name='Name',
            bio='Hello world',
            nationality='US',
        )
        result = self.service.update_profile(user, dto)

        self.assertEqual(result['first_name'], 'Updated')
        self.assertEqual(result['last_name'], 'Name')
        self.assertEqual(result['bio'], 'Hello world')
        self.assertEqual(result['nationality'], 'US')

    def test_update_profile_partial(self):
        user = create_active_user(email='partial@example.com')
        create_guest_profile(user, first_name='Original', last_name='Name')

        dto = GuestProfileUpdateDTO(bio='Only updating bio')
        result = self.service.update_profile(user, dto)

        self.assertEqual(result['first_name'], 'Original')
        self.assertEqual(result['bio'], 'Only updating bio')

    def test_update_profile_with_avatar(self):
        user = create_active_user(email='avatar@example.com')
        create_guest_profile(user)

        self.mock_s3.upload_avatar.return_value = 'https://s3.example.com/avatar.jpg'

        mock_file = MagicMock()
        dto = GuestProfileUpdateDTO()
        result = self.service.update_profile(user, dto, avatar_file=mock_file)

        self.mock_s3.upload_avatar.assert_called_once()
        self.assertEqual(result['avatar_url'], 'https://s3.example.com/avatar.jpg')

    def test_update_profile_not_found(self):
        user = create_active_user(email='noprofileupdate@example.com')

        dto = GuestProfileUpdateDTO(first_name='Test')
        with self.assertRaises(ProfileNotFoundError):
            self.service.update_profile(user, dto)

    def test_update_date_of_birth(self):
        from datetime import date
        user = create_active_user(email='dob@example.com')
        create_guest_profile(user)

        dto = GuestProfileUpdateDTO(date_of_birth=date(1990, 5, 15))
        result = self.service.update_profile(user, dto)

        self.assertEqual(result['date_of_birth'], '1990-05-15')
