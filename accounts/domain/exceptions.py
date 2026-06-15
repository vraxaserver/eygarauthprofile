# accounts/domain/exceptions.py
"""
Domain-specific exceptions for the auth/profile bounded context.
Each maps to a clear business rule violation.
"""


class DomainException(Exception):
    """Base exception for all domain errors."""
    default_message = "A domain error occurred."
    default_code = "domain_error"

    def __init__(self, message: str | None = None, code: str | None = None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)


class UserAlreadyExistsError(DomainException):
    default_message = "A user with this email or phone number already exists."
    default_code = "user_already_exists"


class UserNotFoundError(DomainException):
    default_message = "No user found with the provided credentials."
    default_code = "user_not_found"


class UserNotActiveError(DomainException):
    default_message = "This account has not been verified. Please verify your account first."
    default_code = "user_not_active"


class InvalidCredentialsError(DomainException):
    default_message = "Invalid email/phone or password."
    default_code = "invalid_credentials"


class PasswordMismatchError(DomainException):
    default_message = "Passwords do not match."
    default_code = "password_mismatch"


class InvalidVerificationCodeError(DomainException):
    default_message = "The verification code is invalid."
    default_code = "invalid_verification_code"


class VerificationCodeExpiredError(DomainException):
    default_message = "The verification code has expired. Please request a new one."
    default_code = "verification_code_expired"


class SocialAuthError(DomainException):
    default_message = "Social authentication failed."
    default_code = "social_auth_error"


class InvalidInputError(DomainException):
    default_message = "The provided input is invalid."
    default_code = "invalid_input"


class ProfileNotFoundError(DomainException):
    default_message = "Profile not found."
    default_code = "profile_not_found"
