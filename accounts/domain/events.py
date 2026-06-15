# accounts/domain/events.py
"""
Domain event definitions for the auth/profile bounded context.
Each event is a simple dataclass capturing the facts of what happened.

Every event knows how to convert itself into the standard notification
envelope fields: template, variables, and recipient.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import uuid

from accounts.domain.notification_events import RecipientInfo
from accounts.domain.notification_templates import NotificationTemplate


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Subclasses override this with a NotificationTemplate constant
    template: str = ""

    @property
    def event_type(self) -> str:
        """Semantic event type used as the SNS MessageAttribute.

        Subclasses should override to return a stable, descriptive name
        (e.g. 'UserRegistration') rather than relying on the default
        class-name fallback.
        """
        return self.__class__.__name__

    def to_dict(self) -> dict:
        return asdict(self)

    def to_variables(self) -> dict:
        """Return template variables. Subclasses can override for custom logic."""
        d = asdict(self)
        # Remove base fields that are not template variables
        d.pop('event_id', None)
        d.pop('timestamp', None)
        d.pop('template', None)
        return d

    def to_recipient(self) -> RecipientInfo:
        """Return recipient info. Subclasses override if they carry contact data."""
        return RecipientInfo()


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Published when a new user account is created (before verification)."""
    user_id: str = ""
    email: Optional[str] = None
    phone_number: Optional[str] = None
    otp: str = ""          # Verification code included in the notification
    template: str = NotificationTemplate.SIGNUP_OTP

    @property
    def event_type(self) -> str:
        return "UserRegistration"

    def to_recipient(self) -> RecipientInfo:
        return RecipientInfo(
            email=self.email,
            phone=self.phone_number,
        )

    def to_variables(self) -> dict:
        return {
            'user_id': self.user_id,
            'otp': self.otp,
        }


@dataclass(frozen=True)
class GuestProfileCreated(DomainEvent):
    """Published when a guest profile is auto-created after verification."""
    user_id: str = ""
    guest_profile_id: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    template: str = "GUEST_PROFILE_CREATED"

    def to_recipient(self) -> RecipientInfo:
        return RecipientInfo(email=self.email, phone=self.phone)

    def to_variables(self) -> dict:
        return {
            'user_id': self.user_id,
            'guest_profile_id': self.guest_profile_id,
        }


@dataclass(frozen=True)
class UserVerified(DomainEvent):
    """Published when both email and phone are verified for a user."""
    user_id: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    email_verified: bool = False
    phone_verified: bool = False
    template: str = "USER_VERIFIED"

    def to_recipient(self) -> RecipientInfo:
        return RecipientInfo(email=self.email, phone=self.phone)

    def to_variables(self) -> dict:
        return {
            'user_id': self.user_id,
            'email_verified': self.email_verified,
            'phone_verified': self.phone_verified,
        }


@dataclass(frozen=True)
class HostProfileCreated(DomainEvent):
    """Published when a host profile is submitted for review."""
    user_id: str = ""
    host_profile_id: str = ""
    email: Optional[str] = None
    template: str = NotificationTemplate.HOST_PROFILE_SUBMITTED

    def to_recipient(self) -> RecipientInfo:
        return RecipientInfo(email=self.email)

    def to_variables(self) -> dict:
        return {
            'user_id': self.user_id,
            'host_profile_id': self.host_profile_id,
        }


@dataclass(frozen=True)
class HostProfileVerified(DomainEvent):
    """Published when an admin approves a host profile."""
    user_id: str = ""
    host_profile_id: str = ""
    email: Optional[str] = None
    template: str = NotificationTemplate.HOST_PROFILE_APPROVED

    def to_recipient(self) -> RecipientInfo:
        return RecipientInfo(email=self.email)

    def to_variables(self) -> dict:
        return {
            'user_id': self.user_id,
            'host_profile_id': self.host_profile_id,
        }


@dataclass(frozen=True)
class PasswordResetRequested(DomainEvent):
    """Published when a user requests a password reset."""
    user_id: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    channel: str = ""  # 'email' or 'phone'
    otp: str = ""     # Reset code included in the notification
    template: str = NotificationTemplate.PASSWORD_RESET_OTP

    @property
    def event_type(self) -> str:
        return "PasswordResetRequested"

    def to_recipient(self) -> RecipientInfo:
        return RecipientInfo(email=self.email, phone=self.phone)

    def to_variables(self) -> dict:
        return {
            'user_id': self.user_id,
            'channel': self.channel,
            'otp': self.otp,
        }
