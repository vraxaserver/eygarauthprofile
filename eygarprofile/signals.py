from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from .models import EygarHost, ProfileStatusHistory
from eygarprofile.application.services.host_profile_service import HostProfileService
import logging

logger = logging.getLogger(__name__)


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
    """Handle status changes and send notifications via HostProfileService."""
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

            # Delegate notifications and events to HostProfileService
            try:
                host_service = HostProfileService()
                host_service.on_status_changed(
                    eygar_host=instance,
                    old_status=old_status or 'draft',
                    new_status=new_status,
                    review_notes=getattr(instance, 'review_notes', ''),
                )
            except Exception as e:
                logger.error(
                    "Failed to process status change notification for host %s: %s",
                    instance.id,
                    str(e),
                )


@receiver(post_save, sender=EygarHost)
def notify_admins_on_submission(sender, instance, created, **kwargs):
    """Notify admins when a new profile is submitted for review."""
    if not created and hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.status

        if old_status != 'submitted' and new_status == 'submitted':
            try:
                from django.contrib.auth import get_user_model
                from accounts.infrastructure.notification_gateway import get_notification_gateway

                User = get_user_model()
                gateway = get_notification_gateway()

                # Get all admin email addresses
                admin_emails = list(
                    User.objects.filter(
                        Q(is_staff=True) | Q(is_superuser=True)
                    ).values_list('email', flat=True)
                )

                for admin_email in admin_emails:
                    if admin_email:
                        gateway.send_transactional_email(
                            to_email=admin_email,
                            subject='New Host Profile Submitted for Review',
                            message=(
                                f"A new host profile has been submitted for review.\n\n"
                                f"User: {instance.user.username} ({instance.user.email})\n"
                                f"Submitted: {instance.submitted_at.strftime('%B %d, %Y at %I:%M %p') if instance.submitted_at else 'N/A'}\n"
                                f"Profile ID: {instance.id}\n\n"
                                f"Please log in to the admin panel to review the application."
                            ),
                        )
            except Exception as e:
                logger.error("Failed to send admin notification email: %s", str(e))


# Optional: Signal for when documents are uploaded
@receiver(post_save, sender=EygarHost)
def handle_document_upload_completion(sender, instance, **kwargs):
    """Handle completion of document uploads"""
    if instance.business_profile_completed and instance.identity_verification_completed:
        # Trigger any additional processing when critical documents are uploaded
        # For example, queue document verification tasks, etc.
        pass
