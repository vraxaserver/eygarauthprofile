# accounts/application/services/registration_service.py
"""
Handles user registration with email or phone number.
"""
import logging
import re

from django.db import transaction

from accounts.application.dto import RegisterDTO
from accounts.domain.events import UserRegistered
from accounts.domain.exceptions import (
    InvalidInputError,
    PasswordMismatchError,
    UserAlreadyExistsError,
)
from accounts.infrastructure.notification_gateway import get_notification_gateway
from accounts.infrastructure.repositories import (
    UserRepository,
    VerificationCodeRepository,
)
from accounts.infrastructure.sns_publisher import get_sns_publisher
from accounts.models import VerificationCode

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
PHONE_REGEX = re.compile(r'^\+?1?\d{9,15}$')


def detect_identifier_type(value: str) -> str:
    """Return 'email' or 'phone' based on the input format."""
    if EMAIL_REGEX.match(value):
        return 'email'
    if PHONE_REGEX.match(value):
        return 'phone'
    raise InvalidInputError("Please provide a valid email address or phone number.")


class RegistrationService:

    def __init__(
        self,
        user_repo=None,
        code_repo=None,
        notification_gateway=None,
        sns_publisher=None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.code_repo = code_repo or VerificationCodeRepository()
        self.notification = notification_gateway or get_notification_gateway()
        self.sns = sns_publisher or get_sns_publisher()

    def register(self, dto: RegisterDTO) -> dict:
        """
        Register a new user with email or phone, returning a summary dict.

        Raises
        ------
        InvalidInputError, PasswordMismatchError, UserAlreadyExistsError
        """
        # --- Validation ---
        identifier_type = detect_identifier_type(dto.email_or_phone)

        if dto.password != dto.confirm_password:
            raise PasswordMismatchError()

        # Check duplicate
        if identifier_type == 'email':
            if self.user_repo.exists_by_email(dto.email_or_phone):
                raise UserAlreadyExistsError("A user with this email already exists.")
        else:
            if self.user_repo.exists_by_phone(dto.email_or_phone):
                raise UserAlreadyExistsError("A user with this phone number already exists.")

        # --- Create user (inactive) ---
        with transaction.atomic():
            email = dto.email_or_phone if identifier_type == 'email' else None
            phone = dto.email_or_phone if identifier_type == 'phone' else None

            user = self.user_repo.create_user(
                email=email,
                phone_number=phone,
                password=dto.password,
            )

            # --- Generate verification code ---
            code = VerificationCode.generate_code()
            channel = identifier_type
            self.code_repo.create(
                user=user,
                code=code,
                channel=channel,
                purpose='registration',
                expires_at=VerificationCode.default_expiry(),
            )

        # --- Send verification code via eygarnotification ---
        self.notification.send_verification_code(
            channel=channel,
            recipient=dto.email_or_phone,
            code=code,
            purpose='registration',
            user_id=str(user.id),
            user_name=user.first_name or '',
        )

        # --- Publish UserRegistered event ---
        event = UserRegistered(
            user_id=str(user.id),
            email=user.email,
            phone_number=user.phone_number,
            otp=code,
        )
        self.sns.publish_event(event)

        logger.info("User registered: %s (channel=%s)", dto.email_or_phone, channel)

        return {
            'user_id': str(user.id),
            'identifier_type': identifier_type,
            'message': f'Verification code sent to your {identifier_type}.',
        }
