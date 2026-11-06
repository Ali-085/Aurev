from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import PlatformLimits, MarketCategory, TradingCategory
from audit.models import AuditLog
from .serializers import (
    PlatformLimitsSerializer,
    MarketCategorySerializer,
    TradingCategorySerializer,
    AuditLogSerializer, UserManagementSerializer, ServerManagementSerializer
)
from users.models import User, Role, UserRole
from servers.models import Server, PlatformChoice
from payouts.models import PayoutSubmission
from django.contrib.auth import get_user_model
import traceback
import sys
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def is_platform_owner(user):
    """Check if user is platform owner (superuser)."""
    return user.is_superuser


# ============= OVERVIEW =============

@api_view(['GET'])
def platform_overview(request):
    """
    Platform owner dashboard overview.
    
    Returns:
    - Total servers
    - Total verified payouts
    - Total payout volume
    - Active servers this week
    - Recent high value payouts
    - System status
    """
    if not is_platform_owner(request.user):
        return Response({"error": "Not allowed"}, status=403)
    
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    
    # Server stats
    total_servers = Server.objects.count()
    active_servers_week = Server.objects.filter(
        payout_submissions__created_at__gte=week_ago
    ).distinct().count()
    suspended_servers = Server.objects.filter(suspended=True).count()
    
    # Payout stats
    all_payouts = PayoutSubmission.objects.filter(status='Approved')
    payout_stats = all_payouts.aggregate(
        total_count=Count('id'),
        total_volume=Sum('amount')
    )
    
    # Recent high value payouts (>$5000)
    high_value_payouts = PayoutSubmission.objects.filter(
        amount__gte=5000,
        created_at__gte=week_ago
    ).select_related('user', 'server').order_by('-amount')[:10]
    
    high_value_list = [
        {
            'id': p.id,
            'amount': float(p.amount),
            'user': p.user.username,
            'server': p.server.name,
            'market': p.market_category,
            'instrument': p.instrument,
            'date': p.created_at.strftime('%Y-%m-%d %H:%M'),
            'status': p.status
        }
        for p in high_value_payouts
    ]
    
    # System status
    pending_payouts = PayoutSubmission.objects.filter(status='Pending').count()
    total_users = User.objects.count()
    active_users_week = User.objects.filter(
        last_login__gte=week_ago
    ).count()
    
    # Platform limits
    limits = PlatformLimits.get_limits()
    
    return Response({
        'servers': {
            'total': total_servers,
            'active_this_week': active_servers_week,
            'suspended': suspended_servers
        },
        'payouts': {
            'total_count': payout_stats['total_count'],
            'total_volume': float(payout_stats['total_volume'] or 0),
            'pending_queue': pending_payouts,
            'high_value_recent': high_value_list
        },
        'users': {
            'total': total_users,
            'active_this_week': active_users_week
        },
        'system_status': {
            'maintenance_mode': limits.maintenance_mode,
            'payout_queue_size': pending_payouts,
            'data_retention_days': limits.data_retention_days,
            'ai_fraud_detection': limits.enable_ai_fraud_detection
        }
    })


# ============= SERVERS =============

@api_view(['GET', 'POST'])
def manage_servers(request):
    """List all servers or create new server."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    if request.method == 'GET':
        from core.pagination import StandardResultsPagination
        
        servers = Server.objects.select_related('owner_user').prefetch_related('members').all()
        
        # Apply search
        search = request.query_params.get('search', '')
        if search:
            servers = servers.filter(
                Q(name__icontains=search) | 
                Q(owner_user__username__icontains=search) |
                Q(owner_user__email__icontains=search)
            )
        
        # Apply filters
        filter_type = request.query_params.get('filter')
        if filter_type == 'verified':
            servers = servers.filter(is_verified=True, suspended=False)
        elif filter_type == 'unverified':
            servers = servers.filter(is_verified=False, suspended=False)
        elif filter_type == 'suspended':
            servers = servers.filter(suspended=True)
        
        # Order by created_at
        servers = servers.order_by('-created_at')
        
        # Apply pagination
        paginator = StandardResultsPagination()
        paginated_servers = paginator.paginate_queryset(servers, request)
        serializer = ServerManagementSerializer(paginated_servers, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    # POST - create server (admin override)
    # Implementation for creating servers as admin
    return Response({"message": "Create server endpoint"}, status=201)


@api_view(['PUT', 'DELETE'])
def manage_server_detail(request, server_id):
    """Update or delete specific server."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    try:
        server = Server.objects.get(id=server_id)
    except Server.DoesNotExist:
        return Response({"error": "Server not found"}, status=404)
    
    if request.method == 'PUT':
        action = request.data.get('action')
        
        if action == 'suspend':
            import bleach
            
            reason = request.data.get('reason', 'Suspended by platform owner')
            # SECURITY: Sanitize reason to prevent XSS
            reason = bleach.clean(str(reason).strip(), tags=[], strip=True)[:500]
            
            server.suspended = True
            server.suspension_reason = reason
            server.save()
            
            # Log action
            AuditLog.log(
                request.user,
                action_type='suspend',
                target_table='server',
                target_id=server.id,
                metadata={'reason': server.suspension_reason}
            )
            
            return Response({"message": "Server suspended"})
        
        elif action == 'unsuspend':
            server.suspended = False
            server.suspension_reason = None
            server.save()
            return Response({"message": "Server unsuspended"})
        
        elif action == 'verify':
            server.is_verified = True
            server.save()
            return Response({"message": "Server verified"})
        
        elif action == 'change_subscription':
            # Note: Subscription changes should be done through Stripe, not directly
            # This endpoint is deprecated - use Stripe subscription management instead
            return Response(
                {"error": "Subscription changes must be done through Stripe"},
                status=400
            )
    
    elif request.method == 'DELETE':
        server_name = server.name
        server.delete()
        
        AuditLog.log(
            request.user,
            action_type='delete',
            target_table='server',
            target_id=server_id,
            metadata={'name': server_name}
        )
        
        return Response({"message": "Server deleted"})


# ============= USERS =============

@api_view(['GET'])
def manage_users(request):
    """List all users with filters."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    users = User.objects.prefetch_related(
        'user_roles__role',
        'owned_servers',
        'server_memberships'
    ).all()
    
    # Apply filters
    search = request.query_params.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Filter by status
    status_filter = request.query_params.get('status')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Filter by role
    role = request.query_params.get('role')
    if role:
        users = users.filter(user_roles__role__name=role).distinct()
    
    # Order by created_at
    users = users.order_by('-created_at')
    
    serializer = UserManagementSerializer(users, many=True)
    return Response({'users': serializer.data})


@api_view(['PUT', 'DELETE'])
def manage_user_detail(request, user_id):
    """
    Update or delete specific user with comprehensive security.
    
    SECURITY MEASURES:
    - Platform owner only access
    - Cannot modify self or other superusers
    - Atomic transactions for role changes
    - Input validation and sanitization
    - Comprehensive audit logging
    """
    try:
        if not is_platform_owner(request.user):
            return Response({"error": "Platform owner access required"}, status=403)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        # SECURITY: Prevent modifying self
        if user.id == request.user.id:
            return Response({"error": "Cannot modify your own account"}, status=403)
        
        # SECURITY: Prevent modifying other superusers
        if user.is_superuser:
            return Response({"error": "Cannot modify other superuser accounts"}, status=403)
        
        if request.method == 'PUT':
            action = request.data.get('action')
            
            # SECURITY: Validate action parameter
            if not action:
                return Response({"error": "Action parameter is required"}, status=400)
            
            if action == 'deactivate':
                # SECURITY: Use update() instead of save() for atomic operation
                from django.db import transaction
                with transaction.atomic():
                    User.objects.filter(id=user_id).update(is_active=False)
                    
                    AuditLog.log(
                        request.user,
                        action_type='update',
                        target_table='user',
                        target_id=user.id,
                        metadata={
                            'username': user.username,
                            'email': user.email,
                            'action': 'deactivated',
                            'previous_status': 'active'
                        }
                    )
                
                return Response({"message": f"User {user.username} deactivated successfully"})
            
            elif action == 'activate':
                # SECURITY: Use atomic transaction
                from django.db import transaction
                
                with transaction.atomic():
                    User.objects.filter(id=user_id).update(is_active=True)
                    
                    AuditLog.log(
                        request.user,
                        action_type='update',
                        target_table='user',
                        target_id=user.id,
                        metadata={
                            'username': user.username,
                            'email': user.email,
                            'action': 'activated',
                            'previous_status': 'inactive'
                        }
                    )
                
                return Response({"message": f"User {user.username} activated successfully"})
            
            elif action == 'change_role':
                from django.db import transaction
                from datetime import timedelta
                import bleach
                
                new_role_name = request.data.get('role')
                
                # SECURITY: Validate role parameter exists
                if not new_role_name:
                    return Response({"error": "Role parameter is required"}, status=400)
                
                # SECURITY: Sanitize input to prevent XSS
                new_role_name = bleach.clean(str(new_role_name).strip(), tags=[], strip=True)
                
                # SECURITY: Strict whitelist validation
                valid_roles = ['ServerCreator', 'Admin', 'Moderator', 'Trader']
                if new_role_name not in valid_roles:
                    return Response({
                        "error": f"Invalid role '{new_role_name}'. Must be one of: {', '.join(valid_roles)}"
                    }, status=400)
                
                # If assigning ServerCreator role, subscription data is required
                if new_role_name == 'ServerCreator':
                    subscription_data = request.data.get('subscription')
                    
                    if not subscription_data:
                        return Response({
                            "error": "ServerCreator role requires subscription data",
                            "required_fields": {
                                "subscription": {
                                    "tier": "standard | premium | elite",
                                    "duration_days": "int (null for permanent)",
                                    "reason": "string",
                                    "override_existing": "bool (optional, default: false)"
                                }
                            }
                        }, status=400)
                    
                    tier = subscription_data.get('tier')
                    duration_days = subscription_data.get('duration_days')
                    reason = subscription_data.get('reason', '').strip()
                    override_existing = subscription_data.get('override_existing', False)
                    
                    # Validate subscription data
                    if not tier:
                        return Response({"error": "subscription.tier is required"}, status=400)
                    if tier not in ['standard', 'premium', 'elite']:
                        return Response({"error": "subscription.tier must be: standard, premium, or elite"}, status=400)
                    if not reason:
                        return Response({"error": "subscription.reason is required for manual grants"}, status=400)
                    
                    # Check for existing subscription
                    from subscriptions.models import UserSubscription, SubscriptionPlan
                    
                    existing_subscription = UserSubscription.objects.filter(
                        user=user,
                        status__in=['active', 'trialing', 'past_due']
                    ).select_related('plan').first()
                    
                    if existing_subscription and not existing_subscription.is_manual_grant and not override_existing:
                        return Response({
                            "error": "User has an active Stripe subscription",
                            "message": "Cannot override paid subscription without override_existing=true",
                            "existing_subscription": {
                                "tier": existing_subscription.plan.tier,
                                "status": existing_subscription.status,
                                "type": "stripe",
                                "expires": existing_subscription.current_period_end.isoformat()
                            }
                        }, status=400)
                    
                    # Convert duration to int or None
                    try:
                        if duration_days is None or duration_days == '' or int(duration_days) <= 0:
                            duration_days = None  # Permanent
                        else:
                            duration_days = int(duration_days)
                    except (ValueError, TypeError):
                        return Response({"error": "subscription.duration_days must be a positive integer or null"}, status=400)
                    
                    # Get subscription plan
                    try:
                        plan = SubscriptionPlan.objects.get(tier=tier)
                    except SubscriptionPlan.DoesNotExist:
                        return Response({"error": f"Subscription plan '{tier}' not found"}, status=404)
                    
                    # Calculate subscription period
                    now = timezone.now()
                    if duration_days is None:
                        period_end = now + timedelta(days=3650)  # 10 years (permanent)
                    else:
                        period_end = now + timedelta(days=duration_days)
                
                # Get old roles for audit log
                old_roles = list(user.user_roles.values_list('role__name', flat=True))
                
                # SECURITY: Use safe role assignment with authorization
                try:
                    user.set_role(new_role_name, changed_by=request.user)
                except (PermissionError, ValueError) as e:
                    return Response({'error': str(e)}, status=403)
                
                # If ServerCreator, create/update subscription
                if new_role_name == 'ServerCreator':
                    # Delete existing subscription if any
                    if existing_subscription:
                        old_tier = existing_subscription.plan.tier
                        existing_subscription.delete()
                        
                        AuditLog.log(
                            request.user,
                            action_type='update',
                            target_table='user',
                            target_id=user.id,
                            metadata={
                                'action': 'subscription_overridden',
                                'username': user.username,
                                'old_tier': old_tier,
                                'was_manual_grant': existing_subscription.is_manual_grant,
                                'override_reason': reason
                            }
                        )
                    
                    # Create manual grant subscription
                    UserSubscription.objects.create(
                        user=user,
                        plan=plan,
                        stripe_subscription_id=None,
                        status='active',
                        current_period_start=now,
                        current_period_end=period_end,
                        cancel_at_period_end=False,
                        is_manual_grant=True,
                        granted_by=request.user,
                        grant_reason=reason,
                        manual_grant_duration_days=duration_days
                    )
                    
                    AuditLog.log(
                        request.user,
                        action_type='create',
                        target_table='user',
                        target_id=user.id,
                        metadata={
                            'action': 'subscription_granted',
                            'username': user.username,
                            'tier': tier,
                            'duration_days': duration_days,
                            'is_permanent': duration_days is None,
                            'reason': reason,
                            'period_end': period_end.isoformat()
                        }
                    )
                
                # Comprehensive audit logging for role change
                AuditLog.log(
                    request.user,
                    action_type='update',
                    target_table='user',
                    target_id=user.id,
                    metadata={
                        'action': 'role_changed',
                        'username': user.username,
                        'email': user.email,
                        'old_roles': old_roles,
                        'new_role': new_role_name,
                        'changed_by': request.user.username,
                        'subscription_granted': new_role_name == 'ServerCreator'
                    }
                )
                
                response_data = {
                    "message": f"User {user.username} role changed to {new_role_name}",
                    "old_roles": old_roles,
                    "new_role": new_role_name
                }
                
                if new_role_name == 'ServerCreator':
                    response_data['subscription'] = {
                        'tier': tier,
                        'status': 'active',
                        'duration_days': duration_days,
                        'is_permanent': duration_days is None,
                        'expires': period_end.isoformat()
                    }
                
                return Response(response_data)
            
            else:
                # SECURITY: Reject unknown actions
                return Response({
                    "error": f"Invalid action '{action}'. Must be: deactivate, activate, or change_role"
                }, status=400)
        
        elif request.method == 'DELETE':
            username = user.username
            user.delete()
            
            AuditLog.log(
                request.user,
                action_type='delete',
                target_table='user',
                target_id=user_id,
                metadata={
                    'action': 'user_deleted',
                    'username': username
                }
            )
            
            return Response({"message": "User deleted"})
    except Exception as e:
        logger.exception(f"Error managing user {user_id} by {request.user.email}")
        return Response(
            {'error': 'An error occurred while managing the user. Please try again.'},
            status=500
        )


@api_view(['POST'])
def ban_user(request, user_id):
    """
    Ban or suspend a user.
    
    Request body:
    - reason: String (required) - Reason for the ban
    - duration_days: Integer (optional) - Ban duration in days, null/0 for permanent
    """
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)
    
    # SECURITY: Prevent banning self
    if user.id == request.user.id:
        return Response({"error": "Cannot ban your own account"}, status=403)
    
    # SECURITY: Prevent banning other superusers
    if user.is_superuser:
        return Response({"error": "Cannot ban other superuser accounts"}, status=403)
    
    reason = request.data.get('reason', '').strip()
    duration_days = request.data.get('duration_days')
    
    if not reason:
        return Response({"error": "Ban reason is required"}, status=400)
    
    # Sanitize reason
    import bleach
    reason = bleach.clean(reason, tags=[], strip=True)[:500]
    
    # Calculate ban expiration
    ban_until = None
    if duration_days and int(duration_days) > 0:
        from datetime import timedelta
        ban_until = timezone.now() + timedelta(days=int(duration_days))
    
    # Deactivate user
    from django.db import transaction
    
    with transaction.atomic():
        User.objects.filter(id=user_id).update(is_active=False)
        
        AuditLog.log(
            request.user,
            action_type='suspend',
            target_table='user',
            target_id=user.id,
            metadata={
                'username': user.username,
                'email': user.email,
                'action': 'user_banned',
                'reason': reason,
                'duration_days': duration_days,
                'ban_until': ban_until.isoformat() if ban_until else 'permanent',
                'is_permanent': ban_until is None
            }
        )
    
    return Response({
        "message": f"User {user.username} has been banned",
        "reason": reason,
        "ban_until": ban_until.isoformat() if ban_until else "permanent"
    })


@api_view(['POST'])
def unban_user(request, user_id):
    """Unban or reactivate a banned user."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)
    
    # SECURITY: Prevent unbanning superusers (shouldn't be banned anyway)
    if user.is_superuser:
        return Response({"error": "Cannot modify superuser accounts"}, status=403)
    
    # Reactivate user
    from django.db import transaction
    
    with transaction.atomic():
        User.objects.filter(id=user_id).update(is_active=True)
        
        AuditLog.log(
            request.user,
            action_type='unsuspend',
            target_table='user',
            target_id=user.id,
            metadata={
                'username': user.username,
                'email': user.email,
                'action': 'user_unbanned'
            }
        )
    
    return Response({
        "message": f"User {user.username} has been unbanned and reactivated"
    })


# ============= GLOBAL PAYOUTS =============

@api_view(['GET'])
def global_payouts(request):
    """List all payouts with filters and pagination."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    from core.pagination import StandardResultsPagination
    
    payouts = PayoutSubmission.objects.select_related('user', 'server', 'reviewer').all()
    
    # Filters
    status = request.query_params.get('status')
    if status:
        payouts = payouts.filter(status=status)
    
    server_id = request.query_params.get('server')
    if server_id:
        payouts = payouts.filter(server_id=server_id)
    
    market = request.query_params.get('market')
    if market:
        payouts = payouts.filter(market_category=market)
    
    min_amount = request.query_params.get('min_amount')
    if min_amount:
        payouts = payouts.filter(amount__gte=min_amount)
    
    max_amount = request.query_params.get('max_amount')
    if max_amount:
        payouts = payouts.filter(amount__lte=max_amount)
    
    date_from = request.query_params.get('date_from')
    if date_from:
        payouts = payouts.filter(created_at__gte=date_from)
    
    date_to = request.query_params.get('date_to')
    if date_to:
        payouts = payouts.filter(created_at__lte=date_to)
    
    # Order by created_at
    payouts = payouts.order_by('-created_at')
    
    # Apply pagination
    paginator = StandardResultsPagination()
    paginated_payouts = paginator.paginate_queryset(payouts, request)
    
    payout_list = [
        {
            'id': p.id,
            'user': p.user.username,
            'server': p.server.name,
            'amount': float(p.amount),
            'currency': p.currency,
            'market': p.market_category,
            'instrument': p.instrument,
            'status': p.status,
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M'),
            'reviewed_by': p.reviewer.username if p.reviewer else None,
            'reviewed_at': p.reviewed_at.strftime('%Y-%m-%d %H:%M') if p.reviewed_at else None
        }
        for p in paginated_payouts
    ]
    
    return paginator.get_paginated_response(payout_list)


@api_view(['POST'])
def quick_payout_action(request, payout_id):
    """Quick approve/reject payout with atomic transaction protection."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    action = request.data.get('action')
    reason = request.data.get('reason', '')
    
    # SECURITY: Sanitize reason to prevent XSS
    import bleach
    reason = bleach.clean(str(reason).strip(), tags=[], strip=True)[:500]
    
    # SECURITY: Use transaction.atomic() and select_for_update() to prevent race conditions
    with transaction.atomic():
        try:
            # Lock payout row to prevent concurrent modifications
            payout = PayoutSubmission.objects.select_for_update().get(id=payout_id)
        except PayoutSubmission.DoesNotExist:
            return Response({"error": "Payout not found"}, status=404)
        
        # Allow platform owner to revert approved payouts or reject any status
        if action == 'reject':
            # Can reject from any status (Pending, Approved, Suspicious)
            pass
        elif action == 'approve':
            # Can only approve Pending payouts
            if payout.status != 'Pending':
                return Response(
                    {"message": f"Cannot approve payout with status: {payout.status}"},
                    status=400
                )
        else:
            return Response({"error": "Invalid action. Use 'approve' or 'reject'."}, status=400)
        
        if action == 'approve':
            payout.status = 'Approved'
            payout.reviewer = request.user
            payout.reviewed_at = timezone.now()
            payout.save()
            
            # Update member stats atomically with row locking
            member = payout.server.members.select_for_update().filter(user=payout.user).first()
            if member:
                member.total_verified_payouts += payout.amount
                member.total_submissions += 1
                member.last_submission_at = payout.created_at
                member.save()
            
            AuditLog.log(
                request.user,
                action_type='approve',
                target_table='payout',
                target_id=payout.id,
                metadata={'amount': float(payout.amount), 'user': payout.user.username}
            )
            
            return Response({"message": "Payout approved"})
        
        elif action == 'reject':
            from payouts.models import PayoutReviewLog
            from analytics.models import ServerAnalytics, UserAnalytics
            from decimal import Decimal
            
            previous_status = payout.status
            
            # If reverting an approved payout, deduct from member stats and analytics
            if previous_status == 'Approved':
                # Update member stats
                member = payout.server.members.select_for_update().filter(user=payout.user).first()
                if member:
                    member.total_verified_payouts = max(Decimal('0'), member.total_verified_payouts - payout.amount)
                    member.total_submissions = max(0, member.total_submissions - 1)
                    member.save()
                
                # Update server analytics
                try:
                    server_analytics = ServerAnalytics.objects.select_for_update().get(server=payout.server)
                    server_analytics.total_volume = max(Decimal('0'), server_analytics.total_volume - payout.amount)
                    server_analytics.total_payouts = max(0, server_analytics.total_payouts - 1)
                    
                    # Update market breakdown
                    if server_analytics.market_breakdown:
                        market_key = payout.market_category
                        if market_key in server_analytics.market_breakdown:
                            server_analytics.market_breakdown[market_key] = max(
                                0, 
                                float(server_analytics.market_breakdown[market_key]) - float(payout.amount)
                            )
                    
                    # Update instrument breakdown
                    if server_analytics.instrument_breakdown:
                        instrument_key = payout.instrument
                        if instrument_key in server_analytics.instrument_breakdown:
                            server_analytics.instrument_breakdown[instrument_key] = max(
                                0,
                                float(server_analytics.instrument_breakdown[instrument_key]) - float(payout.amount)
                            )
                    
                    # Update daily breakdown
                    if server_analytics.daily_breakdown:
                        date_key = payout.payout_date.strftime('%Y-%m-%d')
                        if date_key in server_analytics.daily_breakdown:
                            server_analytics.daily_breakdown[date_key] = max(
                                0,
                                float(server_analytics.daily_breakdown[date_key]) - float(payout.amount)
                            )
                    
                    # Recalculate unique traders
                    server_analytics.unique_traders = PayoutSubmission.objects.filter(
                        server=payout.server,
                        status='Approved'
                    ).exclude(id=payout.id).values('user').distinct().count()
                    
                    server_analytics.save()
                except ServerAnalytics.DoesNotExist:
                    pass  # Analytics don't exist yet, nothing to update
                
                # Update user analytics
                try:
                    user_analytics = UserAnalytics.objects.select_for_update().get(user=payout.user)
                    user_analytics.total_volume = max(Decimal('0'), user_analytics.total_volume - payout.amount)
                    user_analytics.total_payouts = max(0, user_analytics.total_payouts - 1)
                    
                    # Update market breakdown
                    if user_analytics.market_breakdown:
                        market_key = payout.market_category
                        if market_key in user_analytics.market_breakdown:
                            user_analytics.market_breakdown[market_key] = max(
                                0,
                                float(user_analytics.market_breakdown[market_key]) - float(payout.amount)
                            )
                    
                    # Update instrument breakdown
                    if user_analytics.instrument_breakdown:
                        instrument_key = payout.instrument
                        if instrument_key in user_analytics.instrument_breakdown:
                            user_analytics.instrument_breakdown[instrument_key] = max(
                                0,
                                float(user_analytics.instrument_breakdown[instrument_key]) - float(payout.amount)
                            )
                    
                    user_analytics.save()
                except UserAnalytics.DoesNotExist:
                    pass  # Analytics don't exist yet, nothing to update
            
            payout.status = 'Rejected'
            payout.reviewer = request.user
            payout.reviewed_at = timezone.now()
            payout.save()
            
            # Create review log
            PayoutReviewLog.objects.create(
                payout_submission=payout,
                reviewer_user=request.user,
                action='Rejected',
                reason=reason or f'Rejected by platform owner (reverted from {previous_status})'
            )
            
            AuditLog.log(
                request.user,
                action_type='reject',
                target_table='payout',
                target_id=payout.id,
                metadata={
                    'amount': float(payout.amount), 
                    'reason': reason,
                    'previous_status': previous_status,
                    'reverted': previous_status == 'Approved'
                }
            )
            
            return Response({
                "message": f"Payout {'reverted and ' if previous_status == 'Approved' else ''}rejected",
                "previous_status": previous_status
            })
        
        else:
            return Response({"error": "Invalid action. Use 'approve' or 'reject'."}, status=400)


# ============= GLOBAL CONFIG =============

# GlobalMarket endpoints removed - model deleted during schema simplification


# GlobalMarket detail endpoint removed - model deleted during schema simplification


# GlobalCategory endpoints removed - model deleted during schema simplification


# GlobalCategory detail endpoint removed - model deleted during schema simplification


@api_view(['GET', 'PUT'])
def manage_limits(request):
    """Get or update platform limits."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    limits = PlatformLimits.get_limits()
    
    if request.method == 'GET':
        serializer = PlatformLimitsSerializer(limits)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = PlatformLimitsSerializer(limits, data=request.data, partial=True)
        if serializer.is_valid():
            limits = serializer.save(updated_by=request.user)
            
            AuditLog.log(
                request.user,
                action_type='update',
                target_table='platform',
                target_id=1,
                metadata={
                    'action': 'limits_changed',
                    'changes': request.data
                }
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# ============= AUDIT LOGS =============

@api_view(['GET'])
def audit_logs(request):
    """Get audit logs with recent actions."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    logs = AuditLog.objects.select_related('actor_user').all()
    
    # Filters
    action = request.query_params.get('action')
    if action:
        logs = logs.filter(action_type=action)
    
    admin_id = request.query_params.get('admin')
    if admin_id:
        logs = logs.filter(actor_user_id=admin_id)
    
    limit = int(request.query_params.get('limit', 100))
    logs = logs.order_by('-created_at')[:limit]
    
    serializer = AuditLogSerializer(logs, many=True)
    return Response({
        'logs': serializer.data,
        'recent_actions': serializer.data[:50]  # Include recent_actions for audit tab
    })


# ============= BILLING =============

@api_view(['GET'])
def billing_overview(request):
    """Platform billing and revenue overview."""
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    # Subscription stats using UserSubscription model
    from subscriptions.models import UserSubscription, SubscriptionPlan
    
    # Get subscription breakdown by tier
    subscription_stats = UserSubscription.objects.filter(
        status__in=['active', 'trialing']
    ).values('plan__tier').annotate(count=Count('id'))
    
    subscription_breakdown = {stat['plan__tier']: stat['count'] for stat in subscription_stats}
    
    # Get plan prices from database
    plans = SubscriptionPlan.objects.filter(is_active=True)
    tier_prices = {plan.tier: float(plan.price_per_month) for plan in plans}
    
    # Calculate monthly revenue
    monthly_revenue = sum(subscription_breakdown.get(tier, 0) * price for tier, price in tier_prices.items())
    
    # Active subscriptions count
    active_subscriptions = UserSubscription.objects.filter(
        status__in=['active', 'trialing']
    ).count()
    
    return Response({
        'subscription_breakdown': subscription_breakdown,
        'active_subscriptions': active_subscriptions,
        'monthly_recurring_revenue': monthly_revenue,
        'total_revenue_estimate': monthly_revenue * 12  # Annual estimate
    })


# ============= SUBSCRIPTION MANAGEMENT =============

@api_view(['GET'])
def get_subscription_status(request, user_id):
    """
    Get subscription status for a user.
    
    Returns:
    - has_subscription: bool
    - subscription_type: 'stripe' | 'manual_grant' | null
    - tier: 'standard' | 'premium' | 'elite' | null
    - status: 'active' | 'trialing' | 'past_due' | 'canceled' | 'unpaid' | null
    - current_period_end: ISO datetime | null
    - is_paid: bool (true if Stripe, false if manual grant)
    - grant_info: {granted_by, grant_reason, duration_days} | null
    """
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)
    
    from subscriptions.models import UserSubscription
    
    # Get active subscription (only one per user allowed)
    subscription = UserSubscription.objects.filter(
        user=user,
        status__in=['active', 'trialing', 'past_due']
    ).select_related('plan', 'granted_by').first()
    
    if not subscription:
        return Response({
            'has_subscription': False,
            'subscription_type': None,
            'tier': None,
            'status': None,
            'current_period_end': None,
            'is_paid': False,
            'grant_info': None
        })
    
    grant_info = None
    if subscription.is_manual_grant:
        grant_info = {
            'granted_by': subscription.granted_by.username if subscription.granted_by else 'Unknown',
            'grant_reason': subscription.grant_reason,
            'duration_days': subscription.manual_grant_duration_days,
            'is_permanent': subscription.manual_grant_duration_days is None
        }
    
    return Response({
        'has_subscription': True,
        'subscription_type': 'manual_grant' if subscription.is_manual_grant else 'stripe',
        'tier': subscription.plan.tier,
        'status': subscription.status,
        'current_period_end': subscription.current_period_end.isoformat(),
        'is_paid': not subscription.is_manual_grant,
        'grant_info': grant_info
    })


@api_view(['POST'])
def grant_subscription(request, user_id):
    """
    Manually grant subscription to a user.
    
    Required fields:
    - tier: 'standard' | 'premium' | 'elite'
    - duration_days: int (null or 0 = permanent)
    - reason: str (reason for grant)
    
    Optional fields:
    - override_existing: bool (default: false) - allow override of paid Stripe subscriptions
    
    SECURITY:
    - Platform owner only
    - Cannot override Stripe subscription unless override_existing=true
    - Creates audit log
    - One subscription per user enforcement
    """
    if not is_platform_owner(request.user):
        return Response({"error": "Platform owner access required"}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)
    
    # Validate required fields
    tier = request.data.get('tier')
    duration_days = request.data.get('duration_days')
    reason = request.data.get('reason', '').strip()
    override_existing = request.data.get('override_existing', False)
    
    # SECURITY: Sanitize reason to prevent XSS
    import bleach
    reason = bleach.clean(str(reason), tags=[], strip=True)[:500]
    
    if not tier:
        return Response({"error": "tier is required (standard, premium, or elite)"}, status=400)
    
    if tier not in ['standard', 'premium', 'elite']:
        return Response({"error": "Invalid tier. Must be: standard, premium, or elite"}, status=400)
    
    if not reason:
        return Response({"error": "reason is required for manual grants"}, status=400)
    
    # Convert duration_days to int or None for permanent
    try:
        if duration_days is None or duration_days == '' or int(duration_days) <= 0:
            duration_days = None  # Permanent
        else:
            duration_days = int(duration_days)
    except (ValueError, TypeError):
        return Response({"error": "duration_days must be a positive integer or null for permanent"}, status=400)
    
    from subscriptions.models import UserSubscription, SubscriptionPlan
    from datetime import timedelta
    
    # Check for existing subscription
    existing_subscription = UserSubscription.objects.filter(
        user=user,
        status__in=['active', 'trialing', 'past_due']
    ).select_related('plan').first()
    
    if existing_subscription:
        # Check if it's a paid Stripe subscription
        if not existing_subscription.is_manual_grant and not override_existing:
            return Response({
                "error": "User has an active Stripe subscription",
                "message": "Cannot override paid subscription without override_existing=true",
                "existing_subscription": {
                    "tier": existing_subscription.plan.tier,
                    "status": existing_subscription.status,
                    "type": "stripe",
                    "expires": existing_subscription.current_period_end.isoformat()
                }
            }, status=400)
        
        # Cancel/delete existing subscription (manual grant or override approved)
        old_tier = existing_subscription.plan.tier
        existing_subscription.delete()
        
        AuditLog.log(
            request.user,
            action_type='update',
            target_table='user',
            target_id=user.id,
            metadata={
                'action': 'subscription_overridden',
                'username': user.username,
                'old_tier': old_tier,
                'was_manual_grant': existing_subscription.is_manual_grant,
                'override_reason': reason
            }
        )
    
    # Get subscription plan
    try:
        plan = SubscriptionPlan.objects.get(tier=tier)
    except SubscriptionPlan.DoesNotExist:
        return Response({"error": f"Subscription plan '{tier}' not found"}, status=404)
    
    # Calculate subscription period
    now = timezone.now()
    if duration_days is None:
        # Permanent: set end date 10 years in future
        period_end = now + timedelta(days=3650)
    else:
        period_end = now + timedelta(days=duration_days)
    
    # Create manual grant subscription
    with transaction.atomic():
        subscription = UserSubscription.objects.create(
            user=user,
            plan=plan,
            stripe_subscription_id=None,  # No Stripe ID for manual grants
            status='active',
            current_period_start=now,
            current_period_end=period_end,
            cancel_at_period_end=False,
            is_manual_grant=True,
            granted_by=request.user,
            grant_reason=reason,
            manual_grant_duration_days=duration_days
        )
        
        AuditLog.log(
            request.user,
            action_type='create',
            target_table='user',
            target_id=user.id,
            metadata={
                'action': 'subscription_granted',
                'username': user.username,
                'tier': tier,
                'duration_days': duration_days,
                'is_permanent': duration_days is None,
                'reason': reason,
                'period_end': period_end.isoformat()
            }
        )
    
    return Response({
        "message": f"Subscription granted successfully to {user.username}",
        "subscription": {
            "tier": tier,
            "status": "active",
            "duration_days": duration_days,
            "is_permanent": duration_days is None,
            "current_period_end": period_end.isoformat(),
            "granted_by": request.user.username,
            "grant_reason": reason
        }
    }, status=201)


# ============= MARKET CATEGORIES MANAGEMENT =============

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Allow unauthenticated users to view markets
def market_categories_list(request):
    """
    GET: List all market categories (public access for dropdowns)
    POST: Create new market category (platform owner only)
    """
    if request.method == 'GET':
        # Anyone can view active markets (for dropdowns)
        # SECURITY: Authenticated superusers see all, others see only active
        if request.user.is_authenticated and request.user.is_superuser:
            markets = MarketCategory.objects.all()
        else:
            markets = MarketCategory.objects.filter(is_active=True)
        
        serializer = MarketCategorySerializer(markets, many=True)
        return Response({'markets': serializer.data})
    
    elif request.method == 'POST':
        # SECURITY: Only authenticated platform owner can create
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        serializer = MarketCategorySerializer(data=request.data)
        if serializer.is_valid():
            market = serializer.save()
            
            # Audit log
            AuditLog.log(
                request.user,
                action_type='create',
                target_table='market_categories',
                target_id=market.id,
                metadata={'action': 'market_created', 'name': market.name, 'icon': market.icon}
            )
            
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])  # Allow public read access
def market_category_detail(request, pk):
    """
    GET: Get market category detail (public access)
    PUT: Update market category (platform owner only)
    DELETE: Delete market category (platform owner only)
    """
    try:
        market = MarketCategory.objects.get(pk=pk)
    except MarketCategory.DoesNotExist:
        return Response({"error": "Market category not found"}, status=404)
    
    if request.method == 'GET':
        serializer = MarketCategorySerializer(market)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # SECURITY: Only authenticated platform owner can update
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        serializer = MarketCategorySerializer(market, data=request.data, partial=True)
        if serializer.is_valid():
            market = serializer.save()
            
            # Audit log
            AuditLog.log(
                request.user,
                action_type='update',
                target_table='market_categories',
                target_id=market.id,
                metadata={
                    'action': 'market_updated',
                    'name': market.name,
                    'is_active': market.is_active,
                    'changes': request.data
                }
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        # SECURITY: Only authenticated platform owner can delete
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        # Check if any payouts use this market
        from payouts.models import PayoutSubmission
        payout_count = PayoutSubmission.objects.filter(market_category=market.name).count()
        
        if payout_count > 0:
            return Response({
                "error": f"Cannot delete market '{market.name}' - it is used in {payout_count} payout submissions"
            }, status=400)
        
        # Audit log before deletion
        AuditLog.log(
            request.user,
            action_type='delete',
            target_table='market_categories',
            target_id=market.id,
            metadata={'action': 'market_deleted', 'name': market.name}
        )
        
        market.delete()
        return Response({"message": "Market category deleted successfully"}, status=204)


# ============= TRADING CATEGORIES MANAGEMENT =============

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Allow public read access
def trading_categories_list(request):
    """
    GET: List all trading categories (public access)
    POST: Create new trading category (platform owner only)
    """
    if request.method == 'GET':
        # Anyone can view active categories
        # SECURITY: Authenticated superusers see all, others see only active
        if request.user.is_authenticated and request.user.is_superuser:
            categories = TradingCategory.objects.all()
        else:
            categories = TradingCategory.objects.filter(is_active=True)
        
        # Optional filter by type
        category_type = request.GET.get('type')
        if category_type:
            categories = categories.filter(category_type=category_type)
        
        serializer = TradingCategorySerializer(categories, many=True)
        return Response({'categories': serializer.data})
    
    elif request.method == 'POST':
        # SECURITY: Only authenticated platform owner can create
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        serializer = TradingCategorySerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            
            # Audit log
            AuditLog.log(
                request.user,
                action_type='create',
                target_table='trading_categories',
                target_id=category.id,
                metadata={
                    'action': 'category_created',
                    'name': category.name,
                    'type': category.category_type
                }
            )
            
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([AllowAny])  # Allow public read access
def trading_category_detail(request, pk):
    """
    GET: Get trading category detail (public access)
    PUT: Update trading category (platform owner only)
    DELETE: Delete trading category (platform owner only)
    """
    try:
        category = TradingCategory.objects.get(pk=pk)
    except TradingCategory.DoesNotExist:
        return Response({"error": "Trading category not found"}, status=404)
    
    if request.method == 'GET':
        serializer = TradingCategorySerializer(category)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # SECURITY: Only authenticated platform owner can update
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        serializer = TradingCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            category = serializer.save()
            
            # Audit log
            AuditLog.log(
                request.user,
                action_type='update',
                target_table='trading_categories',
                target_id=category.id,
                metadata={
                    'action': 'category_updated',
                    'name': category.name,
                    'type': category.category_type,
                    'is_active': category.is_active,
                    'changes': request.data
                }
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        # SECURITY: Only authenticated platform owner can delete
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        # Audit log before deletion
        AuditLog.log(
            request.user,
            action_type='delete',
            target_table='trading_categories',
            target_id=category.id,
            metadata={
                'action': 'category_deleted',
                'name': category.name,
                'type': category.category_type
            }
        )
        
        category.delete()
        return Response({"message": "Trading category deleted successfully"}, status=204)


# ============= PLATFORM CHOICES =============

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def platform_choice_list(request):
    """
    GET: List all platform choices (ordered by display_order) - PUBLIC.
    POST: Create a new platform choice (superuser only).
    """
    if request.method == 'GET':
        # PUBLIC: Anyone can view platform choices (needed for dropdowns)
        platforms = PlatformChoice.objects.all()
        
        # Optionally filter to only active platforms
        if request.query_params.get('active_only') == 'true':
            platforms = platforms.filter(is_active=True)
        
        data = [{
            'id': p.id,
            'name': p.name,
            'is_active': p.is_active,
            'display_order': p.display_order,
            'created_at': p.created_at
        } for p in platforms]
        
        return Response(data)
    
    elif request.method == 'POST':
        # SECURITY: Only platform owner can create platforms
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        name = request.data.get('name', '').strip()
        if not name:
            return Response({"error": "Platform name is required"}, status=400)
        
        # Check for duplicate
        if PlatformChoice.objects.filter(name__iexact=name).exists():
            return Response({"error": "Platform with this name already exists"}, status=400)
        
        display_order = request.data.get('display_order', 0)
        is_active = request.data.get('is_active', True)
        
        platform = PlatformChoice.objects.create(
            name=name,
            is_active=is_active,
            display_order=display_order
        )
        
        # Audit log
        AuditLog.log(
            request.user,
            action_type='create',
            target_table='platform_choices',
            target_id=platform.id,
            metadata={'action': 'platform_created', 'name': name}
        )
        
        return Response({
            'id': platform.id,
            'name': platform.name,
            'is_active': platform.is_active,
            'display_order': platform.display_order,
            'created_at': platform.created_at
        }, status=201)


@api_view(['GET', 'PUT', 'DELETE'])
def platform_choice_detail(request, pk):
    """
    GET: Retrieve a specific platform choice.
    PUT: Update a platform choice (superuser only).
    DELETE: Delete a platform choice (superuser only).
    """
    try:
        platform = PlatformChoice.objects.get(pk=pk)
    except PlatformChoice.DoesNotExist:
        return Response({"error": "Platform not found"}, status=404)
    
    if request.method == 'GET':
        return Response({
            'id': platform.id,
            'name': platform.name,
            'is_active': platform.is_active,
            'display_order': platform.display_order,
            'created_at': platform.created_at
        })
    
    elif request.method == 'PUT':
        # SECURITY: Only platform owner can update
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        # Update fields
        if 'name' in request.data:
            new_name = request.data['name'].strip()
            if not new_name:
                return Response({"error": "Platform name cannot be empty"}, status=400)
            
            # Check for duplicate (excluding current platform)
            if PlatformChoice.objects.filter(name__iexact=new_name).exclude(pk=pk).exists():
                return Response({"error": "Platform with this name already exists"}, status=400)
            
            platform.name = new_name
        
        if 'is_active' in request.data:
            platform.is_active = request.data['is_active']
        
        if 'display_order' in request.data:
            platform.display_order = request.data['display_order']
        
        platform.save()
        
        # Audit log
        AuditLog.log(
            request.user,
            action_type='update',
            target_table='platform_choices',
            target_id=platform.id,
            metadata={
                'action': 'platform_updated',
                'name': platform.name,
                'is_active': platform.is_active
            }
        )
        
        return Response({
            'id': platform.id,
            'name': platform.name,
            'is_active': platform.is_active,
            'display_order': platform.display_order,
            'created_at': platform.created_at
        })
    
    elif request.method == 'DELETE':
        # SECURITY: Only platform owner can delete
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        # Check if any servers are using this platform
        server_count = Server.objects.filter(platform=platform).count()
        if server_count > 0:
            return Response({
                "error": f"Cannot delete platform. {server_count} server(s) are using this platform."
            }, status=400)
        
        # Audit log before deletion
        AuditLog.log(
            request.user,
            action_type='delete',
            target_table='platform_choices',
            target_id=platform.id,
            metadata={'action': 'platform_deleted', 'name': platform.name}
        )
        
        platform.delete()
        return Response({"message": "Platform deleted successfully"}, status=204)


# ============= PROP FIRMS MANAGEMENT =============

@api_view(['GET', 'POST'])
def prop_firms_list(request):
    """
    List all prop firms or create a new one.
    GET: Anyone can view (for frontend dropdown population)
    POST: Platform owner only
    """
    if request.method == 'GET':
        from payouts.prop_firms import PropFirm
        from .serializers import PropFirmManagementSerializer
        
        # Get all prop firms (active and inactive for admin view)
        if request.user.is_authenticated and is_platform_owner(request.user):
            firms = PropFirm.objects.all().order_by('display_order', 'name')
        else:
            # Regular users see only active firms
            firms = PropFirm.objects.filter(is_active=True).order_by('display_order', 'name')
        
        serializer = PropFirmManagementSerializer(firms, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        from payouts.prop_firms import PropFirm
        from .serializers import PropFirmManagementSerializer
        from django.utils.text import slugify
        
        # SECURITY: Only platform owner can create
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        # Validate required fields
        name = request.data.get('name', '').strip()
        if not name:
            return Response({"error": "Prop firm name is required"}, status=400)
        
        # Check for duplicates (case-insensitive)
        if PropFirm.objects.filter(name__iexact=name).exists():
            return Response({"error": "Prop firm with this name already exists"}, status=400)
        
        # Create prop firm
        firm = PropFirm.objects.create(
            name=name,
            slug=slugify(name),
            is_active=request.data.get('is_active', True),
            logo_url=request.data.get('logo_url', ''),
            website_url=request.data.get('website_url', ''),
            display_order=request.data.get('display_order', 0)
        )
        
        # Audit log
        AuditLog.log(
            request.user,
            action_type='create',
            target_table='prop_firms',
            target_id=firm.id,
            metadata={
                'action': 'prop_firm_created',
                'name': firm.name,
                'slug': firm.slug
            }
        )
        
        serializer = PropFirmManagementSerializer(firm)
        return Response(serializer.data, status=201)


@api_view(['GET', 'PUT', 'DELETE'])
def prop_firm_detail(request, pk):
    """
    Get, update, or delete a specific prop firm.
    GET: Anyone can view
    PUT/DELETE: Platform owner only
    """
    from payouts.prop_firms import PropFirm
    from .serializers import PropFirmManagementSerializer
    from django.utils.text import slugify
    
    try:
        firm = PropFirm.objects.get(pk=pk)
    except PropFirm.DoesNotExist:
        return Response({"error": "Prop firm not found"}, status=404)
    
    if request.method == 'GET':
        serializer = PropFirmManagementSerializer(firm)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # SECURITY: Only platform owner can update
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        # Update fields
        if 'name' in request.data:
            new_name = request.data['name'].strip()
            if not new_name:
                return Response({"error": "Prop firm name cannot be empty"}, status=400)
            
            # Check for duplicate (excluding current firm)
            if PropFirm.objects.filter(name__iexact=new_name).exclude(pk=pk).exists():
                return Response({"error": "Prop firm with this name already exists"}, status=400)
            
            firm.name = new_name
            firm.slug = slugify(new_name)
        
        if 'is_active' in request.data:
            firm.is_active = request.data['is_active']
        
        if 'logo_url' in request.data:
            firm.logo_url = request.data['logo_url']
        
        if 'website_url' in request.data:
            firm.website_url = request.data['website_url']
        
        if 'display_order' in request.data:
            firm.display_order = request.data['display_order']
        
        firm.save()
        
        # Audit log
        AuditLog.log(
            request.user,
            action_type='update',
            target_table='prop_firms',
            target_id=firm.id,
            metadata={
                'action': 'prop_firm_updated',
                'name': firm.name,
                'is_active': firm.is_active
            }
        )
        
        serializer = PropFirmManagementSerializer(firm)
        return Response(serializer.data)
    
    elif request.method == 'DELETE':
        # SECURITY: Only platform owner can delete
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        if not is_platform_owner(request.user):
            return Response({"error": "Permission denied"}, status=403)
        
        # Check if any payouts are using this firm
        from payouts.models import PayoutSubmission
        payout_count = PayoutSubmission.objects.filter(prop_firm=firm).count()
        if payout_count > 0:
            return Response({
                "error": f"Cannot delete prop firm. {payout_count} payout(s) are using this firm."
            }, status=400)
        
        # Audit log before deletion
        AuditLog.log(
            request.user,
            action_type='delete',
            target_table='prop_firms',
            target_id=firm.id,
            metadata={'action': 'prop_firm_deleted', 'name': firm.name}
        )
        
        firm.delete()
        return Response({"message": "Prop firm deleted successfully"}, status=204)
