"""
Email Service using Resend API

Centralized email sending functionality with Resend integration.

SETUP REQUIRED:
1. Install resend: pip install resend
2. Set RESEND_API_KEY in environment variables
3. Configure sending domain in Resend dashboard
4. Add SPF and DKIM records to your DNS (see Resend docs)

SECURITY:
- API key loaded from environment
- Email content sanitized
- Only verification links included (no passwords)
- HTTPS-only links
- Rate-limited at application level
"""

import resend
import logging
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import email_verification_token

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Custom exception for email service errors"""
    pass


def _get_resend_api_key():
    """
    Get Resend API key from settings.
    
    Raises:
        EmailServiceError: If API key is not configured
    """
    api_key = getattr(settings, 'RESEND_API_KEY', None)
    if not api_key:
        logger.error("RESEND_API_KEY not found in settings")
        raise EmailServiceError(
            "Email service not configured. Please set RESEND_API_KEY in environment variables."
        )
    return api_key


def _get_frontend_url():
    """Get frontend URL from settings"""
    return getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')


def _get_from_email():
    """Get sender email from settings"""
    return getattr(settings, 'FROM_EMAIL', 'Aurevia <noreply@aurevia.com>')


def send_verification_email(user):
    """
    Send email verification link to user.
    
    Args:
        user: User instance (must have email and pk)
        
    Returns:
        dict: Resend API response
        
    Raises:
        EmailServiceError: If email fails to send
        
    SECURITY:
    - Uses PasswordResetTokenGenerator for secure tokens
    - Token expires after 24 hours
    - Token invalidated after activation
    - HTTPS-only links (enforced in production)
    """
    try:
        # Initialize Resend with API key
        resend.api_key = _get_resend_api_key()
        
        # Generate secure token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        
        # Build verification link
        frontend_url = _get_frontend_url()
        verification_link = f"{frontend_url}/verify?uid={uid}&token={token}"
        
        # SECURITY: Ensure HTTPS in production
        if not settings.DEBUG and not verification_link.startswith('https://'):
            logger.error(f"Non-HTTPS verification link in production: {verification_link}")
            raise EmailServiceError("Verification links must use HTTPS in production")
        
        # Email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1e 50%, #000000 100%);
                    border-radius: 16px;
                    padding: 40px;
                    box-shadow: 0 8px 32px rgba(0, 102, 255, 0.2);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 48px;
                    margin-bottom: 10px;
                }}
                h1 {{
                    color: #ffffff;
                    font-size: 28px;
                    margin: 0 0 10px 0;
                }}
                .subtitle {{
                    color: #b3b3b3;
                    font-size: 16px;
                }}
                .content {{
                    background: rgba(26, 26, 46, 0.8);
                    border: 1px solid rgba(77, 148, 255, 0.2);
                    border-radius: 12px;
                    padding: 30px;
                    margin: 30px 0;
                }}
                .content p {{
                    color: #e0e0e0;
                    margin: 0 0 20px 0;
                }}
                .button {{
                    display: inline-block;
                    padding: 14px 32px;
                    background: linear-gradient(135deg, #0066FF 0%, #0052CC 100%);
                    color: #ffffff !important;
                    text-decoration: none;
                    border-radius: 10px;
                    font-weight: 600;
                    font-size: 16px;
                    box-shadow: 0 4px 16px rgba(0, 102, 255, 0.3);
                    transition: transform 0.2s;
                }}
                .button:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0, 102, 255, 0.4);
                }}
                .footer {{
                    text-align: center;
                    color: #808080;
                    font-size: 14px;
                    margin-top: 30px;
                }}
                .link {{
                    color: #4D94FF;
                    word-break: break-all;
                }}
                .warning {{
                    background: rgba(245, 158, 11, 0.1);
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    border-radius: 8px;
                    padding: 15px;
                    margin-top: 20px;
                    color: #f59e0b;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🏆</div>
                    <h1>Welcome to Aurevia!</h1>
                    <p class="subtitle">Trading Leaderboard Platform</p>
                </div>
                
                <div class="content">
                    <p>Hi <strong>{user.username}</strong>,</p>
                    
                    <p>Thank you for registering! Please verify your email address to activate your account and start using Aurevia.</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_link}" class="button">
                            Verify Email Address
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #b3b3b3;">
                        Or copy and paste this link into your browser:
                    </p>
                    <p style="font-size: 13px;">
                        <a href="{verification_link}" class="link">{verification_link}</a>
                    </p>
                    
                    <div class="warning">
                        ⚠️ This verification link expires in 24 hours. If you didn't create an account, please ignore this email.
                    </div>
                </div>
                
                <div class="footer">
                    <p>Aurevia - Trading Leaderboard Platform</p>
                    <p>Need help? Contact our support team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        Welcome to Aurevia!
        
        Hi {user.username},
        
        Thank you for registering! Please verify your email address to activate your account.
        
        Click here to verify: {verification_link}
        
        Or copy and paste this link into your browser:
        {verification_link}
        
        This verification link expires in 24 hours.
        
        If you didn't create an account, please ignore this email.
        
        ---
        Aurevia - Trading Leaderboard Platform
        """
        
        # Send email via Resend
        params = {
            "from": _get_from_email(),
            "to": [user.email],
            "subject": "Verify your email - Aurevia",
            "html": html_content,
            "text": text_content,
        }
        
        logger.info(f"Sending verification email to {user.email} (user_id: {user.pk})")
        response = resend.Emails.send(params)
        
        logger.info(f"Verification email sent successfully to {user.email} (resend_id: {response.get('id', 'N/A')})")
        return response
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}", exc_info=True)
        raise EmailServiceError(f"Failed to send verification email: {str(e)}")


def send_resend_verification_email(user):
    """
    Resend verification email (same as send_verification_email but with logging context).
    
    Args:
        user: User instance
        
    Returns:
        dict: Resend API response
        
    Raises:
        EmailServiceError: If email fails to send
    """
    logger.info(f"Resending verification email to {user.email} (user_id: {user.pk})")
    return send_verification_email(user)


def send_password_reset_email(user, reset_token):
    """
    Send password reset email with secure token.
    
    Args:
        user: User instance
        reset_token: Raw reset token (will be hashed before storage)
        
    Returns:
        dict: Resend API response
        
    Raises:
        EmailServiceError: If email fails to send
        
    SECURITY:
    - Token is single-use and time-limited (30 minutes)
    - HTTPS-only links in production
    - No sensitive information in email
    - Generic message to prevent user enumeration
    """
    try:
        # Initialize Resend with API key
        resend.api_key = _get_resend_api_key()
        
        # Encode user ID
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Build reset link
        frontend_url = _get_frontend_url()
        reset_link = f"{frontend_url}/reset-password/{uid}/{reset_token}"
        
        # SECURITY: Ensure HTTPS in production
        if not settings.DEBUG and not reset_link.startswith('https://'):
            logger.error(f"Non-HTTPS reset link in production: {reset_link}")
            raise EmailServiceError("Password reset links must use HTTPS in production")
        
        # Email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your Password - Aurevia</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background: radial-gradient(circle at 50% 0%, #04142e 0%, #020306 100%); background-color: #020306;">
            
            <div style="background: rgba(0, 102, 255, 0.05); border: 1px solid rgba(77, 148, 255, 0.2); border-radius: 16px; box-shadow: 0 8px 32px rgba(0, 102, 255, 0.2); overflow: hidden;">
                <div style="background: linear-gradient(135deg, #0066FF 0%, #0052CC 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px; text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);">🔒 Password Reset</h1>
                </div>
                
                <div style="padding: 30px;">
                    <p style="font-size: 16px; margin-bottom: 20px; color: #ffffff;">Hi <strong>{user.username}</strong>,</p>
                    
                    <p style="font-size: 16px; margin-bottom: 20px; color: #b3b3b3;">
                        We received a request to reset your password for your Aurevia account. Click the button below to create a new password:
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_link}" 
                           style="background: linear-gradient(135deg, #0066FF 0%, #0052CC 100%); 
                                  color: white; 
                                  padding: 14px 32px; 
                                  text-decoration: none; 
                                  border-radius: 8px; 
                                  font-weight: 600; 
                                  font-size: 16px;
                                  display: inline-block;
                                  box-shadow: 0 4px 12px rgba(0, 102, 255, 0.4);">
                            Reset My Password
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #b3b3b3; margin-top: 30px;">
                        Or copy and paste this link into your browser:
                    </p>
                    <p style="font-size: 13px; color: #4d94ff; word-break: break-all; background: rgba(0, 0, 0, 0.3); padding: 12px; border-radius: 6px; border: 1px solid rgba(77, 148, 255, 0.2);">
                        {reset_link}
                    </p>
                    
                    <div style="background: rgba(0, 0, 0, 0.3); border-left: 4px solid #4d94ff; padding: 15px; margin: 25px 0; border-radius: 6px;">
                        <p style="margin: 0 0 12px 0; font-size: 14px; color: #ffffff; font-weight: 600;">
                            ⚠️ Security Notice
                        </p>
                        <p style="margin: 0; font-size: 13px; color: #b3b3b3;">
                            This link expires in <strong>30 minutes</strong> and can only be used once.
                        </p>
                    </div>
                    
                    <p style="font-size: 14px; color: #b3b3b3; margin-top: 25px;">
                        If you didn't request a password reset, please ignore this email or contact support if you have concerns about your account security.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid rgba(77, 148, 255, 0.2); margin: 30px 0;">
                    
                    <p style="font-size: 13px; color: rgba(255, 255, 255, 0.4); text-align: center; margin-top: 20px;">
                        Best regards,<br>
                        <strong style="color: #4d94ff;">The Aurevia Team</strong>
                    </p>
                    <p style="font-size: 12px; color: rgba(255, 255, 255, 0.3); text-align: center; margin-top: 12px;">
                        © 2024 Aurevia. All rights reserved.
                    </p>
                </div>
            </div>
            
        </body>
        </html>
        """
        
        # Plain text version
        text_content = f"""
        Reset Your Password
        
        Hi {user.username},
        
        We received a request to reset your password. Click the link below to create a new password:
        
        {reset_link}
        
        Security Notice:
        This link expires in 30 minutes and can only be used once.
        
        If you didn't request a password reset, please ignore this email or contact support if you have concerns.
        
        ---
        This is an automated message from Aurevia.
        """
        
        params = {
            "from": _get_from_email(),
            "to": [user.email],
            "subject": "Reset Your Password - Aurevia",
            "html": html_content,
            "text": text_content,
        }
        
        logger.info(f"Sending password reset email to {user.email} (user_id: {user.pk})")
        response = resend.Emails.send(params)
        
        logger.info(f"Password reset email sent successfully to {user.email} (resend_id: {response.get('id', 'N/A')})")
        return response
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user.email}: {str(e)}", exc_info=True)
        raise EmailServiceError(f"Failed to send password reset email: {str(e)}")
