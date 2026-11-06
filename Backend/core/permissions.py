from rest_framework import permissions


class IsAdminOrModerator(permissions.BasePermission):
    """
    Custom permission for platform Admin and Moderator roles.
    
    IMPORTANT: This is for PLATFORM staff (Admin/Moderator), NOT server owners.
    Server owners cannot review, approve, or reject payouts.
    
    Used for:
    - Payout review/approval/rejection
    - Platform moderation tasks
    
    Role Differences:
    - Admin: Can edit minor payout details, reassign categories, restore rejected submissions
    - Moderator: Can only review and approve/reject (no editing)
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SECURITY: Check email verification
        if not request.user.email_verified:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user has platform Admin or Moderator role
        # Superuser can do EVERYTHING Admins and Moderators can do
        # NOTE: Server ownership does NOT grant payout review permissions
        return request.user.user_roles.filter(
            role__name__in=['Admin', 'Moderator']
        ).exists()


class IsAdminOnly(permissions.BasePermission):
    """
    Custom permission for Admin role only.
    
    Admins are high-trust moderators with expanded moderation capabilities:
    - Edit minor payout details (formatting, category reassignment)
    - Restore accidentally rejected submissions
    - Pause payout submissions on servers
    - Download data reports for moderation
    - Access server-specific analytics
    
    Admins CANNOT:
    - Delete servers
    - Modify platform settings
    - Edit global rankings or totals
    - View security/audit logs (Superuser only)
    - Change subscription settings (Superuser only)
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SECURITY: Check email verification
        if not request.user.email_verified:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Superuser can do everything Admin can do, plus more
        return request.user.user_roles.filter(role__name='Admin').exists()


class IsModeratorOnly(permissions.BasePermission):
    """
    Custom permission for Moderator role only.
    
    Moderators are verification workers ONLY with very limited permissions:
    - Review payout submissions
    - Approve or reject payouts
    - Mark payouts as fake/fraudulent
    - Add reason/comment when rejecting
    - View server analytics (for verification context only)
    - View trader/member profiles
    - Recheck previously handled submissions
    
    Moderators CANNOT:
    - Delete ANYTHING
    - Edit ANY payout details
    - Modify server totals or rankings
    - Add/remove users or servers
    - Change settings or categories
    - Access global analytics
    - Access admin settings
    - Create/delete accounts
    - Export full data
    - See platform financials
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SECURITY: Check email verification
        if not request.user.email_verified:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Superuser and Admin can do everything Moderator can do
        return request.user.user_roles.filter(role__name__in=['Admin', 'Moderator']).exists()


class IsSuperuserOnly(permissions.BasePermission):
    """
    Custom permission for platform superusers only.
    Superusers have full unrestricted access to site administration:
    - User role management (create/delete admin/mod accounts)
    - Server management (create, edit, delete any server)
    - Server verification and suspension
    - Global platform settings
    - ALL audit logs (who approved what, when)
    - Security logs and hosting settings
    - Override moderator decisions
    - Manually adjust totals, rankings, and data
    - Access ALL analytics
    - Subscription/payment settings
    
    Note: This is for PLATFORM superusers (site admins), NOT server owners.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SECURITY: Check email verification
        if not request.user.email_verified:
            return False
        
        # Only superusers have access
        return request.user.is_superuser


class IsServerOwnerOnly(permissions.BasePermission):
    """
    Custom permission for server owners managing their own servers.
    Server owners can:
    - Customize Elite branding (if they have Elite subscription)
    - View analytics for their own server
    - Manage server settings
    
    Server owners CANNOT:
    - Review/approve/reject payouts (platform Admin/Moderator only)
    - Suspend other servers
    - Manage user roles
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SECURITY: Check email verification
        if not request.user.email_verified:
            return False
        
        # Check if user owns any servers
        return request.user.owned_servers.exists()
    
    def has_object_permission(self, request, view, obj):
        # Check if user owns the specific server
        if hasattr(obj, 'server'):
            return obj.server.owner_user == request.user
        if hasattr(obj, 'owner_user'):
            return obj.owner_user == request.user
        return False


class SubscriptionPermission(permissions.BasePermission):
    """
    Subscription tier-based permission.
    Validates BOTH subscription tier AND subscription status via UserSubscription model.
    
    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, SubscriptionPermission]
            required_tier = 'elite'  # or 'standard', 'premium'
    """
    
    TIER_LEVELS = {
        'standard': 1,
        'premium': 2,
        'elite': 3,
    }
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SECURITY: Check email verification AND full activation
        # Subscriptions require completed onboarding (both flags)
        if not request.user.email_verified or not request.user.is_active:
            return False
        
        # Get required tier from view (default to 'standard')
        required_tier = getattr(view, 'required_tier', 'standard')
        required_tier_level = self.TIER_LEVELS.get(required_tier, 1)
        
        # Get user's active subscription
        from subscriptions.models import UserSubscription
        active_sub = UserSubscription.objects.filter(
            user=request.user,
            status__in=['active', 'trialing', 'past_due']
        ).select_related('plan').first()
        
        # No active subscription = deny access (all tiers are paid)
        if not active_sub:
            return False
        
        # Get user's tier level
        user_tier = active_sub.plan.tier
        user_tier_level = self.TIER_LEVELS.get(user_tier, 0)
        
        # Must have sufficient tier level
        if user_tier_level < required_tier_level:
            return False
        
        return True
