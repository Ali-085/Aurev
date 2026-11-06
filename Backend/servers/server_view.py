"""
Server View API

This provides server analytics and data with mixed access levels:
- Public endpoints: check_membership, join_server, leave_server
- Member-only endpoints: dashboard, leaderboard, heatmap, gallery, 
  moderation_stats, global_comparison

PERMISSIONS:
- Public: Anyone can check membership status and join servers
- Member-only: Dashboard and analytics require server membership
- Owner-only: Managed through separate ServerOwnerAnalytics

FEATURES:
- Server dashboard with total payouts, graphs, breakdowns (Members)
- Top traders leaderboard (Members)
- Market breakdown pie charts (Members)
- Submission heatmaps (Members)
- Screenshot gallery (Members)
- Moderation stats (Members)
- Global server comparisons (Members)
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from users.permissions import IsEmailVerified
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

from servers.models import Server, ServerMember
from payouts.models import PayoutSubmission
from payouts.serializers import PayoutSubmissionSerializer
from analytics.models import ServerAnalytics, ServerRanking, GlobalAnalyticsDaily


class IsServerMember(BasePermission):
    """
    Permission class to check if user is a member of the server.
    """
    message = 'You must be a member of this server to access this resource.'
    
    def has_object_permission(self, request, view, obj):
        # obj is the Server instance
        if not request.user.is_authenticated:
            return False
        
        # Check if user is owner
        if obj.owner_user == request.user:
            return True
        
        # Check if user is a member
        return ServerMember.objects.filter(
            server=obj,
            user=request.user
        ).exists()


class ServerPublicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Server ViewSet with mixed access levels.
    
    Public endpoints:
    - check_membership: Check if user is a member
    - join_server: Join the server
    - leave_server: Leave the server
    
    Member-only endpoints (require IsAuthenticated + IsServerMember):
    - dashboard: Comprehensive server analytics
    - leaderboard: Top traders ranking
    - heatmap: Submission activity patterns
    - gallery: Screenshot collection
    - moderation_stats: Transparency metrics
    - global_comparison: Server vs platform stats
    """
    
    permission_classes = [AllowAny]
    lookup_field = 'pk'
    
    def get_queryset(self):
        """Get all active (non-suspended) servers."""
        # Public server browsing - exclude suspended and soft-deleted servers
        return Server.objects.filter(suspended=False, is_deleted=False)
    
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def public_dashboard(self, request, pk=None):
        """
        Get public server dashboard data (restricted data for marketing).
        Public access - anyone can view.
        
        Returns same structure as dashboard but accessible to everyone.
        Used by ServerPublicView page to show limited data and drive subscriptions.
        """
        # Call dashboard with a mock request that bypasses permission checks
        # by directly executing the dashboard logic
        server = self.get_object()
        
        # Create a temporary override to skip permission checks
        original_action = self.action
        self.action = 'dashboard'
        try:
            # Call the dashboard method directly
            response = self._get_dashboard_data(request, server)
            return response
        finally:
            self.action = original_action
    
    def _get_dashboard_data(self, request, server):
        """
        Internal method containing dashboard logic.
        Used by both public_dashboard and dashboard endpoints.
        """
        
        try:
            # Get comprehensive analytics
            analytics = ServerAnalytics.objects.get(server=server)
        except ServerAnalytics.DoesNotExist:
            analytics = None
        
        # Get approved submissions for calculations
        approved_submissions = PayoutSubmission.objects.filter(
            server=server,
            status='Approved'
        )
        
        # Basic stats
        total_volume = approved_submissions.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        total_submissions = approved_submissions.count()
        
        # Unique traders
        unique_traders = approved_submissions.values('user').distinct().count()
        
        # Time-based data (last 30 days for graphs)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        
        # Daily breakdown for graph
        daily_data = approved_submissions.filter(
            payout_date__gte=thirty_days_ago
        ).values('payout_date').annotate(
            volume=Sum('amount'),
            count=Count('id')
        ).order_by('payout_date')
        
        daily_graph = [
            {
                'date': item['payout_date'].isoformat(),
                'volume': float(item['volume']),
                'count': item['count']
            }
            for item in daily_data
        ]
        
        # Weekly aggregation (last 12 weeks)
        twelve_weeks_ago = timezone.now().date() - timedelta(weeks=12)
        weekly_data = []
        
        current_date = twelve_weeks_ago
        while current_date <= timezone.now().date():
            week_end = current_date + timedelta(days=7)
            week_submissions = approved_submissions.filter(
                payout_date__gte=current_date,
                payout_date__lt=week_end
            )
            week_volume = week_submissions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            week_count = week_submissions.count()
            
            weekly_data.append({
                'week_start': current_date.isoformat(),
                'volume': float(week_volume),
                'count': week_count
            })
            current_date = week_end
        
        # Monthly aggregation (last 12 months)
        twelve_months_ago = timezone.now().date() - timedelta(days=365)
        monthly_data = defaultdict(lambda: {'volume': 0, 'count': 0})
        
        for submission in approved_submissions.filter(payout_date__gte=twelve_months_ago):
            month_key = submission.payout_date.strftime('%Y-%m')
            monthly_data[month_key]['volume'] += float(submission.amount)
            monthly_data[month_key]['count'] += 1
        
        monthly_graph = [
            {
                'month': month,
                'volume': data['volume'],
                'count': data['count']
            }
            for month, data in sorted(monthly_data.items())
        ]
        
        # Market breakdown (for pie chart)
        market_breakdown = approved_submissions.values('market_category').annotate(
            volume=Sum('amount'),
            count=Count('id')
        ).order_by('-volume')
        
        market_pie = [
            {
                'category': item['market_category'],
                'volume': float(item['volume']),
                'count': item['count'],
                'percentage': float(item['volume']) / float(total_volume) * 100 if total_volume > 0 else 0
            }
            for item in market_breakdown
        ]
        
        # Instrument breakdown (top 10)
        instrument_breakdown = approved_submissions.values('instrument').annotate(
            volume=Sum('amount'),
            count=Count('id')
        ).order_by('-volume')[:10]
        
        instrument_data = [
            {
                'instrument': item['instrument'],
                'volume': float(item['volume']),
                'count': item['count']
            }
            for item in instrument_breakdown
        ]
        
        # Top performance day
        best_day = approved_submissions.values('payout_date').annotate(
            volume=Sum('amount')
        ).order_by('-volume').first()
        
        top_day = None
        if best_day:
            top_day = {
                'date': best_day['payout_date'].isoformat(),
                'volume': float(best_day['volume'])
            }
        
        # Global ranking with scores
        try:
            ranking = ServerRanking.objects.get(server=server)
            global_rank = ranking.global_rank
            monthly_rank = ranking.monthly_rank
            weekly_rank = ranking.weekly_rank
            
            # Get full ranking data with scores from RankingService
            from servers.services.ranking_service import RankingService
            all_rankings = RankingService.get_rankings()
            
            # Find this server's ranking entry
            server_ranking_data = next(
                (r for r in all_rankings if r['server']['id'] == str(server.id)),
                None
            )
            
            # Extract scores if found
            if server_ranking_data:
                ranking_scores = server_ranking_data.get('scores', {})
                total_score = server_ranking_data.get('total_score', 0)
            else:
                # Fallback: no scores available
                ranking_scores = None
                total_score = None
        except ServerRanking.DoesNotExist:
            global_rank = None
            monthly_rank = None
            weekly_rank = None
            ranking_scores = None
            total_score = None
        
        # Recent activity (last 7 days)
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        recent_volume = approved_submissions.filter(
            payout_date__gte=seven_days_ago
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        recent_count = approved_submissions.filter(
            payout_date__gte=seven_days_ago
        ).count()
        
        # Calculate Server Metrics Overview (Institutional Metrics)
        # Active submitters (last 30 days)
        active_submitters = approved_submissions.filter(
            payout_date__gte=thirty_days_ago
        ).values('user').distinct().count()
        
        # Approval rate (last 3 months)
        three_months_ago = timezone.now().date() - timedelta(days=90)
        recent_submissions = PayoutSubmission.objects.filter(
            server=server,
            created_at__gte=three_months_ago
        )
        total_recent = recent_submissions.count()
        approved_recent = recent_submissions.filter(status='Approved').count()
        approval_rate = (approved_recent / total_recent * 100) if total_recent > 0 else 0
        
        # Growth rate (change in verified payout count over last 30 days)
        sixty_days_ago = timezone.now().date() - timedelta(days=60)
        previous_period_count = approved_submissions.filter(
            payout_date__gte=sixty_days_ago,
            payout_date__lt=thirty_days_ago
        ).count()
        current_period_count = approved_submissions.filter(
            payout_date__gte=thirty_days_ago
        ).count()
        
        if previous_period_count > 0:
            growth_rate = ((current_period_count - previous_period_count) / previous_period_count) * 100
        else:
            growth_rate = 100.0 if current_period_count > 0 else 0.0
        
        # Server Health Score (from ServerRanking or calculate if not exists)
        health_score = None
        if global_rank and ranking:
            # Calculate health score based on ranking metrics
            # This should match the radar chart calculation from Servers.jsx
            try:
                from analytics.ranking import calculate_server_health_score
                health_score = calculate_server_health_score(server)
            except:
                # Fallback: Simple health calculation
                if global_rank <= 10:
                    health_score = 95.0
                elif global_rank <= 50:
                    health_score = 85.0
                elif global_rank <= 100:
                    health_score = 75.0
                else:
                    health_score = 60.0
        
        # Get logo URL (already a full URL from R2 storage)
        logo_url = server.logo_url if server.logo_url else None
        
        # Top 5 Traders (for leaderboard on public view) - Respecting Privacy Settings
        from utils.privacy import get_public_trader_view
        
        top_traders_data = []
        top_members = ServerMember.objects.filter(
            server=server,
            total_verified_payouts__gt=0
        ).select_related('user').order_by('-total_verified_payouts')[:5]
        
        for rank, member in enumerate(top_members, start=1):
            member_submissions = approved_submissions.filter(user=member.user)
            trader_volume = member_submissions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
            trader_count = member_submissions.count()
            
            # Get trader's best market
            best_market = member_submissions.values('market_category').annotate(
                volume=Sum('amount')
            ).order_by('-volume').first()
            
            # Apply privacy settings
            trader_view = get_public_trader_view(
                user=member.user,
                requesting_user=request.user if request.user.is_authenticated else None
            )
            
            # If trader has privacy enabled, anonymize their data
            if trader_view['is_private'] and not (request.user.is_authenticated and request.user.id == member.user.id):
                top_traders_data.append({
                    'rank': rank,
                    'user_id': str(member.user.id),
                    'username': trader_view['username'],  # Will be masked (e.g., "Private Trader #abc123")
                    'profile_url': f'/trader/{str(member.user.id)}/public',
                    'total_volume': float(trader_volume),
                    'submission_count': trader_count,
                    'best_market': best_market['market_category'] if best_market else None,
                    'contribution_percentage': (float(trader_volume) / float(total_volume) * 100) if total_volume > 0 else 0,
                    'is_private': True  # Flag to indicate masked data
                })
            else:
                top_traders_data.append({
                    'rank': rank,
                    'user_id': str(member.user.id),
                    'username': trader_view['username'],
                    'profile_url': f'/trader/{str(member.user.id)}/public',
                    'total_volume': float(trader_volume),
                    'submission_count': trader_count,
                    'best_market': best_market['market_category'] if best_market else None,
                    'contribution_percentage': (float(trader_volume) / float(total_volume) * 100) if total_volume > 0 else 0,
                    'is_private': False
                })
        
        # Active submitters trend (last 12 weeks)
        submitter_trend = []
        current_date = twelve_weeks_ago
        while current_date <= timezone.now().date():
            week_end = current_date + timedelta(days=7)
            week_submitters = approved_submissions.filter(
                payout_date__gte=current_date,
                payout_date__lt=week_end
            ).values('user').distinct().count()
            
            submitter_trend.append({
                'week_start': current_date.isoformat(),
                'active_submitters': week_submitters
            })
            current_date = week_end
        
        # Historical Stats Calculation
        # Lifetime stats (all-time)
        all_time_submissions = approved_submissions.aggregate(
            lifetime_volume=Sum('amount'),
            lifetime_count=Count('id')
        )
        lifetime_volume = all_time_submissions['lifetime_volume'] or Decimal('0')
        lifetime_count = all_time_submissions['lifetime_count'] or 0
        
        # Calculate monthly averages across all months with data
        all_monthly_data = defaultdict(lambda: {'volume': Decimal('0'), 'count': 0})
        for submission in approved_submissions:
            month_key = submission.payout_date.strftime('%Y-%m')
            all_monthly_data[month_key]['volume'] += submission.amount
            all_monthly_data[month_key]['count'] += 1
        
        monthly_volumes = [data['volume'] for data in all_monthly_data.values()]
        monthly_counts = [data['count'] for data in all_monthly_data.values()]
        
        # Monthly average
        avg_monthly_volume = sum(monthly_volumes) / len(monthly_volumes) if monthly_volumes else Decimal('0')
        avg_monthly_count = sum(monthly_counts) / len(monthly_counts) if monthly_counts else 0
        
        # Peak and lowest months
        peak_month = None
        lowest_month = None
        if all_monthly_data:
            sorted_months = sorted(all_monthly_data.items(), key=lambda x: x[1]['volume'], reverse=True)
            peak_month = {
                'month': sorted_months[0][0],
                'volume': float(sorted_months[0][1]['volume']),
                'count': sorted_months[0][1]['count']
            }
            lowest_month = {
                'month': sorted_months[-1][0],
                'volume': float(sorted_months[-1][1]['volume']),
                'count': sorted_months[-1][1]['count']
            }
        
        # Growth trajectory (compare first 3 months vs last 3 months)
        sorted_month_keys = sorted(all_monthly_data.keys())
        growth_trajectory = 'stable'
        trajectory_percentage = 0.0
        
        if len(sorted_month_keys) >= 6:
            first_three = sum(all_monthly_data[month]['volume'] for month in sorted_month_keys[:3])
            last_three = sum(all_monthly_data[month]['volume'] for month in sorted_month_keys[-3:])
            
            if first_three > 0:
                trajectory_percentage = ((last_three - first_three) / first_three) * 100
                if trajectory_percentage > 20:
                    growth_trajectory = 'growing'
                elif trajectory_percentage < -20:
                    growth_trajectory = 'declining'
        
        # Stability rating (based on variance in monthly volumes)
        stability_rating = 'N/A'
        stability_score = 0
        if len(monthly_volumes) >= 3:
            avg_vol = sum(monthly_volumes) / len(monthly_volumes)
            variance = sum((vol - avg_vol) ** 2 for vol in monthly_volumes) / len(monthly_volumes)
            std_dev = variance ** Decimal('0.5')
            coefficient_of_variation = (std_dev / avg_vol * 100) if avg_vol > 0 else Decimal('0')
            
            if coefficient_of_variation < 20:
                stability_rating = 'Very Stable'
                stability_score = 95
            elif coefficient_of_variation < 40:
                stability_rating = 'Stable'
                stability_score = 80
            elif coefficient_of_variation < 60:
                stability_rating = 'Moderate'
                stability_score = 60
            else:
                stability_rating = 'Volatile'
                stability_score = 35
        
        # Submission accuracy history (last 6 months)
        six_months_ago = timezone.now().date() - timedelta(days=180)
        accuracy_history = []
        
        current_month = six_months_ago
        while current_month <= timezone.now().date():
            month_end = (current_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_submissions = PayoutSubmission.objects.filter(
                server=server,
                created_at__gte=current_month,
                created_at__lte=month_end
            )
            
            total_month = month_submissions.count()
            approved_month = month_submissions.filter(status='Approved').count()
            accuracy = (approved_month / total_month * 100) if total_month > 0 else 0
            
            accuracy_history.append({
                'month': current_month.strftime('%Y-%m'),
                'accuracy': round(accuracy, 1),
                'total_submissions': total_month,
                'approved_submissions': approved_month
            })
            
            current_month = month_end + timedelta(days=1)
        
        historical_stats = {
            'lifetime_volume': float(lifetime_volume),
            'lifetime_count': lifetime_count,
            'avg_monthly_volume': float(avg_monthly_volume),
            'avg_monthly_count': round(avg_monthly_count, 1),
            'peak_month': peak_month,
            'lowest_month': lowest_month,
            'growth_trajectory': growth_trajectory,
            'trajectory_percentage': round(float(trajectory_percentage), 2),
            'stability_rating': stability_rating,
            'stability_score': stability_score,
            'accuracy_history': accuracy_history
        }
        
        # Recent Payout Feed (last 20 verified payouts)
        recent_payouts = approved_submissions.select_related(
            'user', 'prop_firm'
        ).order_by('-payout_date', '-created_at')[:20]
        
        payout_feed = []
        for submission in recent_payouts:
            # Apply privacy settings for trader
            trader_view = get_public_trader_view(
                user=submission.user,
                requesting_user=request.user if request.user.is_authenticated else None
            )
            
            # Get screenshot URL
            screenshot_url = None
            if submission.screenshot:
                screenshot_url = request.build_absolute_uri(submission.screenshot.url)
            
            payout_feed.append({
                'id': str(submission.id),
                'amount': float(submission.amount),
                'market_category': submission.market_category,
                'instrument': submission.instrument,
                'payout_date': submission.payout_date.isoformat(),
                'created_at': submission.created_at.isoformat(),
                'trader': {
                    'id': str(submission.user.id),
                    'username': trader_view['username'],
                    'is_private': trader_view['is_private']
                },
                'prop_firm': {
                    'id': str(submission.prop_firm.id),
                    'name': submission.prop_firm.name
                } if submission.prop_firm else None,
                'screenshot_url': screenshot_url,
                'status': submission.status
                # SECURITY: reviewer, reviewed_at, review_logs NOT exposed in public view
            })
        
        return Response({
            'server': {
                'id': str(server.id),
                'name': server.name,
                'description': server.description,
                'platform': server.platform.name if server.platform else None,
                'logo_url': logo_url,
                'invite_link': server.invite_link,
                'website': server.website,
                'twitter_url': server.twitter_url,
                'youtube_url': server.youtube_url,
                'instagram_url': server.instagram_url,
                'support_email': server.support_email,
                'market_categories': server.market_categories or [],
                'is_verified': server.is_verified,
                'created_at': server.created_at.isoformat(),
                'owner_id': str(server.owner_user.id),  # For join button logic
                # Add fields needed for radar chart calculations
                'total_verified_payouts': float(total_volume),
                'total_submissions': total_submissions,
                'member_count': ServerMember.objects.filter(server=server).count(),
                # Count rejected submissions (without exposing rejection reasons)
                'suspicious_count': PayoutSubmission.objects.filter(
                    server=server,
                    status='Rejected'
                ).count()
            },
            'stats': {
                'total_volume': float(total_volume),
                'total_submissions': total_submissions,
                'unique_traders': unique_traders,
                'recent_volume_7d': float(recent_volume),
                'recent_count_7d': recent_count,
            },
            'metrics_overview': {
                'total_verified_volume': float(total_volume),
                'verified_payout_count': total_submissions,
                'active_submitters_30d': active_submitters,
                'approval_rate_3m': round(approval_rate, 2),
                'growth_rate_30d': round(growth_rate, 2),
                'health_score': round(health_score, 2) if health_score else None
            },
            'graphs': {
                'daily': daily_graph,
                'weekly': weekly_data,
                'monthly': monthly_graph,
                'submitter_trend': submitter_trend
            },
            'breakdowns': {
                'markets': market_pie,
                'instruments': instrument_data
            },
            'top_day': top_day,
            'top_traders': top_traders_data,
            'recent_payouts': payout_feed,
            'historical_stats': historical_stats,
            'rankings': {
                'global_rank': global_rank,
                'monthly_rank': monthly_rank,
                'weekly_rank': weekly_rank,
                'scores': ranking_scores,
                'total_score': total_score
            }
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsEmailVerified, IsServerMember, IsEmailVerified])
    def dashboard(self, request, pk=None):
        """
        Get comprehensive server dashboard data.
        Member-only access.
        
        Returns:
        - Total payout volume
        - Total submissions (approved)
        - Total traders
        - Daily/weekly/monthly graphs
        - Market breakdown
        - Instrument breakdown
        - Top performance day
        - Recent activity
        - Global rank
        """
        server = self.get_object()
        return self._get_dashboard_data(request, server)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated ,IsEmailVerified ,IsServerMember])
    def leaderboard(self, request, pk=None):
        """
        Get server-specific trader leaderboard.
        Member-only access.
        
        Returns top traders ranked by total verified payouts.
        Includes their stats, submission count, and best market.
        """
        server = self.get_object()
        
        # Get limit from query params (default 50, max 100)
        limit = min(int(request.query_params.get('limit', 50)), 100)
        
        # Get top traders
        top_traders = ServerMember.objects.filter(
            server=server,
            total_verified_payouts__gt=0
        ).select_related('user').order_by('-total_verified_payouts')[:limit]
        
        from utils.privacy import get_public_trader_view, mask_trader_stats
        
        leaderboard_data = []
        
        for rank, member in enumerate(top_traders, start=1):
            # Get member's submissions for this server
            submissions = PayoutSubmission.objects.filter(
                server=server,
                user=member.user,
                status='Approved'
            )
            
            # Get best market for this member
            best_market = submissions.values('market_category').annotate(
                volume=Sum('amount')
            ).order_by('-volume').first()
            
            # Get best instrument
            best_instrument = submissions.values('instrument').annotate(
                volume=Sum('amount')
            ).order_by('-volume').first()
            
            # Recent activity (last 30 days)
            thirty_days_ago = timezone.now().date() - timedelta(days=30)
            recent_submissions = submissions.filter(
                payout_date__gte=thirty_days_ago
            ).count()
            
            # Apply privacy masking
            trader_view = get_public_trader_view(member.user, requesting_user=request.user, has_valid_token=False)
            
            stats = {
                'total_volume': float(member.total_verified_payouts),
                'total_submissions': member.total_submissions,
                'best_market': best_market['market_category'] if best_market else None,
                'best_instrument': best_instrument['instrument'] if best_instrument else None,
                'recent_submissions_30d': recent_submissions,
                'joined_at': member.joined_at.isoformat(),
                'last_submission': member.last_submission_at.isoformat() if member.last_submission_at else None
            }
            
            # Determine if stats should be masked based on privacy and user access
            is_owner = request.user.is_authenticated and request.user.id == member.user.id
            should_mask = trader_view['is_private'] and not is_owner
            masked_stats = mask_trader_stats(stats, should_mask)
            
            trader_id = trader_view['id']
            leaderboard_data.append({
                'rank': rank,
                'username': trader_view['username'],
                'user_id': trader_view['id'],
                'profile_url': f'/trader/{trader_id}/public',
                'is_private': trader_view['is_private'],
                **masked_stats
            })
        
        return Response({
            'server': {
                'id': server.id,
                'name': server.name,
                'id': str(server.id)
            },
            'leaderboard': leaderboard_data,
            'total_traders': ServerMember.objects.filter(server=server).count()
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated ,IsEmailVerified ,IsServerMember])
    def heatmap(self, request, pk=None):
        """
        Get submission heatmap data.
        Member-only access.
        
        Returns submission activity by day of week and hour of day
        to visualize when traders are most active.
        """
        server = self.get_object()
        
        # Get submissions from last 90 days
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        submissions = PayoutSubmission.objects.filter(
            server=server,
            status='Approved',
            created_at__gte=ninety_days_ago
        ).values('created_at')
        
        # Initialize heatmap data structure
        # day_of_week (0=Monday, 6=Sunday) x hour (0-23)
        heatmap = [[0 for _ in range(24)] for _ in range(7)]
        
        for submission in submissions:
            day_of_week = submission['created_at'].weekday()
            hour = submission['created_at'].hour
            heatmap[day_of_week][hour] += 1
        
        # Format for frontend
        heatmap_data = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day_idx, day_name in enumerate(day_names):
            for hour in range(24):
                heatmap_data.append({
                    'day': day_name,
                    'hour': hour,
                    'count': heatmap[day_idx][hour]
                })
        
        return Response({
            'server': {
                'id': server.id,
                'name': server.name,
                'id': str(server.id)
            },
            'heatmap': heatmap_data
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsEmailVerified,IsServerMember])
    def gallery(self, request, pk=None):
        """
        Get screenshot gallery of recent approved submissions.
        Member-only access.
        
        Returns paginated list of submission screenshots with basic info.
        """
        server = self.get_object()
        
        # Get limit and offset from query params
        limit = min(int(request.query_params.get('limit', 20)), 50)
        offset = int(request.query_params.get('offset', 0))
        
        # Get approved submissions with screenshots
        submissions = PayoutSubmission.objects.filter(
            server=server,
            status='Approved'
        ).exclude(
            screenshot=''
        ).select_related('user').order_by('-created_at')[offset:offset+limit]
        
        gallery_items = []
        
        for submission in submissions:
            screenshot_url = submission.screenshot.url
            
            gallery_items.append({
                'id': submission.id,
                'screenshot': screenshot_url,
                'amount': float(submission.amount),
                'currency': submission.currency,
                'market': submission.market_category,
                'instrument': submission.instrument,
                'username': submission.user.username,
                'payout_date': submission.payout_date.isoformat(),
                'submitted_at': submission.created_at.isoformat()
            })
        
        # Get total count for pagination
        total_count = PayoutSubmission.objects.filter(
            server=server,
            status='Approved'
        ).exclude(
            screenshot=''
        ).count()
        
        return Response({
            'server': {
                'id': server.id,
                'name': server.name,
                'id': str(server.id)
            },
            'gallery': gallery_items,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total_count
            }
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsEmailVerified,IsServerMember])
    def moderation_stats(self, request, pk=None):
        """
        Get moderation transparency stats.
        Member-only access.
        
        Shows approval rates, rejection reasons, and review times
        to build trust with the community.
        """
        server = self.get_object()
        
        # Get all submissions
        all_submissions = PayoutSubmission.objects.filter(server=server)
        
        # Status breakdown
        status_counts = all_submissions.values('status').annotate(
            count=Count('id')
        )
        
        status_breakdown = {
            item['status']: item['count']
            for item in status_counts
        }
        
        total = all_submissions.count()
        approved = status_breakdown.get('Approved', 0)
        rejected = status_breakdown.get('Rejected', 0)
        pending = status_breakdown.get('Pending', 0)
        suspicious = status_breakdown.get('Suspicious', 0)
        
        # Approval rate
        approval_rate = (approved / (approved + rejected) * 100) if (approved + rejected) > 0 else 0
        
        # Average review time (for reviewed submissions)
        reviewed_submissions = all_submissions.filter(
            status__in=['Approved', 'Rejected', 'Suspicious'],
            reviewed_at__isnull=False
        )
        
        avg_review_time_seconds = 0
        if reviewed_submissions.exists():
            total_seconds = 0
            count = 0
            for submission in reviewed_submissions:
                if submission.reviewed_at and submission.created_at:
                    delta = submission.reviewed_at - submission.created_at
                    total_seconds += delta.total_seconds()
                    count += 1
            
            avg_review_time_seconds = total_seconds / count if count > 0 else 0
        
        # Convert to hours
        avg_review_time_hours = avg_review_time_seconds / 3600
        
        # Top rejection reasons (from review logs)
        from payouts.models import PayoutReviewLog
        
        rejection_logs = PayoutReviewLog.objects.filter(
            payout_submission__server=server,
            action='Rejected'
        ).values('reason').annotate(count=Count('id')).order_by('-count')[:5]
        
        top_rejection_reasons = [
            {
                'reason': log['reason'][:100],  # Truncate long reasons
                'count': log['count']
            }
            for log in rejection_logs
        ]
        
        # Recent activity (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_approved = all_submissions.filter(
            status='Approved',
            reviewed_at__gte=seven_days_ago
        ).count()
        
        recent_rejected = all_submissions.filter(
            status='Rejected',
            reviewed_at__gte=seven_days_ago
        ).count()
        
        return Response({
            'server': {
                'id': server.id,
                'name': server.name,
                'id': str(server.id)
            },
            'stats': {
                'total_submissions': total,
                'approved': approved,
                'rejected': rejected,
                'pending': pending,
                'suspicious': suspicious,
                'approval_rate': round(approval_rate, 2),
                'avg_review_time_hours': round(avg_review_time_hours, 2)
            },
            'breakdown': status_breakdown,
            'top_rejection_reasons': top_rejection_reasons,
            'recent_activity': {
                'approved_7d': recent_approved,
                'rejected_7d': recent_rejected
            }
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated,IsEmailVerified ,IsServerMember])
    def global_comparison(self, request, pk=None):
        """
        Compare this server vs global averages.
        Member-only access.
        
        Shows how this server ranks against all servers on the platform.
        """
        server = self.get_object()
        
        # Get this server's stats
        try:
            server_analytics = ServerAnalytics.objects.get(server=server)
            server_volume = server_analytics.total_volume
            server_payouts = server_analytics.total_payouts
            server_traders = server_analytics.unique_traders
        except ServerAnalytics.DoesNotExist:
            server_volume = Decimal('0')
            server_payouts = 0
            server_traders = 0
        
        # Get global stats
        # Count only active servers (not suspended or soft-deleted)
        total_servers = Server.objects.filter(suspended=False, is_deleted=False).count()
        
        # Get all server analytics for comparison
        all_server_analytics = ServerAnalytics.objects.all()
        
        global_total_volume = all_server_analytics.aggregate(
            total=Sum('total_volume')
        )['total'] or Decimal('0')
        
        global_total_payouts = all_server_analytics.aggregate(
            total=Sum('total_payouts')
        )['total'] or 0
        
        global_avg_volume = global_total_volume / total_servers if total_servers > 0 else Decimal('0')
        global_avg_payouts = global_total_payouts / total_servers if total_servers > 0 else 0
        
        # Calculate percentile rankings
        better_than_volume = all_server_analytics.filter(
            total_volume__lt=server_volume
        ).count()
        volume_percentile = (better_than_volume / total_servers * 100) if total_servers > 0 else 0
        
        better_than_payouts = all_server_analytics.filter(
            total_payouts__lt=server_payouts
        ).count()
        payouts_percentile = (better_than_payouts / total_servers * 100) if total_servers > 0 else 0
        
        # Get server ranking
        try:
            ranking = ServerRanking.objects.get(server=server)
            global_rank = ranking.global_rank
        except ServerRanking.DoesNotExist:
            global_rank = None
        
        # Get top 10 servers for reference
        top_servers = ServerAnalytics.objects.select_related('server').order_by('-total_volume')[:10]
        
        top_10_list = [
            {
                'rank': idx + 1,
                'name': analytics.server.name,
                'id': str(analytics.server.id),
                'volume': float(analytics.total_volume),
                'payouts': analytics.total_payouts
            }
            for idx, analytics in enumerate(top_servers)
        ]
        
        return Response({
            'server': {
                'id': server.id,
                'name': server.name,
                'id': str(server.id),
                'volume': float(server_volume),
                'payouts': server_payouts,
                'traders': server_traders,
                'global_rank': global_rank
            },
            'global': {
                'total_servers': total_servers,
                'total_volume': float(global_total_volume),
                'total_payouts': global_total_payouts,
                'avg_volume_per_server': float(global_avg_volume),
                'avg_payouts_per_server': round(global_avg_payouts, 2)
            },
            'comparison': {
                'volume_vs_avg': float(server_volume - global_avg_volume),
                'volume_percentile': round(volume_percentile, 2),
                'payouts_vs_avg': server_payouts - global_avg_payouts,
                'payouts_percentile': round(payouts_percentile, 2)
            },
            'top_10': top_10_list
        })
    
    @action(detail=True, methods=['get'])
    def check_membership(self, request, pk=None):
        """
        Check if current user is a member of this server.
        
        Returns membership status and submission eligibility.
        Public endpoint but returns different data based on authentication.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        server = self.get_object()
        
        if not request.user.is_authenticated:
            return Response({
                'is_member': False,
                'can_submit': False,
                'message': 'Login required to join and submit payouts'
            })
        
        is_member = ServerMember.objects.filter(
            server=server,
            user=request.user
        ).exists()
        
        logger.info(f"🔍 Membership check - Server: {server.name} (ID: {server.id}), User: {request.user.email} (ID: {request.user.id}), Is Member: {is_member}")
        
        # Check if submissions are allowed
        can_submit = is_member and not server.payout_submissions_paused and not server.suspended
        
        response_data = {
            'is_member': is_member,
            'can_submit': can_submit,
            'server': {
                'id': server.id,
                'name': server.name,
                'id': str(server.id),
                'submissions_paused': server.payout_submissions_paused,
                'suspended': server.suspended
            }
        }
        
        if not is_member:
            response_data['message'] = 'You must join this server to submit payouts'
        elif not can_submit:
            if server.payout_submissions_paused:
                response_data['message'] = 'Payout submissions are currently paused for this server'
            elif server.suspended:
                response_data['message'] = 'This server is suspended'
        else:
            response_data['message'] = 'You can submit payouts for this server'
        
        return Response(response_data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsEmailVerified])
    def join_server(self, request, pk=None):
        """
        Join this server to be able to submit payouts.
        
        Creates a ServerMember record for the authenticated user.
        """
        server = self.get_object()
        
        if server.suspended:
            return Response(
                {
                    'error': 'Cannot join a suspended server',
                    'reason': server.suspension_reason
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already a member
        member, created = ServerMember.objects.get_or_create(
            server=server,
            user=request.user,
            defaults={
                'joined_at': timezone.now()
            }
        )
        
        if not created:
            return Response(
                {
                    'message': 'You are already a member of this server',
                    'joined_at': member.joined_at.isoformat()
                },
                status=status.HTTP_200_OK
            )
        
        return Response(
            {
                'message': f'Successfully joined {server.name}!',
                'server': {
                    'id': server.id,
                    'name': server.name,
                    'id': str(server.id)
                },
                'joined_at': member.joined_at.isoformat()
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsEmailVerified])
    def my_stats(self, request, pk=None):
        """
        Get current user's stats for this server.
        
        Shows their submissions, rank, and performance.
        """
        server = self.get_object()
        
        try:
            member = ServerMember.objects.get(server=server, user=request.user)
        except ServerMember.DoesNotExist:
            return Response(
                {
                    'error': 'You are not a member of this server',
                    'action_required': 'Join this server first'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get user's submissions for this server
        submissions = PayoutSubmission.objects.filter(
            server=server,
            user=request.user
        )
        
        total = submissions.count()
        approved = submissions.filter(status='Approved').count()
        rejected = submissions.filter(status='Rejected').count()
        pending = submissions.filter(status='Pending').count()
        
        approval_rate = (approved / (approved + rejected) * 100) if (approved + rejected) > 0 else 0
        
        # Get user's rank in this server
        higher_ranked = ServerMember.objects.filter(
            server=server,
            total_verified_payouts__gt=member.total_verified_payouts
        ).count()
        rank = higher_ranked + 1
        
        # Recent submissions (last 5)
        recent = submissions.order_by('-created_at')[:5]
        recent_data = [
            {
                'id': sub.id,
                'amount': float(sub.amount),
                'market': sub.market_category,
                'instrument': sub.instrument,
                'status': sub.status,
                'created_at': sub.created_at.isoformat()
            }
            for sub in recent
        ]
        
        return Response({
            'member': {
                'joined_at': member.joined_at.isoformat(),
                'total_verified_payouts': float(member.total_verified_payouts),
                'rank': rank
            },
            'submissions': {
                'total': total,
                'approved': approved,
                'rejected': rejected,
                'pending': pending,
                'approval_rate': round(approval_rate, 2)
            },
            'recent_submissions': recent_data
        })
