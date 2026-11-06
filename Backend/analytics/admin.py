from django.contrib import admin
from .models import ServerAnalyticsDaily, GlobalAnalyticsDaily, ServerRanking


@admin.register(ServerAnalyticsDaily)
class ServerAnalyticsDailyAdmin(admin.ModelAdmin):
    list_display = ['server', 'date', 'total_payout_volume', 'verified_count']
    list_filter = ['date']
    search_fields = ['server__name']
    raw_id_fields = ['server']
    date_hierarchy = 'date'


@admin.register(GlobalAnalyticsDaily)
class GlobalAnalyticsDailyAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_servers', 'total_verified_payouts', 'total_payout_volume']
    list_filter = ['date']
    date_hierarchy = 'date'


@admin.register(ServerRanking)
class ServerRankingAdmin(admin.ModelAdmin):
    list_display = ['server', 'global_rank', 'monthly_rank', 'weekly_rank', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['server__name']
    raw_id_fields = ['server']
    ordering = ['global_rank']
