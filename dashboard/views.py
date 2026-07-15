from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, F
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
from decimal import Decimal
import json

from .models import Subscription, SubscriptionAddon, Addon, Invoice, Software, HostingPlan, SubscriptionHistory, Client, Moneyexpected, Inbalance, Todo


def get_client_or_none(request):
    """Get client for logged-in user or None"""
    if request.user.is_authenticated:
        try:
            return request.user.client_profile
        except Client.DoesNotExist:
            return None
    return None


@login_required(login_url='login_view')
def dashboard_home(request):
    profile = request.user.profile
    if profile.user_type == 'client':
        return redirect('main:client_dashboard')
    else:
        return redirect('main:admin_dashboard')
    return redirect('main:login')


@login_required(login_url='login_view')
def subscriptions_list(request):
    """List all subscriptions for customer"""
    client = get_client_or_none(request)
    
    if not client:
        return redirect('dashboard:client_onboarding')
    
    subscriptions = client.subscriptions.all().select_related(
        'software', 'hosting_plan'
    ).prefetch_related('addons__addon')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        subscriptions = subscriptions.filter(status=status_filter)
    
    context = {
        'client': client,
        'subscriptions': subscriptions,
        'status_choices': Subscription._meta.get_field('status').choices,
        'active_count': client.active_subscriptions.count(),
    }
    
    return render(request, 'dashboard/subscriptions_list.html', context)


@login_required(login_url='login_view')
def subscription_detail(request, subscription_id):
    """View subscription details"""
    client = get_client_or_none(request)
    
    if not client:
        return redirect('dashboard:client_onboarding')
    
    subscription = get_object_or_404(Subscription, id=subscription_id, client=client)
    
    context = {
        'client': client,
        'subscription': subscription,
        'software': subscription.software,
        'hosting_plan': subscription.hosting_plan,
        'addons': subscription.addons.filter(is_active=True).select_related('addon'),
        'available_addons': Addon.objects.filter(is_active=True).exclude(
            subscriptions__subscription=subscription,
            subscriptions__is_active=True
        ),
        'invoices': subscription.invoices.order_by('-issued_date'),
        'history': subscription.history.all().order_by('-created_at')[:10],
        'monthly_cost': subscription.get_monthly_cost(),
        'yearly_cost': subscription.get_yearly_cost(),
    }
    
    return render(request, 'dashboard/subscription_detail.html', context)


@login_required(login_url='login_view')
@require_http_methods(["POST"])
@login_required(login_url='login_view')
def add_addon(request, subscription_id):
    """Add an addon to subscription"""
    client = get_client_or_none(request)
    
    if not client:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    
    subscription = get_object_or_404(Subscription, id=subscription_id, client=client)
    addon_id = request.POST.get('addon_id')
    quantity = request.POST.get('quantity', 1)
    
    try:
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1
    except (ValueError, TypeError):
        quantity = 1
    
    addon = get_object_or_404(Addon, id=addon_id, is_active=True)
    
    # Check if addon already added
    sub_addon, created = SubscriptionAddon.objects.get_or_create(
        subscription=subscription,
        addon=addon,
        defaults={'quantity': quantity}
    )
    
    if not created:
        if sub_addon.is_active:
            sub_addon.quantity += quantity
            sub_addon.save()
        else:
            sub_addon.is_active = True
            sub_addon.quantity = quantity
            sub_addon.removed_date = None
            sub_addon.save()
    
    # Record history
    SubscriptionHistory.objects.create(
        subscription=subscription,
        change_type='addon_added',
        description=f'Added {addon.name} (x{quantity})',
        user=request.user
    )
    
    messages.success(request, f'{addon.name} added successfully!')
    return redirect('dashboard:subscription_detail', subscription_id=subscription_id)


@login_required(login_url='login_view')
@require_http_methods(["POST"])
def remove_addon(request, subscription_id, addon_id):
    """Remove an addon from subscription"""
    client = get_client_or_none(request)
    
    if not client:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    
    subscription = get_object_or_404(Subscription, id=subscription_id, client=client)
    addon = get_object_or_404(Addon, id=addon_id)
    
    sub_addon = get_object_or_404(SubscriptionAddon, subscription=subscription, addon=addon)
    addon_name = addon.name
    sub_addon.deactivate()
    
    # Record history
    SubscriptionHistory.objects.create(
        subscription=subscription,
        change_type='addon_removed',
        description=f'Removed {addon_name}',
        user=request.user
    )
    
    messages.success(request, f'{addon_name} removed successfully!')
    return redirect('dashboard:subscription_detail', subscription_id=subscription_id)


@login_required(login_url='login_view')
@require_http_methods(["POST"])
def update_addon_quantity(request, subscription_id, addon_id):
    """Update addon quantity"""
    client = get_client_or_none(request)
    
    if not client:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    
    subscription = get_object_or_404(Subscription, id=subscription_id, client=client)
    addon = get_object_or_404(Addon, id=addon_id)
    
    sub_addon = get_object_or_404(SubscriptionAddon, subscription=subscription, addon=addon)
    
    quantity = request.POST.get('quantity', 1)
    try:
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1
        if addon.max_quantity and quantity > addon.max_quantity:
            quantity = addon.max_quantity
    except (ValueError, TypeError):
        quantity = 1
    
    old_qty = sub_addon.quantity
    sub_addon.quantity = quantity
    sub_addon.save()
    
    # Record history
    SubscriptionHistory.objects.create(
        subscription=subscription,
        change_type='other',
        description=f'Updated {addon.name} quantity from {old_qty} to {quantity}',
        user=request.user
    )
    
    messages.success(request, 'Addon quantity updated!')
    return redirect('dashboard:subscription_detail', subscription_id=subscription_id)


@login_required(login_url='login_view')
def invoices_list(request):
    """List all invoices for customer"""
    client = get_client_or_none(request)
    
    if not client:
        return redirect('dashboard:client_onboarding')
    
    invoices = Invoice.objects.filter(
        subscription__client=client
    ).select_related('subscription__software').order_by('-issued_date')
    
    # Filter by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    context = {
        'client': client,
        'invoices': invoices,
        'status_choices': Invoice._meta.get_field('status').choices,
        'total_paid': sum(inv.total_amount for inv in invoices if inv.status == 'paid'),
        'total_pending': sum(inv.total_amount for inv in invoices if inv.status in ['pending', 'overdue']),
    }
    
    return render(request, 'dashboard/invoices_list.html', context)


@login_required(login_url='login_view')
def invoice_detail(request, invoice_id):
    """View invoice details"""
    client = get_client_or_none(request)
    
    if not client:
        return redirect('dashboard:client_onboarding')
    
    invoice = get_object_or_404(Invoice, id=invoice_id, subscription__client=client)
    subscription = invoice.subscription
    
    # Get subscription details at time of invoice
    sub_addons = subscription.addons.filter(is_active=True).select_related('addon')
    
    context = {
        'client': client,
        'invoice': invoice,
        'subscription': subscription,
        'software': subscription.software,
        'hosting_plan': subscription.hosting_plan,
        'addons': sub_addons,
        'can_pay': invoice.status == 'pending',
    }
    
    return render(request, 'dashboard/invoice_detail.html', context)


@login_required(login_url='login_view')
def profile_settings(request):
    """Customer profile settings"""
    client = get_client_or_none(request)
    
    if not client:
        return redirect('dashboard:client_onboarding')
    
    if request.method == 'POST':
        # Update client profile
        client.company_name = request.POST.get('company_name', client.company_name)
        client.phone = request.POST.get('phone', client.phone)
        client.address = request.POST.get('address', client.address)
        client.city = request.POST.get('city', client.city)
        client.country = request.POST.get('country', client.country)
        client.save()
        
        # Update user
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('dashboard:profile_settings')
    
    context = {
        'client': client,
        'user': request.user,
    }
    
    return render(request, 'dashboard/profile_settings.html', context)


@login_required(login_url='login_view')
def upgrade_plan(request, subscription_id):
    """Upgrade subscription hosting plan"""
    client = get_client_or_none(request)
    
    if not client:
        return redirect('dashboard:client_onboarding')
    
    subscription = get_object_or_404(Subscription, id=subscription_id, client=client)
    
    # Get available plans that are more expensive than current
    current_price = subscription.hosting_plan.price
    available_plans = HostingPlan.objects.filter(
        is_active=True,
        price__gt=current_price
    ).order_by('price')
    
    if request.method == 'POST':
        plan_id = request.POST.get('hosting_plan')
        new_plan = get_object_or_404(HostingPlan, id=plan_id, is_active=True)
        
        old_plan = subscription.hosting_plan
        subscription.hosting_plan = new_plan
        subscription.save()
        
        # Record history
        SubscriptionHistory.objects.create(
            subscription=subscription,
            change_type='upgraded',
            description=f'Upgraded hosting plan from {old_plan.name} to {new_plan.name}',
            user=request.user,
            old_value=json.dumps({'plan': old_plan.name, 'price': str(old_plan.price)}),
            new_value=json.dumps({'plan': new_plan.name, 'price': str(new_plan.price)})
        )
        
        messages.success(request, f'Upgraded to {new_plan.name}!')
        return redirect('dashboard:subscription_detail', subscription_id=subscription_id)
    
    context = {
        'client': client,
        'subscription': subscription,
        'current_plan': subscription.hosting_plan,
        'available_plans': available_plans,
        'monthly_increase': sum(
            (plan.price - subscription.hosting_plan.price) for plan in available_plans
        ) / len(available_plans) if available_plans else 0,
    }
    
    return render(request, 'dashboard/upgrade_plan.html', context)


@login_required(login_url='login_view')
def usage_analytics(request):
    """Usage and spending analytics"""
    client = get_client_or_none(request)
    
    if not client:
        return redirect('dashboard:client_onboarding')
    
    subscriptions = client.subscriptions.all()
    active_addons = SubscriptionAddon.objects.filter(
        subscription__client=client,
        is_active=True
    )
    
    # Monthly spending over last 12 months
    from datetime import datetime
    now = timezone.now()
    months_data = []
    
    for i in range(11, -1, -1):
        month_start = now - timedelta(days=30*i)
        month_invoices = Invoice.objects.filter(
            subscription__client=client,
            issued_date__month=month_start.month,
            issued_date__year=month_start.year,
            status='paid'
        )
        total = float(sum(Decimal(str(inv.total_amount)) for inv in month_invoices))
        months_data.append({
            'month': month_start.strftime('%b %Y'),
            'total': total
        })
    
    # Chart data for JavaScript
    monthly_labels = [d['month'] for d in months_data]
    monthly_values = [d['total'] for d in months_data]
    
    # Cost breakdown
    total_subscriptions_cost = sum(
        Decimal(str(sub.hosting_plan.price)) 
        for sub in subscriptions.filter(status='active')
    )
    total_addons_cost = sum(
        Decimal(str(addon.get_total_price())) 
        for addon in active_addons
    )
    
    breakdown_labels = ['Hosting Plans', 'Add-ons'] if total_addons_cost > 0 else ['Hosting Plans']
    breakdown_values = [float(total_subscriptions_cost), float(total_addons_cost)] if total_addons_cost > 0 else [float(total_subscriptions_cost)]
    
    context = {
        'client': client,
        'subscriptions': subscriptions,
        'addons': active_addons,
        'active_subscriptions': subscriptions.filter(status='active').count(),
        'addons_count': active_addons.count(),
        'total_spending': sum(Decimal(str(inv.total_amount)) for inv in Invoice.objects.filter(
            subscription__client=client,
            status='paid'
        )),
        'avg_monthly_cost': client.monthly_cost,
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_data': json.dumps(monthly_values),
        'breakdown_labels': json.dumps(breakdown_labels),
        'breakdown_data': json.dumps(breakdown_values),
    }
    
    return render(request, 'dashboard/usage_analytics.html', context)


@login_required(login_url='login_view')
def client_onboarding(request):
    """Onboarding for new clients"""
    # Check if client already exists
    try:
        client = request.user.client_profile
        return redirect('dashboard:dashboard_home')
    except Client.DoesNotExist:
        pass
    
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        city = request.POST.get('city', '')
        country = request.POST.get('country', '')
        vat_number = request.POST.get('vat_number', '')
        website = request.POST.get('website', '')
        state = request.POST.get('state', '')
        
        # Create client profile
        client = Client.objects.create(
            user=request.user,
            company_name=company_name,
            phone=phone,
            address=address,
            city=city,
            country=country,
            vat_number=vat_number or None,
        )
        
        # Update user profile
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.save()
        
        messages.success(request, 'Profile created successfully! You can now create your first subscription.')
        return redirect('dashboard:dashboard_home')
    
    context = {
        'user': request.user,
    }
    
    return render(request, 'dashboard/onboarding.html', context)


# ===== ADMIN MANAGEMENT VIEWS =====

def staff_required(view_func):
    """Decorator to require staff/superuser access"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def admin_dashboard(request):
    """Admin dashboard overview with key metrics"""
    total_clients = Client.objects.count()
    active_subscriptions = Subscription.objects.filter(status='active').count()
    
    pending_invoices = Invoice.objects.filter(status__in=['pending', 'overdue']).count()
    
    # Recent activity
    recent_subscriptions = Subscription.objects.order_by('-created_at')[:5]
    recent_invoices = Invoice.objects.order_by('-issued_date')[:5]
    
    context = {
        'total_clients': total_clients,
        'active_subscriptions': active_subscriptions,
        'total_revenue': total_revenue,
        'pending_invoices': pending_invoices,
        'recent_subscriptions': recent_subscriptions,
        'recent_invoices': recent_invoices,
        'todos': Todo.objects.filter(is_completed=False)
    }
    
    return render(request, 'admin/dashboard.html', context)


@staff_required
def admin_clients(request):
    """Manage all clients"""
    search_query = request.GET.get('q', '')
    clients = Client.objects.all()
    
    if search_query:
        clients = clients.filter(
            Q(company_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    
    context = {
        'clients': clients,
        'search_query': search_query,
    }
    
    return render(request, 'admin/clients_list.html', context)


@staff_required
def admin_client_detail(request, client_id):
    """View and manage specific client"""
    client = get_object_or_404(Client, id=client_id)
    subscriptions = client.subscriptions.all()
    invoices = Invoice.objects.filter(subscription__client=client).order_by('-issued_date')
    context = {
        'client': client,
        'expectedmony': Moneyexpected.objects.filter(raison=client).order_by(-rest),
        'subscriptions': subscriptions,
        'invoices': invoices,
        'total_spending': sum(Decimal(str(inv.total_amount)) for inv in invoices if inv.status == 'paid'),
        'totalexpectedmoney': sum(Decimal(str(em.rest)) for em in Moneyexpected.objects.filter(raison=client)),
    }
    
    return render(request, 'dashboard/client_detail.html', context)


@staff_required
def admin_subscriptions(request):
    """Manage all subscriptions"""
    status_filter = request.GET.get('status', '')
    subscriptions = Subscription.objects.select_related('client', 'software', 'hosting_plan')
    
    if status_filter:
        subscriptions = subscriptions.filter(status=status_filter)
    
    subscriptions = subscriptions.order_by('-created_at')
    
    context = {
        'subscriptions': subscriptions,
        'status_filter': status_filter,
        'status_choices': Subscription.STATUS_CHOICES,
    }
    
    return render(request, 'admin/subscriptions_list.html', context)


@staff_required
def admin_subscription_detail(request, subscription_id):
    """View and manage specific subscription"""
    subscription = get_object_or_404(Subscription, id=subscription_id)
    addons = subscription.addons.filter(is_active=True)
    invoices = subscription.invoices.order_by('-issued_date')
    history = SubscriptionHistory.objects.filter(subscription=subscription).order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'suspend':
            subscription.suspend()
            messages.success(request, f'Subscription suspended.')
        elif action == 'activate':
            subscription.activate()
            messages.success(request, f'Subscription activated.')
        elif action == 'cancel':
            reason = request.POST.get('reason', '')
            subscription.cancel(reason)
            messages.success(request, f'Subscription cancelled.')
        
        return redirect('dashboard:admin_subscription_detail', subscription_id=subscription_id)
    
    context = {
        'subscription': subscription,
        'addons': addons,
        'invoices': invoices,
        'history': history,
    }
    
    return render(request, 'admin/subscription_detail.html', context)


@staff_required
def admin_invoices(request):
    """Manage all invoices"""
    status_filter = request.GET.get('status', '')
    invoices = Invoice.objects.select_related('subscription', 'subscription__client')
    
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    invoices = invoices.order_by('-issued_date')
    
    total_pending = sum(
        Decimal(str(inv.total_amount)) 
        for inv in invoices.filter(status__in=['pending', 'overdue'])
    )
    total_paid = sum(
        Decimal(str(inv.total_amount)) 
        for inv in invoices.filter(status='paid')
    )
    
    context = {
        'invoices': invoices,
        'status_filter': status_filter,
        'total_pending': total_pending,
        'total_paid': total_paid,
        'status_choices': Invoice.INVOICE_STATUS_CHOICES,
    }
    
    return render(request, 'admin/invoices_list.html', context)


@staff_required
def admin_invoice_detail(request, invoice_id):
    """View and manage specific invoice"""
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'mark_paid':
            invoice.status = 'paid'
            invoice.paid_date = timezone.now()
            invoice.save()
            
            SubscriptionHistory.objects.create(
                subscription=invoice.subscription,
                change_type='other',
                description=f'Invoice {invoice.invoice_number} marked as paid',
                user=request.user
            )
            
            messages.success(request, 'Invoice marked as paid.')
        elif action == 'mark_pending':
            invoice.status = 'pending'
            invoice.paid_date = None
            invoice.save()
            messages.success(request, 'Invoice marked as pending.')
        elif action == 'cancel_invoice':
            invoice.status = 'cancelled'
            invoice.save()
            messages.success(request, 'Invoice cancelled.')
        
        return redirect('dashboard:admin_invoice_detail', invoice_id=invoice_id)
    
    context = {
        'invoice': invoice,
    }
    
    return render(request, 'admin/invoice_detail.html', context)


@staff_required
def admin_analytics(request):
    """Admin analytics and reporting"""
    # Revenue analytics
    invoices = Invoice.objects.filter(status='paid')
    total_revenue = sum(Decimal(str(inv.total_amount)) for inv in invoices)
    
    # Monthly revenue
    from datetime import datetime
    now = timezone.now()
    months_data = []
    
    for i in range(11, -1, -1):
        month_start = now - timedelta(days=30*i)
        month_invoices = invoices.filter(
            issued_date__month=month_start.month,
            issued_date__year=month_start.year,
        )
        total = sum(Decimal(str(inv.total_amount)) for inv in month_invoices)
        months_data.append({
            'month': month_start.strftime('%b %Y'),
            'total': float(total)
        })
    
    # Subscription status breakdown
    status_breakdown = {}
    for status, label in Subscription.STATUS_CHOICES:
        count = Subscription.objects.filter(status=status).count()
        status_breakdown[label] = count
    
    # Top clients by revenue
    top_clients = []
    clients = Client.objects.all()
    for client in clients[:10]:
        client_invoices = Invoice.objects.filter(
            subscription__client=client,
            status='paid'
        )
        total = sum(Decimal(str(inv.total_amount)) for inv in client_invoices)
        if total > 0:
            top_clients.append({'client': client, 'total': float(total)})
    
    top_clients.sort(key=lambda x: x['total'], reverse=True)
    
    context = {
        'total_revenue': total_revenue,
        'monthly_labels': json.dumps([d['month'] for d in months_data]),
        'monthly_data': json.dumps([d['total'] for d in months_data]),
        'status_breakdown': status_breakdown,
        'top_clients': top_clients[:5],
        'total_subscriptions': Subscription.objects.count(),
        'active_subscriptions': Subscription.objects.filter(status='active').count(),
        'total_clients': Client.objects.count(),
    }
    
    return render(request, 'admin/analytics.html', context)


def money_expected_details(request):
    id=request.GET.get('id')
    inbalance=Inbalance.objects.filter(moneyexpected_id=id)
    return JsonResponse(list(inbalance.values()), safe=False)

def services(request):
    ctx = {
        'hostings': HostingPlan.objects.filter(is_active=True).order_by('monthly_price'),
        'addons': Addon.objects.filter(is_active=True).order_by('monthly_price'),
    }
    return render(request, 'dashboard/services.html', ctx)