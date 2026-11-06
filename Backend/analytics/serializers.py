from rest_framework import serializers
from .models import ServerAnalyticsDaily, GlobalAnalyticsDaily, ServerRanking
from servers.serializers import ServerSerializer


class ServerAnalyticsDailySerializer(serializers.ModelSerializer):
    """Serializer for ServerAnalyticsDaily model."""
    
    server = ServerSerializer(read_only=True)
    
    class Meta:
        model = ServerAnalyticsDaily
        fields = [
            'id', 'server', 'date', 'total_payout_volume',
            'verified_count', 'market_breakdown', 'instrument_breakdown'
        ]


class GlobalAnalyticsDailySerializer(serializers.ModelSerializer):
    """Serializer for GlobalAnalyticsDaily model."""
    
    class Meta:
        model = GlobalAnalyticsDaily
        fields = [
            'id', 'date', 'total_servers', 'total_verified_payouts',
            'total_payout_volume', 'top_servers', 'top_instruments'
        ]


class ServerRankingSerializer(serializers.ModelSerializer):
    """Serializer for ServerRanking model."""
    
    server = ServerSerializer(read_only=True)
    
    class Meta:
        model = ServerRanking
        fields = [
            'id', 'server', 'global_rank', 'monthly_rank',
            'weekly_rank', 'last_updated'
        ]
