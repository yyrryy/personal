import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from dashboard.models import Profile, Outraisons, Inbalance, Outbalance, Activity, Depense, Essance, Node, Moneyexpected,Client
from django.http import JsonResponse
from itertools import chain
from datetime import date, timedelta
from django.db.models import Sum
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
def home(request):
    return render(request, 'main/home5.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Get user profile to check user type
            try:
                profile = user.profile
                if profile.user_type == 'client':
                    return redirect('main:client_dashboard')
                elif profile.user_type in ['admin', 'superadmin']:
                    return redirect('main:admin_dashboard')
            except Profile.DoesNotExist:
                # If no profile exists, create one with default client type
                Profile.objects.create(user=user, user_type='client')
                return redirect('main:client_dashboard')
            
            # Fallback to main if user type is unexpected
            return redirect('main')
        else:
            context = {'error': 'اسم المستخدم أو كلمة المرور غير صحيح'}
            return render(request, 'main/login.html', context)
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if profile.user_type == 'client':
                return redirect('main:client_dashboard')
            elif profile.user_type in ['admin', 'superadmin']:
                return redirect('main:admin_dashboard')
        except Profile.DoesNotExist:
            # If no profile exists, create one with default client type
            Profile.objects.create(user=request.user, user_type='client')
            return redirect('main:client_dashboard')
    return render(request, 'main/login.html')

def logout_view(request):
    """Logout user and redirect to home"""
    logout(request)
    return redirect('main:home')

CACHE_KEY = "hosting_sizes"
CACHE_TIMEOUT = 60 * 60 * 12  # 12 hours
def get_env_float(name, default=None):
    value = os.environ.get(name)

    if value is None:
        if default is not None:
            return default
        raise ValueError(f"{name} is not configured.")

    try:
        return float(value)
    except ValueError:
        raise ValueError(f"{name} must be a number.")


def get_env_value(name):
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is not configured.")
    return value


def choose_package(request):
    return render(request, 'main/choose_package.html')

@login_required(login_url='login')
def client_dashboard(request):
    """Client dashboard view"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = Profile.objects.create(user=request.user, user_type='client')
    client=Client.objects.get(user=request.user)
    # Get client subscriptions or relevant data
    context = {
        'user': request.user,
        'profile': profile,
        'expectedmony': Moneyexpected.objects.filter(raison=client),
        'totalexpectedmoney': sum(em.rest for em in Moneyexpected.objects.filter(raison=client)),
    }
    return render(request, 'dashboard/client_dashboard.html', context)

@login_required(login_url='login')
def admin_dashboard(request):
    """Admin/SuperAdmin dashboard view"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return redirect('main:client_dashboard')
    
    # Check if user is admin or superadmin
    if profile.user_type not in ['admin', 'superadmin']:
        return redirect('main:client_dashboard')
    expectedmoney=Moneyexpected.objects.all().order_by('-rest')
    # Get admin stats
    context = {
        'user': request.user,
        'profile': profile,
        'is_superadmin': profile.user_type == 'superadmin',
        'is_admin': profile.user_type == 'admin',
        'totalmoneyexpected':expectedmoney.aggregate(total=Sum('rest'))['total'] or 0,
        'expectedmoney': expectedmoney
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

# API Endpoints for AJAX

@login_required(login_url='login')
@csrf_exempt
def api_create_client(request):
    """Create a new client via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    # Check if user is admin or superadmin
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if request.method == 'POST':
        from django.contrib.auth.models import User
        
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        company_name = request.POST.get('company_name')
        company_type = request.POST.get('company_type')
        
        # Validate required fields
        if not all([username, email, password]):
            return JsonResponse({'success': False, 'error': 'حقول مطلوبة مفقودة'})
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'اسم المستخدم موجود بالفعل'})
        
        # Check if email exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'البريد الإلكتروني موجود بالفعل'})
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=full_name
            )
            
            # Create profile
            Profile.objects.create(
                user=user,
                user_type='client',
                phone=phone,
                company_name=company_name,
                company_type=company_type
            )
            
            return JsonResponse({'success': True, 'message': 'تم إنشاء العميل بنجاح'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='login')
def api_get_clients(request):
    """Get list of all clients via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    from django.contrib.auth.models import User
    
    clients = []
    for client in Client.objects.all():
        clients.append({
            'id': client.id,
            'name': client.name,
            'company_name': client.company_name,
            'email': client.user.email,
            'phone': client.phone,
            'country': client.country,
            'is_verified': client.is_verified,

        })
    
    return JsonResponse({'success': True, 'clients': clients})

@login_required(login_url='login')
@csrf_exempt
def api_create_subscription(request):
    """Create a new subscription via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if request.method == 'POST':
        
        client_id = request.POST.get('client')
        software_id = request.POST.get('software')
        hosting_plan_id = request.POST.get('hosting_plan')
        start_date = request.POST.get('start_date')
        
        if not all([client_id, software_id, hosting_plan_id, start_date]):
            return JsonResponse({'success': False, 'error': 'حقول مطلوبة مفقودة'})
        
        try:
            # Get related objects
            client = Client.objects.get(id=client_id)
            software = Software.objects.get(id=software_id)
            hosting_plan = HostingPlan.objects.get(id=hosting_plan_id)
            
            # Create subscription
            subscription = Subscription.objects.create(
                client=client,
                software=software,
                hosting_plan=hosting_plan,
                status='active'
            )
            
            return JsonResponse({'success': True, 'message': 'تم إنشاء الاشتراك بنجاح'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='login')
def api_get_subscriptions(request):
    """Get list of all subscriptions via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    from dashboard.models import Subscription
    
    subscriptions = []
    for sub in Subscription.objects.select_related('software', 'hosting_plan', 'client'):
        subscriptions.append({
            'id': sub.id,
            'client_name': sub.client.company_name,
            'software_name': sub.software.name if sub.software else 'N/A',
            'price': str(sub.hosting_plan.price) if sub.hosting_plan else '0',
            'status': sub.status,
            'created_at': sub.start_date.isoformat() if sub.start_date else timezone.now().isoformat()
        })
    
    return JsonResponse({'success': True, 'subscriptions': subscriptions})

@login_required(login_url='login')
def api_subscription_options(request):
    """Get options for creating subscription (clients, software, hosting plans)"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    
    # Get clients
    clients = []
    for client in Client.objects.all():
        clients.append({
            'id': client.id,
            'name': client.company_name,
            'email': client.user.email
        })
    
    # Get software
    software_list = []
    for software in Software.objects.filter(is_active=True):
        software_list.append({
            'id': software.id,
            'name': f"{software.emoji} {software.name}",
            'emoji': software.emoji
        })
    
    # Get hosting plans
    hosting_plans = []
    for plan in HostingPlan.objects.filter(is_active=True):
        hosting_plans.append({
            'id': plan.id,
            'name': plan.name,
            'price': str(plan.price),
            'tier': plan.tier
        })
    
    return JsonResponse({
        'success': True,
        'clients': clients,
        'software': software_list,
        'hosting_plans': hosting_plans
    })

@login_required(login_url='login')
@csrf_exempt
def api_create_hosting_plan(request):
    """Create a new hosting plan via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if request.method == 'POST':
        from dashboard.models import HostingPlan
        
        name = request.POST.get('name')
        tier = request.POST.get('tier')
        description = request.POST.get('description')
        price = request.POST.get('price')
        storage_gb = request.POST.get('storage_gb')
        bandwidth_gb = request.POST.get('bandwidth_gb')
        max_users = request.POST.get('max_users')
        uptime_sla = request.POST.get('uptime_sla', '99.90')
        is_active = request.POST.get('is_active') == 'on'
        is_recommended = request.POST.get('is_recommended') == 'on'
        
        if not all([name, tier, description, price, storage_gb, bandwidth_gb]):
            return JsonResponse({'success': False, 'error': 'حقول مطلوبة مفقودة'})
        
        try:
            plan = HostingPlan.objects.create(
                name=name,
                tier=tier,
                description=description,
                price=price,
                storage_gb=int(storage_gb),
                bandwidth_gb=int(bandwidth_gb),
                max_users=int(max_users) if max_users else None,
                uptime_sla=uptime_sla,
                is_active=is_active,
                is_recommended=is_recommended
            )
            return JsonResponse({'success': True, 'message': 'تم إنشاء الخطة بنجاح'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='login')
@csrf_exempt
def api_update_hosting_plan(request):
    """Update a hosting plan via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if request.method == 'POST':
        from dashboard.models import HostingPlan
        
        plan_id = request.POST.get('hosting_plan_id')
        if not plan_id:
            return JsonResponse({'success': False, 'error': 'Plan ID required'})
        
        try:
            plan = HostingPlan.objects.get(id=plan_id)
            
            # Update fields
            plan.name = request.POST.get('name', plan.name)
            plan.tier = request.POST.get('tier', plan.tier)
            plan.description = request.POST.get('description', plan.description)
            plan.price = request.POST.get('price', plan.price)
            plan.storage_gb = int(request.POST.get('storage_gb', plan.storage_gb))
            plan.bandwidth_gb = int(request.POST.get('bandwidth_gb', plan.bandwidth_gb))
            
            max_users = request.POST.get('max_users')
            plan.max_users = int(max_users) if max_users else None
            
            plan.uptime_sla = request.POST.get('uptime_sla', plan.uptime_sla)
            plan.is_active = request.POST.get('is_active') == 'on'
            plan.is_recommended = request.POST.get('is_recommended') == 'on'
            
            plan.save()
            return JsonResponse({'success': True, 'message': 'تم تحديث الخطة بنجاح'})
        except HostingPlan.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'خطة غير موجودة'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='login')
def api_get_hosting_plans(request):
    """Get list of all hosting plans via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    from dashboard.models import HostingPlan
    
    hosting_plans = []
    for plan in HostingPlan.objects.all().order_by('price'):
        hosting_plans.append({
            'id': plan.id,
            'name': plan.name,
            'tier': plan.tier,
            'description': plan.description,
            'price': str(plan.price),
            'storage_gb': plan.storage_gb,
            'bandwidth_gb': plan.bandwidth_gb,
            'max_users': plan.max_users,
            'uptime_sla': str(plan.uptime_sla),
            'is_active': plan.is_active,
            'is_recommended': plan.is_recommended,
            'created_at': plan.created_at.isoformat()
        })
    
    return JsonResponse({'success': True, 'hosting_plans': hosting_plans})

@login_required(login_url='login')
@csrf_exempt
def api_create_addon(request):
    """Create a new addon via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if request.method == 'POST':
        from dashboard.models import Addon
        from django.utils.text import slugify
        
        name = request.POST.get('name')
        addon_type = request.POST.get('addon_type')
        description = request.POST.get('description')
        price = request.POST.get('price')
        emoji = request.POST.get('emoji', '⭐')
        max_quantity = request.POST.get('max_quantity')
        is_active = request.POST.get('is_active') == 'on'
        is_required = request.POST.get('is_required') == 'on'
        
        if not all([name, addon_type, description, price]):
            return JsonResponse({'success': False, 'error': 'حقول مطلوبة مفقودة'})
        
        try:
            slug = slugify(name)
            # Ensure unique slug
            count = Addon.objects.filter(slug__startswith=slug).count()
            if count > 0:
                slug = f"{slug}-{count}"
            
            addon = Addon.objects.create(
                name=name,
                slug=slug,
                addon_type=addon_type,
                description=description,
                price=price,
                emoji=emoji,
                max_quantity=int(max_quantity) if max_quantity else None,
                is_active=is_active,
                is_required=is_required
            )
            return JsonResponse({'success': True, 'message': 'تم إنشاء الإضافة بنجاح'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='login')
@csrf_exempt
def api_update_addon(request):
    """Update an addon via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if request.method == 'POST':
        from dashboard.models import Addon
        
        addon_id = request.POST.get('addon_id')
        if not addon_id:
            return JsonResponse({'success': False, 'error': 'Addon ID required'})
        
        try:
            addon = Addon.objects.get(id=addon_id)
            
            # Update fields
            addon.name = request.POST.get('name', addon.name)
            addon.addon_type = request.POST.get('addon_type', addon.addon_type)
            addon.description = request.POST.get('description', addon.description)
            addon.price = request.POST.get('price', addon.price)
            addon.emoji = request.POST.get('emoji', addon.emoji)
            
            max_quantity = request.POST.get('max_quantity')
            addon.max_quantity = int(max_quantity) if max_quantity else None
            
            addon.is_active = request.POST.get('is_active') == 'on'
            addon.is_required = request.POST.get('is_required') == 'on'
            
            addon.save()
            return JsonResponse({'success': True, 'message': 'تم تحديث الإضافة بنجاح'})
        except Addon.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'إضافة غير موجودة'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='login')
def api_get_addons(request):
    """Get list of all addons via AJAX"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    if profile.user_type not in ['admin', 'superadmin']:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    from dashboard.models import Addon
    
    addons = []
    for addon in Addon.objects.all().order_by('addon_type', 'name'):
        addons.append({
            'id': addon.id,
            'name': addon.name,
            'slug': addon.slug,
            'addon_type': addon.addon_type,
            'description': addon.description,
            'price': str(addon.price),
            'emoji': addon.emoji,
            'is_active': addon.is_active,
            'is_required': addon.is_required,
            'max_quantity': addon.max_quantity,
            'created_at': addon.created_at.isoformat()
        })
    
    return JsonResponse({'success': True, 'addons': addons})


    if not isinstance(extras, dict):
        return "Aucun"

    labels = {
        "domain": "Nom de domaine",
        "ssl": "Certificat SSL",
        "backup": "Backup automatisé",
        "maintenance": "Maintenance",
        "monitoring": "Monitoring",
        "email": "Email pro",
        "sauvegarde": "Sauvegarde locale",
        "maintenance_local": "Maintenance locale",
        "support_prioritaire": "Support prioritaire",
    }
    selected = []
    for key, label in labels.items():
        extra = extras.get(key) or {}
        if extra.get("chosen"):
            line = label
            if key == "domain":
                domain_name = str(extra.get("name") or "").strip()
                if domain_name:
                    line = f"{line} ({domain_name})"
            price = str(extra.get("price") or "").strip()
            if price:
                line = f"{line} - {price}"
            selected.append(line)
    return ", ".join(selected) if selected else "Aucun"


def build_contact_message(payload):
    nom = str(payload.get("nom") or "").strip()
    telephone = str(payload.get("telephone") or "").strip()
    entreprise = str(payload.get("entreprise") or "").strip()
    logiciel = str(payload.get("logiciel") or "").strip()
    hebergement = str(payload.get("hebergement") or "").strip()
    message = str(payload.get("message") or "").strip()
    addons = format_selected_addons(payload.get("extras") or {})

    lines = [
        "Nouvelle demande (assistant de configuration)",
        f"Nom: {nom or '—'}",
        f"Telephone: {telephone or '—'}",
        f"Entreprise: {entreprise or '—'}",
        f"Logiciel: {logiciel or '—'}",
        f"Hebergement: {hebergement or '—'}",
        f"Add-ons: {addons}",
    ]
    if message:
        lines.append(f"Message: {message}")
    return "\n".join(lines)


def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        raise Exception(f"Telegram API error: HTTP {exc.code}")
    except URLError:
        raise Exception("Unable to reach Telegram API")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise Exception("Invalid response from Telegram API")

    if not data.get("ok"):
        raise Exception(data.get("description") or "Telegram API error")


@csrf_exempt
def contact(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)
    print('>> payload', payload)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    missing = []
    for field in ("nom", "telephone"):
        if not str(payload.get(field) or "").strip():
            missing.append(field)
    if missing:
        return JsonResponse(
            {"error": "Missing required fields: " + ", ".join(missing)},
            status=400,
        )

    try:
        token = get_env_value("TELEGRAM_BOT_TOKEN")
        chat_id = get_env_value("TELEGRAM_CHAT_ID")
        message = build_contact_message(payload)
        chatIds=chat_id.split(",")
        for i in chatIds:
            send_telegram_message(token, i, message)
    except ValueError as exc:
        print('>> error', exc)
        return JsonResponse({"error": str(exc)}, status=500)
    except Exception as exc:
        print('>> error', exc)
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({"ok": True})


def fetch_hosting_sizes(token):
    """
    Fetch hosting sizes from provider API.
    Cached for 12 hours.
    """

    # return cached instead of making rewuast
    # cached_sizes = cache.get(CACHE_KEY)
    # if cached_sizes:
    #     return cached_sizes

    req = Request(
        "https://api.digitalocean.com/v2/sizes?per_page=200",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urlopen(req, timeout=10) as response:
            payload = response.read().decode("utf-8")

    except HTTPError as exc:
        raise Exception(f"Hosting API error: HTTP {exc.code}")

    except URLError:
        raise Exception("Unable to reach hosting provider")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise Exception("Invalid response from hosting provider")

    sizes = {
        size.get("slug"): size
        for size in data.get("sizes", [])
    }

    cache.set(CACHE_KEY, sizes, CACHE_TIMEOUT)

    return sizes


def hosting_plans(request):
    try:
        token = os.environ.get("DIGITALOCEAN_TOKEN")

        if not token:
            return JsonResponse(
                {"error": "DIGITALOCEAN_TOKEN is not configured."},
                status=500
            )

        usd_to_dh = get_env_float("DO_USD_TO_DH")

        plan_configs = {
            "starter": {
                "slug": os.environ.get(
                    "DO_SIZE_STARTER",
                    "s-1vcpu-512mb-10gb"
                ),
                "support_hours": 24,
                "recommended_for": "Très petite entreprise",
                "business_margin": 35,
            },
            "growth": {
                "slug": os.environ.get(
                    "DO_SIZE_GROWTH",
                    "s-1vcpu-1gb"
                ),
                "support_hours": 12,
                "recommended_for": "Petite entreprise",
                "business_margin": 40,
            },
            "professional": {
                "slug": os.environ.get(
                    "DO_SIZE_PROFESSIONAL",
                    "s-1vcpu-2gb"
                ),
                "support_hours": 8,
                "recommended_for": "Entreprise active",
                "business_margin": 50,
            },
            "business": {
                "slug": os.environ.get(
                    "DO_SIZE_BUSINESS",
                    "s-2vcpu-2gb"
                ),
                "support_hours": 4,
                "recommended_for": "Entreprise intensive",
                "business_margin": 60,
            },
        }

        sizes = fetch_hosting_sizes(token)

        missing_slugs = [
            config["slug"]
            for config in plan_configs.values()
            if config["slug"] not in sizes
        ]

        if missing_slugs:
            return JsonResponse(
                {
                    "error": (
                        "Missing size slugs: "
                        + ", ".join(missing_slugs)
                    )
                },
                status=502,
            )

        plans = {}

        for key, config in plan_configs.items():
            slug = config["slug"]
            size = sizes[slug]

            provider_monthly_usd = size.get("price_monthly")

            if provider_monthly_usd is None:
                return JsonResponse(
                    {
                        "error": (
                            f"Size {slug} "
                            "has no monthly price."
                        )
                    },
                    status=502,
                )

            provider_monthly_dh = round(
                float(provider_monthly_usd)
                * usd_to_dh
            )

            monthly_sell_price = (
                provider_monthly_dh
                + config["business_margin"]
            )

            plans[key] = {
                "monthly_dh": monthly_sell_price,
                "yearly_dh": monthly_sell_price * 12,

                # infrastructure info
                "vcpus": size.get("vcpus"),
                "memory_mb": size.get("memory"),
                "disk_gb": size.get("disk"),
                "transfer_tb": size.get("transfer"),

                # business info
                "support_hours": config["support_hours"],
                "recommended_for": config["recommended_for"],
            }

        return JsonResponse({
            "currency": "DH",
            "billing_cycles": [
                "monthly",
                "yearly"
            ],
            "plans": plans,
        })

    except ValueError as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=500
        )

    except Exception as exc:
        return JsonResponse(
            {"error": str(exc)},
            status=502
        )
@login_required(login_url='login')
def main(request):
    thismonth=date.today().month
    thisyear=date.today().year
    profile=Profile.objects.get(pk=1)
    essances=list(Essance.objects.all())
    # litters=essances.aggregate(total=Sum('qty'))['total'] or 0
    distance=0
    previouslitter=0
    lastlitter=0
    tt=0
    nextfill=0
    if essances:
        distance=float(essances[-1].km)-float(essances[-2].km)
        previouslitter=essances[-2].qty
        lastlitter=essances[-1].qty
        tt=round((195*essances[-1].qty)/3.75)
        nextfill=tt+essances[-1].km
    print('>> dust', distance, previouslitter)
    totalmoneyexpected = Moneyexpected.objects.aggregate(total=Sum('amount'))['total'] or 0
    # nextfill=(distance*lastlitter)/previouslitter
    # nextfill=round(nextfill+essances[-1].km, 2)
    ageindays=int(profile.age())*365.5
    print('>>', ageindays, profile.age_in_days())
    ageindays=(profile.age_in_days()/21915)*100
    print('>>', ageindays)
    
    # print('litters', litters)
    # perkm=litters/distance
    # print('perkm', perkm)
    # print('perkm', 1.48*perkm)

    previousmonth=thismonth-1
    balancein=Inbalance.objects.all().order_by('-date')
    balanceout=Outbalance.objects.all().order_by('-date')
    # totalfixeddepense=Depense.objects.filter(isfix=True).aggregate(total=Sum('amount'))['total'] or 0
    fromlastmonth=0
    if Inbalance.objects.filter(raison_id=14, date__year=thisyear, date__month=thismonth).exists():
        fromlastmonth=Inbalance.objects.filter(raison_id=14, date__year=thisyear, date__month=thismonth)[0].amount
    totalfixeddepense=Outbalance.objects.filter(date__year=thisyear, date__month=thismonth, raison_id=6).aggregate(total=Sum('amount'))['total'] or 0
    totalthismonthin=balancein.exclude(raison_id=14).filter(date__year=thisyear, date__month=thismonth).aggregate(total=Sum('amount'))['total'] or 0
    totalthismonthout=balanceout.filter(date__year=thisyear, date__month=thismonth).aggregate(total=Sum('amount'))['total'] or 0
    thismonthbalance=totalthismonthin-totalthismonthout
    previousmonthin=balancein.filter(date__year=thisyear, date__month=previousmonth).aggregate(total=Sum('amount'))['total'] or 0
    previousmonthout=balanceout.filter(date__year=thisyear, date__month=previousmonth).aggregate(total=Sum('amount'))['total'] or 0
    previousmonthbalance=previousmonthin-previousmonthout
    for i in balanceout.filter(date__year=thisyear, date__month=thismonth-2):
        print('>>', i.amount, i.note)
    print('previous month out', previousmonthbalance)
    netpreviousmonthbalance=previousmonthbalance-totalfixeddepense
    sold=totalthismonthin+previousmonthbalance
    print('>> previousmonthin', previousmonthin, 'previousmonthout', previousmonthout, 'totalfixeddepense', totalfixeddepense, 'netpreviousmonthbalance', netpreviousmonthbalance)
    # netmonthbalance=thismonthbalance-totalfixeddepense
    # get all outbalances with raison id is 4
    essenceout=Outbalance.objects.filter(date__year=thisyear, date__month=thismonth, raison_id=4).aggregate(total=Sum('amount'))['total'] or 0
    # get days passed in this month and divideessenceout by it
    dayspassed=date.today().day
    essenceoutperday=essenceout/dayspassed
    netmonthbalance=totalthismonthin-totalthismonthout+fromlastmonth
    thismonthessence=round(essenceoutperday*30)
    releve = sorted(
        chain(((inb, 'inb') for inb in balancein.filter(date__year=thisyear, date__month=thismonth)), ((outbb, 'outbb') for outbb in balanceout.filter(date__year=thisyear, date__month=thismonth))),
        key=lambda item: item[0].date,
        reverse=True  # Sort in descending order
    )
    #544R34RR
    totalin=Inbalance.objects.exclude(raison__ignored=True).aggregate(Sum('amount'))['amount__sum']
    totalout=Outbalance.objects.aggregate(Sum('amount'))['amount__sum']
    ctx = {
        'essenceoutperday': essenceoutperday,
        'essenceout': essenceout,
        'nextfill': nextfill,
        'thismonthessence': thismonthessence,
        'previousmonthbalance':previousmonthbalance,
        'title': 'Dashboard',
        'profile': profile,
        'outraisons': Outraisons.objects.all(),
        'clients': Client.objects.all(),
        'releve': releve,
        'thismonthin':totalthismonthin,
        'thismonthout':totalthismonthout,
        'totalfixeddepense':totalfixeddepense,
        'netmonthbalance':netmonthbalance,
        'sold':sold,
        'ageindays':ageindays,
        'fromlastmonth':fromlastmonth,
        "expectedmoney": Moneyexpected.objects.all(),
        'totalmoneyexpected': totalmoneyexpected
    }
    return render(request, 'main/main2.html', ctx)




def addtobalance(request):
    profile=Profile.objects.get(pk=1)

    amountin=request.POST.get('amountin')
    raison=request.POST.get('raisonin')
    Inbalance.objects.create(amount=amountin, raison_id=raison, date=timezone.now())
    inraisons=Client.objects.get(pk=raison)
    if inraisons.rest>0:
        inraisons.rest-=float(amountin)
        inraisons.save()
    profile.balance+=float(amountin)
    profile.save()
    print(amountin, raison)
    return redirect('main:main')

def outbalance(request):
    profile=Profile.objects.get(pk=1)
    amountout=request.POST.get('amountout')
    essaanceprice=request.POST.get('essaanceprice')
    # this will be used as note
    kilomtrage=request.POST.get('kilomtrage')
    raison=request.POST.get('raisonout')
    empty=request.POST.get('empty')=='yes'
    print(amountout, raison, essaanceprice)
    if raison=="4":
        qty=round(float(amountout)/float(essaanceprice), 2)
        Essance.objects.create(price=essaanceprice, amount=amountout, km=kilomtrage,  qty=qty, empty=empty)
    Outbalance.objects.create(amount=amountout, raison_id=raison, note=kilomtrage, date=timezone.now())
    profile.balance-=float(amountout)
    profile.save()
    return redirect('main:main')


def activities(request):
    last_activity = Activity.objects.last()
    if last_activity:
        last_activity_date = last_activity.date
        today = timezone.now().date()
        print("ee", (today - last_activity_date).days)
        if (today - last_activity_date).days > 0:
            # Create missing days
            for day in range((today - last_activity_date).days):
                new_activity_date = last_activity_date + timedelta(days=day + 1)
                if new_activity_date <= today:
                    Activity.objects.create(date=new_activity_date, events="missed fajr")
                    print(new_activity_date)
    ctx={
        'title':'Acttivities',
        'activities':Activity.objects.all().order_by('-date')[:30]
    }
    return render(request, 'main/activities.html', ctx)

def createactivity(request):
    today = date.today()

    todayact=Activity.objects.filter(date=today)
    if not todayact:
        Activity.objects.create()
    return JsonResponse({
        'done':True
    })

def updateactiv(request):
    id=request.GET.get('id')
    activity=request.GET.get('activity')
    act=Activity.objects.get(pk=id)
    if activity=='mast':
        print('>> mast')
        act.mast+=1
    else:
        setattr(act, activity, not getattr(act, activity))
    act.save()
    return JsonResponse({
        'done':True
    })

def updatewaketime(request):
    id=request.GET.get('id')
    time=request.GET.get('time')
    act=Activity.objects.get(pk=id)
    act.wake=time
    act.save()
    return JsonResponse({
        'success':True
    })

def updatesleeptime(request):
    id=request.GET.get('id')
    time=request.GET.get('time')
    act=Activity.objects.get(pk=id)
    if time:
        act.sleep=time
    else:
        act.sleep=None
    act.save()
    print(">> time", time)
    return JsonResponse({
        'success':True
    })

def addevents(request):
    id=request.GET.get('id')
    events=request.GET.get('events')
    act=Activity.objects.get(pk=id)
    act.events=events
    act.save()
    return JsonResponse({
        'success':True
    })

def getsource(request):
    source=request.GET.get('source')
    balancein=Inbalance.objects.filter(raison=source).order_by('-date')
    total=balancein.aggregate(total=Sum('amount'))
    return JsonResponse({
        'trs':render(request, 'main/source.html', {'releve':balancein}).content.decode('utf-8'),
        'total':total['total'],
        'rest':Client.objects.get(pk=source).rest
    })

def adjustsold(request):
    realsold=request.GET.get('realsold')
    actualsold=request.GET.get('actualsold')
    print('actualsold', actualsold, 'realsold', realsold)
    
    diff=float(actualsold)-float(realsold)
    # just create an outbalance with the diff
    Outbalance.objects.create(amount=diff, raison_id=3, date=timezone.now())

    return JsonResponse({
        'success':True
    })

def quran(request):
    ctx={
        'title':'quran',
    }
    return render(request, 'main/quran.html', ctx)
def tree(request):
    ctx={
        'title':'tree',
    }
    return render(request, 'main/tree3.html', ctx)
def addexpectedmoney(request):
    amount=request.GET.get('amount')
    raison=request.GET.get('raison')
    note=request.GET.get('note')
    Moneyexpected.objects.create(amount=amount, raison_id=raison, note=note, rest=amount)
    return redirect('main:main')

def receiveexpectedmoney(request):
    id=request.GET.get('id')
    amount=request.GET.get('amount')
    money=Moneyexpected.objects.get(pk=id)
    # from_reason = Client.objects.get(pk=money.raison_id,)
    Inbalance.objects.create(moneyexpected=money, amount=amount, raison_id=money.raison_id, note=money.note, date=timezone.now())
    money.rest -= float(amount)
    if money.rest == 0:
        money.paid=True
    money.save()
    # if from_reason.rest > 0:
    #     from_reason.rest -= float(money.amount)
    #     from_reason.save()
    return redirect('dashboard:admin_client_detail', client_id=money.raison_id)
# def getdata(request):
#     villages = Village.objects.all()
#     #"name": village.name,
#     # Serialize the queryset to JSON
#     data = [{"lat": village.lat, "long": village.long, "ishelped": village.ishelped, "isaccessible": village.isaccissible, "habitat": village.habitat} for village in villages]

#     return JsonResponse(data, safe=False)

def deleteexpectedmoney(request):
    id=request.GET.get('id')
    money=Moneyexpected.objects.get(pk=id)
    money.delete()
    return redirect('main:main')