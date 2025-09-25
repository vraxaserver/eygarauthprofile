# accounts/urls.py
from django.urls import path
from .views import (
    RegisterView, ActivateView, MyTokenObtainPairView,
    LogoutView, MeView, MyProfileView, ChangePasswordView
)
from rest_framework_simplejwt.views import TokenRefreshView

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("activate/", ActivateView.as_view(), name="activate"),
    path("login/", MyTokenObtainPairView.as_view(), name="token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("profile/", MyProfileView.as_view(), name="auth_profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
]
