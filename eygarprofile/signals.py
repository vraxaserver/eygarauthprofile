from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from .models import EygarHost, ProfileStatusHistory


@receiver(pre_save, sender=EygarHost)
def track_status_changes(sender, instance, **kwargs):
    """Track status changes before saving"""
    if instance.pk:
        try:
            old_instance = EygarHost.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except EygarHost.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=EygarHost)
def handle_status_change(sender, instance, created, **kwargs):
    """Handle status changes and send notifications"""
    if not created and hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.status
        
        if old_status != new_status:
            # Create status history record
            ProfileStatusHistory.objects.create(
                eygar_host=instance,
                old_status=old_status or 'draft',
                new_status=new_status,
                changed_by=getattr(instance, 'reviewer', None),
                change_reason=f'Status changed from {old_status} to {new_status}'
            )
            
            # Send email notification for status changes
            send_status_change_email(instance, old_status, new_status)


def send_status_change_email(eygar_host, old_status, new_status):
    """Send email notification when profile status changes"""
    user = eygar_host.user
    
    status_messages = {
        'approved': {
            'subject': 'Congratulations! Your Host Profile Has Been Approved',
            'message': f"""
                Dear {user.first_name or user.username},

                Great news! Your host profile has been approved and you can now start hosting.

                Your profile review is complete and you now have access to all host features.

                Next Steps:
                - Complete your host dashboard setup
                - Create your first listing
                - Start welcoming guests

                Thank you for joining our platform!

                Best regards,
                The Review Team
            """
        },
        'rejected': {
            'subject': 'Host Profile Application Update Required',
            'message': f"""
                Dear {user.first_name or user.username},

                Thank you for your interest in becoming a host on our platform.

                Unfortunately, your host profile application requires some updates before it can be approved.

                Review Notes: {eygar_host.review_notes or 'Please review your submitted information and ensure all required documents are clear and valid.'}

                What you can do:
                - Review the feedback provided
                - Update your profile information as needed
                - Resubmit your application for review

                If you have any questions, please don't hesitate to contact our support team.

                Best regards,
                The Review Team
            """
        },
        'pending': {
            'subject': 'Host Profile Under Review',
            'message': f"""
                Dear {user.first_name or user.username},

                Your host profile is currently under review by our team.

                We are carefully reviewing all the information and documents you've submitted to ensure everything meets our standards.

                Expected Timeline: 2-3 business days
                Current Status: Pending Review

                You will receive another email once the review is completed.

                Thank you for your patience.

                Best regards,
                The Review Team
            """
        },
        'on_hold': {
            'subject': 'Host Profile Application On Hold',
            'message': f"""
                Dear {user.first_name or user.username},

                Your host profile application has been temporarily placed on hold.

                This may be due to:
                - Additional verification required
                - Technical review in progress
                - Documentation clarification needed

                Review Notes: {eygar_host.review_notes or 'Our team is conducting additional verification steps.'}

                We will update you as soon as the review process continues.

                If you have any urgent questions, please contact our support team.

                Best regards,
                The Review Team
            """
        },
        'submitted': {
            'subject': 'Host Profile Submitted Successfully',
            'message': f"""
                Dear {user.first_name or user.username},

                Your host profile has been successfully submitted for review.

                What happens next:
                - Our team will review your application within 2-3 business days
                - We'll verify all submitted documents and information
                - You'll receive an email notification with the review result

                Submission Details:
                - Submitted on: {eygar_host.submitted_at.strftime('%B %d, %Y at %I:%M %p') if eygar_host.submitted_at else 'N/A'}
                - Application ID: {eygar_host.id}

                Thank you for your patience during the review process.

                Best regards,
                The Review Team
            """
        }
    }
    
    email_content = status_messages.get(new_status)
    if email_content:
        try:
            send_mail(
                subject=email_content['subject'],
                message=email_content['message'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Log the error but don't raise it
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send status change email to {user.email}: {str(e)}")


@receiver(post_save, sender=EygarHost)
def notify_admins_on_submission(sender, instance, created, **kwargs):
    """Notify admins when a new profile is submitted for review"""
    if not created and hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.status
        
        if old_status != 'submitted' and new_status == 'submitted':
            # Send notification to admin/moderators
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                # Get all admin users
                admin_users = User.objects.filter(
                    Q(is_staff=True) | Q(is_superuser=True)
                ).values_list('email', flat=True)
                
                if admin_users:
                    subject = f"New Host Profile Submitted for Review"
                    message = f"""
                    A new host profile has been submitted for review.

                    User: {instance.user.username} ({instance.user.email})
                    Submitted: {instance.submitted_at.strftime('%B %d, %Y at %I:%M %p') if instance.submitted_at else 'N/A'}
                    Profile ID: {instance.id}

                    Please log in to the admin panel to review the application.

                    Admin Panel: {settings.ADMIN_URL if hasattr(settings, 'ADMIN_URL') else '/admin/'}
                    """
                    
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=list(admin_users),
                        fail_silently=True,
                    )
                    
            except Exception as e:
                # Log the error but don't raise it
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send admin notification email: {str(e)}")


# Optional: Signal for when documents are uploaded
@receiver(post_save, sender=EygarHost)
def handle_document_upload_completion(sender, instance, **kwargs):
    """Handle completion of document uploads"""
    if instance.business_profile_completed and instance.identity_verification_completed:
        # Trigger any additional processing when critical documents are uploaded
        # For example, queue document verification tasks, etc.
        pass
