# accounts/domain/repositories.py
"""
Abstract repository interfaces (ports) for the domain layer.
Concrete implementations live in the infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID


class UserRepositoryInterface(ABC):
    """Port for user persistence operations."""

    @abstractmethod
    def get_by_id(self, user_id: UUID):
        ...

    @abstractmethod
    def get_by_email(self, email: str):
        ...

    @abstractmethod
    def get_by_phone(self, phone_number: str):
        ...

    @abstractmethod
    def get_by_email_or_phone(self, identifier: str):
        ...

    @abstractmethod
    def exists_by_email(self, email: str) -> bool:
        ...

    @abstractmethod
    def exists_by_phone(self, phone_number: str) -> bool:
        ...

    @abstractmethod
    def create_user(self, email: Optional[str], phone_number: Optional[str], password: str, **extra_fields):
        ...

    @abstractmethod
    def save(self, user) -> None:
        ...


class GuestProfileRepositoryInterface(ABC):
    """Port for guest profile persistence operations."""

    @abstractmethod
    def get_by_user(self, user):
        ...

    @abstractmethod
    def create(self, user, **profile_data):
        ...

    @abstractmethod
    def update(self, profile, **data):
        ...

    @abstractmethod
    def exists_for_user(self, user) -> bool:
        ...


class VerificationCodeRepositoryInterface(ABC):
    """Port for verification code persistence operations."""

    @abstractmethod
    def create(self, user, code: str, channel: str, purpose: str, expires_at):
        ...

    @abstractmethod
    def get_active_code(self, user, purpose: str, channel: str):
        """Return the latest non-expired, unused code for the user."""
        ...

    @abstractmethod
    def invalidate_codes(self, user, purpose: str, channel: str) -> None:
        """Mark all existing codes for this user/purpose/channel as used."""
        ...

    @abstractmethod
    def mark_used(self, code_obj) -> None:
        ...


class SocialAccountRepositoryInterface(ABC):
    """Port for social account persistence operations."""

    @abstractmethod
    def get_by_provider_uid(self, provider: str, provider_user_id: str):
        ...

    @abstractmethod
    def create(self, user, provider: str, provider_user_id: str, **extra):
        ...

    @abstractmethod
    def update_or_create(self, user, provider: str, provider_user_id: str, **extra):
        ...
