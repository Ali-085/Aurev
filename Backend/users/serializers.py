from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .models import Role, UserRole, PasswordResetToken
from utils.privacy import get_public_trader_view

User = get_user_model()


class PublicTraderSerializer(serializers.Serializer):
    """Serializer for public trader view with privacy masking.
    
    SECURITY: Does not expose 'masked' flag to frontend.
    Frontend determines masking by checking if data is hidden (null fields).
    """
    id = serializers.UUIDField()
    username = serializers.CharField()
    avatar_url = serializers.URLField(allow_null=True)
    is_private = serializers.BooleanField()
    
    def to_representation(self, instance):
        """Apply privacy masking to trader data."""
        requesting_user = self.context.get('request').user if self.context.get('request') else None
        has_valid_token = self.context.get('has_valid_token', False)
        
        return get_public_trader_view(
            user=instance,
            requesting_user=requesting_user,
            has_valid_token=has_valid_token
        )


class PublicTraderProfileSerializer(serializers.Serializer):
    """
    Public trader profile serializer - PROFESSIONAL PERFORMANCE CARD ONLY.
    
    STRICT RULES:
    - NO personal data (name, email, contact info)
    - NO sensitive trading info (deposits, balances, detailed history)
    - Shows ONLY: alias/handle, server context, lifetime volume, rank, payout feed
    - Headline stats: total volume, payout count, largest payout, active period, approval rate
    - Achievement badges: performance-based only (no sensitive data)
    - If privacy=true: Returns minimal anonymized version
    - If privacy=false: Returns professional performance card
    """
    
    # Basic Info (non-personal)
    id = serializers.UUIDField()
    alias = serializers.CharField()  # Never real name
    avatar_url = serializers.URLField(allow_null=True)
    is_private = serializers.BooleanField()
    
    # Headline Stats (Top Bar Metrics)
    lifetime_volume = serializers.FloatField(allow_null=True)
    lifetime_volume_range = serializers.CharField(allow_null=True)
    total_verified_payout_count = serializers.IntegerField(allow_null=True)
    largest_verified_payout = serializers.FloatField(allow_null=True)
    active_period = serializers.CharField(allow_null=True)
    approval_rate = serializers.FloatField(allow_null=True)
    
    # Server Association (non-sensitive performance context)
    server_name = serializers.CharField(allow_null=True)
    server_rank = serializers.IntegerField(allow_null=True)
    contribution_percentage = serializers.FloatField(allow_null=True)
    server_contribution_30d = serializers.FloatField(allow_null=True)
    
    # Achievement Badges (safe, performance-based only)
    public_achievements = serializers.ListField(child=serializers.CharField(), allow_null=True)
    
    # Performance Charts Data (institutional, simple visualizations)
    chart_data = serializers.DictField(allow_null=True)
    
    # Payout Feed (approved payouts only)
    recent_payouts = serializers.ListField(allow_null=True)
    
    def to_representation(self, instance):
        """
        Build professional performance card with strict privacy enforcement.
        
        SECURITY: Token validation happens server-side only.
        Frontend receives filtered data, never sees internal validation flags.
        
        Returns minimal anonymized data if privacy=true, otherwise returns
        professional performance card with ONLY allowed fields.
        """
        from utils.privacy import get_public_profile
        
        requesting_user = self.context.get('request').user if self.context.get('request') else None
        # SECURITY: Use internal flag that's never exposed to frontend
        has_valid_token = self.context.get('_internal_has_valid_token', False)
        server_id = self.context.get('server_id')  # Optional: specific server context
        
        return get_public_profile(
            user=instance,
            requesting_user=requesting_user,
            has_valid_token=has_valid_token,
            server_id=server_id
        )


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with capability-based permissions."""
    permissions = serializers.SerializerMethodField()
    private_analytics_url = serializers.SerializerMethodField()
    default_dashboard_url = serializers.SerializerMethodField()
    current_role = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'avatar_url',
            'privacy', 'private_analytics_token', 'private_analytics_url',
            'created_at', 'updated_at', 'permissions', 'default_dashboard_url',
            'is_active', 'email_verified', 'current_role'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'permissions',
            'private_analytics_token', 'private_analytics_url', 'default_dashboard_url'
        ]
        # SECURITY: Never expose:
        # - stripe_customer_id (payment data)
        # - roles (internal hierarchy)
        # - is_superuser (privilege escalation risk)
    
    def get_permissions(self, obj):
        """
        Get user capabilities (what they CAN do, not their role names).
        This provides frontend authorization hints without exposing internal hierarchy.
        Uses optimized queries if annotations are available.
        """
        from .utils import get_user_permissions
        return get_user_permissions(obj)
    
    def get_private_analytics_url(self, obj):
        """Get private analytics URL if privacy is enabled."""
        if obj.privacy and obj.private_analytics_token:
            from django.conf import settings
            return f"{settings.FRONTEND_URL}/analytics/private?token={obj.private_analytics_token}"
        return None
    
    def get_current_role(self, obj):
        """
        Get user's current role name.
        Returns None if user has no role assigned.
        """
        user_role = obj.user_roles.first()
        return user_role.role.name if user_role else None
    
    def get_default_dashboard_url(self, obj):
        """
        SECURITY: Return dashboard URL without exposing role hierarchy.
        Staff users get /dashboard, regular users get /profile.
        This allows proper redirect after login without revealing internal roles.
        """
        # Superuser or admin/moderator get dashboard
        if obj.is_superuser:
            return '/dashboard'
        
        user_role = obj.user_roles.first()
        if user_role and user_role.role.name in ['Admin', 'Moderator']:
            return '/dashboard'
        
        # ServerCreator role: redirect to server creation if no server, otherwise dashboard
        if user_role and user_role.role.name == 'ServerCreator':
            from servers.models import Server
            if Server.objects.filter(owner_user=obj).exists():
                return '/dashboard'
            else:
                return '/servers/create'
        
        # Server owners get server dashboard
        from servers.models import Server
        if Server.objects.filter(owner_user=obj).exists():
            return '/dashboard'
        
        # Regular traders get profile
        return '/profile'


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    account_type = serializers.ChoiceField(
        choices=['trader', 'server_creator'],
        default='trader',
        write_only=True,
        help_text="Account type: 'trader' (regular user), 'server_creator' (creates servers - requires subscription)"
    )
    server_id = serializers.UUIDField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Server UUID to join (required if account_type is 'trader')"
    )
    
    # Server Creator fields
    tier = serializers.ChoiceField(
        choices=['standard', 'premium', 'elite'],
        write_only=True,
        required=False,
        help_text="Subscription tier (required if account_type is 'server_creator')"
    )
    server_name = serializers.CharField(
        max_length=100,
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Initial server name (optional)"
    )
    server_description = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Server description (optional)"
    )
    discord_server_id = serializers.CharField(
        max_length=100,
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Discord server ID (optional)"
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 'avatar_url',
            'account_type', 'server_id', 'tier', 'server_name', 
            'server_description', 'discord_server_id'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # Validate server creator registration requires tier
        if attrs.get('account_type') == 'server_creator' and not attrs.get('tier'):
            raise serializers.ValidationError({"tier": "Subscription tier is required for server creator registration."})
        
        return attrs
    
    def create(self, validated_data):
        from servers.models import Server, ServerMember
        from .models import ServerCreatorApplication, Role, UserRole
        from datetime import timedelta
        
        account_type = validated_data.pop('account_type', 'trader')
        server_id = validated_data.pop('server_id', None)
        tier = validated_data.pop('tier', None)
        server_name = validated_data.pop('server_name', '')
        server_description = validated_data.pop('server_description', '')
        discord_server_id = validated_data.pop('discord_server_id', '')
        validated_data.pop('password_confirm')
        
        # SECURITY: Create user with is_active=False (model default)
        user = User.objects.create_user(**validated_data)
        
        # Assign role based on account type
        if account_type == 'server_creator':
            # SECURITY: Create application - user stays inactive until payment
            # Role will be assigned to ServerCreator by webhook after successful payment
            ServerCreatorApplication.objects.create(
                user=user,
                tier=tier,
                status='pending_email',
                server_name=server_name,
                server_description=server_description,
                discord_server_id=discord_server_id,
                expires_at=timezone.now() + timedelta(hours=24)
            )
            # Don't assign Trader role yet - will get ServerCreator after payment
        else:
            # All other users (trader) get Trader role by default
            trader_role, _ = Role.objects.get_or_create(
                name='Trader',
                defaults={'description': 'Regular platform user'}
            )
            UserRole.objects.create(user=user, role=trader_role)
            
            # If trader with server_id, join the server
            if account_type == 'trader' and server_id:
                try:
                    server = Server.objects.get(id=server_id)
                    server_member, created = ServerMember.objects.get_or_create(
                        server=server,
                        user=user
                    )
                    if created:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"✅ Created ServerMember for user {user.email} (ID: {user.id}) in server {server.name} (ID: {server.id})")
                    else:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"ℹ️ ServerMember already exists for user {user.email} in server {server.name}")
                except Server.DoesNotExist:
                    # If server doesn't exist, user is still created but not joined
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"⚠️ Server ID {server_id} not found during registration for user {user.email}")
                    pass
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"❌ Error creating ServerMember for user {user.email} in server {server_id}: {str(e)}")
                    # Don't fail registration if server join fails
                    pass
        
        return user


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole model."""
    
    user = UserSerializer(read_only=True)
    role = RoleSerializer(read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['id', 'user', 'role', 'created_at']


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Serializer for forgot password request.
    
    SECURITY:
    - Always returns success (prevents user enumeration)
    - Email is case-insensitive
    - No indication if email exists or not
    """
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Normalize email to lowercase."""
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    
    SECURITY:
    - Validates token hash match
    - Checks token expiration
    - Ensures token hasn't been used
    - Enforces strong password requirements
    - Single-use tokens
    """
    
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_new_password(self, value):
        """
        Validate password strength using Django's validators.
        
        Raises:
            serializers.ValidationError: If password is weak
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """
        Validate password confirmation and token.
        
        SECURITY: Detailed validation happens in view to prevent timing attacks.
        """
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        
        # Decode uid
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
            attrs['user'] = user
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                'uid': 'Invalid reset link.'
            })
        
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for authenticated password change.
    
    SECURITY:
    - Requires current password verification
    - Enforces strong password requirements
    - Invalidates other sessions after change
    """
    
    current_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_current_password(self, value):
        """Verify current password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value
    
    def validate_new_password(self, value):
        """
        Validate password strength using Django's validators.
        
        Raises:
            serializers.ValidationError: If password is weak
        """
        try:
            # Pass user context for better validation
            user = self.context['request'].user
            validate_password(value, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        
        # Ensure new password is different from current
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': 'New password must be different from current password.'
            })
        
        return attrs
