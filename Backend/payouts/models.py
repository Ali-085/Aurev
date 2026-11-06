from django.db import models
from django.conf import settings
from django.utils import timezone
from .prop_firms import PropFirm


class PayoutSubmission(models.Model):
    """Payout submission with screenshot proof."""
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Suspicious', 'Suspicious'),
    ]
    
    # Note: Market categories are now dynamically managed in platform_admin.MarketCategory
    # Platform owner can add/remove/enable/disable markets through the admin panel
    # Validation is done in serializers against the database
    
    server = models.ForeignKey(
        'servers.Server',
        on_delete=models.CASCADE,
        related_name='payout_submissions'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payout_submissions'
    )
    prop_firm = models.ForeignKey(
        PropFirm,
        on_delete=models.PROTECT,
        related_name='payout_submissions',
        help_text="The prop firm that issued this payout"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    market_category = models.CharField(
        max_length=50,
        help_text="Market category from platform_admin.MarketCategory (validated dynamically)"
    )
    instrument = models.CharField(max_length=100)
    # Proof of payout screenshot
    screenshot = models.ImageField(
        upload_to='payouts/%Y/%m/',
        max_length=500,
        help_text="Proof of payout (JPG, PNG, WebP only)"
    )
    # Private verification image (bank invoice/transaction) - accessible only to platform staff
    private_verification_image = models.ImageField(
        upload_to='payouts/private/%Y/%m/',
        max_length=500,
        help_text="Bank invoice/transaction screenshot (required) - only visible to admin/moderator/superuser"
    )
    payout_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_payouts'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # Discord username/contact info for moderators to contact submitter if needed
    discord_contact_info = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Discord username or contact info (optional, for staff use only)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'payout_submissions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['server', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['payout_date']),
        ]
        # SECURITY: Prevent duplicate payout submissions across servers
        # A trader cannot resubmit the same payout (same amount, market, prop_firm, instrument, date)
        unique_together = [
            ('user', 'amount', 'market_category', 'prop_firm', 'instrument', 'payout_date')
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency} ({self.status})"


class PayoutSubmissionDetail(models.Model):
    """Additional details and metadata for payout submissions."""
    
    payout_submission = models.OneToOneField(
        PayoutSubmission,
        on_delete=models.CASCADE,
        related_name='details'
    )
    auto_detected_time = models.TimeField(null=True, blank=True)
    duplicate_flag = models.BooleanField(default=False)
    risk_score = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'payout_submission_details'
    
    def __str__(self):
        return f"Details for {self.payout_submission}"


class PayoutReviewLog(models.Model):
    """Log of all review actions on payout submissions."""
    
    ACTION_CHOICES = [
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Restored', 'Restored'),
        ('MarkedSuspicious', 'Marked Suspicious'),
    ]
    
    payout_submission = models.ForeignKey(
        PayoutSubmission,
        on_delete=models.CASCADE,
        related_name='review_logs'
    )
    reviewer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_actions'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    reason = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'payout_review_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action} by {self.reviewer_user.username} on {self.created_at}"
