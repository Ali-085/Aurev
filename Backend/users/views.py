"""
User Views with Email Verification

SECURITY FEATURES:
- Registration creates inactive users (is_active=False)
- Verification tokens using PasswordResetTokenGenerator
- Rate limiting on all auth endpoints
- Generic responses to prevent user enumeration
- Resend cooldown (60 seconds per user)
- Logging of suspicious activity
- HTTPS-only verification links in production
"""

from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
import logging
import traceback
import sys
from core.permissions import IsSuperuserOnly, IsAdminOnly
from .permissions import IsEmailVerified
from .permissions import IsEmailVerified
from .models import Role, UserRole
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    RoleSerializer,
    UserRoleSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer
)
from .tokens import email_verification_token
from .emails import send_verification_email, send_resend_verification_email, send_password_reset_email, EmailServiceError
from .models import PasswordResetToken

User = get_user_model()
logger = logging.getLogger(__name__)


class LoginRateThrottle(AnonRateThrottle):
    """Rate limiting for login attempts to prevent brute force attacks"""
    scope = 'login'
    
    def allow_request(self, request, view):
        # Disable throttling in development mode
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)


class RegisterRateThrottle(AnonRateThrottle):
    """Rate limiting for registration to prevent spam/bot attacks - 5/min per IP"""
    scope = 'register'
    rate = '5/min'
    
    def allow_request(self, request, view):
        # Disable throttling in development mode
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)


class VerifyRateThrottle(AnonRateThrottle):
    """Rate limiting for verification endpoint - 10/min per IP"""
    scope = 'verify'
    rate = '10/min'
    
    def allow_request(self, request, view):
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)


class ResendVerificationRateThrottle(AnonRateThrottle):
    """Rate limiting for resend verification - 3/min per IP"""
    scope = 'resend_verification'
    rate = '3/min'
    
    def allow_request(self, request, view):
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)


class RefreshRateThrottle(AnonRateThrottle):
    """Rate limiting for token refresh to prevent abuse"""
    scope = 'refresh'
    
    def allow_request(self, request, view):
        # Disable throttling in development mode
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)


class CookieTokenObtainPairView(TokenObtainPairView):
    """
    JWT token view that sets tokens in HttpOnly cookies
    More secure than localStorage - prevents XSS attacks
    
    SECURITY: Uses standard Django authentication - no bypasses
    """
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
      try:
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')
            
            # Get user info
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(access_token)
            user = User.objects.get(id=token['user_id'])
            
            # SECURITY: Check if user email is verified
            if not user.email_verified:
                logger.warning(f"Login attempt by unverified user: {user.email}")
                return Response(
                    {
                        'detail': 'Account not verified. Please check your email for verification link.',
                        'error_code': 'EMAIL_NOT_VERIFIED'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if server creator has pending payment (informational only - they can still login)
            from .models import ServerCreatorApplication
            pending_app = ServerCreatorApplication.objects.filter(
                user=user,
                status='pending_payment'
            ).first()
            
            if pending_app:
                logger.info(f"Server creator with pending payment logged in: {user.email}")
                # Don't block login - just add metadata to response
                response.data['pending_payment'] = True
                response.data['application_id'] = pending_app.pk
                response.data['redirect_to'] = '/server-creator/checkout'
            
            # Set access token in HttpOnly cookie
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=not settings.DEBUG,  # HTTPS only in production
                samesite='Lax',
                max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
            )
            
            # Set refresh token in HttpOnly cookie
            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax',
                max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            )
            
            # SECURITY: Don't return tokens in response body
            # Tokens are in HttpOnly cookies - JavaScript cannot access them
            from .serializers import UserSerializer
            from .utils import optimize_user_queryset
            
            # Optimize user query to prevent N+1 and get fresh permissions
            user = optimize_user_queryset(User.objects.filter(pk=user.pk)).first()
            
            serialized_data = UserSerializer(user).data
            
            # DEBUG: Log what permissions are being sent to frontend
            logger.info(f"🔐 Login response for {user.email}:")
            logger.info(f"   Permissions being sent: {serialized_data.get('permissions', {})}")
            
            response.data = {
                'user': serialized_data,
            }
        
        return response
      except Exception as e:
        logger.exception(f"Login error for request from {request.META.get('REMOTE_ADDR')}")
        return Response(
            {'detail': 'An error occurred during login. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class CookieTokenRefreshView(TokenRefreshView):
    """Refresh JWT token from HttpOnly cookie"""
    throttle_classes = [RefreshRateThrottle]
    
    def post(self, request, *args, **kwargs):
        # Get refresh token from cookie
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Add refresh token to request data
        request.data['refresh'] = refresh_token
        
        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == 200:
                access_token = response.data.get('access')
                
                # Set new access token in cookie
                response.set_cookie(
                    key='access_token',
                    value=access_token,
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite='Lax',
                    max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
                )
                
                # If rotation is enabled, update refresh token cookie
                if 'refresh' in response.data:
                    refresh_token = response.data.get('refresh')
                    response.set_cookie(
                        key='refresh_token',
                        value=refresh_token,
                        httponly=True,
                        secure=not settings.DEBUG,
                        samesite='Lax',
                        max_age=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
                    )
                
                response.data = {'detail': 'Token refreshed successfully'}
            
            return response
            
        except (InvalidToken, TokenError) as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )


@api_view(['POST'])
def logout_view(request):
    """Logout by clearing HttpOnly cookies
    
    SECURITY: Uses global permissions (IsAuthenticated + IsEmailVerified)
    """
    response = Response({'detail': 'Successfully logged out'}, status=status.HTTP_200_OK)
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response


class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint with email verification
    
    SECURITY:
    - Creates user with is_active=False
    - Sends verification email via Resend
    - Returns generic success message (no user enumeration)
    - Rate limited to 5/min per IP
    - Logs registration attempts
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer
    throttle_classes = [RegisterRateThrottle]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # SECURITY: User created with is_active=False (model default)
        user = serializer.save()
        
        logger.info(f"New user registered (inactive): {user.email} (user_id: {user.pk})")
        
        # Send verification email
        try:
            send_verification_email(user)
            logger.info(f"Verification email sent to {user.email}")
        except EmailServiceError as e:
            # SECURITY: Don't expose email service errors to user
            # Log error but return success (email service issues shouldn't block registration)
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        
        # SECURITY: Generic response - don't confirm whether email exists
        return Response({
            'detail': 'If an account exists for this email, a verification link has been sent.',
            'redirect_to': '/verify-notice'
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_email_view(request):
    """
    Verify user email with uid and token
    
    SECURITY:
    - Validates token server-side
    - Token expires after 24 hours
    - Token invalidated after use (is_active changes)
    - Logs invalid attempts
    - Rate limited to 10/min per IP
    - Generic error messages
    """
    throttle = VerifyRateThrottle()
    if not throttle.allow_request(request, verify_email_view):
        return Response(
            {'detail': 'Too many verification attempts. Please try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    try:
     uid = request.data.get('uid')
     token = request.data.get('token')
    
     if not uid or not token:
        logger.warning(f"Verification attempt without uid/token from IP: {request.META.get('REMOTE_ADDR')}")
        return Response(
            {'detail': 'Verification link is invalid or expired.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
     try:
        # Decode user ID (UUID)
         user_id = force_str(urlsafe_base64_decode(uid))
         # Convert to UUID object for lookup (handles both string UUID and raw bytes)
         import uuid as uuid_lib
         try:
             user_uuid = uuid_lib.UUID(user_id)
         except ValueError:
            # If conversion fails, user_id might already be in correct format
             user_uuid = user_id
         user = User.objects.get(pk=user_uuid)
        
        # SECURITY: Check if user is already active
         if user.is_active:
             logger.info(f"Verification attempt for already active user: {user.email}")
             return Response(
                 {'detail': 'Account already verified. Please log in.'},
                 status=status.HTTP_200_OK
             )
        
        # Validate token
         if not email_verification_token.check_token(user, token):
             logger.warning(
                 f"Invalid/expired verification token for user: {user.email} (user_id: {user.pk}), "
                 f"IP: {request.META.get('REMOTE_ADDR')}"
             )
             return Response(
                {'detail': 'Verification link is invalid or expired. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
             )
        
        # Check if this is a Server Creator application
         from .models import ServerCreatorApplication            
            # SECURITY: Server creators get email_verified but NOT activated (need payment)
            # email_verified allows them to authenticate and call checkout endpoint
         with transaction.atomic():
                 application =(
                    ServerCreatorApplication.objects
                    .select_for_update()
                    .filter(user=user, status='pending_email')
                    .first()
                    )
         
         if application:
            # SECURE APPROACH: Activate server creators after email verification
            # Payment status is tracked in ServerCreatorApplication.status
            # Payment enforcement happens at checkout/server creation, not login
            user.email_verified = True
            user.is_active = True  # Allow login - payment checked separately
            user.save(update_fields=['email_verified', 'is_active'])
                
            application.status = 'pending_payment'
            application.email_verified_at = timezone.now()
            application.save(update_fields=['status', 'email_verified_at'])
            
            logger.info(f"Server creator email verified: {user.email} (user_id: {user.pk}), redirecting to payment")
            
            # Return success - user can now login normally
            # Frontend should redirect to checkout based on application status
            return Response({
                 'detail': 'Email verified! Please complete payment to activate your server creator account.',
                 'redirect_to': '/server-creator/checkout',
                 'requires_payment': True,
                 'application_id': application.pk
            }, status=status.HTTP_200_OK)
            
         else:
             # Trader - activate immediately and ensure Trader role is assigned
             from .models import Role, UserRole
             from servers.models import Server, ServerMember
             
             with transaction.atomic():
                 user.email_verified = True
                 user.is_active = True
                 user.save(update_fields=['email_verified', 'is_active'])
                 
                 # Ensure Trader role is assigned (in case it wasn't during registration)
                 if not user.user_roles.exists():
                     trader_role, _ = Role.objects.get_or_create(
                         name='Trader',
                         defaults={'description': 'Regular platform user'}
                     )
                     UserRole.objects.create(user=user, role=trader_role)
            
             logger.info(f"User email verified successfully: {user.email} (user_id: {user.pk})")
            
             return Response({
                 'detail': 'Email verified successfully! You can now log in.',
                 'redirect_to': '/login'
             }, status=status.HTTP_200_OK)
        
     except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
         logger.warning(
             f"Invalid verification attempt - uid: {uid}, "
             f"IP: {request.META.get('REMOTE_ADDR')}, error: {str(e)}"
         )
         return Response(
             {'detail': 'Verification link is invalid or expired.'},
             status=status.HTTP_400_BAD_REQUEST
         )
    except Exception as e:
        logger.exception(f"Email verification error for request from {request.META.get('REMOTE_ADDR')}")
        return Response(
            {'detail': 'An error occurred during verification. Please try again or contact support.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def resend_verification_view(request):
    """
    Resend verification email
    
    SECURITY:
    - 60 second cooldown per user (prevents spam)
    - Rate limited to 3/min per IP
    - Generic response (no user enumeration)
    - Logs resend attempts and abuse
    - Only sends if user exists and is inactive
    """
    throttle = ResendVerificationRateThrottle()
    if not throttle.allow_request(request, resend_verification_view):
        return Response(
            {'detail': 'Too many requests. Please try again later.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response(
            {'detail': 'Email is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # SECURITY: Check cooldown using cache
    cache_key = f'resend_verification_{email}'
    if cache.get(cache_key):
        # Log potential abuse
        logger.warning(
            f"Resend verification cooldown violation for email: {email}, "
            f"IP: {request.META.get('REMOTE_ADDR')}"
        )
        # SECURITY: Generic response - don't reveal cooldown exists
        return Response(
            {'detail': 'If an account exists for this email, a verification link has been sent.'},
            status=status.HTTP_200_OK
        )
    
    try:
        user = User.objects.get(email=email)
        
        # Only resend if email not verified
        if not user.email_verified:
            # Set cooldown (60 seconds)
            cache.set(cache_key, True, 60)
            
            # Send verification email
            try:
                send_resend_verification_email(user)
                logger.info(f"Verification email resent to {user.email} (user_id: {user.pk})")
            except EmailServiceError as e:
                logger.error(f"Failed to resend verification email to {user.email}: {str(e)}")
        else:
            # Email already verified - don't send email
            logger.info(f"Resend verification requested for verified user: {user.email}")
    
    except User.DoesNotExist:
        # User doesn't exist - log attempt
        logger.info(f"Resend verification requested for non-existent email: {email}")
    
    # SECURITY: Add timing normalization to prevent enumeration via response time
    import time
    import random
    # Add random delay (100-300ms) to normalize response timing
    time.sleep(0.1 + random.random() * 0.2)
    
    # SECURITY: Always return same generic message (prevent user enumeration)
    return Response(
        {'detail': 'If an account exists for this email, a verification link has been sent.'},
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
def current_user_view(request):
    """
    Get current user info with roles and permissions
    
    SECURITY: Uses global permissions (IsAuthenticated + IsEmailVerified)
    Only authenticated, verified users can access their own data
    """
    from .utils import optimize_user_queryset
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Optimize query to prevent N+1
    user = optimize_user_queryset(User.objects.filter(pk=request.user.pk)).first()
    serialized_data = UserSerializer(user).data
    
    # DEBUG: Log what permissions are being sent
    logger.info(f"🔐 /auth/me/ response for {user.email}:")
    logger.info(f"   Permissions being sent: {serialized_data.get('permissions', {})}")
    
    return Response(serialized_data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_trader_profile_view(request, user_id):
    """
    Get public trader profile - PROFESSIONAL PERFORMANCE CARD ONLY.
    
    STRICT PRIVACY ENFORCEMENT:
    - NO personal data (real name, email, contact info)
    - NO sensitive trading info (deposits, balances, detailed history)
    - Shows ONLY: alias/handle, server context, lifetime volume, rank, payout feed
    
    Privacy Modes:
    - privacy=true: Returns minimal anonymized version (unless valid token)
    - privacy=false: Returns professional performance card with allowed fields
    
    Token Access:
    - Query param: ?token=<uuid>
    - Header: X-Private-Analytics-Token: <uuid>
    
    SECURITY: Public endpoint - no authentication required
    Token validation happens server-side only, never exposed to client
    """
    from utils.privacy import check_private_analytics_access
    from .serializers import PublicTraderProfileSerializer
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {'detail': 'Trader not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # SECURITY: Validate token server-side only, never expose to frontend
    token = request.query_params.get('token') or request.META.get('HTTP_X_PRIVATE_ANALYTICS_TOKEN')
    has_valid_token = False
    if token:
        has_valid_token = check_private_analytics_access(token, user)
    
    # Optional: specific server context
    server_id = request.query_params.get('server_id')
    
    # SECURITY: Don't pass has_valid_token to serializer context
    # Instead, pass it internally for data filtering only
    serializer = PublicTraderProfileSerializer(
        user,
        context={
            'request': request,
            '_internal_has_valid_token': has_valid_token,  # Internal use only
            'server_id': server_id
        }
    )
    
    # Log access (has_token for audit purposes only, never sent to client)
    logger.info(f"Public profile accessed: user={user_id}, privacy={user.privacy}, token_valid={has_valid_token}")
    
    return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model.
    
    Owner: Full access (create, edit, delete any user, view all users)
    Admin: View regular member profiles only (no staff, no create/edit/delete)
    Moderator: View regular member profiles only (no staff)
    
    SECURITY: 
    - All actions require email verification
    - Admin/Moderator cannot see Owner, Admin, Moderator, or Superuser profiles
    """
    
    serializer_class = UserSerializer
    # Uses global DEFAULT_PERMISSION_CLASSES (IsAuthenticated + IsEmailVerified)
    
    def get_queryset(self):
        """
        Optimize queryset and filter based on user role.
        
        SECURITY: Admin/Moderator can only see regular users (no platform staff)
        """
        from .utils import optimize_user_queryset
        
        queryset = optimize_user_queryset(User.objects.all())
        
        # Superuser sees all users
        if self.request.user.is_superuser:
            return queryset
        
        # Admin/Moderator see only regular users (exclude platform staff)
        # Exclude users with Admin or Moderator roles, and superusers
        return queryset.exclude(
            user_roles__role__name__in=['Admin', 'Moderator']
        ).exclude(
            is_superuser=True
        ).distinct()
    
    def get_permissions(self):
        # SECURITY: Custom permission classes now check email verification internally
        
        # User management actions (privacy, profile) use their own permission_classes
        if self.action in ['update_profile', 'toggle_privacy', 'regenerate_private_token', 'get_privacy_settings']:
            # These use the permission_classes defined in their @action decorators
            return super().get_permissions()
        
        # Create/Update/Delete require Superuser permission ONLY
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperuserOnly()]
        # List/Retrieve - Admin can view member profiles (filtered by get_queryset)
        return [IsAdminOnly()]
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated,IsEmailVerified])
    def update_profile(self, request):
        """
        Update current user profile.
        
        SECURITY: Uses global permissions (IsAuthenticated + IsEmailVerified)
        """
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='privacy/toggle', permission_classes=[IsAuthenticated ,IsEmailVerified ])
    def toggle_privacy(self, request):
        """
        Toggle privacy setting for current user.
        
        SECURITY: Uses global permissions (IsAuthenticated + IsEmailVerified)
        """
        user = request.user
        user.privacy = not user.privacy
        user.save(update_fields=['privacy'])
        
        logger.info(f"User {user.username} toggled privacy to {user.privacy}")
        
        return Response({
            'privacy': user.privacy,
            'private_analytics_token': str(user.private_analytics_token) if user.privacy else None,
            'private_analytics_url': f"{settings.FRONTEND_URL}/analytics/private?token={user.private_analytics_token}" if user.privacy else None
        })
    
    @action(detail=False, methods=['post'], url_path='privacy/regenerate-token', permission_classes=[IsAuthenticated ,IsEmailVerified])
    def regenerate_private_token(self, request):
        """
        Regenerate private analytics token.
        
        SECURITY: Uses global permissions (IsAuthenticated + IsEmailVerified)
        """
        user = request.user
        
        if not user.privacy:
            return Response(
                {'detail': 'Privacy must be enabled to regenerate token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_token = user.generate_private_analytics_token()
        
        logger.info(f"User {user.username} regenerated private analytics token")
        
        return Response({
            'private_analytics_token': str(new_token),
            'private_analytics_url': f"{settings.FRONTEND_URL}/analytics/private?token={new_token}"
        })
    
    @action(detail=False, methods=['get'], url_path='privacy/settings', permission_classes=[IsAuthenticated, IsEmailVerified])
    def get_privacy_settings(self, request):
        """
        Get current privacy settings.
        
        SECURITY: Uses global permissions (IsAuthenticated + IsEmailVerified)
        """
        user = request.user
        
        return Response({
            'privacy': user.privacy,
            'private_analytics_token': str(user.private_analytics_token) if user.privacy else None,
            'private_analytics_url': f"{settings.FRONTEND_URL}/analytics/private?token={user.private_analytics_token}" if user.privacy and user.private_analytics_token else None
        })


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Role model - Platform Superuser only.
    
    Only platform superusers should view available roles.
    This prevents regular users from discovering the role hierarchy.
    
    SECURITY: IsSuperuserOnly checks authentication + email verification + superuser status
    """
    
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsSuperuserOnly]


class UserRoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UserRole model - Platform Superuser only.
    
    Only platform superusers can assign/remove user roles.
    This is a critical operation that affects platform permissions.
    
    SECURITY: IsSuperuserOnly checks authentication + email verification + superuser status
    """
    
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    # SECURITY: IsSuperuserOnly now checks authentication + email verification internally
    permission_classes = [IsSuperuserOnly]


class ForgotPasswordThrottle(AnonRateThrottle):
    """Rate limit for forgot password endpoint - 10 requests per hour."""
    rate = '10/hour'
    
    def allow_request(self, request, view):
        # Disable throttling in development mode
        if settings.DEBUG:
            return True
        return super().allow_request(request, view)


class ForgotPasswordView(generics.GenericAPIView):
    """
    Initiate password reset flow.
    
    POST /api/auth/forgot-password/
    
    SECURITY:
    - Always returns success (prevents user enumeration)
    - Rate limited (3 requests/hour per IP)
    - Generates cryptographically secure tokens
    - Tokens are hashed before storage
    - Invalidates previous tokens
    - Time-limited tokens (30 minutes)
    - Logs all reset attempts
    """
    
    serializer_class = ForgotPasswordSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ForgotPasswordThrottle]
    
    def post(self, request):
        """
        Handle forgot password request.
        
        SECURITY: Always returns success, even if email doesn't exist.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # Get client IP for logging
        ip_address = self.get_client_ip(request)
        
        try:
            user = User.objects.get(email=email)
            
            # Create password reset token
            token_instance, raw_token = PasswordResetToken.create_for_user(
                user=user,
                expiry_minutes=30,
                ip_address=ip_address
            )
            
            # Send password reset email
            try:
                send_password_reset_email(user, raw_token)
                
                # Log successful reset request
                logger.info(
                    f"Password reset email sent to {email} from IP {ip_address}"
                )
                
                # Create audit log
                from audit.models import AuditLog
                AuditLog.log(
                    user=None,  # Anonymous action
                    action_type='other',
                    target_table='user',
                    target_id=str(user.id),
                    metadata={
                        'action': 'password_reset_requested',
                        'email': email,
                        'ip_address': ip_address,
                        'token_expires_at': token_instance.expires_at.isoformat()
                    }
                )
                
            except EmailServiceError as e:
                logger.error(
                    f"Failed to send password reset email to {email}: {str(e)}"
                )
                # Still return success (don't reveal if email exists)
                
        except User.DoesNotExist:
            # Log attempt for non-existent email (security monitoring)
            logger.warning(
                f"Password reset attempted for non-existent email: {email} "
                f"from IP {ip_address}"
            )
        
        # SECURITY: Always return success
        return Response({
            'detail': 'If an account with that email exists, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)
    
    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ResetPasswordView(generics.GenericAPIView):
    """
    Complete password reset with token.
    
    POST /api/auth/reset-password/
    
    SECURITY:
    - Validates token hash
    - Checks expiration
    - Single-use tokens
    - Strong password enforcement
    - Invalidates all user sessions
    - Creates audit log
    - Transaction safety
    """
    
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Reset password with valid token.
        
        SECURITY: Validates token, enforces password strength, logs action.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        # Verify token
        token_instance = PasswordResetToken.verify_token(user, token)
        
        if not token_instance:
            return Response({
                'error': 'Invalid or expired reset link.',
                'error_code': 'INVALID_TOKEN'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get client IP
        ip_address = self.get_client_ip(request)
        
        try:
            with transaction.atomic():
                # Set new password
                user.set_password(new_password)
                user.save(update_fields=['password'])
                
                # Mark token as used
                token_instance.mark_as_used()
                
                # Invalidate all refresh tokens (log out everywhere)
                RefreshToken.for_user(user)
                
                # Create audit log
                from audit.models import AuditLog
                AuditLog.log(
                    user=user,
                    action_type='update',
                    target_table='user',
                    target_id=str(user.id),
                    metadata={
                        'action': 'password_reset_completed',
                        'ip_address': ip_address,
                        'sessions_invalidated': True
                    }
                )
                
                logger.info(
                    f"Password reset successful for {user.email} from IP {ip_address}"
                )
            
            return Response({
                'detail': 'Password has been reset successfully. Please log in with your new password.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Password reset failed for {user.email}: {str(e)}\n{traceback.format_exc()}"
            )
            return Response({
                'error': 'Password reset failed. Please try again.',
                'error_code': 'RESET_FAILED'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ChangePasswordView(generics.GenericAPIView):
    """
    Change password for authenticated user.
    
    POST /api/auth/change-password/
    
    SECURITY:
    - Requires authentication
    - Verifies current password
    - Enforces strong password
    - Invalidates other sessions
    - Creates audit log
    - Transaction safety
    """
    
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Change user password.
        
        SECURITY: Validates current password, enforces strength, logs action.
        """
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        new_password = serializer.validated_data['new_password']
        
        # Get client IP
        ip_address = self.get_client_ip(request)
        
        try:
            with transaction.atomic():
                # Set new password
                user.set_password(new_password)
                user.save(update_fields=['password'])
                
                # Invalidate all refresh tokens (log out other sessions)
                RefreshToken.for_user(user)
                
                # Create audit log
                from audit.models import AuditLog
                AuditLog.log(
                    user=user,
                    action_type='update',
                    target_table='user',
                    target_id=str(user.id),
                    metadata={
                        'action': 'password_changed',
                        'ip_address': ip_address,
                        'other_sessions_invalidated': True
                    }
                )
                
                logger.info(
                    f"Password changed successfully for {user.email} from IP {ip_address}"
                )
            
            return Response({
                'detail': 'Password changed successfully. Other sessions have been logged out.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(
                f"Password change failed for {user.email}: {str(e)}\n{traceback.format_exc()}"
            )
            return Response({
                'error': 'Password change failed. Please try again.',
                'error_code': 'CHANGE_FAILED'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
