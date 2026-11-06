from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import AuditLog
from .serializers import AuditLogSerializer
from users.permissions import IsEmailVerified


class IsSuperuserOnlyAuditAccess(permissions.BasePermission):
    """
    Custom permission for audit logs - SUPERUSER ONLY.
    
    CRITICAL REQUIREMENT:
    Only platform superusers can access audit/security logs.
    Admins and Moderators CANNOT view audit logs.
    
    Audit logs track:
    - Who approved/rejected payouts
    - Who edited data
    - Who created/deleted accounts
    - Timestamps of all actions
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SECURITY: Check email verification
        if not request.user.email_verified:
            return False
        
        # ONLY superusers have access to audit logs
        return request.user.is_superuser


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for AuditLog model - SUPERUSER ONLY.
    
    Security/audit logs are restricted to platform superusers only.
    Admins, Moderators, and Server Owners CANNOT access these logs.
    """
    
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    # SECURITY: IsSuperuserOnlyAuditAccess now checks authentication + email verification internally
    permission_classes = [IsSuperuserOnlyAuditAccess]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['action_type', 'target_table', 'actor_user']
    search_fields = ['target_table', 'target_id', 'metadata']
    ordering_fields = ['created_at', 'action_type']
    
    # Owner sees ALL logs - no filtering needed
