from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class ServerAnalyticsDaily(models.Model):
    """Daily analytics aggregated per server."""
    
    server = models.ForeignKey(
        'servers.Server',
        on_delete=models.CASCADE,
        related_name='daily_analytics'
    )
    date = models.DateField()
    total_payout_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    verified_count = models.IntegerField(default=0)
    market_breakdown = models.JSONField(default=dict, blank=True)
    instrument_breakdown = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'server_analytics_daily'
        unique_together = ['server', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['server', 'date']),
        ]
    
    def __str__(self):
        return f"{self.server.name} - {self.date}"


class GlobalAnalyticsDaily(models.Model):
    """Daily analytics for the entire platform."""
    
    date = models.DateField(unique=True)
    total_servers = models.IntegerField(default=0)
    total_verified_payouts = models.IntegerField(default=0)
    total_payout_volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    top_servers = models.JSONField(default=list, blank=True)
    top_instruments = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = 'global_analytics_daily'
        ordering = ['-date']
    
    def __str__(self):
        return f"Global Analytics - {self.date}"


class ServerRanking(models.Model):
    """Server rankings based on performance metrics."""
    
    server = models.OneToOneField(
        'servers.Server',
        on_delete=models.CASCADE,
        related_name='ranking'
    )
    global_rank = models.IntegerField(null=True, blank=True)
    monthly_rank = models.IntegerField(null=True, blank=True)
    weekly_rank = models.IntegerField(null=True, blank=True)
    
    # Comprehensive Scores (0-100)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    performance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    growth_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    engagement_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    diversity_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    last_updated = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'server_rankings'
        ordering = ['global_rank']
    
    def __str__(self):
        return f"{self.server.name} - Rank: {self.global_rank}"


class ServerAnalytics(models.Model):
    """
    Comprehensive analytics for a server's trading activity.
    
    Updated automatically when payouts are approved.
    Tracks market categories, instruments, and daily performance.
    """
    server = models.OneToOneField('servers.Server', on_delete=models.CASCADE, related_name='comprehensive_analytics')
    
    # Volume stats
    total_volume = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    total_payouts = models.IntegerField(default=0)
    unique_traders = models.IntegerField(default=0)
    
    # Market breakdown (JSON)
    # Example: {"Futures": 50000.00, "Forex": 30000.00, "Crypto": 20000.00}
    market_breakdown = models.JSONField(default=dict, blank=True)
    
    # Instrument breakdown (JSON)
    # Example: {"ES": 25000.00, "NQ": 25000.00, "EURUSD": 30000.00}
    instrument_breakdown = models.JSONField(default=dict, blank=True)
    
    # Daily breakdown (JSON)
    # Example: {"2024-01-15": 5000.00, "2024-01-16": 7500.00}
    daily_breakdown = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'server_analytics_comprehensive'
        verbose_name_plural = 'Server Analytics'
    
    def __str__(self):
        return f'Analytics for {self.server.name}'
    
    def get_top_market(self):
        """Get the market with highest volume."""
        if not self.market_breakdown:
            return None
        return max(self.market_breakdown.items(), key=lambda x: x[1])[0]
    
    def get_top_instrument(self):
        """Get the instrument with highest volume."""
        if not self.instrument_breakdown:
            return None
        return max(self.instrument_breakdown.items(), key=lambda x: x[1])[0]


class UserAnalytics(models.Model):
    """
    Comprehensive analytics for a user's trading activity across all servers.
    
    Updated automatically when payouts are approved.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='analytics')
    
    # Volume stats
    total_volume = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    total_payouts = models.IntegerField(default=0)
    servers_count = models.IntegerField(default=0)  # Servers where user has submissions
    
    # Market breakdown (JSON)
    market_breakdown = models.JSONField(default=dict, blank=True)
    
    # Instrument breakdown (JSON)
    instrument_breakdown = models.JSONField(default=dict, blank=True)
    
    # Best performance
    best_month = models.DateField(null=True, blank=True)
    best_month_volume = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'))
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_analytics'
        verbose_name_plural = 'User Analytics'
    
    def __str__(self):
        return f'Analytics for {self.user.username}'
    
    def get_top_market(self):
        """Get the market with highest volume."""
        if not self.market_breakdown:
            return None
        return max(self.market_breakdown.items(), key=lambda x: x[1])[0]
    
    def get_top_instrument(self):
        """Get the instrument with highest volume."""
        if not self.instrument_breakdown:
            return None
        return max(self.instrument_breakdown.items(), key=lambda x: x[1])[0]
