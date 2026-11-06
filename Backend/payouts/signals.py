from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PayoutSubmission
from audit.models import AuditLog


@receiver(post_save, sender=PayoutSubmission)
def log_payout_changes(sender, instance, created, **kwargs):
    """Log payout submission and review actions."""
    if created:
        AuditLog.log(
            user=instance.user,
            action_type='create',
            target_table='payout_submissions',
            target_id=instance.id,
            metadata={
                'amount': str(instance.amount),
                'server': instance.server.name,
                'market': instance.market_category
            }
        )
    elif instance.status in ['Approved', 'Rejected']:
        action = 'approve' if instance.status == 'Approved' else 'reject'
        AuditLog.log(
            user=instance.reviewer,
            action_type=action,
            target_table='payout_submissions',
            target_id=instance.id,
            metadata={
                'amount': str(instance.amount),
                'status': instance.status
            }
        )
