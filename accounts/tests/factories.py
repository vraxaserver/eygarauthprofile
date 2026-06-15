# accounts/tests/factories.py
"""
Test helpers and factory functions for creating test fixtures.
"""
from django.contrib.auth import get_user_model
from accounts.models import GuestProfile, VerificationCode, PasswordResetToken, SocialAccount

User = get_user_model()


def create_user(
    email='test@example.com',
    phone_number=None,
    password='TestPass123!',
    is_active=False,
    is_email_verified=False,
    is_phone_verified=False,
    **kwargs,
):
    """Create a test user."""
    user = User(
        email=email,
        phone_number=phone_number,
        username=email or phone_number,
        is_active=is_active,
        is_email_verified=is_email_verified,
        is_phone_verified=is_phone_verified,
        **kwargs,
    )
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()
    return user


def create_active_user(email='active@example.com', **kwargs):
    """Create an active, email-verified user."""
    return create_user(
        email=email,
        is_active=True,
        is_email_verified=True,
        **kwargs,
    )


def create_guest_profile(user, **kwargs):
    """Create a guest profile for a user."""
    defaults = {
        'first_name': 'Test',
        'last_name': 'User',
        'email': user.email or '',
        'phone_number': user.phone_number or '',
    }
    defaults.update(kwargs)
    return GuestProfile.objects.create(user=user, **defaults)


def create_verification_code(user, code='123456', channel='email', purpose='registration', **kwargs):
    """Create a verification code."""
    return VerificationCode.objects.create(
        user=user,
        code=code,
        channel=channel,
        purpose=purpose,
        expires_at=kwargs.pop('expires_at', VerificationCode.default_expiry()),
        **kwargs,
    )


def create_password_reset_token(user, code='654321', **kwargs):
    """Create a password reset token."""
    from datetime import timedelta
    from django.utils import timezone
    return PasswordResetToken.objects.create(
        user=user,
        code=code,
        expires_at=kwargs.pop('expires_at', timezone.now() + timedelta(minutes=15)),
        **kwargs,
    )
