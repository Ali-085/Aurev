"""
Moderator Dashboard ViewSet

Provides MINIMAL permissions for verification workers.
Moderators can ONLY review payouts - nothing else.

Moderator Permissions:
✓ Review payout submissions (approve/reject)
✓ Mark submissions as fraudulent
✓ Add rejection reason/comment
✓ View server analytics (verification context only)
✓ View member profiles (submission history)
✓ Access payout logs

Moderator Restrictions (CRITICAL):
✗ Delete ANYTHING
✗ Edit ANY payout details
✗ Modify server totals
✗ Modify rankings
✗ Add/remove users or servers
✗ Change settings or categories
✗ Access global analytics
✗ Access admin settings
✗ Create/delete accounts
✗ Export full data
✗ See platform financials

Moderators = VERIFICATION WORKERS ONLY
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from core.permissions import IsModeratorOnly
from users.permissions import IsEmailVerified
from payouts.models import PayoutSubmission, PayoutReviewLog
from servers.models import Server, ServerMember
from django.contrib.auth import get_user_model

User = get_user_model()


class ModeratorDashboardViewSet(viewsets.ViewSet):
    """
    Moderator Dashboard - Verification Workers Only.
    
    Moderators are RESTRICTED to payout review tasks only.
    They cannot edit, delete, or access any admin features.
    """
    # SECURITY: IsModeratorOnly now checks authentication + email verification internally
    permission_classes = [IsModeratorOnly]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Moderator dashboard overview - limited to review metrics.
        
        Returns:
        - Pending submissions count (queue size)
        - My reviews today
        - My total reviews (lifetime)
        - My approval rate
        """
        user = request.user
        
        # Pending queue
        pending_count = PayoutSubmission.objects.filter(status='Pending').count()
        
        # My reviews today
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        my_reviews_today = PayoutSubmission.objects.filter(
            reviewer=user,
            reviewed_at__gte=today_start
        ).count()
        
        # My total reviews (lifetime)
        my_total_reviews = PayoutSubmission.objects.filter(reviewer=user).count()
        
        # My approval rate
        my_approvals = PayoutSubmission.objects.filter(
            reviewer=user,
            status='Approved'
        ).count()
        my_rejections = PayoutSubmission.objects.filter(
            reviewer=user,
            status='Rejected'
        ).count()
        
        approval_rate = 0
        if my_total_reviews > 0:
            approval_rate = round((my_approvals / my_total_reviews) * 100, 1)
        
        return Response({
            'pending_queue': pending_count,
            'my_reviews_today': my_reviews_today,
            'my_total_reviews': my_total_reviews,
            'my_approvals': my_approvals,
            'my_rejections': my_rejections,
            'my_approval_rate': approval_rate
        })
    
    @action(detail=False, methods=['get'])
    def review_queue(self, request):
        """
        Get pending payouts for review (queue sorted by oldest first).
        
        FIFO: First In, First Out
        Oldest submissions reviewed first to ensure fairness.
        
        Query params:
        - limit: Number of submissions to fetch (default 20, max 50)
        """
        limit = int(request.query_params.get('limit', 20))
        limit = min(limit, 50)  # Max 50 at a time
        
        queryset = PayoutSubmission.objects.filter(
            status='Pending'
        ).select_related(
            'user', 'server'
        ).order_by('created_at')[:limit]  # Oldest first
        
        from payouts.serializers import PayoutSubmissionSerializer
        serializer = PayoutSubmissionSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def submission_detail(self, request, pk=None):
        """
        Get detailed submission for review.
        
        Includes:
        - Full submission data
        - Screenshot URL
        - User submission history (for context)
        - Server stats (for verification)
        - Review history (if re-reviewing)
        """
        try:
            submission = PayoutSubmission.objects.select_related(
                'user', 'server', 'reviewer'
            ).get(pk=pk)
        except PayoutSubmission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=404)
        
        # User submission history (last 10)
        user_history = PayoutSubmission.objects.filter(
            user=submission.user
        ).exclude(id=submission.id).order_by('-created_at')[:10]
        
        user_history_data = [{
            'id': s.id,
            'amount': float(s.amount),
            'status': s.status,
            'market_category': s.market_category,
            'created_at': s.created_at,
            'reviewed_at': s.reviewed_at
        } for s in user_history]
        
        # User stats
        user_total_submissions = PayoutSubmission.objects.filter(
            user=submission.user
        ).count()
        user_approved = PayoutSubmission.objects.filter(
            user=submission.user,
            status='Approved'
        ).count()
        user_rejected = PayoutSubmission.objects.filter(
            user=submission.user,
            status='Rejected'
        ).count()
        
        # Server stats (context for verification)
        server_stats = {
            'total_submissions': PayoutSubmission.objects.filter(
                server=submission.server
            ).count(),
            'approved': PayoutSubmission.objects.filter(
                server=submission.server,
                status='Approved'
            ).count(),
            'rejected': PayoutSubmission.objects.filter(
                server=submission.server,
                status='Rejected'
            ).count()
        }
        
        # Review history (if re-reviewing)
        review_logs = PayoutReviewLog.objects.filter(
            payout_submission=submission
        ).select_related('reviewer_user').order_by('-created_at')
        
        review_history_data = [{
            'reviewer': log.reviewer_user.username,
            'action': log.action,
            'reason': log.reason,
            'created_at': log.created_at
        } for log in review_logs]
        
        from payouts.serializers import PayoutSubmissionSerializer
        
        return Response({
            'submission': PayoutSubmissionSerializer(submission).data,
            'user_stats': {
                'total_submissions': user_total_submissions,
                'approved': user_approved,
                'rejected': user_rejected,
                'approval_rate': round((user_approved / user_total_submissions * 100) if user_total_submissions > 0 else 0, 1)
            },
            'user_history': user_history_data,
            'server_stats': server_stats,
            'review_history': review_history_data
        })
    
    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """
        Get my review history (moderator's own reviews).
        
        Query params:
        - status: Filter by status (Approved/Rejected/Suspicious)
        - limit: Number of results (default 50, max 100)
        """
        user = request.user
        status_filter = request.query_params.get('status')
        limit = int(request.query_params.get('limit', 50))
        limit = min(limit, 100)
        
        queryset = PayoutSubmission.objects.filter(
            reviewer=user
        ).select_related('user', 'server')
        
        if status_filter and status_filter in ['Approved', 'Rejected', 'Suspicious']:
            queryset = queryset.filter(status=status_filter)
        
        queryset = queryset.order_by('-reviewed_at')[:limit]
        
        from payouts.serializers import PayoutSubmissionSerializer
        serializer = PayoutSubmissionSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def server_context(self, request):
        """
        Get server context for verification (read-only).
        
        Query params:
        - server_id: Server ID to view
        
        Shows basic server stats for fraud detection context.
        RESTRICTION: Moderators cannot modify anything.
        """
        server_id = request.query_params.get('server_id')
        if not server_id:
            return Response({'error': 'server_id required'}, status=400)
        
        try:
            server = Server.objects.get(id=server_id)
        except Server.DoesNotExist:
            return Response({'error': 'Server not found'}, status=404)
        
        # Basic server info (read-only)
        stats = {
            'server': {
                'id': server.id,
                'name': server.name,
                'platform': server.platform,
                'is_verified': server.is_verified,
                'suspended': server.suspended
            },
            'submission_stats': {
                'total': PayoutSubmission.objects.filter(server=server).count(),
                'pending': PayoutSubmission.objects.filter(server=server, status='Pending').count(),
                'approved': PayoutSubmission.objects.filter(server=server, status='Approved').count(),
                'rejected': PayoutSubmission.objects.filter(server=server, status='Rejected').count(),
                'suspicious': PayoutSubmission.objects.filter(server=server, status='Suspicious').count()
            },
            'member_count': ServerMember.objects.filter(server=server).count()
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def member_context(self, request):
        """
        Get member context for verification (read-only).
        
        Query params:
        - user_id: User ID to view
        
        Shows submission history for fraud detection.
        RESTRICTION: Moderators cannot modify anything.
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=400)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        
        # Submission stats
        total_submissions = PayoutSubmission.objects.filter(user=user).count()
        approved = PayoutSubmission.objects.filter(user=user, status='Approved').count()
        rejected = PayoutSubmission.objects.filter(user=user, status='Rejected').count()
        suspicious = PayoutSubmission.objects.filter(user=user, status='Suspicious').count()
        
        # Recent submissions (last 20)
        recent = PayoutSubmission.objects.filter(
            user=user
        ).select_related('server').order_by('-created_at')[:20]
        
        recent_data = [{
            'id': s.id,
            'amount': float(s.amount),
            'status': s.status,
            'market_category': s.market_category,
            'server_name': s.server.name,
            'created_at': s.created_at,
            'reviewed_at': s.reviewed_at
        } for s in recent]
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'date_joined': user.date_joined
            },
            'stats': {
                'total_submissions': total_submissions,
                'approved': approved,
                'rejected': rejected,
                'suspicious': suspicious,
                'approval_rate': round((approved / total_submissions * 100) if total_submissions > 0 else 0, 1)
            },
            'recent_submissions': recent_data
        })
    
    @action(detail=False, methods=['get'])
    def payout_logs(self, request):
        """
        View payout submission logs (read-only).
        
        Query params:
        - submission_id: Payout submission ID
        
        Shows complete review history for a submission.
        RESTRICTION: View only, no editing.
        """
        submission_id = request.query_params.get('submission_id')
        if not submission_id:
            return Response({'error': 'submission_id required'}, status=400)
        
        try:
            submission = PayoutSubmission.objects.get(id=submission_id)
        except PayoutSubmission.DoesNotExist:
            return Response({'error': 'Submission not found'}, status=404)
        
        # Get all review logs
        logs = PayoutReviewLog.objects.filter(
            payout_submission=submission
        ).select_related('reviewer_user').order_by('created_at')
        
        logs_data = [{
            'id': log.id,
            'reviewer': log.reviewer_user.username,
            'action': log.action,
            'reason': log.reason,
            'created_at': log.created_at
        } for log in logs]
        
        return Response({
            'submission_id': submission.id,
            'user': submission.user.username,
            'server': submission.server.name,
            'amount': float(submission.amount),
            'status': submission.status,
            'logs': logs_data
        })
