# accounts/serializers.py
"""
DRF serializers for the accounts app.
Thin validation layer — business logic lives in application services.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from accounts.models import GuestProfile

User = get_user_model()


# ---------------------------------------------------------------------------
# Registration & Verification
# ---------------------------------------------------------------------------

class RegisterSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': "Passwords don't match."})
        return attrs


class VerifyCodeSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Verification code must contain only digits.")
        return value


class ResendCodeSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class LoginSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


# ---------------------------------------------------------------------------
# Password Management
# ---------------------------------------------------------------------------

class ForgotPasswordSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
    )
    confirm_password = serializers.CharField(required=True)

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Reset code must contain only digits.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': "Passwords don't match."})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])


# ---------------------------------------------------------------------------
# Social Auth
# ---------------------------------------------------------------------------

class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'facebook'])
    access_token = serializers.CharField(required=True)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'email', 'phone_number', 'avatar_url',
            'first_name', 'last_name',
            'is_email_verified', 'is_phone_verified',
            'stripe_customer_id', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'email', 'phone_number',
            'is_email_verified', 'is_phone_verified',
            'stripe_customer_id', 'created_at', 'updated_at',
        )


# ---------------------------------------------------------------------------
# Guest Profile
# ---------------------------------------------------------------------------

class GuestProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestProfile
        fields = (
            'id', 'first_name', 'last_name', 'date_of_birth',
            'gender', 'nationality', 'email', 'phone_number',
            'avatar_url', 'preferred_language', 'bio',
            'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


# ---------------------------------------------------------------------------
# User Profile (combined User + Host + Vendor — backward compat)
# ---------------------------------------------------------------------------

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full profile view for the authenticated user.
    Keeps backward compatibility with existing eygar_host / vendor_profile nesting.
    """
    from eygarprofile.serializers import EygarHostSerializer, EygarVendorSerializer

    eygar_host = EygarHostSerializer(required=False, allow_null=True)
    eygar_vendor = EygarVendorSerializer(
        required=False, allow_null=True, source='vendor_profile',
    )
    guest_profile = GuestProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'phone_number', 'username',
            'first_name', 'last_name', 'avatar_url',
            'is_email_verified', 'is_phone_verified',
            'stripe_customer_id',
            'is_staff', 'is_superuser', 'is_active',
            'created_at', 'updated_at',
            'guest_profile', 'eygar_host', 'eygar_vendor',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def update(self, instance, validated_data):
        from eygarprofile.serializers import EygarHostSerializer

        host_data = validated_data.pop('eygar_host', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if host_data is not None:
            host_obj = getattr(instance, 'eygar_host', None)
            if host_obj:
                serializer = EygarHostSerializer(instance=host_obj, data=host_data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
            else:
                host_data['user'] = instance
                serializer = EygarHostSerializer(data=host_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

        return instance
