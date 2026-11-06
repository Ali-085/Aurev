"""
Custom pagination classes for the API.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination with configurable page size.
    
    Default: 20 items per page
    Max: 100 items per page
    Query params:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Return paginated response with metadata.
        
        Response format:
        {
            "count": 100,
            "next": "http://api.example.org/accounts/?page=3",
            "previous": "http://api.example.org/accounts/?page=1",
            "results": [...]
        }
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.page_size,
            'current_page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'results': data
        })


class LargeResultsPagination(PageNumberPagination):
    """
    Pagination for large datasets (reports, exports).
    
    Default: 50 items per page
    Max: 200 items per page
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class SmallResultsPagination(PageNumberPagination):
    """
    Pagination for small, focused lists (dropdowns, previews).
    
    Default: 10 items per page
    Max: 50 items per page
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
