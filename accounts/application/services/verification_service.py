# accounts/application/services/verification_service.py
"""
Handles verification code validation, account activation,
and automatic guest profile creation.
"""
import logging

from django.conf import settings
from django.db import transaction

from accounts.application.dto import VerifyCodeDTO, ResendCodeDTO
from accounts.application.services.registration_service import detect_identifier_type
from accounts.domain.events import GuestProfileCreated, UserVerified
from accounts.domain.exceptions import (
    InvalidVerificationCodeError,
    UserNotFoundError,
    VerificationCodeExpiredError,
)
from accounts.infrastructure.notification_gateway import get_notification_gateway
from accounts.infrastructure.repositories import (
    GuestProfileRepository,
    UserRepository,
    VerificationCodeRepository,
)
from accounts.infrastructure.sqs_publisher import get_sqs_publisher
from accounts.models import VerificationCode

logger = logging.getLogger(__name__)


class VerificationService:

    def __init__(
        self,
        user_repo=None,
        code_repo=None,
        profile_repo=None,
        notification_gateway=None,
        sqs_publisher=None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.code_repo = code_repo or VerificationCodeRepository()
        self.profile_repo = profile_repo or GuestProfileRepository()
        self.notification = notification_gateway or get_notification_gateway()
        self.sqs = sqs_publisher or get_sqs_publisher()

    def verify_code(self, dto: VerifyCodeDTO) -> dict:
        """
        Verify a 6-digit code, activate the user, create guest profile,
        and publish domain events.

        Returns a dict with user_id and profile info.
        """
        identifier_type = detect_identifier_type(dto.email_or_phone)

        # --- Find user ---
        user = self.user_repo.get_by_email_or_phone(dto.email_or_phone)
        if not user:
            raise UserNotFoundError()

        # --- Find active code ---
        code_obj = self.code_repo.get_active_code(
            user=user,
            purpose='registration',
            channel=identifier_type,
        )

        if not code_obj:
            raise InvalidVerificationCodeError("No active verification code found. Please request a new one.")

        if code_obj.is_expired:
            raise VerificationCodeExpiredError()

        if code_obj.code != dto.code:
            raise InvalidVerificationCodeError()

        # --- Activate user and create profile ---
        with transaction.atomic():
            self.code_repo.mark_used(code_obj)

            user.is_active = True
            if identifier_type == 'email':
                user.is_email_verified = True
            else:
                user.is_phone_verified = True
            self.user_repo.save(user)

            # Create guest profile if it doesn't exist
            guest_profile = None
            if not self.profile_repo.exists_for_user(user):
                profile_data = {
                    'email': user.email or '',
                    'phone_number': user.phone_number or '',
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                }
                guest_profile = self.profile_repo.create(user=user, **profile_data)

            # Optional: create Stripe customer
            self._create_stripe_customer(user)

        # --- Publish events ---
        if guest_profile:
            event = GuestProfileCreated(
                user_id=str(user.id),
                guest_profile_id=str(guest_profile.id),
                email=user.email,
                phone=user.phone_number,
            )
            self.sqs.publish_event(event)

        # Check if fully verified (both email and phone)
        if user.is_fully_verified:
            event = UserVerified(
                user_id=str(user.id),
                email=user.email,
                phone=user.phone_number,
                email_verified=user.is_email_verified,
                phone_verified=user.is_phone_verified,
            )
            self.sqs.publish_event(event)

        logger.info("User verified: %s", dto.email_or_phone)

        return {
            'user_id': str(user.id),
            'is_active': user.is_active,
            'is_email_verified': user.is_email_verified,
            'is_phone_verified': user.is_phone_verified,
            'message': 'Account verified successfully.',
        }

    def verify_additional_contact(self, user, dto: VerifyCodeDTO) -> dict:
        """
        Verify an additional contact method (e.g., phone after email).
        Used when a verified user adds a second contact method.
        """
        identifier_type = detect_identifier_type(dto.email_or_phone)
        purpose = f'{identifier_type}_verification'

        code_obj = self.code_repo.get_active_code(
            user=user,
            purpose=purpose,
            channel=identifier_type,
        )

        if not code_obj:
            raise InvalidVerificationCodeError("No active verification code found.")

        if code_obj.is_expired:
            raise VerificationCodeExpiredError()

        if code_obj.code != dto.code:
            raise InvalidVerificationCodeError()

        with transaction.atomic():
            self.code_repo.mark_used(code_obj)

            if identifier_type == 'email':
                user.email = dto.email_or_phone
                user.is_email_verified = True
            else:
                user.phone_number = dto.email_or_phone
                user.is_phone_verified = True
            self.user_repo.save(user)

        # Check if now fully verified
        if user.is_fully_verified:
            event = UserVerified(
                user_id=str(user.id),
                email=user.email,
                phone=user.phone_number,
                email_verified=user.is_email_verified,
                phone_verified=user.is_phone_verified,
            )
            self.sqs.publish_event(event)

        return {
            'user_id': str(user.id),
            'is_email_verified': user.is_email_verified,
            'is_phone_verified': user.is_phone_verified,
            'message': f'{identifier_type.title()} verified successfully.',
        }

    def resend_code(self, dto: ResendCodeDTO) -> dict:
        """
        Invalidate existing codes and send a new one.
        """
        identifier_type = detect_identifier_type(dto.email_or_phone)

        user = self.user_repo.get_by_email_or_phone(dto.email_or_phone)
        if not user:
            raise UserNotFoundError()

        channel = identifier_type

        # Invalidate old codes
        self.code_repo.invalidate_codes(
            user=user,
            purpose='registration',
            channel=channel,
        )

        # Generate new code
        code = VerificationCode.generate_code()
        self.code_repo.create(
            user=user,
            code=code,
            channel=channel,
            purpose='registration',
            expires_at=VerificationCode.default_expiry(),
        )

        # Send via notification service
        self.notification.send_verification_code(
            channel=channel,
            recipient=dto.email_or_phone,
            code=code,
            purpose='registration',
            user_id=str(user.id),
            user_name=user.first_name or '',
        )

        logger.info("Resent verification code to %s", dto.email_or_phone)

        return {'message': f'A new verification code has been sent to your {identifier_type}.'}

    def _create_stripe_customer(self, user):
        """Optionally create a Stripe customer on verification."""
        stripe_enabled = getattr(settings, 'STRIPE_ENABLED', True)
        if not stripe_enabled:
            return

        if user.stripe_customer_id:
            return

        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or None,
                metadata={
                    'user_id': str(user.pk),
                    'source': 'auth-service-verification',
                },
                idempotency_key=f"user-verify-{user.pk}",
            )
            user.stripe_customer_id = customer['id']
            user.save(update_fields=['stripe_customer_id'])
        except Exception:
            logger.exception("Failed to create Stripe customer for user %s", user.id)
            # Don't block activation for Stripe failure
