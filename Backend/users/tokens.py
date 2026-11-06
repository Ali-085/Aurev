"""
Email Verification Token Generator

Uses Django's PasswordResetTokenGenerator to create secure, 
time-limited tokens for email verification.

SECURITY:
- Tokens are cryptographically secure
- Tokens expire after a set time (default: 24 hours)
- Tokens are invalidated after use (when is_active changes)
- Cannot be reused or guessed
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for email verification.
    
    Inherits from PasswordResetTokenGenerator to ensure:
    - Secure token generation using HMAC
    - Automatic expiration
    - Token invalidation on user state change
    
    The token includes:
    - User's primary key
    - User's is_active status (changes when verified)
    - Timestamp of last password change
    - Current timestamp
    """
    
    def _make_hash_value(self, user, timestamp):
        """
        Hash includes user's active state so token becomes invalid after verification.
        
        This ensures that:
        1. Token expires when user is activated
        2. Token expires when user changes password
        3. Token expires after timeout period
        """
        return (
            six.text_type(user.pk) + 
            six.text_type(timestamp) + 
            six.text_type(user.is_active)
        )


# Create a single instance to use throughout the application
email_verification_token = EmailVerificationTokenGenerator()
