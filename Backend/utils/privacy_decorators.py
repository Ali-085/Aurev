"""
Decorators for privacy-related authorization.
"""
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from utils.privacy import check_private_analytics_access

User = get_user_model()


def check_private_analytics_token(view_func):
    """
    Decorator to check for valid private analytics token.
    
    Adds 'has_valid_token' to request context if token is valid.
    Token can be provided via:
    - Query parameter: ?token=<uuid>
    - Header: X-Private-Analytics-Token: <uuid>
    
    Usage:
        @check_private_analytics_token
        def my_view(request, user_id):
            has_access = request.has_valid_token
            # ... your logic
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get token from query params or headers
        token = request.query_params.get('token') or request.META.get('HTTP_X_PRIVATE_ANALYTICS_TOKEN')
        
        # Get user_id from kwargs (common pattern)
        user_id = kwargs.get('user_id') or kwargs.get('pk')
        
        request.has_valid_token = False
        
        if token and user_id:
            try:
                user = User.objects.get(id=user_id)
                request.has_valid_token = check_private_analytics_access(token, user)
            except User.DoesNotExist:
                pass
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_private_analytics_token(view_func):
    """
    Decorator that REQUIRES a valid private analytics token.
    
    Returns 403 if no valid token is provided.
    
    Usage:
        @require_private_analytics_token
        def private_analytics_view(request, user_id):
            # Token is guaranteed to be valid here
            # ... your logic
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get token from query params or headers
        token = request.query_params.get('token') or request.META.get('HTTP_X_PRIVATE_ANALYTICS_TOKEN')
        
        # Get user_id from kwargs
        user_id = kwargs.get('user_id') or kwargs.get('pk')
        
        if not token:
            return Response(
                {'detail': 'Private analytics token required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not user_id:
            return Response(
                {'detail': 'User ID required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            if not check_private_analytics_access(token, user):
                return Response(
                    {'detail': 'Invalid or expired token.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        request.has_valid_token = True
        return view_func(request, *args, **kwargs)
    
    return wrapper
