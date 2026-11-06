from rest_framework import serializers
import logging

logger = logging.getLogger(__name__)
from .models import Server, ServerMember
from users.serializers import UserSerializer


class ServerSerializer(serializers.ModelSerializer):
    """
    Serializer for Server model with comprehensive analytics for leaderboard ranking.
    
    Includes data for Master Formula:
    - Performance: Verified payout volume (log-scaled)
    - Growth: Percentage growth over time
    - Engagement: Active traders, submission frequency, approval rate
    - Quality: Fake detection rate, approval accuracy
    - Diversity: Market variety, trader spread, instrument diversity
    """
    
    owner_user = UserSerializer(read_only=True)
    platform = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    total_verified_payouts = serializers.SerializerMethodField()
    total_submissions = serializers.SerializerMethodField()
    suspicious_count = serializers.SerializerMethodField()
    unique_markets = serializers.SerializerMethodField()
    unique_instruments = serializers.SerializerMethodField()
    active_traders_count = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    global_rank = serializers.SerializerMethodField()
    
    class Meta:
        model = Server
        fields = [
            'id', 'owner_user', 'name', 'description', 'logo_url',
            'platform', 'invite_link', 'website', 'twitter_url', 'youtube_url', 
            'instagram_url', 'support_email', 'market_categories', 'is_verified', 'suspended',
            'suspension_reason', 'created_at', 'updated_at', 
            'member_count', 'total_verified_payouts', 'total_submissions',
            'suspicious_count', 'unique_markets', 'unique_instruments',
            'active_traders_count', 'global_rank'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'updated_at']
    
    def get_platform(self, obj):
        """Return platform name from ForeignKey"""
        try:
            return obj.platform.name if obj.platform else None
        except Exception:
            return None
    
    def get_logo_url(self, obj):
        """Return absolute URL for server logo"""
        try:
            # Return logo_url from R2 storage
            if obj.logo_url:
                return obj.logo_url
        except Exception:
            pass
        return None
    
    def get_global_rank(self, obj):
        """Return server's global ranking position"""
        if hasattr(obj, 'ranking'):
            return obj.ranking.global_rank
        return None
    
    def get_member_count(self, obj):
        """Total server members"""
        try:
            return obj.members.count()
        except Exception:
            return 0
    
    def get_total_verified_payouts(self, obj):
        """Sum of all approved payout amounts"""
        try:
            from django.db.models import Sum
            result = obj.payout_submissions.filter(status='Approved').aggregate(
                total=Sum('amount')
            )
            return float(result['total'] or 0)
        except Exception:
            return 0.0
    
    def get_total_submissions(self, obj):
        """Total payout submissions (all statuses)"""
        try:
            return obj.payout_submissions.count()
        except Exception:
            return 0
    
    def get_suspicious_count(self, obj):
        """Count of suspicious/rejected submissions"""
        try:
            return obj.payout_submissions.filter(
                status__in=['Suspicious', 'Rejected']
            ).count()
        except Exception:
            return 0
    
    def get_unique_markets(self, obj):
        """Number of unique market categories traded"""
        try:
            return obj.payout_submissions.values('market_category').distinct().count()
        except Exception:
            return 0
    
    def get_unique_instruments(self, obj):
        """Number of unique instruments traded"""
        try:
            return obj.payout_submissions.values('instrument').distinct().count()
        except Exception:
            return 0
    
    def get_active_traders_count(self, obj):
        """Number of members with at least one submission"""
        try:
            return obj.payout_submissions.values('user').distinct().count()
        except Exception:
            return 0


class ServerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a server with platform limits enforcement."""
    
    platform = serializers.CharField()
    market_categories = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="List of market categories from platform_admin.MarketCategory"
    )
    
    class Meta:
        model = Server
        fields = ['name', 'description', 'platform', 'invite_link', 'market_categories']
        extra_kwargs = {
            'invite_link': {'required': False, 'allow_blank': True, 'allow_null': True}
        }
    
    def to_internal_value(self, data):
        """Parse market_categories if it's a JSON string"""
        import json
        from django.http import QueryDict
        
        # Handle market_categories sent as JSON string from FormData
        if 'market_categories' in data:
            categories = data.get('market_categories')
            logger.info(f"CREATE - Received: {categories} (type: {type(categories)})")
            if isinstance(categories, str):
                try:
                    parsed_categories = json.loads(categories)
                    logger.info(f"CREATE - Parsed: {parsed_categories}")
                    # Convert QueryDict to regular dict for proper list handling
                    if isinstance(data, QueryDict):
                        data = dict(data.lists())  # Convert to dict with lists
                        # Extract single values from lists (except market_categories)
                        data = {k: v[0] if len(v) == 1 else v for k, v in data.items()}
                    else:
                        data = data.copy()
                    data['market_categories'] = parsed_categories
                    logger.info(f"CREATE - Final data type: {type(data)}, market_categories: {data.get('market_categories')}")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse market_categories JSON in create: {e}")
        
        return super().to_internal_value(data)
    
    def validate_platform(self, value):
        """Validate platform exists and is active."""
        from .models import PlatformChoice
        
        try:
            platform = PlatformChoice.objects.get(name=value, is_active=True)
            return platform
        except PlatformChoice.DoesNotExist:
            active_platforms = list(
                PlatformChoice.objects.filter(is_active=True).values_list('name', flat=True)
            )
            raise serializers.ValidationError(
                f"Invalid platform. Must be one of: {', '.join(active_platforms)}"
            )
    
    def validate_market_categories(self, value):
        """Validate market categories against active platform categories"""
        if not value:
            return []
        
        from platform_admin.models import MarketCategory
        
        active_categories = list(
            MarketCategory.objects.filter(is_active=True).values_list('name', flat=True)
        )
        
        invalid_categories = [cat for cat in value if cat not in active_categories]
        
        if invalid_categories:
            raise serializers.ValidationError(
                f"Invalid market categories: {', '.join(invalid_categories)}. "
                f"Must be one of: {', '.join(active_categories)}"
            )
        
        return value
    
    def create(self, validated_data):
        from platform_admin.enforcement import enforce_server_limits
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .models import ServerMember
        
        user = self.context['request'].user
        
        # ENFORCE PLATFORM LIMITS: Check server creation quotas
        try:
            enforce_server_limits(user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'non_field_errors': str(e)})
        
        # Create the server
        server = Server.objects.create(owner_user=user, **validated_data)
        
        # Automatically create a membership for the owner
        # This allows owners to submit payouts and appear in stats
        ServerMember.objects.create(
            server=server,
            user=user
        )
        
        return server


class ServerUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating server details (owner only)."""
    
    platform = serializers.CharField(required=False)
    market_categories = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="List of market categories from platform_admin.MarketCategory"
    )
    
    class Meta:
        model = Server
        fields = ['name', 'description', 'platform', 'invite_link', 'market_categories']
        extra_kwargs = {
            'invite_link': {'required': False, 'allow_blank': True, 'allow_null': True}
        }
    
    def to_internal_value(self, data):
        """Parse market_categories if it's a JSON string"""
        import json
        from django.http import QueryDict
        
        # Handle market_categories sent as JSON string from FormData
        if 'market_categories' in data:
            categories = data.get('market_categories')
            logger.info(f"UPDATE - Received: {categories} (type: {type(categories)})")
            if isinstance(categories, str):
                try:
                    parsed_categories = json.loads(categories)
                    logger.info(f"UPDATE - Parsed: {parsed_categories}")
                    # Convert QueryDict to regular dict for proper list handling
                    if isinstance(data, QueryDict):
                        data = dict(data.lists())  # Convert to dict with lists
                        # Extract single values from lists (except market_categories)
                        data = {k: v[0] if len(v) == 1 else v for k, v in data.items()}
                    else:
                        data = data.copy()
                    data['market_categories'] = parsed_categories
                    logger.info(f"UPDATE - Final data type: {type(data)}, market_categories: {data.get('market_categories')}")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse market_categories JSON in update: {e}")
        
        return super().to_internal_value(data)
    
    def validate_platform(self, value):
        """Validate platform exists and is active."""
        from .models import PlatformChoice
        
        try:
            platform = PlatformChoice.objects.get(name=value, is_active=True)
            return platform
        except PlatformChoice.DoesNotExist:
            active_platforms = list(
                PlatformChoice.objects.filter(is_active=True).values_list('name', flat=True)
            )
            raise serializers.ValidationError(
                f"Invalid platform. Must be one of: {', '.join(active_platforms)}"
            )
    
    def validate_market_categories(self, value):
        """Validate market categories against active platform categories."""
        logger.info(f"Validating market_categories: {value} (type: {type(value)})")
        if not value:
            return []
        
        from platform_admin.models import MarketCategory
        
        active_categories = list(
            MarketCategory.objects.filter(is_active=True).values_list('name', flat=True)
        )
        logger.info(f"Active categories from DB: {active_categories}")
        
        invalid_categories = [cat for cat in value if cat not in active_categories]
        
        if invalid_categories:
            logger.error(f"Invalid categories detected: {invalid_categories}")
            raise serializers.ValidationError(
                f"Invalid market categories: {', '.join(invalid_categories)}. "
                f"Must be one of: {', '.join(active_categories)}"
            )
        
        return value


class ServerMemberSerializer(serializers.ModelSerializer):
    """Serializer for ServerMember model."""
    
    user = UserSerializer(read_only=True)
    server = ServerSerializer(read_only=True)
    
    class Meta:
        model = ServerMember
        fields = [
            'id', 'server', 'user', 'joined_at',
            'total_verified_payouts', 'total_submissions',
            'last_submission_at'
        ]
        read_only_fields = [
            'id', 'joined_at', 'total_verified_payouts',
            'total_submissions', 'last_submission_at'
        ]
