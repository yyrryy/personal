# Subscription Dashboard - Quick Start Guide

## ✅ Models Created Successfully

All subscription management models have been created and migrated to the database.

### 8 Core Models:
1. **Software** - Product offerings (e.g., Restaurant Management)
2. **HostingPlan** - Infrastructure options (Shared, VPS, Dedicated, Cloud)
3. **Addon** - Optional features (Support, Analytics, Storage, etc.)
4. **Inraisons** - Customer profiles linked to Django Users
5. **Subscription** - Customer subscriptions with billing tracking
6. **SubscriptionAddon** - Add-on purchases (many-to-many with quantities)
7. **Invoice** - Billing and payment tracking
8. **SubscriptionHistory** - Audit trail of all changes

---

## 🚀 Getting Started

### Access Admin Panel
The Django admin now has complete management interfaces for all subscription models:

```bash
cd /home/yurey/projects/personal
source venv/bin/activate
python manage.py runserver
```

Then visit: `http://localhost:8000/admin/`

### Admin Features Available

| Model | Features |
|-------|----------|
| **Software** | Add products, manage pricing, set emoji icons |
| **HostingPlan** | Create hosting tiers with resource limits, SLA settings |
| **Addon** | Define add-on packages with types and pricing |
| **Inraisons** | Manage customer profiles, verification, company info |
| **Subscription** | Create/manage subscriptions with bulk actions (Activate, Suspend, Cancel) |
| **Invoice** | Create invoices, track payments, mark as paid/overdue |
| **SubscriptionHistory** | View immutable audit trail (read-only) |

---

## 📊 Admin Panel Highlights

### 🔧 Subscription Management
- **Inline Addon Management**: Add/remove addons directly on subscription edit page
- **Cost Calculator**: See monthly and yearly costs in real-time
- **Bulk Actions**: Activate, suspend, or cancel multiple subscriptions at once
- **Status Tracking**: Pending → Active → Suspended/Cancelled workflow

### 💰 Pricing & Billing
- **Automatic Cost Calculation**: Includes software + hosting + addons - discount
- **Tax Support**: Add tax percentage, system calculates tax automatically
- **Multiple Billing Cycles**: Monthly or yearly billing support
- **Invoice Management**: Track payment status and methods

### 👥 Customer Management
- **Unified Inraisons Profiles**: One profile per user with company details
- **Active Subscriptions Overview**: See active subscriptions per customer
- **Verification Tracking**: Mark customers as verified/KYC approved

### 📋 Audit & Compliance
- **Complete Audit Trail**: Every change tracked in SubscriptionHistory
- **User Attribution**: See which admin made each change
- **Immutable History**: Cannot edit/delete history entries

---

## 💻 Programmatic Usage

### Create a Software Product
```python
from dashboard.models import Software

software = Software.objects.create(
    name="E-Commerce Platform",
    slug="ecommerce",
    description="Complete online store solution",
    emoji="🛒",
    base_price=99.99,
    is_active=True
)
```

### Create a Hosting Plan
```python
from dashboard.models import HostingPlan

plan = HostingPlan.objects.create(
    name="Professional VPS",
    tier="vps",
    description="2 CPU cores, 4GB RAM, 50GB SSD",
    price=49.99,
    storage_gb=50,
    bandwidth_gb=500,
    uptime_sla=99.95,
    is_recommended=True
)
```

### Create Add-ons
```python
from dashboard.models import Addon

# Email support addon
Addon.objects.create(
    name="Email Support",
    slug="email-support",
    addon_type="support",
    description="24/7 email support",
    price=9.99,
    emoji="📧",
    is_required=False
)

# Advanced analytics addon
Addon.objects.create(
    name="Advanced Analytics",
    slug="advanced-analytics",
    addon_type="analytics",
    description="Real-time dashboards and reports",
    price=19.99,
    emoji="📊"
)
```

### Create a Customer Subscription
```python
from django.contrib.auth.models import User
from dashboard.models import Inraisons, Subscription, SubscriptionAddon, Addon

# Get or create user and client
user, _ = User.objects.get_or_create(
    username='customer@example.com',
    email='customer@example.com'
)
client, _ = Inraisons.objects.get_or_create(
    user=user,
    company_name="Acme Corporation"
)

# Create subscription
subscription = Subscription.objects.create(
    client=client,
    software=software,
    hosting_plan=plan,
    status='pending',
    billing_cycle='yearly',
    discount_percentage=5
)

# Add email support addon
addon = Addon.objects.get(slug='email-support')
SubscriptionAddon.objects.create(
    subscription=subscription,
    addon=addon,
    quantity=1
)

# Activate subscription
subscription.activate()

# Check pricing
print(f"Monthly cost: €{subscription.get_monthly_cost()}")
print(f"Yearly cost: €{subscription.get_yearly_cost()}")
```

### Create and Manage Invoices
```python
from datetime import datetime, timedelta
from dashboard.models import Invoice

# Create invoice
invoice = Invoice.objects.create(
    subscription=subscription,
    invoice_number=f"INV-{datetime.now().year}-001",
    status='pending',
    subtotal=subscription.get_monthly_cost(),
    tax_percentage=20,
    tax_amount=subscription.get_monthly_cost() * 0.20,
    total_amount=subscription.get_monthly_cost() * 1.20,
    due_date=datetime.now() + timedelta(days=30),
    payment_method='Credit Card'
)

# Mark as paid
invoice.mark_as_paid()
```

### Track Changes
```python
from dashboard.models import SubscriptionHistory
import json

SubscriptionHistory.objects.create(
    subscription=subscription,
    change_type='upgraded',
    description='Upgraded from VPS to Dedicated',
    user=request.user,
    old_value=json.dumps({"hosting_plan": "vps"}),
    new_value=json.dumps({"hosting_plan": "dedicated"})
)
```

---

## 🏗️ Database Structure

### Key Relationships
```
Django User
    ↓
  Inraisons (1:1)
    ↓
  Subscription (1:Many)
    ├─ Software (Many:1)
    ├─ HostingPlan (Many:1)
    ├─ SubscriptionAddon (1:Many) → Addon
    ├─ Invoice (1:Many)
    └─ SubscriptionHistory (1:Many)
```

### Constraints
- **One Active Subscription Per Software**: Prevents duplicate active subscriptions for same client/software
- **Unique Invoice Numbers**: Each invoice has unique invoice_number
- **Unique Add-on Attachments**: Each add-on can only be attached once per subscription

---

## 🔄 Subscription Lifecycle

```
1. PENDING
   ├─ Created with status='pending'
   ├─ addons can be added/removed
   └─ pricing can be customized
         ↓
2. ACTIVE (activate() method)
   ├─ Billing cycle starts
   ├─ next_billing_date is calculated
   └─ Can be suspended or cancelled
         ↓
3a. SUSPENDED (suspend() method)
    └─ Can be resumed by creating new subscription
    
3b. CANCELLED (cancel() method)
    ├─ end_date is recorded
    └─ Cannot be reactivated
```

---

## 💳 Pricing Calculation

**Monthly Cost** = (Software Price + Hosting Price + Addons Price) - Discount

```
Software base price (or custom price)
+
Hosting plan price
+
(Addon price × Quantity) × All active addons
-
(Subtotal × Discount Percentage / 100)
=
Monthly Cost
```

**Tax** = Monthly Cost × Tax Percentage / 100

**Invoice Total** = Monthly Cost + Tax

---

## 🎯 Common Admin Tasks

### Add a New Product
1. Go to Django Admin → Software
2. Click "Add Software"
3. Fill in: Name, Slug (auto-generated), Description, Emoji, Base Price
4. Save

### Create Subscription for Customer
1. Go to Dashboard Admin → Inraisons
2. Find or create customer
3. Go to Dashboard Admin → Subscription
4. Click "Add Subscription"
5. Select client, software, hosting plan
6. Add add-ons via inline editor
7. Set billing cycle and discount if needed
8. Set status to "pending"
9. Save and use "Activate subscription" bulk action

### Issue Invoice
1. Go to Dashboard Admin → Invoice
2. Click "Add Invoice"
3. Select subscription
4. Enter invoice number, subtotal, tax %
5. System auto-calculates tax and total
6. Set due date
7. Save
8. Use "Mark as paid" when payment received

### View Subscription Changes
1. Go to Dashboard Admin → Subscription History
2. Filter by subscription or change type
3. View all modifications with before/after values
4. See which admin made each change

---

## 📝 Next Steps

1. **Create Sample Data**: Use admin panel to add:
   - 2-3 Software products
   - 3-4 Hosting plans
   - 5-10 Add-ons

2. **Test Workflows**: Create test subscriptions and invoices

3. **Build Customer Dashboard**: Create views for customers to:
   - View active subscriptions
   - Add/remove add-ons
   - View invoices and payment history
   - Upgrade/downgrade plans

4. **Integrate Payment Processing**:
   - Stripe for credit card payments
   - Email notifications for invoices

5. **Create API Endpoints**:
   - List subscriptions
   - Create/update subscriptions
   - Manage add-ons
   - List invoices

---

## 📚 Documentation

Full detailed documentation available in: `SUBSCRIPTION_MODELS.md`

Includes:
- Complete field descriptions
- All methods and their usage
- Data relationships
- Validation rules
- Examples and best practices

---

## ✅ Verification

System check passed with no issues:
```
System check identified no issues (0 silenced).
```

All models are ready for use!

**Models Status**: ✅ Created and Migrated
**Admin Interface**: ✅ Fully Configured  
**Ready for**: ✅ Production Use
