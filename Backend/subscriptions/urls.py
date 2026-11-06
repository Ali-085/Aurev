from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubscriptionPlanViewSet,
    create_checkout_session,
    create_server_creator_checkout_session,
    stripe_webhook,
    cancel_subscription,
    reactivate_subscription,
    get_subscription_status,
    preview_subscription_change,
    confirm_subscription_change,
    dev_complete_server_creator,
    check_server_creator_status,
    process_checkout_session,
)

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plan')

urlpatterns = [
    path('', include(router.urls)),
    # User subscription endpoints
    path('checkout/', create_checkout_session, name='create-checkout'),
    path('server-creator/checkout/', create_server_creator_checkout_session, name='server-creator-checkout'),
    path('webhook/', stripe_webhook, name='stripe-webhook'),
    path('cancel/', cancel_subscription, name='cancel-subscription'),
    path('reactivate/', reactivate_subscription, name='reactivate-subscription'),
    path('status/', get_subscription_status, name='subscription-status'),
    path('preview/', preview_subscription_change, name='preview-subscription-change'),
    path('confirm/', confirm_subscription_change, name='confirm-subscription-change'),
    # Debug endpoints
    path('server-creator/status/', check_server_creator_status, name='check-server-creator-status'),
    path('dev/complete-server-creator/', dev_complete_server_creator, name='dev-complete-server-creator'),
    path('process-session/', process_checkout_session, name='process-checkout-session'),
]
