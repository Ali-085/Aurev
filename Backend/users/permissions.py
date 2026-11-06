"""Custom Permission Classes for Email Verification

SECURITY:
- Ensures users are email verified before accessing protected features
- Returns 403 with specific error code for unverified accounts
- Can be applied globally or per-view/viewset
"""

import logging
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


class IsEmailVerified(permissions.BasePermission):
    """
    Permission class that only allows access to users with verified email (email_verified=True).
    
    Usage:
        # In a view or viewset
        permission_classes = [permissions.IsAuthenticated, IsEmailVerified]
        
        # Or globally in settings.py:
        REST_FRAMEWORK = {
            'DEFAULT_PERMISSION_CLASSES': [
                'rest_framework.permissions.IsAuthenticated',
                'users.permissions.IsEmailVerified',
            ],
        }
    
    SECURITY:
    - Checks email_verified field (set to True after email verification)
    - Separate from is_active (which requires full onboarding/payment for server creators)
    - Returns 403 with error_code for frontend handling
    - Logs unverified access attempts
    """
    
    message = {
        'detail': 'Account not verified. Please check your email for verification link.',
        'error_code': 'EMAIL_NOT_VERIFIED'
    }
    
    def has_permission(self, request, view):
        """
        Check if user is authenticated and email is verified.
        
        Returns:
            bool: True if user has verified email, False otherwise
        """
        # Allow anonymous requests to pass through
        # (IsAuthenticated permission should handle auth check)
        if not request.user or not request.user.is_authenticated:
            return True
        
        # Check if email is verified
        if not request.user.email_verified:
            # Log the attempt
            logger.warning(
                f"Unverified user attempted access: {request.user.email} "
                f"(user_id: {request.user.pk}), path: {request.path}"
            )
            # Raise PermissionDenied with custom message
            raise PermissionDenied(self.message)
        
        return True


# Alias for backwards compatibility
EmailVerifiedPermission = IsEmailVerified
