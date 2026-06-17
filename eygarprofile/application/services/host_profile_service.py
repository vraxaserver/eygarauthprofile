# eygarprofile/application/services/host_profile_service.py
"""
Service layer for host profile domain events.
Wraps the existing ViewSet logic for event publishing.
"""
import logging

from accounts.domain.events import HostProfileCreated, HostProfileVerified
from accounts.domain.notification_templates import NotificationTemplate
from accounts.infrastructure.notification_gateway import get_notification_gateway
from accounts.infrastructure.sqs_publisher import get_sqs_publisher

logger = logging.getLogger(__name__)


class HostProfileService:

    def __init__(self, sqs_publisher=None, notification_gateway=None):
        self.sqs = sqs_publisher or get_sqs_publisher()
        self.notification = notification_gateway or get_notification_gateway()

    def on_profile_submitted(self, eygar_host):
        """
        Called when a host profile is submitted for review.
        Publishes HostProfileCreated event and notifies the user.
        """
        event = HostProfileCreated(
            user_id=str(eygar_host.user.id),
            host_profile_id=str(eygar_host.id),
            email=eygar_host.user.email,
        )
        self.sqs.publish_event(event)

        # Notify user via eygarnotification
        if eygar_host.user.email:
            self.notification.send_transactional_email(
                to_email=eygar_host.user.email,
                subject='Host Profile Submitted for Review',
                message=(
                    f"Dear {eygar_host.user.first_name or eygar_host.user.username},\n\n"
                    "Your host profile has been successfully submitted for review.\n"
                    "Our team will review your application within 2-3 business days.\n\n"
                    "Best regards,\nThe Eygar Team"
                ),
                template=NotificationTemplate.HOST_PROFILE_SUBMITTED,
                user_id=str(eygar_host.user.id),
                user_name=eygar_host.user.first_name or eygar_host.user.username,
            )

        logger.info(
            "HostProfileCreated event published for host=%s user=%s",
            eygar_host.id,
            eygar_host.user.id,
        )

    def on_profile_approved(self, eygar_host, reviewer=None):
        """
        Called when an admin approves a host profile.
        Publishes HostProfileVerified event and notifies the user.
        """
        # Mark host as verified on the User model
        user = eygar_host.user
        user.is_host_verified = True
        user.save(update_fields=['is_host_verified'])

        event = HostProfileVerified(
            user_id=str(user.id),
            host_profile_id=str(eygar_host.id),
            email=user.email,
        )
        self.sqs.publish_event(event)

        # Notify user
        if user.email:
            self.notification.send_transactional_email(
                to_email=user.email,
                subject='Congratulations! Your Host Profile Has Been Approved',
                message=(
                    f"Dear {user.first_name or user.username},\n\n"
                    "Great news! Your host profile has been approved.\n"
                    "You can now start hosting on the Eygar platform.\n\n"
                    "Best regards,\nThe Eygar Team"
                ),
                template=NotificationTemplate.HOST_PROFILE_APPROVED,
                user_id=str(user.id),
                user_name=user.first_name or user.username,
            )

        logger.info(
            "HostProfileVerified event published for host=%s user=%s",
            eygar_host.id,
            user.id,
        )

    def on_profile_rejected(self, eygar_host, review_notes=''):
        """
        Called when an admin rejects a host profile.
        Notifies the user via eygarnotification.
        """
        user = eygar_host.user
        if user.email:
            self.notification.send_transactional_email(
                to_email=user.email,
                subject='Host Profile Application Update Required',
                message=(
                    f"Dear {user.first_name or user.username},\n\n"
                    "Your host profile application requires some updates.\n\n"
                    f"Review Notes: {review_notes or 'Please review your submitted information.'}\n\n"
                    "Please update your profile and resubmit.\n\n"
                    "Best regards,\nThe Eygar Team"
                ),
                template=NotificationTemplate.HOST_PROFILE_REJECTED,
                user_id=str(user.id),
                user_name=user.first_name or user.username,
            )

    def on_status_changed(self, eygar_host, old_status, new_status, review_notes=''):
        """
        Generic handler for any host profile status change.
        Routes to specific handlers and sends notifications.
        """
        if new_status == 'approved':
            self.on_profile_approved(eygar_host)
        elif new_status == 'rejected':
            self.on_profile_rejected(eygar_host, review_notes)
        elif new_status == 'submitted' and old_status != 'submitted':
            self.on_profile_submitted(eygar_host)
        else:
            # Generic notification for other status changes (pending, on_hold)
            user = eygar_host.user
            if user.email:
                self.notification.send_transactional_email(
                    to_email=user.email,
                    subject=f'Host Profile Status Update: {new_status.title()}',
                    message=(
                        f"Dear {user.first_name or user.username},\n\n"
                        f"Your host profile status has been updated to: {new_status.title()}\n"
                        f"{('Notes: ' + review_notes) if review_notes else ''}\n\n"
                        "Best regards,\nThe Eygar Team"
                    ),
                    template=NotificationTemplate.HOST_PROFILE_STATUS_UPDATE,
                    user_id=str(user.id),
                    user_name=user.first_name or user.username,
                )
