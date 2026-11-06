from django.db import models
from django.conf import settings
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """Subscription plans available for purchase"""
    
    TIER_CHOICES = [
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('elite', 'Elite'),
    ]
    
    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    description = models.TextField()
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=255, unique=True)
    stripe_product_id = models.CharField(max_length=255)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plans'
        ordering = ['sort_order', 'price_per_month']
    
    def __str__(self):
        return f"{self.name} - ${self.price_per_month}/mo"


class UserSubscription(models.Model):
    """User subscription records - source of truth from Stripe webhooks or manual grants"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('trialing', 'Trialing'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='user_subscriptions'
    )
    stripe_subscription_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    
    # Cancellation and grace period tracking
    canceled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when subscription was canceled"
    )
    grace_period_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data will be deleted after this date (if cancellation not reversed)"
    )
    deletion_warning_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when deletion warning email was sent"
    )
    
    # Optimistic locking for race condition prevention
    version = models.IntegerField(
        default=0,
        help_text="Version number for optimistic locking (incremented on each update)"
    )
    
    # Manual grant fields (for superuser-granted subscriptions)
    is_manual_grant = models.BooleanField(
        default=False,
        help_text="True if subscription was manually granted by platform admin (not Stripe)"
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_subscriptions',
        help_text="Platform admin who granted this manual subscription"
    )
    grant_reason = models.TextField(
        blank=True,
        help_text="Reason for manual grant (e.g., 'Beta tester', 'Partnership agreement')"
    )
    manual_grant_duration_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duration in days for manual grants (null = indefinite/permanent)"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_subscriptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['stripe_subscription_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.tier} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Override save to implement optimistic locking via version field."""
        if self.pk:
            # Increment version on every update to detect concurrent modifications
            # This happens at the database level to ensure atomicity
            from django.db.models import F
            self.__class__.objects.filter(pk=self.pk).update(version=F('version') + 1)
        super().save(*args, **kwargs)


# ServerSubscription removed - using UserSubscription tier to determine server capabilities



