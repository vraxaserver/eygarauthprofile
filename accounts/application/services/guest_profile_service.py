# accounts/application/services/guest_profile_service.py
"""
Handles guest profile CRUD operations.
"""
import logging

from accounts.application.dto import GuestProfileUpdateDTO
from accounts.domain.exceptions import ProfileNotFoundError
from accounts.infrastructure.repositories import GuestProfileRepository
from accounts.infrastructure.s3_storage import S3StorageService

logger = logging.getLogger(__name__)


class GuestProfileService:

    def __init__(self, profile_repo=None, s3_storage=None):
        self.profile_repo = profile_repo or GuestProfileRepository()
        self.s3 = s3_storage or S3StorageService()

    def get_profile(self, user) -> dict:
        """
        Retrieve the guest profile for a user.
        """
        profile = self.profile_repo.get_by_user(user)
        if not profile:
            raise ProfileNotFoundError("Guest profile not found. Please complete verification first.")

        return self._profile_to_dict(profile)

    def update_profile(self, user, dto: GuestProfileUpdateDTO, avatar_file=None) -> dict:
        """
        Update guest profile fields and optionally upload a new avatar.
        """
        profile = self.profile_repo.get_by_user(user)
        if not profile:
            raise ProfileNotFoundError("Guest profile not found.")

        # Handle avatar upload
        if avatar_file:
            avatar_url = self.s3.upload_avatar(str(user.id), avatar_file)
            dto.avatar_url = avatar_url

        # Build update dict from non-None DTO fields
        update_data = {}
        for field_name in [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'nationality', 'email', 'phone_number', 'avatar_url',
            'preferred_language', 'bio',
        ]:
            value = getattr(dto, field_name, None)
            if value is not None:
                update_data[field_name] = value

        if update_data:
            profile = self.profile_repo.update(profile, **update_data)

        logger.info("Guest profile updated for user %s", user.id)

        return self._profile_to_dict(profile)

    def _profile_to_dict(self, profile) -> dict:
        return {
            'id': str(profile.id),
            'user_id': str(profile.user_id),
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'date_of_birth': str(profile.date_of_birth) if profile.date_of_birth else None,
            'gender': profile.gender,
            'nationality': profile.nationality,
            'email': profile.email,
            'phone_number': profile.phone_number,
            'avatar_url': profile.avatar_url,
            'preferred_language': profile.preferred_language,
            'bio': profile.bio,
            'created_at': profile.created_at.isoformat() if profile.created_at else None,
            'updated_at': profile.updated_at.isoformat() if profile.updated_at else None,
        }
