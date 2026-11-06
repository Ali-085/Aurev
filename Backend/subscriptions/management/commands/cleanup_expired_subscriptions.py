"""
Subscription Cleanup Management Command

Handles:
1. Send deletion warning emails (X days before grace period ends)
2. Delete expired server data (after grace period ends)
3. Clean up orphaned records

Run daily via cron:
    python manage.py cleanup_expired_subscriptions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from subscriptions.models import UserSubscription
from servers.models import Server, ServerMember
from payouts.models import PayoutSubmission
from platform_admin.models import PlatformLimits
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up expired subscriptions and delete server data after grace period'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompts',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Subscription Cleanup Process'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No data will be deleted\n'))
        
        # Get platform settings
        limits = PlatformLimits.get_limits()
        
        if not limits.enable_server_data_deletion:
            self.stdout.write(self.style.NOTICE(
                '⚠️  Server data deletion is disabled in platform settings. Exiting.'
            ))
            return
        
        # Step 1: Send deletion warnings
        self.stdout.write('\n' + self.style.HTTP_INFO('Step 1: Sending deletion warnings'))
        self.send_deletion_warnings(limits, dry_run)
        
        # Step 2: Delete expired server data
        self.stdout.write('\n' + self.style.HTTP_INFO('Step 2: Deleting expired server data'))
        deleted_count = self.delete_expired_servers(limits, dry_run, force)
        
        # Summary
        self.stdout.write('\n' + self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS(f'✅ Cleanup complete. Servers deleted: {deleted_count}'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

    def send_deletion_warnings(self, limits, dry_run):
        """Send warning emails before data deletion"""
        if limits.notify_before_deletion_days == 0:
            self.stdout.write(self.style.NOTICE('   ⏭️  Warning emails disabled (notify_before_deletion_days = 0)'))
            return
        
        now = timezone.now()
        warning_threshold = now + timedelta(days=limits.notify_before_deletion_days)
        
        # Find subscriptions approaching deletion that haven't been warned yet
        subscriptions_to_warn = UserSubscription.objects.filter(
            status='canceled',
            grace_period_ends_at__lte=warning_threshold,
            grace_period_ends_at__gt=now,
            deletion_warning_sent_at__isnull=True
        ).select_related('user', 'plan')
        
        count = subscriptions_to_warn.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('   ✅ No subscriptions need warnings'))
            return
        
        self.stdout.write(self.style.WARNING(f'   📧 Found {count} subscriptions to warn'))
        
        if not dry_run:
            for sub in subscriptions_to_warn:
                # TODO: Send actual email notification
                # For now, just log and mark as sent
                logger.info(
                    f"Deletion warning: user_id={sub.user_id}, "
                    f"grace_period_ends={sub.grace_period_ends_at.isoformat()}"
                )
                
                sub.deletion_warning_sent_at = now
                sub.save(update_fields=['deletion_warning_sent_at'])
                
                self.stdout.write(
                    f'   ✉️  Warned {sub.user.email} (grace ends: {sub.grace_period_ends_at.date()})'
                )
        else:
            for sub in subscriptions_to_warn:
                self.stdout.write(
                    f'   [DRY RUN] Would warn {sub.user.email} '
                    f'(grace ends: {sub.grace_period_ends_at.date()})'
                )

    def delete_expired_servers(self, limits, dry_run, force):
        """Delete servers for subscriptions past grace period"""
        now = timezone.now()
        
        # Find expired subscriptions
        expired_subscriptions = UserSubscription.objects.filter(
            status='canceled',
            grace_period_ends_at__lte=now
        ).select_related('user', 'plan')
        
        count = expired_subscriptions.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('   ✅ No expired subscriptions found'))
            return 0
        
        self.stdout.write(self.style.ERROR(f'   🗑️  Found {count} expired subscriptions'))
        
        # Safety check
        if not force and not dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n   ⚠️  This will PERMANENTLY DELETE data for {count} subscriptions!'
            ))
            confirm = input('   Type "DELETE" to confirm: ')
            if confirm != 'DELETE':
                self.stdout.write(self.style.ERROR('   ❌ Aborted'))
                return 0
        
        deleted_servers_total = 0
        
        for sub in expired_subscriptions:
            user = sub.user
            
            # Find servers to delete
            servers_to_delete = Server.objects.filter(
                owner_user=user,
                is_deleted=True,
                deletion_reason='subscription_canceled'
            )
            
            server_count = servers_to_delete.count()
            deleted_servers_total += server_count
            
            if server_count == 0:
                self.stdout.write(f'   ℹ️  {user.email}: No servers to delete')
                continue
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'   [DRY RUN] Would delete {server_count} servers for {user.email}'
                    )
                )
            else:
                with transaction.atomic():
                    # Hard delete servers and cascade to related data
                    # Cascade will automatically delete:
                    # - ServerMember records
                    # - PayoutSubmission records (if ON DELETE CASCADE)
                    # - Server rankings/analytics
                    
                    for server in servers_to_delete:
                        server_name = server.name
                        server_id = server.id
                        
                        # Log deletion for audit trail
                        logger.warning(
                            f"HARD DELETE: server_id={server_id}, "
                            f"server_name={server_name}, "
                            f"owner_email={user.email}, "
                            f"reason=grace_period_expired"
                        )
                        
                        server.delete()
                    
                    self.stdout.write(
                        self.style.ERROR(
                            f'   🗑️  DELETED {server_count} servers for {user.email} '
                            f'(expired: {sub.grace_period_ends_at.date()})'
                        )
                    )
        
        return deleted_servers_total
