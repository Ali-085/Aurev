"""
Email Verification Middleware

Optional middleware for SPA behavior: automatically rejects requests 
from unverified users with a 403 response.

USAGE OPTIONS:

Option 1: Use Permission Classes (Recommended)
----------------------------------------------
Apply IsEmailVerified permission per-view or globally in settings.py.
See users/permissions.py for details.

Option 2: Use This Middleware (Alternative)
------------------------------------------
Add to MIDDLEWARE in settings.py:

MIDDLEWARE = [
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'users.middleware.EmailVerificationMiddleware',  # Add after auth middleware
    ...
]

Configure exempt paths:

EMAIL_VERIFICATION_EXEMPT_PATHS = [
    '/api/auth/register/',
    '/api/auth/login/',
    '/api/auth/verify/',
    '/api/auth/resend-verification/',
    '/api/auth/refresh/',
    '/api/auth/logout/',
    '/admin/',
]

SECURITY:
- Checks is_active field for authenticated users
- Returns 403 JSON response for API requests
- Exempt paths allow registration/verification flow
- Logs unverified access attempts
"""

import logging
from django.http import JsonResponse
from django.conf import settings
from django.urls import resolve

logger = logging.getLogger(__name__)


class EmailVerificationMiddleware:
    """
    Middleware to enforce email verification for authenticated users.
    
    Checks if authenticated users have verified their email (is_active=True).
    If not, returns 403 with error_code for frontend handling.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Get exempt paths from settings
        self.exempt_paths = getattr(
            settings,
            'EMAIL_VERIFICATION_EXEMPT_PATHS',
            [
                '/api/auth/register/',
                '/api/auth/login/',
                '/api/auth/verify/',
                '/api/auth/resend-verification/',
                '/api/auth/refresh/',
                '/api/auth/logout/',
                '/admin/',
                '/api/docs/',
                '/api/schema/',
            ]
        )
    
    def __call__(self, request):
        """
        Process request and check email verification status.
        """
        # Skip check for exempt paths
        if self._is_exempt_path(request.path):
            return self.get_response(request)
        
        # Skip check for unauthenticated users
        if not request.user or not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip check for superusers
        if request.user.is_superuser:
            return self.get_response(request)
        
        # Check if user email is verified
        if not request.user.email_verified:
            # Log the attempt
            logger.warning(
                f"Unverified user blocked by middleware: {request.user.email} "
                f"(user_id: {request.user.pk}), path: {request.path}, "
                f"method: {request.method}"
            )
            
            # Return 403 with error code for API requests
            return JsonResponse(
                {
                    'detail': 'Account not verified. Please check your email for verification link.',
                    'error_code': 'EMAIL_NOT_VERIFIED',
                    'redirect_to': '/verify-notice'
                },
                status=403
            )
        
        # User is verified, continue processing
        response = self.get_response(request)
        return response
    
    def _is_exempt_path(self, path):
        """
        Check if the request path is exempt from verification check.
        
        Args:
            path (str): Request path
            
        Returns:
            bool: True if path is exempt, False otherwise
        """
        # Exact match
        if path in self.exempt_paths:
            return True
        
        # Prefix match (for paths with parameters)
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        
        return False
