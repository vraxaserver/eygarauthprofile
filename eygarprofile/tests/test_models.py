import pdb
import os
import tempfile
from decimal import Decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.utils import timezone
from unittest.mock import patch, MagicMock

from eygarprofile.models import (
    EygarHost, BusinessProfile, IdentityVerification,
    ContactDetails, ReviewSubmission, ProfileStatusHistory
)

User = get_user_model()


class EygarHostModelTest(TestCase):
    """Test cases for EygarHost model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )

    def test_eygar_host_creation(self):
        """Test EygarHost model creation"""
        profile = EygarHost.objects.create(user=self.user)
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.status, 'draft')
        self.assertEqual(profile.current_step, 'business_profile')
        self.assertFalse(profile.business_profile_completed)
        self.assertFalse(profile.identity_verification_completed)
        self.assertFalse(profile.contact_details_completed)
        self.assertFalse(profile.review_submission_completed)
        self.assertIsNotNone(profile.id)
        self.assertIsNotNone(profile.created_at)

    def test_one_to_one_relationship_constraint(self):
        """Test that user can have only one eygar host"""
        EygarHost.objects.create(user=self.user)
        
        with self.assertRaises(IntegrityError):
            EygarHost.objects.create(user=self.user)

    def test_completion_percentage_calculation(self):
        """Test completion percentage property"""
        profile = EygarHost.objects.create(user=self.user)
        
        # Initially 0%
        self.assertEqual(profile.completion_percentage, 0.0)
        
        # After completing first step - 25%
        profile.business_profile_completed = True
        self.assertEqual(profile.completion_percentage, 25.0)
        
        # After completing two steps - 50%
        profile.identity_verification_completed = True
        self.assertEqual(profile.completion_percentage, 50.0)
        
        # After completing all steps - 100%
        profile.contact_details_completed = True
        profile.review_submission_completed = True
        self.assertEqual(profile.completion_percentage, 100.0)

    def test_get_next_step_logic(self):
        """Test get_next_step method logic"""
        profile = EygarHost.objects.create(user=self.user)
        
        # Initially should return business_profile
        self.assertEqual(profile.get_next_step(), 'business_profile')
        
        # After completing business profile
        profile.business_profile_completed = True
        self.assertEqual(profile.get_next_step(), 'identity_verification')
        
        # After completing identity verification
        profile.identity_verification_completed = True
        self.assertEqual(profile.get_next_step(), 'contact_details')
        
        # After completing contact details
        profile.contact_details_completed = True
        self.assertEqual(profile.get_next_step(), 'review_submission')
        
        # After completing all steps
        profile.review_submission_completed = True
        self.assertIsNone(profile.get_next_step())

    def test_can_proceed_to_step_validation(self):
        """Test step progression validation"""
        profile = EygarHost.objects.create(user=self.user)
        
        # Can access first step
        self.assertTrue(profile.can_proceed_to_step('business_profile'))
        
        # Cannot skip steps
        self.assertFalse(profile.can_proceed_to_step('contact_details'))
        
        # After completing business profile, can access next step
        profile.business_profile_completed = True
        profile.current_step = 'identity_verification'
        self.assertTrue(profile.can_proceed_to_step('identity_verification'))
        self.assertFalse(profile.can_proceed_to_step('review_submission'))

    def test_string_representation(self):
        """Test model string representation"""
        profile = EygarHost.objects.create(user=self.user)
        expected_str = f"Eygar Host - {self.user.username}"
        self.assertEqual(str(profile), expected_str)

    def test_model_ordering(self):
        """Test model ordering by created_at descending"""
        user2 = User.objects.create_user(username='user2', email='user2@test.com')
        
        profile1 = EygarHost.objects.create(user=self.user)
        profile2 = EygarHost.objects.create(user=user2)
        
        profiles = EygarHost.objects.all()
        self.assertEqual(profiles[0], profile2)  # Most recent first
        self.assertEqual(profiles[1], profile1)


class BusinessProfileModelTest(TestCase):
    """Test cases for BusinessProfile model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.eygar_host = EygarHost.objects.create(user=self.user)

    def test_business_profile_creation(self):
        """Test BusinessProfile model creation"""
        # Create a test file
        test_file = SimpleUploadedFile(
            "license.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        business_profile = BusinessProfile.objects.create(
            eygar_host=self.eygar_host,
            business_name="Test Business LLC",
            business_type="Hotel",
            license_number="LIC123456",
            license_document=test_file,
            business_address_line1="123 Test St",
            business_city="Test City",
            business_state="Test State",
            business_postal_code="12345",
            business_country="Test Country"
        )
        
        self.assertEqual(business_profile.eygar_host, self.eygar_host)
        self.assertEqual(business_profile.business_name, "Test Business LLC")
        self.assertEqual(business_profile.license_number, "LIC123456")
        self.assertIsNotNone(business_profile.created_at)

    def test_one_to_one_relationship_with_eygar_host(self):
        """Test one-to-one relationship constraint"""
        BusinessProfile.objects.create(
            eygar_host=self.eygar_host,
            business_name="Test Business",
            license_number="LIC123"
        )
        
        with self.assertRaises(IntegrityError):
            BusinessProfile.objects.create(
                eygar_host=self.eygar_host,
                business_name="Another Business",
                license_number="LIC456"
            )

    def test_string_representation(self):
        """Test BusinessProfile string representation"""
        business_profile = BusinessProfile.objects.create(
            eygar_host=self.eygar_host,
            business_name="Test Business LLC",
            license_number="LIC123"
        )
        
        expected_str = "Business Profile - Test Business LLC"
        self.assertEqual(str(business_profile), expected_str)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_file_upload_paths(self):
        """Test file upload path generation"""
        test_license = SimpleUploadedFile(
            "license.pdf",
            b"license content",
            content_type="application/pdf"
        )
        test_logo = SimpleUploadedFile(
            "logo.png",
            b"logo content",
            content_type="image/png"
        )
        
        business_profile = BusinessProfile.objects.create(
            eygar_host=self.eygar_host,
            business_name="Test Business",
            license_number="LIC123",
            license_document=test_license,
            business_logo=test_logo
        )
        
        # Check that files are uploaded to correct paths
        self.assertIn('licenses/', business_profile.license_document.name)
        self.assertIn('business_logos/', business_profile.business_logo.name)


class IdentityVerificationModelTest(TestCase):
    """Test cases for IdentityVerification model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.eygar_host = EygarHost.objects.create(user=self.user)

    def test_identity_verification_creation(self):
        """Test IdentityVerification model creation"""
        front_image = SimpleUploadedFile(
            "id_front.jpg",
            b"image_content",
            content_type="image/jpeg"
        )
        
        identity_verification = IdentityVerification.objects.create(
            eygar_host=self.eygar_host,
            document_type='national_id',
            document_number='ID123456789',
            document_image_front=front_image
        )
        
        self.assertEqual(identity_verification.eygar_host, self.eygar_host)
        self.assertEqual(identity_verification.document_type, 'national_id')
        self.assertEqual(identity_verification.verification_status, 'pending')
        self.assertEqual(identity_verification.document_number, 'ID123456789')

    def test_verification_status_choices(self):
        """Test verification status choices"""
        identity_verification = IdentityVerification.objects.create(
            eygar_host=self.eygar_host,
            document_type='passport',
            document_number='P123456'
        )
        
        # Test valid status values
        valid_statuses = ['pending', 'verified', 'rejected']
        for status in valid_statuses:
            identity_verification.verification_status = status
            identity_verification.save()
            self.assertEqual(identity_verification.verification_status, status)

    def test_document_type_choices(self):
        """Test document type choices"""
        valid_types = ['national_id', 'passport']
        
        for doc_type in valid_types:
            identity_verification = IdentityVerification.objects.create(
                eygar_host=self.eygar_host,
                document_type=doc_type,
                document_number=f'DOC{doc_type}'
            )
            self.assertEqual(identity_verification.document_type, doc_type)

    def test_string_representation(self):
        """Test IdentityVerification string representation"""
        identity_verification = IdentityVerification.objects.create(
            eygar_host=self.eygar_host,
            document_type='national_id',
            document_number='ID123456'
        )
        
        expected_str = f"Identity Verification - {self.user.username}"
        self.assertEqual(str(identity_verification), expected_str)


class ContactDetailsModelTest(TestCase):
    """Test cases for ContactDetails model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.eygar_host = EygarHost.objects.create(user=self.user)

    def test_contact_details_creation(self):
        """Test ContactDetails model creation"""
        contact_details = ContactDetails.objects.create(
            eygar_host=self.eygar_host,
            address_line1="123 Main St",
            city="Test City",
            state="Test State",
            postal_code="12345",
            country="Test Country",
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            mobile_number="+1234567890"
        )
        
        self.assertEqual(contact_details.eygar_host, self.eygar_host)
        self.assertEqual(contact_details.city, "Test City")
        self.assertEqual(contact_details.latitude, Decimal('40.7128'))
        self.assertEqual(contact_details.mobile_verified, 'pending')

    def test_phone_number_validation(self):
        """Test phone number field validation"""
        contact_details = ContactDetails(
            eygar_host=self.eygar_host,
            address_line1="123 Main St",
            city="Test City",
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            mobile_number="invalid_phone"
        )
        
        with self.assertRaises(ValidationError):
            contact_details.full_clean()

    def test_verification_status_defaults(self):
        """Test that all verification statuses default to pending"""
        contact_details = ContactDetails.objects.create(
            eygar_host=self.eygar_host,
            address_line1="123 Main St",
            city="Test City",
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            mobile_number="+1234567890"
        )
        
        self.assertEqual(contact_details.mobile_verified, 'pending')
        self.assertEqual(contact_details.whatsapp_verified, 'pending')
        self.assertEqual(contact_details.telegram_verified, 'pending')
        self.assertEqual(contact_details.facebook_verified, 'pending')
        self.assertEqual(contact_details.email_verified, 'pending')

    def test_coordinates_precision(self):
        """Test coordinate field precision"""
        contact_details = ContactDetails.objects.create(
            eygar_host=self.eygar_host,
            address_line1="123 Main St",
            city="Test City",
            latitude=Decimal('40.712800'),  # 6 decimal places
            longitude=Decimal('-74.006000'),
            mobile_number="+1234567890"
        )
        
        self.assertEqual(contact_details.latitude, Decimal('40.712800'))
        self.assertEqual(contact_details.longitude, Decimal('-74.006000'))


class ReviewSubmissionModelTest(TestCase):
    """Test cases for ReviewSubmission model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.eygar_host = EygarHost.objects.create(user=self.user)

    def test_review_submission_creation(self):
        """Test ReviewSubmission model creation"""
        review_submission = ReviewSubmission.objects.create(
            eygar_host=self.eygar_host,
            additional_notes="Please review my application",
            terms_accepted=True,
            privacy_policy_accepted=True
        )
        
        self.assertEqual(review_submission.eygar_host, self.eygar_host)
        self.assertTrue(review_submission.terms_accepted)
        self.assertTrue(review_submission.privacy_policy_accepted)
        self.assertIsNotNone(review_submission.submitted_at)

    def test_terms_and_privacy_defaults(self):
        """Test default values for terms and privacy policy"""
        review_submission = ReviewSubmission.objects.create(
            eygar_host=self.eygar_host
        )
        
        self.assertFalse(review_submission.terms_accepted)
        self.assertFalse(review_submission.privacy_policy_accepted)

    def test_string_representation(self):
        """Test ReviewSubmission string representation"""
        review_submission = ReviewSubmission.objects.create(
            eygar_host=self.eygar_host,
            terms_accepted=True,
            privacy_policy_accepted=True
        )
        
        expected_str = f"Review Submission - {self.user.username}"
        self.assertEqual(str(review_submission), expected_str)


class ProfileStatusHistoryModelTest(TestCase):
    """Test cases for ProfileStatusHistory model"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            is_staff=True
        )
        self.eygar_host = EygarHost.objects.create(user=self.user)

    def test_status_history_creation(self):
        """Test ProfileStatusHistory model creation"""
        history = ProfileStatusHistory.objects.create(
            eygar_host=self.eygar_host,
            old_status='draft',
            new_status='submitted',
            changed_by=self.admin_user,
            change_reason='Profile submitted for review'
        )
        
        self.assertEqual(history.eygar_host, self.eygar_host)
        self.assertEqual(history.old_status, 'draft')
        self.assertEqual(history.new_status, 'submitted')
        self.assertEqual(history.changed_by, self.admin_user)
        self.assertIsNotNone(history.created_at)

    def test_status_history_ordering(self):
        """Test status history ordering by created_at descending"""
        history1 = ProfileStatusHistory.objects.create(
            eygar_host=self.eygar_host,
            old_status='draft',
            new_status='submitted'
        )
        history2 = ProfileStatusHistory.objects.create(
            eygar_host=self.eygar_host,
            old_status='submitted',
            new_status='approved'
        )
        
        histories = ProfileStatusHistory.objects.all()
        self.assertEqual(histories[0], history1)  # Most recent first
        self.assertEqual(histories[1], history2)

    def test_string_representation(self):
        """Test ProfileStatusHistory string representation"""
        history = ProfileStatusHistory.objects.create(
            eygar_host=self.eygar_host,
            old_status='draft',
            new_status='submitted'
        )
        
        expected_str = "Status Change: draft -> submitted"
        self.assertEqual(str(history), expected_str)

    def test_nullable_changed_by_field(self):
        """Test that changed_by field can be null"""
        history = ProfileStatusHistory.objects.create(
            eygar_host=self.eygar_host,
            old_status='draft',
            new_status='submitted',
            changed_by=None  # System change, no user
        )
        
        self.assertIsNone(history.changed_by)

    def test_cascade_delete_with_eygar_host(self):
        """Test cascade delete when host profile is deleted"""
        history = ProfileStatusHistory.objects.create(
            eygar_host=self.eygar_host,
            old_status='draft',
            new_status='submitted'
        )
        
        # Delete host profile should delete history
        self.eygar_host.delete()
        
        with self.assertRaises(ProfileStatusHistory.DoesNotExist):
            ProfileStatusHistory.objects.get(id=history.id)

    def test_set_null_when_user_deleted(self):
        """Test SET_NULL behavior when user is deleted"""
        history = ProfileStatusHistory.objects.create(
            eygar_host=self.eygar_host,
            old_status='draft',
            new_status='submitted',
            changed_by=self.admin_user
        )
        
        # Delete admin user
        self.admin_user.delete()
        
        # Refresh history from database
        history.refresh_from_db()
        self.assertIsNone(history.changed_by)


class ModelIntegrationTest(TestCase):
    """Integration tests for all models working together"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            is_staff=True
        )

    def test_complete_profile_creation_flow(self):
        """Test creating a complete host profile with all related models"""
        # Create host profile
        eygar_host = EygarHost.objects.create(user=self.user)
        
        # Create business profile
        business_profile = BusinessProfile.objects.create(
            eygar_host=eygar_host,
            business_name="Complete Business",
            license_number="LIC123456",
            business_address_line1="123 Business Ave",
            business_city="Business City",
            business_state="BS",
            business_postal_code="12345",
            business_country="Business Country"
        )
        
        # Create identity verification
        identity_verification = IdentityVerification.objects.create(
            eygar_host=eygar_host,
            document_type='national_id',
            document_number='ID987654321',
            verification_status='verified'
        )
        
        # Create contact details
        contact_details = ContactDetails.objects.create(
            eygar_host=eygar_host,
            address_line1="123 Contact St",
            city="Contact City",
            state="CS",
            postal_code="54321",
            country="Contact Country",
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060'),
            mobile_number="+1987654321"
        )
        
        # Create review submission
        review_submission = ReviewSubmission.objects.create(
            eygar_host=eygar_host,
            terms_accepted=True,
            privacy_policy_accepted=True
        )
        
        # Create status history
        status_history = ProfileStatusHistory.objects.create(
            eygar_host=eygar_host,
            old_status='draft',
            new_status='submitted',
            changed_by=self.admin_user
        )
        
        # Test all relationships work
        self.assertEqual(eygar_host.business_profile, business_profile)
        self.assertEqual(eygar_host.identity_verification, identity_verification)
        self.assertEqual(eygar_host.contact_details, contact_details)
        self.assertEqual(eygar_host.review_submission, review_submission)
        self.assertEqual(eygar_host.status_history.count(), 1)
        
        # Test reverse relationships
        self.assertEqual(business_profile.eygar_host, eygar_host)
        self.assertEqual(identity_verification.eygar_host, eygar_host)
        self.assertEqual(contact_details.eygar_host, eygar_host)
        self.assertEqual(review_submission.eygar_host, eygar_host)

    def test_profile_completion_tracking(self):
        """Test profile completion tracking through related models"""
        eygar_host = EygarHost.objects.create(user=self.user)
        
        # Initially no steps completed
        self.assertEqual(eygar_host.completion_percentage, 0.0)
        
        # Complete business profile
        BusinessProfile.objects.create(
            eygar_host=eygar_host,
            business_name="Test Business",
            license_number="LIC123"
        )
        eygar_host.business_profile_completed = True
        eygar_host.save()
        
        self.assertEqual(eygar_host.completion_percentage, 25.0)
        self.assertEqual(eygar_host.get_next_step(), 'identity_verification')
        
        # Complete identity verification
        IdentityVerification.objects.create(
            eygar_host=eygar_host,
            document_type='national_id',
            document_number='ID123',
            verification_status='verified'
        )
        eygar_host.identity_verification_completed = True
        eygar_host.save()
        
        self.assertEqual(eygar_host.completion_percentage, 50.0)
        self.assertEqual(eygar_host.get_next_step(), 'contact_details')

    def test_cascade_deletes(self):
        """Test cascade deletion behavior"""
        eygar_host = EygarHost.objects.create(user=self.user)
        
        BusinessProfile.objects.create(
            eygar_host=eygar_host,
            business_name="Test Business",
            license_number="LIC123"
        )
        
        IdentityVerification.objects.create(
            eygar_host=eygar_host,
            document_type='national_id',
            document_number='ID123'
        )
        
        # Store IDs before deletion
        business_profile_id = eygar_host.business_profile.id
        identity_verification_id = eygar_host.identity_verification.id
        
        # Delete host profile
        eygar_host.delete()
        
        # All related models should be deleted
        self.assertFalse(BusinessProfile.objects.filter(id=business_profile_id).exists())
        self.assertFalse(IdentityVerification.objects.filter(id=identity_verification_id).exists())

    def test_user_deletion_behavior(self):
        """Test what happens when user is deleted"""
        eygar_host = EygarHost.objects.create(user=self.user)
        
        BusinessProfile.objects.create(
            eygar_host=eygar_host,
            business_name="Test Business",
            license_number="LIC123"
        )
        
        # Delete user should cascade to host profile and all related models
        user_id = self.user.id
        self.user.delete()
        
        self.assertFalse(EygarHost.objects.filter(user_id=user_id).exists())
        self.assertFalse(BusinessProfile.objects.filter(eygar_host__user_id=user_id).exists())
