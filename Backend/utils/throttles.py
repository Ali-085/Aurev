"""
Custom Throttles for API Rate Limiting

Provides rate limiting for sensitive operations to prevent abuse.
"""

from rest_framework.throttling import UserRateThrottle
from django.conf import settings


class ImageUploadThrottle(UserRateThrottle):
    """
    Rate limit for image uploads.
    
    Prevents:
    - DoS attacks via excessive uploads
    - Storage exhaustion
    - Bandwidth abuse
    
    Default: 10 uploads per hour per user
    
    Can be configured in settings.py:
        REST_FRAMEWORK = {
            'DEFAULT_THROTTLE_RATES': {
                'image_upload': '10/hour',
            }
        }
    """
    scope = 'image_upload'
    
    def allow_request(self, request, view):
        # Disable throttling in development mode
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)


class PayoutSubmissionThrottle(UserRateThrottle):
    """
    Rate limit for payout submissions.
    
    Prevents:
    - Spam submissions
    - System overload
    
    Default: 20 submissions per hour per user
    """
    scope = 'payout_submission'
    
    def allow_request(self, request, view):
        # Disable throttling in development mode
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)


class AdminActionThrottle(UserRateThrottle):
    """
    Rate limit for admin/moderator actions.
    
    Prevents:
    - Accidental mass operations
    - Compromised account abuse
    
    Default: 100 actions per minute per user
    """
    scope = 'admin_action'
    
    def allow_request(self, request, view):
        # Disable throttling in development mode
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)
