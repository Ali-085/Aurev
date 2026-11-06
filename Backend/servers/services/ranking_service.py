import math
from django.db.models import Sum, Count, Q, F, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from servers.models import Server
from analytics.models import ServerRanking
from payouts.models import PayoutSubmission

class RankingService:
    CACHE_KEY = 'global_server_rankings_v1'
    CACHE_TIMEOUT = 3600 * 2  # 2 hours

    @staticmethod
    def get_rankings(refresh=False):
        """
        Get server rankings, either from cache or by computing them.
        """
        if not refresh:
            cached = cache.get(RankingService.CACHE_KEY)
            if cached:
                return cached
        
        return RankingService.compute_and_cache_rankings()

    @staticmethod
    def compute_and_cache_rankings():
        """
        Compute rankings for ALL verified servers and cache the result.
        """
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Time windows for growth/trend
        sixty_days_ago = now - timedelta(days=60)
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)

        # 1. Fetch base data with annotations
        servers = Server.objects.filter(is_verified=True, suspended=False).annotate(
            total_verified_payouts=Sum('payout_submissions__amount', filter=Q(payout_submissions__status='Approved')),
            total_submissions=Count('payout_submissions'),
            verified_count=Count('payout_submissions', filter=Q(payout_submissions__status='Approved')),
            active_members=Count('payout_submissions__user', filter=Q(payout_submissions__created_at__gte=thirty_days_ago, payout_submissions__status='Approved'), distinct=True),
            suspicious_count=Count('payout_submissions', filter=Q(payout_submissions__status='Suspicious')),
            # Removed member_count from here to avoid Cartesian product with payout_submissions Sum
            
            # Growth Metrics (30d)
            volume_30d=Sum('payout_submissions__amount', filter=Q(payout_submissions__status='Approved', payout_submissions__created_at__gte=thirty_days_ago)),
            volume_prev_30d=Sum('payout_submissions__amount', filter=Q(payout_submissions__status='Approved', payout_submissions__created_at__range=(sixty_days_ago, thirty_days_ago))),
            
            # Trend Metrics (7d)
            volume_7d=Sum('payout_submissions__amount', filter=Q(payout_submissions__status='Approved', payout_submissions__created_at__gte=seven_days_ago)),
            volume_prev_7d=Sum('payout_submissions__amount', filter=Q(payout_submissions__status='Approved', payout_submissions__created_at__range=(fourteen_days_ago, seven_days_ago))),
        )

        ranking_data = []
        
        # 1.5 Fetch previous ranks for change calculation
        previous_ranks = {
            sr.server_id: sr.global_rank 
            for sr in ServerRanking.objects.filter(server__in=servers)
        }

        # 1.6 Fetch member counts separately to avoid join duplication
        # This fixes the issue where Sum('payout_submissions__amount') was being multiplied by member count
        member_counts = {
            s['id']: s['cnt']
            for s in Server.objects.filter(id__in=[s.id for s in servers])
            .annotate(cnt=Count('members'))
            .values('id', 'cnt')
        }
        
        # 2. Calculate Raw Scores
        for server in servers:
            # Safe defaults
            volume = float(server.total_verified_payouts or 0)
            submissions = server.verified_count or 0 # Use VERIFIED ONLY for scoring
            verified = server.verified_count or 0
            active_traders = server.active_members or 0
            # Fallback for member count if not explicitly tracked
            # Retrieve from separate query dict
            real_member_count = member_counts.get(server.id, 0)
            members = max(real_member_count, 1, active_traders, 1)

            # Performance: Log-scaled volume
            raw_performance = math.log10(volume + 1) if volume > 0 else 0

            # Growth: Submissions per member
            raw_growth = submissions / members

            # Engagement: Activity & Approval
            freq_score = (submissions / members) * 2
            consistency = 25 if submissions > 10 else (submissions * 2.5)
            raw_engagement = (active_traders * 0.5) + freq_score + consistency

            # Diversity: Scale (simplified from frontend as we might lack market breakdown here efficiently)
            # We can use active_traders as a proxy for diversity/size
            raw_diversity = (active_traders * 0.5) + 60 # Base score

            # Quality: Average Verified payout amount (High value = High quality)
            # User requested to avoid suspicious/rejected rates.
            raw_quality = (volume / verified) if verified > 0 else 0

            ranking_data.append({
                'server': server,
                'raw': {
                    'performance': raw_performance,
                    'growth': raw_growth,
                    'engagement': raw_engagement,
                    'diversity': raw_diversity,
                    'quality': raw_quality
                }
            })

        if not ranking_data:
            return []

        # 3. Find Max Values for Normalization
        max_vals = {
            'performance': max((d['raw']['performance'] for d in ranking_data), default=1),
            'growth': max((d['raw']['growth'] for d in ranking_data), default=1),
            'engagement': max((d['raw']['engagement'] for d in ranking_data), default=1),
            'diversity': max((d['raw']['diversity'] for d in ranking_data), default=1),
            'quality': max((d['raw']['quality'] for d in ranking_data), default=1),
        }

        # Prevent division by zero
        for k in max_vals:
            if max_vals[k] == 0: max_vals[k] = 1

        # 4. Normalize & Weight
        # Weights: 20% each for 5 metrics
        WEIGHT = 0.20
        
        final_rankings = []
        
        for item in ranking_data:
            try:
                scores = {}
                total_score = 0
                
                for key in ['performance', 'growth', 'engagement', 'diversity', 'quality']:
                    normalized = (item['raw'][key] / max_vals[key]) * 100
                    scores[key] = min(100, max(0, normalized)) # Clamp 0-100
                    total_score += scores[key] * WEIGHT
                
                item['scores'] = scores
                item['total_score'] = total_score
                final_rankings.append(item)
            except Exception as e:
                print(f"Error scoring server {item['server'].id}: {e}")
                continue

        # 5. Sort by Total Score
        final_rankings.sort(key=lambda x: x['total_score'], reverse=True)

        # 6. Update Database & Prepare Cache List
        ranking_objects = []
        cached_list = []

        for rank, item in enumerate(final_rankings, 1):
            try:
                server = item['server']
                # Update/Create ServerRanking
                # We use update_or_create logic or prepare for bulk update
                # Ideally bulk_update for perf, but lets be safe with get_or_create first
                
                # Prepare minimal dict for frontend
                cached_item = {
                    'rank': rank,
                    'server': {
                        'id': str(server.id),
                        'name': server.name,
                        'profile_url': f"/servers/{server.id}/public",
                        'logo_url': server.logo_url,
                        'icon': server.icon if hasattr(server, 'icon') else '', # Handle potential missing icon field too just in case
                        'platform': server.platform.name.lower() if server.platform else '',
                        'description': server.description,
                    },
                    'scores': item['scores'],
                    'metrics': {
                        'total_volume': float(server.total_verified_payouts or 0),
                        'member_count': member_counts.get(server.id, 0),
                        'total_payouts': server.total_submissions,
                        'active_submitters_30d': server.active_members,
                        'approval_rate': round((server.verified_count / server.total_submissions * 100) if server.total_submissions else 0, 1),
                    },
                    'total_score': item['total_score'],
                    'metadata': {
                        'category': server.market_categories[0].lower() if server.market_categories else 'mixed', 
                        'established': server.created_at.isoformat()
                    },
                    'momentum': {
                        'volume_change_30d': 0, # Calculated below
                        'trend_7d': 'neutral',
                        'trend_icon': 'neutral',
                        'rank_change': 0
                    }
                }
                
                # Calculate Momentum Metrics
                # 30D Volume Change
                v30 = float(server.volume_30d or 0)
                v30_prev = float(server.volume_prev_30d or 0)
                if v30_prev > 0:
                    change_pct = ((v30 - v30_prev) / v30_prev) * 100
                    cached_item['momentum']['volume_change_30d'] = round(change_pct, 1)
                elif v30 > 0:
                    cached_item['momentum']['volume_change_30d'] = 100.0 # New growth
                
                # 7D Trend
                v7 = float(server.volume_7d or 0)
                v7_prev = float(server.volume_prev_7d or 0)
                
                if v7 > v7_prev * 1.05: # >5% growth
                    cached_item['momentum']['trend_7d'] = 'up'
                    cached_item['momentum']['trend_icon'] = '▲' # or unicode arrow
                elif v7 < v7_prev * 0.95: # >5% drop
                    cached_item['momentum']['trend_7d'] = 'down'
                    cached_item['momentum']['trend_icon'] = '▼'
                else:
                    cached_item['momentum']['trend_7d'] = 'neutral'
                    cached_item['momentum']['trend_icon'] = '▶'

                # Rank Change
                old_rank = previous_ranks.get(server.id)
                if old_rank:
                    change = old_rank - rank # e.g. was 5, now 2 => 5 - 2 = +3 (Moved UP 3 spots)
                    cached_item['momentum']['rank_change'] = change
                else:
                    cached_item['momentum']['rank_change'] = 0 # New entrant

                cached_list.append(cached_item)

                # DB Update (deferred to task or done here? Done here for consistency)
                # Find existing ranking or create
                obj, created = ServerRanking.objects.get_or_create(server=server)
                obj.global_rank = rank
                obj.total_score = item['total_score']
                obj.performance_score = item['scores']['performance']
                obj.growth_score = item['scores']['growth']
                obj.engagement_score = item['scores']['engagement']
                obj.diversity_score = item['scores']['diversity']
                obj.last_updated = now
                ranking_objects.append(obj)
            except Exception as e:
                print(f"Error processing server ranking {server.id}: {e}")
                continue

        # Bulk update to save DB queries
        ServerRanking.objects.bulk_update(
            ranking_objects, 
            ['global_rank', 'total_score', 'performance_score', 'growth_score', 'engagement_score', 'diversity_score', 'last_updated']
        )
        
        # 7. Set Cache
        cache.set(RankingService.CACHE_KEY, cached_list, RankingService.CACHE_TIMEOUT)
        
        return cached_list
