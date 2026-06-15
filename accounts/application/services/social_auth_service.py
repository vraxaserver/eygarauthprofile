# accounts/application/services/social_auth_service.py
"""
Handles social authentication (Google, Facebook).
The frontend handles the OAuth redirect and sends the access token to this service.
"""
import logging

import requests
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.application.dto import SocialAuthDTO
from accounts.domain.events import GuestProfileCreated, UserRegistered
from accounts.domain.exceptions import SocialAuthError
from accounts.infrastructure.repositories import (
    GuestProfileRepository,
    SocialAccountRepository,
    UserRepository,
)
from accounts.infrastructure.sns_publisher import get_sns_publisher

logger = logging.getLogger(__name__)

# Provider token-info endpoints
GOOGLE_TOKEN_INFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
FACEBOOK_TOKEN_INFO_URL = 'https://graph.facebook.com/v18.0/me'


class SocialAuthService:

    def __init__(
        self,
        user_repo=None,
        profile_repo=None,
        social_repo=None,
        sns_publisher=None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.profile_repo = profile_repo or GuestProfileRepository()
        self.social_repo = social_repo or SocialAccountRepository()
        self.sns = sns_publisher or get_sns_publisher()

    def authenticate(self, dto: SocialAuthDTO) -> dict:
        """
        Authenticate via social provider token.
        Creates user + guest profile if new.
        Returns JWT tokens.
        """
        if dto.provider not in ('google', 'facebook'):
            raise SocialAuthError(f"Unsupported provider: {dto.provider}")

        # Validate token with provider and extract profile info
        if dto.provider == 'google':
            social_data = self._validate_google_token(dto.access_token)
        else:
            social_data = self._validate_facebook_token(dto.access_token)

        provider_user_id = social_data['id']
        email = social_data.get('email')

        if not email:
            raise SocialAuthError("Email not available from social provider.")

        # Check if social account already exists
        social_account = self.social_repo.get_by_provider_uid(dto.provider, provider_user_id)

        is_new_user = False

        if social_account:
            user = social_account.user
        else:
            # Try to find existing user by email
            user = self.user_repo.get_by_email(email)

            if not user:
                # Create new user
                is_new_user = True
                with transaction.atomic():
                    user = self.user_repo.create_user(
                        email=email,
                        phone_number=None,
                        password=None,  # Social users don't have a password
                        is_active=True,
                        is_email_verified=True,  # Social providers pre-verify email
                        first_name=social_data.get('first_name', ''),
                        last_name=social_data.get('last_name', ''),
                    )
                    # Override is_active since create_user defaults to False
                    user.is_active = True
                    user.is_email_verified = True
                    if social_data.get('first_name'):
                        user.first_name = social_data['first_name']
                    if social_data.get('last_name'):
                        user.last_name = social_data['last_name']
                    user.save()

            # Link social account
            self.social_repo.update_or_create(
                user=user,
                provider=dto.provider,
                provider_user_id=provider_user_id,
                access_token=dto.access_token,
                extra_data=social_data,
            )

        # Ensure user is active and email verified (in case they existed before)
        if not user.is_active or not user.is_email_verified:
            user.is_active = True
            user.is_email_verified = True
            self.user_repo.save(user)

        # Create guest profile if missing
        guest_profile = None
        if not self.profile_repo.exists_for_user(user):
            with transaction.atomic():
                guest_profile = self.profile_repo.create(
                    user=user,
                    email=email,
                    first_name=social_data.get('first_name', ''),
                    last_name=social_data.get('last_name', ''),
                    avatar_url=social_data.get('picture', ''),
                )

        # Publish events for new users
        if is_new_user:
            self.sns.publish_event(UserRegistered(
                user_id=str(user.id),
                email=user.email,
                phone_number=user.phone_number,
            ))

            if guest_profile:
                self.sns.publish_event(GuestProfileCreated(
                    user_id=str(user.id),
                    guest_profile_id=str(guest_profile.id),
                    email=user.email,
                    phone=user.phone_number,
                ))

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        logger.info("Social auth successful: %s via %s (new=%s)", email, dto.provider, is_new_user)

        return {
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'user': {
                'id': str(user.id),
                'email': user.email,
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'avatar_url': user.avatar_url,
                'is_email_verified': user.is_email_verified,
                'is_phone_verified': user.is_phone_verified,
            },
            'is_new_user': is_new_user,
        }

    def _validate_google_token(self, access_token: str) -> dict:
        """Validate Google OAuth2 access token and return user info."""
        try:
            resp = requests.get(
                GOOGLE_TOKEN_INFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
            if resp.status_code != 200:
                raise SocialAuthError("Invalid Google access token.")

            data = resp.json()
            return {
                'id': data.get('sub'),
                'email': data.get('email'),
                'first_name': data.get('given_name', ''),
                'last_name': data.get('family_name', ''),
                'picture': data.get('picture', ''),
                'email_verified': data.get('email_verified', False),
            }
        except requests.RequestException:
            raise SocialAuthError("Failed to validate Google token.")

    def _validate_facebook_token(self, access_token: str) -> dict:
        """Validate Facebook access token and return user info."""
        try:
            resp = requests.get(
                FACEBOOK_TOKEN_INFO_URL,
                params={
                    'access_token': access_token,
                    'fields': 'id,email,first_name,last_name,picture.type(large)',
                },
                timeout=10,
            )
            if resp.status_code != 200:
                raise SocialAuthError("Invalid Facebook access token.")

            data = resp.json()
            picture_url = ''
            if 'picture' in data and 'data' in data['picture']:
                picture_url = data['picture']['data'].get('url', '')

            return {
                'id': data.get('id'),
                'email': data.get('email'),
                'first_name': data.get('first_name', ''),
                'last_name': data.get('last_name', ''),
                'picture': picture_url,
            }
        except requests.RequestException:
            raise SocialAuthError("Failed to validate Facebook token.")
