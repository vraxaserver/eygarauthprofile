from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    EygarHost, BusinessProfile, IdentityVerification, 
    ContactDetails, ReviewSubmission, ProfileStatusHistory
)

User = get_user_model()


class EygarHostSerializer(serializers.ModelSerializer):
    completion_percentage = serializers.ReadOnlyField()
    next_step = serializers.SerializerMethodField()
    
    class Meta:
        model = EygarHost
        fields = [
            'id', 'status', 'current_step', 'completion_percentage',
            'business_profile_completed', 'identity_verification_completed',
            'contact_details_completed', 'review_submission_completed',
            'created_at', 'updated_at', 'submitted_at', 'reviewed_at',
            'review_notes', 'next_step'
        ]
        read_only_fields = [
            'id', 'status', 'submitted_at', 'reviewed_at', 'review_notes'
        ]

    def get_next_step(self, obj):
        return obj.get_next_step()


class BusinessProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfile
        fields = [
            'business_name', 'business_type', 'license_number', 
            'license_document', 'business_logo', 'business_address_line1',
            'business_address_line2', 'business_city', 'business_state',
            'business_postal_code', 'business_country', 'business_description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_license_document(self, value):
        if value:
            # Validate file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("License document size should not exceed 5MB.")
            
            # Validate file type
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError("License document must be PDF, JPG, JPEG, or PNG format.")
        
        return value

    def validate_business_logo(self, value):
        if value:
            # Validate file size (max 2MB)
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError("Business logo size should not exceed 2MB.")
            
            # Validate file type
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError("Business logo must be JPG, JPEG, PNG, or GIF format.")
        
        return value


class IdentityVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityVerification
        fields = [
            'document_type', 'document_number', 'document_image_front',
            'document_image_back', 'verification_status', 'verification_notes',
            'full_name', 'fathers_name', 'date_of_birth',
            'id_address_line1', 'id_address_line2', 'id_city', 'id_state',
            'id_postal_code', 'id_country', 'created_at', 'updated_at', 'verified_at'
        ]
        read_only_fields = [
            'verification_status', 'verification_notes', 'full_name',
            'fathers_name', 'date_of_birth', 'id_address_line1',
            'id_address_line2', 'id_city', 'id_state', 'id_postal_code',
            'id_country', 'created_at', 'updated_at', 'verified_at'
        ]

    def validate_document_image_front(self, value):
        if value:
            # Validate file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Document image size should not exceed 5MB.")
            
            # Validate file type
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError("Document image must be JPG, JPEG, or PNG format.")
        
        return value

    def validate_document_image_back(self, value):
        if value:
            # Validate file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Document image size should not exceed 5MB.")
            
            # Validate file type
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
                raise serializers.ValidationError("Document image must be JPG, JPEG, or PNG format.")
        
        return value


class ContactDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactDetails
        fields = [
            'address_line1', 'address_line2', 'city', 'state', 'postal_code',
            'country', 'latitude', 'longitude', 'mobile_number', 'mobile_verified',
            'whatsapp_number', 'whatsapp_verified', 'telegram_username',
            'telegram_verified', 'facebook_page_url', 'facebook_verified',
            'email_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'mobile_verified', 'whatsapp_verified', 'telegram_verified',
            'facebook_verified', 'email_verified', 'created_at', 'updated_at'
        ]

    def validate_mobile_number(self, value):
        # Additional mobile number validation can be added here
        return value

    def validate_whatsapp_number(self, value):
        if value and len(value.strip()) > 0:
            # WhatsApp number validation
            pass
        return value


class ReviewSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewSubmission
        fields = [
            'additional_notes', 'terms_accepted', 'privacy_policy_accepted',
            'submitted_at'
        ]
        read_only_fields = ['submitted_at']

    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions to proceed.")
        return value

    def validate_privacy_policy_accepted(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the privacy policy to proceed.")
        return value


class ProfileStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = ProfileStatusHistory
        fields = [
            'old_status', 'new_status', 'changed_by_username',
            'change_reason', 'created_at'
        ]
        read_only_fields = ['created_at']


class EygarHostDetailSerializer(serializers.ModelSerializer):
    business_profile = BusinessProfileSerializer(read_only=True)
    identity_verification = IdentityVerificationSerializer(read_only=True)
    contact_details = ContactDetailsSerializer(read_only=True)
    review_submission = ReviewSubmissionSerializer(read_only=True)
    status_history = ProfileStatusHistorySerializer(many=True, read_only=True)
    completion_percentage = serializers.ReadOnlyField()
    next_step = serializers.SerializerMethodField()
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = EygarHost
        fields = [
            'id', 'status', 'current_step', 'completion_percentage',
            'business_profile_completed', 'identity_verification_completed',
            'contact_details_completed', 'review_submission_completed',
            'created_at', 'updated_at', 'submitted_at', 'reviewed_at',
            'review_notes', 'next_step', 'user_info', 'business_profile',
            'identity_verification', 'contact_details', 'review_submission',
            'status_history'
        ]

    def get_next_step(self, obj):
        return obj.get_next_step()

    def get_user_info(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'avatar': obj.user.avatar.url if obj.user.avatar else None,
            'email': obj.user.email,
            'first_name': obj.user.first_name,
            'last_name': obj.user.last_name,
        }


class MobileVerificationSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=20)
    
    def validate_mobile_number(self, value):
        import re
        pattern = r'^\+?1?\d{9,15}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("Invalid mobile number format.")
        return value


class VerifyMobileCodeSerializer(serializers.Serializer):
    verification_code = serializers.CharField(max_length=6, min_length=6)
    
    def validate_verification_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Verification code must contain only digits.")
        return value


class AdminReviewSerializer(serializers.ModelSerializer):
    """Serializer for admin/moderator to review host profiles"""
    class Meta:
        model = EygarHost
        fields = ['status', 'review_notes']

    def validate_status(self, value):
        allowed_statuses = ['approved', 'rejected', 'pending', 'on_hold']
        if value not in allowed_statuses:
            raise serializers.ValidationError("Invalid status for review.")
        return value


class EygarHostProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EygarHost
        fields = '__all__'

# class EygarVendorSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EygarVendor
#         fields = '__all__'

class EygarProfileSerializer(serializers.ModelSerializer):
    host_profile = EygarHostProfileSerializer(source='eygar_host', read_only=True)
    # vendor_profile = EygarVendorSerializer(source='eygar_vendor', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'avatar',
            'first_name',
            'last_name',
            'is_email_verified',
            'created_at',
            'updated_at',
            'host_profile'
            # 'vendor_profile'
        ]