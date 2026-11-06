"""
Custom JWT Authentication for Cookie-based tokens

SECURITY:
- Reads JWT from HttpOnly cookies instead of Authorization header
- Prevents XSS attacks by keeping tokens out of JavaScript reach
- Falls back to Authorization header for API clients that need it
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication that reads tokens from HttpOnly cookies
    
    Priority:
    1. Read from 'access_token' cookie (most secure)
    2. Fall back to Authorization header (for API clients)
    """
    
    def authenticate(self, request):
        # Try to get token from cookie first (most secure)
        raw_token = request.COOKIES.get('access_token')
        
        # Fall back to Authorization header if no cookie
        if raw_token is None:
            header = self.get_header(request)
            if header is None:
                return None
            raw_token = self.get_raw_token(header)
        
        if raw_token is None:
            return None
        
        # Validate token
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
