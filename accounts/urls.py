# accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    RegisterView,
    VerifyCodeView,
    ResendCodeView,
    LoginView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    SocialAuthView,
    MyView,
    MyProfileView,
    GuestProfileView,
)

app_name = "accounts"

urlpatterns = [
    # --- Registration & Verification ---
    path("register/", RegisterView.as_view(), name="register"),
    path("verify/", VerifyCodeView.as_view(), name="verify_code"),
    path("verify/resend/", ResendCodeView.as_view(), name="resend_code"),

    # --- Authentication ---
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # --- Password Management ---
    path("password/forgot/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("password/reset/", ResetPasswordView.as_view(), name="reset_password"),
    path("password/change/", ChangePasswordView.as_view(), name="change_password"),

    # --- Social Auth ---
    path("social/login/", SocialAuthView.as_view(), name="social_login"),

    # --- User & Profile ---
    path("me/", MyView.as_view(), name="me"),
    path("profile/", MyProfileView.as_view(), name="my_profile"),
    path("guest-profile/", GuestProfileView.as_view(), name="guest_profile"),
]
