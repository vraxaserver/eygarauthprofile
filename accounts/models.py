# accounts/models.py
import uuid
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Custom User Manager
# ---------------------------------------------------------------------------

class CustomUserManager(BaseUserManager):
    """
    Manager that supports creating users with either email or phone_number.
    """

    def create_user(self, email=None, phone_number=None, password=None, **extra_fields):
        if not email and not phone_number:
            raise ValueError("Either email or phone_number must be provided.")

        if email:
            email = self.normalize_email(email)

        # Derive a username for AbstractUser compatibility
        username = extra_fields.pop("username", None) or email or phone_number
        extra_fields.setdefault("is_active", False)

        user = self.model(
            email=email,
            phone_number=phone_number,
            username=username,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)
        extra_fields.setdefault("username", email)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email=email, password=password, **extra_fields)


# ---------------------------------------------------------------------------
# User Model
# ---------------------------------------------------------------------------

PHONE_REGEX = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be in the format: '+999999999'. Up to 15 digits allowed.",
)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- Contact identifiers ---
    email = models.EmailField(unique=True, null=True, blank=True)
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[PHONE_REGEX],
    )

    # --- Verification flags ---
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_host_verified = models.BooleanField(default=False)
    is_vendor_verified = models.BooleanField(default=False)

    # --- Media ---
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    avatar_url = models.URLField(null=True, blank=True)

    # --- Stripe ---
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # AbstractUser compatibility — username is not used for login
    username = models.CharField(max_length=150, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email or self.phone_number or str(self.id)

    @property
    def is_fully_verified(self) -> bool:
        """True when both email and phone are verified (if both are set)."""
        if self.email and self.phone_number:
            return self.is_email_verified and self.is_phone_verified
        # If only one contact method is set, that one must be verified.
        if self.email:
            return self.is_email_verified
        if self.phone_number:
            return self.is_phone_verified
        return False


# ---------------------------------------------------------------------------
# Guest Profile
# ---------------------------------------------------------------------------

GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
    ('prefer_not_to_say', 'Prefer not to say'),
]


class GuestProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='guest_profile',
    )

    # --- Personal Information ---
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    nationality = models.CharField(max_length=100, blank=True)

    # --- Contact (mirrors from User, editable on profile) ---
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True, validators=[PHONE_REGEX])

    # --- Media ---
    avatar_url = models.URLField(blank=True)

    # --- Preferences ---
    preferred_language = models.CharField(max_length=10, default='en')
    bio = models.TextField(blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'guest_profiles'

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or str(self.user)


# ---------------------------------------------------------------------------
# Verification Code
# ---------------------------------------------------------------------------

class VerificationCode(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
    ]
    PURPOSE_CHOICES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
        ('email_verification', 'Email Verification'),
        ('phone_verification', 'Phone Verification'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=6)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'verification_codes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'purpose', 'channel', 'is_used']),
        ]

    def __str__(self):
        return f"{self.purpose}/{self.channel} code for {self.user}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired

    @staticmethod
    def generate_code(length: int = 6) -> str:
        return ''.join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def default_expiry(minutes: int | None = None) -> 'timezone.datetime':
        expiry_minutes = minutes or getattr(settings, 'VERIFICATION_CODE_EXPIRY_MINUTES', 10)
        return timezone.now() + timedelta(minutes=expiry_minutes)


# ---------------------------------------------------------------------------
# Password Reset Token
# ---------------------------------------------------------------------------

class PasswordResetToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Password reset for {self.user}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired


# ---------------------------------------------------------------------------
# Social Account
# ---------------------------------------------------------------------------

class SocialAccount(models.Model):
    PROVIDER_CHOICES = [
        ('google', 'Google'),
        ('facebook', 'Facebook'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'social_accounts'
        unique_together = [('provider', 'provider_user_id')]

    def __str__(self):
        return f"{self.provider} account for {self.user}"
