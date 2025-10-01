# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from eygarprofile.serializers import EygarHostSerializer

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("email", "password", "password2", "avatar")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords don’t match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "avatar", "first_name", "last_name", "is_email_verified", "created_at", "updated_at")


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

class UserProfileSerializer(serializers.ModelSerializer):
    eygar_host = EygarHostSerializer(required=False, allow_null=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        # choose the fields you want to expose
        fields = (
            "id",
            "email",
            "username",
            "avatar_url",
            "is_email_verified",
            "is_staff",
            "is_superuser",
            "is_active",
            "created_at",
            "updated_at",
            "eygar_host",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_avatar_url(self, obj):
        if getattr(obj, "avatar", None):
            try:
                return obj.avatar.url
            except Exception:
                return None
        return None

    def update(self, instance, validated_data):
        # Update user basic fields
        host_data = validated_data.pop("eygar_host", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # handle eygar_host create/update
        if host_data is not None:
            host_obj = getattr(instance, "eygar_host", None)
            if host_obj:
                # update via EygarHostSerializer to reuse its logic
                serializer = EygarHostSerializer(instance=host_obj, data=host_data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
            else:
                # create host and nested relations
                host_data["user"] = instance
                serializer = EygarHostSerializer(data=host_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

        return instance