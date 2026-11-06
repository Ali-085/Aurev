from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.http import HttpResponse
import csv
from core.permissions import IsAdminOrModerator, IsAdminOnly, IsSuperuserOnly
from users.permissions import IsEmailVerified
from audit.models import AuditLog
from .models import PayoutSubmission, PayoutSubmissionDetail, PayoutReviewLog
from .serializers import (
    PayoutSubmissionSerializer,
    PayoutSubmissionCreateSerializer,
    PayoutSubmissionDetailSerializer,
    PayoutReviewLogSerializer,
    PayoutReviewSerializer
)


class PayoutSubmissionViewSet(viewsets.ModelViewSet):
    """ViewSet for PayoutSubmission model."""
    
    queryset = PayoutSubmission.objects.all()
    serializer_class = PayoutSubmissionSerializer
    # Admin actions require elevated permissions (set per-action below)
    permission_classes = [permissions.IsAuthenticated,IsEmailVerified]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'market_category', 'server', 'user']
    search_fields = ['instrument', 'user__username']
    ordering_fields = ['created_at', 'amount', 'payout_date']
    
    def get_queryset(self):
        """
        SECURITY: All users can see payout submissions.
        Review metadata (reviewer, reviewed_at) is protected via serializer.
        """
        # All authenticated users can see all submissions
        # PublicPayoutSubmissionSerializer ensures review fields aren't exposed to regular users
        return PayoutSubmission.objects.all()
    
    def get_serializer_class(self):
        """SECURITY: Use different serializers based on role."""
        if self.action == 'create':
            return PayoutSubmissionCreateSerializer
        
        user = self.request.user
        
        # Superuser/Admin/Moderator get full serializer with review fields
        if user.is_superuser:
            return PayoutSubmissionSerializer
        
        user_role = user.user_roles.first()
        if user_role and user_role.role.name in ['Admin', 'Moderator']:
            return PayoutSubmissionSerializer
        
        # Regular users get public serializer WITHOUT review fields
        from .serializers import PublicPayoutSubmissionSerializer
        return PublicPayoutSubmissionSerializer
    
    def get_permissions(self):
        # Destroy requires Admin only
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsSuperuserOnly()]
        # Update/partial_update for minor edits (Admin only via edit_minor_details action)
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsAdminOnly()]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        """
        Delete a payout submission.
        
        SECURITY: 
        - Restricted to Superusers only (via get_permissions)
        - Logs action to AuditLog
        """
        instance = self.get_object()
        payout_id = instance.id
        user_username = instance.user.username
        
        # Log before deletion in case of error, or we could log after. 
        # Usually good to log the attempt or the success. 
        # Django's delete is atomic-ish if DB supports it.
        
        self.perform_destroy(instance)
        
        # Log successful deletion
        AuditLog.log(
            request.user,
            action_type='delete',
            target_table='payout_submission',
            target_id=payout_id,
            metadata={
                'action': 'payout_submission_deleted',
                'payout_id': payout_id,
                'payout_user': user_username
            }
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def create(self, request, *args, **kwargs):
        """Create a new payout submission with membership validation."""
        from servers.models import Server, ServerMember
        
        # Get server_id from request data
        server_id = request.data.get('server_id')
        if not server_id:
            return Response(
                {'error': 'server_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if server exists
        try:
            server = Server.objects.get(id=server_id)
        except Server.DoesNotExist:
            return Response(
                {'error': 'Server not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is server owner OR server member
        is_owner = server.owner_user == request.user
        is_member = ServerMember.objects.filter(server=server, user=request.user).exists()
        
        if not (is_owner or is_member):
            return Response(
                {'error': 'You must be a member or owner of this server to submit payouts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # SECURITY: Block platform staff (superuser/admin/moderator) from submitting payouts
        # Roles are mutually exclusive - if user has Admin or Moderator role, they cannot submit
        # Server ownership is a relationship, not a role
        if request.user.is_superuser:
            return Response(
                {'error': 'Platform superuser cannot submit payouts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_role = request.user.user_roles.first()  # User has exactly one role
        if user_role and user_role.role.name in ['Admin', 'Moderator']:
            return Response(
                {'error': 'Platform staff (Admin/Moderator) cannot submit payouts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().create(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrModerator])
    def review(self, request, pk=None):
        """
        Review a payout submission.
        
        Uses comprehensive verification service to trigger ALL automatic updates:
        - Server member stats
        - Server analytics (markets, instruments, daily)
        - User analytics
        - Global rankings
        - Server leaderboard
        - Global leaderboard
        
        SECURITY: Uses transaction.atomic() and select_for_update() to prevent race conditions.
        """
        from django.db import transaction
        from .verification_service import PayoutVerificationService
        
        serializer = PayoutReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']
        reason = serializer.validated_data['reason']
        
        # SECURITY: Atomic transaction with row-level locking
        with transaction.atomic():
            # Lock the payout row to prevent concurrent updates
            payout = PayoutSubmission.objects.select_for_update().get(pk=pk)
            
            # Prevent double-approval (idempotency check)
            if payout.status != 'Pending':
                return Response(
                    {'error': f'Payout already {payout.status}. Cannot review again.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Use verification service for comprehensive updates
            if action_type == 'Approved':
                payout = PayoutVerificationService.approve_payout(payout, request.user)
                # Create review log
                PayoutReviewLog.objects.create(
                    payout_submission=payout,
                    reviewer_user=request.user,
                    action='Approved',
                    reason=reason
                )
            elif action_type == 'Rejected':
                payout = PayoutVerificationService.reject_payout(payout, request.user, reason)
            elif action_type == 'MarkedSuspicious':
                payout = PayoutVerificationService.mark_suspicious(payout, request.user, reason)
        
        return Response(
            PayoutSubmissionSerializer(payout).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def my_submissions(self, request):
        """Get current user's payout submissions."""
        payouts = PayoutSubmission.objects.filter(user=request.user)
        serializer = self.get_serializer(payouts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def review_history(self, request, pk=None):
        """Get review history for a payout submission."""
        payout = self.get_object()
        logs = payout.review_logs.all()
        serializer = PayoutReviewLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAdminOrModerator])
    def verification_image(self, request, pk=None):
        """
        SECURITY: Serve private verification image only to admin/moderator/superuser.
        
        This endpoint:
        - Requires admin/moderator/superuser authentication
        - Streams image data directly from R2 (never exposes R2 URL)
        - Logs access in AuditLog for compliance
        - Returns 404 if image doesn't exist
        """
        from django.http import FileResponse, Http404
        from audit.models import AuditLog
        from django.core.files.storage import default_storage
        import mimetypes
        
        payout = self.get_object()
        
        # Check if private verification image exists
        if not payout.private_verification_image:
            raise Http404("No private verification image for this payout")
        
        # SECURITY: Log access for compliance
        AuditLog.log(
            user=request.user,
            action_type='verify',
            target_table='payout_submissions',
            target_id=payout.id,
            metadata={
                'action': 'accessed_private_verification_image',
                'image_path': payout.private_verification_image.name
            }
        )
        
        try:
            # SECURITY: Stream file from R2 without exposing direct URL
            file_path = payout.private_verification_image.name
            file_obj = default_storage.open(file_path, 'rb')
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Stream response
            response = FileResponse(file_obj, content_type=content_type)
            response['Content-Disposition'] = f'inline; filename="{file_path.split("/")[-1]}"'
            return response
            
        except Exception as e:
            # Log error
            AuditLog.log(
                user=request.user,
                action_type='other',
                target_table='payout_submissions',
                target_id=payout.id,
                metadata={
                    'action': 'verification_image_access_failed',
                    'error': str(e)
                }
            )
            raise Http404("Private verification image not accessible")
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAdminOnly])
    def edit_minor_details(self, request, pk=None):
        """
        Edit minor payout details (Admin only).
        
        Admins can edit:
        - Instrument (formatting corrections)
        - Notes/comments
        
        Admins CANNOT edit:
        - Amount (Superuser only)
        - Status (use review action)
        - Server assignment
        - User assignment
        """
        from django.db import transaction
        import re
        
        # SECURITY: Atomic transaction
        with transaction.atomic():
            payout = PayoutSubmission.objects.select_for_update().get(pk=pk)
            
            # Only allow specific fields
            allowed_fields = ['instrument']
            data = {k: v for k, v in request.data.items() if k in allowed_fields}
            
            if not data:
                return Response(
                    {'error': 'No editable fields provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # SECURITY: Validate and sanitize input
            if 'instrument' in data:
                instrument = str(data['instrument']).strip()
                # Only allow alphanumeric, spaces, and common trading symbols
                if not re.match(r'^[A-Za-z0-9\s/\-_.]+$', instrument):
                    return Response(
                        {'error': r'Invalid instrument format. Only alphanumeric and /-_. allowed'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if len(instrument) > 100:
                    return Response(
                        {'error': 'Instrument name too long (max 100 characters)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                data['instrument'] = instrument
            
            # Update allowed fields
            for field, value in data.items():
                setattr(payout, field, value)
            
            payout.save(update_fields=list(data.keys()))
        
        # Log the edit
        from audit.models import AuditLog
        AuditLog.log(
            user=request.user,
            action_type='edit',
            target_table='payout_submissions',
            target_id=payout.id,
            metadata={'edited_fields': list(data.keys()), 'admin': request.user.username}
        )
        
        return Response(
            PayoutSubmissionSerializer(payout).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOnly])
    def reassign_category(self, request, pk=None):
        """
        Reassign payout to correct market category (Admin only).
        
        Admins can correct miscategorized payouts.
        """
        from django.db import transaction
        
        # SECURITY: Validate input from serializer choices
        new_category = request.data.get('market_category')
        
        if not new_category:
            return Response(
                {'error': 'market_category is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # SECURITY: Validate against active market categories from database
        from platform_admin.models import MarketCategory
        valid_market = MarketCategory.objects.filter(name=new_category, is_active=True).exists()
        if not valid_market:
            active_markets = list(MarketCategory.objects.filter(is_active=True).values_list('name', flat=True))
            return Response(
                {'error': f'Invalid category. Must be one of: {active_markets}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # SECURITY: Atomic transaction
        with transaction.atomic():
            payout = PayoutSubmission.objects.select_for_update().get(pk=pk)
            old_category = payout.market_category
            payout.market_category = new_category
            payout.save(update_fields=['market_category'])
        
        # Log the reassignment
        from audit.models import AuditLog
        AuditLog.log(
            user=request.user,
            action_type='reassign',
            target_table='payout_submissions',
            target_id=payout.id,
            metadata={
                'old_category': old_category,
                'new_category': new_category,
                'admin': request.user.username
            }
        )
        
        return Response(
            {
                'message': f'Category reassigned from {old_category} to {new_category}',
                'payout': PayoutSubmissionSerializer(payout).data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOnly])
    def restore_rejected(self, request, pk=None):
        """
        Restore accidentally rejected submission (Admin only).
        
        Sets status back to Pending for re-review.
        """
        from django.db import transaction
        import bleach
        
        # SECURITY: Sanitize reason text (XSS prevention)
        reason = request.data.get('reason', 'Restored by admin for re-review')
        reason = bleach.clean(str(reason).strip(), tags=[], strip=True)[:500]  # Max 500 chars
        
        # SECURITY: Atomic transaction
        with transaction.atomic():
            payout = PayoutSubmission.objects.select_for_update().get(pk=pk)
            
            if payout.status != 'Rejected':
                return Response(
                    {'error': 'Can only restore rejected submissions'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            payout.status = 'Pending'
            payout.reviewer = None
            payout.reviewed_at = None
            payout.save(update_fields=['status', 'reviewer', 'reviewed_at'])
        
        # Create review log
        PayoutReviewLog.objects.create(
            payout_submission=payout,
            reviewer_user=request.user,
            action='Restored',
            reason=reason
        )
        
        return Response(
            {
                'message': 'Submission restored to Pending status',
                'payout': PayoutSubmissionSerializer(payout).data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminOnly])
    def export_data(self, request):
        """
        Download payout data report (Admin only).
        
        Exports filtered payout submissions as CSV for moderation analysis.
        """
        # Apply filters from query params
        queryset = self.filter_queryset(self.get_queryset())
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payouts_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User', 'Server', 'Amount', 'Market Category', 
            'Instrument', 'Status', 'Payout Date', 'Created At', 
            'Reviewer', 'Reviewed At'
        ])
        
        for payout in queryset:
            writer.writerow([
                payout.id,
                payout.user.username,
                payout.server.name,
                payout.amount,
                payout.market_category,
                payout.instrument,
                payout.status,
                payout.payout_date,
                payout.created_at,
                payout.reviewer.username if payout.reviewer else 'N/A',
                payout.reviewed_at or 'N/A'
            ])
        
        return response
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperuserOnly])
    def override_decision(self, request, pk=None):
        """
        Override moderator/admin decision (Superuser only).
        
        Platform superusers can override any approval or rejection.
        Uses verification service to trigger ALL automatic updates on approval.
        """
        from django.db import transaction
        from .verification_service import PayoutVerificationService
        import bleach
        
        # SECURITY: Validate status whitelist
        new_status = request.data.get('status')
        reason = request.data.get('reason', 'Overridden by platform Owner')
        
        if new_status not in ['Approved', 'Rejected', 'Suspicious', 'Pending']:
            return Response(
                {'error': 'Invalid status. Must be: Approved, Rejected, Suspicious, or Pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # SECURITY: Sanitize reason (XSS prevention)
        reason = bleach.clean(str(reason).strip(), tags=[], strip=True)[:500]
        
        # SECURITY: Atomic transaction with row-level locking
        with transaction.atomic():
            payout = PayoutSubmission.objects.select_for_update().get(pk=pk)
            old_status = payout.status
            old_reviewer = payout.reviewer
            
            # If overriding to Approved, use verification service for comprehensive updates
            if new_status == 'Approved' and old_status != 'Approved':
                payout = PayoutVerificationService.approve_payout(payout, request.user)
            
            # If overriding FROM Approved to something else, reverse the approval
            elif old_status == 'Approved' and new_status != 'Approved':
                payout = PayoutVerificationService.reverse_approval(payout, request.user, reason)
                # Then apply the new status
                if new_status == 'Rejected':
                    payout = PayoutVerificationService.reject_payout(payout, request.user, reason)
                elif new_status == 'Suspicious':
                    payout = PayoutVerificationService.mark_suspicious(payout, request.user, reason)
            
            # If not involving Approved status, just update directly
            else:
                payout.status = new_status
                payout.reviewer = request.user
                payout.reviewed_at = timezone.now()
                payout.save(update_fields=['status', 'reviewer', 'reviewed_at'])
        
        # Log the override
        PayoutReviewLog.objects.create(
            payout_submission=payout,
            reviewer_user=request.user,
            action='Overridden',
            reason=f'OWNER OVERRIDE: {reason} (Previous status: {old_status}, Previous reviewer: {old_reviewer.username if old_reviewer else "None"})'
        )
        
        # Also log in audit
        from audit.models import AuditLog
        AuditLog.log(
            user=request.user,
            action_type='override',
            target_table='payout_submissions',
            target_id=payout.id,
            metadata={
                'old_status': old_status,
                'new_status': new_status,
                'old_reviewer': old_reviewer.username if old_reviewer else None,
                'reason': reason
            }
        )
        
        return Response(
            {
                'message': 'Decision overridden successfully',
                'old_status': old_status,
                'new_status': new_status,
                'payout': PayoutSubmissionSerializer(payout).data
            },
            status=status.HTTP_200_OK
        )


class PayoutSubmissionDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for PayoutSubmissionDetail model."""
    
    queryset = PayoutSubmissionDetail.objects.all()
    serializer_class = PayoutSubmissionDetailSerializer
    # SECURITY: Payout details are sensitive - require authentication + email verification
    permission_classes = [permissions.IsAuthenticated, IsEmailVerified]


class PayoutReviewLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for PayoutReviewLog model."""
    
    queryset = PayoutReviewLog.objects.all()
    serializer_class = PayoutReviewLogSerializer
    # SECURITY: IsAdminOrModerator now checks authentication + email verification internally
    permission_classes = [IsAdminOrModerator]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['payout_submission', 'reviewer_user', 'action']
    ordering_fields = ['created_at']
