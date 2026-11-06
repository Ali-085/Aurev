"""
Prop Firm Model - Superuser-managed list of prop trading firms.

Platform owner can add/remove/enable prop firms through admin panel.
Used in payout submissions to identify the firm that issued the payout.
"""
from django.db import models


class PropFirm(models.Model):
    """Prop trading firm that issues payouts to traders."""
    
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Official name of the prop firm (e.g., 'FTMO', 'The5%ers', 'TopstepTrader')"
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text="URL-friendly version of the name"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active firms appear in submission forms"
    )
    logo_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional: URL to firm's logo for display"
    )
    website_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Optional: Official website of the prop firm"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order in dropdown (lower = higher in list)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prop_firms'
        ordering = ['display_order', 'name']
        verbose_name = 'Prop Firm'
        verbose_name_plural = 'Prop Firms'
        indexes = [
            models.Index(fields=['is_active', 'display_order']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
