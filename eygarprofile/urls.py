from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EygarHostViewSet, 
    AdminReviewViewSet,
    MobileVerificationView,
    VerifyMobileCodeView,
    EygarProfileViewSet
)

app_name = 'eygarprofile'

# Create router for viewsets
router = DefaultRouter()
router.register('hosts', EygarHostViewSet, basename='eygarhost')
router.register('', EygarProfileViewSet, basename='eygarprofile')

# router.register('vendors', EygarVendorViewSet, basename='eygarvendor')
router.register('admin/reviews', AdminReviewViewSet, basename='admin-review')

urlpatterns = [
    # Include router URLs
    path('profiles/', include(router.urls)),
    
    # Mobile verification endpoints
    path('verify/mobile/send/', MobileVerificationView.as_view(), name='send-mobile-verification'),
    path('verify/mobile/confirm/', VerifyMobileCodeView.as_view(), name='verify-mobile-code'),
    
    # Additional custom endpoints if needed
    # path('profiles/current/', EygarHostViewSet.as_view({'get': 'current'}), name='current-profile'),
]

# URL patterns will be:
# GET/POST /api/host-profile/profiles/ - List/Create host profile
# POST /api/host-profile/profiles/business_profile/ - Step 1: Business profile
# POST /api/host-profile/profiles/identity_verification/ - Step 2: Identity verification
# POST /api/host-profile/profiles/contact_details/ - Step 3: Contact details
# POST /api/host-profile/profiles/submit_for_review/ - Step 4: Submit for review
# GET /api/host-profile/profiles/current_step/ - Get current step info

# Admin URLs:
# GET /api/host-profile/admin/reviews/ - List profiles for review
# GET /api/host-profile/admin/reviews/{id}/ - Get specific profile for review
# POST /api/host-profile/admin/reviews/{id}/review/ - Review and update status

# Verification URLs:
# POST /api/host-profile/verify/mobile/send/ - Send mobile verification code
# POST /api/host-profile/verify/mobile/confirm/ - Verify mobile code