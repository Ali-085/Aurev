"""
User Query Optimization Utilities

Provides optimized querysets and annotations for user-related queries
to prevent N+1 problems when serializing users with roles and permissions.
"""

from django.db.models import Exists, OuterRef, Prefetch
from servers.models import ServerMember, Server
from users.models import UserRole


def optimize_user_queryset(queryset):
    """
    Optimize user queryset to prevent N+1 queries when serializing.
    
    Usage:
        users = User.objects.all()
        users = optimize_user_queryset(users)
        serializer = UserSerializer(users, many=True)
    
    This will:
    - Prefetch user roles (for internal role checks only)
    - Annotate is_member status (for permissions.is_member)
    - Annotate is_owner status (for permissions.is_owner)
    """
    return queryset.prefetch_related(
        Prefetch('user_roles', queryset=UserRole.objects.select_related('role'))
    ).annotate(
        has_server_membership=Exists(
            ServerMember.objects.filter(user=OuterRef('pk'))
        ),
        owns_server=Exists(
            Server.objects.filter(owner_user=OuterRef('pk'))
        )
    )


def get_user_permissions(user):
    """
    Calculate user capabilities based on internal roles and relationships.
    Returns ONLY what the user can do, NOT their role names or hierarchy.
    Optimized version that uses annotations if available.
    
    SECURITY: This is the ONLY place where internal roles are checked.
    Frontend receives generic capability flags (can_review_content, can_manage_content)
    but never sees the actual role names (Moderator, Admin) or privilege hierarchy.
    
    Args:
        user: User instance (may have annotations from optimize_user_queryset)
    
    Returns:
        dict: Capability flags showing what user can do (not their roles)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Get roles efficiently (internal use only - never exposed to frontend)
    if hasattr(user, '_prefetched_objects_cache') and 'user_roles' in user._prefetched_objects_cache:
        roles = [ur.role.name for ur in user.user_roles.all()]
    else:
        roles = list(user.user_roles.values_list('role__name', flat=True))
    
    # Use annotations if available (from optimize_user_queryset)
    if hasattr(user, 'has_server_membership'):
        is_trader = user.has_server_membership
    else:
        is_trader = ServerMember.objects.filter(user=user).exists()
    
    if hasattr(user, 'owns_server'):
        is_server_owner = user.owns_server
    else:
        is_server_owner = Server.objects.filter(owner_user=user).exists()
    
    # Internal role checks (hierarchical - higher roles inherit lower permissions)
    has_moderator_role = 'Moderator' in roles
    has_admin_role = 'Admin' in roles
    has_superuser_role = user.is_superuser
    has_server_creator_role = 'ServerCreator' in roles
    
    # DEBUG logging
    logger.info(f"🔍 Permission check for user {user.email}:")
    logger.info(f"   is_superuser (DB): {user.is_superuser}")
    logger.info(f"   is_active (DB): {user.is_active}")
    logger.info(f"   email_verified (DB): {user.email_verified}")
    logger.info(f"   roles (DB): {roles}")
    logger.info(f"   has_superuser_role (computed): {has_superuser_role}")
    
    # Return ONLY capabilities (what user CAN do), never role names
    # Use generic names that don't reveal internal privilege hierarchy
    permissions = {
        # Subscription-based capabilities
        'can_create_content': has_server_creator_role,
        
        # Platform staff capabilities (generic names)
        'can_review_content': has_moderator_role or has_admin_role or has_superuser_role,
        'can_manage_content': has_admin_role or has_superuser_role,
        'can_access_platform': has_superuser_role,
        
        # Relationship-based status
        'is_member': is_trader,
        'is_creator': is_server_owner,
        
        # Generic staff check (for UI that needs to know if user is any type of staff)
        'has_elevated_access': has_moderator_role or has_admin_role or has_superuser_role,
    }
    
    logger.info(f"   Permissions returned: {permissions}")
    return permissions
