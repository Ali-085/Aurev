"""
API views for prop firm management.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .prop_firms import PropFirm
from .serializers import PropFirmSerializer


class PropFirmViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for prop firms.
    
    Regular users can list active firms for submission forms.
    Only superusers can add/edit/delete firms through admin panel.
    """
    serializer_class = PropFirmSerializer
    permission_classes = [permissions.AllowAny]  # Anyone can view active firms
    
    def get_queryset(self):
        """Return only active prop firms, ordered by display_order."""
        return PropFirm.objects.filter(is_active=True).order_by('display_order', 'name')
    
    @action(detail=False, methods=['get'])
    def choices(self, request):
        """
        Get simplified list of prop firms for dropdown/select inputs.
        
        Returns:
            [
                {"id": 1, "name": "FTMO"},
                {"id": 2, "name": "TopstepTrader"},
                ...
            ]
        """
        firms = self.get_queryset().values('id', 'name')
        return Response(list(firms))
