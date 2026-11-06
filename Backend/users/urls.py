from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    RoleViewSet,
    UserRoleViewSet,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    logout_view,
    UserRegistrationView,
    current_user_view,
    public_trader_profile_view,
    verify_email_view,
    resend_verification_view,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
)
from .avatar_views import (
    upload_user_avatar,
    remove_user_avatar,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'user-roles', UserRoleViewSet, basename='user-role')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', CookieTokenObtainPairView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('me/', current_user_view, name='current_user'),
    path('trader/<uuid:user_id>/public/', public_trader_profile_view, name='public_trader_profile'),
    path('verify/', verify_email_view, name='verify_email'),
    path('resend-verification/', resend_verification_view, name='resend_verification'),
    
    # Password reset endpoints
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Avatar upload endpoints
    path('avatar/upload/', upload_user_avatar, name='upload_avatar'),
    path('avatar/', remove_user_avatar, name='remove_avatar'),
]
