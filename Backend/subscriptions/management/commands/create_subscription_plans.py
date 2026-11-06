from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create default subscription plans'

    def handle(self, *args, **kwargs):
        plans = [
            {
                'name': 'Standard Plan',
                'tier': 'standard',
                'description': 'Perfect for starting your trading community',
                'price_per_month': 19.99,
                'stripe_price_id': 'price_REPLACE_WITH_ACTUAL_ID',
                'stripe_product_id': 'prod_REPLACE_WITH_ACTUAL_ID',
                'features': [
                    '1 server listing',
                    'Up to 10,000 members',
                    'Basic analytics',
                    'Email support',
                    '1,000 payout submissions per day'
                ],
                'sort_order': 1
            },
            {
                'name': 'Premium Plan',
                'tier': 'premium',
                'description': 'For growing trading communities',
                'price_per_month': 49.99,
                'stripe_price_id': 'price_REPLACE_WITH_ACTUAL_ID',
                'stripe_product_id': 'prod_REPLACE_WITH_ACTUAL_ID',
                'features': [
                    'Everything in Standard',
                    'Priority support',
                    'Advanced analytics',
                    'Higher submission limits',
                    'Verification badge'
                ],
                'sort_order': 2
            },
            {
                'name': 'Elite Plan',
                'tier': 'elite',
                'description': 'Maximum features and visibility',
                'price_per_month': 99.99,
                'stripe_price_id': 'price_REPLACE_WITH_ACTUAL_ID',
                'stripe_product_id': 'prod_REPLACE_WITH_ACTUAL_ID',
                'features': [
                    'Everything in Premium',
                    'Unlimited members',
                    'Unlimited submissions',
                    'Featured placement',
                    'Dedicated support',
                    'Elite badge',
                    'Auto-approve threshold'
                ],
                'sort_order': 3
            }
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                tier=plan_data['tier'],
                defaults=plan_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Updated plan: {plan.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully created/updated {len(plans)} subscription plans!')
        )
        self.stdout.write(
            self.style.WARNING(
                '\nIMPORTANT: Update stripe_price_id and stripe_product_id with actual Stripe IDs!'
            )
        )
