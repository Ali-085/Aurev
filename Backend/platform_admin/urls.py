from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .admin_dashboard import AdminDashboardViewSet
from .moderator_dashboard import ModeratorDashboardViewSet
from . import subscription_management

# Admin Dashboard Router
admin_router = DefaultRouter()
admin_router.register(r'admin-dashboard', AdminDashboardViewSet, basename='admin-dashboard')

# Moderator Dashboard Router
moderator_router = DefaultRouter()
moderator_router.register(r'moderator-dashboard', ModeratorDashboardViewSet, basename='moderator-dashboard')

urlpatterns = [
    # Overview
    path('overview/', views.platform_overview, name='platform_overview'),
    
    # Server Management
    path('servers/', views.manage_servers, name='manage_servers'),
    path('servers/<uuid:server_id>/', views.manage_server_detail, name='manage_server_detail'),
    
    # User Management
    path('users/', views.manage_users, name='manage_users'),
    path('users/<uuid:user_id>/', views.manage_user_detail, name='manage_user_detail'),
    path('users/<uuid:user_id>/ban/', views.ban_user, name='ban_user'),
    path('users/<uuid:user_id>/unban/', views.unban_user, name='unban_user'),
    
    # Payout Management
    path('payouts/', views.global_payouts, name='global_payouts'),
    path('payouts/<int:payout_id>/action/', views.quick_payout_action, name='quick_payout_action'),
    
    # Global Configuration
    path('markets/', views.market_categories_list, name='market_categories_list'),
    path('markets/<int:pk>/', views.market_category_detail, name='market_category_detail'),
    path('categories/', views.trading_categories_list, name='trading_categories_list'),
    path('categories/<int:pk>/', views.trading_category_detail, name='trading_category_detail'),
    path('limits/', views.manage_limits, name='manage_limits'),
    path('platforms/', views.platform_choice_list, name='platform_choice_list'),
    path('platforms/<int:pk>/', views.platform_choice_detail, name='platform_choice_detail'),
    path('prop-firms/', views.prop_firms_list, name='prop_firms_list'),
    path('prop-firms/<int:pk>/', views.prop_firm_detail, name='prop_firm_detail'),
    
    # Audit Logs
    path('audit-logs/', views.audit_logs, name='audit_logs'),
    
    # Billing
    path('billing/', views.billing_overview, name='billing_overview'),
    
    # Subscription Management
    path('users/<uuid:user_id>/subscription-status/', views.get_subscription_status, name='get_subscription_status'),
    path('users/<uuid:user_id>/grant-subscription/', views.grant_subscription, name='grant_subscription'),
    
    # Subscription Plans Management (Superuser only)
    path('subscription-plans/', subscription_management.subscription_plans_list, name='subscription_plans_list'),
    path('subscription-plans/<int:plan_id>/', subscription_management.subscription_plan_detail, name='subscription_plan_detail'),
    
    # Admin Dashboard API
    path('', include(admin_router.urls)),
    
    # Moderator Dashboard API
    path('', include(moderator_router.urls)),
]
