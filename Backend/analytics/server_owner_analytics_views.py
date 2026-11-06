from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Max, Min, StdDev, Q, F
from django.db.models.functions import TruncDate, TruncHour, ExtractHour
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from payouts.models import PayoutSubmission
from servers.models import Server, ServerMember
from users.models import UserRole
from subscriptions.tier_utils import get_user_tier, filter_analytics_by_tier, has_tier_access
import math
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
def server_owner_dashboard(request, server_id):
    """
    Comprehensive analytics for server owners.
    Data returned is filtered based on user's subscription tier.
    
    Standard tier: Basic metrics (7-day, 30-day, health score)
    Premium tier: Advanced analytics (trader categorization, trends, predictions)
    Elite tier: Full data access (all analytics, fraud detection, API)
    
    Returns detailed metrics about:
    - Total payout insights
    - Server activity metrics
    - Trader performance breakdown
    - Market category analytics
    - Submission quality metrics
    """
    try:
        user = request.user
        
        # Check if user owns this server
        try:
            server = Server.objects.get(id=server_id)
        except Server.DoesNotExist:
            return Response({"error": "Server not found"}, status=404)
        
        if server.owner_user != user:
            return Response({"error": "You do not own this server"}, status=403)
        
        # Get user's subscription tier (optional - defaults to basic access if no subscription)
        user_tier = get_user_tier(user)
        # Allow access even without subscription (will show basic metrics)
        if not user_tier:
            user_tier = 'Free'  # Default to Free tier
        
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        
        # Get all submissions for this server
        all_submissions = PayoutSubmission.objects.filter(server=server)
        approved = all_submissions.filter(status='Approved')
        rejected = all_submissions.filter(status='Rejected')
        pending = all_submissions.filter(status='Pending')
    
        # === TOTAL PAYOUT INSIGHTS ===
        payout_stats = approved.aggregate(
            total_verified=Sum('amount'),
            avg_payout=Avg('amount'),
            largest_payout=Max('amount'),
            total_submissions=Count('id')
        )
    
        total_verified = float(payout_stats['total_verified'] or 0)
        avg_payout = float(payout_stats['avg_payout'] or 0)
        largest_payout = float(payout_stats['largest_payout'] or 0)
        total_submissions = payout_stats['total_submissions']
    
        # Monthly growth (last 30 days vs previous 30 days)
        current_month = approved.filter(created_at__gte=thirty_days_ago).aggregate(total=Sum('amount'))['total'] or 0
        previous_month = approved.filter(
            created_at__gte=sixty_days_ago,
            created_at__lt=thirty_days_ago
        ).aggregate(total=Sum('amount'))['total'] or 0
    
        monthly_growth = 0
        if previous_month > 0:
            monthly_growth = ((float(current_month) - float(previous_month)) / float(previous_month)) * 100
    
        # Weekly trend (last 7 days)
        weekly_payouts = approved.filter(created_at__gte=seven_days_ago).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('date')
    
        weekly_trend = [
            {
                'date': entry['date'].strftime('%Y-%m-%d'),
                'total': float(entry['total']),
                'count': entry['count']
            }
            for entry in weekly_payouts
        ]
    
        # Daily trend (last 30 days)
        daily_payouts = approved.filter(created_at__gte=thirty_days_ago).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('date')
    
        daily_trend = [
            {
                'date': entry['date'].strftime('%Y-%m-%d'),
                'total': float(entry['total']),
                'count': entry['count']
            }
            for entry in daily_payouts
        ]
    
        # Most consistent traders (based on submission frequency and amount stability)
        members = ServerMember.objects.filter(server=server, total_submissions__gt=0)
        consistent_traders = []
    
        for member in members:
            member_submissions = approved.filter(user=member.user)
            if member_submissions.count() < 3:
                continue
        
            amounts = [float(x) for x in member_submissions.values_list('amount', flat=True)]
            avg_amount = sum(amounts) / len(amounts)
            variance = sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)
            std_dev = math.sqrt(variance) if variance > 0 else 0
        
            # Coefficient of variation (lower is more consistent)
            cv = (std_dev / avg_amount * 100) if avg_amount > 0 else 0
        
            consistent_traders.append({
                'username': member.user.username,
                'user_id': member.user.id,
                'total_payouts': float(member.total_verified_payouts),
                'submission_count': member.total_submissions,
                'consistency_score': max(0, 100 - cv)  # Higher is more consistent
            })
    
        consistent_traders.sort(key=lambda x: x['consistency_score'], reverse=True)
        most_consistent = consistent_traders[:5]
    
        # === SERVER ACTIVITY METRICS ===
        active_7_days = ServerMember.objects.filter(
            server=server,
            last_submission_at__gte=seven_days_ago
        ).count()
    
        active_30_days = ServerMember.objects.filter(
            server=server,
            last_submission_at__gte=thirty_days_ago
        ).count()
    
        # Submission volume per day (last 30 days)
        submissions_per_day = all_submissions.filter(
            created_at__gte=thirty_days_ago
        ).count() / 30.0
    
        # Time of day analysis
        hourly_distribution = all_submissions.filter(
            created_at__gte=thirty_days_ago
        ).annotate(
            hour=ExtractHour('created_at')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')
    
        peak_hours = [
            {'hour': entry['hour'], 'count': entry['count']}
            for entry in hourly_distribution[:5]
        ]
    
        # Approval rate
        total_reviewed = approved.count() + rejected.count()
        approval_rate = (approved.count() / total_reviewed * 100) if total_reviewed > 0 else 0
    
        # Suspicious submission rate (marked as suspicious status)
        suspicious_count = all_submissions.filter(status='Suspicious').count()
    
        suspicious_rate = (suspicious_count / all_submissions.count() * 100) if all_submissions.count() > 0 else 0
    
        # === TRADER PERFORMANCE BREAKDOWN ===
        # Top 5 traders (all time)
        top_traders_alltime = ServerMember.objects.filter(
            server=server
        ).order_by('-total_verified_payouts')[:5].values(
            'user__username', 'user__id', 'total_verified_payouts', 'total_submissions'
        )
    
        top_traders_alltime_list = [
            {
                'username': t['user__username'],
                'user_id': str(t['user__id']),
                'profile_url': f'/trader/{str(t["user__id"])}/public',
                'total': float(t['total_verified_payouts']),
                'submissions': t['total_submissions']
            }
            for t in top_traders_alltime
        ]
    
        # Top 5 traders (last 30 days)
        monthly_top = approved.filter(
            created_at__gte=thirty_days_ago
        ).values('user__username', 'user__id').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:5]
    
        top_traders_monthly = [
            {
                'username': t['user__username'],
                'user_id': str(t['user__id']),
                'profile_url': f'/trader/{str(t["user__id"])}/public',
                'total': float(t['total']),
                'submissions': t['count']
            }
            for t in monthly_top
        ]
    
        # Most improved trader (based on 30-day vs previous 30-day growth)
        improved_traders = []
        for member in members:
            recent = approved.filter(
                user=member.user,
                created_at__gte=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
        
            previous = approved.filter(
                user=member.user,
                created_at__gte=sixty_days_ago,
                created_at__lt=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
        
            if previous > 0 and recent > 0:
                growth = ((float(recent) - float(previous)) / float(previous)) * 100
                improved_traders.append({
                    'username': member.user.username,
                    'user_id': str(member.user.id),
                    'profile_url': f'/trader/{str(member.user.id)}/public',
                    'growth_percentage': growth,
                    'recent_total': float(recent),
                    'previous_total': float(previous)
                })
    
        improved_traders.sort(key=lambda x: x['growth_percentage'], reverse=True)
        most_improved = improved_traders[0] if improved_traders else None
    
        # Highest single payout
        highest_payout = approved.order_by('-amount').first()
        highest_payout_data = None
        if highest_payout:
            highest_payout_data = {
                'username': highest_payout.user.username,
                'user_id': str(highest_payout.user.id),
                'profile_url': f'/trader/{str(highest_payout.user.id)}/public',
                'amount': float(highest_payout.amount),
                'instrument': highest_payout.instrument,
                'market_category': highest_payout.market_category,
                'date': highest_payout.created_at.strftime('%Y-%m-%d')
            }
    
        # Trader categorization (scalper, swing, long-term)
        trader_categories = []
        for member in members:
            member_approved = approved.filter(user=member.user)
            if member_approved.count() < 3:
                continue
        
            avg_amount = member_approved.aggregate(avg=Avg('amount'))['avg']
            submission_count = member_approved.count()
        
            # Infer trading style based on frequency and amount
            days_active = (now - member.joined_at).days
            submissions_per_day = submission_count / days_active if days_active > 0 else 0
        
            if submissions_per_day > 0.5 and avg_amount < 500:
                category = 'Scalper'
            elif submissions_per_day > 0.1 and avg_amount < 2000:
                category = 'Day Trader'
            elif avg_amount >= 2000:
                category = 'Swing/Position'
            else:
                category = 'Long-term'
        
            trader_categories.append({
                'username': member.user.username,
                'user_id': str(member.user.id),
                'profile_url': f'/trader/{str(member.user.id)}/public',
                'category': category,
                'avg_payout': float(avg_amount or 0),
                'frequency': round(submissions_per_day, 2)
            })
    
        # === MARKET CATEGORY ANALYTICS ===
        market_breakdown = approved.values('market_category').annotate(
            total=Sum('amount'),
            avg=Avg('amount'),
            count=Count('id')
        ).order_by('-total')
    
        market_stats = []
        for market in market_breakdown:
            if not market['market_category']:
                continue
        
            # Get instrument breakdown for this market
            instruments = approved.filter(
                market_category=market['market_category']
            ).values('instrument').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('-total')[:5]
        
            instrument_list = [
                {
                    'name': inst['instrument'],
                    'total': float(inst['total']),
                    'count': inst['count']
                }
                for inst in instruments
            ]
        
            # Calculate percentage share
            percentage_share = (float(market['total']) / total_verified * 100) if total_verified > 0 else 0
        
            # Growth trend (last 30 days vs previous)
            recent_market = approved.filter(
                market_category=market['market_category'],
                created_at__gte=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
        
            previous_market = approved.filter(
                market_category=market['market_category'],
                created_at__gte=sixty_days_ago,
                created_at__lt=thirty_days_ago
            ).aggregate(total=Sum('amount'))['total'] or 0
        
            trend = 'stable'
            if previous_market > 0:
                growth = ((float(recent_market) - float(previous_market)) / float(previous_market)) * 100
                if growth > 10:
                    trend = 'growing'
                elif growth < -10:
                    trend = 'declining'
        
            market_stats.append({
                'category': market['market_category'],
                'total': float(market['total']),
                'average': float(market['avg']),
                'submissions': market['count'],
                'percentage_share': round(percentage_share, 2),
                'trend': trend,
                'top_instruments': instrument_list
            })
    
        # === SUBMISSION QUALITY METRICS ===
        # Approval time average
        from payouts.models import PayoutReviewLog
        
        approved_with_time = approved.filter(reviewed_at__isnull=False)
        if approved_with_time.exists():
            approval_times = []
            for sub in approved_with_time:
                time_diff = (sub.reviewed_at - sub.created_at).total_seconds() / 3600  # hours
                approval_times.append(time_diff)
            avg_approval_time = sum(approval_times) / len(approval_times)
        else:
            avg_approval_time = 0
        
        # Rejection reasons breakdown from review logs
        rejection_logs = PayoutReviewLog.objects.filter(
            payout_submission__server=server,
            action='Rejected'
        ).values('reason').annotate(
            count=Count('id')
        ).order_by('-count')
        
        rejection_breakdown = [
            {
                'reason': r['reason'] or 'No reason provided',
                'count': r['count']
            }
            for r in rejection_logs
        ]
        
        # Most common mistakes (top rejection reasons)
        common_mistakes = rejection_breakdown[:5]
        
        # === COMPILE FULL RESPONSE ===
        full_data = {
            'server': {
                'id': server.id,
                'name': server.name,
                'total_members': members.count()
            },
            'payout_insights': {
                'total_verified': total_verified,
                'monthly_growth': round(monthly_growth, 2),
                'weekly_trend': weekly_trend,
                'daily_trend': daily_trend,
                'average_payout': avg_payout,
                'largest_payout': largest_payout,
                'total_submissions': total_submissions,
                'most_consistent_traders': most_consistent
            },
            'activity_metrics': {
                'active_traders_7d': active_7_days,
                'active_traders_30d': active_30_days,
                'submissions_per_day': round(submissions_per_day, 2),
                'peak_submission_hours': peak_hours,
                'approval_rate': round(approval_rate, 2),
                'suspicious_rate': round(suspicious_rate, 2),
                'pending_submissions': pending.count()
            },
            'trader_performance': {
                'top_traders_alltime': top_traders_alltime_list,
                'top_traders_monthly': top_traders_monthly,
                'most_improved': most_improved,
                'highest_single_payout': highest_payout_data,
                'trader_categories': trader_categories
            },
            'market_analytics': market_stats,
            'quality_metrics': {
                'avg_approval_time_hours': round(avg_approval_time, 2),
                'rejection_reasons': rejection_breakdown,
                'common_mistakes': common_mistakes,
                'total_pending': pending.count(),
                'total_rejected': rejected.count()
            }
        }
        
        # Filter data based on subscription tier
        filtered_data = filter_analytics_by_tier(full_data, user_tier)
        
        # Add tier information to response
        filtered_data['subscription'] = {
            'tier': user_tier,
            'tier_display': user_tier.title(),
            'message': get_tier_message(user_tier)
        }
        
        return Response(filtered_data)
    except Exception as e:
        logger.exception(f"Error generating server analytics for user {request.user.email}")
        return Response({
            "error": "Failed to load analytics. Please try again or contact support."
        }, status=500)


def get_tier_message(tier):
    """Get informational message about current tier."""
    if tier == 'standard':
        return "Standard tier: Essential analytics with 7-day and 30-day insights"
    elif tier == 'premium':
        return "Premium tier: Deeper engagement data, momentum intelligence, and advanced health scoring"
    elif tier == 'elite':
        return "Elite tier: Private benchmark analytics, full historical data, and forecast projections"
    return ""


@api_view(['GET'])
def user_owned_servers(request):
    """
    Get list of servers owned by the authenticated user.
    """
    user = request.user
    servers = Server.objects.filter(owner_user=user).values('id', 'name', 'created_at')
    
    # Get user's subscription tier
    user_tier = get_user_tier(user)
    
    return Response({
        'servers': list(servers),
        'subscription_tier': user_tier
    })
