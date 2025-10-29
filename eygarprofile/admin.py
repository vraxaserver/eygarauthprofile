from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    EygarHost, BusinessProfile, IdentityVerification,
    ContactDetails, ReviewSubmission, ProfileStatusHistory,
    VendorProfile, CompanyDetails, ServiceArea, VendorContactDetails
)


class BusinessProfileInline(admin.StackedInline):
    model = BusinessProfile
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class IdentityVerificationInline(admin.StackedInline):
    model = IdentityVerification
    extra = 0
    readonly_fields = ('created_at', 'updated_at', 'verified_at')


class ContactDetailsInline(admin.StackedInline):
    model = ContactDetails
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class ReviewSubmissionInline(admin.StackedInline):
    model = ReviewSubmission
    extra = 0
    readonly_fields = ('submitted_at',)


class ProfileStatusHistoryInline(admin.TabularInline):
    model = ProfileStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'change_reason', 'created_at')


@admin.register(EygarHost)
class EygarHostAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'status', 'current_step', 'completion_percentage_display',
        'created_at', 'submitted_at', 'reviewed_at', 'actions_display'
    ]
    list_filter = [
        'status', 'current_step', 'business_profile_completed',
        'identity_verification_completed', 'contact_details_completed',
        'review_submission_completed', 'created_at'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = [
        'id', 'completion_percentage_display', 'created_at', 'updated_at', # Use the display method here too
        'submitted_at', 'reviewed_at'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'id', 'status', 'current_step')
        }),
        ('Progress Tracking', {
            'fields': (
                'business_profile_completed', 'identity_verification_completed',
                'contact_details_completed', 'review_submission_completed',
                'completion_percentage_display' # Use the display method for consistency
            )
        }),
        ('Review Information', {
            'fields': ('reviewer', 'review_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'submitted_at', 'reviewed_at'),
            'classes': ('collapse',)
        })
    )

    # Assuming these inlines are defined in your project
    # inlines = [
    #     BusinessProfileInline,
    #     IdentityVerificationInline,
    #     ContactDetailsInline,
    #     ReviewSubmissionInline,
    #     ProfileStatusHistoryInline
    # ]

    actions = ['approve_profiles', 'reject_profiles', 'mark_pending']

    def completion_percentage_display(self, obj):
        percentage = obj.completion_percentage
        if percentage == 100:
            color = 'green'
        elif percentage >= 50:
            color = 'orange'
        else:
            color = 'red'

        # --- FIX: Use format_html to mark the output as safe HTML ---
        return format_html(
            '<span style="font-weight: bold; color: {};">{}%</span>',
            color,
            f"{percentage:.1f}" # Format to one decimal place for consistency
        )

    completion_percentage_display.short_description = 'Completion'
    # Note: admin_order_field cannot be used on a property that relies on multiple fields.
    # To make this sortable, you'd need to use a queryset annotation.
    # completion_percentage_display.admin_order_field = 'completion_percentage'

    def actions_display(self, obj):
        if obj.status == 'submitted':
            change_url = reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk])
            return format_html(
                '<a class="button" href="{}">Review</a>',
                change_url
            )
        return '—' # Use an em dash for better visual alignment

    actions_display.short_description = 'Actions'

    # --- BUG FIX in Admin Actions ---

    def approve_profiles(self, request, queryset):
        # First, prepare history objects by capturing the CURRENT state
        history_entries = [
            ProfileStatusHistory(
                eygar_host=host,
                old_status=host.status,
                new_status='approved',
                changed_by=request.user,
                change_reason='Approved via admin bulk action'
            )
            for host in queryset
        ]

        # Then, perform the bulk update
        updated_count = queryset.update(status='approved', reviewer=request.user, reviewed_at=timezone.now())

        # Finally, create the history records
        ProfileStatusHistory.objects.bulk_create(history_entries)

        self.message_user(request, f'{updated_count} profiles approved successfully.')

    approve_profiles.short_description = 'Approve selected profiles'

    def reject_profiles(self, request, queryset):
        history_entries = [
            ProfileStatusHistory(
                eygar_host=host,
                old_status=host.status,
                new_status='rejected',
                changed_by=request.user,
                change_reason='Rejected via admin bulk action'
            )
            for host in queryset
        ]

        updated_count = queryset.update(status='rejected', reviewer=request.user, reviewed_at=timezone.now())
        ProfileStatusHistory.objects.bulk_create(history_entries)

        self.message_user(request, f'{updated_count} profiles rejected.')

    reject_profiles.short_description = 'Reject selected profiles'

    def mark_pending(self, request, queryset):
        history_entries = [
            ProfileStatusHistory(
                eygar_host=host,
                old_status=host.status,
                new_status='pending',
                changed_by=request.user,
                change_reason='Marked as pending via admin bulk action'
            )
            for host in queryset
        ]

        updated_count = queryset.update(status='pending')
        ProfileStatusHistory.objects.bulk_create(history_entries)

        self.message_user(request, f'{updated_count} profiles marked as pending.')

    mark_pending.short_description = 'Mark as pending'


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = [
        'business_name', 'eygar_host_user', 'license_number',
        'business_city', 'business_state', 'created_at'
    ]
    list_filter = ['business_type', 'business_city', 'business_state', 'business_country', 'created_at']
    search_fields = [
        'business_name', 'license_number', 'eygar_host__user__username',
        'business_city', 'business_state'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Business Information', {
            'fields': ('eygar_host', 'business_name', 'business_type', 'business_description')
        }),
        ('License Details', {
            'fields': ('license_number', 'license_document')
        }),
        ('Business Address', {
            'fields': (
                'business_address_line1', 'business_address_line2',
                'business_city', 'business_state', 'business_postal_code', 'business_country'
            )
        }),
        ('Media', {
            'fields': ('business_logo',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def eygar_host_user(self, obj):
        return obj.eygar_host.user.username

    eygar_host_user.short_description = 'User'


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = [
        'eygar_host_user', 'document_type', 'document_number',
        'verification_status', 'full_name', 'verified_at'
    ]
    list_filter = ['document_type', 'verification_status', 'created_at', 'verified_at']
    search_fields = [
        'eygar_host__user__username', 'document_number', 'full_name', 'fathers_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'verified_at']

    fieldsets = (
        ('Profile Information', {
            'fields': ('eygar_host',)
        }),
        ('Document Information', {
            'fields': ('document_type', 'document_number', 'document_image_front', 'document_image_back')
        }),
        ('Verification Status', {
            'fields': ('verification_status', 'verification_notes', 'verified_at')
        }),
        ('Extracted Information', {
            'fields': (
                'full_name', 'fathers_name', 'date_of_birth',
                'id_address_line1', 'id_address_line2', 'id_city',
                'id_state', 'id_postal_code', 'id_country'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def eygar_host_user(self, obj):
        return obj.eygar_host.user.username

    eygar_host_user.short_description = 'User'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj and obj.verification_status == 'verified':
            # Make extracted fields readonly if already verified
            readonly_fields.extend([
                'full_name', 'fathers_name', 'date_of_birth',
                'id_address_line1', 'id_address_line2', 'id_city',
                'id_state', 'id_postal_code', 'id_country'
            ])
        return readonly_fields


@admin.register(ContactDetails)
class ContactDetailsAdmin(admin.ModelAdmin):
    list_display = [
        'eygar_host_user', 'mobile_number', 'mobile_verified',
        'city', 'country', 'created_at'
    ]
    list_filter = [
        'mobile_verified', 'whatsapp_verified', 'telegram_verified',
        'facebook_verified', 'email_verified', 'city', 'country', 'created_at'
    ]
    search_fields = [
        'eygar_host__user__username', 'mobile_number', 'whatsapp_number',
        'telegram_username', 'city', 'country'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Profile Information', {
            'fields': ('eygar_host',)
        }),
        ('Address Information', {
            'fields': (
                'address_line1', 'address_line2', 'city', 'state',
                'postal_code', 'country', 'latitude', 'longitude'
            )
        }),
        ('Contact Information', {
            'fields': (
                ('mobile_number', 'mobile_verified'),
                ('whatsapp_number', 'whatsapp_verified'),
                ('telegram_username', 'telegram_verified'),
                ('facebook_page_url', 'facebook_verified'),
                'email_verified'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def eygar_host_user(self, obj):
        return obj.eygar_host.user.username

    eygar_host_user.short_description = 'User'


@admin.register(ReviewSubmission)
class ReviewSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'eygar_host_user', 'eygar_host_status', 'terms_accepted',
        'privacy_policy_accepted', 'submitted_at'
    ]
    list_filter = ['terms_accepted', 'privacy_policy_accepted', 'submitted_at']
    search_fields = ['eygar_host__user__username', 'additional_notes']
    readonly_fields = ['submitted_at']

    fieldsets = (
        ('Profile Information', {
            'fields': ('eygar_host',)
        }),
        ('Submission Details', {
            'fields': ('additional_notes', 'terms_accepted', 'privacy_policy_accepted')
        }),
        ('Timestamps', {
            'fields': ('submitted_at',)
        })
    )

    def eygar_host_user(self, obj):
        return obj.eygar_host.user.username

    eygar_host_user.short_description = 'User'

    def eygar_host_status(self, obj):
        return obj.eygar_host.status

    eygar_host_status.short_description = 'Profile Status'


@admin.register(ProfileStatusHistory)
class ProfileStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'eygar_host_user', 'old_status', 'new_status',
        'changed_by', 'created_at'
    ]
    list_filter = ['old_status', 'new_status', 'created_at']
    search_fields = [
        'eygar_host__user__username', 'changed_by__username',
        'change_reason'
    ]
    readonly_fields = ['created_at']

    fieldsets = (
        ('Profile Information', {
            'fields': ('eygar_host',)
        }),
        ('Status Change', {
            'fields': ('old_status', 'new_status', 'changed_by', 'change_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )

    def eygar_host_user(self, obj):
        return obj.eygar_host.user.username

    eygar_host_user.short_description = 'User'

    def has_add_permission(self, request):
        # Prevent manual creation of status history
        return False

    def has_change_permission(self, request, obj=None):
        # Make status history read-only
        return False


@admin.register(CompanyDetails)
class CompanyDetailsAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'vendor_profile_user')
    search_fields = ('company_name', 'vendor_profile__user__username')

    def vendor_profile_user(self, obj):
        return obj.vendor_profile.user
    vendor_profile_user.short_description = 'User'

@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ('city', 'state', 'country', 'vendor_profile_user')
    search_fields = ('city', 'state', 'country', 'vendor_profile__user__username')

    def vendor_profile_user(self, obj):
        return obj.vendor_profile.user
    vendor_profile_user.short_description = 'User'

@admin.register(VendorContactDetails)
class VendorContactDetailsAdmin(admin.ModelAdmin):
    list_display = ('primary_contact_email', 'primary_contact_phone', 'vendor_profile_user')
    search_fields = ('primary_contact_email', 'primary_contact_phone', 'vendor_profile__user__username')

    def vendor_profile_user(self, obj):
        return obj.vendor_profile.user
    vendor_profile_user.short_description = 'User'

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for the VendorProfile model.
    """
    list_display = (
        'user',
        'get_company_name',
        'status',
        'submitted_at',
        'company_details_completed',
        'service_area_completed',
        'contact_details_completed'
    )
    list_filter = ('status', 'submitted_at')
    search_fields = ('user__username', 'user__email', 'company_details__company_name')
    list_editable = ('status',)

    readonly_fields = ('user', 'submitted_at', 'created_at', 'updated_at')

    fieldsets = (
        ('Profile Information', {
            'fields': ('user', 'get_company_name')
        }),
        ('Completion Status', {
            'fields': ('company_details_completed', 'service_area_completed', 'contact_details_completed')
        }),
        ('Status and Timestamps', {
            'fields': ('status', 'submitted_at', 'created_at', 'updated_at')
        }),
    )

    actions = ['approve_vendors', 'reject_vendors']

    def get_company_name(self, obj):
        # Safely get the company name from the related CompanyDetails model
        try:
            return obj.company_details.company_name
        except CompanyDetails.DoesNotExist:
            return "N/A"
    get_company_name.short_description = 'Company Name'

    def send_status_update_email(self, request, queryset, new_status):
        """
        Sends an email notification to users about their vendor profile status update.
        """
        for profile in queryset:
            subject = f"Your Vendor Profile has been {new_status.title()}"
            message = f"""
            Hello {profile.user.first_name or profile.user.username},

            This is an update on your vendor profile submission.
            Your profile has been {new_status}.

            {'You can now access vendor features on our platform.' if new_status == 'approved' else 'Please review your profile details and resubmit if necessary.'}

            Thank you,
            The Admin Team
            """
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [profile.user.email],
                fail_silently=False,
            )

    def approve_vendors(self, request, queryset):
        """
        Admin action to approve selected vendor profiles.
        """
        updated_count = queryset.update(status='approved')
        self.message_user(request, f'{updated_count} vendor profiles have been approved.')
        self.send_status_update_email(request, queryset, 'approved')
    approve_vendors.short_description = "Approve selected vendors"

    def reject_vendors(self, request, queryset):
        """
        Admin action to reject selected vendor profiles.
        """
        updated_count = queryset.update(status='rejected')
        self.message_user(request, f'{updated_count} vendor profiles have been rejected.')
        self.send_status_update_email(request, queryset, 'rejected')
    reject_vendors.short_description = "Reject selected vendors"
