from django.urls import path
from . import views

urlpatterns = [
    # Dashboard main
    path('', views.dashboard_home, name='dashboard_home'),
    path('onboarding/', views.client_onboarding, name='client_onboarding'),
    
    # Subscriptions
    path('subscriptions/', views.subscriptions_list, name='subscriptions_list'),
    path('subscription/<int:subscription_id>/', views.subscription_detail, name='subscription_detail'),
    path('subscription/<int:subscription_id>/upgrade/', views.upgrade_plan, name='upgrade_plan'),
    
    # Add-ons management
    path('subscription/<int:subscription_id>/addon/add/', views.add_addon, name='add_addon'),
    path('subscription/<int:subscription_id>/addon/<int:addon_id>/remove/', views.remove_addon, name='remove_addon'),
    path('subscription/<int:subscription_id>/addon/<int:addon_id>/update/', views.update_addon_quantity, name='update_addon_quantity'),
    
    # Invoices
    path('invoices/', views.invoices_list, name='invoices_list'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    
    # Analytics
    path('analytics/', views.usage_analytics, name='usage_analytics'),
    
    # Profile
    path('profile/', views.profile_settings, name='profile_settings'),
    
    # === ADMIN ROUTES ===
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/clients/', views.admin_clients, name='admin_clients'),
    path('admin/client/<int:client_id>/', views.admin_client_detail, name='admin_client_detail'),
    path('admin/subscriptions/', views.admin_subscriptions, name='admin_subscriptions'),
    path('admin/subscription/<int:subscription_id>/', views.admin_subscription_detail, name='admin_subscription_detail'),
    path('admin/invoices/', views.admin_invoices, name='admin_invoices'),
    path('admin/invoice/<int:invoice_id>/', views.admin_invoice_detail, name='admin_invoice_detail'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
]

