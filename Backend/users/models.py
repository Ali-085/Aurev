from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
import hashlib
import uuid


class UserManager(BaseUserManager):
    """Custom user manager."""
    
    def create_user(self, email, username, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_superuser', True)
        # SECURITY: Superusers bypass email verification and are always active
        extra_fields.setdefault('email_verified', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    avatar_url = models.URLField(blank=True, null=True)
    
    # SECURITY: Separate email verification from account activation
    # email_verified: True after email verification (allows authentication)
    # is_active: True after full onboarding (email + payment for server creators)
    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    
    # Stripe integration fields
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    # Privacy settings
    privacy = models.BooleanField(
        default=False, 
        help_text="Hide stats from public view - shows as 'Private Trader #ID' with masked data"
    )
    private_analytics_token = models.UUIDField(
        default=uuid.uuid4, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Token for shareable private analytics link"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stripe_customer_id']),
        ]
    
    def __str__(self):
        return self.username
    
    def generate_private_analytics_token(self):
        """Generate a new private analytics token for shareable links."""
        self.private_analytics_token = uuid.uuid4()
        self.save(update_fields=['private_analytics_token'])
        return self.private_analytics_token
    
    def get_masked_name(self):
        """Get masked name for private traders."""
        if self.privacy:
            return f"Private Trader #{str(self.id)[:8]}"
        return self.username
    
    def set_role(self, role_name, changed_by=None, force=False):
        """
        Safely set user role, enforcing mutual exclusivity.
        
        Args:
            role_name: Name of the role (e.g., 'ServerCreator', 'Admin', 'Moderator', 'Trader')
            changed_by: User object performing the role change (for authorization)
            force: If True, skip safety checks (use with extreme caution)
        
        Returns:
            The created UserRole instance
        
        Raises:
            PermissionError: If unauthorized role change attempted
            ValueError: If trying to change superuser role
        
        Usage:
            user.set_role('ServerCreator', changed_by=admin_user)
        """
        from django.db import transaction
        from django.core.exceptions import PermissionDenied
        
        # SECURITY: Prevent changing superuser via role system
        if self.is_superuser:
            raise ValueError(
                f"Cannot change role for superuser {self.username}. "
                "Superusers are managed via Django admin."
            )
        
        # SECURITY: Only platform owner (superuser) can change roles unless forced
        if not force:
            if changed_by is None:
                raise PermissionDenied(
                    "Role changes require 'changed_by' parameter for audit trail. "
                    "Use force=True only in system operations."
                )
            
            if not changed_by.is_superuser:
                raise PermissionDenied(
                    f"Only platform superuser can change roles. "
                    f"{changed_by.username} is not authorized."
                )
            
            # SECURITY: Prevent self-demotion
            if changed_by.id == self.id:
                current_role = self.get_role()
                if current_role in ['Admin', 'Moderator'] and role_name not in ['Admin', 'Moderator']:
                    raise PermissionDenied(
                        f"Platform staff cannot demote themselves from {current_role} to {role_name}. "
                        "Another superuser must perform this action."
                    )
        
        with transaction.atomic():
            # Remove all existing roles
            old_role = self.get_role()
            self.user_roles.all().delete()
            
            # Get or create the role
            role, _ = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': f'{role_name} role'}
            )
            
            # Assign new role
            user_role = UserRole.objects.create(user=self, role=role)
            
            # Create audit log if changed_by provided
            if changed_by:
                from audit.models import AuditLog
                AuditLog.log(
                    changed_by,
                    action_type='update',
                    target_table='user',
                    target_id=self.id,
                    metadata={
                        'username': self.username,
                        'old_role': old_role,
                        'new_role': role_name,
                        'forced': force
                    }
                )
            
            return user_role
    
    def get_role(self):
        """
        Get user's current role (users have exactly one role).
        
        Returns:
            Role name string or None if no role assigned
        """
        user_role = self.user_roles.first()
        return user_role.role.name if user_role else None


class Role(models.Model):
    """Role model for user permissions."""
    
    ROLE_CHOICES = [
        ('ServerCreator', 'Server Creator'),  # Can create and manage their own servers (requires subscription)
        ('Admin', 'Admin'),                    # High-trust moderators with expanded capabilities
        ('Moderator', 'Moderator'),            # Content reviewers and payout verifiers
        ('Trader', 'Trader')                   # Regular platform user (default role)
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'roles'
    
    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
    Junction table for user-role assignments.
    
    IMPORTANT: Roles are mutually exclusive - a user can have exactly ONE role at a time.
    Before assigning a new role, always delete existing roles:
        user.user_roles.all().delete()
        UserRole.objects.create(user=user, role=new_role)
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_assignments')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'user_roles'
        unique_together = ['user', 'role']
    
    def save(self, *args, **kwargs):
        """
        Override save to enforce mutual exclusivity.
        Raises ValidationError if user already has a different role.
        """
        from django.core.exceptions import ValidationError
        
        # Check if user already has a role (excluding this instance if updating)
        existing_roles = UserRole.objects.filter(user=self.user).exclude(pk=self.pk)
        if existing_roles.exists():
            existing_role_names = ', '.join(existing_roles.values_list('role__name', flat=True))
            raise ValidationError(
                f"User {self.user.username} already has role(s): {existing_role_names}. "
                f"Roles are mutually exclusive. Delete existing roles before assigning a new one."
            )
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


class ServerCreatorApplication(models.Model):
    """
    Server Creator application - pending payment
    
    SECURITY:
    - User created with is_active=False
    - Email verification required first
    - Payment completion activates user
    - Auto-deleted if payment not completed within 24h
    """
    
    STATUS_CHOICES = [
        ('pending_email', 'Pending Email Verification'),
        ('pending_payment', 'Pending Payment'),
        ('payment_processing', 'Payment Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='server_creator_application'
    )
    tier = models.CharField(max_length=20, choices=[
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('elite', 'Elite'),
    ])
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_email')
    
    # Application data
    server_name = models.CharField(max_length=100, blank=True)
    server_description = models.TextField(blank=True)
    discord_server_id = models.CharField(max_length=100, blank=True)
    
    # Tracking
    email_verified_at = models.DateTimeField(null=True, blank=True)
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()  # Auto-delete if not completed
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'server_creator_applications'
        indexes = [
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['stripe_checkout_session_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.tier} ({self.status})"


class PasswordResetToken(models.Model):
    """
    Secure password reset token storage.
    
    SECURITY:
    - Tokens are hashed before storage (never stored in plaintext)
    - Single-use tokens (invalidated after use)
    - Time-limited (default 30 minutes)
    - Previous tokens auto-invalidated when new one generated
    - User enumeration prevention (same response for valid/invalid emails)
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token_hash = models.CharField(
        max_length=128,
        unique=True,
        help_text="SHA-256 hash of the reset token"
    )
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(
        help_text="Token expiration timestamp (default 30 minutes)"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when token was used (prevents reuse)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of reset request (for security auditing)"
    )
    
    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token_hash']),
            models.Index(fields=['user', 'expires_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Reset token for {self.user.email} (expires: {self.expires_at})"
    
    @staticmethod
    def generate_token():
        """
        Generate a cryptographically secure random token.
        
        Returns:
            64-character random string (256 bits of entropy)
        """
        return get_random_string(
            length=64,
            allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        )
    
    @staticmethod
    def hash_token(token):
        """
        Hash a token using SHA-256.
        
        Args:
            token: Raw token string
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()
    
    @classmethod
    def create_for_user(cls, user, expiry_minutes=30, ip_address=None):
        """
        Create a new password reset token for a user.
        
        SECURITY: Invalidates all previous tokens for this user.
        
        Args:
            user: User instance
            expiry_minutes: Token validity in minutes (default 30)
            ip_address: IP address of the request (optional)
            
        Returns:
            tuple: (token_instance, raw_token)
        """
        from django.db import transaction
        
        # Generate raw token
        raw_token = cls.generate_token()
        token_hash = cls.hash_token(raw_token)
        
        # Calculate expiration
        expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        
        with transaction.atomic():
            # Invalidate all previous tokens for this user (security)
            cls.objects.filter(user=user, used_at__isnull=True).update(
                used_at=timezone.now()
            )
            
            # Create new token
            token = cls.objects.create(
                user=user,
                token_hash=token_hash,
                expires_at=expires_at,
                ip_address=ip_address
            )
        
        return token, raw_token
    
    def is_valid(self):
        """
        Check if token is still valid.
        
        Returns:
            bool: True if token is valid (not used, not expired)
        """
        if self.used_at is not None:
            return False
        
        if timezone.now() > self.expires_at:
            return False
        
        return True
    
    def mark_as_used(self):
        """Mark token as used to prevent reuse."""
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])
    
    @classmethod
    def verify_token(cls, user, raw_token):
        """
        Verify a token for a user.
        
        Args:
            user: User instance
            raw_token: Raw token string from URL
            
        Returns:
            PasswordResetToken instance if valid, None otherwise
        """
        token_hash = cls.hash_token(raw_token)
        
        try:
            token = cls.objects.get(
                user=user,
                token_hash=token_hash
            )
            
            if token.is_valid():
                return token
            
        except cls.DoesNotExist:
            pass
        
        return None

