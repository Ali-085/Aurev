"""
Subscription Plan Management for Platform Admins

Endpoints for superusers to manage subscription plans:
- List all plans
- Create new plans
- Update existing plans (features, pricing, Stripe IDs)
- Activate/Deactivate plans
- Delete plans (with safety checks)
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from users.permissions import IsEmailVerified
from rest_framework import status
from django.db import transaction
from subscriptions.models import SubscriptionPlan, UserSubscription
from subscriptions.serializers import SubscriptionPlanSerializer
from audit.models import AuditLog


def is_platform_owner(user):
    """Check if user is platform owner (superuser)."""
    return user.is_superuser


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def subscription_plans_list(request):
    """
    GET: List all subscription plans (including inactive ones for admin)
    POST: Create a new subscription plan
    
    Only accessible by platform superusers.
    """
    if not is_platform_owner(request.user):
        return Response(
            {"error": "Not authorized. Superuser access required."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        # List all plans (including inactive for admin view)
        plans = SubscriptionPlan.objects.all().order_by('sort_order', 'price_per_month')
        
        # Include Stripe IDs for admin
        data = []
        for plan in plans:
            plan_data = {
                'id': plan.id,
                'name': plan.name,
                'tier': plan.tier,
                'description': plan.description,
                'price_per_month': str(plan.price_per_month),
                'stripe_price_id': plan.stripe_price_id,
                'stripe_product_id': plan.stripe_product_id,
                'features': plan.features,
                'is_active': plan.is_active,
                'sort_order': plan.sort_order,
                'created_at': plan.created_at.isoformat(),
                'updated_at': plan.updated_at.isoformat(),
                'active_subscriptions_count': UserSubscription.objects.filter(
                    plan=plan,
                    status__in=['active', 'trialing']
                ).count()
            }
            data.append(plan_data)
        
        return Response({
            'plans': data,
            'total': len(data)
        })
    
    elif request.method == 'POST':
        # Create new subscription plan
        data = request.data
        
        # Validate required fields
        required_fields = ['name', 'tier', 'description', 'price_per_month']
        missing_fields = [f for f in required_fields if not data.get(f)]
        
        if missing_fields:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate tier is unique
        tier = data.get('tier')
        if SubscriptionPlan.objects.filter(tier=tier).exists():
            return Response(
                {"error": f"A plan with tier '{tier}' already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Create plan
                plan = SubscriptionPlan.objects.create(
                    name=data['name'],
                    tier=tier,
                    description=data['description'],
                    price_per_month=data['price_per_month'],
                    stripe_price_id=data.get('stripe_price_id', 'price_PLACEHOLDER'),
                    stripe_product_id=data.get('stripe_product_id', 'prod_PLACEHOLDER'),
                    features=data.get('features', []),
                    is_active=data.get('is_active', True),
                    sort_order=data.get('sort_order', 0)
                )
                # Audit log
                AuditLog.log(
                    user=request.user,
                    action_type='create',
                    target_table='SubscriptionPlan',
                    target_id=plan.id,
                    metadata={
                        'plan_name': plan.name,
                        'tier': plan.tier,
                        'price': str(plan.price_per_month),
                    }
                )

                return Response({
                    'message': 'Subscription plan created successfully',
                    'plan': {
                        'id': plan.id,
                        'name': plan.name,
                        'tier': plan.tier,
                        'price_per_month': str(plan.price_per_month),
                        'stripe_price_id': plan.stripe_price_id,
                        'is_active': plan.is_active
                    }
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {"error": f"Failed to create plan: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsEmailVerified])
def subscription_plan_detail(request, plan_id):
    """
    GET: Retrieve plan details
    PUT/PATCH: Update plan details
    DELETE: Delete plan (if no active subscriptions)
    
    Only accessible by platform superusers.
    """
    if not is_platform_owner(request.user):
        return Response(
            {"error": "Not authorized. Superuser access required."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return Response(
            {"error": "Subscription plan not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        return Response({
            'id': plan.id,
            'name': plan.name,
            'tier': plan.tier,
            'description': plan.description,
            'price_per_month': str(plan.price_per_month),
            'stripe_price_id': plan.stripe_price_id,
            'stripe_product_id': plan.stripe_product_id,
            'features': plan.features,
            'is_active': plan.is_active,
            'sort_order': plan.sort_order,
            'created_at': plan.created_at.isoformat(),
            'updated_at': plan.updated_at.isoformat(),
            'active_subscriptions_count': UserSubscription.objects.filter(
                plan=plan,
                status__in=['active', 'trialing']
            ).count()
        })
    
    elif request.method in ['PUT', 'PATCH']:
        # Update plan
        data = request.data
        updated_fields = []
        
        # Track changes for audit log
        changes = {}
        
        try:
            with transaction.atomic():
                # Update fields if provided
                if 'name' in data and data['name'] != plan.name:
                    changes['name'] = {'old': plan.name, 'new': data['name']}
                    plan.name = data['name']
                    updated_fields.append('name')
                
                if 'description' in data and data['description'] != plan.description:
                    changes['description'] = {'old': plan.description, 'new': data['description']}
                    plan.description = data['description']
                    updated_fields.append('description')
                
                if 'price_per_month' in data:
                    new_price = str(data['price_per_month'])
                    if new_price != str(plan.price_per_month):
                        changes['price_per_month'] = {'old': str(plan.price_per_month), 'new': new_price}
                        plan.price_per_month = data['price_per_month']
                        updated_fields.append('price_per_month')
                
                if 'stripe_price_id' in data and data['stripe_price_id'] != plan.stripe_price_id:
                    changes['stripe_price_id'] = {'old': plan.stripe_price_id, 'new': data['stripe_price_id']}
                    plan.stripe_price_id = data['stripe_price_id']
                    updated_fields.append('stripe_price_id')
                
                if 'stripe_product_id' in data and data['stripe_product_id'] != plan.stripe_product_id:
                    changes['stripe_product_id'] = {'old': plan.stripe_product_id, 'new': data['stripe_product_id']}
                    plan.stripe_product_id = data['stripe_product_id']
                    updated_fields.append('stripe_product_id')
                
                if 'features' in data:
                    changes['features'] = {'old': plan.features, 'new': data['features']}
                    plan.features = data['features']
                    updated_fields.append('features')
                
                if 'is_active' in data and data['is_active'] != plan.is_active:
                    changes['is_active'] = {'old': plan.is_active, 'new': data['is_active']}
                    plan.is_active = data['is_active']
                    updated_fields.append('is_active')
                
                if 'sort_order' in data and data['sort_order'] != plan.sort_order:
                    changes['sort_order'] = {'old': plan.sort_order, 'new': data['sort_order']}
                    plan.sort_order = data['sort_order']
                    updated_fields.append('sort_order')
                
                if not updated_fields:
                    return Response(
                        {"message": "No changes detected"},
                        status=status.HTTP_200_OK
                    )
                
                plan.save()
                
                # Audit log
                AuditLog.log(
                    request.user,
                    action_type='update',
                    target_table='SubscriptionPlan',
                    target_id=plan.id,
                    metadata={
                        'plan_name': plan.name,
                        'tier': plan.tier,
                        'updated_fields': updated_fields,
                        'changes': changes
                    }
                )
                
                return Response({
                    'message': f'Plan updated successfully ({len(updated_fields)} fields changed)',
                    'updated_fields': updated_fields,
                    'plan': {
                        'id': plan.id,
                        'name': plan.name,
                        'tier': plan.tier,
                        'price_per_month': str(plan.price_per_month),
                        'stripe_price_id': plan.stripe_price_id,
                        'stripe_product_id': plan.stripe_product_id,
                        'is_active': plan.is_active
                    }
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {"error": f"Failed to update plan: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    elif request.method == 'DELETE':
        # Check if any users are currently subscribed to this plan
        active_subs = UserSubscription.objects.filter(
            plan=plan,
            status__in=['active', 'trialing']
        ).count()
        
        if active_subs > 0:
            return Response({
                "error": f"Cannot delete plan with {active_subs} active subscription(s)",
                "suggestion": "Deactivate the plan instead to prevent new subscriptions"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if any historical subscriptions exist
        total_subs = UserSubscription.objects.filter(plan=plan).count()
        
        if total_subs > 0:
            return Response({
                "error": f"Cannot delete plan with {total_subs} total subscription record(s)",
                "suggestion": "Plan has historical data. Consider deactivating instead."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                plan_name = plan.name
                plan_tier = plan.tier
                
                # Audit log before deletion
                AuditLog.log(
                    request.user,
                    action_type='delete',
                    target_table='SubscriptionPlan',
                    target_id=plan.id,
                    metadata={
                        'plan_name': plan_name,
                        'tier': plan_tier,
                        'price': str(plan.price_per_month)
                    }
                )
                
                plan.delete()
                
                return Response({
                    'message': f'Subscription plan "{plan_name}" deleted successfully'
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {"error": f"Failed to delete plan: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
