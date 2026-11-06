from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from users.models import User
from servers.models import Server, ServerMember
from payouts.models import PayoutSubmission, PayoutSubmissionDetail
# ServerSubscription removed - using UserSubscription tier


class Command(BaseCommand):
    help = 'Generates test data for development'

    def handle(self, *args, **kwargs):
        self.stdout.write('Generating test data...\n')
        
        # Create test users
        self.stdout.write('Creating test users...')
        users = []
        for i in range(1, 11):
            user, created = User.objects.get_or_create(
                username=f'trader{i}',
                email=f'trader{i}@example.com',
                defaults={'password': 'password123'}
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'Created/verified {len(users)} users'))
        
        # Create test servers
        self.stdout.write('Creating test servers...')
        servers = []
        platforms = ['Discord', 'Telegram', 'WhatsApp', 'Slack']
        
        for i in range(1, 6):
            server, created = Server.objects.get_or_create(
                name=f'Trading Server {i}',
                owner_user=random.choice(users),
                defaults={
                    'description': f'Professional trading community #{i}',
                    'platform': random.choice(platforms),
                    'invite_link': f'https://example.com/invite-{i}',
                    'is_verified': random.choice([True, False]),
                }
            )
            servers.append(server)
        
        self.stdout.write(self.style.SUCCESS(f'Created/verified {len(servers)} servers'))
        
        # Create server members
        self.stdout.write('Creating server members...')
        member_count = 0
        for server in servers:
            for user in random.sample(users, k=random.randint(3, 7)):
                member, created = ServerMember.objects.get_or_create(
                    server=server,
                    user=user
                )
                if created:
                    member_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {member_count} server members'))
        
        # Create payout submissions
        self.stdout.write('Creating payout submissions...')
        markets = ['Futures', 'Forex', 'Crypto', 'Options', 'Equities']
        instruments = ['BTC/USD', 'EUR/USD', 'SPY', 'AAPL', 'ES', 'NQ', 'GC']
        statuses = ['Pending', 'Approved', 'Rejected', 'Suspicious']
        
        payout_count = 0
        for server in servers:
            server_members = ServerMember.objects.filter(server=server)
            
            for _ in range(random.randint(5, 15)):
                member = random.choice(server_members)
                days_ago = random.randint(0, 30)
                
                payout = PayoutSubmission.objects.create(
                    server=server,
                    user=member.user,
                    amount=round(random.uniform(100, 10000), 2),
                    currency='USD',
                    market_category=random.choice(markets),
                    instrument=random.choice(instruments),
                    payout_date=timezone.now().date() - timedelta(days=days_ago),
                    status=random.choice(statuses),
                    created_at=timezone.now() - timedelta(days=days_ago)
                )
                
                # Create details
                PayoutSubmissionDetail.objects.create(
                    payout_submission=payout,
                    risk_score=random.randint(0, 100),
                    duplicate_flag=random.choice([True, False])
                )
                
                # Update member stats if approved
                if payout.status == 'Approved':
                    member.total_verified_payouts += payout.amount
                    member.total_submissions += 1
                    member.last_submission_at = payout.created_at
                    member.save()
                
                payout_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {payout_count} payout submissions'))
        
        self.stdout.write(self.style.SUCCESS('\n✓ Test data generation complete!'))
        self.stdout.write(self.style.SUCCESS('\nYou can now login with:'))
        self.stdout.write('  Email: trader1@example.com')
        self.stdout.write('  Password: password123')
