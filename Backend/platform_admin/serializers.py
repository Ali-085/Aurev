from rest_framework import serializers
from django.db import models
from .models import PlatformLimits, MarketCategory, TradingCategory
from audit.models import AuditLog
from audit.serializers import AuditLogSerializer
from users.models import User
from servers.models import Server
from payouts.prop_firms import PropFirm


class MarketCategorySerializer(serializers.ModelSerializer):
    """Serializer for market categories (Futures, Forex, Crypto, etc.)"""
    
    class Meta:
        model = MarketCategory
        fields = ['id', 'name', 'description', 'icon', 'is_active', 'display_order', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_name(self, value):
        """Ensure name is unique (case-insensitive)"""
        if MarketCategory.objects.filter(name__iexact=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("A market category with this name already exists.")
        return value


class TradingCategorySerializer(serializers.ModelSerializer):
    """Serializer for trading categories (skill level, region, etc.)"""
    category_type_display = serializers.CharField(source='get_category_type_display', read_only=True)
    
    class Meta:
        model = TradingCategory
        fields = ['id', 'name', 'category_type', 'category_type_display', 'description', 'is_active', 'display_order', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Ensure name + category_type combination is unique"""
        name = data.get('name')
        category_type = data.get('category_type')
        
        if name and category_type:
            query = TradingCategory.objects.filter(name__iexact=name, category_type=category_type)
            if self.instance:
                query = query.exclude(id=self.instance.id)
            
            if query.exists():
                raise serializers.ValidationError("A category with this name and type already exists.")
        
        return data


class PlatformLimitsSerializer(serializers.ModelSerializer):
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True)
    
    class Meta:
        model = PlatformLimits
        fields = '__all__'


class UserManagementSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    servers = serializers.SerializerMethodField()
    total_payouts = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_active', 'is_superuser',
                  'roles', 'servers', 'total_payouts', 'last_login', 'created_at']
    
    def get_roles(self, obj):
        # Use .all() to leverage prefetched data from the view
        return [ur.role.name for ur in obj.user_roles.all()]
    
    def get_servers(self, obj):
        owned = obj.owned_servers.count()
        member = obj.server_memberships.count()
        return {'owned': owned, 'member_of': member}
    
    def get_total_payouts(self, obj):
        from payouts.models import PayoutSubmission
        approved = PayoutSubmission.objects.filter(user=obj, status='Approved')
        return {
            'count': approved.count(),
            'total': float(approved.aggregate(total=models.Sum('amount'))['total'] or 0)
        }


class ServerManagementSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner_user.username', read_only=True)
    owner_email = serializers.CharField(source='owner_user.email', read_only=True)
    member_count = serializers.SerializerMethodField()
    total_payouts = serializers.SerializerMethodField()
    subscription_plan = serializers.SerializerMethodField()
    
    class Meta:
        model = Server
        fields = ['id', 'name', 'owner_user', 'owner_username', 'owner_email',
                  'platform', 'is_verified', 'suspended', 'suspension_reason',
                  'member_count', 'total_payouts', 'subscription_plan', 'created_at']
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_total_payouts(self, obj):
        from payouts.models import PayoutSubmission
        approved = PayoutSubmission.objects.filter(server=obj, status='Approved')
        return {
            'count': approved.count(),
            'total': float(approved.aggregate(total=models.Sum('amount'))['total'] or 0)
        }
    
    def get_subscription_plan(self, obj):
        # Get from server owner's active subscription
        sub = obj.owner_user.subscriptions.filter(status='active').first()
        return sub.plan.tier if sub else 'standard'


class PropFirmManagementSerializer(serializers.ModelSerializer):
    """Serializer for prop firm management in platform admin."""
    
    class Meta:
        model = PropFirm
        fields = ['id', 'name', 'slug', 'is_active', 'logo_url', 'website_url', 'display_order', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_name(self, value):
        """Ensure name is unique (case-insensitive)"""
        if PropFirm.objects.filter(name__iexact=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("A prop firm with this name already exists.")
        return value
