"""
Subscription tier utility functions.
Centralized tier checking and feature access control.
"""
from subscriptions.models import UserSubscription


def get_user_tier(user):
    """
    Get user's current subscription tier.
    Returns 'standard', 'premium', 'elite', or None if no active subscription.
    """
    if not user or not user.is_authenticated:
        return None
    
    active_sub = UserSubscription.objects.filter(
        user=user,
        status__in=['active', 'trialing', 'past_due']
    ).select_related('plan').first()
    
    if not active_sub:
        return None
    
    return active_sub.plan.tier


def has_tier_access(user, required_tier):
    """
    Check if user has access to a specific tier or higher.
    
    Args:
        user: User object
        required_tier: 'standard', 'premium', or 'elite'
    
    Returns:
        bool: True if user has required tier or higher
    """
    TIER_LEVELS = {
        'standard': 1,
        'premium': 2,
        'elite': 3,
    }
    
    user_tier = get_user_tier(user)
    if not user_tier:
        return False
    
    user_level = TIER_LEVELS.get(user_tier, 0)
    required_level = TIER_LEVELS.get(required_tier, 999)
    
    return user_level >= required_level


def get_tier_features(tier):
    """
    Get feature set for a specific tier.
    
    Returns dict with feature flags and limits.
    """
    if tier == 'standard':
        return {
            # Data Access
            'total_verified_payouts': True,
            'total_payout_volume': True,
            'unique_traders_count': True,
            'seven_day_volume': True,
            'thirty_day_volume': True,
            'basic_timeline_chart': True,
            'submission_count_per_day': True,
            'basic_health_score': True,
            
            # Advanced Data (Premium+)
            'hourly_distribution': False,
            'trader_categorization': False,
            'consistency_scores': False,
            'market_trend_analysis': False,
            'predictive_insights': False,
            'comparative_benchmarks': False,
            
            # Elite Features
            'advanced_fraud_detection': False,
            'api_access': False,
            'priority_support': False,
            
            # Access
            'payout_submission': True,
            'payout_review': True,
            'eligible_for_rankings': True,
            'public_profile': True,
            'private_dashboard': True,
        }
    
    elif tier == 'premium':
        return {
            # All Standard features
            'total_verified_payouts': True,
            'total_payout_volume': True,
            'unique_traders_count': True,
            'seven_day_volume': True,
            'thirty_day_volume': True,
            'basic_timeline_chart': True,
            'submission_count_per_day': True,
            'basic_health_score': True,
            
            # Premium-specific
            'hourly_distribution': True,
            'trader_categorization': True,
            'consistency_scores': True,
            'market_trend_analysis': True,
            'predictive_insights': True,
            'comparative_benchmarks': True,
            'sixty_day_volume': True,
            'ninety_day_volume': True,
            'advanced_charts': True,
            
            # Elite Features (still locked)
            'advanced_fraud_detection': False,
            'api_access': False,
            'priority_support': False,
            
            # Access
            'payout_submission': True,
            'payout_review': True,
            'eligible_for_rankings': True,
            'public_profile': True,
            'private_dashboard': True,
        }
    
    elif tier == 'elite':
        return {
            # All features unlocked
            'total_verified_payouts': True,
            'total_payout_volume': True,
            'unique_traders_count': True,
            'seven_day_volume': True,
            'thirty_day_volume': True,
            'sixty_day_volume': True,
            'ninety_day_volume': True,
            'basic_timeline_chart': True,
            'advanced_charts': True,
            'submission_count_per_day': True,
            'basic_health_score': True,
            'hourly_distribution': True,
            'trader_categorization': True,
            'consistency_scores': True,
            'market_trend_analysis': True,
            'predictive_insights': True,
            'comparative_benchmarks': True,
            'advanced_fraud_detection': True,
            'api_access': True,
            'priority_support': True,
            'payout_submission': True,
            'payout_review': True,
            'eligible_for_rankings': True,
            'public_profile': True,
            'private_dashboard': True,
        }
    
    # No tier / inactive subscription
    return {
        'payout_submission': False,
        'payout_review': False,
        'eligible_for_rankings': False,
        'public_profile': False,
        'private_dashboard': False,
    }


def filter_analytics_by_tier(data, user_tier):
    """
    Filter analytics data based on user's subscription tier.
    
    Args:
        data: Full analytics dict
        user_tier: 'standard', 'premium', or 'elite'
    
    Returns:
        Filtered data dict with only allowed fields for that tier
    """
    features = get_tier_features(user_tier)
    
    if user_tier == 'standard':
        # Standard tier gets basic data only
        filtered = {
            'server': data.get('server'),
            'payout_insights': {
                'total_verified': data['payout_insights']['total_verified'],
                'average_payout': data['payout_insights']['average_payout'],
                'total_submissions': data['payout_insights']['total_submissions'],
                'weekly_trend': data['payout_insights']['weekly_trend'],  # 7-day
                'daily_trend': data['payout_insights']['daily_trend'][:30],  # 30-day only
            },
            'activity_metrics': {
                'active_traders_7d': data['activity_metrics']['active_traders_7d'],
                'active_traders_30d': data['activity_metrics']['active_traders_30d'],
                'submissions_per_day': data['activity_metrics']['submissions_per_day'],
                'approval_rate': data['activity_metrics']['approval_rate'],
                'pending_submissions': data['activity_metrics']['pending_submissions'],
            },
            'trader_performance': {
                'top_traders_monthly': data['trader_performance']['top_traders_monthly'][:5],
            },
            'health_score': calculate_basic_health_score(data),
        }
        return filtered
    
    elif user_tier == 'premium':
        # Premium tier gets Standard + advanced engagement & momentum data
        filtered = {
            'server': data.get('server'),
            'payout_insights': {
                'total_verified': data['payout_insights']['total_verified'],
                'average_payout': data['payout_insights']['average_payout'],
                'total_submissions': data['payout_insights']['total_submissions'],
                'weekly_trend': data['payout_insights']['weekly_trend'],
                'daily_trend': data['payout_insights']['daily_trend'],
                'monthly_growth': data['payout_insights']['monthly_growth'],  # Premium adds growth %
                'largest_payout': data['payout_insights']['largest_payout'],  # Premium adds this
            },
            'activity_metrics': {
                'active_traders_7d': data['activity_metrics']['active_traders_7d'],
                'active_traders_30d': data['activity_metrics']['active_traders_30d'],
                'submissions_per_day': data['activity_metrics']['submissions_per_day'],
                'approval_rate': data['activity_metrics']['approval_rate'],
                'pending_submissions': data['activity_metrics']['pending_submissions'],
                'peak_submission_hours': data['activity_metrics']['peak_submission_hours'][:3],  # Top 3 hours
            },
            'trader_performance': {
                'top_traders_monthly': data['trader_performance']['top_traders_monthly'][:5],
                'top_traders_alltime': data['trader_performance']['top_traders_alltime'][:5],  # Premium adds all-time
                'most_consistent_traders': data['payout_insights'].get('most_consistent_traders', [])[:5],  # Premium adds consistency
            },
            'engagement_data': calculate_engagement_data(data),  # Premium-specific
            'momentum_intelligence': calculate_momentum_intelligence(data),  # Premium-specific
            'health_score': calculate_premium_health_score(data),  # Upgraded score
        }
        return filtered
    
    elif user_tier == 'elite':
        # Elite tier gets all Standard + Premium + exclusive benchmarking & forecasting
        filtered = {
            'server': data.get('server'),
            'payout_insights': data.get('payout_insights'),  # Full payout data
            'activity_metrics': data.get('activity_metrics'),  # Full activity data
            'trader_performance': {
                'top_traders_monthly': data['trader_performance']['top_traders_monthly'][:15],  # Elite shows top 15
                'top_traders_alltime': data['trader_performance']['top_traders_alltime'][:15],
                'most_consistent_traders': data.get('payout_insights', {}).get('most_consistent_traders', [])[:15],
                'full_breakdown': True,  # Flag indicating complete breakdown available
            },
            'engagement_data': calculate_engagement_data(data),
            'momentum_intelligence': calculate_momentum_intelligence(data),
            'health_score': calculate_premium_health_score(data),
            'benchmark_analytics': calculate_benchmark_analytics(data),  # Elite-exclusive
            'historical_analytics': calculate_historical_analytics(data),  # Elite-exclusive
            'forecast_projections': calculate_forecast_projections(data),  # Elite-exclusive
            'elite_features': {
                'custom_slug_enabled': True,
                'api_access_enabled': True,
                'advanced_fraud_detection': True,
                'priority_support': True,
            }
        }
        return filtered
    
    else:
        # No tier or invalid tier
        return {}


def calculate_basic_health_score(data):
    """
    Calculate basic server health score for Standard tier.
    
    Simple formula based on:
    - Approval rate (40%)
    - Active traders (30%)
    - Submission consistency (30%)
    """
    approval_rate = data['activity_metrics'].get('approval_rate', 0)
    active_7d = data['activity_metrics'].get('active_traders_7d', 0)
    active_30d = data['activity_metrics'].get('active_traders_30d', 1)  # Avoid division by zero
    submissions_per_day = data['activity_metrics'].get('submissions_per_day', 0)
    
    # Approval rate component (0-40 points)
    approval_component = (approval_rate / 100) * 40
    
    # Activity component (0-30 points)
    # Higher percentage of 7-day active vs 30-day active is better
    activity_ratio = (active_7d / active_30d) if active_30d > 0 else 0
    activity_component = min(activity_ratio, 1.0) * 30
    
    # Consistency component (0-30 points)
    # Higher submissions per day is better, cap at 10/day for full points
    consistency_component = min(submissions_per_day / 10, 1.0) * 30
    
    total_score = approval_component + activity_component + consistency_component
    
    return {
        'score': round(total_score, 1),
        'rating': get_health_rating(total_score),
        'components': {
            'approval': round(approval_component, 1),
            'activity': round(activity_component, 1),
            'consistency': round(consistency_component, 1),
        }
    }


def get_health_rating(score):
    """Convert numeric health score to rating."""
    if score >= 90:
        return 'Excellent'
    elif score >= 75:
        return 'Good'
    elif score >= 60:
        return 'Fair'
    elif score >= 40:
        return 'Poor'
    else:
        return 'Critical'


def calculate_engagement_data(data):
    """
    Calculate deeper engagement metrics for Premium tier.
    
    Returns:
    - Top 5 contributing traders
    - Activity distribution (frequent vs occasional vs rare)
    - Trader consistency classification
    """
    trader_performance = data.get('trader_performance', {})
    top_monthly = trader_performance.get('top_traders_monthly', [])
    top_alltime = trader_performance.get('top_traders_alltime', [])
    
    # Top 5 contributors (combine monthly and all-time for relevance)
    top_contributors = top_monthly[:5] if top_monthly else []
    
    # Activity distribution - categorize traders
    # This would ideally come from analyzing all members, but we'll use existing data
    total_traders = data.get('server', {}).get('total_members', 0)
    active_7d = data.get('activity_metrics', {}).get('active_traders_7d', 0)
    active_30d = data.get('activity_metrics', {}).get('active_traders_30d', 0)
    
    # Calculate distribution
    frequent = active_7d  # Active in last 7 days
    occasional = active_30d - active_7d  # Active in 30 days but not 7 days
    rare = total_traders - active_30d  # Not active in 30 days
    
    activity_distribution = {
        'frequent_submitters': frequent,
        'occasional_submitters': max(0, occasional),
        'rare_submitters': max(0, rare),
        'total_traders': total_traders,
        'distribution_percentages': {
            'frequent': round((frequent / total_traders * 100) if total_traders > 0 else 0, 1),
            'occasional': round((occasional / total_traders * 100) if total_traders > 0 else 0, 1),
            'rare': round((rare / total_traders * 100) if total_traders > 0 else 0, 1),
        }
    }
    
    # Trader consistency classification
    consistency_ratio = (active_7d / active_30d) if active_30d > 0 else 0
    
    if consistency_ratio >= 0.7:
        consistency_level = 'High'
        consistency_description = 'Most active traders remain consistently engaged'
    elif consistency_ratio >= 0.4:
        consistency_level = 'Moderate'
        consistency_description = 'Good trader retention with some fluctuation'
    else:
        consistency_level = 'Low'
        consistency_description = 'High trader churn, focus on retention'
    
    return {
        'top_contributors': top_contributors,
        'activity_distribution': activity_distribution,
        'consistency_classification': {
            'level': consistency_level,
            'ratio': round(consistency_ratio, 2),
            'description': consistency_description,
        }
    }


def calculate_momentum_intelligence(data):
    """
    Calculate momentum and activity intelligence for Premium tier.
    
    Returns:
    - Submission spikes (days with high activity)
    - Cooldown periods (days with low activity)
    - 7-day vs 30-day momentum comparison
    - Growth trajectory analysis
    """
    daily_trend = data.get('payout_insights', {}).get('daily_trend', [])
    weekly_trend = data.get('payout_insights', {}).get('weekly_trend', [])
    monthly_growth = data.get('payout_insights', {}).get('monthly_growth', 0)
    
    # Calculate average submission count
    if daily_trend:
        submission_counts = [day.get('count', 0) for day in daily_trend]
        avg_submissions = sum(submission_counts) / len(submission_counts) if submission_counts else 0
        
        # Identify spikes (days > 150% of average)
        spike_threshold = avg_submissions * 1.5
        spikes = [
            {
                'date': day['date'],
                'count': day['count'],
                'volume': day['total'],
                'above_average': round(((day['count'] / avg_submissions) - 1) * 100, 1) if avg_submissions > 0 else 0
            }
            for day in daily_trend if day.get('count', 0) > spike_threshold
        ]
        
        # Identify cooldowns (days < 50% of average)
        cooldown_threshold = avg_submissions * 0.5
        cooldowns = [
            {
                'date': day['date'],
                'count': day['count'],
                'volume': day['total'],
                'below_average': round((1 - (day['count'] / avg_submissions)) * 100, 1) if avg_submissions > 0 else 0
            }
            for day in daily_trend if day.get('count', 0) < cooldown_threshold and avg_submissions > 0
        ]
    else:
        spikes = []
        cooldowns = []
        avg_submissions = 0
    
    # 7-day vs 30-day momentum comparison
    weekly_volume = sum(day.get('total', 0) for day in weekly_trend)
    monthly_volume = sum(day.get('total', 0) for day in daily_trend)
    
    # Calculate 7-day average vs 30-day average
    weekly_avg = weekly_volume / 7 if len(weekly_trend) > 0 else 0
    monthly_avg = monthly_volume / 30 if len(daily_trend) > 0 else 0
    
    momentum_comparison = weekly_avg / monthly_avg if monthly_avg > 0 else 1.0
    
    if momentum_comparison > 1.2:
        momentum_status = 'Accelerating'
        momentum_description = 'Recent activity is significantly higher than monthly average'
    elif momentum_comparison > 0.95:
        momentum_status = 'Stable'
        momentum_description = 'Activity levels are consistent and steady'
    else:
        momentum_status = 'Slowing'
        momentum_description = 'Recent activity is lower than monthly average'
    
    # Growth trajectory
    if monthly_growth > 20:
        trajectory = 'High Growth'
        trajectory_icon = '📈'
    elif monthly_growth > 5:
        trajectory = 'Growing'
        trajectory_icon = '↗️'
    elif monthly_growth > -5:
        trajectory = 'Stable'
        trajectory_icon = '→'
    elif monthly_growth > -20:
        trajectory = 'Declining'
        trajectory_icon = '↘️'
    else:
        trajectory = 'Significant Decline'
        trajectory_icon = '📉'
    
    return {
        'submission_spikes': spikes[:5],  # Top 5 spikes
        'cooldown_periods': cooldowns[:5],  # Top 5 cooldowns
        'momentum_comparison': {
            'ratio': round(momentum_comparison, 2),
            'status': momentum_status,
            'description': momentum_description,
            'weekly_avg_daily': round(weekly_avg, 2),
            'monthly_avg_daily': round(monthly_avg, 2),
        },
        'growth_trajectory': {
            'status': trajectory,
            'icon': trajectory_icon,
            'monthly_growth_percent': round(monthly_growth, 1),
            'description': f"Your community is {trajectory.lower()}"
        }
    }


def calculate_premium_health_score(data):
    """
    Calculate upgraded health score for Premium tier.
    
    Components:
    - Approval rate (25%)
    - Submission momentum (25%)
    - Trader participation (25%)
    - Growth stability (25%)
    """
    activity = data.get('activity_metrics', {})
    payout_insights = data.get('payout_insights', {})
    
    approval_rate = activity.get('approval_rate', 0)
    submissions_per_day = activity.get('submissions_per_day', 0)
    active_7d = activity.get('active_traders_7d', 0)
    active_30d = activity.get('active_traders_30d', 1)  # Avoid division by zero
    monthly_growth = payout_insights.get('monthly_growth', 0)
    
    # 1. Approval rate component (25 points)
    approval_component = (approval_rate / 100) * 25
    
    # 2. Submission momentum component (25 points)
    # Higher submissions per day is better, cap at 20/day for full points
    momentum_component = min(submissions_per_day / 20, 1.0) * 25
    
    # 3. Trader participation component (25 points)
    # Higher percentage of 7-day active vs 30-day active is better
    participation_ratio = (active_7d / active_30d) if active_30d > 0 else 0
    participation_component = min(participation_ratio, 1.0) * 25
    
    # 4. Growth stability component (25 points)
    # Positive growth is good, but extreme volatility is concerning
    # Sweet spot: 5-30% monthly growth
    if monthly_growth < 0:
        growth_component = max(0, 25 + (monthly_growth * 0.5))  # Penalty for decline
    elif monthly_growth <= 30:
        growth_component = min(25, 15 + (monthly_growth * 0.33))  # Reward steady growth
    else:
        growth_component = max(15, 25 - ((monthly_growth - 30) * 0.2))  # Slight penalty for extreme growth (may be unsustainable)
    
    total_score = approval_component + momentum_component + participation_component + growth_component
    
    # Determine overall status
    if total_score >= 85:
        status = 'Thriving'
        status_description = 'Your community is highly engaged and growing healthily'
    elif total_score >= 70:
        status = 'Growing'
        status_description = 'Your community is growing with good engagement'
    elif total_score >= 55:
        status = 'Stable'
        status_description = 'Your community maintains steady activity levels'
    elif total_score >= 40:
        status = 'Slowing'
        status_description = 'Your community shows signs of decreased engagement'
    else:
        status = 'At Risk'
        status_description = 'Your community needs immediate attention to improve engagement'
    
    return {
        'score': round(total_score, 1),
        'rating': get_health_rating(total_score),
        'status': status,
        'status_description': status_description,
        'components': {
            'approval': round(approval_component, 1),
            'momentum': round(momentum_component, 1),
            'participation': round(participation_component, 1),
            'growth': round(growth_component, 1),
        },
        'recommendations': generate_health_recommendations(
            approval_component, momentum_component, participation_component, growth_component
        )
    }


def generate_health_recommendations(approval, momentum, participation, growth):
    """Generate actionable recommendations based on health score components."""
    recommendations = []
    
    if approval < 15:
        recommendations.append({
            'area': 'Approval Rate',
            'priority': 'High',
            'action': 'Review submission quality guidelines with traders'
        })
    
    if momentum < 15:
        recommendations.append({
            'area': 'Submission Activity',
            'priority': 'High',
            'action': 'Encourage more frequent payout submissions from active traders'
        })
    
    if participation < 15:
        recommendations.append({
            'area': 'Trader Retention',
            'priority': 'Critical',
            'action': 'Focus on re-engaging inactive traders'
        })
    
    if growth < 15:
        recommendations.append({
            'area': 'Community Growth',
            'priority': 'Medium',
            'action': 'Consider promotional activities to attract new traders'
        })
    
    if not recommendations:
        recommendations.append({
            'area': 'Overall',
            'priority': 'Low',
            'action': 'Maintain current engagement strategies'
        })
    
    return recommendations


def calculate_benchmark_analytics(data):
    """
    Calculate PRIVATE benchmark comparisons for Elite tier.
    
    Shows server's relative position against Aurevia ecosystem averages.
    NOT competitive, NOT public, purely informational.
    
    Returns:
    - Volume vs average
    - Growth vs average
    - Trader activity vs average
    - Payout frequency vs average
    - Stability vs average
    """
    from payouts.models import PayoutSubmission
    from servers.models import Server
    from django.db.models import Count, Sum, Avg, Q
    from datetime import timedelta
    from django.utils import timezone
    
    # Get this server's metrics
    server = data.get('server', {})
    server_id = server.get('id')
    
    payout_insights = data.get('payout_insights', {})
    activity_metrics = data.get('activity_metrics', {})
    
    # Calculate ecosystem-wide averages (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Average payout volume per server
    avg_volume = PayoutSubmission.objects.filter(
        status='approved',
        created_at__gte=thirty_days_ago
    ).values('server').annotate(
        total=Sum('payout_amount')
    ).aggregate(avg=Avg('total'))['avg'] or 0
    
    # Average trader count per server
    avg_traders = Server.objects.annotate(
        member_count=Count('members')
    ).aggregate(avg=Avg('member_count'))['avg'] or 0
    
    # Average submissions per server
    avg_submissions = PayoutSubmission.objects.filter(
        created_at__gte=thirty_days_ago
    ).values('server').annotate(
        count=Count('id')
    ).aggregate(avg=Avg('count'))['avg'] or 0
    
    # Calculate this server's metrics
    server_volume = payout_insights.get('total_verified', 0)
    server_traders = activity_metrics.get('active_traders_30d', 0)
    server_submissions = payout_insights.get('total_submissions', 0)
    monthly_growth = payout_insights.get('monthly_growth', 0)
    
    # Calculate percentile rankings (simplified)
    # In production, you'd query actual rankings from database
    
    def calculate_percentile(value, average):
        """Simple percentile calculation based on deviation from average."""
        if average == 0:
            return 50.0
        ratio = value / average
        if ratio >= 2.0:
            return 95.0
        elif ratio >= 1.5:
            return 80.0
        elif ratio >= 1.2:
            return 70.0
        elif ratio >= 1.0:
            return 60.0
        elif ratio >= 0.8:
            return 40.0
        elif ratio >= 0.5:
            return 25.0
        else:
            return 10.0
    
    volume_percentile = calculate_percentile(server_volume, avg_volume)
    trader_percentile = calculate_percentile(server_traders, avg_traders)
    submission_percentile = calculate_percentile(server_submissions, avg_submissions)
    
    # Growth comparison (relative to ecosystem)
    # Assume average monthly growth is around 10%
    ecosystem_avg_growth = 10.0
    growth_comparison = monthly_growth - ecosystem_avg_growth
    
    def get_position_description(percentile):
        """Convert percentile to friendly description."""
        if percentile >= 90:
            return "Top 10%"
        elif percentile >= 75:
            return "Top 25%"
        elif percentile >= 50:
            return "Above Average"
        elif percentile >= 25:
            return "Below Average"
        else:
            return "Bottom 25%"
    
    return {
        'volume_benchmark': {
            'your_volume': round(server_volume, 2),
            'ecosystem_average': round(avg_volume, 2),
            'percentile': round(volume_percentile, 1),
            'position': get_position_description(volume_percentile),
            'comparison': f"{'Above' if server_volume >= avg_volume else 'Below'} average by {abs(round((server_volume / avg_volume - 1) * 100, 1)) if avg_volume > 0 else 0}%"
        },
        'trader_activity_benchmark': {
            'your_active_traders': server_traders,
            'ecosystem_average': round(avg_traders, 1),
            'percentile': round(trader_percentile, 1),
            'position': get_position_description(trader_percentile),
            'comparison': f"{'Above' if server_traders >= avg_traders else 'Below'} average by {abs(round((server_traders / avg_traders - 1) * 100, 1)) if avg_traders > 0 else 0}%"
        },
        'submission_frequency_benchmark': {
            'your_submissions': server_submissions,
            'ecosystem_average': round(avg_submissions, 1),
            'percentile': round(submission_percentile, 1),
            'position': get_position_description(submission_percentile),
            'comparison': f"{'Above' if server_submissions >= avg_submissions else 'Below'} average by {abs(round((server_submissions / avg_submissions - 1) * 100, 1)) if avg_submissions > 0 else 0}%"
        },
        'growth_benchmark': {
            'your_growth': round(monthly_growth, 1),
            'ecosystem_average': ecosystem_avg_growth,
            'difference': round(growth_comparison, 1),
            'status': 'Outpacing' if growth_comparison > 5 else ('Matching' if growth_comparison > -5 else 'Lagging'),
            'description': f"Your growth is {abs(round(growth_comparison, 1))}% {'faster' if growth_comparison > 0 else 'slower'} than average"
        },
        'overall_ranking': {
            'composite_score': round((volume_percentile + trader_percentile + submission_percentile) / 3, 1),
            'tier_placement': get_position_description((volume_percentile + trader_percentile + submission_percentile) / 3),
            'summary': 'You are performing strongly across most metrics' if volume_percentile > 60 else 'Focus on improving key engagement metrics'
        },
        'privacy_note': 'These comparisons are private and visible only to you. Other servers cannot see your data.'
    }


def calculate_historical_analytics(data):
    """
    Calculate in-depth historical analytics for Elite tier.
    
    Returns:
    - Month-by-month payout history
    - Trader activity history
    - Long-term retention curve
    - Lifetime payout data
    - Lifetime trajectory chart
    """
    from payouts.models import PayoutSubmission
    from django.db.models import Count, Sum, Avg
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models.functions import TruncMonth
    
    server = data.get('server', {})
    server_id = server.get('id')
    
    if not server_id:
        return {}
    
    # Month-by-month payout history (last 12 months)
    one_year_ago = timezone.now() - timedelta(days=365)
    
    monthly_payouts = PayoutSubmission.objects.filter(
        server_id=server_id,
        status='approved',
        created_at__gte=one_year_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total_volume=Sum('payout_amount'),
        total_count=Count('id'),
        avg_payout=Avg('payout_amount'),
        unique_traders=Count('user', distinct=True)
    ).order_by('month')
    
    monthly_history = [
        {
            'month': entry['month'].strftime('%Y-%m'),
            'volume': round(float(entry['total_volume']), 2),
            'count': entry['total_count'],
            'average': round(float(entry['avg_payout']), 2),
            'unique_traders': entry['unique_traders']
        }
        for entry in monthly_payouts
    ]
    
    # Lifetime totals
    lifetime_stats = PayoutSubmission.objects.filter(
        server_id=server_id,
        status='approved'
    ).aggregate(
        total_volume=Sum('payout_amount'),
        total_count=Count('id'),
        avg_payout=Avg('payout_amount'),
        unique_traders=Count('user', distinct=True)
    )
    
    # Calculate retention curve (cohort analysis simplified)
    # Track how many traders remain active over time
    retention_data = []
    for months_ago in [1, 3, 6, 9, 12]:
        date_threshold = timezone.now() - timedelta(days=months_ago * 30)
        active_since = PayoutSubmission.objects.filter(
            server_id=server_id,
            created_at__lte=date_threshold
        ).values('user').distinct().count()
        
        still_active = PayoutSubmission.objects.filter(
            server_id=server_id,
            created_at__lte=date_threshold,
            user__in=PayoutSubmission.objects.filter(
                server_id=server_id,
                created_at__gte=date_threshold
            ).values('user')
        ).values('user').distinct().count()
        
        retention_rate = (still_active / active_since * 100) if active_since > 0 else 0
        
        retention_data.append({
            'period': f'{months_ago} months',
            'initial_traders': active_since,
            'retained_traders': still_active,
            'retention_rate': round(retention_rate, 1)
        })
    
    # Lifetime trajectory (quarterly breakdown)
    quarters_back = 8  # 2 years
    quarterly_trend = []
    
    for q in range(quarters_back):
        end_date = timezone.now() - timedelta(days=q * 90)
        start_date = end_date - timedelta(days=90)
        
        quarter_data = PayoutSubmission.objects.filter(
            server_id=server_id,
            status='approved',
            created_at__gte=start_date,
            created_at__lt=end_date
        ).aggregate(
            volume=Sum('payout_amount'),
            count=Count('id')
        )
        
        if quarter_data['volume']:
            quarterly_trend.insert(0, {
                'quarter': f'Q{((end_date.month - 1) // 3) + 1} {end_date.year}',
                'volume': round(float(quarter_data['volume']), 2),
                'submissions': quarter_data['count']
            })
    
    return {
        'monthly_history': monthly_history,
        'lifetime_totals': {
            'total_volume': round(float(lifetime_stats['total_volume'] or 0), 2),
            'total_payouts': lifetime_stats['total_count'],
            'average_payout': round(float(lifetime_stats['avg_payout'] or 0), 2),
            'unique_traders': lifetime_stats['unique_traders'],
            'first_payout_date': PayoutSubmission.objects.filter(
                server_id=server_id,
                status='approved'
            ).order_by('created_at').values_list('created_at', flat=True).first()
        },
        'retention_curve': retention_data,
        'quarterly_trajectory': quarterly_trend,
        'insights': {
            'best_month': max(monthly_history, key=lambda x: x['volume'])['month'] if monthly_history else 'N/A',
            'growth_trend': 'Upward' if len(monthly_history) >= 2 and monthly_history[-1]['volume'] > monthly_history[0]['volume'] else 'Stable',
            'consistency_rating': 'High' if len(monthly_history) >= 6 and all(m['count'] > 0 for m in monthly_history[-6:]) else 'Moderate'
        }
    }


def calculate_forecast_projections(data):
    """
    Calculate simplified forecast and projections for Elite tier.
    
    Uses basic math and trend analysis (NO AI).
    
    Returns:
    - Projected 30-day payout totals
    - Projected growth or slowdown
    - Momentum trend line
    - Estimated rank movement
    """
    payout_insights = data.get('payout_insights', {})
    activity_metrics = data.get('activity_metrics', {})
    
    # Get historical data
    daily_trend = payout_insights.get('daily_trend', [])
    monthly_growth = payout_insights.get('monthly_growth', 0)
    
    if not daily_trend or len(daily_trend) < 7:
        return {
            'insufficient_data': True,
            'message': 'Need at least 7 days of data for projections'
        }
    
    # Calculate recent averages
    last_7_days = daily_trend[-7:]
    last_30_days = daily_trend[-30:] if len(daily_trend) >= 30 else daily_trend
    
    avg_7day_volume = sum(day.get('total', 0) for day in last_7_days) / len(last_7_days)
    avg_30day_volume = sum(day.get('total', 0) for day in last_30_days) / len(last_30_days)
    
    avg_7day_count = sum(day.get('count', 0) for day in last_7_days) / len(last_7_days)
    avg_30day_count = sum(day.get('count', 0) for day in last_30_days) / len(last_30_days)
    
    # Calculate momentum factor (how recent activity compares to historical)
    momentum_factor = avg_7day_volume / avg_30day_volume if avg_30day_volume > 0 else 1.0
    
    # Project next 30 days using weighted average (recent activity weighted higher)
    weighted_daily_avg = (avg_7day_volume * 0.7) + (avg_30day_volume * 0.3)
    projected_30day_volume = weighted_daily_avg * 30
    
    weighted_daily_count = (avg_7day_count * 0.7) + (avg_30day_count * 0.3)
    projected_30day_submissions = int(weighted_daily_count * 30)
    
    # Calculate trend direction
    if momentum_factor > 1.15:
        trend_direction = 'Accelerating'
        trend_description = 'Strong upward momentum detected'
    elif momentum_factor > 1.05:
        trend_direction = 'Growing'
        trend_description = 'Modest growth trend continuing'
    elif momentum_factor > 0.95:
        trend_direction = 'Stable'
        trend_description = 'Consistent performance maintained'
    elif momentum_factor > 0.85:
        trend_direction = 'Slowing'
        trend_description = 'Slight decline in recent activity'
    else:
        trend_direction = 'Declining'
        trend_description = 'Significant slowdown detected'
    
    # Calculate confidence level (based on data consistency)
    volume_variance = sum((day.get('total', 0) - avg_30day_volume) ** 2 for day in last_30_days) / len(last_30_days)
    volume_std_dev = volume_variance ** 0.5
    coefficient_of_variation = (volume_std_dev / avg_30day_volume) if avg_30day_volume > 0 else 1.0
    
    if coefficient_of_variation < 0.3:
        confidence = 'High'
        confidence_pct = 85
    elif coefficient_of_variation < 0.6:
        confidence = 'Moderate'
        confidence_pct = 70
    else:
        confidence = 'Low'
        confidence_pct = 50
    
    # Estimated rank movement (simplified)
    # Positive growth suggests potential rank increase
    if monthly_growth > 15:
        rank_movement = 'Likely to rise'
        rank_change_estimate = '+2-5 positions'
    elif monthly_growth > 5:
        rank_movement = 'May improve'
        rank_change_estimate = '+1-2 positions'
    elif monthly_growth > -5:
        rank_movement = 'Stable position'
        rank_change_estimate = 'No significant change'
    elif monthly_growth > -15:
        rank_movement = 'May decline'
        rank_change_estimate = '-1-2 positions'
    else:
        rank_movement = 'Likely to fall'
        rank_change_estimate = '-2-5 positions'
    
    return {
        'next_30_days': {
            'projected_volume': round(projected_30day_volume, 2),
            'projected_submissions': projected_30day_submissions,
            'projected_avg_daily': round(weighted_daily_avg, 2),
            'confidence_level': confidence,
            'confidence_percentage': confidence_pct
        },
        'growth_projection': {
            'trend_direction': trend_direction,
            'momentum_factor': round(momentum_factor, 2),
            'description': trend_description,
            'expected_monthly_growth': round(monthly_growth * momentum_factor, 1)
        },
        'momentum_trend_line': {
            'current_momentum': round(momentum_factor, 2),
            'short_term_avg': round(avg_7day_volume, 2),
            'long_term_avg': round(avg_30day_volume, 2),
            'trend_slope': 'Positive' if momentum_factor > 1.05 else ('Neutral' if momentum_factor > 0.95 else 'Negative')
        },
        'rank_estimation': {
            'movement_prediction': rank_movement,
            'estimated_change': rank_change_estimate,
            'based_on': f'{round(monthly_growth, 1)}% monthly growth'
        },
        'methodology_note': 'Projections based on weighted averages of recent activity. Past performance does not guarantee future results.'
    }
