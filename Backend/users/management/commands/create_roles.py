from django.core.management.base import BaseCommand
from users.models import Role


class Command(BaseCommand):
    help = 'Creates initial roles for the platform'

    def handle(self, *args, **kwargs):
        roles = [
            ('Trader', 'Regular platform user'),
            ('Admin', 'Platform administrator with elevated permissions'),
            ('Moderator', 'Content moderator for reviewing payouts'),
            ('ServerCreator', 'Server creator with subscription'),
        ]
        
        created_count = 0
        
        for role_name, description in roles:
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': description}
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created role: {role_name}')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'Role already exists: {role_name}')
                )
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully created {created_count} role(s)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\nAll roles already exist')
            )
