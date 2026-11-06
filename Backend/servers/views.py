from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.http import HttpResponse
from django.utils import timezone
import csv
import logging
from core.permissions import IsSuperuserOnly, IsAdminOnly
from users.permissions import IsEmailVerified
from .models import Server, ServerMember
from .serializers import (
    ServerSerializer,
    ServerCreateSerializer,
    ServerUpdateSerializer,
    ServerMemberSerializer
)

logger = logging.getLogger(__name__)



class IsServerOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow server owners to edit.
    
    Note: Server CREATION is protected by role + subscription checks in enforcement.py
    This permission is only for editing EXISTING servers owned by the user.
    """
    
    def has_object_permission(self, request, view, obj):
        # Allow read access for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For write operations, check authentication and email verification
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SECURITY: Check email verification AND full activation
        # Server creators must complete payment to manage servers
        if not request.user.email_verified or not request.user.is_active:
            return False
        
        return obj.owner_user == request.user


class ServerViewSet(viewsets.ModelViewSet):
    """ViewSet for Server model."""
    
    queryset = Server.objects.all()  # Owners/Admins need to see suspended servers
    serializer_class = ServerSerializer
    # SECURITY: Allow anonymous read access for server browsing
    # For write operations: IsServerOwnerOrReadOnly checks auth + email verification + ownership internally
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsServerOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['platform', 'is_verified', 'suspended']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    lookup_field = 'pk'
    
    def get_queryset(self):
        """
        Filter servers based on user role:
        - Platform admins: See all servers (including suspended and soft-deleted)
        - Server owners: See their own servers (including soft-deleted during grace period)
        - Regular users: Only see active, non-suspended, non-deleted servers
        """
        try:
            queryset = super().get_queryset()
            
            # Platform admins see all servers (including suspended and soft-deleted)
            if self.request.user.is_authenticated:
                if (self.request.user.is_superuser or 
                    self.request.user.user_roles.filter(role__name='Admin').exists()):
                    return queryset
                
                # Server owners see their own servers (including soft-deleted during grace period)
                # This allows them to see cancellation status and reactivate
                if self.action in ['list', 'retrieve']:
                    owned_servers = queryset.filter(owner_user=self.request.user)
                    public_servers = queryset.filter(suspended=False, is_deleted=False)
                    return (owned_servers | public_servers).distinct()
            
            # Regular users only see active, non-suspended, non-deleted servers
            return queryset.filter(suspended=False, is_deleted=False)
        except Exception as e:
            logger.exception(f"Error in get_queryset for user {self.request.user if self.request.user.is_authenticated else 'Anonymous'}")
            # Return safe default queryset
            return Server.objects.filter(suspended=False, is_deleted=False)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ServerCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ServerUpdateSerializer
        return ServerSerializer
    
    def get_permissions(self):
        # SECURITY: IsSuperuserOnly now checks authentication + email verification internally
        # Verify/suspend/unsuspend require Superuser permission
        if self.action in ['verify', 'suspend', 'unsuspend']:
            return [IsSuperuserOnly()]
        return super().get_permissions()
    
    def create(self, request, *args, **kwargs):
        """
        Create a new server with payment verification.
        
        SECURITY: Check if user has completed payment (for server creators)
        """
        try:
            # Check if user has pending payment
            from users.models import ServerCreatorApplication
            
            pending_app = ServerCreatorApplication.objects.filter(
                user=request.user,
                status='pending_payment'
            ).first()
            
            if pending_app:
                return Response(
                    {
                        'error': 'Please complete payment to create your server.',
                        'error_code': 'PAYMENT_REQUIRED',
                        'redirect_to': '/server-creator/checkout',
                        'application_id': pending_app.pk
                    },
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
            
            # Check if user has ServerCreator role
            user_role = request.user.user_roles.first()
            if not user_role or user_role.role.name != 'ServerCreator':
                return Response(
                    {
                        'error': 'Only server creators can create servers. Please upgrade your account.',
                        'error_code': 'INSUFFICIENT_PERMISSIONS'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Proceed with normal creation
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.exception(f"Error creating server for user {request.user.email}")
            return Response(
                {'error': 'Failed to create server. Please try again or contact support.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a server as a member with capacity enforcement."""
        from platform_admin.enforcement import enforce_member_limits
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        # SECURITY: Block platform staff from joining servers
        # Roles are mutually exclusive - users have exactly one role
        if request.user.is_superuser:
            return Response(
                {'error': 'Platform superuser cannot join servers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_role = request.user.user_roles.first()  # User has exactly one role
        if user_role and user_role.role.name in ['Admin', 'Moderator']:
            return Response(
                {'error': 'Platform staff (Admin/Moderator) cannot join servers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        server = self.get_object()
        
        # ENFORCE PLATFORM LIMITS: Check if server has reached member capacity
        try:
            enforce_member_limits(server)
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        member, created = ServerMember.objects.get_or_create(
            server=server,
            user=request.user
        )
        
        if created:
            return Response(
                {'message': 'Successfully joined server'},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {'message': 'Already a member of this server'},
                status=status.HTTP_200_OK
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsEmailVerified])
    def leave(self, request, pk=None):
        """
        Leave a server as a trader/member.
        
        SECURITY:
        - Requires authentication and email verification
        - Server creators/owners cannot leave their own server
        - Idempotent: multiple requests return consistent state
        - Transactional: all DB changes are atomic
        - Creates audit log entry
        
        BUSINESS RULES:
        - Only traders can leave servers
        - Platform staff (Admin, Moderator, Superuser) cannot leave
        - Server owners must transfer or delete server instead
        - Removes all server-specific permissions and access
        """
        from django.db import transaction
        from audit.models import AuditLog
        
        server = self.get_object()
        
        # SECURITY: Block platform staff from leaving servers
        if request.user.is_superuser:
            return Response(
                {'error': 'Platform superuser cannot leave servers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_role = request.user.user_roles.first()  # User has exactly one role
        if user_role and user_role.role.name in ['Admin', 'Moderator']:
            return Response(
                {'error': 'Platform staff (Admin/Moderator) cannot leave servers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # BUSINESS RULE: Server owners cannot leave their own server
        if server.owner_user == request.user:
            return Response(
                {
                    'error': 'Server owners cannot leave their own server',
                    'detail': 'Please transfer ownership or delete the server instead'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # IDEMPOTENT: Check if already not a member
        try:
            member = ServerMember.objects.get(server=server, user=request.user)
        except ServerMember.DoesNotExist:
            # Already not a member - return success for idempotency
            return Response(
                {
                    'message': 'Not a member of this server',
                    'detail': 'You have already left this server or were never a member'
                },
                status=status.HTTP_200_OK
            )
        
        # TRANSACTIONAL: Remove membership and log action atomically
        try:
            with transaction.atomic():
                # Store member info for audit log before deletion
                member_data = {
                    'server_id': str(server.id),
                    'server_name': server.name,
                    'user_id': str(request.user.id),
                    'username': request.user.username,
                    'joined_at': member.joined_at.isoformat(),
                    'total_verified_payouts': float(member.total_verified_payouts),
                    'total_submissions': member.total_submissions,
                    'last_submission_at': member.last_submission_at.isoformat() if member.last_submission_at else None
                }
                
                # Remove membership (cascades to remove permissions/roles)
                member.delete()
                
                # AUDIT LOG: Track leave_server action
                AuditLog.log(
                    user=request.user,
                    action_type='delete',  # Using 'delete' as it's removing membership
                    target_table='server_members',
                    target_id=f"{server.id}:{request.user.id}",
                    metadata={
                        'action': 'leave_server',
                        **member_data
                    }
                )
                
                logger.info(
                    f"User {request.user.username} (ID: {request.user.id}) left server "
                    f"{server.name} (ID: {server.id})"
                )
            
            return Response(
                {
                    'message': 'Successfully left server',
                    'server_name': server.name
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(
                f"Error leaving server {server.id} for user {request.user.id}: {str(e)}",
                exc_info=True
            )
            return Response(
                {
                    'error': 'Failed to leave server',
                    'detail': 'An unexpected error occurred. Please try again.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get server members leaderboard with privacy masking."""
        from utils.privacy import get_public_trader_view, mask_trader_stats
        
        server = self.get_object()
        members = server.members.select_related('user').all()
        
        members_data = []
        for member in members:
            trader_view = get_public_trader_view(member.user, requesting_user=request.user, has_valid_token=False)
            
            stats = {
                'total_verified_payouts': float(member.total_verified_payouts),
                'total_submissions': member.total_submissions,
                'last_submission_at': member.last_submission_at.isoformat() if member.last_submission_at else None
            }
            
            # Determine if stats should be masked based on privacy and user access
            is_owner = request.user.is_authenticated and request.user.id == member.user.id
            should_mask = trader_view['is_private'] and not is_owner
            masked_stats = mask_trader_stats(stats, should_mask)
            
            trader_id = trader_view['id']
            members_data.append({
                'id': str(member.id),
                'user': {
                    'id': trader_view['id'],
                    'username': trader_view['username'],
                    'profile_url': f'/trader/{trader_id}/public',
                    'avatar_url': trader_view.get('avatar_url'),
                    'is_private': trader_view['is_private']
                },
                'joined_at': member.joined_at.isoformat(),
                **masked_stats
            })
        
        return Response(members_data)
    
    @action(detail=False, methods=['get'])
    def my_servers(self, request):
        """Get servers owned by current user."""
        servers = Server.objects.filter(owner_user=request.user)
        serializer = self.get_serializer(servers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperuserOnly])
    def verify(self, request, pk=None):
        """
        Verify a server (Platform Superuser only).
        
        Server verification is a critical trust signal.
        Only platform superusers can grant verification status.
        """
        server = self.get_object()
        server.is_verified = True
        server.save()
        
        return Response(
            {'message': f'Server "{server.name}" has been suspended'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperuserOnly])
    def suspend(self, request, pk=None):
        """
        Suspend a server (Platform Superuser only).
        
        Server suspension removes it from listings.
        Only platform Owners can suspend servers.
        """
        from django.db import transaction
        import bleach
        
        # SECURITY: Sanitize reason (XSS prevention)
        reason = request.data.get('reason', 'Violation of platform policies')
        reason = bleach.clean(str(reason).strip(), tags=[], strip=True)[:500]
        
        # SECURITY: Atomic transaction
        with transaction.atomic():
            server = type(self).queryset.model.objects.select_for_update().get(pk=pk)
            server.suspended = True
            server.suspension_reason = reason
            server.save(update_fields=['suspended', 'suspension_reason'])
        
        return Response(
            {'message': f'Server "{server.name}" has been suspended', 'reason': reason},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperuserOnly])
    def unsuspend(self, request, pk=None):
        """
        Unsuspend a server (Platform Superuser only).
        """
        server = self.get_object()
        
        server.suspended = False
        server.suspension_reason = ''
        server.save()
        
        return Response(
            {'message': f'Server "{server.name}" has been unsuspended'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOnly])
    def pause_submissions(self, request, pk=None):
        """
        Pause payout submissions on a server (Admin only).
        
        Admins can temporarily pause submissions for moderation purposes.
        """
        from django.db import transaction
        import bleach
        
        # SECURITY: Sanitize reason (XSS prevention)
        reason = request.data.get('reason', 'Under moderation review')
        reason = bleach.clean(str(reason).strip(), tags=[], strip=True)[:500]
        
        # SECURITY: Atomic transaction
        with transaction.atomic():
            server = type(self).queryset.model.objects.select_for_update().get(pk=pk)
            server.payout_submissions_paused = True
            server.paused_by = request.user
            server.paused_at = timezone.now()
            server.save(update_fields=['payout_submissions_paused', 'paused_by', 'paused_at'])
        
        return Response(
            {
                'message': f'Payout submissions paused for "{server.name}"',
                'reason': reason,
                'paused_by': request.user.username
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOnly])
    def unpause_submissions(self, request, pk=None):
        """
        Unpause payout submissions on a server (Admin only).
        """
        server = self.get_object()
        
        server.payout_submissions_paused = False
        server.paused_by = None
        server.paused_at = None
        server.save()
        
        return Response(
            {'message': f'Payout submissions resumed for "{server.name}"'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAdminOnly])
    def export_data(self, request, pk=None):
        """
        Download server data report (Admin only).
        
        Exports server members and payout statistics as CSV.
        """
        server = self.get_object()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{server.id}_data.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Username', 'Joined At', 'Total Verified Payouts', 'Total Submissions', 'Last Submission'])
        
        for member in server.members.select_related('user').all():
            writer.writerow([
                member.user.username,
                member.joined_at,
                member.total_verified_payouts,
                member.total_submissions,
                member.last_submission_at or 'N/A'
            ])
        
        return response
    
 
class ServerMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ServerMember model."""
    
    queryset = ServerMember.objects.all()
    serializer_class = ServerMemberSerializer
    # SECURITY: Allow anonymous read for public leaderboards, but require email verification for authenticated access
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsEmailVerified]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['server', 'user']
    ordering_fields = ['total_verified_payouts', 'total_submissions', 'joined_at']
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsEmailVerified])
    def my_servers(self, request):
        """
        Get all servers the authenticated user owns or is a member of.
        Returns server details with membership/ownership information.
        
        SECURITY:
        - Requires authentication and email verification
        - Only returns user's own servers and memberships
        """
        from django.db.models import Q
        
        servers_data = []
        
        # Get servers owned by user
        owned_servers = Server.objects.filter(
            owner_user=request.user
        ).exclude(
            Q(suspended=True) | Q(is_deleted=True)
        )
        
        for server in owned_servers:
            server_serializer = ServerSerializer(server, context={'request': request})
            server_data = server_serializer.data
            server_data['is_owner'] = True
            server_data['membership'] = None  # Owner doesn't need membership record
            servers_data.append(server_data)
        
        # Get servers where user is a member
        memberships = ServerMember.objects.filter(
            user=request.user
        ).select_related('server', 'server__platform', 'server__owner_user').order_by('-joined_at')
        
        for membership in memberships:
            server = membership.server
            
            # Skip suspended or deleted servers
            if server.suspended or server.is_deleted:
                continue
            
            # Skip if already included as owner
            if server.owner_user == request.user:
                continue
            
            # Build server data with membership info
            server_serializer = ServerSerializer(server, context={'request': request})
            server_data = server_serializer.data
            server_data['is_owner'] = False
            
            # Add membership-specific data
            server_data['membership'] = {
                'joined_at': membership.joined_at.isoformat(),
                'total_verified_payouts': float(membership.total_verified_payouts),
                'total_submissions': membership.total_submissions,
                'last_submission_at': membership.last_submission_at.isoformat() if membership.last_submission_at else None
            }
            
            servers_data.append(server_data)
        
        return Response(servers_data, status=status.HTTP_200_OK)
