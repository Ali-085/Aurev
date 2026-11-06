from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.db.models import Sum, Count
from datetime import timedelta
from django.utils import timezone
from .models import ServerAnalyticsDaily, GlobalAnalyticsDaily, ServerRanking
from .serializers import (
    ServerAnalyticsDailySerializer,
    GlobalAnalyticsDailySerializer,
    ServerRankingSerializer
)


class ServerAnalyticsDailyViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ServerAnalyticsDaily model."""
    
    queryset = ServerAnalyticsDaily.objects.all()
    serializer_class = ServerAnalyticsDailySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['server', 'date']
    ordering_fields = ['date', 'total_payout_volume', 'verified_count']
    
    @action(detail=False, methods=['get'])
    def server_trends(self, request):
        """Get trend data for a specific server."""
        server_id = request.query_params.get('server_id')
        days = int(request.query_params.get('days', 30))
        
        if not server_id:
            return Response({'error': 'server_id parameter is required'}, status=400)
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        analytics = ServerAnalyticsDaily.objects.filter(
            server_id=server_id,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        serializer = self.get_serializer(analytics, many=True)
        return Response(serializer.data)


class GlobalAnalyticsDailyViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for GlobalAnalyticsDaily model."""
    
    queryset = GlobalAnalyticsDaily.objects.all()
    serializer_class = GlobalAnalyticsDailySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['date']
    ordering_fields = ['date']
    
    @action(detail=False, methods=['get'])
    def platform_trends(self, request):
        """Get platform-wide trends."""
        days = int(request.query_params.get('days', 30))
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        analytics = GlobalAnalyticsDaily.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        serializer = self.get_serializer(analytics, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def current_stats(self, request):
        """Get current platform statistics."""
        from servers.models import Server
        from payouts.models import PayoutSubmission
        
        total_servers = Server.objects.filter(suspended=False).count()
        verified_servers = Server.objects.filter(is_verified=True, suspended=False).count()
        total_payouts = PayoutSubmission.objects.filter(status='Approved').count()
        total_volume = PayoutSubmission.objects.filter(
            status='Approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'total_servers': total_servers,
            'verified_servers': verified_servers,
            'total_verified_payouts': total_payouts,
            'total_payout_volume': float(total_volume)
        })


class ServerRankingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ServerRanking model."""
    
    queryset = ServerRanking.objects.all()
    serializer_class = ServerRankingSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [OrderingFilter]
    ordering_fields = ['global_rank', 'monthly_rank', 'weekly_rank']
    
    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Get server leaderboard."""
        period = request.query_params.get('period', 'global')
        limit = int(request.query_params.get('limit', 50))
        
        if period == 'weekly':
            rankings = ServerRanking.objects.order_by('weekly_rank')[:limit]
        elif period == 'monthly':
            rankings = ServerRanking.objects.order_by('monthly_rank')[:limit]
        else:
            rankings = ServerRanking.objects.order_by('global_rank')[:limit]
        
        serializer = self.get_serializer(rankings, many=True)
        return Response(serializer.data)
