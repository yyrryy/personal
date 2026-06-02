from django.contrib import admin
from django.utils.html import format_html

# Register your models here.
from . import models

# ========== SUBSCRIPTION ADMIN CONFIGS ==========

@admin.register(models.Software)
class SoftwareAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'slug', 'base_price', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'slug', 'emoji', 'description')}),
        ('Pricing', {'fields': ('base_price',)}),
        ('Status', {'fields': ('is_active',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(models.HostingPlan)
class HostingPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'price', 'storage_gb', 'bandwidth_gb', 'is_recommended', 'is_active')
    list_filter = ('tier', 'is_active', 'is_recommended', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'tier', 'description')}),
        ('Resources', {'fields': ('storage_gb', 'bandwidth_gb', 'max_users', 'uptime_sla')}),
        ('Pricing & Status', {'fields': ('price', 'is_active', 'is_recommended')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(models.Addon)
class AddonAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'addon_type', 'price', 'is_required', 'is_active')
    list_filter = ('addon_type', 'is_required', 'is_active', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'slug', 'emoji', 'addon_type', 'description')}),
        ('Pricing & Limits', {'fields': ('price', 'max_quantity')}),
        ('Status', {'fields': ('is_active', 'is_required')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(models.Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'get_email', 'phone', 'country', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at', 'country')
    search_fields = ('company_name', 'user__email', 'vat_number')
    readonly_fields = ('created_at', 'updated_at', 'active_subscriptions_count')
    fieldsets = (
        ('User Account', {'fields': ('user',)}),
        ('Company Info', {'fields': ('company_name', 'vat_number', 'is_verified')}),
        ('Contact', {'fields': ('phone', 'address', 'city', 'country')}),
        ('Stats', {'fields': ('active_subscriptions_count',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def active_subscriptions_count(self, obj):
        return obj.active_subscriptions.count()
    active_subscriptions_count.short_description = 'Active Subscriptions'


class SubscriptionAddonInline(admin.TabularInline):
    model = models.SubscriptionAddon
    extra = 1
    fields = ('addon', 'quantity', 'is_active', 'added_date', 'removed_date')
    readonly_fields = ('added_date', 'removed_date')


@admin.register(models.Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('client', 'software', 'hosting_plan', 'status', 'billing_cycle', 'monthly_cost_display', 'created_at')
    list_filter = ('status', 'billing_cycle', 'created_at', 'software', 'hosting_plan')
    search_fields = ('client__company_name', 'software__name')
    readonly_fields = ('start_date', 'created_at', 'updated_at', 'monthly_cost_display', 'yearly_cost_display')
    inlines = [SubscriptionAddonInline]
    fieldsets = (
        ('Subscription Info', {'fields': ('client', 'software', 'hosting_plan')}),
        ('Billing', {'fields': ('status', 'billing_cycle', 'custom_software_price', 'discount_percentage', 'is_auto_renew')}),
        ('Dates', {'fields': ('start_date', 'end_date', 'next_billing_date')}),
        ('Pricing Summary', {
            'fields': ('monthly_cost_display', 'yearly_cost_display'),
            'classes': ('collapse',)
        }),
        ('Notes', {'fields': ('notes',), 'classes': ('collapse',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    actions = ['activate_subscription', 'suspend_subscription', 'cancel_subscription']

    def monthly_cost_display(self, obj):
        return f"€{obj.get_monthly_cost()}"
    monthly_cost_display.short_description = 'Monthly Cost'

    def yearly_cost_display(self, obj):
        return f"€{obj.get_yearly_cost()}"
    yearly_cost_display.short_description = 'Yearly Cost'

    def activate_subscription(self, request, queryset):
        queryset.update(status='active')
    activate_subscription.short_description = "Activate selected subscriptions"

    def suspend_subscription(self, request, queryset):
        queryset.update(status='suspended')
    suspend_subscription.short_description = "Suspend selected subscriptions"

    def cancel_subscription(self, request, queryset):
        for subscription in queryset:
            subscription.cancel()
    cancel_subscription.short_description = "Cancel selected subscriptions"


@admin.register(models.SubscriptionAddon)
class SubscriptionAddonAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'addon', 'quantity', 'is_active', 'added_date')
    list_filter = ('is_active', 'added_date', 'addon__addon_type')
    search_fields = ('subscription__client__company_name', 'addon__name')
    readonly_fields = ('added_date', 'removed_date')
    fieldsets = (
        ('Addon Assignment', {'fields': ('subscription', 'addon')}),
        ('Quantity & Status', {'fields': ('quantity', 'is_active')}),
        ('Dates', {'fields': ('added_date', 'removed_date')}),
    )
    actions = ['deactivate_addons']

    def deactivate_addons(self, request, queryset):
        for addon in queryset:
            addon.deactivate()
    deactivate_addons.short_description = "Deactivate selected addons"


@admin.register(models.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'subscription', 'status', 'total_amount_display', 'issued_date', 'due_date')
    list_filter = ('status', 'issued_date', 'due_date')
    search_fields = ('invoice_number', 'subscription__client__company_name')
    readonly_fields = ('issued_date', 'created_at', 'updated_at', 'tax_amount', 'total_amount')
    fieldsets = (
        ('Invoice Info', {'fields': ('invoice_number', 'subscription', 'status')}),
        ('Amounts', {'fields': ('subtotal', 'tax_percentage', 'tax_amount', 'discount_amount', 'total_amount')}),
        ('Dates', {'fields': ('issued_date', 'due_date', 'paid_date')}),
        ('Payment', {'fields': ('payment_method', 'notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    actions = ['mark_as_paid', 'mark_as_overdue']

    def total_amount_display(self, obj):
        return f"€{obj.total_amount}"
    total_amount_display.short_description = 'Total'

    def mark_as_paid(self, request, queryset):
        for invoice in queryset:
            invoice.mark_as_paid()
    mark_as_paid.short_description = "Mark selected invoices as paid"

    def mark_as_overdue(self, request, queryset):
        for invoice in queryset:
            invoice.mark_as_overdue()
    mark_as_overdue.short_description = "Mark selected invoices as overdue"


@admin.register(models.SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'change_type', 'created_at', 'user')
    list_filter = ('change_type', 'created_at')
    search_fields = ('subscription__client__company_name', 'description')
    readonly_fields = ('created_at', 'subscription', 'change_type', 'old_value', 'new_value', 'description', 'user')
    
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ========== LEGACY ADMIN REGISTRATIONS ==========

admin.site.register(models.Outraisons)
admin.site.register(models.Inraisons)
admin.site.register(models.Profile)
admin.site.register(models.Inbalance)
admin.site.register(models.Outbalance)
admin.site.register(models.Activity)
admin.site.register(models.Depense)
admin.site.register(models.Essance)
admin.site.register(models.Connection)
admin.site.register(models.Node)
admin.site.register(models.Roadmap)
admin.site.register(models.RoadmapItem)
admin.site.register(models.Moneyexpected)