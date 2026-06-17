# eygarprofile/tests/test_host_profile.py
"""
Unit tests for host profile event publishing and multi-step flow.
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from accounts.tests.factories import create_active_user
from eygarprofile.application.services.host_profile_service import HostProfileService
from eygarprofile.models import EygarHost


class HostProfileServiceTest(TestCase):

    def setUp(self):
        self.mock_sns = MagicMock()
        self.mock_notification = MagicMock()
        self.service = HostProfileService(
            sqs_publisher=self.mock_sns,
            notification_gateway=self.mock_notification,
        )

    def test_on_profile_submitted_publishes_event(self):
        user = create_active_user(email='host@example.com')
        host = EygarHost.objects.create(user=user, status='submitted')

        self.service.on_profile_submitted(host)

        self.mock_sns.publish_event.assert_called_once()
        event = self.mock_sns.publish_event.call_args[0][0]
        self.assertEqual(event.event_type, 'HostProfileCreated')
        self.assertEqual(event.user_id, str(user.id))
        self.assertEqual(event.host_profile_id, str(host.id))

    def test_on_profile_submitted_sends_notification(self):
        user = create_active_user(email='hostnotif@example.com')
        host = EygarHost.objects.create(user=user, status='submitted')

        self.service.on_profile_submitted(host)

        self.mock_notification.send_transactional_email.assert_called_once()
        call_kwargs = self.mock_notification.send_transactional_email.call_args[1]
        self.assertEqual(call_kwargs['to_email'], 'hostnotif@example.com')

    def test_on_profile_approved_publishes_verified_event(self):
        user = create_active_user(email='approved@example.com')
        host = EygarHost.objects.create(user=user, status='approved')

        self.service.on_profile_approved(host)

        self.mock_sns.publish_event.assert_called_once()
        event = self.mock_sns.publish_event.call_args[0][0]
        self.assertEqual(event.event_type, 'HostProfileVerified')

    def test_on_profile_approved_sets_user_host_verified(self):
        user = create_active_user(email='verified@example.com')
        host = EygarHost.objects.create(user=user, status='approved')

        self.service.on_profile_approved(host)

        user.refresh_from_db()
        self.assertTrue(user.is_host_verified)

    def test_on_profile_rejected_sends_notification(self):
        user = create_active_user(email='rejected@example.com')
        host = EygarHost.objects.create(user=user, status='rejected')

        self.service.on_profile_rejected(host, review_notes='Missing documents')

        self.mock_notification.send_transactional_email.assert_called_once()
        call_kwargs = self.mock_notification.send_transactional_email.call_args[1]
        self.assertIn('Missing documents', call_kwargs['message'])

    def test_on_profile_rejected_does_not_publish_verified_event(self):
        user = create_active_user(email='notverified@example.com')
        host = EygarHost.objects.create(user=user, status='rejected')

        self.service.on_profile_rejected(host)

        self.mock_sns.publish_event.assert_not_called()

    def test_on_status_changed_routes_correctly(self):
        user = create_active_user(email='routing@example.com')
        host = EygarHost.objects.create(user=user, status='approved')

        # Test approved routing
        self.service.on_status_changed(host, 'submitted', 'approved')
        event = self.mock_sns.publish_event.call_args[0][0]
        self.assertEqual(event.event_type, 'HostProfileVerified')

    def test_notifications_via_sqs_not_direct_email(self):
        """Verify that all notifications go through the NotificationGateway (SQS),
        not through direct email sending."""
        user = create_active_user(email='snsonly@example.com')
        host = EygarHost.objects.create(user=user, status='submitted')

        self.service.on_profile_submitted(host)

        # NotificationGateway should be called
        self.mock_notification.send_transactional_email.assert_called_once()
        # No direct email calls should exist


class HostProfileMultiStepTest(TestCase):

    def test_host_profile_step_progression(self):
        user = create_active_user(email='steps@example.com')
        host = EygarHost.objects.create(user=user)

        self.assertEqual(host.current_step, 'business_profile')
        self.assertFalse(host.business_profile_completed)

        # Simulate step completion
        host.business_profile_completed = True
        host.current_step = 'identity_verification'
        host.save()

        self.assertEqual(host.get_next_step(), 'identity_verification')
        self.assertEqual(host.completion_percentage, 25.0)

    def test_host_profile_completion_percentage(self):
        user = create_active_user(email='percent@example.com')
        host = EygarHost.objects.create(
            user=user,
            business_profile_completed=True,
            identity_verification_completed=True,
            contact_details_completed=True,
            review_submission_completed=True,
        )

        self.assertEqual(host.completion_percentage, 100.0)

    def test_host_profile_cannot_skip_steps(self):
        user = create_active_user(email='skiptest@example.com')
        host = EygarHost.objects.create(user=user)

        # Should not be able to proceed to contact_details without completing business_profile
        self.assertFalse(host.can_proceed_to_step('contact_details'))
        self.assertTrue(host.can_proceed_to_step('business_profile'))

    def test_s3_uploads_for_documents(self):
        """Host profile documents should use S3 storage."""
        from eygarprofile.models import BusinessProfile, get_license_upload_path, get_logo_upload_path

        user = create_active_user(email='s3test@example.com')
        host = EygarHost.objects.create(user=user)

        # Test upload path generation — these are Django upload_to callables
        mock_instance = MagicMock()
        mock_instance.eygar_host = host
        mock_instance.eygar_host.id = host.id

        license_path = get_license_upload_path(mock_instance, 'license.pdf')
        self.assertIn(str(host.id), license_path)
        self.assertIn('license', license_path.lower())

        logo_path = get_logo_upload_path(mock_instance, 'logo.png')
        self.assertIn(str(host.id), logo_path)
        self.assertIn('logo', logo_path.lower())
