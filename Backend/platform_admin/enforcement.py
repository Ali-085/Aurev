"""
Platform Limits Enforcement

This module enforces all PlatformLimits settings across the system:
- Payout submission limits
- Server creation limits
- File upload validation
- Daily submission quotas
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import PlatformLimits


class LimitsEnforcer:
    """Enforce platform limits across all operations."""
    
    @staticmethod
    def get_limits():
        """Get current platform limits."""
        return PlatformLimits.get_limits()
    
    @staticmethod
    def validate_payout_amount(amount):
        """
        Validate payout amount against max_payout_amount limit.
        
        Raises:
            ValidationError: If amount exceeds limit
        """
        limits = PlatformLimits.get_limits()
        
        if amount > limits.max_payout_amount:
            raise ValidationError(
                f"Payout amount ${amount} exceeds maximum allowed ${limits.max_payout_amount}"
            )
    
    @staticmethod
    def validate_daily_user_submissions(user):
        """
        Check if user has exceeded daily submission limit.
        
        Raises:
            ValidationError: If user has reached daily limit
        """
        from payouts.models import PayoutSubmission
        
        limits = PlatformLimits.get_limits()
        
        # Check submissions in last 24 hours
        yesterday = timezone.now() - timedelta(days=1)
        submissions_today = PayoutSubmission.objects.filter(
            user=user,
            created_at__gte=yesterday
        ).count()
        
        if submissions_today >= limits.max_submissions_per_user_per_day:
            raise ValidationError(
                f"You have reached the daily submission limit of {limits.max_submissions_per_user_per_day}. "
                f"Please try again tomorrow."
            )
    
    @staticmethod
    def validate_daily_server_submissions(server):
        """
        Check if server has exceeded daily submission limit.
        Elite users get elite-specific limit (configurable by platform owner).
        
        Raises:
            ValidationError: If server has reached daily limit (0 = unlimited)
        """
        from payouts.models import PayoutSubmission
        
        limits = PlatformLimits.get_limits()
        
        # ELITE USERS: Use elite-specific limit based on server owner's subscription
        owner = server.owner_user
        has_elite = owner.subscriptions.filter(status='active', plan__tier='elite').exists()
        
        if has_elite:
            max_daily = limits.max_submissions_per_server_per_day_elite
        else:
            max_daily = limits.max_submissions_per_server_per_day
        
        # 0 = unlimited
        if max_daily == 0:
            return
        
        # Check submissions in last 24 hours
        yesterday = timezone.now() - timedelta(days=1)
        submissions_today = PayoutSubmission.objects.filter(
            server=server,
            created_at__gte=yesterday
        ).count()
        
        if submissions_today >= max_daily:
            raise ValidationError(
                f"This server has reached its daily submission limit of {max_daily}. "
                f"Please try again tomorrow."
            )
    
    @staticmethod
    def validate_file_upload(file):
        """
        Validate file upload against size and format limits.
        
        Raises:
            ValidationError: If file is invalid
        """
        limits = PlatformLimits.get_limits()
        
        # Check file size (convert MB to bytes)
        max_size_bytes = limits.max_screenshot_file_size_mb * 1024 * 1024
        if file.size > max_size_bytes:
            raise ValidationError(
                f"File size {file.size / (1024*1024):.2f}MB exceeds maximum of {limits.max_screenshot_file_size_mb}MB"
            )
        
        # Check file format
        allowed_formats = [f.strip().lower() for f in limits.allowed_file_formats.split(',')]
        file_extension = file.name.split('.')[-1].lower() if '.' in file.name else ''
        
        if file_extension not in allowed_formats:
            raise ValidationError(
                f"File format '.{file_extension}' not allowed. Allowed formats: {', '.join(allowed_formats)}"
            )
    
    @staticmethod
    def validate_server_creation(owner_user):
        """
        Check if user can create a server. Requires ServerCreator role and active subscription.
        All users limited to 1 server regardless of tier.
        
        Raises:
            ValidationError: If user doesn't have permission or already owns a server
        """
        # SECURITY: Must have ServerCreator role (assigned after payment)
        has_server_creator_role = owner_user.user_roles.filter(role__name='ServerCreator').exists()
        if not has_server_creator_role:
            raise ValidationError(
                "You must have a Server Creator subscription to create servers. "
                "Please complete your registration and payment."
            )
        
        # SECURITY: Must have active subscription (stricter check - no past_due)
        from subscriptions.models import UserSubscription
        has_active_subscription = UserSubscription.objects.filter(
            user=owner_user,
            status__in=['active', 'trialing']  # Removed 'past_due' for stricter validation
        ).exists()
        
        if not has_active_subscription:
            raise ValidationError(
                "You must have an active subscription to create servers. "
                "Please subscribe or renew your subscription."
            )
        
        # Check server count limit
        if owner_user.owned_servers.count() >= 1:
            raise ValidationError(
                "Server limit reached. You can only own 1 server. "
                "Please delete your existing server before creating a new one."
            )
    
    @staticmethod
    def validate_server_members(server):
        """
        Check if server has reached member limit.
        Elite users get elite-specific limit (configurable by platform owner).
        
        Raises:
            ValidationError: If server has reached member limit (0 = unlimited)
        """
        limits = PlatformLimits.get_limits()
        
        # ELITE USERS: Use elite-specific limit based on server owner's subscription
        owner = server.owner_user
        has_elite = owner.subscriptions.filter(status='active', plan__tier='elite').exists()
        
        if has_elite:
            max_members = limits.max_server_members_elite
        else:
            max_members = limits.max_server_members
        
        # 0 = unlimited
        if max_members == 0:
            return
        
        current_members = server.members.count()
        
        if current_members >= max_members:
            raise ValidationError(
                f"This server has reached its maximum capacity of {max_members} members."
            )
    
    @staticmethod
    def check_maintenance_mode():
        """
        Check if system is in maintenance mode.
        
        Raises:
            ValidationError: If maintenance mode is enabled
        """
        limits = PlatformLimits.get_limits()
        
        if limits.maintenance_mode:
            raise ValidationError(
                "The platform is currently undergoing maintenance. Please try again later."
            )
    
    @staticmethod
    def should_auto_approve(amount, server=None):
        """
        Check if payout should be auto-approved based on threshold.
        Elite users can have separate auto-approve threshold.
        
        Returns:
            bool: True if amount is below auto-approve threshold (when enabled)
        """
        limits = PlatformLimits.get_limits()
        
        # ELITE USERS: Use elite-specific threshold if configured
        if server:
            owner = server.owner_user
            has_elite = owner.subscriptions.filter(status='active', plan__tier='elite').exists()
            
            if has_elite:
                threshold = limits.elite_auto_approve_threshold
                # 0 = use global setting for elite
                if threshold == 0:
                    threshold = limits.payout_auto_approve_threshold
            else:
                threshold = limits.payout_auto_approve_threshold
        else:
            threshold = limits.payout_auto_approve_threshold
        
        # 0 = auto-approve disabled
        if threshold == 0:
            return False
        
        return amount <= threshold
    
    @staticmethod
    def is_ai_fraud_detection_enabled():
        """Check if AI fraud detection is enabled."""
        limits = PlatformLimits.get_limits()
        return limits.enable_ai_fraud_detection
    
    @staticmethod
    def check_ranking_eligibility(user_stats):
        """
        Check if user/server meets ranking eligibility criteria.
        
        Args:
            user_stats: Dict with 'payout_count' and 'total_volume'
        
        Returns:
            tuple: (is_eligible, reason)
        """
        limits = PlatformLimits.get_limits()
        
        payout_count = user_stats.get('payout_count', 0)
        total_volume = user_stats.get('total_volume', 0)
        
        if payout_count < limits.min_payout_count_for_ranking:
            return False, f"Need {limits.min_payout_count_for_ranking} payouts (have {payout_count})"
        
        if total_volume < limits.min_total_volume_for_ranking:
            return False, f"Need ${limits.min_total_volume_for_ranking} volume (have ${total_volume})"
        
        return True, "Eligible"


# Convenience functions for common checks

def enforce_payout_limits(user, server, amount, file=None):
    """
    Run all payout-related validations in one call.
    
    Raises:
        ValidationError: If any limit is exceeded
    """
    enforcer = LimitsEnforcer()
    
    # System checks
    enforcer.check_maintenance_mode()
    
    # Amount validation
    enforcer.validate_payout_amount(amount)
    
    # Daily limits
    enforcer.validate_daily_user_submissions(user)
    enforcer.validate_daily_server_submissions(server)
    
    # File validation
    if file:
        enforcer.validate_file_upload(file)


def enforce_server_limits(owner_user):
    """
    Run all server-related validations.
    
    Raises:
        ValidationError: If any limit is exceeded
    """
    enforcer = LimitsEnforcer()
    
    enforcer.check_maintenance_mode()
    enforcer.validate_server_creation(owner_user)


def enforce_member_limits(server):
    """
    Check if server can accept new members.
    
    Raises:
        ValidationError: If server is at capacity
    """
    enforcer = LimitsEnforcer()
    enforcer.validate_server_members(server)
