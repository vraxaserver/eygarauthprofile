# accounts/tests/test_me_endpoint.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.tests.factories import create_active_user

class MyViewTestCase(APITestCase):
    def setUp(self):
        self.user = create_active_user(email='testme@example.com', first_name='OldFirst', last_name='OldLast')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('accounts:me')

    def test_get_me(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'OldFirst')
        self.assertEqual(response.data['last_name'], 'OldLast')

    def test_update_name_success(self):
        data = {
            'first_name': 'NewFirst',
            'last_name': 'NewLast'
        }
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'NewFirst')
        self.assertEqual(response.data['last_name'], 'NewLast')

        # Verify database
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'NewFirst')
        self.assertEqual(self.user.last_name, 'NewLast')

    @patch('accounts.views.upload_fileobj_to_s3')
    def test_update_avatar_success(self, mock_upload):
        mock_upload.return_value = ('https://s3.example.com/avatars/new_avatar.png', 'key')
        
        avatar_file = SimpleUploadedFile("avatar.png", b"file_content", content_type="image/png")
        data = {
            'avatar': avatar_file
        }
        response = self.client.patch(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['avatar_url'], 'https://s3.example.com/avatars/new_avatar.png')

        # Verify database
        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar_url, 'https://s3.example.com/avatars/new_avatar.png')
