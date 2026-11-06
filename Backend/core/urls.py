"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # API endpoints
    path('api/auth/', include('users.urls')),
    path('api/servers/', include('servers.urls')),
    path('api/payouts/', include('payouts.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/audit/', include('audit.urls')),
    path('api/platform-admin/', include('platform_admin.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
