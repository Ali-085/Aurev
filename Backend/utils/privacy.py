"""
Privacy utilities for trader data masking and anonymization.
"""
from typing import Optional, Dict, Any


def get_volume_range(volume: float) -> str:
    """
    Get volume range bucket for privacy masking.
    
    Args:
        volume: The actual volume amount
        
    Returns:
        String representation of volume range
    """
    if volume < 10000:
        return "0-10k"
    elif volume < 50000:
        return "10k-50k"
    elif volume < 100000:
        return "50k-100k"
    elif volume < 500000:
        return "100k-500k"
    else:
        return "500k+"


def get_public_trader_view(
    user,
    requesting_user=None,
    has_valid_token: bool = False
) -> Dict[str, Any]:
    """
    Get public view of trader with privacy masking applied.
    
    SECURITY: Does not expose internal 'masked' flag to frontend.
    Frontend determines masking by checking data presence (null fields, etc).
    
    Args:
        user: The User model instance
        requesting_user: The user making the request (if authenticated)
        has_valid_token: Whether a valid private analytics token was provided
        
    Returns:
        Dictionary with trader data, masked if privacy is enabled.
        'is_private' indicates privacy setting, but not internal validation state.
    """
    # Allow full access if:
    # 1. Requesting user is the trader themselves
    # 2. Valid private analytics token provided
    # 3. Privacy is not enabled
    if (requesting_user and requesting_user.id == user.id) or has_valid_token or not user.privacy:
        return {
            'id': str(user.id),
            'username': user.username,
            'avatar_url': user.avatar_url,
            'is_private': user.privacy,
        }
    
    # Apply privacy masking
    return {
        'id': str(user.id),
        'username': user.get_masked_name(),
        'avatar_url': None,  # Hide avatar for private traders
        'is_private': True,
    }


def mask_trader_stats(stats: Dict[str, Any], is_masked: bool) -> Dict[str, Any]:
    """
    Mask trader statistics based on privacy settings.
    
    Args:
        stats: Dictionary containing trader statistics
        is_masked: Whether masking should be applied
        
    Returns:
        Dictionary with potentially masked statistics
    """
    if not is_masked:
        return stats
    
    masked_stats = {}
    
    # Only show volume range, not exact values
    if 'total_volume' in stats:
        masked_stats['volume_range'] = get_volume_range(stats['total_volume'])
    
    # Hide all other stats
    masked_stats['hidden'] = True
    masked_stats['message'] = 'Stats hidden by trader privacy settings'
    
    return masked_stats


def check_private_analytics_access(token: Optional[str], user) -> bool:
    """
    Check if provided token grants access to private analytics.
    
    Args:
        token: The token from query params or headers
        user: The User model instance
        
    Returns:
        True if token is valid and matches user's private analytics token
    """
    if not token or not user.privacy or not user.private_analytics_token:
        return False
    
    try:
        # Compare token strings
        return str(user.private_analytics_token) == str(token)
    except (ValueError, AttributeError):
        return False


def get_public_profile(
    user,
    requesting_user=None,
    has_valid_token: bool = False,
    server_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get public trader profile - PROFESSIONAL PERFORMANCE CARD ONLY.
    
    STRICT PRIVACY ENFORCEMENT:
    - NO personal data (real name, email, contact info)
    - NO sensitive trading info (deposits, balances, detailed history)
    - Shows ONLY: alias/handle, server context, lifetime volume, rank, payout feed
    - Headline stats: total volume, payout count, largest payout, active period, approval rate
    - Achievement badges: performance-based only (no sensitive data)
    
    Args:
        user: The User model instance
        requesting_user: The user making the request (if authenticated)
        has_valid_token: Whether a valid private analytics token was provided
        server_id: Optional UUID of specific server for context
        
    Returns:
        Dictionary with professional performance card data
    """
    from servers.models import ServerMember
    from payouts.models import PayoutSubmission
    from django.db.models import Sum, Count, F, Max, Q
    from django.utils import timezone
    from datetime import timedelta
    
    # Check if user has access (themselves or valid token)
    is_owner = requesting_user and requesting_user.id == user.id
    has_access = is_owner or has_valid_token
    
    # If privacy enabled and no access, return minimal anonymized version
    if user.privacy and not has_access:
        return {
            'id': str(user.id),
            'alias': user.get_masked_name(),
            'avatar_url': None,
            'is_private': True,
            'server_name': None,
            'server_rank': None,
            'contribution_percentage': None,
            'server_contribution_30d': None,
            'lifetime_volume': None,
            'lifetime_volume_range': 'Hidden',
            'total_verified_payout_count': None,
            'largest_verified_payout': None,
            'active_period': None,
            'approval_rate': None,
            'public_achievements': [],
            'chart_data': {
                'payout_timeline': [],
                'market_breakdown': {},
                'submission_accuracy_history': []
            },
            'recent_payouts': []
        }
    
    # Build professional performance card (privacy=false or has access)
    profile = {
        'id': str(user.id),
        'alias': user.username,  # Use username as alias (must be sanitized, never real name)
        'avatar_url': user.avatar_url,
        'is_private': user.privacy,
    }
    
    # === HEADLINE STATS CALCULATION ===
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)
    
    # OPTIMIZED: Get all payout submission stats with single query using select_related
    approved_payouts = PayoutSubmission.objects.filter(
        user=user, status='Approved'
    ).select_related('server', 'prop_firm')
    
    # OPTIMIZED: Single aggregate query for all stats
    from django.db.models import Q
    stats = PayoutSubmission.objects.filter(user=user).aggregate(
        total_volume=Sum('amount', filter=Q(status='Approved')),
        approved_count=Count('id', filter=Q(status='Approved')),
        largest_payout=Max('amount', filter=Q(status='Approved')),
        total_submissions=Count('id'),
        recent_30d=Count('id', filter=Q(status='Approved', payout_date__gte=thirty_days_ago)),
        recent_90d=Count('id', filter=Q(status='Approved', payout_date__gte=ninety_days_ago))
    )
    
    # Extract stats from single query
    lifetime_volume_data = {
        'total': stats['total_volume'],
        'count': stats['approved_count'],
        'largest': stats['largest_payout']
    }
    total_submissions = stats['total_submissions']
    
    lifetime_volume = float(lifetime_volume_data['total'] or 0)
    total_verified_count = lifetime_volume_data['count'] or 0
    largest_payout = float(lifetime_volume_data['largest'] or 0)
    
    # OPTIMIZED: Active period indicator from aggregated data
    recent_30d = stats['recent_30d'] > 0
    recent_90d = stats['recent_90d'] > 0
    
    if recent_30d:
        active_period = "Active in last 30 days"
    elif recent_90d:
        active_period = "Active in last 90 days"
    else:
        active_period = "Inactive"
    
    # Approval rate
    approval_rate = 0
    if total_submissions > 0:
        approval_rate = round((total_verified_count / total_submissions) * 100, 1)
    
    # === ACHIEVEMENT BADGES (SAFE ONLY) ===
    achievements = []
    
    # Volume-based clubs
    if lifetime_volume >= 100000:
        achievements.append("100K Club")
    elif lifetime_volume >= 50000:
        achievements.append("50K Club")
    elif lifetime_volume >= 25000:
        achievements.append("25K Club")
    elif lifetime_volume >= 10000:
        achievements.append("10K Club")
    
    # Elite performer (top tier)
    if lifetime_volume >= 100000 and approval_rate >= 90:
        achievements.append("Elite Performer")
    
    # Consistency badges
    if recent_30d:
        achievements.append("Active 30 Days")
    
    if approval_rate >= 90:
        achievements.append("90% Verification Accuracy")
    
    if total_verified_count >= 50:
        achievements.append("High Frequency Submitter")
    
    profile.update({
        'lifetime_volume': lifetime_volume,
        'lifetime_volume_range': get_volume_range(lifetime_volume) if user.privacy else None,
        'total_verified_payout_count': total_verified_count,
        'largest_verified_payout': largest_payout,
        'active_period': active_period,
        'approval_rate': approval_rate,
        'public_achievements': achievements,
    })
    
    # === SERVER CONTEXT ===
    # Get server context if server_id provided, otherwise use primary server
    server_member = None
    if server_id:
        try:
            server_member = ServerMember.objects.select_related('server').get(
                user=user,
                server_id=server_id
            )
        except ServerMember.DoesNotExist:
            pass
    else:
        # Get primary server (highest volume)
        server_member = ServerMember.objects.filter(user=user).order_by(
            '-total_verified_payouts'
        ).select_related('server').first()
    
    if server_member:
        # OPTIMIZED: Calculate all server stats in single aggregate query
        server_stats = PayoutSubmission.objects.filter(
            server=server_member.server,
            status='Approved'
        ).aggregate(
            server_total=Sum('amount'),
            server_30d=Sum('amount', filter=Q(payout_date__gte=thirty_days_ago)),
            trader_30d=Sum('amount', filter=Q(
                user=user,
                payout_date__gte=thirty_days_ago
            ))
        )
        
        server_total_volume = float(server_stats['server_total'] or 0)
        server_30d_volume = float(server_stats['server_30d'] or 0)
        trader_30d_volume = float(server_stats['trader_30d'] or 0)
        
        contribution = 0
        if server_total_volume > 0:
            contribution = round(
                (float(server_member.total_verified_payouts) / server_total_volume) * 100,
                2
            )
        
        contribution_30d = 0
        if server_30d_volume > 0:
            contribution_30d = round(
                (trader_30d_volume / server_30d_volume) * 100,
                2
            )
        
        # OPTIMIZED: Get server rank with single count query
        rank = ServerMember.objects.filter(
            server=server_member.server,
            total_verified_payouts__gt=server_member.total_verified_payouts
        ).count() + 1
        
        profile.update({
            'server_name': server_member.server.name,
            'server_rank': rank,
            'contribution_percentage': contribution,
            'server_contribution_30d': contribution_30d,
        })
    else:
        profile.update({
            'server_name': None,
            'server_rank': None,
            'contribution_percentage': None,
            'server_contribution_30d': None,
        })
    
    # === PERFORMANCE CHARTS DATA ===
    # Only include chart data if privacy is disabled
    chart_data = {
        'payout_timeline': [],
        'market_breakdown': {},
        'submission_accuracy_history': []
    }
    
    if not user.privacy or has_access:
        # 1. Payout Timeline - All approved payouts over time
        timeline_payouts = PayoutSubmission.objects.filter(
            user=user,
            status='Approved'
        ).values('payout_date', 'amount').order_by('payout_date')
        
        for payout in timeline_payouts:
            chart_data['payout_timeline'].append({
                'date': payout['payout_date'].isoformat(),
                'amount': float(payout['amount'])
            })
        
        # 2. Market Breakdown - Distribution by market category
        market_stats = PayoutSubmission.objects.filter(
            user=user,
            status='Approved'
        ).values('market_category').annotate(
            total_volume=Sum('amount'),
            count=Count('id')
        )
        
        for market in market_stats:
            category = market['market_category'] or 'Unknown'
            chart_data['market_breakdown'][category] = {
                'volume': float(market['total_volume']),
                'count': market['count'],
                'percentage': 0  # Will be calculated after totals known
            }
        
        # Calculate percentages for market breakdown
        total_market_volume = sum(m['volume'] for m in chart_data['market_breakdown'].values())
        if total_market_volume > 0:
            for category in chart_data['market_breakdown']:
                chart_data['market_breakdown'][category]['percentage'] = round(
                    (chart_data['market_breakdown'][category]['volume'] / total_market_volume) * 100,
                    1
                )
        
        # 3. Submission Accuracy History - Monthly approval rates
        from django.db.models.functions import TruncMonth
        
        monthly_stats = PayoutSubmission.objects.filter(
            user=user
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total=Count('id'),
            approved=Count('id', filter=Q(status='Approved'))
        ).order_by('month')
        
        for month_data in monthly_stats:
            total = month_data['total']
            approved = month_data['approved']
            accuracy = round((approved / total) * 100, 1) if total > 0 else 0
            
            chart_data['submission_accuracy_history'].append({
                'month': month_data['month'].isoformat(),
                'total_submissions': total,
                'approved_submissions': approved,
                'accuracy_rate': accuracy
            })
    
    profile['chart_data'] = chart_data
    
    # === RECENT PAYOUT FEED (PROFESSIONAL & CREDIBLE) ===
    # Shows reliability and transparency with detailed payout information
    recent_payouts_qs = PayoutSubmission.objects.filter(
        user=user,
        status='Approved'
    ).select_related('server', 'prop_firm').order_by('-payout_date')[:20]  # Increased to 20 for better feed
    
    recent_payouts = []
    for payout in recent_payouts_qs:
        payout_entry = {
            'id': str(payout.id),
            'amount': float(payout.amount),
            'amount_range': get_volume_range(payout.amount) if user.privacy else None,
            'currency': payout.currency,
            'payout_date': payout.payout_date.isoformat(),
            'market_category': payout.market_category,
            'instrument': payout.instrument,
            'server_name': payout.server.name if payout.server else None,
            # Prop firm is the actual firm that issued the payout (FTMO, TopStep, etc.)
            'firm_name': payout.prop_firm.name if payout.prop_firm else 'Unknown',
            'firm_logo_url': payout.prop_firm.logo_url if payout.prop_firm else None,
        }
        
        # Add screenshot thumbnail URL if available and privacy allows
        # Screenshots are public proof of credibility for approved payouts
        if payout.screenshot:
            payout_entry['screenshot_url'] = payout.screenshot.url
            payout_entry['has_screenshot'] = True
        else:
            payout_entry['screenshot_url'] = None
            payout_entry['has_screenshot'] = False
        
        recent_payouts.append(payout_entry)
    
    profile['recent_payouts'] = recent_payouts
    
    return profile
