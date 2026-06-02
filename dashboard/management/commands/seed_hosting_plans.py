from django.core.management.base import BaseCommand
from dashboard.models import HostingPlan
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed the database with hosting plans from home3.html'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing hosting plans before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            HostingPlan.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared existing hosting plans'))

        hosting_plans_data = [
            {
                'name': 'Local',
                'tier': 'shared',
                'description': 'Local hosting option',
                'price': Decimal('0'),
                'storage_gb': 10,
                'bandwidth_gb': 5,
                'max_users': 1,
                'uptime_sla': Decimal('95.00'),
                'is_active': True,
            },
            {
                'name': 'Starter',
                'tier': 'shared',
                'description': 'Perfect for small projects and testing',
                'price': Decimal('50'),
                'storage_gb': 25,
                'bandwidth_gb': 50,
                'max_users': 2,
                'uptime_sla': Decimal('95.00'),
                'is_active': True,
            },
            {
                'name': 'Growth',
                'tier': 'shared',
                'description': 'For growing teams and projects',
                'price': Decimal('70'),
                'storage_gb': 50,
                'bandwidth_gb': 100,
                'max_users': 5,
                'uptime_sla': Decimal('97.00'),
                'is_active': True,
            },
            {
                'name': 'Professional',
                'tier': 'vps',
                'description': 'Professional tier with advanced features',
                'price': Decimal('130'),
                'storage_gb': 100,
                'bandwidth_gb': 250,
                'max_users': 10,
                'uptime_sla': Decimal('98.00'),
                'is_active': True,
            },
            {
                'name': 'Business',
                'tier': 'vps',
                'description': 'Business-grade hosting with premium support',
                'price': Decimal('200'),
                'storage_gb': 200,
                'bandwidth_gb': 500,
                'max_users': 25,
                'uptime_sla': Decimal('99.00'),
                'is_active': True,
            },
            {
                'name': 'Business +',
                'tier': 'vps',
                'description': 'Enhanced business plan with extra resources',
                'price': Decimal('250'),
                'storage_gb': 300,
                'bandwidth_gb': 750,
                'max_users': 50,
                'uptime_sla': Decimal('99.00'),
                'is_active': True,
            },
            {
                'name': 'Grand Business',
                'tier': 'dedicated',
                'description': 'Enterprise hosting for large-scale operations',
                'price': Decimal('500'),
                'storage_gb': 500,
                'bandwidth_gb': 1000,
                'max_users': 100,
                'uptime_sla': Decimal('99.50'),
                'is_active': True,
            },
            {
                'name': 'Premium Business',
                'tier': 'dedicated',
                'description': 'Premium enterprise hosting with dedicated support',
                'price': Decimal('1000'),
                'storage_gb': 1000,
                'bandwidth_gb': 2000,
                'max_users': 250,
                'uptime_sla': Decimal('99.90'),
                'is_active': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in hosting_plans_data:
            plan, created = HostingPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created hosting plan: {plan.name}")
                )
            else:
                # Update existing plan with new data
                for key, value in plan_data.items():
                    setattr(plan, key, value)
                plan.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"↻ Updated hosting plan: {plan.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Hosting plans seeded successfully!"
                f"\n   Created: {created_count}"
                f"\n   Updated: {updated_count}"
                f"\n   Total: {len(hosting_plans_data)}"
            )
        )
