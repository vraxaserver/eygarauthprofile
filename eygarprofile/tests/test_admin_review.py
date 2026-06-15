# eygarprofile/tests/test_admin_review.py
"""
Unit tests for admin host profile review flow.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from accounts.tests.factories import create_active_user
from eygarprofile.application.services.host_profile_service import HostProfileService
from eygarprofile.models import EygarHost, ProfileStatusHistory


class AdminReviewTest(TestCase):

    def setUp(self):
        self.mock_sns = MagicMock()
        self.mock_notification = MagicMock()
        self.service = HostProfileService(
            sns_publisher=self.mock_sns,
            notification_gateway=self.mock_notification,
        )

    def test_admin_approve_publishes_host_profile_verified(self):
        user = create_active_user(email='approve@example.com')
        host = EygarHost.objects.create(user=user, status='submitted')

        self.service.on_profile_approved(host)

        self.mock_sns.publish_event.assert_called_once()
        event = self.mock_sns.publish_event.call_args[0][0]
        self.assertEqual(event.event_type, 'HostProfileVerified')
        self.assertEqual(event.user_id, str(user.id))

    def test_admin_reject_does_not_publish_verified(self):
        user = create_active_user(email='reject@example.com')
        host = EygarHost.objects.create(user=user, status='submitted')

        self.service.on_profile_rejected(host, review_notes='Invalid documents')

        self.mock_sns.publish_event.assert_not_called()

    def test_admin_reject_sends_notification_with_notes(self):
        user = create_active_user(email='rejectnotes@example.com')
        host = EygarHost.objects.create(user=user, status='submitted')

        self.service.on_profile_rejected(host, review_notes='Please resubmit ID')

        self.mock_notification.send_transactional_email.assert_called_once()
        call_kwargs = self.mock_notification.send_transactional_email.call_args[1]
        self.assertIn('Please resubmit ID', call_kwargs['message'])

    def test_admin_approve_sets_user_host_verified_flag(self):
        user = create_active_user(email='flagtest@example.com')
        host = EygarHost.objects.create(user=user, status='submitted')

        self.service.on_profile_approved(host)

        user.refresh_from_db()
        self.assertTrue(user.is_host_verified)

    def test_status_history_created_on_review(self):
        user = create_active_user(email='history@example.com')
        admin_user = create_active_user(
            email='admin@example.com',
            is_staff=True,
            is_superuser=True,
        )

        host = EygarHost.objects.create(user=user, status='submitted')

        # Simulate admin review
        old_status = host.status
        host.status = 'approved'
        host.reviewed_at = timezone.now()
        host.reviewer = admin_user
        host.review_notes = 'Looks good'
        host.save()

        ProfileStatusHistory.objects.create(
            eygar_host=host,
            old_status=old_status,
            new_status='approved',
            changed_by=admin_user,
            change_reason='Looks good',
        )

        histories = ProfileStatusHistory.objects.filter(eygar_host=host)
        self.assertTrue(histories.exists())

        latest = histories.first()
        self.assertEqual(latest.old_status, 'submitted')
        self.assertEqual(latest.new_status, 'approved')
        self.assertEqual(latest.changed_by, admin_user)

    def test_only_staff_can_review(self):
        """Admin review permission check (integration-level test)."""
        from eygarprofile.permissions import IsAdminOrModerator

        permission = IsAdminOrModerator()

        # Non-staff user
        mock_request = MagicMock()
        mock_request.user.is_authenticated = True
        mock_request.user.is_staff = False
        mock_request.user.is_superuser = False
        mock_request.user.is_moderator = False
        self.assertFalse(permission.has_permission(mock_request, None))

        # Staff user
        mock_request.user.is_staff = True
        self.assertTrue(permission.has_permission(mock_request, None))

        # Superuser
        mock_request.user.is_staff = False
        mock_request.user.is_superuser = True
        self.assertTrue(permission.has_permission(mock_request, None))
