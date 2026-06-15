# accounts/infrastructure/s3_storage.py
"""
S3 file-upload helper for the accounts domain (avatars, etc.).
Wraps the project-level aws_utils to keep infrastructure concerns
inside this layer.
"""
import logging

from conf.utils.aws_utils import upload_fileobj_to_s3

logger = logging.getLogger(__name__)


class S3StorageService:
    """Thin wrapper around the project S3 upload utility."""

    def upload_avatar(self, user_id: str, file_obj) -> str:
        """
        Upload an avatar image and return its public URL.
        """
        key_prefix = f"avatars/{user_id}/"
        url, _key = upload_fileobj_to_s3(file_obj, key_prefix=key_prefix)
        logger.info("Uploaded avatar for user %s → %s", user_id, url)
        return url

    def upload_file(self, key_prefix: str, file_obj) -> str:
        """
        Generic file upload returning the public URL.
        """
        url, _key = upload_fileobj_to_s3(file_obj, key_prefix=key_prefix)
        return url
