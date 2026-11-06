from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ServerAnalyticsDailyViewSet,
    GlobalAnalyticsDailyViewSet,
    ServerRankingViewSet
)
from . import analytics_views, trader_analytics_views, server_owner_analytics_views
from .recent_payouts_view import recent_payouts_feed

router = DefaultRouter()
router.register(r'server-daily', ServerAnalyticsDailyViewSet, basename='server-analytics')
router.register(r'global-daily', GlobalAnalyticsDailyViewSet, basename='global-analytics')
router.register(r'rankings', ServerRankingViewSet, basename='server-ranking')

urlpatterns = [
    path('', include(router.urls)),
    # Analytics dashboard endpoints
    path('global-overview/', analytics_views.global_overview, name='analytics-global-overview'),
    path('global-timeseries/', analytics_views.global_timeseries, name='analytics-global-timeseries'),
    path('market-detail/', analytics_views.market_detail, name='analytics-market-detail'),
    path('monthly-awards/', analytics_views.monthly_awards, name='analytics-monthly-awards'),
    path('top-servers/', analytics_views.top_servers_leaderboard, name='top-servers-leaderboard'),
    # Public server analytics
    path('server/<uuid:server_id>/public/', analytics_views.public_server_analytics, name='public-server-analytics'),
    # Trader profile analytics
    path('trader/profile/', trader_analytics_views.trader_profile_analytics, name='trader-profile-analytics'),
    # Server owner analytics
    path('server-owner/servers/', server_owner_analytics_views.user_owned_servers, name='owner-servers'),
    path('server-owner/dashboard/<uuid:server_id>/', server_owner_analytics_views.server_owner_dashboard, name='server-owner-dashboard'),
    # Recent payouts feed
    path('recent-payouts/', recent_payouts_feed, name='recent-payouts-feed'),
]
