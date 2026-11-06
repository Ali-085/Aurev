from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Max, Min, StdDev, Q, F
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from payouts.models import PayoutSubmission
from servers.models import ServerMember
import math


@api_view(['GET'])
def trader_profile_analytics(request):
    """
    Comprehensive analytics for logged-in trader.
    
    Returns:
    - Payout overview (total, monthly growth, averages, largest)
    - Consistency metrics (score, streaks, volatility, risk rating)
    - Market-specific stats for each market category
    - Rankings (server rank, global rank)
    - Badges earned
    """
    user = request.user
    
    # Check if user is a trader (has ServerMember records)
    is_trader = ServerMember.objects.filter(user=user).exists()
    if not is_trader:
        return Response(
            {"error": "Only traders can access analytics. Join a server as a trader to view your stats."},
            status=403
        )
    
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    
    # Get all user submissions (including rejected/suspicious for accurate metrics)
    all_submissions = PayoutSubmission.objects.filter(user=user)
    approved = all_submissions.filter(status='Approved')
    rejected = all_submissions.filter(status='Rejected')
    suspicious = all_submissions.filter(status='Suspicious')
    
    # TRADER METRICS: Include all submissions (approved + rejected + suspicious)
    # This penalizes traders for bad submissions in their approval rate
    total_attempts = all_submissions.count()
    total_approved = approved.count()
    total_rejected = rejected.count()
    total_suspicious = suspicious.count()
    
    # Calculate approval rate (% of submissions that get approved)
    approval_rate = (total_approved / total_attempts * 100) if total_attempts > 0 else 0
    
    # === PAYOUT OVERVIEW (Only approved payouts count toward volume) ===
    payout_stats = approved.aggregate(
        total_verified=Sum('amount'),
        avg_payout=Avg('amount'),
        largest_payout=Max('amount'),
        total_submissions=Count('id')
    )
    
    total_verified = float(payout_stats['total_verified'] or 0)
    avg_payout = float(payout_stats['avg_payout'] or 0)
    largest_payout = float(payout_stats['largest_payout'] or 0)
    approved_count = payout_stats['total_submissions']
    
    # Monthly growth (last 30 days vs previous 30 days)
    current_month = approved.filter(created_at__gte=thirty_days_ago).aggregate(total=Sum('amount'))['total'] or 0
    previous_month = approved.filter(
        created_at__gte=sixty_days_ago,
        created_at__lt=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_growth = float(((current_month - previous_month) / previous_month * 100) if previous_month > 0 else 0)
    
    # Submission frequency (based on ALL attempts, not just approved)
    if all_submissions.exists():
        first_submission = all_submissions.order_by('created_at').first().created_at
        days_active = (now - first_submission).days or 1
        daily_frequency = total_attempts / days_active
        weekly_frequency = daily_frequency * 7
    else:
        daily_frequency = 0
        weekly_frequency = 0
    
    # Time of day analysis (hour when most trades happen)
    hourly_distribution = approved.annotate(
        hour=TruncHour('created_at')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('-count')
    
    most_active_hour = None
    if hourly_distribution:
        most_active_hour = hourly_distribution[0]['hour'].hour
    
    # === CONSISTENCY METRICS ===
    
    # Calculate consistency score (0-100)
    # Based on: submission regularity, payout stability, growth trend
    consistency_score = calculate_consistency_score(approved, approved_count)
    
    # Submission streaks
    submission_streak = calculate_submission_streak(approved)
    longest_streak = submission_streak['longest']
    current_streak = submission_streak['current']
    
    # Volatility score (standard deviation / mean)
    std_dev = float(approved.aggregate(std=StdDev('amount'))['std'] or 0)
    volatility = (std_dev / avg_payout * 100) if avg_payout > 0 else 0
    
    # Risk rating based on volatility
    if volatility < 30:
        risk_rating = 'Stable'
    elif volatility < 60:
        risk_rating = 'Moderate'
    elif volatility < 100:
        risk_rating = 'Inconsistent'
    else:
        risk_rating = 'Aggressive'
    
    # Growth trendline (simplified linear regression)
    growth_trend = calculate_growth_trend(approved)
    
    # === MARKET-SPECIFIC STATS ===
    market_categories = ['Futures', 'Forex', 'Crypto', 'Options', 'Equities']
    market_stats = []
    
    for category in market_categories:
        market_submissions = approved.filter(market_category=category)
        
        if market_submissions.exists():
            stats = market_submissions.aggregate(
                total_payout=Sum('amount'),
                avg_payout=Avg('amount'),
                submission_count=Count('id')
            )
            
            # Most profitable instrument
            top_instrument = market_submissions.values('instrument').annotate(
                total=Sum('amount')
            ).order_by('-total').first()
            
            # Win-rate approximation (approved / total in this market)
            total_in_market = all_submissions.filter(market_category=category).count()
            win_rate = (stats['submission_count'] / total_in_market * 100) if total_in_market > 0 else 0
            
            market_stats.append({
                'category': category.lower(),
                'total_payout': float(stats['total_payout']),
                'avg_payout': float(stats['avg_payout']),
                'submission_count': stats['submission_count'],
                'win_rate': win_rate,
                'most_profitable_instrument': top_instrument['instrument'] if top_instrument else 'N/A',
                'most_profitable_amount': float(top_instrument['total']) if top_instrument else 0
            })
    
    # === RANKINGS ===
    
    # Global rank (by total verified payouts)
    users_above = PayoutSubmission.objects.filter(
        status='Approved'
    ).values('user').annotate(
        total=Sum('amount')
    ).filter(total__gt=total_verified).count()
    
    global_rank = users_above + 1
    
    # Server ranks (for each server user is a member of)
    memberships = ServerMember.objects.filter(user=user).select_related('server')
    server_ranks = []
    
    for membership in memberships:
        # Get all members of this server ranked by verified payouts
        members_above = ServerMember.objects.filter(
            server=membership.server,
            total_verified_payouts__gt=membership.total_verified_payouts
        ).count()
        
        server_ranks.append({
            'server_name': membership.server.name,
            'server_id': str(membership.server.id),
            'profile_url': f'/servers/{str(membership.server.id)}/public',
            'rank': members_above + 1,
            'total_members': ServerMember.objects.filter(server=membership.server).count()
        })
    
    # === BADGES ===
    badges = calculate_badges(
        consistency_score=consistency_score,
        total_verified=total_verified,
        current_streak=current_streak,
        risk_rating=risk_rating,
        market_stats=market_stats
    )
    
    return Response({
        'payout_overview': {
            'total_verified': total_verified,
            'monthly_growth': monthly_growth,
            'current_month_total': float(current_month),
            'previous_month_total': float(previous_month),
            'avg_payout': avg_payout,
            'largest_payout': largest_payout,
            'total_submissions': approved_count,
            'daily_frequency': daily_frequency,
            'weekly_frequency': weekly_frequency,
            'most_active_hour': most_active_hour
        },
        'submission_metrics': {
            'total_attempts': total_attempts,
            'total_approved': total_approved,
            'total_rejected': total_rejected,
            'total_suspicious': total_suspicious,
            'approval_rate': round(approval_rate, 2)
        },
        'consistency_metrics': {
            'consistency_score': consistency_score,
            'longest_streak': longest_streak,
            'current_streak': current_streak,
            'volatility_score': volatility,
            'growth_trend': growth_trend,
            'risk_rating': risk_rating
        },
        'market_stats': market_stats,
        'rankings': {
            'global_rank': global_rank,
            'server_ranks': server_ranks
        },
        'badges': badges
    })


def calculate_consistency_score(approved_submissions, total_count):
    """
    Aurevia proprietary consistency score (0-100).
    
    Factors:
    - Submission regularity (40 points)
    - Payout stability (30 points)
    - Growth trend (30 points)
    """
    if total_count == 0:
        return 0
    
    score = 0
    now = timezone.now()
    
    # 1. Submission regularity (40 points)
    # Check submissions over last 30 days
    last_30_days = approved_submissions.filter(
        created_at__gte=now - timedelta(days=30)
    ).annotate(date=TruncDate('created_at')).values('date').distinct().count()
    
    regularity_score = min((last_30_days / 20) * 40, 40)  # Max 40 points if 20+ unique days
    score += regularity_score
    
    # 2. Payout stability (30 points)
    # Lower standard deviation relative to mean = more stable
    stats = approved_submissions.aggregate(
        avg=Avg('amount'),
        std=StdDev('amount')
    )
    
    if stats['avg'] and stats['std']:
        coefficient_of_variation = float(stats['std']) / float(stats['avg'])
        # Lower CV = higher score (inverse relationship)
        stability_score = max(30 - (coefficient_of_variation * 30), 0)
        score += stability_score
    else:
        score += 15  # Neutral score if insufficient data
    
    # 3. Growth trend (30 points)
    # Positive growth = higher score
    recent_avg = approved_submissions.filter(
        created_at__gte=now - timedelta(days=30)
    ).aggregate(avg=Avg('amount'))['avg'] or 0
    
    older_avg = approved_submissions.filter(
        created_at__gte=now - timedelta(days=60),
        created_at__lt=now - timedelta(days=30)
    ).aggregate(avg=Avg('amount'))['avg'] or 0
    
    if older_avg > 0:
        growth_rate = (float(recent_avg) - float(older_avg)) / float(older_avg)
        # Positive growth up to 50% = full 30 points
        growth_score = min(max((growth_rate / 0.5) * 30, 0), 30)
        score += growth_score
    else:
        score += 15  # Neutral for new traders
    
    return round(score, 1)


def calculate_submission_streak(approved_submissions):
    """Calculate current and longest submission streaks."""
    if not approved_submissions.exists():
        return {'current': 0, 'longest': 0}
    
    # Get all submission dates
    dates = list(approved_submissions.annotate(
        date=TruncDate('created_at')
    ).values_list('date', flat=True).distinct().order_by('date'))
    
    if not dates:
        return {'current': 0, 'longest': 0}
    
    current_streak = 0
    longest_streak = 0
    temp_streak = 1
    
    now = timezone.now().date()
    
    # Check if most recent date is today or yesterday for current streak
    if dates[-1] >= now - timedelta(days=1):
        current_streak = 1
        for i in range(len(dates) - 2, -1, -1):
            if (dates[i + 1] - dates[i]).days <= 1:
                current_streak += 1
            else:
                break
    
    # Calculate longest streak
    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days <= 1:
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 1
    
    longest_streak = max(longest_streak, temp_streak, current_streak)
    
    return {'current': current_streak, 'longest': longest_streak}


def calculate_growth_trend(approved_submissions):
    """
    Calculate growth trend (simplified linear regression slope).
    Returns: 'Increasing', 'Stable', or 'Decreasing'
    """
    submissions = list(approved_submissions.order_by('created_at').values('created_at', 'amount'))
    
    if len(submissions) < 5:
        return 'Insufficient Data'
    
    # Simple linear regression
    n = len(submissions)
    x_values = list(range(n))
    y_values = [float(s['amount']) for s in submissions]
    
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n
    
    numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
    denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        return 'Stable'
    
    slope = numerator / denominator
    
    # Classify based on slope
    if slope > y_mean * 0.01:  # Slope > 1% of mean
        return 'Increasing'
    elif slope < -y_mean * 0.01:
        return 'Decreasing'
    else:
        return 'Stable'


def calculate_badges(consistency_score, total_verified, current_streak, risk_rating, market_stats):
    """
    Calculate earned badges based on trader performance.
    
    Badge types:
    - Consistency Badge: Score > 75
    - High Performer: Total > $10k
    - Top Market Specialist: Dominant in one market (>60% of earnings)
    - Verified Trader: At least 10 approved submissions
    - Monthly Champion: Current streak > 20 days
    - Stable Trader: Risk rating = Stable
    """
    badges = []
    
    # Consistency Badge
    if consistency_score >= 75:
        badges.append({
            'name': 'Consistency Master',
            'icon': '',
            'description': 'Maintains excellent trading consistency',
            'color': '#28a745'
        })
    elif consistency_score >= 60:
        badges.append({
            'name': 'Consistent Trader',
            'icon': '',
            'description': 'Shows consistent trading patterns',
            'color': '#17a2b8'
        })
    
    # High Performer
    if total_verified >= 50000:
        badges.append({
            'name': 'Elite Performer',
            'icon': '',
            'description': 'Over $50k in verified payouts',
            'color': '#6f42c1'
        })
    elif total_verified >= 10000:
        badges.append({
            'name': 'High Performer',
            'icon': '',
            'description': 'Over $10k in verified payouts',
            'color': '#007bff'
        })
    
    # Top Market Specialist
    if market_stats:
        total_all_markets = sum(m['total_payout'] for m in market_stats)
        for market in market_stats:
            if total_all_markets > 0:
                market_percentage = (market['total_payout'] / total_all_markets) * 100
                if market_percentage > 60 and market['submission_count'] >= 10:
                    badges.append({
                        'name': f'{market["category"].title()} Specialist',
                        'icon': '🎓',
                        'description': f'Specializes in {market["category"]} trading',
                        'color': '#ffc107'
                    })
                    break
    
    # Streak badges
    if current_streak >= 30:
        badges.append({
            'name': 'Monthly Champion',
            'icon': '',
            'description': '30+ day submission streak',
            'color': '#dc3545'
        })
    elif current_streak >= 7:
        badges.append({
            'name': 'Weekly Warrior',
            'icon': '',
            'description': '7+ day submission streak',
            'color': '#fd7e14'
        })
    
    # Risk rating badge
    if risk_rating == 'Stable':
        badges.append({
            'name': 'Stable Trader',
            'icon': '',
            'description': 'Maintains stable payout patterns',
            'color': '#20c997'
        })
    
    return badges
