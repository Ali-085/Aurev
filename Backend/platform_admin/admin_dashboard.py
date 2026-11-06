"""
Admin Dashboard ViewSet

Provides comprehensive admin panel endpoints for platform Admins.
Admins are high-trust moderators with expanded capabilities but RESTRICTED from:
- Deleting servers
- Editing revenue/rankings
- Modifying platform settings
- Changing permissions
- Accessing audit logs
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, Avg
from users.permissions import IsEmailVerified
from django.utils import timezone
from datetime import timedelta
from core.permissions import IsAdminOnly, IsSuperuserOnly
from payouts.models import PayoutSubmission
from servers.models import Server, ServerMember
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminDashboardViewSet(viewsets.ViewSet):
    """
    Admin Dashboard for platform Admins.
    
    Admin Permissions:
    ✓ Review payout submissions
    ✓ Approve/reject payouts
    ✓ Mark submissions as suspicious
    ✓ Edit minor payout details (formatting, category)
    ✓ Restore rejected submissions
    ✓ Access server analytics for moderation
    ✓ View member profiles
    ✓ Pause server submissions
    ✓ Download moderation reports
    
    Admin Restrictions (CRITICAL):
    ✗ Delete servers (Superuser only)
    ✗ Edit revenue numbers (Superuser only)
    ✗ Edit rankings (Superuser only)
    ✗ Change subscriptions (Superuser only)
    ✗ Modify platform settings (Superuser only)
    ✗ View audit logs (Superuser only)
    ✗ Change permissions (Superuser only)
    """
    # SECURITY: IsAdminOnly now checks authentication + email verification internally
    permission_classes = [IsAdminOnly]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        Admin dashboard overview statistics.
        
        Returns:
        - Pending submissions count
        - Today's reviews count
        - Suspicious submissions count
        - Paused servers count
        """
        # Pending submissions
        pending_count = PayoutSubmission.objects.filter(status='Pending').count()
        
        # Suspicious submissions
        suspicious_count = PayoutSubmission.objects.filter(status='Suspicious').count()
        
        # Today's reviews by this admin
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        my_reviews_today = PayoutSubmission.objects.filter(
            reviewer=request.user,
            reviewed_at__gte=today_start
        ).count()
        
        # Paused servers
        paused_servers_count = Server.objects.filter(payout_submissions_paused=True).count()
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        weekly_submissions = PayoutSubmission.objects.filter(
            created_at__gte=week_ago
        ).count()
        weekly_approvals = PayoutSubmission.objects.filter(
            status='Approved',
            reviewed_at__gte=week_ago
        ).count()
        weekly_rejections = PayoutSubmission.objects.filter(
            status='Rejected',
            reviewed_at__gte=week_ago
        ).count()
        
        return Response({
            'pending_submissions': pending_count,
            'suspicious_submissions': suspicious_count,
            'my_reviews_today': my_reviews_today,
            'paused_servers': paused_servers_count,
            'weekly_stats': {
                'submissions': weekly_submissions,
                'approvals': weekly_approvals,
                'rejections': weekly_rejections
            }
        })
    
    @action(detail=False, methods=['get'])
    def pending_submissions(self, request):
        """
        Get all pending payout submissions for review.
        
        Filters:
        - server: Filter by server ID
        - market_category: Filter by market type
        - min_amount: Minimum payout amount
        - max_amount: Maximum payout amount
        """
        queryset = PayoutSubmission.objects.filter(status='Pending').select_related(
            'user', 'server'
        ).order_by('-created_at')
        
        # Apply filters
        server_id = request.query_params.get('server')
        if server_id:
            queryset = queryset.filter(server_id=server_id)
        
        market_category = request.query_params.get('market_category')
        if market_category:
            queryset = queryset.filter(market_category=market_category)
        
        min_amount = request.query_params.get('min_amount')
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        
        max_amount = request.query_params.get('max_amount')
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)
        
        from payouts.serializers import PayoutSubmissionSerializer
        serializer = PayoutSubmissionSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def suspicious_submissions(self, request):
        """Get all submissions marked as suspicious."""
        submissions = PayoutSubmission.objects.filter(
            status='Suspicious'
        ).select_related('user', 'server', 'reviewer').order_by('-reviewed_at')
        
        from payouts.serializers import PayoutSubmissionSerializer
        serializer = PayoutSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def server_list(self, request):
        """
        Get list of servers for moderation.
        
        Admins can:
        - View server details
        - Pause/resume submissions
        - View analytics
        
        Admins CANNOT:
        - Delete servers (Superuser only)
        - Suspend servers (Superuser only)
        """
        servers = Server.objects.annotate(
            total_submissions=Count('payout_submissions'),
            pending_submissions=Count(
                'payout_submissions',
                filter=Q(payout_submissions__status='Pending')
            ),
            total_members=Count('members')
        ).order_by('-created_at')
        
        # Filter by status if provided
        paused = request.query_params.get('paused')
        if paused == 'true':
            servers = servers.filter(payout_submissions_paused=True)
        elif paused == 'false':
            servers = servers.filter(payout_submissions_paused=False)
        
        data = []
        for server in servers:
            data.append({
                'id': str(server.id),
                'name': server.name,
                'platform': server.platform.name if server.platform else 'Unknown',
                'owner': server.owner_user.username,
                'is_verified': server.is_verified,
                'suspended': server.suspended,
                'payout_submissions_paused': server.payout_submissions_paused,
                'paused_by': server.paused_by.username if server.paused_by else None,
                'paused_at': server.paused_at,
                'total_submissions': server.total_submissions,
                'pending_submissions': server.pending_submissions,
                'total_members': server.total_members,
                'created_at': server.created_at
            })
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def pause_server_submissions(self, request, pk=None):
        """
        Pause payout submissions for a server (Admin moderation power).
        
        Used when:
        - Investigating suspicious activity
        - Server owner requested pause
        - High volume of rejections
        """
        from django.db import transaction
        
        try:
            with transaction.atomic():
                server = Server.objects.select_for_update().get(pk=pk)
                
                # SECURITY: Admins cannot suspend servers (Owner only)
                # They can only pause submissions temporarily
                if server.suspended:
                    return Response(
                        {'error': 'Server is suspended. Contact platform Owner.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                server.payout_submissions_paused = True
                server.paused_by = request.user
                server.paused_at = timezone.now()
                server.save(update_fields=['payout_submissions_paused', 'paused_by', 'paused_at'])
                
                # SECURITY: Sanitize reason to prevent XSS
                import bleach
                reason = request.data.get('reason', 'Admin moderation')
                reason = bleach.clean(str(reason).strip(), tags=[], strip=True)[:500]
                
                # Log action
                from audit.models import AuditLog
                AuditLog.log(
                    request.user,
                    action_type='other',
                    target_table='Server',
                    target_id=server.id,
                    metadata={
                        'server_name': server.name,
                        'reason': reason,
                        'action': 'pause_submissions'
                    }
                )
            
            return Response({
                'message': f'Payout submissions paused for {server.name}',
                'paused_at': server.paused_at,
                'paused_by': request.user.username
            })
        
        except Server.DoesNotExist:
            return Response({'error': 'Server not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def resume_server_submissions(self, request, pk=None):
        """Resume payout submissions for a server."""
        from django.db import transaction
        
        try:
            with transaction.atomic():
                server = Server.objects.select_for_update().get(pk=pk)
                
                if not server.payout_submissions_paused:
                    return Response(
                        {'error': 'Server submissions are not paused'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                server.payout_submissions_paused = False
                server.paused_by = None
                server.paused_at = None
                server.save(update_fields=['payout_submissions_paused', 'paused_by', 'paused_at'])
                
                # SECURITY: Sanitize reason to prevent XSS
                import bleach
                reason = request.data.get('reason', 'Issue resolved')
                reason = bleach.clean(str(reason).strip(), tags=[], strip=True)[:500]
                
                # Log action
                from audit.models import AuditLog
                AuditLog.log(
                    request.user,
                    action_type='other',
                    target_table='Server',
                    target_id=server.id,
                    metadata={
                        'server_name': server.name,
                        'reason': reason,
                        'action': 'resume_submissions'
                    }
                )
            
            return Response({
                'message': f'Payout submissions resumed for {server.name}'
            })
        
        except Server.DoesNotExist:
            return Response({'error': 'Server not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def server_analytics(self, request, pk=None):
        """
        Get server analytics for moderation purposes.
        
        Shows:
        - Total submissions and approvals
        - Rejection rate
        - Top submitters
        - Recent activity
        """
        try:
            server = Server.objects.get(pk=pk)
        except Server.DoesNotExist:
            return Response({'error': 'Server not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Submission stats
        total_submissions = PayoutSubmission.objects.filter(server=server).count()
        approved = PayoutSubmission.objects.filter(server=server, status='Approved').count()
        rejected = PayoutSubmission.objects.filter(server=server, status='Rejected').count()
        pending = PayoutSubmission.objects.filter(server=server, status='Pending').count()
        suspicious = PayoutSubmission.objects.filter(server=server, status='Suspicious').count()
        
        # Rejection rate
        rejection_rate = (rejected / total_submissions * 100) if total_submissions > 0 else 0
        
        # Top submitters
        top_submitters = ServerMember.objects.filter(
            server=server
        ).select_related('user').order_by('-total_submissions')[:10]
        
        top_submitters_data = [{
            'user_id': member.user.id,
            'username': member.user.username,
            'total_submissions': member.total_submissions,
            'total_verified_payouts': float(member.total_verified_payouts)
        } for member in top_submitters]
        
        # Recent suspicious activity (last 30 days)
        month_ago = timezone.now() - timedelta(days=30)
        recent_suspicious = PayoutSubmission.objects.filter(
            server=server,
            status='Suspicious',
            reviewed_at__gte=month_ago
        ).count()
        
        return Response({
            'server': {
                'id': server.id,
                'name': server.name,
                'owner': server.owner_user.username,
                'platform': server.platform,
                'is_verified': server.is_verified,
                'payout_submissions_paused': server.payout_submissions_paused
            },
            'stats': {
                'total_submissions': total_submissions,
                'approved': approved,
                'rejected': rejected,
                'pending': pending,
                'suspicious': suspicious,
                'rejection_rate': round(rejection_rate, 2)
            },
            'top_submitters': top_submitters_data,
            'recent_suspicious_count': recent_suspicious
        })
    
    @action(detail=False, methods=['get'])
    def member_profile(self, request):
        """
        View member profile for moderation.
        
        Query params:
        - user_id: User ID to view
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # User submission stats
        total_submissions = PayoutSubmission.objects.filter(user=user).count()
        approved = PayoutSubmission.objects.filter(user=user, status='Approved').count()
        rejected = PayoutSubmission.objects.filter(user=user, status='Rejected').count()
        suspicious = PayoutSubmission.objects.filter(user=user, status='Suspicious').count()
        
        # Total verified amount
        total_verified = PayoutSubmission.objects.filter(
            user=user,
            status='Approved'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Server memberships
        memberships = ServerMember.objects.filter(user=user).select_related('server')
        memberships_data = [{
            'server_id': m.server.id,
            'server_name': m.server.name,
            'total_submissions': m.total_submissions,
            'total_verified_payouts': float(m.total_verified_payouts),
            'joined_at': m.joined_at
        } for m in memberships]
        
        # Recent submissions
        recent_submissions = PayoutSubmission.objects.filter(
            user=user
        ).select_related('server').order_by('-created_at')[:10]
        
        recent_data = [{
            'id': sub.id,
            'amount': float(sub.amount),
            'market_category': sub.market_category,
            'status': sub.status,
            'server_name': sub.server.name,
            'created_at': sub.created_at,
            'reviewed_at': sub.reviewed_at
        } for sub in recent_submissions]
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'date_joined': user.date_joined,
                'is_active': user.is_active
            },
            'stats': {
                'total_submissions': total_submissions,
                'approved': approved,
                'rejected': rejected,
                'suspicious': suspicious,
                'approval_rate': round((approved / total_submissions * 100) if total_submissions > 0 else 0, 2),
                'total_verified_amount': float(total_verified)
            },
            'server_memberships': memberships_data,
            'recent_submissions': recent_data
        })
    
    @action(detail=False, methods=['get'])
    def download_report(self, request):
        """
        Download moderation report (CSV format).
        
        Query params:
        - report_type: 'submissions', 'suspicious', 'rejections'
        - start_date: Filter start date
        - end_date: Filter end date
        """
        import csv
        from django.http import HttpResponse
        
        report_type = request.query_params.get('report_type', 'submissions')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Build queryset based on report type
        if report_type == 'suspicious':
            queryset = PayoutSubmission.objects.filter(status='Suspicious')
        elif report_type == 'rejections':
            queryset = PayoutSubmission.objects.filter(status='Rejected')
        else:
            queryset = PayoutSubmission.objects.all()
        
        # Apply date filters
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        queryset = queryset.select_related('user', 'server', 'reviewer').order_by('-created_at')
        
        # Create CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="admin_report_{report_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User', 'Server', 'Amount', 'Currency', 'Market', 'Instrument',
            'Status', 'Reviewer', 'Submitted', 'Reviewed'
        ])
        
        for submission in queryset:
            writer.writerow([
                submission.id,
                submission.user.username,
                submission.server.name,
                float(submission.amount),
                submission.currency,
                submission.market_category,
                submission.instrument,
                submission.status,
                submission.reviewer.username if submission.reviewer else 'N/A',
                submission.created_at.strftime('%Y-%m-%d %H:%M'),
                submission.reviewed_at.strftime('%Y-%m-%d %H:%M') if submission.reviewed_at else 'N/A'
            ])
        
        return response
