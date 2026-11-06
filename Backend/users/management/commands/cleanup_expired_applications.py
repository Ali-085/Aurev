"""
Management command to cleanup expired Server Creator applications.

Run this command periodically (e.g., daily via cron/scheduler) to:
- Delete users and applications that didn't complete payment within 24h
- Clean up cancelled/expired applications

Usage:
    python manage.py cleanup_expired_applications
    
Can be scheduled with:
- Cron (Linux): 0 2 * * * cd /path/to/project && python manage.py cleanup_expired_applications
- Task Scheduler (Windows)
- Django-Q, Celery, or similar
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from users.models import User, ServerCreatorApplication
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Cleanup expired Server Creator applications and associated users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        # Find expired applications
        expired_applications = ServerCreatorApplication.objects.filter(
            status__in=['pending_email', 'pending_payment', 'payment_processing'],
            expires_at__lt=now
        ).select_related('user')
        
        count = expired_applications.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired applications found'))
            return
        
        self.stdout.write(f"Found {count} expired applications")
        
        deleted_users = []
        deleted_applications = []
        
        for application in expired_applications:
            user = application.user
            
            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Would delete: User {user.email} (ID: {user.id}), "
                    f"Application {application.pk}, Status: {application.status}, "
                    f"Expired: {application.expires_at}"
                )
                deleted_users.append(user.email)
                deleted_applications.append(application.pk)
            else:
                try:
                    with transaction.atomic():
                        # Delete user (cascade will delete application via OneToOneField)
                        user_email = user.email
                        user_id = user.id
                        app_id = application.pk
                        
                        user.delete()
                        
                        deleted_users.append(user_email)
                        deleted_applications.append(app_id)
                        
                        logger.info(
                            f"Deleted expired application: User {user_email} (ID: {user_id}), "
                            f"Application {app_id}"
                        )
                        self.stdout.write(
                            self.style.WARNING(
                                f"Deleted: User {user_email} (ID: {user_id}), Application {app_id}"
                            )
                        )
                        
                except Exception as e:
                    logger.error(f"Failed to delete user {user.email}: {str(e)}")
                    self.stdout.write(
                        self.style.ERROR(f"Failed to delete user {user.email}: {str(e)}")
                    )
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n[DRY RUN] Would delete {len(deleted_users)} users and their applications"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSuccessfully deleted {len(deleted_users)} users and their applications"
                )
            )
            
            if deleted_users:
                self.stdout.write("\nDeleted users:")
                for email in deleted_users:
                    self.stdout.write(f"  - {email}")
