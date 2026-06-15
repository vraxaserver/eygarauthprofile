# accounts/domain/notification_templates.py
"""
Centralised registry of notification template identifiers.

Adding a new notification type requires only:
  1. Add a constant to NotificationTemplate.
  2. Add an entry to TEMPLATE_DEFAULTS.
  3. (In the Notification Service) create the actual template content.
"""


class NotificationTemplate:
    """String constants for every notification template."""

    # --- OTP / Verification ---
    SIGNUP_OTP = "SIGNUP_OTP"
    LOGIN_OTP = "LOGIN_OTP"
    EMAIL_VERIFICATION_OTP = "EMAIL_VERIFICATION_OTP"
    PHONE_VERIFICATION_OTP = "PHONE_VERIFICATION_OTP"
    PASSWORD_RESET_OTP = "PASSWORD_RESET_OTP"

    # --- Host Profile ---
    HOST_PROFILE_SUBMITTED = "HOST_PROFILE_SUBMITTED"
    HOST_PROFILE_APPROVED = "HOST_PROFILE_APPROVED"
    HOST_PROFILE_REJECTED = "HOST_PROFILE_REJECTED"
    HOST_PROFILE_STATUS_UPDATE = "HOST_PROFILE_STATUS_UPDATE"

    # --- Domain Events ---
    GUEST_PROFILE_CREATED = "GUEST_PROFILE_CREATED"
    USER_VERIFIED = "USER_VERIFIED"

    # --- Transactional ---
    WELCOME_EMAIL = "WELCOME_EMAIL"
    GENERIC_TRANSACTIONAL = "GENERIC_TRANSACTIONAL"

    # --- Future ---
    BOOKING_CONFIRMATION = "BOOKING_CONFIRMATION"
    PAYMENT_CONFIRMATION = "PAYMENT_CONFIRMATION"
    PAYMENT_FAILED = "PAYMENT_FAILED"


# Default channels per template.
# Services can override channels when they have more context
# (e.g., a phone-only user should not get EMAIL).
TEMPLATE_DEFAULTS: dict[str, dict] = {
    # OTP templates — dual-channel by default
    NotificationTemplate.SIGNUP_OTP: {
        "channels": ("SMS", "EMAIL"),
    },
    NotificationTemplate.LOGIN_OTP: {
        "channels": ("SMS", "EMAIL"),
    },
    NotificationTemplate.EMAIL_VERIFICATION_OTP: {
        "channels": ("EMAIL",),
    },
    NotificationTemplate.PHONE_VERIFICATION_OTP: {
        "channels": ("SMS",),
    },
    NotificationTemplate.PASSWORD_RESET_OTP: {
        "channels": ("SMS", "EMAIL"),
    },

    # Host profile templates — email only
    NotificationTemplate.HOST_PROFILE_SUBMITTED: {
        "channels": ("EMAIL",),
    },
    NotificationTemplate.HOST_PROFILE_APPROVED: {
        "channels": ("EMAIL",),
    },
    NotificationTemplate.HOST_PROFILE_REJECTED: {
        "channels": ("EMAIL",),
    },
    NotificationTemplate.HOST_PROFILE_STATUS_UPDATE: {
        "channels": ("EMAIL",),
    },

    # Domain event templates
    NotificationTemplate.GUEST_PROFILE_CREATED: {
        "channels": ("EMAIL",),
    },
    NotificationTemplate.USER_VERIFIED: {
        "channels": ("EMAIL",),
    },

    # Generic transactional — email only
    NotificationTemplate.WELCOME_EMAIL: {
        "channels": ("EMAIL",),
    },
    NotificationTemplate.GENERIC_TRANSACTIONAL: {
        "channels": ("EMAIL",),
    },

    # Future templates
    NotificationTemplate.BOOKING_CONFIRMATION: {
        "channels": ("SMS", "EMAIL"),
    },
    NotificationTemplate.PAYMENT_CONFIRMATION: {
        "channels": ("EMAIL",),
    },
    NotificationTemplate.PAYMENT_FAILED: {
        "channels": ("SMS", "EMAIL"),
    },
}


def get_template_defaults(template: str) -> dict:
    """
    Look up default channels for a template.

    Returns a dict with 'channels' (tuple).
    Falls back to single-channel EMAIL if unknown.
    """
    return TEMPLATE_DEFAULTS.get(template, {
        "channels": ("EMAIL",),
    })
