# admin.py
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, Permission
from django import forms
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from accounts.models import GuestProfile, VerificationCode, PasswordResetToken, SocialAccount

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "phone_number", "username", "avatar", "is_staff", "is_superuser", "is_active")


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = (
        "id",
        "email",
        "phone_number",
        "username",
        "is_staff",
        "is_superuser",
        "is_active",
        "is_email_verified",
        "is_phone_verified",
        "is_host_verified",
        "stripe_customer_id",
        "created_at",
    )
    list_filter = (
        "is_staff", "is_superuser", "is_active",
        "is_email_verified", "is_phone_verified", "is_host_verified",
        "groups",
    )
    search_fields = ("email", "phone_number", "username")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "phone_number", "username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "avatar", "avatar_url", "avatar_preview", "stripe_customer_id")}),
        (_("Verification"), {"fields": ("is_email_verified", "is_phone_verified", "is_host_verified", "is_vendor_verified")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("last_login", "created_at", "updated_at", "avatar_preview")

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "phone_number", "username", "password1", "password2", "is_staff", "is_superuser", "is_active"),
        }),
    )

    filter_horizontal = ("groups", "user_permissions")

    actions = [
        "make_staff",
        "remove_staff",
        "make_superuser",
        "remove_superuser",
        "activate_users",
        "deactivate_users",
        "verify_email",
        "unverify_email",
        "verify_phone",
    ]

    def avatar_preview(self, obj):
        if obj and getattr(obj, "avatar", None):
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 80px; border-radius: 6px;" />',
                obj.avatar.url,
            )
        if obj and obj.avatar_url:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 80px; border-radius: 6px;" />',
                obj.avatar_url,
            )
        return "(no avatar)"
    avatar_preview.short_description = "Avatar preview"

    # ---------------------
    # Bulk action methods
    # ---------------------
    @admin.action(description="Make selected users staff")
    def make_staff(self, request, queryset):
        updated = queryset.update(is_staff=True)
        self.message_user(request, f"{updated} user(s) were marked as staff.", messages.SUCCESS)

    @admin.action(description="Remove staff status from selected users")
    def remove_staff(self, request, queryset):
        updated = queryset.update(is_staff=False)
        self.message_user(request, f"{updated} user(s) staff rights removed.", messages.SUCCESS)

    @admin.action(description="Make selected users superusers")
    def make_superuser(self, request, queryset):
        # Be careful: making superusers grants full rights
        updated = queryset.update(is_superuser=True, is_staff=True)
        self.message_user(request, f"{updated} user(s) were promoted to superuser.", messages.WARNING)

    @admin.action(description="Remove superuser status from selected users")
    def remove_superuser(self, request, queryset):
        updated = queryset.update(is_superuser=False)
        self.message_user(request, f"{updated} user(s) removed superuser status.", messages.SUCCESS)

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) were activated.", messages.SUCCESS)

    @admin.action(description="Deactivate selected users")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) were deactivated.", messages.WARNING)

    @admin.action(description="Mark selected users' email as verified")
    def verify_email(self, request, queryset):
        updated = queryset.update(is_email_verified=True)
        self.message_user(request, f"{updated} user(s) email marked as verified.", messages.SUCCESS)

    @admin.action(description="Unmark selected users' email as verified")
    def unverify_email(self, request, queryset):
        updated = queryset.update(is_email_verified=False)
        self.message_user(request, f"{updated} user(s) email marked as unverified.", messages.WARNING)

    @admin.action(description="Mark selected users' phone as verified")
    def verify_phone(self, request, queryset):
        updated = queryset.update(is_phone_verified=True)
        self.message_user(request, f"{updated} user(s) phone marked as verified.", messages.SUCCESS)


# ---------------------------------------------------------------------------
# Guest Profile Admin
# ---------------------------------------------------------------------------

@admin.register(GuestProfile)
class GuestProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "first_name", "last_name", "email", "phone_number", "created_at")
    search_fields = ("first_name", "last_name", "email", "phone_number", "user__email")
    list_filter = ("gender", "preferred_language")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user",)


# ---------------------------------------------------------------------------
# Verification Code Admin (read-only for debugging)
# ---------------------------------------------------------------------------

@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "code", "channel", "purpose", "is_used", "expires_at", "created_at")
    search_fields = ("user__email", "user__phone_number", "code")
    list_filter = ("channel", "purpose", "is_used")
    readonly_fields = ("id", "user", "code", "channel", "purpose", "is_used", "expires_at", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Password Reset Token Admin (read-only for debugging)
# ---------------------------------------------------------------------------

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "code", "is_used", "expires_at", "created_at")
    search_fields = ("user__email", "user__phone_number")
    list_filter = ("is_used",)
    readonly_fields = ("id", "user", "code", "is_used", "expires_at", "created_at")
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Social Account Admin
# ---------------------------------------------------------------------------

@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "provider", "provider_user_id", "created_at")
    search_fields = ("user__email", "provider_user_id")
    list_filter = ("provider",)
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user",)


# Permission admin
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "codename", "content_type")
    search_fields = ("name", "codename")
    list_filter = ("content_type",)
    ordering = ("content_type__app_label", "content_type__model", "codename")
