from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# ========== SUBSCRIPTION MANAGEMENT MODELS ==========

class Software(models.Model):
    """Represents a software product (e.g., Restaurant Management)"""
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    emoji = models.CharField(max_length=10, default='💻')  # For UI display
    base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base price per month")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.emoji} {self.name}"


class HostingPlan(models.Model):
    """Different hosting options (e.g., Shared, VPS, Dedicated)"""
    TIER_CHOICES = [
        ('shared', 'Shared Hosting'),
        ('vps', 'VPS'),
        ('dedicated', 'Dedicated Server'),
        ('cloud', 'Cloud'),
    ]

    name = models.CharField(max_length=200)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    storage_gb = models.IntegerField(help_text="Storage in GB")
    bandwidth_gb = models.IntegerField(help_text="Bandwidth in GB")
    max_users = models.IntegerField(null=True, blank=True, help_text="Max concurrent users, null=unlimited")
    uptime_sla = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('99.90'), help_text="Uptime SLA percentage")
    is_active = models.BooleanField(default=True)
    is_recommended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - €{self.price}/mo"


class Addon(models.Model):
    """Add-ons that can be purchased (e.g., Email Support, Advanced Analytics)"""
    ADDON_TYPE_CHOICES = [
        ('support', 'Support'),
        ('feature', 'Feature'),
        ('integration', 'Integration'),
        ('security', 'Security'),
        ('analytics', 'Analytics'),
        ('storage', 'Storage'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    addon_type = models.CharField(max_length=20, choices=ADDON_TYPE_CHOICES)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Additional price per month")
    emoji = models.CharField(max_length=10, default='⭐')
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False, help_text="Must be purchased with subscription")
    max_quantity = models.IntegerField(null=True, blank=True, help_text="Max quantity per subscription, null=unlimited")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['addon_type', 'name']

    def __str__(self):
        return f"{self.emoji} {self.name}"


class Client(models.Model):
    """Customer profile linked to Django User"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=300)
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    vat_number = models.CharField(max_length=50, blank=True, unique=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company_name} ({self.user.email})"

    @property
    def active_subscriptions(self):
        return self.subscriptions.filter(status='active')

    @property
    def monthly_cost(self):
        """Calculate total monthly cost of all active subscriptions"""
        total = Decimal('0')
        for subscription in self.active_subscriptions:
            total += subscription.get_monthly_cost()
        return total


class Subscription(models.Model):
    """Customer subscription to a software with hosting plan"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='subscriptions')
    software = models.ForeignKey(Software, on_delete=models.CASCADE, related_name='subscriptions')
    hosting_plan = models.ForeignKey(HostingPlan, on_delete=models.PROTECT, related_name='subscriptions')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='yearly')
    
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    next_billing_date = models.DateTimeField(null=True, blank=True)
    
    custom_software_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Override base price if needed")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Discount percentage (0-100)")
    
    is_auto_renew = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('client', 'software', 'status')  # One active per client/software combo

    def __str__(self):
        return f"{self.client.company_name} - {self.software.name}"

    def get_monthly_cost(self):
        """Calculate monthly cost including hosting, software, and active addons"""
        software_price = self.custom_software_price or self.software.base_price
        hosting_price = self.hosting_plan.price
        addons_price = sum(
            sa.addon.price * sa.quantity 
            for sa in self.addons.filter(is_active=True)
        )
        
        subtotal = software_price + hosting_price + addons_price
        discount_amount = (subtotal * self.discount_percentage) / Decimal('100')
        return subtotal - discount_amount

    def get_yearly_cost(self):
        """Calculate yearly cost"""
        return self.get_monthly_cost() * Decimal('12')

    def calculate_next_billing_date(self):
        """Calculate when next billing should occur"""
        if self.billing_cycle == 'monthly':
            return self.next_billing_date + relativedelta(months=1)
        else:  # yearly
            return self.next_billing_date + relativedelta(years=1)

    def activate(self):
        """Activate subscription"""
        self.status = 'active'
        if self.billing_cycle == 'monthly':
            self.next_billing_date = timezone.now() + relativedelta(months=1)
        else:
            self.next_billing_date = timezone.now() + relativedelta(years=1)
        self.save()

    def suspend(self):
        """Suspend subscription"""
        self.status = 'suspended'
        self.save()

    def cancel(self):
        """Cancel subscription"""
        self.status = 'cancelled'
        self.end_date = timezone.now()
        self.save()


class SubscriptionAddon(models.Model):
    """Junction model for Subscription and Addon with quantity"""
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='addons')
    addon = models.ForeignKey(Addon, on_delete=models.CASCADE, related_name='subscriptions')
    quantity = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    added_date = models.DateTimeField(auto_now_add=True)
    removed_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('subscription', 'addon')

    def __str__(self):
        return f"{self.subscription.client.company_name} - {self.addon.name} (x{self.quantity})"

    def deactivate(self):
        """Deactivate addon"""
        self.is_active = False
        self.removed_date = timezone.now()
        self.save()

    def get_total_price(self):
        """Calculate total price for addon (price * quantity)"""
        return self.addon.price * self.quantity


class Invoice(models.Model):
    """Billing invoices for subscriptions"""
    INVOICE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='draft')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    issued_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    paid_date = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issued_date']

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.subscription.client.company_name}"

    def mark_as_paid(self):
        """Mark invoice as paid"""
        self.status = 'paid'
        self.paid_date = timezone.now()
        self.save()

    def mark_as_overdue(self):
        """Mark invoice as overdue"""
        if self.status != 'paid':
            self.status = 'overdue'
            self.save()


class SubscriptionHistory(models.Model):
    """Track all changes to subscriptions for audit trail"""
    CHANGE_TYPE_CHOICES = [
        ('created', 'Created'),
        ('activated', 'Activated'),
        ('suspended', 'Suspended'),
        ('resumed', 'Resumed'),
        ('cancelled', 'Cancelled'),
        ('upgraded', 'Upgraded'),
        ('downgraded', 'Downgraded'),
        ('addon_added', 'Addon Added'),
        ('addon_removed', 'Addon Removed'),
        ('plan_changed', 'Plan Changed'),
        ('discount_applied', 'Discount Applied'),
        ('other', 'Other'),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='history')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES)
    
    old_value = models.TextField(null=True, blank=True, help_text="Previous value as JSON")
    new_value = models.TextField(null=True, blank=True, help_text="New value as JSON")
    
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscription_changes')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subscription} - {self.change_type}"


# ========== LEGACY MODELS (PRESERVED) ==========

class Supervisor(models.Model):
    name=models.CharField(max_length=500)

# Create your models here.
class Village(models.Model):
    lat=models.CharField(max_length=500)
    long=models.CharField(max_length=500)
    ishelped=models.BooleanField(default=False)
    isaccissible=models.BooleanField(default=False)
    habitat=models.FloatField()
    

class Essance(models.Model):
    price=models.FloatField()
    # this will record the kilmotrage
    km=models.FloatField()
    # amount of essance en dh
    amount=models.FloatField()
    qty=models.FloatField()
    empty=models.BooleanField(default=False)
    

class Profile(models.Model):
    """Extended user profile with role-based access control"""
    
    USER_TYPE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('client', 'Client'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', default=None, null=True, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='client')
    balance = models.FloatField(default=0.0)
    birthday = models.DateTimeField(null=True, blank=True)
    name = models.CharField(default=None, max_length=500, null=True, blank=True)
    idnumber = models.CharField(default=None, max_length=500, null=True, blank=True)
    idimage1 = models.CharField(default=None, max_length=500, null=True, blank=True)
    idimage2 = models.CharField(default=None, max_length=500, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    company_name = models.CharField(max_length=500, null=True, blank=True)
    company_type = models.CharField(max_length=200, null=True, blank=True, help_text="Type of business (e.g., Restaurant, Boutique, etc.)")
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} ({self.get_user_type_display()})"
    
    def age(self):
        if not self.birthday:
            return None
        now = timezone.now()
        delta = relativedelta(now, self.birthday)
        age = delta.years
        return age
    
    def age_in_days(self):
        if not self.birthday:
            return None
        now = timezone.now()
        delta = now - self.birthday
        return delta.days
    
    def is_superadmin(self):
        return self.user_type == 'superadmin'
    
    def is_admin(self):
        return self.user_type == 'admin'
    
    def is_client(self):
        return self.user_type == 'client'
# raisons of out of balance
class Outraisons(models.Model):
    raison=models.TextField()
    def __str__(self) -> str:
        return self.raison

# raisons of in of balance
class Inraisons(models.Model):
    raison=models.TextField()
    #ch!7al b9a 3ndo
    rest=models.FloatField(default=0.0)
    #ignored means that I will not count it in the total balance(ref 544R34RR), but I want to keep it for record
    ignored=models.BooleanField(default=False)
    def __str__(self) -> str:
        return self.raison

class Outbalance(models.Model):
    amount=models.FloatField()
    date=models.DateTimeField()
    raison=models.ForeignKey(Outraisons, on_delete=models.CASCADE)
    note=models.TextField(default=None, null=True, blank=True)
    def __str__(self) -> str:
        return str(self.date)
class Inbalance(models.Model):
    amount=models.FloatField()
    date=models.DateTimeField()
    raison=models.ForeignKey(Inraisons, on_delete=models.CASCADE)
    note=models.TextField(default=None, null=True, blank=True)
    
        
class Activity(models.Model):
    date=models.DateField(default=timezone.now, null=True)
    events=models.TextField()
    prayer=models.BooleanField(default=False)
    fajr=models.BooleanField(default=False)
    duhr=models.BooleanField(default=False)
    asr=models.BooleanField(default=False)
    maghrib=models.BooleanField(default=False)
    isha=models.BooleanField(default=False)
    shower=models.BooleanField(default=False)
    football=models.BooleanField(default=False)
    run=models.BooleanField(default=False)
    coding=models.BooleanField(default=False)
    quran=models.BooleanField(default=False)
    working=models.BooleanField(default=False)
    sick=models.BooleanField(default=False)
    pushups=models.BooleanField(default=False)
    freelancing=models.BooleanField(default=False)
    mast=models.IntegerField(default=0)
    sleep=models.TimeField(default=None, null=True, blank=True)
    wake=models.TimeField(default=None, null=True, blank=True)
    face=models.ImageField(upload_to='faces/', default=None, null=True, blank=True)
    abs=models.ImageField(upload_to='abss/', default=None, null=True, blank=True)
    def __str__(self) -> str:
        return str(self.date)
    
class Depense(models.Model):
    name=models.CharField(max_length=500)
    amount=models.FloatField()
    isfix=models.BooleanField(default=False)
    date=models.DateTimeField(auto_now=True)
    def __str__(self) -> str:
        return str(self.date)
    
class Node(models.Model):
    title = models.CharField(max_length=200)
    type = models.CharField(max_length=200, default='', null=True, blank=True)  # e.g., "task", "idea"
    imglink = models.CharField(max_length=200, default=None, null=True, blank=True)  # e.g., "task", "idea"
    videolink = models.CharField(max_length=200, default=None, null=True, blank=True)  # e.g., "task", "idea"
    ytlink = models.CharField(max_length=200, default=None, null=True, blank=True)  # e.g., "task", "idea"
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="node_images/", blank=True, null=True)
    x = models.FloatField(default=100)  # position on board
    y = models.FloatField(default=100)
    def __str__(self):
        return self.title


class Connection(models.Model):
    source = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="connections_from")
    target = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="connections_to")
    label = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=20, default="#000")  # optional color

    def __str__(self):
        return f"{self.source} -> {self.target} ({self.label})"
class Item(models.Model):
    name = models.CharField(max_length=200)
    image=models.ImageField(upload_to="item_images/", blank=True, null=True)
    def __str__(self):
        return self.name
class Roadmap(models.Model):
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    estimated_completion_date = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return self.title

class RoadmapItem(models.Model):
    # admin.site.register(models.Profile)
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="items")

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    category = models.CharField(max_length=200, blank=True)  
    # No fixed choices → flexible for any roadmap type

    order = models.IntegerField(default=0)  
    # You can use order instead of day_start/day_end to support ALL kinds of roadmaps

    completed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.title} - {'Done' if self.completed else 'Pending'}"
    
class Moneyexpected(models.Model):
    amount=models.FloatField()
    raison=models.ForeignKey(Inraisons, on_delete=models.CASCADE)
    # wether I get it or not
    paid=models.BooleanField(default=False)
    note=models.TextField(default=None, null=True, blank=True)
    def __str__(self) -> str:
        return f"{self.amount} expected from {self.raison.raison}"
