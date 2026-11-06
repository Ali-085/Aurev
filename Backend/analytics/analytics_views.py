from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status as http_status
from django.db.models import Sum, Count, Avg, Q, F, Max, Case, When, FloatField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from django.utils import timezone
from datetime import timedelta, datetime
from payouts.models import PayoutSubmission
from servers.models import Server
from users.models import User
from django.shortcuts import get_object_or_404
import pytz

@api_view(['GET'])
@permission_classes([AllowAny])
def global_overview(request):
    """
    Global platform analytics overview - SECTION 1: Global Performance Metrics.
    
    Returns headline stats that establish scale and legitimacy:
    - Total Verified Payouts (count)
    - Total Payout Volume ($)
    - Active Servers (servers with at least 1 verified payout in last 30d)
    - Active Submissions Today (live ecosystem activity)
    - Aurevia System Uptime (institutional credibility)
    - Market comparison heatmap (all 5 markets)
    - Platform-wide submission insights
    - Daily/monthly trends
    - Approval/rejection statistics
    """
    
    # Time ranges
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_ago = now - timedelta(days=30)
    last_month_start = (now - timedelta(days=60)).replace(day=1)
    last_month_end = (now - timedelta(days=30)).replace(day=1)
    
    # All submissions
    all_submissions = PayoutSubmission.objects.all()
    approved = all_submissions.filter(status='Approved')
    
    # ===== SECTION 1: GLOBAL PERFORMANCE METRICS (TOP HEADER) =====
    # These are the "headline stats" that instantly establish scale and legitimacy
    
    # 1. Total Verified Payouts (count of all approved payouts)
    total_verified_payouts = approved.count()
    
    # 2. Total Payout Volume ($) - all-time processed volume
    total_payout_volume = approved.aggregate(total=Sum('amount'))['total'] or 0
    
    # 3. Active Servers (servers with at least 1 verified payout in last 30 days)
    active_servers_count = approved.filter(
        created_at__gte=month_ago
    ).values('server_id').distinct().count()
    
    # 4. Active Submissions Today (live ecosystem activity)
    active_submissions_today = all_submissions.filter(created_at__gte=today_start).count()
    
    # 5. Aurevia System Uptime (institutional credibility)
    # This should be pulled from your monitoring system (e.g., UptimeRobot, Datadog)
    # For now, we'll use a placeholder that you can replace with actual monitoring data
    system_uptime = 99.99  # Replace with actual uptime from monitoring service
    
    # Additional metrics for context
    total_submissions = all_submissions.count()
    daily_volume = approved.filter(created_at__gte=today_start).aggregate(total=Sum('amount'))['total'] or 0
    daily_submissions = all_submissions.filter(created_at__gte=today_start).count()
    
    # Status breakdown
    status_counts = all_submissions.values('status').annotate(count=Count('id'))
    status_dict = {s['status']: s['count'] for s in status_counts}
    
    approved_count = status_dict.get('Approved', 0)
    pending_count = status_dict.get('Pending', 0)
    rejected_count = status_dict.get('Rejected', 0)
    suspicious_count = status_dict.get('Suspicious', 0)
    
    # Rates
    total = total_submissions or 1
    approval_rate = (approved_count / total) * 100
    pending_rate = (pending_count / total) * 100
    rejection_rate = (rejected_count / total) * 100
    suspicious_rate = (suspicious_count / total) * 100
    
    # Market comparison (last 30 days vs previous 30 days)
    market_categories = ['Futures', 'Forex', 'Crypto', 'Options', 'Equities']
    market_comparison = []
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    
    for category in market_categories:
        current_period = approved.filter(
            market_category=category,
            created_at__gte=thirty_days_ago
        ).aggregate(
            volume=Sum('amount'),
            submissions=Count('id')
        )
        
        previous_period = approved.filter(
            market_category=category,
            created_at__gte=sixty_days_ago,
            created_at__lt=thirty_days_ago
        ).aggregate(volume=Sum('amount'))
        
        current_vol = float(current_period['volume'] or 0)
        prev_vol = float(previous_period['volume'] or 0)
        growth = ((current_vol - prev_vol) / prev_vol * 100) if prev_vol > 0 else 0
        
        market_comparison.append({
            'category': category.lower(),
            'volume': current_vol,
            'submissions': current_period['submissions'] or 0,
            'growth': growth
        })
    
    # Daily trends (last 30 days)
    daily_trends = approved.filter(
        created_at__gte=month_ago
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        value=Sum('amount')
    ).order_by('date')
    
    daily_trends_data = [{
        'date': trend['date'].strftime('%m/%d'),
        'value': float(trend['value'])
    } for trend in daily_trends]
    
    # Payout Scatter Data with filtering support
    # Shows individual payout distribution without exposing user/server identities
    # Supports: scatter_period (7d, 30d, 90d, 180d, 365d, all) and scatter_granularity (day, week, month, year)
    
    scatter_period = request.GET.get('scatter_period', '90d').strip().lower()
    scatter_granularity = request.GET.get('scatter_granularity', 'day').strip().lower()
    
    # Sanitize and validate scatter_period
    scatter_period = ''.join(c for c in scatter_period if c.isalnum())
    valid_periods = {'7d': 7, '30d': 30, '90d': 90, '180d': 180, '365d': 365, 'all': 3650}
    days_back = valid_periods.get(scatter_period, 90)
    
    # Sanitize and validate scatter_granularity
    scatter_granularity = ''.join(c for c in scatter_granularity if c.isalpha())
    valid_granularities = ['day', 'week', 'month', 'year']
    if scatter_granularity not in valid_granularities:
        scatter_granularity = 'day'
    
    scatter_start_date = now - timedelta(days=days_back)
    payout_scatter_query = approved.filter(created_at__gte=scatter_start_date)
    
    # Apply granularity aggregation
    if scatter_granularity == 'day':
        scatter_data = payout_scatter_query.values('payout_date', 'amount').order_by('payout_date')
        scatter_points = [{
            'date': payout['payout_date'].strftime('%Y-%m-%d'),
            'amount': float(payout['amount'])
        } for payout in list(scatter_data)[:1000]]  # Limit to 1000 points
    elif scatter_granularity == 'week':
        scatter_data = payout_scatter_query.annotate(
            week=TruncWeek('created_at')
        ).values('week', 'amount').order_by('week')
        scatter_points = [{
            'date': payout['week'].strftime('%Y-%m-%d'),
            'amount': float(payout['amount'])
        } for payout in list(scatter_data)[:1000]]
    elif scatter_granularity == 'month':
        scatter_data = payout_scatter_query.annotate(
            month=TruncMonth('created_at')
        ).values('month', 'amount').order_by('month')
        scatter_points = [{
            'date': payout['month'].strftime('%Y-%m-%d'),
            'amount': float(payout['amount'])
        } for payout in list(scatter_data)[:1000]]
    else:  # year
        scatter_data = payout_scatter_query.annotate(
            year=TruncYear('created_at')
        ).values('year', 'amount').order_by('year')
        scatter_points = [{
            'date': payout['year'].strftime('%Y-%m-%d'),
            'amount': float(payout['amount'])
        } for payout in list(scatter_data)[:1000]]
    
    # ===== SECTION 2: GLOBAL ECOSYSTEM TRENDS (GRAPHS + CHARTS) =====
    # Shows how fast Aurevia is growing without exposing private data
    
    # 1. Monthly Verified Payout Volume (Line Chart) - Last 12 months
    from django.db.models.functions import TruncMonth
    twelve_months_ago = now - timedelta(days=365)
    
    monthly_volume_trends = approved.filter(
        created_at__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        volume=Sum('amount')
    ).order_by('month')
    
    monthly_volume_data = [{
        'month': trend['month'].strftime('%b %Y'),
        'volume': float(trend['volume'] or 0)
    } for trend in monthly_volume_trends]
    
    # 2. Monthly Verified Payout Count (Bar Chart) - Last 12 months
    monthly_count_trends = approved.filter(
        created_at__gte=twelve_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    monthly_count_data = [{
        'month': trend['month'].strftime('%b %Y'),
        'count': trend['count']
    } for trend in monthly_count_trends]
    
    # 3. Category Breakdown (Pie/Donut Chart) - All time
    category_breakdown = approved.values('market_category').annotate(
        volume=Sum('amount'),
        count=Count('id')
    ).order_by('-volume')
    
    category_breakdown_data = [{
        'category': cat['market_category'],
        'volume': float(cat['volume'] or 0),
        'count': cat['count'],
        'percentage': (float(cat['volume'] or 0) / float(total_payout_volume) * 100) if total_payout_volume > 0 else 0
    } for cat in category_breakdown]
    
    # 4. Ecosystem Growth Curve (Combined Line Chart)
    # Combines cumulative payouts count + cumulative volume over time
    # Supports weekly, monthly, and yearly aggregation based on 'period' query param
    
    # Get period from query params (default to 'month')
    period = request.GET.get('period', 'month').lower()
    
    # Determine truncation function and date format based on period
    if period == 'week':
        trunc_func = TruncWeek
        date_format = '%b %d, %Y'  # e.g., "Jan 15, 2024"
        period_label = 'week'
    elif period == 'year':
        trunc_func = TruncYear
        date_format = '%Y'  # e.g., "2024"
        period_label = 'year'
    else:  # default to month
        trunc_func = TruncMonth
        date_format = '%b %Y'  # e.g., "Jan 2024"
        period_label = 'month'
    
    # Aggregate by selected period
    growth_data = approved.annotate(
        period=trunc_func('created_at')
    ).values('period').annotate(
        volume=Sum('amount'),
        count=Count('id')
    ).order_by('period')
    
    # Calculate cumulative values and combined metric
    cumulative_volume = 0
    cumulative_count = 0
    ecosystem_growth_data = []
    
    for trend in growth_data:
        cumulative_volume += float(trend['volume'] or 0)
        cumulative_count += trend['count']
        
        # Combined metric: count + (volume / 1000) to balance scale
        # This puts both metrics on similar magnitude for visualization
        combined_metric = cumulative_count + (cumulative_volume / 1000)
        
        ecosystem_growth_data.append({
            period_label: trend['period'].strftime(date_format),
            'cumulative_volume': round(cumulative_volume, 2),
            'cumulative_count': cumulative_count,
            'combined': round(combined_metric, 2)  # Single combined data point
        })
    
    # ========================================
    # SECTION 3: Global Highlights & Records
    # ========================================
    # Twitter-worthy stats that build hype and tell the Aurevia story
    
    # 1. Largest Payout This Month (amount only - no user/server exposure)
    today = timezone.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    largest_payout_this_month = approved.filter(
        created_at__gte=month_start
    ).aggregate(Max('amount'))['amount__max']
    
    # 2. Fastest Growing Server This Month (server name only)
    # Calculate growth by comparing this month's payouts to last month's
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    # This month's payout counts per server
    this_month_counts = approved.filter(
        created_at__gte=month_start
    ).values('server__name').annotate(
        count=Count('id')
    )
    
    # Last month's payout counts per server
    last_month_counts = approved.filter(
        created_at__gte=last_month_start,
        created_at__lt=month_start
    ).values('server__name').annotate(
        count=Count('id')
    )
    
    # Build lookup dict for last month
    last_month_lookup = {item['server__name']: item['count'] for item in last_month_counts}
    
    # Calculate growth rates
    fastest_growing = None
    max_growth = 0
    for server_data in this_month_counts:
        server_name = server_data['server__name']
        this_count = server_data['count']
        last_count = last_month_lookup.get(server_name, 0)
        
        # Calculate absolute growth (new payouts this month)
        growth = this_count - last_count
        if growth > max_growth:
            max_growth = growth
            fastest_growing = server_name
    
    # 3. Milestone Indicator
    # Check if we've crossed major milestones
    milestone_message = None
    milestones = [
        (50000000, "$50,000,000 in total verified payouts"),
        (25000000, "$25,000,000 in total verified payouts"),
        (10000000, "$10,000,000 in total verified payouts"),
        (5000000, "$5,000,000 in total verified payouts"),
        (1000000, "$1,000,000 in total verified payouts"),
    ]
    
    for threshold, message in milestones:
        if total_payout_volume >= threshold:
            milestone_message = f"Aurevia has surpassed {message}"
            break
    
    # 4. 7-Day Trend Summary
    seven_days_ago = today - timedelta(days=7)
    fourteen_days_ago = today - timedelta(days=14)
    
    # This week's stats (last 7 days)
    this_week_stats = approved.filter(created_at__gte=seven_days_ago).aggregate(
        payouts=Count('id'),
        volume=Sum('amount')
    )
    this_week_payouts = this_week_stats['payouts'] or 0
    this_week_volume = float(this_week_stats['volume'] or 0)
    
    # Last week's stats (7-14 days ago)
    last_week_stats = approved.filter(
        created_at__gte=fourteen_days_ago,
        created_at__lt=seven_days_ago
    ).aggregate(
        payouts=Count('id'),
        volume=Sum('amount')
    )
    last_week_payouts = last_week_stats['payouts'] or 0
    last_week_volume = float(last_week_stats['volume'] or 0)
    
    # Calculate % change
    payouts_change = ((this_week_payouts - last_week_payouts) / last_week_payouts * 100) if last_week_payouts > 0 else 0
    volume_change = ((this_week_volume - last_week_volume) / last_week_volume * 100) if last_week_volume > 0 else 0
    
    # 5. Submission Heat Score
    # Calculate based on today's activity vs average daily activity

    start_date = datetime(2024, 1, 1, tzinfo=pytz.UTC)
    avg_daily_submissions = total_submissions / max((today - start_date).days, 1)
    
    if active_submissions_today >= avg_daily_submissions * 1.5:
        heat_score = "High Activity"
    elif active_submissions_today >= avg_daily_submissions * 0.7:
        heat_score = "Normal"
    else:
        heat_score = "Cooling"
    
    return Response({
        # SECTION 1: Global Performance Metrics (Top Header - Headline Stats)
        'global_metrics': {
            'total_verified_payouts': total_verified_payouts,  # e.g., 128,493 verified payouts
            'total_payout_volume': float(total_payout_volume),  # e.g., $17,203,912 processed
            'active_servers': active_servers_count,  # servers with ≥1 verified payout in last 30d
            'active_submissions_today': active_submissions_today,  # live ecosystem activity
            'system_uptime': system_uptime  # e.g., 99.99% uptime → institutional credibility
        },
        
        # SECTION 2: Global Ecosystem Trends (Graphs + Charts)
        'ecosystem_trends': {
            'monthly_volume': monthly_volume_data,  # Line chart: monthly payout volume
            'monthly_count': monthly_count_data,  # Bar chart: monthly payout count
            'category_breakdown': category_breakdown_data,  # Pie/Donut: market category distribution
            'growth_curve': ecosystem_growth_data,  # Line chart: cumulative growth over time
            'payout_scatter': scatter_points  # Scatter plot: individual payout distribution over time
        },
        
        # SECTION 3: Global Highlights & Records (Hype & Story)
        'highlights_and_records': {
            'largest_payout_this_month': float(largest_payout_this_month) if largest_payout_this_month else 0,
            'fastest_growing_server': fastest_growing or "N/A",
            'milestone_message': milestone_message,
            'seven_day_trends': {
                'this_week_payouts': this_week_payouts,
                'this_week_volume': round(this_week_volume, 2),
                'payouts_change_percent': round(payouts_change, 2),
                'volume_change_percent': round(volume_change, 2)
            },
            'submission_heat_score': heat_score
        },
        
        # Legacy fields (for backward compatibility)
        'total_volume': float(total_payout_volume),
        'total_submissions': total_submissions,
        'total_verified_payouts': total_verified_payouts,
        'daily_volume': float(daily_volume),
        'daily_submissions': daily_submissions,
        'active_submissions_today': active_submissions_today,
        'active_servers': active_servers_count,
        'system_uptime': system_uptime,
        
        # Submission status breakdown
        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'suspicious_count': suspicious_count,
        'approval_rate': approval_rate,
        'pending_rate': pending_rate,
        'rejection_rate': rejection_rate,
        'suspicious_rate': suspicious_rate,
        
        # Market and trend data
        'market_comparison': market_comparison,
        'daily_trends': daily_trends_data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def market_detail(request):
    """
    Deep dive analytics for a specific market category.
    
    Query params:
    - market_category: futures, forex, crypto, options, equities (case-insensitive)
    
    Returns:
    - Total volume, avg payout, unique traders/servers/instruments
    - Instrument breakdown with heatmap data
    - Top servers and traders for that market
    - Timeframe distribution (placeholder)
    """
    
    # Get market category and capitalize to match database values
    market_category = request.query_params.get('market_category', 'futures').capitalize()
    
    # Filter approved submissions for this market
    submissions = PayoutSubmission.objects.filter(
        status='Approved',
        market_category=market_category
    )
    
    # Overall stats
    stats = submissions.aggregate(
        total_payouts=Sum('amount'),
        avg_payout=Avg('amount'),
        median_payout=Avg('amount'),  # Simplified - use proper median in production
        total_submissions=Count('id'),
        unique_traders=Count('user', distinct=True),
        unique_servers=Count('server', distinct=True),
        unique_instruments=Count('instrument', distinct=True)
    )
    
    # Instrument analytics
    instruments = submissions.values('instrument').annotate(
        total_payout=Sum('amount'),
        submission_count=Count('id'),
        avg_payout=Avg('amount'),
        unique_traders=Count('user', distinct=True)
    ).order_by('-total_payout')
    
    instruments_data = [{
        'instrument': inst['instrument'],
        'total_payout': float(inst['total_payout']),
        'submission_count': inst['submission_count'],
        'avg_payout': float(inst['avg_payout']),
        'unique_traders': inst['unique_traders']
    } for inst in instruments]
    
    # Top servers in this market
    top_servers = submissions.values(
        'server__id',
        'server__name'
    ).annotate(
        total_payout=Sum('amount'),
        submission_count=Count('id')
    ).order_by('-total_payout')[:10]
    
    top_servers_data = [{
        'server_id': str(server['server__id']),
        'server_name': server['server__name'],
        'profile_url': f'/servers/{str(server["server__id"])}/public',
        'total_payout': float(server['total_payout']),
        'submission_count': server['submission_count']
    } for server in top_servers]
    
    # Top traders in this market
    from utils.privacy import get_public_trader_view, mask_trader_stats
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    top_traders = submissions.values(
        'user__id',
        'user__username'
    ).annotate(
        total_payout=Sum('amount'),
        submission_count=Count('id'),
        avg_payout=Avg('amount'),
        instrument_count=Count('instrument', distinct=True)
    ).order_by('-total_payout')[:10]
    
    top_traders_data = []
    for trader in top_traders:
        user = User.objects.get(id=trader['user__id'])
        trader_view = get_public_trader_view(user, requesting_user=None, has_valid_token=False)
        
        stats = {
            'total_payout': float(trader['total_payout']),
            'submission_count': trader['submission_count'],
            'avg_payout': float(trader['avg_payout']),
            'instrument_count': trader['instrument_count']
        }
        
        # Public analytics endpoint - mask if user has privacy enabled
        should_mask = trader_view['is_private']
        masked_stats = mask_trader_stats(stats, should_mask)
        
        top_traders_data.append({
            'user_id': trader_view['id'],
            'username': trader_view['username'],
            'profile_url': f'/trader/{trader_view["id"]}/public',
            'is_private': trader_view['is_private'],
            **masked_stats
        })
    
    # Timeframe distribution (placeholder - add timeframe field if needed)
    timeframes = [
        {'timeframe': '1 min', 'count': 0},
        {'timeframe': '5 min', 'count': 0},
        {'timeframe': '15 min', 'count': 0},
        {'timeframe': '30 min', 'count': 0},
        {'timeframe': '1 hour', 'count': 0},
        {'timeframe': '4 hour', 'count': 0},
        {'timeframe': 'Daily', 'count': 0},
    ]
    
    return Response({
        'market_category': market_category,
        'total_payouts': float(stats['total_payouts'] or 0),
        'avg_payout': float(stats['avg_payout'] or 0),
        'median_payout': float(stats['median_payout'] or 0),
        'total_submissions': stats['total_submissions'],
        'unique_traders': stats['unique_traders'],
        'unique_servers': stats['unique_servers'],
        'unique_instruments': stats['unique_instruments'],
        'instruments': instruments_data,
        'top_servers': top_servers_data,
        'top_traders': top_traders_data,
        'timeframes': timeframes
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def monthly_awards(request):
    """
    Monthly awards and achievements.
    
    Returns:
    - Server of the Month (highest volume)
    - Trader of the Month (highest earnings)
    - Rising Star (highest growth rate)
    - Most Active Community (most submissions)
    - Historical winners
    """
    
    # Current month
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get current month data
    current_month_submissions = PayoutSubmission.objects.filter(
        status='Approved',
        created_at__gte=month_start
    )
    
    # Server of the Month (highest volume)
    server_of_month = current_month_submissions.values(
        'server__id',
        'server__name'
    ).annotate(
        total_volume=Sum('amount')
    ).order_by('-total_volume').first()
    
    server_winner = {
        'id': str(server_of_month['server__id']),
        'name': server_of_month['server__name'],
        'profile_url': f'/servers/{str(server_of_month["server__id"])}/public',
        'value': float(server_of_month['total_volume'])
    } if server_of_month else None
    
    # Trader of the Month (highest earnings)
    trader_of_month = current_month_submissions.values(
        'user__id',
        'user__username'
    ).annotate(
        total_volume=Sum('amount')
    ).order_by('-total_volume').first()
    
    trader_winner = {
        'id': str(trader_of_month['user__id']),
        'name': trader_of_month['user__username'],
        'profile_url': f'/trader/{str(trader_of_month["user__id"])}/public',
        'value': float(trader_of_month['total_volume'])
    } if trader_of_month else None
    
    # Rising Star (new server with high volume)
    # Servers created this month
    rising_star_server = Server.objects.filter(
        created_at__gte=month_start
    ).annotate(
        total_volume=Sum(
            'payout_submissions__amount',
            filter=Q(payout_submissions__status='Approved')
        )
    ).order_by('-total_volume').first()
    
    rising_star = {
        'id': str(rising_star_server.id) if rising_star_server else None,
        'name': rising_star_server.name if rising_star_server else 'N/A',
        'profile_url': f'/servers/{str(rising_star_server.id)}/public' if rising_star_server else None,
        'value': float(rising_star_server.total_volume) if rising_star_server and rising_star_server.total_volume else 0
    } if rising_star_server else None
    
    # Most Active Community (most submissions)
    most_active = current_month_submissions.values(
        'server__id',
        'server__name'
    ).annotate(
        submission_count=Count('id')
    ).order_by('-submission_count').first()
    
    most_active_winner = {
        'id': str(most_active['server__id']),
        'name': most_active['server__name'],
        'profile_url': f'/servers/{str(most_active["server__id"])}/public',
        'value': f"{most_active['submission_count']} submissions"
    } if most_active else None
    
    # Historical winners (last 6 months)
    historical = []
    for i in range(1, 7):
        month_date = (now - timedelta(days=30*i)).replace(day=1)
        month_name = month_date.strftime('%B %Y')
        
        # Get winners for that month
        month_end = (month_date + timedelta(days=32)).replace(day=1)
        month_submissions = PayoutSubmission.objects.filter(
            status='Approved',
            created_at__gte=month_date,
            created_at__lt=month_end
        )
        
        server = month_submissions.values('server__name').annotate(
            total=Sum('amount')
        ).order_by('-total').first()
        
        trader = month_submissions.values('user__username').annotate(
            total=Sum('amount')
        ).order_by('-total').first()
        
        historical.append({
            'month': month_name,
            'server': server['server__name'] if server else 'N/A',
            'trader': trader['user__username'] if trader else 'N/A',
            'rising_star': 'N/A'
        })
    
    return Response({
        'server_of_month': server_winner,
        'trader_of_month': trader_winner,
        'rising_star': rising_star,
        'most_active': most_active_winner,
        'historical': historical
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def public_server_analytics(request, server_id):
    """
    Public analytics view for a specific server.
    
    Shows:
    1. Total verified payout volume time series (line graph)
    2. Verified payout count per day/week (bar chart with top 3 payouts)
    3. Top traders contribution (stacked contribution graph)
    4. Payout momentum score (rolling trend graph)
    
    This is the PUBLIC view - no private/subscription data.
    """
    server = get_object_or_404(Server, id=server_id)
    
    # Get all approved payouts for this server
    approved_payouts = PayoutSubmission.objects.filter(
        server_id=server_id,
        status='approved'
    ).order_by('created_at')
    
    if not approved_payouts.exists():
        return Response({
            'server': {
                'id': str(server.id),
                'name': server.name,
                'profile_url': f'/servers/{str(server.id)}/public',
            },
            'message': 'No verified payouts yet',
            'has_data': False
        })
    
    # ===== 1. TOTAL VERIFIED PAYOUT VOLUME (TIME SERIES) =====
    # Cumulative sum over time for "net worth chart"
    daily_cumulative = []
    running_total = 0
    
    daily_aggregates = approved_payouts.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        daily_total=Sum('amount')
    ).order_by('date')
    
    for entry in daily_aggregates:
        running_total += float(entry['daily_total'])
        daily_cumulative.append({
            'date': entry['date'].strftime('%Y-%m-%d'),
            'total_volume': round(running_total, 2)
        })
    
    volume_time_series = {
        'data': daily_cumulative,
        'current_total': round(running_total, 2),
        'first_payout_date': daily_cumulative[0]['date'] if daily_cumulative else None,
        'growth_period_days': (timezone.now().date() - approved_payouts.first().created_at.date()).days if approved_payouts.exists() else 0
    }
    
    # ===== 2. VERIFIED PAYOUT COUNT PER WEEK (ACTIVITY GRAPH) =====
    # Bi-weekly/monthly breakdown with top 3 payouts per period
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Get weekly aggregates (last 30 days)
    weekly_activity = approved_payouts.filter(
        created_at__gte=thirty_days_ago
    ).annotate(
        week=TruncWeek('created_at')
    ).values('week').annotate(
        total_paid=Sum('amount'),
        submission_count=Count('id'),
        unique_traders=Count('user', distinct=True)
    ).order_by('week')
    
    activity_data = []
    for week_data in weekly_activity:
        week_start = week_data['week']
        week_end = week_start + timedelta(days=7)
        
        # Get top 3 payouts for this week
        top_3_payouts = approved_payouts.filter(
            created_at__gte=week_start,
            created_at__lt=week_end
        ).order_by('-amount').values(
            'amount',
            'user__username',
            'instrument',
            'created_at'
        )[:3]
        
        # PUBLIC VIEW: No detailed top 3 payouts per week
        activity_data.append({
            'week_start': week_start.strftime('%Y-%m-%d'),
            'total_paid': round(float(week_data['total_paid']), 2),
            'submission_count': week_data['submission_count'],
            'unique_traders': week_data['unique_traders']
        })
    
    # ===== 3. TOP TRADERS CONTRIBUTION (STACKED GRAPH) =====
    # Shows which traders contribute most volume (dependency analysis)
    # PUBLIC VIEW: Limited to Top 3 (Standard+ shows more)
    from utils.privacy import get_public_trader_view, mask_trader_stats
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    top_traders = approved_payouts.values(
        'user__id',
        'user__username'
    ).annotate(
        total_contribution=Sum('amount'),
        submission_count=Count('id')
    ).order_by('-total_contribution')[:3]  # Limited to top 3 for public
    
    trader_contributions = []
    for trader in top_traders:
        user = User.objects.get(id=trader['user__id'])
        trader_view = get_public_trader_view(user, requesting_user=None, has_valid_token=False)
        
        stats = {
            'total_contribution': round(float(trader['total_contribution']), 2),
            'submission_count': trader['submission_count'],
            'percentage': round((float(trader['total_contribution']) / running_total * 100) if running_total > 0 else 0, 2)
        }
        
        # Public analytics endpoint - mask if user has privacy enabled
        should_mask = trader_view['is_private']
        masked_stats = mask_trader_stats(stats, should_mask)
        
        trader_contributions.append({
            'trader_id': trader_view['id'],
            'username': trader_view['username'],
            'is_private': trader_view['is_private'],
            **masked_stats
        })
    
    # Calculate community health (concentration risk)
    top_3_percentage = sum(t['percentage'] for t in trader_contributions[:3])
    
    if top_3_percentage > 70:
        community_depth = 'Fragile'
        depth_description = 'Heavy reliance on few traders'
    elif top_3_percentage > 50:
        community_depth = 'Moderate'
        depth_description = 'Some concentration, diversify encouraged'
    else:
        community_depth = 'Strong'
        depth_description = 'Healthy distribution across traders'
    
    # ===== 4. PAYOUT MOMENTUM SCORE (SIMPLIFIED) =====
    # PUBLIC VIEW: Icon and status only, no detailed breakdown
    seven_days_ago = now - timedelta(days=7)
    
    volume_7d = approved_payouts.filter(
        created_at__gte=seven_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    volume_30d = approved_payouts.filter(
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate daily averages
    avg_7d = float(volume_7d) / 7
    avg_30d = float(volume_30d) / 30
    
    # Momentum ratio
    momentum_ratio = (avg_7d / avg_30d) if avg_30d > 0 else 1.0
    
    # Status determination
    if momentum_ratio >= 1.2:
        momentum_status = 'Accelerating'
        momentum_icon = ''
    elif momentum_ratio >= 1.05:
        momentum_status = 'Growing'
        momentum_icon = ''
    elif momentum_ratio >= 0.95:
        momentum_status = 'Stable'
        momentum_icon = ''
    elif momentum_ratio >= 0.8:
        momentum_status = 'Slowing'
        momentum_icon = ''
    else:
        momentum_status = 'Cooling'
        momentum_icon = ''
    
    # PUBLIC VIEW: Simplified - no detailed timeline or averages
    momentum_data = {
        'status': momentum_status,
        'icon': momentum_icon,
        'description': f'Recent activity is {"heating up" if momentum_ratio > 1.1 else ("cooling down" if momentum_ratio < 0.9 else "steady")}'
    }
    
    # ===== 5. VERIFIED PAYOUT TIMELINE (EVENT TIMELINE) =====
    # Visual heartbeat of the server - each payout as a dot
    # Get recent payouts (last 90 days for performance)
    ninety_days_ago = now - timedelta(days=90)
    recent_payouts = approved_payouts.filter(
        created_at__gte=ninety_days_ago
    ).order_by('-created_at')
    
    # Filter options (optional query params)
    filter_trader = request.query_params.get('trader_id')
    filter_market = request.query_params.get('market_category')
    
    # ===== 5. VERIFIED PAYOUT TIMELINE (SIMPLIFIED) =====
    # PUBLIC VIEW: Count only, no detailed events (Standard+ shows timeline)
    ninety_days_ago = now - timedelta(days=90)
    recent_payout_count = approved_payouts.filter(
        created_at__gte=ninety_days_ago
    ).count()
    
    # ===== 6. SERVER HEALTH SCORE (SIMPLIFIED) =====
    # PUBLIC VIEW: Overall score only, no component breakdown (Standard+ shows breakdown)
    
    # Quick calculation for overall health
    submissions_per_day = approved_payouts.filter(
        created_at__gte=thirty_days_ago
    ).count() / 30
    
    # Simplified scoring
    if submissions_per_day >= 10:
        activity_score = 100
    elif submissions_per_day >= 5:
        activity_score = 70 + (submissions_per_day - 5) * 6
    elif submissions_per_day >= 1:
        activity_score = 40 + (submissions_per_day - 1) * 7.5
    else:
        activity_score = max(submissions_per_day * 40, 10)
    
    # Simple diversity check
    if top_3_percentage < 30:
        diversity_score = 100
    elif top_3_percentage < 50:
        diversity_score = 70
    elif top_3_percentage < 70:
        diversity_score = 50
    else:
        diversity_score = 30
    
    # Overall health (simplified)
    overall_health = (activity_score + diversity_score) / 2
    
    # Health rating
    if overall_health >= 90:
        health_rating = 'Exceptional'
        health_badge = ''
    elif overall_health >= 80:
        health_rating = 'Excellent'
        health_badge = ''
    elif overall_health >= 70:
        health_rating = 'Strong'
        health_badge = ''
    elif overall_health >= 60:
        health_rating = 'Good'
        health_badge = ''
    elif overall_health >= 50:
        health_rating = 'Fair'
        health_badge = ''
    else:
        health_rating = 'Needs Improvement'
        health_badge = ''
    
    health_breakdown = {
        'overall_score': round(overall_health, 1),
        'rating': health_rating,
        'badge': health_badge,
        'message': 'Subscribe to see detailed health component breakdown'
    }
    
    # ===== 7. SERVER RANK (CURRENT ONLY) =====
    # PUBLIC VIEW: Current rank only, no timeline (Premium+ shows progression)
    from analytics.models import ServerRanking
    
    current_ranking = ServerRanking.objects.filter(
        server_id=server_id
    ).order_by('-last_updated').first()
    
    rank_data = {
        'current_rank': current_ranking.global_rank if current_ranking else None,
        'message': 'Subscribe to see rank progression timeline'
    }
    
    # ===== 8. EXTRA STATS =====
    
    # Fastest Growing Week
    fastest_week = None
    max_weekly_volume = 0
    
    for i, week_data in enumerate(activity_data):
        if week_data['total_paid'] > max_weekly_volume:
            max_weekly_volume = week_data['total_paid']
            fastest_week = {
                'week_number': i + 1,
                'date': week_data['week_start'],
                'volume': round(week_data['total_paid'], 2),
                'description': f"Best week: +${round(week_data['total_paid'], 2):,.2f}"
            }
    
    # Average Time Between Payouts
    if approved_payouts.count() > 1:
        first_payout = approved_payouts.first().created_at
        last_payout = approved_payouts.last().created_at
        total_days = (last_payout - first_payout).total_seconds() / 86400
        avg_time_between = total_days / (approved_payouts.count() - 1)
        
        if avg_time_between < 1:
            time_between_display = f"{avg_time_between * 24:.1f} hours"
        else:
            time_between_display = f"{avg_time_between:.1f} days"
    else:
        avg_time_between = 0
        time_between_display = "N/A"
    
    # Submission Acceptance Rate (legitimacy flex)
    all_server_submissions = PayoutSubmission.objects.filter(server_id=server_id)
    total_submissions = all_server_submissions.count()
    approved_count = approved_payouts.count()
    rejected_count = all_server_submissions.filter(status='rejected').count()
    pending_count = all_server_submissions.filter(status='pending').count()
    
    acceptance_rate = (approved_count / total_submissions * 100) if total_submissions > 0 else 0
    
    if acceptance_rate >= 95:
        acceptance_badge = 'Elite'
    elif acceptance_rate >= 90:
        acceptance_badge = 'Excellent'
    elif acceptance_rate >= 80:
        acceptance_badge = 'Strong'
    elif acceptance_rate >= 70:
        acceptance_badge = 'Good'
    else:
        acceptance_badge = 'Fair'
    
    # ===== 7. SERVER RANK (CURRENT ONLY) =====
    # PUBLIC VIEW: Current rank only, no timeline (Premium+ shows progression)
    from analytics.models import ServerRanking
    
    current_ranking = ServerRanking.objects.filter(
        server_id=server_id
    ).order_by('-last_updated').first()
    
    rank_data = {
        'current_rank': current_ranking.global_rank if current_ranking else None,
        'message': 'Subscribe to see rank progression timeline'
    }
    
    # ===== 8. EXTRA STATS =====
    
    # Fastest Growing Week
    fastest_week = None
    max_weekly_volume = 0
    
    for i, week_data in enumerate(activity_data):
        if week_data['total_paid'] > max_weekly_volume:
            max_weekly_volume = week_data['total_paid']
            fastest_week = {
                'week_number': i + 1,
                'date': week_data['week_start'],
                'volume': round(week_data['total_paid'], 2),
                'description': f"Best week: +${round(week_data['total_paid'], 2):,.2f}"
            }
    
    # Monthly Payout Volume Change (%)
    sixty_days_ago = now - timedelta(days=60)
    
    current_month_volume = approved_payouts.filter(
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    previous_month_volume = approved_payouts.filter(
        created_at__gte=sixty_days_ago,
        created_at__lt=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_change = ((float(current_month_volume) - float(previous_month_volume)) / float(previous_month_volume) * 100) if previous_month_volume > 0 else 0
    
    monthly_change_display = f"+{round(monthly_change, 1)}%" if monthly_change > 0 else f"{round(monthly_change, 1)}%"
    
    # Time Since Last Payout
    last_payout_obj = approved_payouts.last()
    if last_payout_obj:
        time_since_last = now - last_payout_obj.created_at
        hours_since = time_since_last.total_seconds() / 3600
        days_since = time_since_last.days
        
        if hours_since < 1:
            time_since_display = f"{int(time_since_last.total_seconds() / 60)} minutes ago"
        elif hours_since < 24:
            time_since_display = f"{int(hours_since)} hours ago"
        elif days_since == 1:
            time_since_display = "1 day ago"
        else:
            time_since_display = f"{days_since} days ago"
    else:
        time_since_display = "No payouts yet"
    
    # PUBLIC VIEW: Limited extra stats
    extra_stats = {
        'avg_time_between_payouts': {
            'display': time_between_display,
            'description': 'Average community engagement frequency'
        },
        'submission_acceptance': {
            'rate': round(acceptance_rate, 1),
            'badge': acceptance_badge,
            'description': 'Submission quality indicator'
        },
        'monthly_volume_change': {
            'percentage': round(monthly_change, 1),
            'display': monthly_change_display,
            'direction': 'up' if monthly_change > 0 else ('down' if monthly_change < 0 else 'stable')
        },
        'top_3_volume_share': {
            'percentage': round(top_3_percentage, 1),
            'display': f"{round(top_3_percentage, 1)}% of volume",
            'description': 'Distribution health indicator'
        },
        'last_payout': {
            'date': last_payout_obj.created_at.strftime('%Y-%m-%d %H:%M') if last_payout_obj else None,
            'time_ago': time_since_display,
            'amount': round(float(last_payout_obj.amount), 2) if last_payout_obj else 0,
            'trader': last_payout_obj.user.username if last_payout_obj else None
        }
    }
    
    # ===== 9. BONUS METRICS (Quick Stats) =====
    # Small but impactful metrics for richness
    
    # Total payouts by timeframe
    seven_days_ago = now - timedelta(days=7)
    ninety_days_ago_calc = now - timedelta(days=90)
    
    total_payouts_alltime = approved_payouts.aggregate(
        count=Count('id'),
        volume=Sum('amount')
    )
    
    total_payouts_90d = approved_payouts.filter(
        created_at__gte=ninety_days_ago_calc
    ).aggregate(
        count=Count('id'),
        volume=Sum('amount')
    )
    
    total_payouts_7d = approved_payouts.filter(
        created_at__gte=seven_days_ago
    ).aggregate(
        count=Count('id'),
        volume=Sum('amount')
    )
    
    # Total traders by timeframe
    total_traders_alltime = approved_payouts.values('user').distinct().count()
    
    total_traders_this_month = approved_payouts.filter(
        created_at__gte=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ).values('user').distinct().count()
    
    # Monthly Payout Volume Change (%)
    sixty_days_ago = now - timedelta(days=60)
    
    current_month_volume = approved_payouts.filter(
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    previous_month_volume = approved_payouts.filter(
        created_at__gte=sixty_days_ago,
        created_at__lt=thirty_days_ago
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_change = ((float(current_month_volume) - float(previous_month_volume)) / float(previous_month_volume) * 100) if previous_month_volume > 0 else 0
    
    monthly_change_display = f"+{round(monthly_change, 1)}%" if monthly_change > 0 else f"{round(monthly_change, 1)}%"
    
    # Time Since Last Payout
    last_payout_obj = approved_payouts.last()
    if last_payout_obj:
        time_since_last = now - last_payout_obj.created_at
        hours_since = time_since_last.total_seconds() / 3600
        days_since = time_since_last.days
        
        if hours_since < 1:
            time_since_display = f"{int(time_since_last.total_seconds() / 60)} minutes ago"
        elif hours_since < 24:
            time_since_display = f"{int(hours_since)} hours ago"
        elif days_since == 1:
            time_since_display = "1 day ago"
        else:
            time_since_display = f"{days_since} days ago"
    else:
        time_since_display = "No payouts yet"
    
    # PUBLIC VIEW: Limited extra stats
    extra_stats = {
        'avg_time_between_payouts': {
            'display': time_between_display,
            'description': 'Average community engagement frequency'
        },
        'submission_acceptance': {
            'rate': round(acceptance_rate, 1),
            'badge': acceptance_badge,
            'description': 'Submission quality indicator'
        },
        'monthly_volume_change': {
            'percentage': round(monthly_change, 1),
            'display': monthly_change_display,
            'direction': 'up' if monthly_change > 0 else ('down' if monthly_change < 0 else 'stable')
        },
        'top_3_volume_share': {
            'percentage': round(top_3_percentage, 1),
            'display': f"Top 3 = {round(top_3_percentage, 1)}% of volume",
            'description': 'Distribution health indicator'
        },
        'last_payout': {
            'time_ago': time_since_display,
            'description': 'Server activity recency'
        }
    }
    
    # ===== 9. BONUS METRICS (LIMITED) =====
    # PUBLIC VIEW: All-time stats only (Standard+ shows breakdowns)
    
    total_payouts_alltime = approved_payouts.aggregate(
        count=Count('id'),
        volume=Sum('amount')
    )
    
    # Server age on Aurevia
    server_age = (now - server.created_at).days
    if server_age < 30:
        age_display = f"{server_age} days"
    elif server_age < 365:
        age_display = f"{server_age // 30} months"
    else:
        years = server_age // 365
        remaining_months = (server_age % 365) // 30
        age_display = f"{years} year{'s' if years > 1 else ''}" + (f", {remaining_months} month{'s' if remaining_months > 1 else ''}" if remaining_months > 0 else "")
    
    # First verified payout date
    first_payout = approved_payouts.first()
    first_payout_date = first_payout.created_at.strftime('%B %d, %Y') if first_payout else None
    
    bonus_metrics = {
        'all_time': {
            'total_payouts': total_payouts_alltime['count'],
            'total_volume': round(float(total_payouts_alltime['volume'] or 0), 2),
            'total_traders': total_traders_alltime
        },
        'server_age': {
            'display': age_display,
            'joined_date': server.created_at.strftime('%B %d, %Y')
        },
        'first_payout': {
            'date': first_payout_date
        },
        'message': 'Subscribe to see detailed historical breakdowns (7d, 30d, 90d, best month)'
    }
    
    # ===== RESPONSE =====
    return Response({
        'server': {
            'id': str(server.id),
            'name': server.name,
            'profile_url': f'/servers/{str(server.id)}/public',
        },
        'has_data': True,
        'volume_time_series': volume_time_series,
        'weekly_activity': {
            'data': activity_data,
            'total_weeks': len(activity_data)
        },
        'trader_contributions': {
            'top_traders': trader_contributions,
            'community_depth': community_depth,
            'depth_description': depth_description,
            'top_3_concentration': round(top_3_percentage, 2),
            'message': 'Subscribe to see top 5-15 traders'
        },
        'momentum_intelligence': momentum_data,
        'payout_timeline': {
            'recent_count': recent_payout_count,
            'message': 'Subscribe to see detailed payout event timeline with filters'
        },
        'health_breakdown': health_breakdown,
        'rank_progression': rank_data,
        'extra_stats': extra_stats,
        'bonus_metrics': bonus_metrics
    })


from servers.services.ranking_service import RankingService
from datetime import datetime

@api_view(['GET'])
@permission_classes([AllowAny])
def top_servers_leaderboard(request):
    """
    Top servers leaderboard using centralized RankingService.
    
    Now uses cached global rankings for consistency and performance.
    Filtering and pagination are applied to the cached dataset.
    """
    try:
        # 1. Get Global Rankings (Cached)
        # This returns the full list of verified servers, scored and ranked globally
        all_servers = RankingService.get_rankings()
    
        # 2. Parse Filter Parameters
        
        # Platform filter
        platform_param = request.GET.get('platform', '').strip().lower()
        platform_param = ''.join(c for c in platform_param if c.isalnum())
        
        # Category filter
        category_param = request.GET.get('category', '').strip().lower()
        category_param = ''.join(c for c in category_param if c.isalnum())
        
        # Timeframe (Server Age) filter
        timeframe_param = request.GET.get('timeframe', 'all').strip().lower()
        valid_timeframes = ['7d', '30d', '90d', 'all']
        timeframe = timeframe_param if timeframe_param in valid_timeframes else 'all'
        
        # Min Volume filter
        try:
            min_volume = float(request.GET.get('min_volume', 0))
        except (ValueError, TypeError):
            min_volume = 0
            
        # Sort parameter
        sort_param = request.GET.get('sort_by', 'volume').strip().lower()
        valid_sorts = {
            'volume': 'total_volume',
            'payouts': 'total_payouts',
            'growth': 'volume_change_30d',
            'activity': 'active_submitters_30d',
            'approval_rate': 'approval_rate',
            'score': 'total_score'
        }
        
        # Limit
        try:
            limit = int(request.GET.get('limit', 10))
            limit = max(1, min(limit, 1000))
        except ValueError:
            limit = 10

        # 3. Apply Filters in Memory
        filtered_list = all_servers

        if platform_param:
            filtered_list = [
                s for s in filtered_list 
                if platform_param in s['server'].get('platform', '').lower()
            ]
            
        if category_param and category_param != 'mixed':
            filtered_list = [
                s for s in filtered_list 
                if category_param in s['metadata'].get('category', '').lower()
            ]
            
        if min_volume > 0:
            filtered_list = [
                s for s in filtered_list 
                if s['metrics'].get('total_volume', 0) >= min_volume
            ]
            
        if timeframe != 'all':
            now = datetime.fromisoformat(all_servers[0]['metadata']['established']).now().astimezone() if all_servers else timezone.now()
            days_map = {'7d': 7, '30d': 30, '90d': 90}
            days = days_map.get(timeframe, 36500)
            cutoff = now - timedelta(days=days)
            
            filtered_list = [
                s for s in filtered_list 
                if datetime.fromisoformat(s['metadata']['established']) >= cutoff
            ]

        # 4. Apply Sorting
        if sort_param in valid_sorts and sort_param != 'score':
            key = valid_sorts[sort_param]
            def get_sort_val(item):
                if key in item: return item[key]
                if key in item['metrics']: return item['metrics'][key]
                if key in item['scores']: return item['scores'][key]
                return 0
                
            filtered_list.sort(key=get_sort_val, reverse=True)
        elif sort_param == 'score':
            pass
            
        # 5. Pagination
        paginated_result = filtered_list[:limit]
        
        return Response(paginated_result)

    except Exception as e:
        import traceback
        print("CRITICAL ERROR in top_servers_leaderboard:")
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def global_timeseries(request):
    """
    Returns timeseries data for a selected metric over a specified period.
    
    Query params:
    - metric: 'total_verified_payouts', 'total_payout_volume', 'active_servers', 'active_submissions_today', 'system_uptime'
    - period: 'week', 'month', 'year' (aggregation period)
    - market: optional market category filter (e.g., 'Futures', 'Forex', 'Crypto', 'Options', 'Equities')
    
    Returns:
    - timeseries: [{ date: 'YYYY-MM-DD', value: number }, ...]
    """
    
    # Sanitize and validate inputs
    metric = request.GET.get('metric', 'total_verified_payouts').strip()
    period = request.GET.get('period', 'month').strip().lower()
    market = request.GET.get('market', '').strip()
    
    # Validate metric
    valid_metrics = [
        'total_verified_payouts',
        'total_payout_volume',
        'active_servers',
        'active_submissions_today',
        'system_uptime'
    ]
    if metric not in valid_metrics:
        return Response({'error': 'Invalid metric'}, status=http_status.HTTP_400_BAD_REQUEST)
    
    # Validate period
    if period == 'week':
        trunc_func = TruncWeek
        date_format = '%Y-%m-%d'
        lookback_days = 90  # Last ~12 weeks
    elif period == 'year':
        trunc_func = TruncYear
        date_format = '%Y'
        lookback_days = 1095  # Last 3 years
    else:  # default to month
        trunc_func = TruncMonth
        date_format = '%Y-%m'
        lookback_days = 365  # Last 12 months
    
    now = timezone.now()
    start_date = now - timedelta(days=lookback_days)
    
    # Base query: approved submissions
    base_query = PayoutSubmission.objects.filter(status='Approved', created_at__gte=start_date)
    
    # Apply market filter if provided
    if market and market.lower() != 'all':
        # Sanitize market name
        market_clean = ''.join(c for c in market if c.isalpha())
        if market_clean:
            base_query = base_query.filter(market_category__iexact=market_clean)
    
    # Generate timeseries based on metric
    timeseries = []
    
    if metric == 'total_verified_payouts':
        # Count of approved payouts per period
        data = base_query.annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            value=Count('id')
        ).order_by('period')
        
        timeseries = [{
            'date': item['period'].strftime(date_format),
            'value': item['value']
        } for item in data]
    
    elif metric == 'total_payout_volume':
        # Sum of payout amounts per period
        data = base_query.annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            value=Sum('amount')
        ).order_by('period')
        
        timeseries = [{
            'date': item['period'].strftime(date_format),
            'value': float(item['value'] or 0)
        } for item in data]
    
    elif metric == 'active_servers':
        # Distinct servers per period
        data = base_query.annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            value=Count('server_id', distinct=True)
        ).order_by('period')
        
        timeseries = [{
            'date': item['period'].strftime(date_format),
            'value': item['value']
        } for item in data]
    
    elif metric == 'active_submissions_today':
        # Total submissions (all statuses) per period
        all_submissions = PayoutSubmission.objects.filter(created_at__gte=start_date)
        if market and market.lower() != 'all':
            market_clean = ''.join(c for c in market if c.isalpha())
            if market_clean:
                all_submissions = all_submissions.filter(market_category__iexact=market_clean)
        
        data = all_submissions.annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            value=Count('id')
        ).order_by('period')
        
        timeseries = [{
            'date': item['period'].strftime(date_format),
            'value': item['value']
        } for item in data]
    
    elif metric == 'system_uptime':
        # Placeholder: system uptime is typically a constant or monitored externally
        # For demo purposes, return synthetic data showing high uptime
        data = base_query.annotate(
            period=trunc_func('created_at')
        ).values('period').distinct().order_by('period')
        
        timeseries = [{
            'date': item['period'].strftime(date_format),
            'value': 99.99  # Static uptime value
        } for item in data]
    
    return Response({
        'timeseries': timeseries,
        'metric': metric,
        'period': period,
        'market': market if market else 'all'
    })
