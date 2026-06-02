# Subscription Management Models Documentation

## Overview
This document describes the complete subscription management system models created for the customer dashboard. These models enable customers to manage their subscriptions, add-ons, billing, and upgrade/downgrade services.

---

## Core Models

### 1. **Software**
Represents a software product that customers can subscribe to (e.g., Restaurant Management, E-commerce Platform).

**Fields:**
- `name` (CharField, unique) - Product name
- `slug` (SlugField, unique) - URL-friendly identifier
- `description` (TextField) - Product description
- `emoji` (CharField) - Icon for UI display
- `base_price` (DecimalField) - Base monthly price
- `is_active` (BooleanField) - Active status
- `created_at`, `updated_at` - Timestamps

**Methods:**
- `__str__()` - Returns emoji + name

---

### 2. **HostingPlan**
Different hosting infrastructure options available with a subscription.

**Fields:**
- `name` (CharField) - Plan name
- `tier` (CharField, choices) - Plan tier: Shared, VPS, Dedicated, Cloud
- `description` (TextField) - Plan description
- `price` (DecimalField) - Monthly hosting price
- `storage_gb` (IntegerField) - Storage capacity in GB
- `bandwidth_gb` (IntegerField) - Bandwidth in GB
- `max_users` (IntegerField, nullable) - Max concurrent users
- `uptime_sla` (DecimalField) - Service level agreement % (default 99.9)
- `is_active` (BooleanField) - Active status
- `is_recommended` (BooleanField) - Highlighted in UI
- `created_at`, `updated_at` - Timestamps

**Usage:** Customers select a hosting plan when creating/upgrading subscription.

---

### 3. **Addon**
Optional add-ons that can be purchased with a subscription (e.g., Email Support, Advanced Analytics).

**Fields:**
- `name` (CharField) - Addon name
- `slug` (SlugField, unique) - URL identifier
- `addon_type` (CharField, choices) - Type: Support, Feature, Integration, Security, Analytics, Storage, Other
- `description` (TextField) - Addon description
- `price` (DecimalField) - Monthly price
- `emoji` (CharField) - Icon for UI
- `is_active` (BooleanField) - Active status
- `is_required` (BooleanField) - Must be purchased with subscription
- `max_quantity` (IntegerField, nullable) - Max quantity per subscription
- `created_at`, `updated_at` - Timestamps

**Usage:** Addons are attached to subscriptions via `SubscriptionAddon` model.

---

### 4. **Client**
Customer profile linked to Django User account.

**Fields:**
- `user` (OneToOneField to User) - Linked Django user
- `company_name` (CharField) - Customer company name
- `phone` (CharField, optional) - Contact phone
- `country` (CharField, optional) - Country
- `city` (CharField, optional) - City
- `address` (TextField, optional) - Street address
- `vat_number` (CharField, optional, unique) - VAT/Tax ID
- `is_verified` (BooleanField) - KYC verification status
- `created_at`, `updated_at` - Timestamps

**Methods:**
- `active_subscriptions` (property) - Returns all active subscriptions
- `monthly_cost` (property) - Calculates total monthly cost of all active subscriptions
- `__str__()` - Returns company name + email

---

### 5. **Subscription**
Represents a customer's subscription to a software + hosting plan combination.

**Fields:**
- `client` (ForeignKey to Client) - Customer
- `software` (ForeignKey to Software) - Subscribed software
- `hosting_plan` (ForeignKey to HostingPlan) - Selected hosting infrastructure
- `status` (CharField, choices) - Pending, Active, Suspended, Cancelled, Expired
- `billing_cycle` (CharField, choices) - Monthly or Yearly
- `start_date` (DateTimeField) - Subscription start
- `end_date` (DateTimeField, optional) - Subscription end
- `next_billing_date` (DateTimeField, optional) - Next billing date
- `custom_software_price` (DecimalField, optional) - Override software base price
- `discount_percentage` (DecimalField) - Discount 0-100%
- `is_auto_renew` (BooleanField) - Auto-renew on expiry
- `notes` (TextField, optional) - Internal notes
- `created_at`, `updated_at` - Timestamps

**Constraints:**
- Unique together: (client, software, status) - One active per client/software

**Methods:**
- `get_monthly_cost()` - Calculates total monthly cost including software, hosting, and addons with discount applied
- `get_yearly_cost()` - Returns get_monthly_cost() × 12
- `calculate_next_billing_date()` - Calculates next billing date based on cycle
- `activate()` - Set status to active and calculate next billing date
- `suspend()` - Set status to suspended
- `cancel()` - Set status to cancelled and record end date

---

### 6. **SubscriptionAddon**
Junction model linking Subscriptions to Addons with quantity.

**Fields:**
- `subscription` (ForeignKey to Subscription) - Parent subscription
- `addon` (ForeignKey to Addon) - Selected addon
- `quantity` (IntegerField) - How many of this addon (default 1)
- `is_active` (BooleanField) - Addon active status
- `added_date` (DateTimeField) - When addon was added
- `removed_date` (DateTimeField, optional) - When addon was removed

**Constraints:**
- Unique together: (subscription, addon)

**Methods:**
- `deactivate()` - Deactivate addon and record removal date
- `__str__()` - Returns "Client - AddonName (x Quantity)"

**Usage Example:**
```python
subscription = Subscription.objects.get(id=1)
# Add addon
addon = Addon.objects.get(slug='email-support')
SubscriptionAddon.objects.create(subscription=subscription, addon=addon, quantity=2)
```

---

### 7. **Invoice**
Billing invoice for subscription charges.

**Fields:**
- `subscription` (ForeignKey to Subscription) - Associated subscription
- `invoice_number` (CharField, unique) - Invoice number (e.g., INV-2024-001)
- `status` (CharField, choices) - Draft, Pending, Paid, Overdue, Cancelled
- `subtotal` (DecimalField) - Amount before tax/discount
- `tax_percentage` (DecimalField) - Tax rate %
- `tax_amount` (DecimalField) - Calculated tax amount
- `discount_amount` (DecimalField) - Discount amount
- `total_amount` (DecimalField) - Final amount due
- `issued_date` (DateTimeField) - Invoice creation date
- `due_date` (DateTimeField) - Payment deadline
- `paid_date` (DateTimeField, optional) - Payment date
- `notes` (TextField, optional) - Payment terms/notes
- `payment_method` (CharField, optional) - Payment method (e.g., Card, Bank Transfer)
- `created_at`, `updated_at` - Timestamps

**Methods:**
- `mark_as_paid()` - Set status to paid and record payment date
- `mark_as_overdue()` - Set status to overdue if not already paid
- `__str__()` - Returns "Invoice [number] - [customer]"

---

### 8. **SubscriptionHistory**
Audit trail tracking all changes to subscriptions for compliance and troubleshooting.

**Fields:**
- `subscription` (ForeignKey to Subscription) - Modified subscription
- `change_type` (CharField, choices) - Created, Activated, Suspended, Resumed, Cancelled, Upgraded, Downgraded, Addon Added, Addon Removed, Plan Changed, Discount Applied, Other
- `old_value` (TextField, optional) - Previous value as JSON
- `new_value` (TextField, optional) - New value as JSON
- `description` (TextField) - Human-readable change description
- `user` (ForeignKey to User, optional) - Admin who made the change
- `created_at` (DateTimeField) - When change occurred

**Usage:** Automatically created when subscriptions are modified via `activate()`, `suspend()`, `cancel()`, or manually created for tracking.

---

## Data Model Relationships

```
User (Django)
  ↓
Client (One-to-One)
  ↓
Subscription (One-to-Many)
  ├─ Software (Many-to-One)
  ├─ HostingPlan (Many-to-One)
  ├─ SubscriptionAddon (One-to-Many)
  │  └─ Addon (Many-to-One)
  ├─ Invoice (One-to-Many)
  └─ SubscriptionHistory (One-to-Many)
```

---

## Admin Interface Features

### Software Admin
- List view: Name, Slug, Base Price, Active Status
- Filters: Active status, Creation date
- Search: By name or slug
- Auto-generated slug from name

### HostingPlan Admin
- List view: Name, Tier, Price, Storage, Bandwidth, Recommended status
- Filters: Tier, Active status, Recommended flag
- Organized fieldsets for easy management

### Addon Admin
- List view: Name, Type, Price, Required status, Active status
- Filters: Type, Required, Active status
- Auto-generated slug from name

### Client Admin
- List view: Company name, Email, Phone, Country, Verified status
- Inline display of active subscriptions count
- Filters: Verification status, Country, Creation date
- Search: By company, email, VAT number

### Subscription Admin
- List view: Client, Software, Hosting Plan, Status, Billing Cycle, Monthly Cost
- Inline editing of attached addons
- Display monthly and yearly cost calculations
- Bulk actions: Activate, Suspend, Cancel subscriptions
- Filters: Status, Billing cycle, Software, Hosting plan

### Invoice Admin
- List view: Invoice number, Client, Status, Total Amount, Dates
- Bulk actions: Mark as paid, Mark as overdue
- Status tracking and payment method recording

### SubscriptionHistory Admin
- Read-only view (immutable audit trail)
- Displays all changes with before/after values
- Searchable and filterable

---

## Usage Examples

### Creating a New Subscription

```python
from django.contrib.auth.models import User
from dashboard.models import Client, Software, HostingPlan, Subscription, Addon, SubscriptionAddon

# Get or create client
user = User.objects.get(username='customer@example.com')
client = Client.objects.get(user=user)

# Get software and hosting plan
software = Software.objects.get(slug='restaurant-management')
hosting = HostingPlan.objects.get(tier='vps')

# Create subscription
subscription = Subscription.objects.create(
    client=client,
    software=software,
    hosting_plan=hosting,
    status='pending',
    billing_cycle='yearly',
    discount_percentage=10  # 10% discount
)

# Add addons
addon = Addon.objects.get(slug='email-support')
SubscriptionAddon.objects.create(subscription=subscription, addon=addon, quantity=1)

# Activate subscription
subscription.activate()

# Calculate monthly cost
print(f"Monthly: €{subscription.get_monthly_cost()}")
print(f"Yearly: €{subscription.get_yearly_cost()}")
```

### Creating an Invoice

```python
from datetime import datetime, timedelta
from dashboard.models import Invoice

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

### Tracking Changes

```python
from dashboard.models import SubscriptionHistory

# Create history entry when subscription status changes
SubscriptionHistory.objects.create(
    subscription=subscription,
    change_type='activated',
    description=f'Subscription activated by admin',
    user=request.user,
    old_value='{"status": "pending"}',
    new_value='{"status": "active"}'
)
```

---

## Validation & Best Practices

1. **Unique Subscriptions**: One active subscription per client/software combination prevents duplicate active subscriptions
2. **Discount Limits**: Discount percentage should be 0-100 (enforced in validation or forms)
3. **Billing Dates**: Always use `activate()` method to properly calculate next billing date
4. **Audit Trail**: Always create `SubscriptionHistory` entries for compliance
5. **Pricing**: Use `Decimal` fields for all monetary values to avoid floating-point errors
6. **Status Workflow**: 
   - Pending → Active (via `activate()`)
   - Active → Suspended/Cancelled (via `suspend()` or `cancel()`)
   - Never go backwards (cancelled/expired cannot be reactivated - create new subscription)

---

## Future Enhancements

- [ ] Payment gateway integration (Stripe, PayPal)
- [ ] Automated invoice generation and email
- [ ] Subscription renewal reminder emails
- [ ] Usage tracking and limits enforcement
- [ ] Custom pricing tiers per client
- [ ] Proration for mid-cycle changes
- [ ] Subscription analytics dashboard
- [ ] API endpoints for customer portal

---

## Database Schema Notes

**Total Tables Created**: 8 new models
**Total Fields**: ~100+ database fields across all models
**Database Engine**: SQLite (development), can scale to PostgreSQL

**Migration File**: `dashboard/migrations/0027_subscription_models.py`

To redo migrations:
```bash
python manage.py migrate dashboard
```

To create test data:
```bash
python manage.py shell
# Then use examples from Usage Examples section
```
