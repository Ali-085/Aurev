from django.db import models
from django.conf import settings
from django.utils import timezone


class AuditLog(models.Model):
    """Audit log for tracking all important actions."""
    
    ACTION_TYPE_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('verify', 'Verify'),
        ('suspend', 'Suspend'),
        ('unsuspend', 'Unsuspend'),
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('other', 'Other'),
    ]
    
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_actions'
    )
    action_type = models.CharField(max_length=50, choices=ACTION_TYPE_CHOICES)
    target_table = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actor_user', 'created_at']),
            models.Index(fields=['target_table', 'target_id']),
            models.Index(fields=['action_type']),
        ]
    
    def __str__(self):
        actor = self.actor_user.username if self.actor_user else 'System'
        return f"{actor} - {self.action_type} on {self.target_table}({self.target_id})"
    
    @classmethod
    def log(cls, user, action_type, target_table, target_id, metadata=None):
        """Helper method to create audit log entries."""
        return cls.objects.create(
            actor_user=user,
            action_type=action_type,
            target_table=target_table,
            target_id=str(target_id),
            metadata=metadata or {}
        )
