# accounts/infrastructure/repositories.py
"""
Concrete Django ORM implementations of the domain repository interfaces.
"""
import logging
from typing import Optional
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from accounts.domain.repositories import (
    UserRepositoryInterface,
    GuestProfileRepositoryInterface,
    VerificationCodeRepositoryInterface,
    SocialAccountRepositoryInterface,
)
from accounts.models import GuestProfile, VerificationCode, SocialAccount

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRepository(UserRepositoryInterface):

    def get_by_id(self, user_id: UUID):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def get_by_email(self, email: str):
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None

    def get_by_phone(self, phone_number: str):
        try:
            return User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return None

    def get_by_email_or_phone(self, identifier: str):
        """Lookup user by email or phone number."""
        try:
            return User.objects.get(Q(email__iexact=identifier) | Q(phone_number=identifier))
        except User.DoesNotExist:
            return None

    def exists_by_email(self, email: str) -> bool:
        return User.objects.filter(email__iexact=email).exists()

    def exists_by_phone(self, phone_number: str) -> bool:
        return User.objects.filter(phone_number=phone_number).exists()

    def create_user(self, email=None, phone_number=None, password=None, **extra_fields):
        return User.objects.create_user(
            email=email,
            phone_number=phone_number,
            password=password,
            **extra_fields,
        )

    def save(self, user) -> None:
        user.save()


class GuestProfileRepository(GuestProfileRepositoryInterface):

    def get_by_user(self, user):
        try:
            return GuestProfile.objects.get(user=user)
        except GuestProfile.DoesNotExist:
            return None

    def create(self, user, **profile_data):
        return GuestProfile.objects.create(user=user, **profile_data)

    def update(self, profile, **data):
        for field, value in data.items():
            setattr(profile, field, value)
        profile.save()
        return profile

    def exists_for_user(self, user) -> bool:
        return GuestProfile.objects.filter(user=user).exists()


class VerificationCodeRepository(VerificationCodeRepositoryInterface):

    def create(self, user, code: str, channel: str, purpose: str, expires_at):
        return VerificationCode.objects.create(
            user=user,
            code=code,
            channel=channel,
            purpose=purpose,
            expires_at=expires_at,
        )

    def get_active_code(self, user, purpose: str, channel: str):
        """Return the latest non-expired, unused code for the user."""
        return (
            VerificationCode.objects
            .filter(
                user=user,
                purpose=purpose,
                channel=channel,
                is_used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by('-created_at')
            .first()
        )

    def invalidate_codes(self, user, purpose: str, channel: str) -> None:
        VerificationCode.objects.filter(
            user=user,
            purpose=purpose,
            channel=channel,
            is_used=False,
        ).update(is_used=True)

    def mark_used(self, code_obj) -> None:
        code_obj.is_used = True
        code_obj.save(update_fields=['is_used'])


class SocialAccountRepository(SocialAccountRepositoryInterface):

    def get_by_provider_uid(self, provider: str, provider_user_id: str):
        try:
            return SocialAccount.objects.get(
                provider=provider,
                provider_user_id=provider_user_id,
            )
        except SocialAccount.DoesNotExist:
            return None

    def create(self, user, provider: str, provider_user_id: str, **extra):
        return SocialAccount.objects.create(
            user=user,
            provider=provider,
            provider_user_id=provider_user_id,
            **extra,
        )

    def update_or_create(self, user, provider: str, provider_user_id: str, **extra):
        obj, created = SocialAccount.objects.update_or_create(
            provider=provider,
            provider_user_id=provider_user_id,
            defaults={'user': user, **extra},
        )
        return obj, created
