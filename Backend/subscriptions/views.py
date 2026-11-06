import stripe
import logging
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import SubscriptionPermission
from users.models import User
from .models import SubscriptionPlan, UserSubscription
from .serializers import ( 
    SubscriptionPlanSerializer
)

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


# User Subscription Views (Webhook-First Pattern)

class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """View available subscription plans"""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]


@api_view(['POST'])
def create_checkout_session(request):
    """
    Create Stripe checkout session for subscription or handle upgrade/downgrade.
    Frontend redirects user to Stripe Checkout.
    
    SECURITY: Accepts tier OR price_id from frontend, but validates against database.
    Price is determined by the database plan, not frontend input.
    
    NOTE: Server creators with pending applications must use the dedicated 
    server-creator checkout endpoint instead.
    
    FLOW:
    1. Check if user already has active subscription
    2. If same plan: reject (already subscribed)
    3. If upgrade/downgrade: return requires_confirmation flag (frontend shows preview)
    4. If new subscription: create Stripe customer (fail-early), then checkout session
    """
    from users.models import ServerCreatorApplication
    
    try:
        # SECURITY: Prevent server creators from using this endpoint during registration
        if ServerCreatorApplication.objects.filter(
            user=request.user,
            status__in=['pending_email', 'pending_payment', 'payment_processing']
        ).exists():
            return Response(
                {'error': 'Server creator registration in progress. Please complete payment via the registration flow.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tier = request.data.get('tier')
        price_id = request.data.get('price_id')
        
        if not tier and not price_id:
            return Response(
                {'error': 'Either tier or price_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # SECURITY: Get plan from database (source of truth for pricing)
        # Never trust frontend for price - always look up in database
        try:
            if price_id:
                # Lookup by Stripe price_id (more secure - prevents tier spoofing)
                plan = SubscriptionPlan.objects.get(stripe_price_id=price_id, is_active=True)
            else:
                # Lookup by tier (more user-friendly)
                plan = SubscriptionPlan.objects.get(tier=tier, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid subscription plan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # SECURITY: Check if user already has an active subscription
        active_subscription = UserSubscription.objects.filter(
            user=user,
            status__in=['active', 'trialing']
        ).first()
        
        # If user has active subscription, handle upgrade/downgrade flow
        if active_subscription:
            # Check if trying to subscribe to the same plan
            if active_subscription.plan.stripe_price_id == plan.stripe_price_id:
                return Response(
                    {'error': 'You are already subscribed to this plan'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # All tiers are paid (standard/premium/elite)
            # To cancel subscription completely, user should use cancel_subscription endpoint
            
            # For upgrades/downgrades, return flag to trigger preview dialog
            # Frontend will call preview_subscription_change, show confirmation, then call confirm_subscription_change
            return Response({
                'requires_confirmation': True,
                'message': 'Subscription change requires confirmation',
                'current_plan': {
                    'name': active_subscription.plan.name,
                    'tier': active_subscription.plan.tier,
                    'price': float(active_subscription.plan.price_per_month),
                },
                'new_plan': {
                    'name': plan.name,
                    'tier': plan.tier,
                    'price': float(plan.price_per_month),
                },
            })
        
        # For new subscriptions (no active subscription), create Stripe customer if needed
        if not user.stripe_customer_id:
            # FAIL-EARLY: Create customer in Stripe FIRST
            try:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={'user_id': user.id}
                )
            except stripe.StripeError as e:
                logger.error(f"Failed to create Stripe customer: {str(e)}")
                return Response(
                    {'error': 'Failed to create customer account. Please try again.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Only update DB if Stripe succeeded
            with transaction.atomic():
                user_obj = User.objects.select_for_update().get(id=user.id)
                # Double-check in case another request already created it
                if not user_obj.stripe_customer_id:
                    user_obj.stripe_customer_id = customer.id
                    user_obj.save(update_fields=['stripe_customer_id'])
                # Update the reference
                user = user_obj
        
        # URLs from backend settings - never trust frontend
        success_url = f"{settings.FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.FRONTEND_URL}/subscription/cancel"
        
        # Create checkout session
        # SECURITY: Use plan.stripe_price_id from database (not frontend input)
        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            line_items=[{
                'price': plan.stripe_price_id,  # From database, not user input
                'quantity': 1,
            }],
            mode='subscription',
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': user.id,
                'tier': plan.tier,  # Use database tier, not frontend input
            }
        )
        
        return Response({
            'sessionId': checkout_session.id,
            'url': checkout_session.url
        })
    
    except stripe.StripeError as e:
        logger.error(f"Stripe error in checkout: {str(e)}")
        return Response(
            {'error': 'Payment processing error. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Checkout session creation failed: {str(e)}")
        return Response(
            {'error': 'An error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_server_creator_checkout_session(request):
    """
    Create Stripe checkout session for Server Creator application.
    Called after email verification for server creator accounts.
    
    SECURITY:
    - Verifies user has pending application
    - Uses tier from application (not frontend)
    - Creates checkout with application_id in metadata
    """
    from users.models import ServerCreatorApplication
    
    try:
        user = request.user
        logger.info(f"🔍 Checkout request from user: {user.id} ({user.email})")
        
        # SECURITY: Verify user has pending application
        # Accept both pending_payment and payment_processing (in case user refreshes page)
        # Use transaction.atomic() for select_for_update()
        with transaction.atomic():
            try:
                application = ServerCreatorApplication.objects.select_for_update().get(
                    user=user,
                    status__in=['pending_payment', 'payment_processing']
                )
                logger.info(f"✅ Found application: {application.id} (status: {application.status})")
            except ServerCreatorApplication.DoesNotExist:
                # Debug: Check what applications exist for this user
                all_apps = ServerCreatorApplication.objects.filter(user=user)
                logger.error(f"❌ No pending application found for user {user.id}")
                logger.error(f"   User has {all_apps.count()} applications total:")
                for app in all_apps:
                    logger.error(f"   - App {app.id}: status={app.status}, tier={app.tier}")
                
                return Response(
                    {'error': 'No pending server creator application found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if application expired
            if application.expires_at < timezone.now():
                application.status = 'expired'
                application.save(update_fields=['status'])
                return Response(
                    {'error': 'Application expired. Please register again.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # SECURITY: Get plan from database using tier from application (not frontend)
        try:
            plan = SubscriptionPlan.objects.get(tier=application.tier, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid subscription plan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create Stripe customer if needed
        if not user.stripe_customer_id:
            try:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={'user_id': user.id}
                )
            except stripe.StripeError as e:
                logger.error(f"Failed to create Stripe customer for server creator: {str(e)}")
                return Response(
                    {'error': 'Failed to create customer account. Please try again.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                user_obj = User.objects.select_for_update().get(id=user.id)
                if not user_obj.stripe_customer_id:
                    user_obj.stripe_customer_id = customer.id
                    user_obj.save(update_fields=['stripe_customer_id'])
                user = user_obj
        
        # URLs from backend settings
        success_url = f"{settings.FRONTEND_URL}/server-creator/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.FRONTEND_URL}/server-creator/cancel"
        
        # Create checkout session with application metadata
        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': user.id,
                'tier': plan.tier,
                'application_id': application.pk,
                'is_server_creator_registration': 'true'
            }
        )
        
        # Update application with checkout session ID
        with transaction.atomic():
            app_obj = ServerCreatorApplication.objects.select_for_update().get(pk=application.pk)
            app_obj.stripe_checkout_session_id = checkout_session.id
            app_obj.status = 'payment_processing'
            app_obj.save(update_fields=['stripe_checkout_session_id', 'status'])
        
        logger.info(f"Checkout session created for server creator: {user.email}, application_id: {application.pk}")
        
        return Response({
            'sessionId': checkout_session.id,
            'url': checkout_session.url
        })
    
    except stripe.StripeError as e:
        logger.error(f"Stripe error in server creator checkout: {str(e)}")
        return Response(
            {'error': 'Payment processing error. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Server creator checkout session creation failed: {str(e)}")
        return Response(
            {'error': 'An error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """
    Stripe webhook handler - SOURCE OF TRUTH for subscription data
    Database is updated ONLY from webhook events, never from frontend
    """
    logger.info("="*80)
    logger.info("🎯 WEBHOOK RECEIVED FROM STRIPE")
    logger.info("="*80)
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    logger.info(f"📦 Payload size: {len(payload)} bytes")
    logger.info(f"🔐 Signature header present: {bool(sig_header)}")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info("✅ Webhook signature verified successfully")
    except ValueError as e:
        logger.error(f"❌ Invalid webhook payload: {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"❌ Invalid webhook signature: {str(e)}")
        return HttpResponse(status=400)
    
    # Handle the event
    event_type = event['type']
    event_id = event['id']
    logger.info(f"📥 Event Type: {event_type}")
    logger.info(f"🆔 Event ID: {event_id}")
    logger.info(f"📅 Created: {event.get('created')}")
    
    try:
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            logger.info("💳 CHECKOUT SESSION COMPLETED EVENT")
            logger.info(f"   Session ID: {session.get('id')}")
            logger.info(f"   Customer: {session.get('customer')}")
            logger.info(f"   Payment Status: {session.get('payment_status')}")
            logger.info(f"   Metadata: {session.get('metadata')}")
            logger.info("   Calling handle_checkout_session_completed...")
            handle_checkout_session_completed(session)
            logger.info("✅ handle_checkout_session_completed finished")
        elif event_type == 'customer.subscription.updated':
            logger.info("🔄 SUBSCRIPTION UPDATED EVENT")
            handle_subscription_updated(event['data']['object'])
        elif event_type == 'customer.subscription.deleted':
            logger.info("❌ SUBSCRIPTION DELETED EVENT")
            handle_subscription_deleted(event['data']['object'])
        elif event_type == 'invoice.payment_failed':
            logger.info("💥 PAYMENT FAILED EVENT")
            handle_payment_failed(event['data']['object'])
        else:
            logger.info(f"ℹ️ Unhandled event type: {event_type}")
    
    except Exception as e:
        logger.error(f"Webhook handler error for {event_type}: {str(e)}")
        logger.exception("Webhook processing failed")
        return HttpResponse(status=500)
    
    logger.info("✅ Webhook processed successfully, returning 200")
    logger.info("="*80)
    return HttpResponse(status=200)


def handle_checkout_session_completed(session):
    """
    Handle successful checkout - create subscription record
    Uses atomic transaction with row locking to prevent race conditions
    
    SECURITY: For server creator registrations, activates user and grants role
    """
    from users.models import ServerCreatorApplication, Role, UserRole
    
    logger.info(f"🎯 Processing checkout session: {session.get('id')}")
    
    subscription_id = session.get('subscription')
    customer_id = session.get('customer')
    
    if not subscription_id:
        logger.warning(f"⚠️ No subscription in session {session['id']}")
        return
    
    logger.info(f"📋 Retrieving Stripe subscription: {subscription_id}")
    # Get full subscription details from Stripe
    stripe_sub = stripe.Subscription.retrieve(subscription_id)
    logger.info(f"✅ Stripe subscription retrieved: status={stripe_sub['status']}")
    
    # Extract metadata
    metadata = session.get('metadata', {})
    logger.info(f"📦 Session metadata: {metadata}")
    
    user_id = metadata.get('user_id')
    tier = metadata.get('tier')
    application_id = metadata.get('application_id')
    is_server_creator_registration = metadata.get('is_server_creator_registration') == 'true'
    
    logger.info(f"🔍 Extracted: user_id={user_id}, tier={tier}, application_id={application_id}, is_server_creator={is_server_creator_registration}")
    
    if not user_id or not tier:
        logger.error(f"Missing metadata in session {session['id']}")
        return
    
    with transaction.atomic():
        # Lock user row to prevent concurrent updates
        try:
            user = User.objects.select_for_update().get(id=user_id)
            logger.info(f"👤 Found user: {user.email} (id={user.id}, is_active={user.is_active})")
        except User.DoesNotExist:
            logger.error(f"❌ User not found in checkout webhook: {user_id}")
            return
        
        # Get plan - validate it exists
        try:
            plan = SubscriptionPlan.objects.get(tier=tier, is_active=True)
            logger.info(f"📊 Found plan: {plan.name} (tier={tier})")
        except SubscriptionPlan.DoesNotExist:
            logger.error(f"❌ Plan not found for tier {tier} in webhook")
            return
        
        # Extract subscription period info with safe defaults
        try:
            current_period_start = timezone.datetime.fromtimestamp(
                stripe_sub['current_period_start'], tz=timezone.utc
            )
            current_period_end = timezone.datetime.fromtimestamp(
                stripe_sub['current_period_end'], tz=timezone.utc
            )
            cancel_at_period_end = stripe_sub.get('cancel_at_period_end', False)
        except (KeyError, TypeError) as e:
            logger.error(f"❌ Error extracting subscription period: {str(e)}")
            logger.error(f"   Stripe subscription data: {stripe_sub}")
            # Use safe defaults
            current_period_start = timezone.now()
            current_period_end = timezone.now() + timezone.timedelta(days=30)
            cancel_at_period_end = False
        
        # IDEMPOTENCY: Check if subscription already exists
        subscription, created = UserSubscription.objects.update_or_create(
            stripe_subscription_id=subscription_id,
            defaults={
                'user': user,
                'plan': plan,
                'status': stripe_sub.get('status', 'active'),
                'current_period_start': current_period_start,
                'current_period_end': current_period_end,
                'cancel_at_period_end': cancel_at_period_end,
            }
        )
        
        # Update user model
        user.stripe_customer_id = customer_id
        user.save(update_fields=['stripe_customer_id'])
        
        # SECURITY: Handle server creator registration - activate user and grant role
        if is_server_creator_registration and application_id:
            logger.info("="*60)
            logger.info(f"🎓 SERVER CREATOR REGISTRATION PROCESSING")
            logger.info(f"   Application ID: {application_id}")
            logger.info(f"   User ID: {user_id}")
            logger.info(f"   User Email: {user.email}")
            logger.info("="*60)
            
            try:
                # Check if application exists BEFORE locking
                app_exists = ServerCreatorApplication.objects.filter(pk=application_id).exists()
                logger.info(f"📋 Application exists check: {app_exists}")
                
                if not app_exists:
                    logger.error(f"❌❌❌ APPLICATION NOT FOUND IN DATABASE: {application_id}")
                    logger.error(f"   This means the application was deleted or never existed")
                    return
                
                application = ServerCreatorApplication.objects.select_for_update().get(pk=application_id)
                logger.info(f"📋 Found application:")
                logger.info(f"   Status: {application.status}")
                logger.info(f"   Tier: {application.tier}")
                logger.info(f"   User: {application.user_id}")
                logger.info(f"   Created: {application.created_at}")
                logger.info(f"   Email Verified: {application.email_verified_at}")
                logger.info(f"   Payment Completed: {application.payment_completed_at}")
                
                # IDEMPOTENCY: Check if already completed
                if application.status != 'completed':
                    logger.info(f"🔄 Starting activation process (current status: {application.status})")
                    
                    # Activate user (CRITICAL: This enables login)
                    logger.info(f"   Before: user.is_active = {user.is_active}")
                    user.is_active = True
                    user.save(update_fields=['is_active'])
                    logger.info(f"   After: user.is_active = {user.is_active}")
                    logger.info(f"✅ User activated")
                    
                    # Grant ServerCreator role (SECURITY: System operation, use force)
                    logger.info(f"   Granting ServerCreator role...")
                    try:
                        user.set_role('ServerCreator', changed_by=None, force=True)
                        logger.info(f"✅ ServerCreator role granted successfully")
                        
                        # Verify role was assigned
                        user_roles = user.user_roles.all()
                        logger.info(f"   User now has {user_roles.count()} roles:")
                        for ur in user_roles:
                            logger.info(f"     - {ur.role.name}")
                    except Exception as e:
                        logger.error(f"Failed to grant ServerCreator role: {str(e)}")
                        logger.exception("Role grant failed")
                        raise
                    
                    # Update application status
                    logger.info(f"   Updating application status from {application.status} to completed")
                    application.status = 'completed'
                    application.payment_completed_at = timezone.now()
                    application.save(update_fields=['status', 'payment_completed_at'])
                    logger.info(f"✅ Application marked completed")
                    
                    logger.info("="*60)
                    logger.info(f"🎉🎉🎉 SERVER CREATOR ACTIVATION COMPLETE")
                    logger.info(f"   User: {user.email}")
                    logger.info(f"   User ID: {user_id}")
                    logger.info(f"   Application ID: {application_id}")
                    logger.info(f"   is_active: {user.is_active}")
                    logger.info(f"   Role: ServerCreator")
                    logger.info("="*60)
                else:
                    logger.info(f"⏭️ Server creator already activated (idempotent)")
                    logger.info(f"   User: {user.email}")
                    logger.info(f"   Application status: {application.status}")
                    
            except ServerCreatorApplication.DoesNotExist:
                logger.error("="*60)
                logger.error(f"❌❌❌ SERVER CREATOR APPLICATION NOT FOUND")
                logger.error(f"   Application ID: {application_id}")
                logger.error(f"   User ID: {user_id}")
                logger.error(f"   This application may have been deleted")
                logger.error("="*60)
    
    logger.info(f"Subscription created for user {user_id}: {tier}")


def handle_subscription_updated(stripe_sub):
    """Handle subscription updates from Stripe"""
    subscription_id = stripe_sub['id']
    
    with transaction.atomic():
        try:
            sub = UserSubscription.objects.select_for_update().get(
                stripe_subscription_id=subscription_id
            )
        except UserSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {subscription_id}")
            return
        
        # Validate user exists
        try:
            user = User.objects.select_for_update().get(id=sub.user_id)
        except User.DoesNotExist:
            logger.error(f"User not found for subscription: {sub.user_id}")
            return
        
        # Update subscription
        sub.status = stripe_sub['status']
        sub.current_period_start = timezone.datetime.fromtimestamp(
            stripe_sub['current_period_start'], tz=timezone.utc
        )
        sub.current_period_end = timezone.datetime.fromtimestamp(
            stripe_sub['current_period_end'], tz=timezone.utc
        )
        sub.cancel_at_period_end = stripe_sub['cancel_at_period_end']
        sub.save()
    
    logger.info(f"Subscription updated: {subscription_id} -> {stripe_sub['status']}")


def handle_subscription_deleted(stripe_sub):
    """
    Handle subscription cancellation with proper cleanup:
    1. Update subscription status to 'canceled'
    2. Set grace period based on platform settings
    3. Remove ServerCreator role
    4. Soft delete all owned servers
    5. Notify user about grace period
    """
    from servers.models import Server
    from users.models import UserRole, Role
    from platform_admin.models import PlatformLimits
    from datetime import timedelta
    
    subscription_id = stripe_sub['id']
    
    with transaction.atomic():
        try:
            sub = UserSubscription.objects.select_for_update().get(
                stripe_subscription_id=subscription_id
            )
        except UserSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {subscription_id}")
            return
        
        # Validate user exists
        try:
            user = User.objects.select_for_update().get(id=sub.user_id)
        except User.DoesNotExist:
            logger.error(f"User not found for subscription deletion: {sub.user_id}")
            return
        
        # Get platform settings for grace period
        limits = PlatformLimits.get_limits()
        grace_period_days = limits.subscription_grace_period_days
        
        # Calculate grace period end date
        canceled_at = timezone.now()
        grace_period_ends_at = canceled_at + timedelta(days=grace_period_days)
        
        # Update subscription with cancellation details
        sub.status = 'canceled'
        sub.canceled_at = canceled_at
        sub.grace_period_ends_at = grace_period_ends_at
        sub.save(update_fields=['status', 'canceled_at', 'grace_period_ends_at'])
        
        # Remove ServerCreator role
        try:
            server_creator_role = Role.objects.get(name='ServerCreator')
            UserRole.objects.filter(user=user, role=server_creator_role).delete()
            logger.info(f"Removed ServerCreator role from user {user.id}")
        except Role.DoesNotExist:
            logger.warning("ServerCreator role not found in database")
        
        # Soft delete all owned servers
        owned_servers = Server.objects.filter(owner_user=user, is_deleted=False)
        server_count = owned_servers.count()
        
        if server_count > 0:
            owned_servers.update(
                is_deleted=True,
                deleted_at=canceled_at,
                deletion_reason='subscription_canceled',
                payout_submissions_paused=True  # Pause submissions immediately
            )
            logger.info(f"Soft deleted {server_count} servers for user {user.id}")
        
        # TODO: Send cancellation email with grace period details
        # Email should include:
        # - Cancellation confirmation
        # - Grace period end date
        # - Reactivation instructions
        # - Data deletion warning
        
        logger.info(
            f"Subscription canceled: {subscription_id}, "
            f"Grace period ends: {grace_period_ends_at.isoformat()}, "
            f"Servers soft deleted: {server_count}"
        )


def handle_payment_failed(invoice):
    """Handle failed payment - set to past_due (grace period)"""
    subscription_id = invoice.get('subscription')
    
    if not subscription_id:
        return
    
    with transaction.atomic():
        try:
            sub = UserSubscription.objects.select_for_update().get(
                stripe_subscription_id=subscription_id
            )
        except UserSubscription.DoesNotExist:
            logger.warning(f"Subscription not found: {subscription_id}")
            return
        
        # Validate user exists
        try:
            user = User.objects.select_for_update().get(id=sub.user_id)
        except User.DoesNotExist:
            logger.error(f"User not found for payment failure: {sub.user_id}")
            return
        
        # Update status to past_due (grace period - user keeps access)
        sub.status = 'past_due'
        sub.save(update_fields=['status'])
    
    logger.info(f"Payment failed for subscription: {subscription_id}")


@api_view(['POST'])
def reactivate_subscription(request):
    """
    Reactivate a canceled subscription during grace period.
    
    SECURITY:
    - Only works for canceled subscriptions within grace period
    - Restores ServerCreator role
    - Un-soft-deletes servers
    - Reactivates subscription in Stripe
    """
    from servers.models import Server
    from users.models import UserRole, Role
    
    user = request.user
    
    try:
        with transaction.atomic():
            # Get canceled subscription within grace period
            sub = UserSubscription.objects.select_for_update().get(
                user=user,
                status='canceled'
            )
            
            # Check if within grace period
            # SECURITY: Add clock skew buffer (5 minutes) to handle timezone differences
            from datetime import timedelta
            CLOCK_SKEW_BUFFER = timedelta(minutes=5)
            
            if sub.grace_period_ends_at:
                effective_expiry = sub.grace_period_ends_at + CLOCK_SKEW_BUFFER
                if timezone.now() > effective_expiry:
                    return Response(
                        {'error': 'Grace period has expired. Data has been deleted. Please create a new subscription.'},
                        status=status.HTTP_410_GONE
                    )
            
            # Check if manual grant
            if sub.is_manual_grant:
                return Response(
                    {'error': 'Manual grants cannot be reactivated. Please contact support.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reactivate in Stripe first (fail-early pattern)
            if sub.stripe_subscription_id:
                try:
                    # Remove cancel_at_period_end flag
                    updated_stripe_sub = stripe.Subscription.modify(
                        sub.stripe_subscription_id,
                        cancel_at_period_end=False
                    )
                    
                    # Update local record
                    sub.status = updated_stripe_sub['status']
                    sub.current_period_start = timezone.datetime.fromtimestamp(
                        updated_stripe_sub['current_period_start'], tz=timezone.utc
                    )
                    sub.current_period_end = timezone.datetime.fromtimestamp(
                        updated_stripe_sub['current_period_end'], tz=timezone.utc
                    )
                    sub.cancel_at_period_end = False
                    sub.canceled_at = None
                    sub.grace_period_ends_at = None
                    sub.deletion_warning_sent_at = None
                    sub.save()
                    
                except stripe.error.StripeError as e:
                    logger.error(f"Failed to reactivate Stripe subscription: {str(e)}")
                    return Response(
                        {'error': f'Failed to reactivate subscription: {str(e)}'},
                        status=status.HTTP_502_BAD_GATEWAY
                    )
            
            # Restore ServerCreator role (SECURITY: System operation, use force)
            try:
                user.set_role('ServerCreator', changed_by=None, force=True)
            except Exception as e:
                logger.error(f"Failed to restore ServerCreator role: {str(e)}")
                return Response(
                    {'error': 'Failed to restore role. Please contact support.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Restore soft-deleted servers
            restored_servers = Server.objects.filter(
                owner_user=user,
                is_deleted=True,
                deletion_reason='subscription_canceled'
            )
            server_count = restored_servers.count()
            
            restored_servers.update(
                is_deleted=False,
                deleted_at=None,
                deletion_reason=None,
                payout_submissions_paused=False  # Resume submissions
            )
            
            logger.info(
                f"Subscription reactivated for user {user.id}: "
                f"{sub.stripe_subscription_id}, restored {server_count} servers"
            )
            
            return Response({
                'success': True,
                'message': 'Subscription reactivated successfully',
                'servers_restored': server_count,
                'tier': sub.plan.tier,
                'status': sub.status,
                'period_end': sub.current_period_end.isoformat()
            })
            
    except UserSubscription.DoesNotExist:
        return Response(
            {'error': 'No canceled subscription found to reactivate'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Subscription reactivation failed: {str(e)}")
        return Response(
            {'error': 'Failed to reactivate subscription'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def cancel_subscription(request):
    """
    Cancel user's active subscription at period end.
    
    SECURITY: 
    - Requires authentication - users can only cancel their own subscription
    - Cannot cancel manual grants (only platform admins can remove those)
    - Uses select_for_update() to prevent race conditions
    """
    user = request.user
    
    try:
        with transaction.atomic():
            sub = UserSubscription.objects.select_for_update().get(
                user=user,
                status__in=['active', 'trialing']
            )
            
            # Prevent cancellation of manual grants via this endpoint
            if sub.is_manual_grant:
                return Response(
                    {'error': 'Manual grants cannot be canceled. Please contact support.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cancel at period end in Stripe
            if sub.stripe_subscription_id:
                stripe.Subscription.modify(
                    sub.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            
            # Update local record
            sub.cancel_at_period_end = True
            sub.save(update_fields=['cancel_at_period_end'])
        
        return Response({
            'success': True,
            'message': 'Subscription will be canceled at period end',
            'period_end': sub.current_period_end.isoformat()
        })
        
    except UserSubscription.DoesNotExist:
        return Response(
            {'error': 'No active subscription found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe cancellation failed: {str(e)}")
        return Response(
            {'error': 'Failed to cancel subscription with payment provider'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        logger.error(f"Subscription cancellation failed: {str(e)}")
        return Response(
            {'error': 'Failed to cancel subscription'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_subscription_status(request):
    """
    Get user's current subscription status.
    
    SECURITY: Requires authentication - users can only see their own subscription.
    """
    user = request.user
    
    try:
        sub = UserSubscription.objects.select_related('plan', 'granted_by').get(
            user=user,
            status__in=['active', 'trialing', 'past_due', 'canceled']
        )
        
        grant_info = None
        if sub.is_manual_grant:
            grant_info = {
                'granted_by': sub.granted_by.username if sub.granted_by else 'System',
                'grant_reason': sub.grant_reason,
                'duration_days': sub.manual_grant_duration_days,
                'is_permanent': sub.manual_grant_duration_days is None
            }
        
        return Response({
            'has_subscription': True,
            'subscription_type': 'manual_grant' if sub.is_manual_grant else 'stripe',
            'tier': sub.plan.tier,
            'plan_name': sub.plan.name,
            'status': sub.status,
            'current_period_end': sub.current_period_end.isoformat(),
            'cancel_at_period_end': sub.cancel_at_period_end,
            'grant_info': grant_info
        })
    except UserSubscription.DoesNotExist:
        return Response({
            'has_subscription': False,
            'subscription_type': None,
            'tier': 'free',
            'plan_name': 'Free',
            'status': None,
        })


@api_view(['POST'])
def preview_subscription_change(request):
    """
    Preview proration amount for subscription change.
    Called after create_checkout_session returns requires_confirmation=True.
    Frontend displays preview dialog with proration details.
    """
    try:
        tier = request.data.get('tier')
        price_id = request.data.get('price_id')
        
        if not tier and not price_id:
            return Response(
                {'error': 'Either tier or price_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate plan
        try:
            if price_id:
                plan = SubscriptionPlan.objects.get(stripe_price_id=price_id, is_active=True)
            else:
                plan = SubscriptionPlan.objects.get(tier=tier, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid subscription plan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # Check if user has active subscription
        active_subscription = UserSubscription.objects.filter(
            user=user,
            status__in=['active', 'trialing']
        ).first()
        
        if not active_subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if same plan
        if active_subscription.plan.stripe_price_id == plan.stripe_price_id:
            return Response(
                {'error': 'You are already on this plan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Note: All tiers are paid (standard/premium/elite)
        # To cancel subscription, use cancel_subscription endpoint
        
        try:
            # Get current subscription from Stripe
            stripe_sub = stripe.Subscription.retrieve(active_subscription.stripe_subscription_id)
            
            # Preview the upcoming invoice with proration
            upcoming_invoice = stripe.Invoice.upcoming(
                customer=user.stripe_customer_id,
                subscription=active_subscription.stripe_subscription_id,
                subscription_items=[{
                    'id': stripe_sub['items']['data'][0].id,
                    'price': plan.stripe_price_id,
                }],
                subscription_proration_behavior='create_prorations',
            )
            
            # Calculate proration amount
            proration_amount = 0
            for line in upcoming_invoice.get('lines', {}).get('data', []):
                if line.get('proration'):
                    proration_amount += line.get('amount', 0)
            
            # Convert from cents to dollars
            proration_amount_dollars = proration_amount / 100
            
            # Determine if upgrade or downgrade
            current_price = active_subscription.plan.price_per_month
            new_price = plan.price_per_month
            is_upgrade = new_price > current_price
            
            return Response({
                'current_plan': {
                    'name': active_subscription.plan.name,
                    'tier': active_subscription.plan.tier,
                    'price': float(current_price),
                },
                'new_plan': {
                    'name': plan.name,
                    'tier': plan.tier,
                    'price': float(new_price),
                },
                'proration': {
                    'amount': proration_amount_dollars,
                    'is_charge': proration_amount > 0,
                    'is_credit': proration_amount < 0,
                },
                'is_upgrade': is_upgrade,
                'period_end': active_subscription.current_period_end.isoformat(),
                'immediate_charge': proration_amount_dollars if proration_amount > 0 else 0,
                'credit_applied': abs(proration_amount_dollars) if proration_amount < 0 else 0,
            })
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error previewing change: {str(e)}")
            return Response(
                {'error': 'Failed to calculate proration. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Error previewing subscription change: {str(e)}")
        return Response(
            {'error': 'An error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def confirm_subscription_change(request):
    """
    Confirm and execute subscription change after preview.
    Called after user confirms the proration in preview dialog.
    
    SECURITY:
    - Fail-early: Update Stripe first
    - Only update DB if Stripe succeeded
    - Use atomic transactions with row locking
    """
    try:
        tier = request.data.get('tier')
        price_id = request.data.get('price_id')
        
        if not tier and not price_id:
            return Response(
                {'error': 'Either tier or price_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate plan
        try:
            if price_id:
                plan = SubscriptionPlan.objects.get(stripe_price_id=price_id, is_active=True)
            else:
                plan = SubscriptionPlan.objects.get(tier=tier, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid subscription plan'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # Check if user has active subscription
        active_subscription = UserSubscription.objects.filter(
            user=user,
            status__in=['active', 'trialing']
        ).first()
        
        if not active_subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Get the Stripe subscription
            stripe_sub = stripe.Subscription.retrieve(active_subscription.stripe_subscription_id)
            
            # FAIL-EARLY: Update Stripe subscription first
            updated_sub = stripe.Subscription.modify(
                active_subscription.stripe_subscription_id,
                cancel_at_period_end=False,
                proration_behavior='create_prorations',
                items=[{
                    'id': stripe_sub['items']['data'][0].id,
                    'price': plan.stripe_price_id,
                }]
            )
            
            # Only update DB if Stripe succeeded
            with transaction.atomic():
                # Lock records to prevent race conditions
                active_sub = UserSubscription.objects.select_for_update().get(id=active_subscription.id)
                
                # Update subscription record
                period_start = timezone.datetime.fromtimestamp(updated_sub['current_period_start'], tz=timezone.utc)
                period_end = timezone.datetime.fromtimestamp(updated_sub['current_period_end'], tz=timezone.utc)
                
                active_sub.plan = plan
                active_sub.status = updated_sub['status']
                active_sub.current_period_start = period_start
                active_sub.current_period_end = period_end
                active_sub.save()
            
            logger.info(f"Successfully changed subscription for user {user.id} from {active_subscription.plan.tier} to {plan.tier}")
            
            return Response({
                'message': 'Subscription updated successfully',
                'new_tier': plan.tier,
            })
            
        except stripe.StripeError as e:
            logger.error(f"Stripe error confirming change: {str(e)}")
            return Response(
                {'error': f'Failed to update subscription: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Error confirming subscription change: {str(e)}")
        return Response(
            {'error': 'An error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def check_server_creator_status(request):
    """
    Check server creator application status for current user.
    Returns pending_payment flag and application details for frontend routing logic.
    
    Used by:
    - PendingPaymentGuard: Redirects to checkout if pending_payment=true
    - ServerCreatorCheckout: Polls until status=completed or pending_payment=false
    """
    from users.models import ServerCreatorApplication
    
    user = request.user
    
    try:
        # Get most recent application (if any)
        application = ServerCreatorApplication.objects.filter(user=user).order_by('-created_at').first()
        
        if not application:
            # No application found - user is not a server creator applicant
            return Response({
                'pending_payment': False,
                'status': None,
                'application_id': None,
            })
        
        # Check if payment is pending
        pending_payment = application.status in ['pending_payment', 'payment_processing']
        
        return Response({
            'pending_payment': pending_payment,
            'status': application.status,
            'application_id': application.id,
            'tier': application.tier,
            'expires_at': application.expires_at.isoformat() if application.expires_at else None,
        })
    except Exception as e:
        logger.error(f"Error checking server creator status: {str(e)}")
        return Response(
            {'error': 'An unexpected error occurred. Please try again or contact support.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_checkout_session(request):
    """
    Manually process a Stripe checkout session by session_id.
    Used when webhooks fail or are delayed.
    
    SECURITY:
    - Verifies session belongs to authenticated user
    - Fetches real data from Stripe API
    - Processes same as webhook handler
    """
    from users.models import ServerCreatorApplication
    
    session_id = request.data.get('session_id')
    
    if not session_id:
        return Response(
            {'error': 'session_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    
    try:
        # Fetch the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        # SECURITY: Verify session belongs to this user
        metadata = session.get('metadata', {})
        session_user_id = metadata.get('user_id')
        
        if str(session_user_id) != str(user.id):
            logger.error(f"Session user mismatch: session={session_user_id}, request={user.id}")
            return Response(
                {'error': 'Session does not belong to you'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if payment was completed
        if session.get('payment_status') != 'paid':
            return Response(
                {'error': f"Payment not completed. Status: {session.get('payment_status')}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process the session (same logic as webhook)
        logger.info(f"🔄 Manually processing checkout session: {session_id}")
        handle_checkout_session_completed(session)
        
        # Refresh application status
        application = ServerCreatorApplication.objects.filter(user=user).order_by('-created_at').first()
        
        return Response({
            'success': True,
            'message': 'Checkout session processed successfully',
            'status': application.status if application else None,
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error processing session: {str(e)}")
        return Response(
            {'error': 'Failed to verify payment session. Please contact support.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error processing checkout session: {str(e)}")
        return Response(
            {'error': 'Failed to process payment session. Please contact support.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def dev_complete_server_creator(request):
    """
    DEVELOPMENT ONLY: Manually complete server creator registration
    Simulates webhook processing when Stripe webhooks aren't available in local dev
    
    SECURITY: Only works in DEBUG mode
    """
    from django.conf import settings
    
    if not settings.DEBUG:
        return Response(
            {'error': 'This endpoint is only available in development'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    from users.models import ServerCreatorApplication, Role, UserRole
    
    user = request.user
    
    try:
        with transaction.atomic():
            # Find user's pending application
            try:
                application = ServerCreatorApplication.objects.select_for_update().get(
                    user=user,
                    status='payment_processing'
                )
            except ServerCreatorApplication.DoesNotExist:
                return Response(
                    {'error': 'No payment processing application found. Status may already be completed.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Activate user (CRITICAL: This enables login)
            user.is_active = True
            user.save(update_fields=['is_active'])
            
            # Grant ServerCreator role (SECURITY: System operation, use force)
            try:
                user.set_role('ServerCreator', changed_by=None, force=True)
            except Exception as e:
                logger.error(f"Failed to grant ServerCreator role: {str(e)}")
                raise
            
            # Update application status
            application.status = 'completed'
            application.payment_completed_at = timezone.now()
            application.save(update_fields=['status', 'payment_completed_at'])
            
            logger.info(f"DEV: Manually completed server creator registration for {user.email}")
            
            return Response({
                'success': True,
                'message': 'Server creator registration completed',
                'user_id': user.id,
                'is_active': user.is_active,
                'current_role': user.user_roles.first().role.name if user.user_roles.first() else None
            })
            
    except Exception as e:
        logger.error(f"DEV: Failed to complete server creator registration: {str(e)}")
        return Response(
            {'error': 'Failed to complete registration. Please contact support.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Server Subscription Views (Existing)


# ServerSubscriptionViewSet removed - using UserSubscription tier to determine server capabilities
