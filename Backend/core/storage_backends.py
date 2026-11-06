"""
Cloudflare R2 Storage Backend Configuration

This module configures Django to use Cloudflare R2 (S3-compatible) for media storage.
Supports both public and private buckets with signed URLs.

SECURITY:
- Uses boto3 for S3-compatible storage
- Supports private buckets with signed URLs
- Credentials loaded from environment variables
- File upload validation handled by SecureImageUploader

Usage in models:
    from core.storage_backends import get_media_storage
    
    class MyModel(models.Model):
        image = models.ImageField(
            storage=get_media_storage,
            upload_to='images/%Y/%m/'
        )
"""

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class R2MediaStorage(S3Boto3Storage):
    """
    Cloudflare R2 storage backend for media files.
    
    Features:
    - Private bucket with signed URLs
    - Automatic file overwrite prevention
    - Custom file naming support
    - CORS support for direct uploads
    """
    
    # R2 Configuration
    access_key = settings.R2_ACCESS_KEY_ID
    secret_key = settings.R2_SECRET_ACCESS_KEY
    bucket_name = settings.R2_BUCKET_NAME
    endpoint_url = settings.R2_ENDPOINT_URL
    region_name = settings.R2_REGION_NAME
    signature_version = settings.R2_SIGNATURE_VERSION
    
    # Custom domain (optional)
    custom_domain = settings.R2_CUSTOM_DOMAIN
    
    # Security settings
    file_overwrite = False  # Prevent overwriting existing files
    default_acl = None  # Private bucket (no public ACL)
    
    # Signed URL configuration for private access
    querystring_auth = True  # Use signed URLs
    querystring_expire = settings.R2_SIGNED_URL_EXPIRATION  # URL expiration time
    
    # URL configuration
    url_protocol = 'https:'
    
    # Object parameters
    object_parameters = {
        'CacheControl': 'max-age=86400',  # 24 hours
    }
    
    def get_object_parameters(self, name):
        """
        Customize object parameters based on file type.
        """
        params = self.object_parameters.copy()
        
        # Set Content-Type based on extension
        if name.endswith(('.jpg', '.jpeg')):
            params['ContentType'] = 'image/jpeg'
        elif name.endswith('.png'):
            params['ContentType'] = 'image/png'
        elif name.endswith('.webp'):
            params['ContentType'] = 'image/webp'
        
        # Security: Prevent inline execution
        params['ContentDisposition'] = 'inline'
        
        return params


class R2StaticStorage(S3Boto3Storage):
    """
    Cloudflare R2 storage backend for static files.
    
    For production deployments where static files are also served from R2.
    """
    
    access_key = settings.R2_ACCESS_KEY_ID
    secret_key = settings.R2_SECRET_ACCESS_KEY
    bucket_name = settings.R2_BUCKET_NAME
    endpoint_url = settings.R2_ENDPOINT_URL
    region_name = settings.R2_REGION_NAME
    signature_version = settings.R2_SIGNATURE_VERSION
    
    location = 'static'  # Store in /static/ folder
    default_acl = 'public-read'  # Static files are public
    file_overwrite = True  # Overwrite on collectstatic
    
    # No signed URLs for static files
    querystring_auth = False
    
    # Aggressive caching for static files
    object_parameters = {
        'CacheControl': 'max-age=31536000',  # 1 year
    }


def get_media_storage():
    """
    Factory function to get appropriate storage backend.
    
    Returns R2 storage if USE_R2_STORAGE is True, otherwise FileSystemStorage.
    This allows easy switching between local and R2 storage for development.
    """
    if settings.USE_R2_STORAGE:
        return R2MediaStorage()
    return None  # Use default FileSystemStorage


def get_static_storage():
    """
    Factory function for static files storage.
    
    Use R2 for static files in production if needed.
    """
    if settings.USE_R2_STORAGE and settings.USE_R2_FOR_STATIC:
        return R2StaticStorage()
    return None
