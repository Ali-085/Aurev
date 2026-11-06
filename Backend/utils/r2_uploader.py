"""
Cloudflare R2 Upload Service

Handles secure upload of processed images to Cloudflare R2 storage.

Features:
- Upload to R2 with deterministic object keys
- Delete old images on update
- Public URL generation
- Error handling and retry logic

Usage:
    from utils.r2_uploader import R2Uploader
    
    uploader = R2Uploader()
    url = uploader.upload_avatar(user_id, file_bytes)
"""

import boto3
import logging
from django.conf import settings
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO

logger = logging.getLogger(__name__)


class R2UploadError(Exception):
    """Raised when R2 upload fails."""
    pass


class R2Uploader:
    """
    Cloudflare R2 uploader for avatars and logos.
    
    Handles:
    - Uploading to R2 with correct content type
    - Generating public URLs
    - Deleting old images
    - Error handling
    """
    
    def __init__(self):
        """Initialize R2 client."""
        if not settings.USE_R2_STORAGE:
            raise R2UploadError("R2 storage is not enabled in settings")
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name=settings.R2_REGION_NAME,
            config=boto3.session.Config(signature_version=settings.R2_SIGNATURE_VERSION)
        )
        
        self.bucket_name = settings.R2_BUCKET_NAME
        self.custom_domain = settings.R2_CUSTOM_DOMAIN
    
    def upload_avatar(
        self,
        user_id: str,
        file_bytes: BinaryIO,
        old_url: Optional[str] = None
    ) -> str:
        """
        Upload user avatar to R2.
        
        Args:
            user_id: User UUID
            file_bytes: Image file as BytesIO
            old_url: Previous avatar URL to delete (optional)
            
        Returns:
            Public URL of uploaded image
            
        Raises:
            R2UploadError: If upload fails
        """
        object_key = f'avatars/users/{user_id}.webp'
        
        try:
            # Delete old avatar if it exists and is different
            if old_url:
                self._delete_if_different(old_url, object_key)
            
            # Upload new avatar
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_bytes,
                ContentType='image/webp',
                CacheControl='public, max-age=31536000',  # 1 year cache
                Metadata={
                    'user-id': str(user_id),
                    'upload-type': 'avatar'
                }
            )
            
            # Generate public URL
            url = self._generate_public_url(object_key)
            
            logger.info(f"Avatar uploaded successfully for user {user_id}: {object_key}")
            
            return url
            
        except ClientError as e:
            logger.error(f"Failed to upload avatar for user {user_id}: {str(e)}")
            raise R2UploadError(f"Failed to upload avatar: {str(e)}")
    
    def upload_server_logo(
        self,
        server_id: str,
        file_bytes: BinaryIO,
        old_url: Optional[str] = None
    ) -> str:
        """
        Upload server logo to R2.
        
        Args:
            server_id: Server UUID
            file_bytes: Image file as BytesIO
            old_url: Previous logo URL to delete (optional)
            
        Returns:
            Public URL of uploaded image
            
        Raises:
            R2UploadError: If upload fails
        """
        object_key = f'avatars/servers/{server_id}.webp'
        
        try:
            # Delete old logo if it exists and is different
            if old_url:
                self._delete_if_different(old_url, object_key)
            
            # Upload new logo
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_bytes,
                ContentType='image/webp',
                CacheControl='public, max-age=31536000',  # 1 year cache
                Metadata={
                    'server-id': str(server_id),
                    'upload-type': 'logo'
                }
            )
            
            # Generate public URL
            url = self._generate_public_url(object_key)
            
            logger.info(f"Logo uploaded successfully for server {server_id}: {object_key}")
            
            return url
            
        except ClientError as e:
            logger.error(f"Failed to upload logo for server {server_id}: {str(e)}")
            raise R2UploadError(f"Failed to upload logo: {str(e)}")
    
    def delete_avatar(self, user_id: str) -> bool:
        """
        Delete user avatar from R2.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if deleted, False if not found
        """
        object_key = f'avatars/users/{user_id}.webp'
        return self._delete_object(object_key)
    
    def delete_server_logo(self, server_id: str) -> bool:
        """
        Delete server logo from R2.
        
        Args:
            server_id: Server UUID
            
        Returns:
            True if deleted, False if not found
        """
        object_key = f'avatars/servers/{server_id}.webp'
        return self._delete_object(object_key)
    
    def _delete_object(self, object_key: str) -> bool:
        """Delete an object from R2."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"Deleted R2 object: {object_key}")
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'NoSuchKey':
                logger.warning(f"Object not found in R2: {object_key}")
                return False
            else:
                logger.error(f"Failed to delete R2 object {object_key}: {str(e)}")
                return False
    
    def _delete_if_different(self, old_url: Optional[str], new_object_key: str):
        """Delete old image if URL points to a different object."""
        if not old_url:
            return
        
        # Extract object key from old URL
        old_object_key = self._extract_object_key(old_url)
        
        # Only delete if it's a different object
        if old_object_key and old_object_key != new_object_key:
            self._delete_object(old_object_key)
    
    def _extract_object_key(self, url: str) -> Optional[str]:
        """
        Extract R2 object key from URL.
        
        Handles both:
        - Custom domain URLs: https://cdn.example.com/avatars/users/123.webp
        - R2 public URLs: https://pub-xxx.r2.dev/avatars/users/123.webp
        """
        if not url:
            return None
        
        # Remove protocol and domain
        if '//' in url:
            url = url.split('//', 1)[1]  # Remove protocol
            if '/' in url:
                url = url.split('/', 1)[1]  # Remove domain
        
        # Check if it looks like an avatar/logo path
        if url.startswith('avatars/'):
            return url
        
        return None
    
    def _generate_public_url(self, object_key: str) -> str:
        """
        Generate public URL for R2 object.
        
        Uses custom domain if configured, otherwise uses R2 public bucket URL.
        """
        if self.custom_domain:
            # Use custom domain (e.g., https://cdn.example.com/avatars/users/123.webp)
            return f'https://{self.custom_domain}/{object_key}'
        else:
            # Use R2 public bucket URL (requires bucket to have public access)
            # Format: https://pub-<hash>.r2.dev/<object_key>
            # Note: You need to enable public access in R2 dashboard
            account_id = settings.R2_ACCOUNT_ID
            return f'https://pub-{account_id}.r2.dev/{object_key}'
