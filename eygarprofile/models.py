from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid
import os

User = get_user_model()

class EygarHost(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('pending', 'Pending'),
        ('on_hold', 'On Hold'),
    ]
    
    STEP_CHOICES = [
        ('business_profile', 'Business Profile'),
        ('identity_verification', 'Identity Verification'),
        ('contact_details', 'Contact Details'),
        ('review_submission', 'Review Submission'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='eygar_host')
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    current_step = models.CharField(max_length=30, choices=STEP_CHOICES, default='business_profile')
    
    # Step completion tracking
    business_profile_completed = models.BooleanField(default=False)
    identity_verification_completed = models.BooleanField(default=False)
    contact_details_completed = models.BooleanField(default=False)
    review_submission_completed = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Review information
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_profiles')
    review_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'eygar_hosts'
        ordering = ['-created_at']

    def __str__(self):
        return f"Eygar Host - {self.user.username}"

    @property
    def completion_percentage(self):
        steps = [
            self.business_profile_completed,
            self.identity_verification_completed,
            self.contact_details_completed,
            self.review_submission_completed
        ]
        completed_steps = sum(steps)
        return (completed_steps / len(steps)) * 100

    def get_next_step(self):
        if not self.business_profile_completed:
            return 'business_profile'
        elif not self.identity_verification_completed:
            return 'identity_verification'
        elif not self.contact_details_completed:
            return 'contact_details'
        elif not self.review_submission_completed:
            return 'review_submission'
        elif self.review_submission_completed:
            return 'completed'
        return None

    def can_proceed_to_step(self, step):
        step_order = ['business_profile', 'identity_verification', 'contact_details', 'review_submission', 'completed']
        current_index = step_order.index(self.current_step) if self.current_step in step_order else 0
        target_index = step_order.index(step)
        
        # Can only proceed to next step or current step
        return target_index <= current_index + 1

def license_upload_path(instance, filename):
    # Store in: licenses/<eygar_host.id>/<filename>
    return os.path.join("licenses", str(instance.eygar_host.id), filename)

def logo_upload_path(instance, filename):
    # Store in: business_logos/<eygar_host.id>/<filename>
    return os.path.join("business_logos", str(instance.eygar_host.id), filename)

class BusinessProfile(models.Model):
    eygar_host = models.OneToOneField(EygarHost, on_delete=models.CASCADE, related_name='business_profile')
    
    # Business Information
    business_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=100)
    license_document = models.FileField(upload_to=license_upload_path, help_text="Upload business license document")
    business_logo = models.ImageField(upload_to=logo_upload_path, null=True, blank=True)
    
    # Business Address
    business_address_line1 = models.CharField(max_length=255)
    business_address_line2 = models.CharField(max_length=255, blank=True)
    business_city = models.CharField(max_length=100)
    business_state = models.CharField(max_length=100)
    business_postal_code = models.CharField(max_length=20)
    business_country = models.CharField(max_length=100)
    
    # Business Description
    business_description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'business_profiles'

    def __str__(self):
        return f"Business Profile - {self.business_name}"


class IdentityVerification(models.Model):
    DOCUMENT_TYPES = [
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
    ]
    
    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    eygar_host = models.OneToOneField(EygarHost, on_delete=models.CASCADE, related_name='identity_verification')
    
    # Document Information
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=50)
    document_image_front = models.ImageField(upload_to='identity_documents/%Y/%m/')
    document_image_back = models.ImageField(upload_to='identity_documents/%Y/%m/', null=True, blank=True)
    
    # Verification Status
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    verification_notes = models.TextField(blank=True)
    
    # Extracted Information (populated after verification)
    full_name = models.CharField(max_length=255, blank=True)
    fathers_name = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Address from ID
    id_address_line1 = models.CharField(max_length=255, blank=True)
    id_address_line2 = models.CharField(max_length=255, blank=True)
    id_city = models.CharField(max_length=100, blank=True)
    id_state = models.CharField(max_length=100, blank=True)
    id_postal_code = models.CharField(max_length=20, blank=True)
    id_country = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'identity_verifications'

    def __str__(self):
        return f"Identity Verification - {self.eygar_host.user.username}"


class ContactDetails(models.Model):
    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]

    eygar_host = models.OneToOneField(EygarHost, on_delete=models.CASCADE, related_name='contact_details')
    
    # Physical Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    # Coordinates
    latitude = models.CharField(max_length=15, null=True, blank=True)
    longitude = models.CharField(max_length=15, null=True, blank=True)
    
    # Contact Information
    mobile_number = models.CharField(max_length=20, validators=[
        RegexValidator(r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    ])
    mobile_verified = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    mobile_verification_code = models.CharField(max_length=6, blank=True)
    mobile_verification_sent_at = models.DateTimeField(null=True, blank=True)
    
    whatsapp_number = models.CharField(max_length=20, blank=True, validators=[
        RegexValidator(r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    ])
    whatsapp_verified = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    
    telegram_username = models.CharField(max_length=100, blank=True)
    telegram_verified = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    
    facebook_page_url = models.URLField(blank=True)
    facebook_verified = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    
    # Email (from user model but can be verified here)
    email_verified = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contact_details'

    def __str__(self):
        return f"Contact Details - {self.eygar_host.user.username}"


class ReviewSubmission(models.Model):
    eygar_host = models.OneToOneField(EygarHost, on_delete=models.CASCADE, related_name='review_submission')
    
    # Submission Information
    submitted_at = models.DateTimeField(auto_now_add=True)
    additional_notes = models.TextField(blank=True, help_text="Any additional information for reviewers")
    
    # Terms and Conditions
    terms_accepted = models.BooleanField(default=False)
    privacy_policy_accepted = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'review_submissions'

    def __str__(self):
        return f"Review Submission - {self.eygar_host.user.username}"


class ProfileStatusHistory(models.Model):
    eygar_host = models.ForeignKey(EygarHost, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    change_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'profile_status_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"Status Change: {self.old_status} -> {self.new_status}"
    
