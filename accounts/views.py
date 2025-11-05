# accounts/views.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.mail import send_mail
from rest_framework import generics, status, permissions, serializers
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import RegisterSerializer, UserSerializer, ChangePasswordSerializer, UserProfileSerializer
from .tokens import make_token, parse_token
from conf.utils.aws_utils import publish_to_sqs

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from conf.utils.aws_utils import upload_fileobj_to_s3
import pdb

User = get_user_model()


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_email_verified:
            raise serializers.ValidationError("Please verify your email before logging in.")
        data["user"] = UserSerializer(self.user).data
        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        token = make_token(user)
        activation_url = f"{settings.SITE_URL}{reverse('accounts:activate')}?token={token}"
        # subject = "Activate your account"
        # message = f"Click here to activate your account: {activation_url}"
        email_payload = {
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'to_emails': [user.email],
            'subject': "Activate your account",
            'message': f"Click here to activate your account: {activation_url}"
        }
        # pdb.set_trace()
        publish_to_sqs(email_payload)

        # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])


class ActivateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        data = parse_token(token)
        if not data:
            return Response({"detail": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(pk=data["user_id"])
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        user.is_active = True
        user.is_email_verified = True
        user.save()
        return Response({"detail": "Account activated"})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"detail": "Refresh token required"}, status=400)
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            return Response({"detail": "Invalid token"}, status=400)
        return Response(status=204)


class MyView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        data = request.data.copy()  # QueryDict -> mutable copy

        # If there's an avatar file in the request, upload it to S3 first
        avatar_file = request.FILES.get("avatar", None)
        if avatar_file:
            # Use a path that groups by user id
            key_prefix = f"avatars/{user.id}/"
            url, key = upload_fileobj_to_s3(avatar_file, key_prefix=key_prefix)
            # Put the S3 URL into the update payload
            data["avatar_url"] = url

            # Optional: If you want to store a local copy in avatar ImageField, you could:
            # user.avatar.save(avatar_file.name, avatar_file, save=False)
            # but typically we keep only avatar_url when using S3.

        serializer = self.get_serializer(user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


class MyProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data["old_password"]):
                return Response({"old_password": "Wrong password"}, status=400)
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return Response({"detail": "Password changed"})
        return Response(serializer.errors, status=400)
