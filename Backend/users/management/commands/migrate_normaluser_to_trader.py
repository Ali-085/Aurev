"""
Management command to migrate NormalUser roles to Trader roles
and assign Trader role to users without any role
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from users.models import User, Role, UserRole


class Command(BaseCommand):
    help = 'Migrates NormalUser roles to Trader and assigns Trader to users without roles'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            # Get or create Trader role
            trader_role, created = Role.objects.get_or_create(
                name='Trader',
                defaults={'description': 'Regular platform user'}
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS('✅ Created Trader role'))
            else:
                self.stdout.write(self.style.WARNING('Trader role already exists'))
            
            # Try to get NormalUser role
            try:
                normal_user_role = Role.objects.get(name='NormalUser')
                
                # Update all UserRole records from NormalUser to Trader
                updated_count = UserRole.objects.filter(role=normal_user_role).update(role=trader_role)
                
                if updated_count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Migrated {updated_count} users from NormalUser to Trader')
                    )
                
                # Delete the NormalUser role
                normal_user_role.delete()
                self.stdout.write(self.style.SUCCESS('✅ Deleted NormalUser role'))
                
            except Role.DoesNotExist:
                self.stdout.write(self.style.WARNING('NormalUser role does not exist (already migrated)'))
            
            # Find users without any role (excluding superusers)
            users_without_role = User.objects.filter(
                user_roles__isnull=True,
                is_superuser=False
            ).exclude(
                # Exclude server creator applicants who are pending payment
                server_creator_applications__status__in=['pending_email', 'pending_payment', 'payment_processing']
            )
            
            assigned_count = 0
            for user in users_without_role:
                UserRole.objects.create(user=user, role=trader_role)
                assigned_count += 1
            
            if assigned_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Assigned Trader role to {assigned_count} users without roles')
                )
            else:
                self.stdout.write(self.style.SUCCESS('All non-superuser users already have roles'))
            
            self.stdout.write(
                self.style.SUCCESS('\n🎉 Migration complete! All users now have appropriate roles.')
            )
