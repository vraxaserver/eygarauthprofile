# accounts/application/dto.py
"""
Data Transfer Objects for service inputs/outputs.
These decouple views from services and ensure type safety.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import date


@dataclass
class RegisterDTO:
    email_or_phone: str
    password: str
    confirm_password: str


@dataclass
class VerifyCodeDTO:
    email_or_phone: str
    code: str


@dataclass
class ResendCodeDTO:
    email_or_phone: str


@dataclass
class LoginDTO:
    email_or_phone: str
    password: str


@dataclass
class ForgotPasswordDTO:
    email_or_phone: str


@dataclass
class ResetPasswordDTO:
    email_or_phone: str
    code: str
    new_password: str
    confirm_password: str


@dataclass
class SocialAuthDTO:
    provider: str   # 'google' or 'facebook'
    access_token: str


@dataclass
class GuestProfileUpdateDTO:
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    preferred_language: Optional[str] = None
    bio: Optional[str] = None
