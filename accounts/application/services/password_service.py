# accounts/application/services/password_service.py
"""
Handles forgot-password and reset-password flows.
"""
import logging
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.application.dto import ForgotPasswordDTO, ResetPasswordDTO
from accounts.application.services.registration_service import detect_identifier_type
from accounts.domain.events import PasswordResetRequested
from accounts.domain.exceptions import (
    InvalidVerificationCodeError,
    PasswordMismatchError,
    UserNotFoundError,
    VerificationCodeExpiredError,
)
from accounts.infrastructure.notification_gateway import get_notification_gateway
from accounts.infrastructure.repositories import UserRepository
from accounts.infrastructure.sqs_publisher import get_sqs_publisher
from accounts.models import PasswordResetToken

logger = logging.getLogger(__name__)


class PasswordService:

    def __init__(
        self,
        user_repo=None,
        notification_gateway=None,
        sqs_publisher=None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.notification = notification_gateway or get_notification_gateway()
        self.sqs = sqs_publisher or get_sqs_publisher()

    def forgot_password(self, dto: ForgotPasswordDTO) -> dict:
        """
        Generate a password-reset code and send it via eygarnotification.
        """
        identifier_type = detect_identifier_type(dto.email_or_phone)

        user = self.user_repo.get_by_email_or_phone(dto.email_or_phone)
        if not user:
            raise UserNotFoundError()

        # Invalidate existing reset tokens
        PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate 6-digit reset code
        code = ''.join(secrets.choice(string.digits) for _ in range(6))
        expiry = timezone.now() + timedelta(minutes=15)

        PasswordResetToken.objects.create(
            user=user,
            code=code,
            expires_at=expiry,
        )

        # Build reset URL for frontend
        reset_url = f"{getattr(settings, 'SITE_URL', '')}/reset-password?code={code}"

        # Send via eygarnotification
        self.notification.send_password_reset(
            channel=identifier_type,
            recipient=dto.email_or_phone,
            code=code,
            reset_url=reset_url,
            user_id=str(user.id),
            user_name=user.first_name or '',
        )

        # Publish domain event
        event = PasswordResetRequested(
            user_id=str(user.id),
            email=user.email,
            phone=user.phone_number,
            channel=identifier_type,
            otp=code,
        )
        self.sqs.publish_event(event)

        logger.info("Password reset requested for %s", dto.email_or_phone)

        return {'message': f'A password reset code has been sent to your {identifier_type}.'}

    def reset_password(self, dto: ResetPasswordDTO) -> dict:
        """
        Validate the reset code and set a new password.
        """
        if dto.new_password != dto.confirm_password:
            raise PasswordMismatchError()

        # Find user
        user = self.user_repo.get_by_email_or_phone(dto.email_or_phone)
        if not user:
            raise UserNotFoundError()

        # Find valid token
        token = (
            PasswordResetToken.objects
            .filter(user=user, code=dto.code, is_used=False)
            .order_by('-created_at')
            .first()
        )

        if not token:
            raise InvalidVerificationCodeError("Invalid reset code.")

        if token.is_expired:
            raise VerificationCodeExpiredError("The reset code has expired. Please request a new one.")

        # Reset password
        with transaction.atomic():
            token.is_used = True
            token.save(update_fields=['is_used'])

            user.set_password(dto.new_password)
            user.save(update_fields=['password'])

        logger.info("Password reset completed for user %s", user.id)

        return {'message': 'Your password has been reset successfully.'}
