from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class PlatformChoice(models.Model):
    """Dynamic platform choices managed by superuser."""
    
    name = models.CharField(max_length=50, unique=True, help_text="Platform name (e.g., Discord, Telegram)")
    is_active = models.BooleanField(default=True, help_text="Whether this platform is available for selection")
    display_order = models.IntegerField(default=0, help_text="Order in which platforms are displayed")
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'platform_choices'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class Server(models.Model):
    """Server/Trading Community model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_servers'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    logo_url = models.URLField(
        blank=True,
        null=True,
        max_length=500,
        help_text="Server logo URL from R2 storage"
    )
    platform = models.ForeignKey(
        PlatformChoice,
        on_delete=models.PROTECT,
        related_name='servers',
        help_text="Platform where this server/community exists"
    )
    invite_link = models.URLField(blank=True, null=True, help_text="Invite/join link for the server")
    website = models.URLField(blank=True, null=True, help_text="Server website URL")
    twitter_url = models.URLField(blank=True, null=True, help_text="Twitter/X profile URL")
    youtube_url = models.URLField(blank=True, null=True, help_text="YouTube channel URL")
    instagram_url = models.URLField(blank=True, null=True, help_text="Instagram profile URL")
    support_email = models.EmailField(blank=True, null=True, help_text="Support contact email")
    market_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="List of market categories this server focuses on (e.g., ['Futures', 'Forex', 'Crypto'])"
    )
    is_verified = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True, null=True)
    payout_submissions_paused = models.BooleanField(
        default=False,
        help_text=" Payout submissions can be paused for moderation purposes"
    )
    paused_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paused_servers'
    )
    paused_at = models.DateTimeField(null=True, blank=True)
    needs_ranking_update = models.BooleanField(default=False, help_text="Flag for batch ranking recalculation")
    
    # Soft delete fields (for subscription cancellation)
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag - server marked for deletion after grace period"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when server was soft deleted"
    )
    deletion_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Reason for deletion (e.g., 'subscription_canceled', 'policy_violation')"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'servers'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class ServerMember(models.Model):
    """Server membership tracking."""
    
    server = models.ForeignKey(
        Server,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='server_memberships'
    )
    joined_at = models.DateTimeField(default=timezone.now)
    total_verified_payouts = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    total_submissions = models.IntegerField(default=0)
    last_submission_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'server_members'
        unique_together = ['server', 'user']
        ordering = ['-total_verified_payouts']
    
    def __str__(self):
        return f"{self.user.username} @ {self.server.name}"
