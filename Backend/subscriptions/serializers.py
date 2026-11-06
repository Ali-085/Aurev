from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription
from servers.serializers import ServerSerializer


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'tier', 'description', 'price_per_month',
            'features', 'sort_order'
        ]
        read_only_fields = ['id']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions with tier-based field filtering"""
    
    plan = SubscriptionPlanSerializer(read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'status', 'current_period_start',
            'current_period_end', 'cancel_at_period_end', 'created_at'
        ]
        read_only_fields = fields
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Field filtering based on user tier (defense in depth)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Get user's active subscription to determine tier
            active_sub = UserSubscription.objects.filter(
                user=request.user,
                status__in=['active', 'trialing']
            ).select_related('plan').first()
            
            user_tier = active_sub.plan.tier if active_sub else 'standard'
            
            # Standard tier users get basic fields only (defense in depth)
            if user_tier == 'standard':
                # Remove all fields except basic info
                allowed_fields = {'id', 'status'}
                for field_name in list(self.fields.keys()):
                    if field_name not in allowed_fields:
                        self.fields.pop(field_name)


# ServerSubscriptionSerializer removed - using UserSubscription tier to determine server capabilities
