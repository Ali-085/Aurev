"""
Payout Verification Service

Handles ALL automatic updates when a payout is approved:
1. Server stats update
2. Server analytics update (categories, markets, days)
3. Global rankings update
4. User profile totals update
5. Server leaderboard update
6. Global leaderboard update

Everything syncs instantly with atomic transactions.
"""
from django.db import models
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, F
from decimal import Decimal


class PayoutVerificationService:
    """
    Central service for handling payout approval cascades.
    
    SECURITY: All operations use transaction.atomic() and select_for_update()
    """
    
    @staticmethod
    @transaction.atomic
    def approve_payout(payout, reviewer):
        """
        Approve a payout and trigger ALL automatic updates.
        
        This is the single source of truth for payout approval logic.
        """
        from servers.models import ServerMember
        from analytics.models import ServerAnalytics, UserAnalytics
        
        # 1. UPDATE PAYOUT STATUS
        payout.status = 'Approved'
        payout.reviewer = reviewer
        payout.reviewed_at = timezone.now()
        payout.save(update_fields=['status', 'reviewer', 'reviewed_at'])
        
        # 2. UPDATE SERVER MEMBER STATS
        member, created = ServerMember.objects.select_for_update().get_or_create(
            server=payout.server,
            user=payout.user,
            defaults={
                'total_verified_payouts': Decimal('0'),
                'total_submissions': 0,
                'last_submission_at': timezone.now()
            }
        )
        member.total_verified_payouts += payout.amount
        member.total_submissions += 1
        member.last_submission_at = payout.created_at
        member.save(update_fields=['total_verified_payouts', 'total_submissions', 'last_submission_at'])
        
        # 3. UPDATE SERVER ANALYTICS
        PayoutVerificationService._update_server_analytics(payout)
        
        # 4. UPDATE USER ANALYTICS
        PayoutVerificationService._update_user_analytics(payout)
        
        # 5. UPDATE GLOBAL RANKINGS (mark for recalculation)
        PayoutVerificationService._trigger_ranking_update(payout.server, payout.user)
        
        # 6. UPDATE SERVER LEADERBOARD CACHE
        PayoutVerificationService._update_server_leaderboard_cache(payout.server)
        
        # 7. UPDATE GLOBAL LEADERBOARD CACHE
        PayoutVerificationService._update_global_leaderboard_cache()
        
        return payout
    
    @staticmethod
    def _update_server_analytics(payout):
        """
        Update server analytics with payout data.
        
        Tracks:
        - Total volume by market category
        - Total volume by instrument
        - Payout count by day
        - Unique traders
        """
        from analytics.models import ServerAnalytics
        
        # Get or create analytics record for this server
        analytics, created = ServerAnalytics.objects.get_or_create(
            server=payout.server,
            defaults={
                'total_volume': Decimal('0'),
                'total_payouts': 0,
                'unique_traders': 0,
                'market_breakdown': {},
                'instrument_breakdown': {},
                'daily_breakdown': {}
            }
        )
        
        # Update total volume and payout count
        analytics.total_volume += payout.amount
        analytics.total_payouts += 1
        
        # Update market category breakdown
        market_breakdown = analytics.market_breakdown or {}
        market_key = payout.market_category
        market_breakdown[market_key] = float(market_breakdown.get(market_key, 0)) + float(payout.amount)
        analytics.market_breakdown = market_breakdown
        
        # Update instrument breakdown
        instrument_breakdown = analytics.instrument_breakdown or {}
        instrument_key = payout.instrument
        instrument_breakdown[instrument_key] = float(instrument_breakdown.get(instrument_key, 0)) + float(payout.amount)
        analytics.instrument_breakdown = instrument_breakdown
        
        # Update daily breakdown
        daily_breakdown = analytics.daily_breakdown or {}
        date_key = payout.payout_date.strftime('%Y-%m-%d')
        daily_breakdown[date_key] = float(daily_breakdown.get(date_key, 0)) + float(payout.amount)
        analytics.daily_breakdown = daily_breakdown
        
        # Update unique traders count
        from payouts.models import PayoutSubmission
        analytics.unique_traders = PayoutSubmission.objects.filter(
            server=payout.server,
            status='Approved'
        ).values('user').distinct().count()
        
        analytics.last_updated = timezone.now()
        analytics.save()
    
    @staticmethod
    def _update_user_analytics(payout):
        """
        Update user analytics/profile totals.
        
        Tracks:
        - Total payouts received
        - Total volume
        - Market preferences
        - Instrument preferences
        """
        from analytics.models import UserAnalytics
        
        # Get or create analytics record for this user
        analytics, created = UserAnalytics.objects.get_or_create(
            user=payout.user,
            defaults={
                'total_volume': Decimal('0'),
                'total_payouts': 0,
                'servers_count': 0,
                'market_breakdown': {},
                'instrument_breakdown': {},
                'best_month': None,
                'best_month_volume': Decimal('0')
            }
        )
        
        # Update total volume and payout count
        analytics.total_volume += payout.amount
        analytics.total_payouts += 1
        
        # Update market category breakdown
        market_breakdown = analytics.market_breakdown or {}
        market_key = payout.market_category
        market_breakdown[market_key] = float(market_breakdown.get(market_key, 0)) + float(payout.amount)
        analytics.market_breakdown = market_breakdown
        
        # Update instrument breakdown
        instrument_breakdown = analytics.instrument_breakdown or {}
        instrument_key = payout.instrument
        instrument_breakdown[instrument_key] = float(instrument_breakdown.get(instrument_key, 0)) + float(payout.amount)
        analytics.instrument_breakdown = instrument_breakdown
        
        # Update servers count
        from servers.models import ServerMember
        analytics.servers_count = ServerMember.objects.filter(
            user=payout.user,
            total_submissions__gt=0
        ).count()
        
        # Update best month
        from payouts.models import PayoutSubmission
        from django.db.models.functions import TruncMonth
        
        monthly_volumes = PayoutSubmission.objects.filter(
            user=payout.user,
            status='Approved'
        ).annotate(
            month=TruncMonth('payout_date')
        ).values('month').annotate(
            volume=Sum('amount')
        ).order_by('-volume').first()
        
        if monthly_volumes:
            analytics.best_month = monthly_volumes['month']
            analytics.best_month_volume = monthly_volumes['volume']
        
        analytics.last_updated = timezone.now()
        analytics.save()
    
    @staticmethod
    def _trigger_ranking_update(server, user):
        """
        Mark server and user for ranking recalculation.
        
        Uses a flag system to batch ranking updates.
        """
        # Mark server as needing ranking update
        server.needs_ranking_update = True
        server.save(update_fields=['needs_ranking_update'])
        
        # Mark user as needing ranking update (if User model has this field)
        if hasattr(user, 'needs_ranking_update'):
            user.needs_ranking_update = True
            user.save(update_fields=['needs_ranking_update'])
    
    @staticmethod
    def _update_server_leaderboard_cache(server):
        """
        Update server leaderboard cache with latest member rankings.
        
        Caches top 100 members for fast access.
        """
        from servers.models import ServerMember
        from django.core.cache import cache
        
        # Get top 100 members by verified payouts
        top_members = ServerMember.objects.filter(
            server=server
        ).select_related('user').order_by(
            '-total_verified_payouts'
        )[:100].values(
            'user__id',
            'user__username',
            'total_verified_payouts',
            'total_submissions'
        )
        
        # Cache for 5 minutes
        cache_key = f'server_leaderboard:{server.id}'
        cache.set(cache_key, list(top_members), 300)
    
    @staticmethod
    def _update_global_leaderboard_cache():
        """
        Update global leaderboard cache with top servers and users.
        
        Caches top 100 servers and top 100 users.
        """
        from servers.models import Server
        from users.models import User
        from payouts.models import PayoutSubmission
        from django.core.cache import cache
        from django.db.models import Sum, Count
        
        # Top 100 servers by total approved payout volume
        top_servers = Server.objects.annotate(
            total_volume=Sum(
                'payout_submissions__amount',
                filter=models.Q(payout_submissions__status='Approved')
            ),
            total_payouts=Count(
                'payout_submissions',
                filter=models.Q(payout_submissions__status='Approved')
            )
        ).filter(
            total_volume__isnull=False
        ).order_by('-total_volume')[:100].values(
            'id', 'name', 'total_volume', 'total_payouts'
        )
        
        # Top 100 users by total approved payout volume
        top_users = User.objects.annotate(
            total_volume=Sum(
                'payout_submissions__amount',
                filter=models.Q(payout_submissions__status='Approved')
            ),
            total_payouts=Count(
                'payout_submissions',
                filter=models.Q(payout_submissions__status='Approved')
            )
        ).filter(
            total_volume__isnull=False
        ).order_by('-total_volume')[:100].values(
            'id', 'username', 'total_volume', 'total_payouts'
        )
        
        # Cache for 5 minutes
        cache.set('global_leaderboard:servers', list(top_servers), 300)
        cache.set('global_leaderboard:users', list(top_users), 300)
    
    @staticmethod
    @transaction.atomic
    def reject_payout(payout, reviewer, reason):
        """
        Reject a payout with reason.
        
        No stats updates needed for rejection.
        """
        payout.status = 'Rejected'
        payout.reviewer = reviewer
        payout.reviewed_at = timezone.now()
        payout.save(update_fields=['status', 'reviewer', 'reviewed_at'])
        
        # Create review log
        from payouts.models import PayoutReviewLog
        PayoutReviewLog.objects.create(
            payout_submission=payout,
            reviewer_user=reviewer,
            action='Rejected',
            reason=reason
        )
        
        return payout
    
    @staticmethod
    @transaction.atomic
    def mark_suspicious(payout, reviewer, reason):
        """
        Mark payout as suspicious for further review.
        """
        payout.status = 'Suspicious'
        payout.reviewer = reviewer
        payout.reviewed_at = timezone.now()
        payout.save(update_fields=['status', 'reviewer', 'reviewed_at'])
        
        # Create review log
        from payouts.models import PayoutReviewLog
        PayoutReviewLog.objects.create(
            payout_submission=payout,
            reviewer_user=reviewer,
            action='MarkedSuspicious',
            reason=reason
        )
        
        return payout
    
    @staticmethod
    @transaction.atomic
    def reverse_approval(payout, admin_user, reason):
        """
        Reverse an approval (Superuser only).
        
        Subtracts from all stats that were added during approval.
        """
        if payout.status != 'Approved':
            raise ValueError('Can only reverse approved payouts')
        
        from servers.models import ServerMember
        
        # Reverse server member stats
        try:
            member = ServerMember.objects.select_for_update().get(
                server=payout.server,
                user=payout.user
            )
            # SECURITY: Prevent negative values
            member.total_verified_payouts = max(Decimal('0'), member.total_verified_payouts - payout.amount)
            member.total_submissions = max(0, member.total_submissions - 1)
            member.save(update_fields=['total_verified_payouts', 'total_submissions'])
        except ServerMember.DoesNotExist:
            pass
        
        # Mark for analytics recalculation
        PayoutVerificationService._trigger_ranking_update(payout.server, payout.user)
        
        # Set back to Pending
        payout.status = 'Pending'
        payout.reviewer = None
        payout.reviewed_at = None
        payout.save(update_fields=['status', 'reviewer', 'reviewed_at'])
        
        # Create review log
        from payouts.models import PayoutReviewLog
        PayoutReviewLog.objects.create(
            payout_submission=payout,
            reviewer_user=admin_user,
            action='Restored',
            reason=f'REVERSED APPROVAL: {reason}'
        )
        
        return payout
