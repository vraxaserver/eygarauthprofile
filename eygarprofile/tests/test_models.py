import os
import uuid
from django.test import TestCase, override_settings
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.auth import get_user_model

# Import all your models
from eygarprofile.models import (
    EygarHost,
    BusinessProfile,
    IdentityVerification,
    ContactDetails,
    ReviewSubmission,
    ProfileStatusHistory,
    license_upload_path,
    logo_upload_path,
)

# Get the custom User model
User = get_user_model()

# Define a temporary media root for testing file uploads
TEST_MEDIA_ROOT = os.path.join(settings.BASE_DIR, "test_media")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class EygarHostModelTests(TestCase):
    """Tests for the EygarHost model."""

    @classmethod
    def setUpTestData(cls):
        # Create users that will be available for all tests in this class
        cls.user = User.objects.create_user(email="host@example.com", password="password123")
        cls.reviewer_user = User.objects.create_user(email="reviewer@example.com", password="password123",
                                                     is_staff=True)

    def test_eygar_host_creation_defaults(self):
        """Test that an EygarHost is created with correct default values."""
        host = EygarHost.objects.create(user=self.user)
        self.assertEqual(host.user, self.user)
        self.assertEqual(host.status, 'draft')
        self.assertEqual(host.current_step, 'business_profile')
        self.assertFalse(host.business_profile_completed)
        self.assertFalse(host.identity_verification_completed)
        self.assertFalse(host.contact_details_completed)
        self.assertFalse(host.review_submission_completed)
        self.assertIsNone(host.submitted_at)
        self.assertIsNone(host.reviewed_at)
        self.assertIsNone(host.reviewer)
        self.assertEqual(host.review_notes, "")
        self.assertIsInstance(host.id, uuid.UUID)

    def test_one_to_one_relationship_with_user(self):
        """Test that a user can only have one EygarHost profile."""
        EygarHost.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            EygarHost.objects.create(user=self.user)

    def test_string_representation(self):
        """Test the __str__ method."""
        host = EygarHost.objects.create(user=self.user)
        self.assertEqual(str(host), f"Eygar Host - {self.user.email}")

    def test_completion_percentage_property(self):
        """Test the completion_percentage property at different stages."""
        host = EygarHost.objects.create(user=self.user)
        self.assertEqual(host.completion_percentage, 0.0)

        host.business_profile_completed = True
        host.save()
        self.assertEqual(host.completion_percentage, 25.0)

        host.identity_verification_completed = True
        host.save()
        self.assertEqual(host.completion_percentage, 50.0)

        host.contact_details_completed = True
        host.save()
        self.assertEqual(host.completion_percentage, 75.0)

        host.review_submission_completed = True
        host.save()
        self.assertEqual(host.completion_percentage, 100.0)

    def test_get_next_step_method(self):
        """Test the logic of the get_next_step method."""
        host = EygarHost.objects.create(user=self.user)
        self.assertEqual(host.get_next_step(), 'business_profile')

        host.business_profile_completed = True
        self.assertEqual(host.get_next_step(), 'identity_verification')

        host.identity_verification_completed = True
        self.assertEqual(host.get_next_step(), 'contact_details')

        host.contact_details_completed = True
        self.assertEqual(host.get_next_step(), 'review_submission')

        host.review_submission_completed = True
        self.assertEqual(host.get_next_step(), 'completed')

    def test_can_proceed_to_step_method(self):
        """Test the logic for step progression validation."""
        host = EygarHost.objects.create(user=self.user)  # current_step is 'business_profile'

        self.assertTrue(host.can_proceed_to_step('business_profile'))
        self.assertTrue(host.can_proceed_to_step('identity_verification'))
        self.assertFalse(host.can_proceed_to_step('contact_details'))  # Cannot skip step

        host.current_step = 'identity_verification'
        host.save()
        self.assertFalse(host.can_proceed_to_step('business_profile'))  # Cannot go back
        self.assertTrue(host.can_proceed_to_step('contact_details'))
        self.assertFalse(host.can_proceed_to_step('review_submission'))


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class RelatedProfileModelsTests(TestCase):
    """Tests for models related to EygarHost, including file uploads."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="host@example.com", password="password123")
        cls.host = EygarHost.objects.create(user=cls.user)

    def test_business_profile_creation(self):
        """Test creating a BusinessProfile with file uploads."""
        # Create dummy files for upload
        dummy_license = SimpleUploadedFile("dummy_license.pdf", b"file_content", content_type="application/pdf")
        dummy_logo = SimpleUploadedFile("dummy_logo.png", b"file_content", content_type="image/png")

        profile = BusinessProfile.objects.create(
            eygar_host=self.host,
            business_name="Test Biz",
            license_number="12345",
            license_document=dummy_license,
            business_logo=dummy_logo,
            business_address_line1="123 Test St"
        )
        self.assertEqual(profile.eygar_host, self.host)
        self.assertEqual(self.host.business_profile, profile)
        self.assertEqual(str(profile), "Business Profile - Test Biz")

        # Test upload paths
        expected_license_path = license_upload_path(profile, "dummy_license.pdf")
        expected_logo_path = logo_upload_path(profile, "dummy_logo.png")
        self.assertIn(str(self.host.id), profile.license_document.name)
        self.assertIn(str(self.host.id), profile.business_logo.name)
        self.assertEqual(profile.license_document.name, expected_license_path)
        self.assertEqual(profile.business_logo.name, expected_logo_path)

    def test_identity_verification_creation(self):
        """Test creating an IdentityVerification model."""
        dummy_img = SimpleUploadedFile("id_front.jpg", b"file_content", content_type="image/jpeg")
        verification = IdentityVerification.objects.create(
            eygar_host=self.host,
            document_type='passport',
            document_number='P123',
            document_image_front=dummy_img
        )
        self.assertEqual(verification.verification_status, 'pending')
        self.assertEqual(str(verification), f"Identity Verification - {self.user.email}")

    def test_contact_details_creation_and_validation(self):
        """Test creating ContactDetails and validating phone numbers."""
        # Test valid number
        contact = ContactDetails(
            eygar_host=self.host,
            address_line1="456 Main St",
            mobile_number='+12345678901'
        )
        contact.full_clean()  # This will not raise an error
        contact.save()
        self.assertEqual(contact.mobile_verified, 'pending')
        self.assertEqual(str(contact), f"Contact Details - {self.user.email}")

        # Test invalid number
        contact_invalid = ContactDetails(
            eygar_host=self.host,
            address_line1="789 Side St",
            mobile_number='invalid-number'
        )
        with self.assertRaises(ValidationError):
            contact_invalid.full_clean()  # This will raise ValidationError

    def test_review_submission_creation(self):
        """Test creating a ReviewSubmission."""
        submission = ReviewSubmission.objects.create(
            eygar_host=self.host,
            additional_notes="Ready for review.",
            terms_accepted=True,
            privacy_policy_accepted=True
        )
        self.assertTrue(submission.terms_accepted)
        self.assertEqual(str(submission), f"Review Submission - {self.user.email}")


class ProfileStatusHistoryTests(TestCase):
    """Tests for the ProfileStatusHistory model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="host@example.com", password="password123")
        cls.reviewer = User.objects.create_user(email="reviewer@example.com", password="password123", is_staff=True)
        cls.host = EygarHost.objects.create(user=cls.user)

    def test_history_creation(self):
        """Test that a history record is created correctly."""
        old_status = self.host.status
        self.host.status = 'submitted'
        self.host.save()

        history = ProfileStatusHistory.objects.create(
            eygar_host=self.host,
            old_status=old_status,
            new_status=self.host.status,
            changed_by=self.reviewer,
            change_reason="User submitted profile."
        )
        self.assertEqual(ProfileStatusHistory.objects.count(), 1)
        self.assertEqual(history.eygar_host, self.host)
        self.assertEqual(history.old_status, 'draft')
        self.assertEqual(history.new_status, 'submitted')
        self.assertEqual(history.changed_by, self.reviewer)
        self.assertEqual(str(history), "Status Change: draft -> submitted")

    def test_multiple_history_entries(self):
        """Test that multiple history entries can be linked to one host."""
        ProfileStatusHistory.objects.create(eygar_host=self.host, old_status='draft', new_status='submitted')
        ProfileStatusHistory.objects.create(eygar_host=self.host, old_status='submitted', new_status='approved')
        self.assertEqual(self.host.status_history.count(), 2)
        # Check that they are ordered by most recent first
        self.assertEqual(self.host.status_history.first().new_status, 'approved')