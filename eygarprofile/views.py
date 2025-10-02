from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import random
import string

User = get_user_model()

from .models import (
    EygarHost, BusinessProfile, IdentityVerification,
    ContactDetails, ReviewSubmission, ProfileStatusHistory
)
from .serializers import (
    EygarHostSerializer, EygarHostDetailSerializer,
    BusinessProfileSerializer, IdentityVerificationSerializer,
    ContactDetailsSerializer, ReviewSubmissionSerializer,
    MobileVerificationSerializer, VerifyMobileCodeSerializer,
    AdminReviewSerializer, EygarProfileSerializer
)
from .permissions import IsOwnerOrReadOnly, IsAdminOrModerator
from .utils import send_sms_verification, verify_identity_document


class EygarHostViewSet(ViewSet):
    """
    ViewSet for managing host profiles and their completion steps
    """
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        """
        Handles GET requests to retrieve a single host profile by its primary key (ID).
        This method is automatically mapped to URLs like /api/profiles/hosts/{pk}/.
        """
        try:
            profile = EygarHost.objects.get(id=pk)
        except EygarHost.DoesNotExist:
            return Response(
                {"error": "Host not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only the profile owner or an admin can retrieve a specific host profile
        is_owner = profile.user == request.user
        is_admin = request.user.is_staff

        if not (is_owner or is_admin):
            return Response(
                {"detail": "You do not have permission to view this profile."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = EygarHostDetailSerializer(profile)
        return Response(serializer.data)

    def get_eygar_host(self):
        """Get or create host profile for current user"""
        profile, created = EygarHost.objects.get_or_create(
            user=self.request.user,
            defaults={'current_step': 'business_profile'}
        )
        return profile

    def list(self, request, *args, **kwargs):
        """
        Get list of all host profiles.
        This method is mapped to URLs like /api/profiles/hosts/.
        """
        # Only admin or superuser can request a list of all hosts
        if not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        host_ids = data.get('host_ids')
        try:
            if host_ids:
                hosts = EygarHost.objects.filter(id__in=host_ids)
            else:
                hosts = EygarHost.objects.all()

            serializer = EygarHostDetailSerializer(hosts, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve host profiles: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='my')
    def my_profile(self, request):
        """
        Returns the host profile for the currently authenticated user.
        This method is mapped to the URL: /api/profiles/hosts/my/
        """
        try:
            # Use the existing helper method to get the user's profile
            profile = self.get_eygar_host()
            serializer = EygarHostDetailSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve your host profile: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def business_profile(self, request):
        """Create or update business profile (Step 1)"""
        profile = self.get_eygar_host()
        
        # Check if user can access this step
        if not profile.can_proceed_to_step('business_profile'):
            return Response(
                {'error': 'Cannot access this step yet'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                business_profile, created = BusinessProfile.objects.get_or_create(
                    eygar_host=profile
                )
                
                serializer = BusinessProfileSerializer(
                    business_profile, 
                    data=request.data, 
                    partial=True
                )
                
                if serializer.is_valid():
                    serializer.save()
                    
                    # Mark step as completed and update current step
                    profile.business_profile_completed = True
                    profile.current_step = 'identity_verification'
                    profile.save()
                    
                    return Response({
                        'message': 'Business profile saved successfully',
                        'data': serializer.data,
                        'next_step': profile.get_next_step()
                    }, status=status.HTTP_200_OK)
                
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {'error': 'Failed to save business profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def identity_verification(self, request):
        """Upload identity documents for verification (Step 2)"""
        profile = self.get_eygar_host()
        
        # Check if user can access this step
        if not profile.can_proceed_to_step('identity_verification'):
            return Response(
                {'error': 'Please complete business profile first'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                identity_verification, created = IdentityVerification.objects.get_or_create(
                    eygar_host=profile
                )
                
                serializer = IdentityVerificationSerializer(
                    identity_verification,
                    data=request.data,
                    partial=True
                )
                
                if serializer.is_valid():
                    serializer.save()
                    
                    # Trigger document verification process
                    verification_result = verify_identity_document(identity_verification)
                    
                    if verification_result['success']:
                        identity_verification.verification_status = 'verified'
                        identity_verification.verified_at = timezone.now()
                        identity_verification.full_name = verification_result.get('full_name', '')
                        identity_verification.fathers_name = verification_result.get('fathers_name', '')
                        # Update other extracted fields...
                        identity_verification.save()
                        
                        # Mark step as completed
                        profile.identity_verification_completed = True
                        profile.current_step = 'contact_details'
                        profile.save()
                        
                        return Response({
                            'message': 'Identity verification completed successfully',
                            'verification_status': 'verified',
                            'next_step': profile.get_next_step()
                        }, status=status.HTTP_200_OK)
                    else:
                        identity_verification.verification_status = 'rejected'
                        identity_verification.verification_notes = verification_result.get('error', 'Document verification failed')
                        identity_verification.save()
                        
                        return Response({
                            'message': 'Document verification failed',
                            'error': verification_result.get('error'),
                            'verification_status': 'rejected'
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {'error': 'Failed to process identity verification'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def contact_details(self, request):
        """Add contact details and trigger verification (Step 3)"""
        profile = self.get_eygar_host()
        
        # Check if user can access this step
        if not profile.can_proceed_to_step('contact_details'):
            return Response(
                {'error': 'Please complete identity verification first'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                contact_details, created = ContactDetails.objects.get_or_create(
                    eygar_host=profile
                )
                
                serializer = ContactDetailsSerializer(
                    contact_details,
                    data=request.data,
                    partial=True
                )
                
                if serializer.is_valid():
                    serializer.save()
                    
                    # Auto-trigger mobile verification
                    if contact_details.mobile_number:
                        self.send_mobile_verification(contact_details)
                    
                    # Mark step as completed
                    profile.contact_details_completed = True
                    profile.current_step = 'review_submission'
                    profile.save()
                    
                    return Response({
                        'message': 'Contact details saved successfully',
                        'data': serializer.data,
                        'next_step': profile.get_next_step()
                    }, status=status.HTTP_200_OK)
                
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {'error': 'Failed to save contact details'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def submit_for_review(self, request):
        """Submit profile for admin review (Step 4)"""
        profile = self.get_eygar_host()
        
        # Check if user can access this step
        if not profile.can_proceed_to_step('review_submission'):
            return Response(
                {'error': 'Please complete contact details first'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate all previous steps are completed
        if not all([
            profile.business_profile_completed,
            profile.identity_verification_completed,
            profile.contact_details_completed
        ]):
            return Response(
                {'error': 'All previous steps must be completed before submission'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                review_submission, created = ReviewSubmission.objects.get_or_create(
                    eygar_host=profile
                )
                
                serializer = ReviewSubmissionSerializer(
                    review_submission,
                    data=request.data,
                    partial=True
                )
                
                if serializer.is_valid():
                    serializer.save()
                    
                    # Update profile status
                    profile.review_submission_completed = True
                    profile.status = 'submitted'
                    profile.submitted_at = timezone.now()
                    profile.save()
                    
                    # Create status history
                    ProfileStatusHistory.objects.create(
                        eygar_host=profile,
                        old_status='draft',
                        new_status='submitted',
                        changed_by=request.user,
                        change_reason='Profile submitted for review'
                    )
                    
                    # Send email notification to user
                    self.send_submission_email(profile)
                    
                    # Send notification to admins/moderators
                    self.notify_admins_new_submission(profile)
                    
                    return Response({
                        'message': 'Profile submitted for review successfully',
                        'status': 'submitted',
                        'submitted_at': profile.submitted_at
                    }, status=status.HTTP_200_OK)
                
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {'error': 'Failed to submit profile for review'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def current_status(self, request):
        """Get current step information"""
        profile = self.get_eygar_host()
        return Response({
            'current_step': profile.current_step,
            'next_step': profile.get_next_step(),
            'completion_percentage': profile.completion_percentage,
            'status': profile.status,
            'steps_completed': {
                'business_profile': profile.business_profile_completed,
                'identity_verification': profile.identity_verification_completed,
                'contact_details': profile.contact_details_completed,
                'review_submission': profile.review_submission_completed,
            }
        })

    def send_mobile_verification(self, contact_details):
        """Send SMS verification code"""
        # Generate 6-digit code
        verification_code = ''.join(random.choices(string.digits, k=6))
        
        contact_details.mobile_verification_code = verification_code
        contact_details.mobile_verification_sent_at = timezone.now()
        contact_details.save()
        
        # Send SMS (implement your SMS provider integration)
        send_sms_verification(contact_details.mobile_number, verification_code)

    def send_submission_email(self, profile):
        """Send email notification to user after submission"""
        subject = "Host Profile Submitted for Review"
        message = f"""
        Dear {profile.user.first_name or profile.user.username},
        
        Your host profile has been successfully submitted for review.
        
        Our team will review your application and get back to you within 2-3 business days.
        
        You will receive an email notification once the review is completed.
        
        Thank you for your patience.
        
        Best regards,
        The Review Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
            fail_silently=True,
        )

    def notify_admins_new_submission(self, profile):
        """Notify admins about new profile submission"""
        # Implementation for notifying admins
        # This could be email, slack notification, etc.
        pass


class MobileVerificationView(APIView):
    """Handle mobile number verification"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Send verification code to mobile number"""
        try:
            profile = get_object_or_404(EygarHost, user=request.user)
            contact_details = get_object_or_404(ContactDetails, eygar_host=profile)
            
            serializer = MobileVerificationSerializer(data=request.data)
            if serializer.is_valid():
                mobile_number = serializer.validated_data['mobile_number']
                
                # Generate verification code
                verification_code = ''.join(random.choices(string.digits, k=6))
                
                # Update contact details
                contact_details.mobile_verification_code = verification_code
                contact_details.mobile_verification_sent_at = timezone.now()
                contact_details.save()
                
                # Send SMS
                success = send_sms_verification(mobile_number, verification_code)
                
                if success:
                    return Response({
                        'message': 'Verification code sent successfully'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Failed to send verification code'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': 'Failed to send verification code'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyMobileCodeView(APIView):
    """Verify mobile verification code"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Verify the mobile verification code"""
        try:
            profile = get_object_or_404(EygarHost, user=request.user)
            contact_details = get_object_or_404(ContactDetails, eygar_host=profile)
            
            serializer = VerifyMobileCodeSerializer(data=request.data)
            if serializer.is_valid():
                verification_code = serializer.validated_data['verification_code']
                
                # Check if code matches and is not expired (valid for 10 minutes)
                if (contact_details.mobile_verification_code == verification_code and
                    contact_details.mobile_verification_sent_at and
                    (timezone.now() - contact_details.mobile_verification_sent_at).seconds < 600):
                    
                    contact_details.mobile_verified = 'verified'
                    contact_details.mobile_verification_code = ''  # Clear the code
                    contact_details.save()
                    
                    return Response({
                        'message': 'Mobile number verified successfully'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Invalid or expired verification code'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(
                {'error': 'Failed to verify mobile number'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminReviewViewSet(ViewSet):
    """Admin/Moderator views for reviewing host profiles"""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrModerator]

    def list(self, request):
        """List all profiles pending review"""
        profiles = EygarHost.objects.filter(status='submitted').order_by('-submitted_at')
        serializer = EygarHostDetailSerializer(profiles, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Get detailed view of a profile for review"""
        profile = get_object_or_404(EygarHost, pk=pk)
        serializer = EygarHostDetailSerializer(profile)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review and update profile status"""
        profile = get_object_or_404(EygarHost, pk=pk)
        
        serializer = AdminReviewSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            old_status = profile.status
            new_status = serializer.validated_data['status']
            review_notes = serializer.validated_data.get('review_notes', '')
            
            with transaction.atomic():
                # Update profile
                profile.status = new_status
                profile.review_notes = review_notes
                profile.reviewed_at = timezone.now()
                profile.reviewer = request.user
                profile.save()
                
                # Create status history
                ProfileStatusHistory.objects.create(
                    eygar_host=profile,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                    change_reason=review_notes
                )
                
                # Send email notification to user
                self.send_review_result_email(profile, new_status, review_notes)
                
                return Response({
                    'message': f'Profile {new_status} successfully',
                    'status': new_status
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def send_review_result_email(self, profile, status, review_notes):
        """Send email notification about review result"""
        status_messages = {
            'approved': 'Congratulations! Your host profile has been approved.',
            'rejected': 'Unfortunately, your host profile has been rejected.',
            'pending': 'Your host profile is still under review.',
            'on_hold': 'Your host profile has been put on hold.'
        }
        
        subject = f"Host Profile Review Result - {status.title()}"
        message = f"""
        Dear {profile.user.first_name or profile.user.username},
        
        {status_messages.get(status, 'Your host profile status has been updated.')}
        
        Status: {status.title()}
        
        {f"Review Notes: {review_notes}" if review_notes else ""}
        
        {"You can now start hosting!" if status == 'approved' else ""}
        
        Best regards,
        The Review Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [profile.user.email],
            fail_silently=True,
        )


class EygarProfileViewSet(ReadOnlyModelViewSet):
    """
    A viewset that provides a single endpoint to retrieve the
    authenticated user's combined profile (User, EygarHost, EygarVendor).
    """
    serializer_class = EygarProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list containing only
        the authenticated user.
        """
        return User.objects.filter(pk=self.request.user.pk)

    def list(self, request, *args, **kwargs):
        """
        Custom list action to return a single object instead of a list.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset.first())
        return Response(serializer.data)

