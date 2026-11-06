"""
Recent Payouts API Endpoint

This endpoint returns a paginated list of recent approved payouts
across all servers for the home page feed.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q
from datetime import datetime
from payouts.models import PayoutSubmission

@api_view(['GET'])
@permission_classes([AllowAny])
def recent_payouts_feed(request):
    """
    Get recent approved payouts across all servers.
    
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Items per page (default: 10, max: 50)
    - server_name: Filter by server name (partial match)
    - amount_min: Minimum amount
    - amount_max: Maximum amount
    - date_from: Start date (YYYY-MM-DD)
    - date_to: End date (YYYY-MM-DD)
    """
    
    # Get query parameters
    page = int(request.query_params.get('page', 1))
    limit = min(int(request.query_params.get('limit', 10)), 50)
    server_name = request.query_params.get('server_name', '').strip()
    amount_min = request.query_params.get('amount_min')
    amount_max = request.query_params.get('amount_max')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    # Base query - approved payouts only
    payouts = PayoutSubmission.objects.filter(
        status='Approved'
    ).select_related('server', 'user').order_by('-created_at')
    
    # Apply filters
    if server_name:
        payouts = payouts.filter(server__name__icontains=server_name)
    
    if amount_min:
        try:
            payouts = payouts.filter(amount__gte=float(amount_min))
        except ValueError:
            pass
    
    if amount_max:
        try:
            payouts = payouts.filter(amount__lte=float(amount_max))
        except ValueError:
            pass
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            payouts = payouts.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            payouts = payouts.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Get total count
    total_count = payouts.count()
    
    # Pagination
    offset = (page - 1) * limit
    payouts_page = payouts[offset:offset + limit]
    
    # Format response
    payout_list = []
    for payout in payouts_page:
        payout_list.append({
            'id': str(payout.id),
            'server_name': payout.server.name,
            'server_id': str(payout.server.id),
            'amount': float(payout.amount),
            'currency': payout.currency,
            'submitted_at': payout.created_at.isoformat(),
            'payout_date': payout.payout_date.isoformat() if payout.payout_date else None,
        })
    
    return Response({
        'payouts': payout_list,
        'pagination': {
            'page': page,
            'limit': limit,
            'total_count': total_count,
            'total_pages': (total_count + limit - 1) // limit
        }
    })
