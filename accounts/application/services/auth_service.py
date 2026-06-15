# accounts/application/services/auth_service.py
"""
Handles authentication (login) logic.
"""
import logging

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.application.dto import LoginDTO
from accounts.application.services.registration_service import detect_identifier_type
from accounts.domain.exceptions import (
    InvalidCredentialsError,
    UserNotActiveError,
    UserNotFoundError,
)
from accounts.infrastructure.repositories import UserRepository

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthService:

    def __init__(self, user_repo=None):
        self.user_repo = user_repo or UserRepository()

    def login(self, dto: LoginDTO) -> dict:
        """
        Authenticate user by email or phone + password.
        Returns JWT tokens and user info.
        """
        # Find user
        user = self.user_repo.get_by_email_or_phone(dto.email_or_phone)
        if not user:
            raise InvalidCredentialsError()

        # Check active/verified status
        if not user.is_active:
            raise UserNotActiveError()

        # Check password
        if not user.check_password(dto.password):
            raise InvalidCredentialsError()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        logger.info("User logged in: %s", dto.email_or_phone)

        return {
            'tokens': tokens,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'avatar_url': user.avatar_url,
                'is_email_verified': user.is_email_verified,
                'is_phone_verified': user.is_phone_verified,
                'stripe_customer_id': user.stripe_customer_id,
            },
        }
