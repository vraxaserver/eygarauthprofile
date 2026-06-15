# accounts/views.py
"""
Thin API views — all business logic delegated to application services.
Views handle HTTP concerns: request parsing, response formatting, status codes.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView  # noqa: F401 — re-exported for URL wiring

from accounts.application.dto import (
    ForgotPasswordDTO,
    GuestProfileUpdateDTO,
    LoginDTO,
    RegisterDTO,
    ResendCodeDTO,
    ResetPasswordDTO,
    SocialAuthDTO,
    VerifyCodeDTO,
)
from accounts.application.services.auth_service import AuthService
from accounts.application.services.guest_profile_service import GuestProfileService
from accounts.application.services.password_service import PasswordService
from accounts.application.services.registration_service import RegistrationService
from accounts.application.services.social_auth_service import SocialAuthService
from accounts.application.services.verification_service import VerificationService
from accounts.domain.exceptions import DomainException
from accounts.serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    GuestProfileSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendCodeSerializer,
    ResetPasswordSerializer,
    SocialAuthSerializer,
    UserProfileSerializer,
    UserSerializer,
    VerifyCodeSerializer,
)
from conf.utils.aws_utils import upload_fileobj_to_s3

logger = logging.getLogger(__name__)
User = get_user_model()


def _error_response(exc: DomainException, http_status=status.HTTP_400_BAD_REQUEST):
    """Convert a DomainException to a DRF Response."""
    return Response(
        {'error': exc.message, 'code': exc.code},
        status=http_status,
    )


# ---------------------------------------------------------------------------
# Registration & Verification
# ---------------------------------------------------------------------------

class RegisterView(APIView):
    """POST /api/v1/auth/register/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = RegisterDTO(**serializer.validated_data)

        try:
            result = RegistrationService().register(dto)
        except DomainException as e:
            return _error_response(e)

        return Response(result, status=status.HTTP_201_CREATED)


class VerifyCodeView(APIView):
    """POST /api/v1/auth/verify/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyCodeSerializer

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = VerifyCodeDTO(**serializer.validated_data)

        try:
            result = VerificationService().verify_code(dto)
        except DomainException as e:
            return _error_response(e)

        return Response(result, status=status.HTTP_200_OK)


class ResendCodeView(APIView):
    """POST /api/v1/auth/verify/resend/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ResendCodeSerializer

    def post(self, request):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = ResendCodeDTO(**serializer.validated_data)

        try:
            result = VerificationService().resend_code(dto)
        except DomainException as e:
            return _error_response(e)

        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class LoginView(APIView):
    """POST /api/v1/auth/login/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = LoginDTO(**serializer.validated_data)

        try:
            result = AuthService().login(dto)
        except DomainException as e:
            return _error_response(e, http_status=status.HTTP_401_UNAUTHORIZED)

        return Response(result, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response(
                {'error': 'Refresh token required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            return Response(
                {'error': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Password Management
# ---------------------------------------------------------------------------

class ForgotPasswordView(APIView):
    """POST /api/v1/auth/password/forgot/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = ForgotPasswordDTO(**serializer.validated_data)

        try:
            result = PasswordService().forgot_password(dto)
        except DomainException as e:
            return _error_response(e)

        return Response(result, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    """POST /api/v1/auth/password/reset/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = ResetPasswordDTO(**serializer.validated_data)

        try:
            result = PasswordService().reset_password(dto)
        except DomainException as e:
            return _error_response(e)

        return Response(result, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """POST /api/v1/auth/password/change/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])

        return Response({'message': 'Password changed successfully.'})


# ---------------------------------------------------------------------------
# Social Auth
# ---------------------------------------------------------------------------

class SocialAuthView(APIView):
    """POST /api/v1/auth/social/login/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = SocialAuthSerializer

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dto = SocialAuthDTO(**serializer.validated_data)

        try:
            result = SocialAuthService().authenticate(dto)
        except DomainException as e:
            return _error_response(e, http_status=status.HTTP_401_UNAUTHORIZED)

        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# User / Profile
# ---------------------------------------------------------------------------

class MyView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/auth/me/"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        data = request.data.copy()

        # Handle avatar upload to S3
        avatar_file = request.FILES.get('avatar')
        if avatar_file:
            key_prefix = f"avatars/{user.id}/"
            url, _key = upload_fileobj_to_s3(avatar_file, key_prefix=key_prefix)
            data['avatar_url'] = url

        serializer = self.get_serializer(user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


class MyProfileView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/auth/profile/"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class GuestProfileView(APIView):
    """GET/PATCH /api/v1/auth/guest-profile/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            result = GuestProfileService().get_profile(request.user)
        except DomainException as e:
            return _error_response(e, http_status=status.HTTP_404_NOT_FOUND)

        return Response(result, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = GuestProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        dto = GuestProfileUpdateDTO(**serializer.validated_data)
        avatar_file = request.FILES.get('avatar')

        try:
            result = GuestProfileService().update_profile(
                user=request.user,
                dto=dto,
                avatar_file=avatar_file,
            )
        except DomainException as e:
            return _error_response(e)

        return Response(result, status=status.HTTP_200_OK)
