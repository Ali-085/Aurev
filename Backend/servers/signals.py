from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Server
from audit.models import AuditLog


@receiver(post_save, sender=Server)
def log_server_changes(sender, instance, created, **kwargs):
    """Log server creation and updates."""
    if created:
        AuditLog.log(
            user=instance.owner_user,
            action_type='create',
            target_table='servers',
            target_id=instance.id,
            metadata={'name': instance.name, 'platform': instance.platform.name if instance.platform else None}
        )
    else:
        # Check if verification status changed
        if instance.is_verified:
            AuditLog.log(
                user=None,  # System action
                action_type='verify',
                target_table='servers',
                target_id=instance.id,
                metadata={'name': instance.name}
            )
        
        # Check if suspension status changed
        if instance.suspended:
            AuditLog.log(
                user=None,
                action_type='suspend',
                target_table='servers',
                target_id=instance.id,
                metadata={
                    'name': instance.name,
                    'reason': instance.suspension_reason
                }
            )
