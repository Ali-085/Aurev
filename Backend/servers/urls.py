from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServerViewSet, ServerMemberViewSet
from .server_view import ServerPublicViewSet
from users.avatar_views import upload_server_logo, remove_server_logo

# Main server management router
router = DefaultRouter()
router.register(r'', ServerViewSet, basename='server')
router.register(r'members', ServerMemberViewSet, basename='server-member')

# Public server view router (for public showcase)
public_router = DefaultRouter()
public_router.register(r'view', ServerPublicViewSet, basename='server-view')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(public_router.urls)),
    
    # Logo upload endpoints
    path('<uuid:server_id>/logo/upload/', upload_server_logo, name='upload_server_logo'),
    path('<uuid:server_id>/logo/', remove_server_logo, name='remove_server_logo'),
]
