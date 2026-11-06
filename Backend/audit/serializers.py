from rest_framework import serializers
from .models import AuditLog
from users.serializers import UserSerializer


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""
    
    actor_user = UserSerializer(read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor_user', 'action_type', 'target_table',
            'target_id', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
