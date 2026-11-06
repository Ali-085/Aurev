from django.contrib import admin
from .models import PayoutSubmission, PayoutSubmissionDetail, PayoutReviewLog
from .prop_firms import PropFirm


@admin.register(PropFirm)
class PropFirmAdmin(admin.ModelAdmin):
    """Admin interface for managing prop firms."""
    
    list_display = ['name', 'slug', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'is_active', 'display_order')
        }),
        ('Optional Details', {
            'fields': ('logo_url', 'website_url'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make slug read-only when editing existing objects."""
        if obj:  # Editing existing object
            return self.readonly_fields + ('slug',)
        return self.readonly_fields


class PayoutSubmissionDetailInline(admin.StackedInline):
    model = PayoutSubmissionDetail
    can_delete = False


@admin.register(PayoutSubmission)
class PayoutSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'server', 'prop_firm', 'amount', 'currency', 'market_category',
        'status', 'payout_date', 'created_at'
    ]
    list_filter = ['status', 'prop_firm', 'market_category', 'currency', 'created_at', 'payout_date']
    search_fields = ['user__username', 'server__name', 'prop_firm__name', 'instrument']
    raw_id_fields = ['server', 'user', 'reviewer']
    readonly_fields = ['created_at', 'reviewed_at']
    inlines = [PayoutSubmissionDetailInline]
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('server', 'user', 'prop_firm', 'payout_date', 'screenshot')
        }),
        ('Trading Details', {
            'fields': ('amount', 'currency', 'market_category', 'instrument')
        }),
        ('Review Status', {
            'fields': ('status', 'reviewer', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PayoutSubmissionDetail)
class PayoutSubmissionDetailAdmin(admin.ModelAdmin):
    list_display = ['payout_submission', 'duplicate_flag', 'risk_score']
    list_filter = ['duplicate_flag', 'risk_score']
    raw_id_fields = ['payout_submission']


@admin.register(PayoutReviewLog)
class PayoutReviewLogAdmin(admin.ModelAdmin):
    list_display = ['payout_submission', 'reviewer_user', 'action', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['reviewer_user__username', 'reason']
    raw_id_fields = ['payout_submission', 'reviewer_user']
    readonly_fields = ['created_at']
