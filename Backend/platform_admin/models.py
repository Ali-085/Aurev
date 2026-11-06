from django.db import models
from django.utils import timezone


class MarketCategory(models.Model):
    """
    Global market categories for payout submissions.
    Platform owner can add/remove/enable/disable markets.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=10, blank=True, null=True, help_text="Emoji or icon")
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0, help_text="Order in dropdowns/lists")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'market_categories'
        ordering = ['display_order', 'name']
        verbose_name = 'Market Category'
        verbose_name_plural = 'Market Categories'
    
    def __str__(self):
        return f"{self.icon} {self.name}" if self.icon else self.name


class TradingCategory(models.Model):
    """
    Additional categorization for payouts (skill level, region, account size, etc.).
    Platform owner can add/remove/enable/disable categories.
    """
    CATEGORY_TYPE_CHOICES = [
        ('server', 'Server Category'),
        ('skill', 'Trader Skill Level'),
        ('payout_type', 'Payout Type'),
        ('region', 'Region'),
        ('account_tier', 'Account Size Tier'),
        ('scaling', 'Scaling Tier'),
    ]
    
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=50, choices=CATEGORY_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0, help_text="Order in dropdowns/lists")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_categories'
        ordering = ['category_type', 'display_order', 'name']
        verbose_name = 'Trading Category'
        verbose_name_plural = 'Trading Categories'
        unique_together = [['name', 'category_type']]
    
    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class PlatformLimits(models.Model):
    """Global platform limits and thresholds."""
    
    # Ranking eligibility
    min_payout_count_for_ranking = models.IntegerField(default=5)
    min_total_volume_for_ranking = models.DecimalField(max_digits=15, decimal_places=2, default=10000)
    
    # Payout submission limits
    max_payout_amount = models.DecimalField(max_digits=15, decimal_places=2, default=1000000)
    max_submissions_per_user_per_day = models.IntegerField(default=10)
    max_screenshot_file_size_mb = models.IntegerField(default=10)
    allowed_file_formats = models.CharField(max_length=255, default='jpg,jpeg,png,webp')
    
    # Server limits (All users limited to 1 server regardless of tier)
    max_server_members = models.IntegerField(default=10000, help_text="0 = unlimited")
    max_submissions_per_server_per_day = models.IntegerField(default=1000, help_text="0 = unlimited")
    
    # Elite-specific limits (configurable by platform owner)
    max_server_members_elite = models.IntegerField(default=0, help_text="Max members for Elite servers (0 = unlimited)")
    max_submissions_per_server_per_day_elite = models.IntegerField(default=0, help_text="Max daily submissions for Elite servers (0 = unlimited)")
    elite_auto_approve_threshold = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        help_text="Auto-approve threshold for Elite servers. 0 = use global setting"
    )
    
    # Analytics limits
    data_retention_days = models.IntegerField(default=365, help_text="0 = unlimited")
    analytics_display_days = models.IntegerField(default=180)
    
    # Subscription and data retention settings
    subscription_grace_period_days = models.IntegerField(
        default=30,
        help_text="Grace period after subscription cancellation before data deletion (days)"
    )
    enable_server_data_deletion = models.BooleanField(
        default=True,
        help_text="Automatically delete server data after grace period expires"
    )
    notify_before_deletion_days = models.IntegerField(
        default=7,
        help_text="Send warning email X days before data deletion (0 = no warning)"
    )
    
    # System settings
    payout_auto_approve_threshold = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        help_text="Auto-approve payouts below this amount. 0 = disabled"
    )
    enable_ai_fraud_detection = models.BooleanField(default=False)
    maintenance_mode = models.BooleanField(default=False)
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='platform_limit_updates'
    )
    
    class Meta:
        db_table = 'platform_limits'
    
    def __str__(self):
        return f"Platform Limits (Updated: {self.updated_at})"
    
    @classmethod
    def get_limits(cls):
        """Get or create the single instance of platform limits."""
        limits, created = cls.objects.get_or_create(id=1)
        return limits


# Note: Using the AuditLog model from the audit app instead of duplicating it here
# Import it in views/serializers when needed: from audit.models import AuditLog
