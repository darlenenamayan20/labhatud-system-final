from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from datetime import date
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.db import models
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count
from django.db.models import Avg, Count, Q
from .models import ShopReview, LaundryShop, Order
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

User = get_user_model()

# Admin access key from settings
ADMIN_ACCESS_KEY = getattr(settings, 'ADMIN_ACCESS_KEY', 'LABHATUD-ADMIN-SECRET-2025')


# ========== NOTIFICATION HELPER FUNCTIONS (MOVED TO TOP) ==========

# ========== UPDATED NOTIFICATION HELPER FUNCTIONS (without metadata) ==========

def create_notification(user, notification_type, title, message, order=None):
    """Helper function to create notifications"""
    from .models import Notification
    
    return Notification.objects.create(
        user=user,
        order=order,
        notification_type=notification_type,
        title=title,
        message=message
    )

def notify_customer_about_shop_action(order, action_type, shop_name, additional_info=None):
    """Notify ONLY the customer about shop actions"""
    messages_map = {
        'accepted': {
            'title': 'Order Accepted! ✅',
            'message': f'{shop_name} has accepted your order #{order.order_number}. Your laundry will be processed soon.'
        },
        'rejected': {
            'title': 'Order Rejected ❌',
            'message': f'{shop_name} has rejected your order #{order.order_number}. Reason: {additional_info.get("reason", "Not specified") if additional_info else "Not specified"}'
        },
        'washing': {
            'title': 'Washing Started 🧼',
            'message': f'{shop_name} has started washing your order #{order.order_number}.'
        },
        'drying': {
            'title': 'Drying in Progress 💨',
            'message': f'Your order #{order.order_number} is now in the drying cycle.'
        },
        'ready': {
            'title': 'Ready for Delivery! ✅',
            'message': f'Your order #{order.order_number} is ready for delivery. A rider will be assigned soon.'
        }
    }
    
    info = messages_map.get(action_type, {})
    if info:
        create_notification(
            user=order.customer,
            notification_type=f'order_{action_type}' if action_type in ['accepted', 'rejected'] else action_type,
            title=info['title'],
            message=info['message'],
            order=order
        )

def notify_assigned_rider_about_ready_order(order):
    """Notify ONLY the assigned rider when order is ready for delivery"""
    if order.rider:
        payout = float(order.total_amount) * 0.2
        
        create_notification(
            user=order.rider,
            notification_type='ready_for_delivery',
            title='Order Ready for Pickup! 📦',
            message=f'Order #{order.order_number} from {order.shop.shop_name} is ready for pickup. Payout: ₱{payout:.2f}',
            order=order
        )
        return True
    return False

def notify_customer_about_rider_action(order, action_type, rider_name, rider_phone=None):
    """Notify ONLY the customer about rider actions"""
    messages_map = {
        'accepted': {
            'title': 'Rider Assigned! 🛵',
            'message': f'Rider {rider_name} has accepted your order #{order.order_number}. They will pick it up from the shop soon.'
        },
        'picked_up': {
            'title': 'Order Picked Up 📦',
            'message': f'Rider {rider_name} has picked up your order #{order.order_number} from {order.shop.shop_name}.'
        },
        'out_for_delivery': {
            'title': 'Order Out for Delivery 🚚',
            'message': f'Your order #{order.order_number} is out for delivery! Rider {rider_name} is on the way to your location.'
        },
        'delivered': {
            'title': 'Order Delivered! 🎉',
            'message': f'Your order #{order.order_number} has been delivered by {rider_name}. Thank you for using LabHatud!'
        }
    }
    
    info = messages_map.get(action_type, {})
    if info:
        create_notification(
            user=order.customer,
            notification_type=f'rider_{action_type}',
            title=info['title'],
            message=info['message'],
            order=order
        )

def notify_shop_about_rider_action(order, action_type, rider_name, rider_phone=None):
    """Notify ONLY the shop owner about rider actions"""
    messages_map = {
        'accepted': {
            'title': 'Rider Assigned to Your Order',
            'message': f'Rider {rider_name} has accepted order #{order.order_number} for delivery from your shop.'
        },
        'picked_up': {
            'title': 'Order Picked Up by Rider',
            'message': f'Rider {rider_name} has picked up order #{order.order_number} from your shop.'
        },
        'delivered': {
            'title': 'Order Delivered Successfully',
            'message': f'Order #{order.order_number} has been delivered to {order.customer.get_full_name()} by rider {rider_name}.'
        }
    }
    
    info = messages_map.get(action_type, {})
    if info:
        create_notification(
            user=order.shop.owner,
            notification_type='shop_update',
            title=info['title'],
            message=info['message'],
            order=order
        )

# ========== HELPER FUNCTIONS ==========

def is_admin_user(user):
    """Check if user is admin - for API permissions"""
    return user.is_authenticated and user.role == 'admin'

def redirect_by_role(user):
    """Helper function to redirect based on user role"""
    role_map = {
        'admin': 'admin_dashboard',
        'owner': 'shop_dashboard',
        'rider': 'rider_dashboard',
        'user': 'student_home',
    }
    return redirect(role_map.get(user.role, 'student_home'))

def index_view(request):
    """Landing page view"""
    return render(request, 'index.html')

def login_register_view(request):
    """Combined login & register page view"""
    if request.user.is_authenticated:
        messages.info(request, f'You are currently logged in as {request.user.username} ({request.user.role}). To login with a different account or register a new one, please logout first.')
        return render(request, 'accounts/login_register.html', {
            'already_logged_in': True,
            'current_user': request.user
        })
    return render(request, 'accounts/login_register.html')

def login_view(request):
    if request.method == 'POST':
        username_input = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user_obj = User.objects.get(email=username_input)
            username = user_obj.username
        except User.DoesNotExist:
            username = username_input

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.role in ('owner', 'rider') and not user.is_approved:
                messages.error(request, 'Your account is pending admin approval. Please wait.')
                return redirect('login_register')
            
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect_by_role(user)
        else:
            messages.error(request, 'Invalid username or password.')

    return redirect('login_register')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('reg_username', '').strip()
        email = request.POST.get('reg_email', '').strip()
        password = request.POST.get('reg_password', '')
        confirm_password = request.POST.get('reg_confirm', '')
        first_name = request.POST.get('reg_firstname', '').strip()
        last_name = request.POST.get('reg_lastname', '').strip()
        role = request.POST.get('reg_role', 'user')
        phone = request.POST.get('reg_phone', '').strip()
        address = request.POST.get('reg_address', '').strip()
        birthdate = request.POST.get('reg_birthdate', '')
        gender = request.POST.get('reg_gender', '').strip()
        admin_key = request.POST.get('reg_admin_key', '').strip()
        
        # Validation
        if not username or not email or not password or not first_name or not last_name:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'accounts/login_register.html')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'accounts/login_register.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters!')
            return render(request, 'accounts/login_register.html')
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'accounts/login_register.html')
        
        # Check if email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'accounts/login_register.html')
        
        # Admin role requires valid server-side key
        if role == 'admin':
            if not admin_key or admin_key != ADMIN_ACCESS_KEY:
                messages.error(request, 'Invalid admin access key.')
                return render(request, 'accounts/login_register.html')
        
        try:
            # Create user with only the required fields first
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
            )
            
            # Set optional fields one by one (to avoid field errors)
            if phone:
                user.phone = phone
            if address:
                user.address = address
            if gender:
                user.gender = gender
            if birthdate:
                try:
                    user.birthdate = date.fromisoformat(birthdate)
                except ValueError:
                    pass
            
            # Set approval status based on role
            if role == 'admin':
                user.is_approved = True
                user.is_staff = True
                user.is_superuser = False
            elif role == 'user':
                user.is_approved = True
            else:  # owner or rider
                user.is_approved = False
            
            # Save the user with all the additional fields
            user.save()
            
            # Handle role-specific redirection
            if role in ('owner', 'rider'):
                messages.success(request, f'{role.title()} account created successfully! Your account is pending admin approval.')
                return redirect('login_register')
            
            # Auto-login for regular users and admins
            login(request, user)
            messages.success(request, f'Account created successfully! Welcome, {first_name}!')
            return redirect_by_role(user)
            
        except Exception as e:
            # Check if the user was actually created despite the error
            if User.objects.filter(username=username).exists():
                # User exists, try to login
                user = User.objects.get(username=username)
                if role in ('owner', 'rider'):
                    messages.success(request, f'{role.title()} account created successfully! Your account is pending admin approval.')
                    return redirect('login_register')
                else:
                    login(request, user)
                    messages.success(request, f'Account created successfully! Welcome, {first_name}!')
                    return redirect_by_role(user)
            else:
                # Real error, show message
                print(f"Registration error: {str(e)}")
                messages.error(request, f'Error creating account: {str(e)}')
                return render(request, 'accounts/login_register.html')
    
    return render(request, 'accounts/login_register.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login_register')

@login_required
def rider_dashboard(request):
    if request.user.role != 'rider':
        messages.error(request, 'Access denied. Rider access only.')
        return redirect('student_home')
    
    if not request.user.is_approved:
        messages.error(request, 'Your rider account is pending admin approval.')
        return redirect('login_register')
    
    # Import models here to avoid circular imports
    from .models import Order, Notification
    from django.db.models import Sum
    from datetime import timedelta
    from django.utils import timezone
    import json
    
    # Get pending orders that are ready but have NO rider assigned yet
    pending_orders = Order.objects.filter(
        status__in=['ready', 'accepted'],
        rider__isnull=True
    ).select_related('customer', 'shop').order_by('-created_at')
    
    # ========== FIXED: Include ALL statuses that a rider should see ==========
    # This includes: washing, drying, ready, accepted, rider_accepted, picked_up, out_for_delivery
    # The rider should see the order throughout the entire laundry process
    accepted_orders = Order.objects.filter(
        rider=request.user,
        status__in=['washing', 'drying', 'ready', 'accepted', 'rider_accepted', 'picked_up', 'out_for_delivery']
    ).select_related('customer', 'shop').order_by('-created_at')
    
    # Get all orders for this rider (including completed)
    all_orders = Order.objects.filter(
        rider=request.user
    ).select_related('customer', 'shop').order_by('-created_at')
    
    # Get rider's completed deliveries
    completed_deliveries = Order.objects.filter(
        rider=request.user,
        status='delivered'
    ).select_related('customer', 'shop').order_by('-delivered_at')
    
    # Get schedule orders (future deliveries) - only this rider's orders
    schedule_orders = Order.objects.filter(
        rider=request.user,
        status__in=['washing', 'drying', 'ready', 'accepted', 'rider_accepted', 'picked_up', 'out_for_delivery'],
        pickup_date__gte=timezone.now().date()
    ).select_related('customer', 'shop').order_by('pickup_date', 'pickup_time')
    
    # Calculate earnings (only this rider's delivered orders)
    total_earnings = Order.objects.filter(
        rider=request.user,
        status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    today = timezone.now().date()
    today_earnings = Order.objects.filter(
        rider=request.user,
        status='delivered',
        delivered_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    week_start = today - timedelta(days=today.weekday())
    weekly_earnings = Order.objects.filter(
        rider=request.user,
        status='delivered',
        delivered_at__date__gte=week_start
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    month_start = today.replace(day=1)
    monthly_earnings = Order.objects.filter(
        rider=request.user,
        status='delivered',
        delivered_at__date__gte=month_start
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    today_deliveries = Order.objects.filter(
        rider=request.user,
        status='delivered',
        delivered_at__date=today
    ).count()
    
    completed_today = today_deliveries
    pending_count = pending_orders.count()
    accepted_orders_count = accepted_orders.count()
    total_deliveries_count = completed_deliveries.count()
    all_tasks_count = all_orders.count()
    completed_deliveries_count = completed_deliveries.count()
    
    # Calculate completion rate
    total_assigned = Order.objects.filter(rider=request.user).count()
    if total_assigned > 0:
        completion_rate = int((completed_deliveries_count / total_assigned) * 100)
    else:
        completion_rate = 100
    
    # Weekly chart data for JavaScript
    weekly_chart_data = []
    weekly_amounts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_earnings = Order.objects.filter(
            rider=request.user,
            status='delivered',
            delivered_at__date=day
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        weekly_chart_data.append({
            'day': day.strftime('%a'),
            'amount': float(day_earnings)
        })
        weekly_amounts.append(float(day_earnings))
    
    # Convert to JSON for JavaScript
    weekly_chart_json = json.dumps(weekly_chart_data)
    
    # Find max for scaling (for chart)
    max_earnings = max(weekly_amounts) if weekly_amounts else 1
    
    # Get greeting based on time
    current_hour = timezone.now().hour
    if current_hour < 12:
        greeting = 'morning'
    elif current_hour < 18:
        greeting = 'afternoon'
    else:
        greeting = 'evening'
    
    # Get notifications
    notifications = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).order_by('-created_at')[:10]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    # Debug output
    print("\n" + "="*60)
    print(f"RIDER DASHBOARD DEBUG - User: {request.user.username}")
    print("="*60)
    print(f"Pending orders: {pending_count}")
    print(f"Active orders for THIS rider (including washing/drying): {accepted_orders_count}")
    for o in accepted_orders:
        print(f"  - Order #{o.order_number}: status='{o.status}'")
    print(f"Completed deliveries: {completed_deliveries_count}")
    print("="*60 + "\n")
    
    context = {
        'user': request.user,
        'greeting': greeting,
        'pending_orders': pending_orders,
        'accepted_orders': accepted_orders,
        'all_orders': all_orders,
        'completed_deliveries': completed_deliveries,
        'schedule_orders': schedule_orders,
        'today_deliveries': today_deliveries,
        'today_earnings': float(today_earnings),
        'total_earnings': float(total_earnings),
        'weekly_earnings': float(weekly_earnings),
        'monthly_earnings': float(monthly_earnings),
        'pending_count': pending_count,
        'accepted_orders_count': accepted_orders_count,
        'completed_today': completed_today,
        'total_deliveries_count': total_deliveries_count,
        'all_tasks_count': all_tasks_count,
        'completed_deliveries_count': completed_deliveries_count,
        'completion_rate': completion_rate,
        'avg_rating': 4.9,
        'avg_delivery_time': 25,
        'weekly_chart_data': weekly_chart_data,
        'weekly_chart_json': weekly_chart_json,
        'max_earnings': max_earnings,
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'rider_dashboard.html', context)

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin access only.')
        return redirect('student_home')
    
    # Get additional statistics for the dashboard
    from .models import Order
    from django.db.models import Sum
    from django.utils import timezone
    
    today = timezone.now().date()
    
    # Calculate total revenue from delivered orders
    total_revenue = Order.objects.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Get today's orders count
    orders_today = Order.objects.filter(created_at__date=today).count()
    
    # Get active deliveries (orders that are in progress)
    active_deliveries = Order.objects.filter(
        status__in=['accepted', 'washing', 'drying', 'ready', 'out_for_delivery']
    ).count()
    
    # Get reported issues (you can modify this based on your business logic)
    reported_issues = 2  # This could be from a support ticket system
    
    # Get cancellations today
    cancellations_today = Order.objects.filter(
        status__in=['cancelled', 'rejected'],
        created_at__date=today
    ).count()
    
    context = {
        'user': request.user,
        'total_users': User.objects.count(),
        'total_customers': User.objects.filter(role='user').count(),
        'active_shops': User.objects.filter(role='owner', is_approved=True).count(),
        'active_riders': User.objects.filter(role='rider', is_approved=True).count(),
        'pending_approvals': User.objects.filter(is_approved=False, role__in=['owner', 'rider']).count(),
        'total_orders': Order.objects.count(),
        'total_revenue': total_revenue,
        'orders_today': orders_today,
        'active_deliveries': active_deliveries,
        'reported_issues': reported_issues,
        'cancellations_today': cancellations_today,
        'monthly_revenue': total_revenue,  # For simplicity, using total revenue
    }
    return render(request, 'admin_dashboard.html', context)

# ========== ADMIN USER MANAGEMENT APIs ==========

@login_required
@user_passes_test(is_admin_user)
@require_http_methods(["GET"])
def admin_users_api(request):
    """
    API endpoint for admin to get all users with statistics
    URL: /api/admin/users/
    """
    users = User.objects.all().order_by('-date_joined')
    
    total_users = users.count()
    total_customers = users.filter(role='user').count()
    pending_approvals = users.filter(is_approved=False, role__in=['owner', 'rider']).count()
    active_shops = users.filter(role='owner', is_approved=True, is_active=True).count()
    active_riders = users.filter(role='rider', is_approved=True, is_active=True).count()
    total_owners = users.filter(role='owner').count()
    total_riders = users.filter(role='rider').count()
    
    user_data = []
    for user in users:
        if not user.is_approved:
            status = 'pending'
        elif not user.is_active:
            status = 'suspended'
        else:
            status = 'active'
        
        user_info = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': user.phone or '',
            'role': user.role,
            'status': status,
            'date_joined': user.date_joined.strftime('%Y-%m-%d'),
            'last_active': user.last_login.strftime('%Y-%m-%d') if user.last_login else user.date_joined.strftime('%Y-%m-%d'),
            'total_orders': getattr(user, 'total_orders', 0),
            'address': user.address or '',
            'birthdate': user.birthdate.strftime('%Y-%m-%d') if user.birthdate else None,
            'gender': user.gender or '',
            'is_approved': user.is_approved,
            'is_active': user.is_active,
        }
        
        if user.role == 'owner':
            user_info['business_name'] = getattr(user, 'business_name', '')
            user_info['vehicle_type'] = getattr(user, 'vehicle_type', '')
        elif user.role == 'rider':
            vehicle_info = ''
            if getattr(user, 'vehicle_model', None) and getattr(user, 'plate_number', None):
                vehicle_info = f"{user.vehicle_model} · {user.plate_number}"
            elif getattr(user, 'vehicle_model', None):
                vehicle_info = user.vehicle_model
            elif getattr(user, 'plate_number', None):
                vehicle_info = f"Plate: {user.plate_number}"
            user_info['vehicle_info'] = vehicle_info
            user_info['vehicle_model'] = getattr(user, 'vehicle_model', '')
            user_info['plate_number'] = getattr(user, 'plate_number', '')
        
        user_data.append(user_info)
    
    pending_users = users.filter(is_approved=False, role__in=['owner', 'rider'])
    pending_data = []
    for user in pending_users:
        pending_info = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'role': user.role,
            'phone': user.phone or '',
            'date_joined': user.date_joined.strftime('%Y-%m-%d'),
        }
        
        if user.role == 'owner':
            pending_info['business_name'] = getattr(user, 'business_name', f"{user.first_name}'s Laundry")
            pending_info['vehicle_info'] = None
        elif user.role == 'rider':
            vehicle_info = ''
            if getattr(user, 'vehicle_model', None) and getattr(user, 'plate_number', None):
                vehicle_info = f"{user.vehicle_model} · {user.plate_number}"
            elif getattr(user, 'vehicle_model', None):
                vehicle_info = user.vehicle_model
            pending_info['vehicle_info'] = vehicle_info
            pending_info['business_name'] = None
        
        pending_data.append(pending_info)
    
    stats = {
        'total_users': total_users,
        'total_customers': total_customers,
        'pending_approvals': pending_approvals,
        'active_shops': active_shops,
        'active_riders': active_riders,
        'total_owners': total_owners,
        'total_riders': total_riders,
    }
    
    return JsonResponse({
        'users': user_data,
        'stats': stats,
        'pending': pending_data
    })

@login_required
@user_passes_test(is_admin_user)
def admin_analytics_api(request):
    """API endpoint for admin to get analytics data"""
    from .models import Order, User, LaundryShop
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        range_param = request.GET.get('range', 'week')
        today = timezone.now().date()
        
        # Determine date range
        if range_param == 'today':
            start_date = today
            days = 1
        elif range_param == 'week':
            start_date = today - timedelta(days=7)
            days = 7
        elif range_param == 'month':
            start_date = today - timedelta(days=30)
            days = 30
        else:  # year
            start_date = today - timedelta(days=365)
            days = 12
        
        # Get orders in range
        orders_in_range = Order.objects.filter(created_at__date__gte=start_date)
        
        # Calculate revenue trend
        previous_start = start_date - timedelta(days=days)
        previous_orders = Order.objects.filter(created_at__date__gte=previous_start, created_at__date__lt=start_date)
        
        current_revenue = orders_in_range.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
        previous_revenue = previous_orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
        revenue_trend = int(((current_revenue - previous_revenue) / previous_revenue) * 100) if previous_revenue > 0 else 0
        
        # Orders trend
        current_orders = orders_in_range.count()
        previous_orders_count = previous_orders.count()
        orders_trend = int(((current_orders - previous_orders_count) / previous_orders_count) * 100) if previous_orders_count > 0 else 0
        
        # Active users (users who placed orders in last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        active_users = User.objects.filter(
            orders__created_at__date__gte=thirty_days_ago,
            role='user'
        ).distinct().count()
        
        # Completion rate
        total_orders_all = Order.objects.count()
        delivered_orders = Order.objects.filter(status='delivered').count()
        completion_rate = int((delivered_orders / total_orders_all) * 100) if total_orders_all > 0 else 0
        
        # Generate time series data
        labels = []
        revenue_data = []
        orders_data = []
        users_data = []
        
        if range_param == 'year':
            for i in range(11, -1, -1):
                month = today - timedelta(days=30 * i)
                labels.append(month.strftime('%b %Y'))
                
                month_orders = Order.objects.filter(
                    created_at__year=month.year,
                    created_at__month=month.month
                )
                revenue_data.append(float(month_orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0))
                orders_data.append(month_orders.count())
                
                month_users = User.objects.filter(
                    date_joined__year=month.year,
                    date_joined__month=month.month,
                    role='user'
                ).count()
                users_data.append(month_users)
        else:
            for i in range(days - 1, -1, -1):
                day = today - timedelta(days=i)
                labels.append(day.strftime('%a, %b %d') if days <= 7 else day.strftime('%b %d'))
                
                day_orders = Order.objects.filter(created_at__date=day)
                revenue_data.append(float(day_orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0))
                orders_data.append(day_orders.count())
                
                day_users = User.objects.filter(date_joined__date=day, role='user').count()
                users_data.append(day_users)
        
        # Top shops
        top_shops = LaundryShop.objects.annotate(
            order_count=Count('orders'),
            total_revenue=Sum('orders__total_amount', filter=Q(orders__status='delivered'))
        ).filter(order_count__gt=0).order_by('-order_count')[:5]
        
        shops_data = [{
            'name': shop.shop_name,
            'orders': shop.order_count,
            'revenue': float(shop.total_revenue or 0),
            'rating': float(shop.rating)
        } for shop in top_shops]
        
        # Top riders
        top_riders = User.objects.filter(
            role='rider',
            delivery_orders__isnull=False
        ).annotate(
            deliveries=Count('delivery_orders', filter=Q(delivery_orders__status='delivered')),
            earnings=Sum('delivery_orders__total_amount', filter=Q(delivery_orders__status='delivered'))
        ).filter(deliveries__gt=0).order_by('-deliveries')[:5]
        
        riders_data = [{
            'name': rider.get_full_name() or rider.username,
            'deliveries': rider.deliveries,
            'earnings': float(rider.earnings or 0),
            'rating': 4.9
        } for rider in top_riders]
        
        # Status distribution
        status_counts = {}
        status_choices = [
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('washing', 'Washing'),
            ('drying', 'Drying'),
            ('ready', 'Ready'),
            ('out_for_delivery', 'Out for Delivery'),
            ('delivered', 'Delivered'),
            ('rejected', 'Rejected')
        ]
        
        for status, _ in status_choices:
            count = Order.objects.filter(status=status).count()
            if count > 0:
                status_counts[status] = count
        
        # Payment distribution
        payment_counts = {}
        payment_choices = [
            ('gcash', 'GCash'),
            ('paypal', 'PayPal'),
            ('cod', 'COD')
        ]
        
        for payment, _ in payment_choices:
            count = Order.objects.filter(payment_method=payment).count()
            if count > 0:
                payment_counts[payment] = count
        
        return JsonResponse({
            'success': True,
            'labels': labels,
            'revenue': revenue_data,
            'orders': orders_data,
            'users': users_data,
            'total_revenue': float(current_revenue),
            'total_orders': current_orders,
            'active_users': active_users,
            'completion_rate': completion_rate,
            'revenue_trend': revenue_trend,
            'orders_trend': orders_trend,
            'users_trend': orders_trend,
            'completion_trend': 0,
            'top_shops': shops_data,
            'top_riders': riders_data,
            'status_distribution': status_counts,
            'payment_distribution': payment_counts
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@csrf_exempt
@require_http_methods(["POST"])
def approve_user_api(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        if user.is_approved:
            return JsonResponse({'error': 'User is already approved'}, status=400)
        
        if user.role not in ['owner', 'rider']:
            return JsonResponse({'error': 'Only shop owners and riders need approval'}, status=400)
        
        user.is_approved = True
        user.is_active = True
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{user.get_full_name()} has been approved successfully',
            'user_id': user.id,
            'role': user.role
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@csrf_exempt
@require_http_methods(["POST"])
def reject_user_api(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        if user.is_approved:
            return JsonResponse({'error': 'User is already approved, cannot reject'}, status=400)
        
        username = user.get_full_name() or user.username
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{username}\'s application has been rejected and removed'
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@csrf_exempt
@require_http_methods(["POST"])
def suspend_user_api(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        if user.role == 'admin':
            return JsonResponse({'error': 'Cannot suspend admin users'}, status=400)
        
        if not user.is_active:
            return JsonResponse({'error': 'User is already suspended or inactive'}, status=400)
        
        user.is_active = False
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{user.get_full_name()} has been suspended',
            'user_id': user.id
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@csrf_exempt
@require_http_methods(["POST"])
def reactivate_user_api(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        if user.is_active:
            return JsonResponse({'error': 'User is already active'}, status=400)
        
        user.is_active = True
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{user.get_full_name()} has been reactivated',
            'user_id': user.id
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_user_api(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        if user.role == 'admin':
            admin_count = User.objects.filter(role='admin').count()
            if admin_count <= 1:
                return JsonResponse({'error': 'Cannot delete the last admin user'}, status=400)
        
        username = user.get_full_name() or user.username
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{username} has been permanently deleted'
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
@csrf_exempt
@require_http_methods(["GET"])
def get_user_detail_api(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        user_detail = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': user.phone or '',
            'role': user.role,
            'is_approved': user.is_approved,
            'is_active': user.is_active,
            'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M'),
            'last_login': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
            'address': user.address or '',
            'birthdate': user.birthdate.strftime('%Y-%m-%d') if user.birthdate else None,
            'gender': user.gender or '',
            'total_orders': getattr(user, 'total_orders', 0),
        }
        
        if user.role == 'owner':
            user_detail['business_name'] = getattr(user, 'business_name', '')
            user_detail['vehicle_type'] = getattr(user, 'vehicle_type', '')
        elif user.role == 'rider':
            user_detail['vehicle_type'] = getattr(user, 'vehicle_type', '')
            user_detail['vehicle_model'] = getattr(user, 'vehicle_model', '')
            user_detail['plate_number'] = getattr(user, 'plate_number', '')
        
        return JsonResponse({'user': user_detail})
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    

# ========== LAUNDRY SHOP MANAGEMENT VIEWS ==========

@login_required
def student_home_view(request):
    """Student/Customer Dashboard - Shows all approved laundry shops"""
    if request.user.role != 'user':
        return redirect_by_role(request.user)
    
    from .models import LaundryShop, Order, Notification, ShopService, ShopReview
    
    # Get all approved shops that are open
    shops = LaundryShop.objects.filter(
        owner__is_approved=True,
        is_open=True
    ).select_related('owner').prefetch_related('services')
    
    # Prepare shop data for template with all details
    shops_data = []
    for shop in shops:
        first_service = shop.services.filter(is_available=True).first()
        
        shops_data.append({
            'id': shop.id,
            'shop_name': shop.shop_name,
            'address': shop.address,
            'description': shop.description or 'No description available',
            'shop_phone': shop.shop_phone or shop.owner.phone,
            'shop_email': shop.shop_email or shop.owner.email,
            'days_open': shop.days_open,
            'opening_time': shop.opening_time.strftime('%I:%M %p'),
            'closing_time': shop.closing_time.strftime('%I:%M %p'),
            'is_open': shop.is_open,
            'rating': float(shop.rating),
            'total_reviews': shop.total_reviews,
            'owner_name': shop.owner.get_full_name() or shop.owner.username,
            'rate_per_kg': float(first_service.price_per_kg) if first_service else 50,
            'services': [
                {
                    'type': s.service_type,
                    'name': s.get_service_type_display(),
                    'price': float(s.price_per_kg),
                    'is_available': s.is_available
                } for s in shop.services.filter(is_available=True)
            ]
        })
    
    # Pending orders (waiting for shop approval)
    pending_orders = Order.objects.filter(
        customer=request.user,
        status='pending'
    ).select_related('shop').order_by('-created_at')[:5]
    
    # Active orders (accepted by shop, assigned to rider, or in progress)
    active_orders = Order.objects.filter(
        customer=request.user,
        status__in=['accepted', 'rider_accepted', 'picked_up', 'washing', 'drying', 'ready', 'out_for_delivery']
    ).select_related('shop', 'rider').order_by('-created_at')[:5]
    
    # Delivered orders (completed) - Add has_review from database
    delivered_orders = Order.objects.filter(
        customer=request.user,
        status='delivered'
    ).select_related('shop').order_by('-created_at')[:10]
    
    # Add has_review from the actual database field
    for order in delivered_orders:
        # Check if review exists - use the has_review field
        order.has_review = order.has_review  # This is from the model field
    
    # Rejected orders
    rejected_orders = Order.objects.filter(
        customer=request.user,
        status='rejected'
    ).select_related('shop').order_by('-created_at')[:5]
    
    # Get unread notifications count
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    # Get user stats
    total_orders = Order.objects.filter(customer=request.user).count()
    completed_orders = Order.objects.filter(customer=request.user, status='delivered').count()
    
    context = {
        'shops': shops,
        'shops_data': shops_data,
        'pending_orders': pending_orders,
        'active_orders': active_orders,
        'delivered_orders': delivered_orders,
        'rejected_orders': rejected_orders,
        'unread_count': unread_count,
        'total_orders': total_orders,
        'pending_orders_count': pending_orders.count(),
        'active_orders_count': active_orders.count(),
        'completed_orders': completed_orders,
        'user': request.user,
    }
    return render(request, 'student_home.html', context)

@login_required
def shop_dashboard(request):
    """Shop Owner Dashboard - Manage shop and orders"""
    if request.user.role != 'owner':
        messages.error(request, 'Access denied. Laundry owner access only.')
        return redirect('student_home')
    
    if not request.user.is_approved:
        messages.error(request, 'Your shop account is pending admin approval.')
        return redirect('login_register')
    
    from .models import LaundryShop, ShopService, ShopAddon, Order, Notification
    from django.db.models import Sum
    
    try:
        shop = LaundryShop.objects.get(owner=request.user)
        services = shop.services.all()
        addons = shop.addons.all()
        
        # ALL orders for this shop (for the Orders panel)
        all_orders = Order.objects.filter(shop=shop).order_by('-created_at')
        
        # PENDING orders (waiting for shop approval)
        pending_orders = Order.objects.filter(shop=shop, status='pending').order_by('-created_at')
        
        # PRODUCTION orders (currently being washed/dried OR picked up by rider)
        production_orders = Order.objects.filter(
            shop=shop, 
            status__in=['washing', 'drying', 'picked_up', 'rider_accepted']
        ).order_by('-created_at')
        
        # READY orders (ready for pickup by rider)
        ready_orders = Order.objects.filter(shop=shop, status='ready').order_by('-created_at')
        
        # OUT FOR DELIVERY orders
        out_for_delivery_orders = Order.objects.filter(shop=shop, status='out_for_delivery').order_by('-created_at')
        
        # DELIVERED orders (completed - goes to history)
        delivered_orders = Order.objects.filter(shop=shop, status='delivered').order_by('-created_at')
        
        completed_today = Order.objects.filter(
            shop=shop, 
            status='delivered',
            delivered_at__date=timezone.now().date()
        ).count()
        
        revenue_today = Order.objects.filter(
            shop=shop,
            status='delivered',
            delivered_at__date=timezone.now().date()
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
        
        # Counts for display
        production_count = production_orders.count()
        ready_count = ready_orders.count()
        out_for_delivery_count = out_for_delivery_orders.count()
        
        context = {
            'shop': shop,
            'services': services,
            'addons': addons,
            'all_orders': all_orders,
            'pending_orders': pending_orders,
            'production_orders': production_orders,
            'ready_orders': ready_orders,
            'out_for_delivery_orders': out_for_delivery_orders,
            'delivered_orders': delivered_orders,
            'all_orders_count': all_orders.count(),
            'pending_count': pending_orders.count(),
            'production_count': production_count,
            'ready_count': ready_count,
            'out_for_delivery_count': out_for_delivery_count,
            'completed_today': completed_today,
            'revenue_today': revenue_today,
            'notifications': notifications,
            'user': request.user,
        }
        return render(request, 'laundry_shop.html', context)
        
    except LaundryShop.DoesNotExist:
        shop = LaundryShop.objects.create(
            owner=request.user,
            shop_name=f"{request.user.first_name}'s Laundry Shop" if request.user.first_name else f"{request.user.username}'s Laundry Shop",
            address=request.user.address or 'Cantilan, Surigao del Sur',
            shop_phone=request.user.phone,
            shop_email=request.user.email,
            is_open=True
        )
        
        default_services = [
            ('mixed', 50.00),
            ('whites', 45.00),
            ('delicates', 55.00),
            ('express', 65.00),
        ]
        for service_type, price in default_services:
            ShopService.objects.create(
                shop=shop,
                service_type=service_type,
                price_per_kg=price,
                is_available=True
            )
        
        messages.info(request, 'Welcome! Your shop has been created. Please complete your shop profile.')
        return redirect('shop_dashboard')


# ========== SHOP PROFILE & SETTINGS APIS ==========

@login_required
def update_shop_profile(request):
    """Update shop profile information"""
    if request.method == 'POST':
        if request.user.role != 'owner':
            messages.error(request, 'Access denied.')
            return redirect('student_home')
        
        from .models import LaundryShop
        
        try:
            shop = LaundryShop.objects.get(owner=request.user)
            
            shop.shop_name = request.POST.get('shop_name', shop.shop_name)
            shop.address = request.POST.get('address', shop.address)
            shop.shop_phone = request.POST.get('phone', shop.shop_phone)
            shop.shop_email = request.POST.get('email', shop.shop_email)
            shop.description = request.POST.get('description', shop.description)
            
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.phone = request.POST.get('phone', user.phone)
            user.address = request.POST.get('address', user.address)
            user.email = request.POST.get('email', user.email)
            
            user.save()
            shop.save()
            
            messages.success(request, 'Profile updated successfully!')
            
        except LaundryShop.DoesNotExist:
            messages.error(request, 'Shop not found. Please contact support.')
        
        return redirect('shop_dashboard')
    
    return redirect('shop_dashboard')


@login_required
def save_shop_profile_api(request):
    """API endpoint to save shop profile information"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    from .models import LaundryShop
    
    try:
        shop = request.user.shop
        shop.shop_name = request.POST.get('shop_name', shop.shop_name)
        shop.address = request.POST.get('address', shop.address)
        shop.shop_phone = request.POST.get('phone', shop.shop_phone)
        shop.shop_email = request.POST.get('email', shop.shop_email)
        shop.description = request.POST.get('description', shop.description)
        
        if request.FILES.get('logo'):
            shop.logo = request.FILES['logo']
        
        shop.save()
        
        return JsonResponse({'success': True, 'message': 'Profile saved successfully!'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@csrf_exempt
def save_shop_settings_api(request):
    """API endpoint to save shop settings (hours, services, etc.)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    from .models import LaundryShop, ShopService
    
    try:
        data = json.loads(request.body)
        shop = request.user.shop
        
        shop.days_open = data.get('days_open', shop.days_open)
        
        if data.get('opening_time'):
            shop.opening_time = data.get('opening_time')
        if data.get('closing_time'):
            shop.closing_time = data.get('closing_time')
        
        shop.daily_order_limit = data.get('daily_order_limit', shop.daily_order_limit)
        shop.is_open = data.get('is_open', shop.is_open)
        shop.save()
        
        services_data = data.get('services', [])
        for service_data in services_data:
            try:
                service = ShopService.objects.get(id=service_data['id'], shop=shop)
                service.price_per_kg = service_data['price']
                service.is_available = service_data['is_available']
                service.save()
            except ShopService.DoesNotExist:
                pass
        
        return JsonResponse({'success': True, 'message': 'Settings saved successfully!'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ========== ORDER MANAGEMENT APIS ==========

@login_required
@csrf_exempt
def accept_order_api(request, order_id):
    """Shop owner accepts order - Notifies ONLY customer"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    from .models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        
        if hasattr(request.user, 'shop') and order.shop == request.user.shop:
            order.status = 'accepted'
            order.save()
            
            notify_customer_about_shop_action(order, 'accepted', order.shop.shop_name)
            
            return JsonResponse({
                'success': True, 
                'message': 'Order accepted successfully! Customer has been notified.'
            })
        else:
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
            
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@csrf_exempt
def reject_order_api(request, order_id):
    """API endpoint to reject an order with reason - Notifies customer"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    from .models import Order
    
    try:
        data = json.loads(request.body)
        order = Order.objects.get(id=order_id)
        reason = data.get('reason', '')
        
        if hasattr(request.user, 'shop') and order.shop == request.user.shop:
            order.status = 'rejected'
            order.rejection_reason = reason
            order.save()
            
            notify_customer_about_shop_action(order, 'rejected', order.shop.shop_name, {'reason': reason})
            
            return JsonResponse({'success': True, 'message': 'Order rejected. Customer notified.'})
        else:
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
            
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@csrf_exempt
def update_order_status_api(request, order_id):
    """Shop owner updates laundry progress (washing, drying, ready)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    from .models import Order
    from django.utils import timezone
    
    try:
        data = json.loads(request.body)
        order = Order.objects.get(id=order_id)
        new_status = data.get('status', '')
        
        print(f"=== UPDATE ORDER STATUS ===")
        print(f"Order ID: {order_id}")
        print(f"Order Number: {order.order_number}")
        print(f"Old Status: {order.status}")
        print(f"New Status: {new_status}")
        print(f"Shop Owner: {request.user.username}")
        
        if hasattr(request.user, 'shop') and order.shop == request.user.shop:
            # Update the status
            order.status = new_status
            
            # Set ready_at timestamp when status becomes 'ready'
            if new_status == 'ready':
                order.ready_at = timezone.now()
            
            order.save()
            
            # Verify it was saved
            order.refresh_from_db()
            print(f"Status after save: {order.status}")
            
            if new_status == 'washing':
                notify_customer_about_shop_action(order, 'washing', order.shop.shop_name)
                
            elif new_status == 'drying':
                notify_customer_about_shop_action(order, 'drying', order.shop.shop_name)
                
            elif new_status == 'ready':
                notify_customer_about_shop_action(order, 'ready', order.shop.shop_name)
                
                rider_notified = False
                if order.rider:
                    notify_assigned_rider_about_ready_order(order)
                    rider_notified = True
                
                return JsonResponse({
                    'success': True,
                    'message': f'Order marked as ready! {"Rider notified." if rider_notified else "No rider assigned yet."}',
                    'rider_notified': rider_notified,
                    'new_status': new_status
                })
            
            print(f"Successfully updated order {order.order_number} to {new_status}")
            return JsonResponse({
                'success': True,
                'message': f'Order status updated to {new_status}. Customer notified.',
                'new_status': new_status
            })
        else:
            print(f"Unauthorized: User {request.user.username} does not own shop for order {order.order_number}")
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
            
    except Order.DoesNotExist:
        print(f"Order with ID {order_id} not found")
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        print(f"Error updating order: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@csrf_exempt
def rider_accept_order_api(request, order_id):
    """Rider accepts order - Notifies customer and shop owner"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    if request.user.role != 'rider':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Riders only'}, status=403)
    
    from .models import Order
    
    try:
        # Allow accepting orders that are 'ready' OR 'accepted' with no rider assigned
        order = Order.objects.get(
            id=order_id, 
            status__in=['ready', 'accepted'], 
            rider__isnull=True
        )
        
        order.rider = request.user
        order.status = 'rider_accepted'
        order.save()
        
        rider_name = request.user.get_full_name() or request.user.username
        rider_phone = request.user.phone or 'No phone provided'
        
        notify_customer_about_rider_action(order, 'accepted', rider_name, rider_phone)
        notify_shop_about_rider_action(order, 'accepted', rider_name, rider_phone)
        
        return JsonResponse({
            'success': True,
            'message': 'Order accepted successfully! Customer and shop have been notified.',
            'order_number': order.order_number,
            'rider_name': rider_name,
            'rider_phone': rider_phone
        })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': 'Order not found, already assigned, or not ready for acceptance.'
        }, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@csrf_exempt
def create_booking_api(request):
    """API endpoint to create a new laundry booking - WAITING FOR SHOP APPROVAL"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    from .models import LaundryShop, ShopService, Order, Notification
    
    try:
        data = json.loads(request.body)
        shop = LaundryShop.objects.get(id=data.get('shop_id'))
        
        service = ShopService.objects.get(shop=shop, service_type=data.get('service_type'))
        weight = float(data.get('weight'))
        total = weight * float(service.price_per_kg)
        
        order = Order.objects.create(
            customer=request.user,
            shop=shop,
            service_type=data.get('service_type'),
            weight=weight,
            total_amount=total,
            payment_method=data.get('payment_method'),
            special_instructions=data.get('instructions', ''),
            pickup_date=data.get('pickup_date'),
            pickup_time=data.get('pickup_time'),
            pickup_address=data.get('pickup_address', shop.address),
            status='pending'
        )
        
        # Notify shop owner
        create_notification(
            user=shop.owner,
            notification_type='new_order',
            title='New Order Received! 🧺',
            message=f'New order #{order.order_number} from {request.user.get_full_name() or request.user.username}. Please review and accept/reject.',
            order=order
        )
        
        # Notify customer
        create_notification(
            user=request.user,
            notification_type='status_update',
            title='Order Placed Successfully! 📝',
            message=f'Your order #{order.order_number} has been placed and is waiting for {shop.shop_name} to accept it.',
            order=order
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Booking created successfully! Waiting for shop approval.',
            'order_number': order.order_number,
            'status': 'pending_shop_approval'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ========== NOTIFICATION APIS ==========

@login_required
def get_notifications_api(request):
    """API endpoint to get unread notifications"""
    from .models import Notification
    
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'created_at': notif.created_at.strftime('%I:%M %p'),
            'type': notif.notification_type
        })
    return JsonResponse({'notifications': data})


@login_required
def mark_notification_read_api(request, notification_id):
    """API endpoint to mark a notification as read"""
    from .models import Notification
    
    try:
        notif = Notification.objects.get(id=notification_id, user=request.user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Notification not found'}, status=404)


@login_required
def clear_all_notifications_api(request):
    """API endpoint to clear all notifications for current user"""
    from .models import Notification
    
    Notification.objects.filter(user=request.user).delete()
    return JsonResponse({'success': True})


# ========== SHOP DETAILS API ==========

@login_required
def get_shop_details_api(request, shop_id):
    """API endpoint to get detailed shop information for modal"""
    from .models import LaundryShop
    
    try:
        shop = LaundryShop.objects.get(id=shop_id, owner__is_approved=True)
        services = shop.services.filter(is_available=True)
        
        data = {
            'id': shop.id,
            'name': shop.shop_name,
            'address': shop.address,
            'description': shop.description or '',
            'days_open': shop.days_open,
            'opening_time': shop.opening_time.strftime('%I:%M %p'),
            'closing_time': shop.closing_time.strftime('%I:%M %p'),
            'is_open': shop.is_open,
            'rating': float(shop.rating),
            'total_reviews': shop.total_reviews,
            'logo_url': shop.logo.url if shop.logo else None,
            'shop_phone': shop.shop_phone or shop.owner.phone,
            'shop_email': shop.shop_email or shop.owner.email,
            'services': [{
                'type': s.service_type,
                'name': s.get_service_type_display(),
                'price': float(s.price_per_kg)
            } for s in services]
        }
        return JsonResponse(data)
        
    except LaundryShop.DoesNotExist:
        return JsonResponse({'error': 'Shop not found'}, status=404)


# ========== ORDER TRACKING API ==========

@login_required
def order_tracking_api(request, order_number):
    """API endpoint to get order tracking information"""
    from .models import Order
    
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
        
        order = Order.objects.select_related('shop', 'rider').get(
            order_number=order_number,
            customer=request.user
        )
        
        # Status display mapping for tracking
        status_display_map = {
            'pending': ('Order Placed', 'status-pending'),
            'accepted': ('Order Accepted by Shop', 'status-progress'),
            'rider_accepted': ('Rider Accepted', 'status-progress'),
            'picked_up': ('Picked Up', 'status-progress'),
            'washing': ('Being Washed', 'status-progress'),
            'drying': ('Drying', 'status-progress'),
            'ready': ('Ready for Delivery', 'status-progress'),
            'out_for_delivery': ('Out for Delivery', 'status-progress'),
            'delivered': ('Delivered', 'status-success'),
            'cancelled': ('Cancelled', 'status-cancelled'),
            'rejected': ('Rejected by Shop', 'status-cancelled'),
        }
        
        status_display, status_class = status_display_map.get(order.status, (order.get_status_display(), 'status-progress'))
        
        # Build timestamps for each stage
        timestamps = {
            'placed': order.created_at.strftime('%b %d, %Y %I:%M %p') if order.created_at else ''
        }
        
        # Shop accepted timestamp
        if order.status in ['accepted', 'rider_accepted', 'picked_up', 'washing', 'drying', 'ready', 'out_for_delivery', 'delivered']:
            timestamps['shop_accepted'] = order.updated_at.strftime('%b %d, %Y %I:%M %p') if order.updated_at else ''
        
        # Rider accepted timestamp
        if order.status in ['rider_accepted', 'picked_up', 'washing', 'drying', 'ready', 'out_for_delivery', 'delivered']:
            timestamps['rider_accepted'] = order.updated_at.strftime('%b %d, %Y %I:%M %p') if order.updated_at else ''
        
        # Picked up timestamp
        if order.status in ['picked_up', 'washing', 'drying', 'ready', 'out_for_delivery', 'delivered']:
            timestamps['picked_up'] = order.updated_at.strftime('%b %d, %Y %I:%M %p') if order.updated_at else ''
        
        # Washing started timestamp
        if order.status in ['washing', 'drying', 'ready', 'out_for_delivery', 'delivered']:
            timestamps['washing'] = order.updated_at.strftime('%b %d, %Y %I:%M %p') if order.updated_at else ''
        
        # Drying started timestamp
        if order.status in ['drying', 'ready', 'out_for_delivery', 'delivered']:
            timestamps['drying'] = order.updated_at.strftime('%b %d, %Y %I:%M %p') if order.updated_at else ''
        
        # Ready for delivery timestamp
        if order.status in ['ready', 'out_for_delivery', 'delivered']:
            timestamps['ready'] = order.updated_at.strftime('%b %d, %Y %I:%M %p') if order.updated_at else ''
        
        # Out for delivery timestamp
        if order.status in ['out_for_delivery', 'delivered']:
            timestamps['out_for_delivery'] = order.updated_at.strftime('%b %d, %Y %I:%M %p') if order.updated_at else ''
        
        # Delivered timestamp
        if order.status == 'delivered' and order.delivered_at:
            timestamps['delivered'] = order.delivered_at.strftime('%b %d, %Y %I:%M %p')
        
        data = {
            'order_number': order.order_number,
            'status': order.status,
            'status_display': status_display,
            'status_class': status_class,
            'shop_name': order.shop.shop_name,
            'service_type': order.get_service_type_display(),
            'weight': float(order.weight),
            'total_amount': float(order.total_amount),
            'rider_name': order.rider.get_full_name() if order.rider else None,
            'rider_phone': order.rider.phone if order.rider else None,
            'pickup_address': order.pickup_address,
            'created_at': order.created_at.strftime('%b %d, %Y %I:%M %p'),
            'timestamps': timestamps
        }
        
        return JsonResponse(data)
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except Exception as e:
        print(f"Error in order_tracking_api: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ========== RIDER APIs ==========

@login_required
def get_pending_orders_api(request):
    """API endpoint for riders to get orders ready for pickup (status='accepted')"""
    if request.user.role != 'rider':
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    from .models import Order
    
    pending_orders = Order.objects.filter(
        status='accepted',
        rider__isnull=True
    ).select_related('customer', 'shop', 'shop__owner').order_by('-created_at')
    
    orders_data = []
    for order in pending_orders:
        orders_data.append({
            'id': order.id,
            'order_number': order.order_number,
            'shop_name': order.shop.shop_name,
            'shop_address': order.shop.address,
            'pickup_address': order.pickup_address,
            'customer_name': order.customer.get_full_name() or order.customer.username,
            'customer_phone': order.customer.phone or 'N/A',
            'weight': float(order.weight),
            'service_type': order.get_service_type_display(),
            'total_amount': float(order.total_amount),
            'estimated_payout': float(order.total_amount) * 0.2,
            'pickup_date': order.pickup_date.strftime('%b %d, %Y'),
            'pickup_time': order.pickup_time.strftime('%I:%M %p'),
            'created_at': order.created_at.strftime('%I:%M %p'),
            'special_instructions': order.special_instructions or ''
        })
    
    return JsonResponse({
        'success': True,
        'orders': orders_data,
        'total_pending': len(orders_data)
    })


@login_required
def get_rider_notifications_api(request):
    """API endpoint for riders to get their notifications"""
    if request.user.role != 'rider':
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    from .models import Notification
    
    notifications = Notification.objects.filter(
        user=request.user, 
        is_read=False
    ).order_by('-created_at')[:20]
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'created_at': notif.created_at.strftime('%I:%M %p'),
            'type': notif.notification_type,
            'order_number': notif.order.order_number if notif.order else None
        })
    
    return JsonResponse({'success': True, 'notifications': data, 'count': len(data)})


# ========== UPDATED RIDER UPDATE ORDER STATUS API WITH SHOP PROCESSING VALIDATION ==========

@login_required
@csrf_exempt
def rider_update_order_status_api(request, order_number):
    """Rider updates delivery status (picked_up, out_for_delivery, delivered)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    if request.user.role != 'rider':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Riders only'}, status=403)
    
    from .models import Order
    from django.utils import timezone
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status', '')
        
        print(f"=== RIDER UPDATE STATUS DEBUG ===")
        print(f"Order: {order_number}")
        print(f"Requested new status: {new_status}")
        
        order = Order.objects.get(order_number=order_number)
        
        print(f"Current order status: {order.status}")
        print(f"Order rider: {order.rider}")
        print(f"Request user: {request.user}")
        
        if order.rider != request.user:
            return JsonResponse({'success': False, 'message': 'You are not assigned to this order'}, status=403)
        
        # ========== STATUS DISPLAY MAPPING ==========
        status_display_map = {
            'pending': 'Pending Approval',
            'accepted': 'Accepted by Shop',
            'washing': 'Being Washed',
            'drying': 'Drying',
            'ready': 'Ready for Pickup',
            'rider_accepted': 'Accepted by Rider',
            'picked_up': 'Picked Up',
            'out_for_delivery': 'Out for Delivery',
            'delivered': 'Delivered',
            'rejected': 'Rejected'
        }
        
        current_status_display = status_display_map.get(order.status, order.status)
        new_status_display = status_display_map.get(new_status, new_status)
        
        # ========== ALLOWED TRANSITIONS ==========
        allowed_transitions = {
            'ready': ['out_for_delivery'],        # Ready can go directly to out_for_delivery
            'rider_accepted': ['picked_up'],
            'picked_up': ['out_for_delivery'],
            'out_for_delivery': ['delivered'],
        }
        
        # ========== VALIDATION: Check if shop has completed processing ==========
        if new_status == 'out_for_delivery':
            # Check if the shop has ever marked the order as 'ready'
            # The ready_at timestamp is set when shop owner marks order as 'ready'
            if not order.ready_at:
                # If ready_at is not set, check if order status is 'ready'
                # If order status is 'ready', that means shop has completed processing
                if order.status != 'ready':
                    return JsonResponse({
                        'success': False,
                        'message': '❌ Cannot mark as "Out for Delivery". The shop has not finished processing your laundry yet (Washing → Drying → Ready for Delivery). Please wait for the shop to complete the process.'
                    }, status=400)
        
        # ========== CHECK IF STATUS TRANSITION IS ALLOWED ==========
        if order.status not in allowed_transitions:
            return JsonResponse({
                'success': False,
                'message': f'⚠️ Cannot update delivery status. Order is currently "{current_status_display}". Expected status: ready, rider_accepted, picked_up, or out_for_delivery.'
            }, status=400)
        
        # Check if the transition is allowed
        if new_status not in allowed_transitions[order.status]:
            expected = allowed_transitions[order.status]
            expected_text = " → ".join(expected) if expected else "No further updates allowed"
            return JsonResponse({
                'success': False,
                'message': f'⚠️ Invalid status transition. Current status: "{current_status_display}". Next allowed status: {expected_text}'
            }, status=400)
        
        # ========== UPDATE THE STATUS ==========
        old_status = order.status
        order.status = new_status
        
        # Set timestamps
        if new_status == 'delivered':
            order.delivered_at = timezone.now()
        elif new_status == 'picked_up':
            order.picked_up_at = timezone.now()
        elif new_status == 'out_for_delivery':
            order.out_for_delivery_at = timezone.now()
        
        order.save()
        
        print(f"Status updated from {old_status} to {new_status}")
        
        # ========== SEND NOTIFICATIONS ==========
        rider_name = request.user.get_full_name() or request.user.username
        rider_phone = request.user.phone or 'No phone provided'
        
        if new_status == 'picked_up':
            notify_customer_about_rider_action(order, 'picked_up', rider_name, rider_phone)
            notify_shop_about_rider_action(order, 'picked_up', rider_name, rider_phone)
            return JsonResponse({
                'success': True,
                'message': f'✅ Order marked as Picked Up! The customer has been notified.',
                'new_status': new_status
            })
            
        elif new_status == 'out_for_delivery':
            notify_customer_about_rider_action(order, 'out_for_delivery', rider_name, rider_phone)
            return JsonResponse({
                'success': True,
                'message': f'🚚 Order marked as Out for Delivery! The customer has been notified.',
                'new_status': new_status
            })
            
        elif new_status == 'delivered':
            notify_customer_about_rider_action(order, 'delivered', rider_name, rider_phone)
            notify_shop_about_rider_action(order, 'delivered', rider_name, rider_phone)
            return JsonResponse({
                'success': True,
                'message': f'✅ Order marked as Delivered! Thank you for your service.',
                'new_status': new_status
            })
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to "{new_status_display}". Customer notified.',
            'new_status': new_status
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        print(f"Error in rider_update_order_status_api: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def get_order_details_api(request, order_number):
    """API endpoint to get detailed order information for rider dashboard view button"""
    from .models import Order
    
    try:
        order = Order.objects.select_related('customer', 'shop', 'rider').get(
            order_number=order_number
        )
        
        if request.user.role == 'rider':
            if order.rider != request.user and order.status != 'accepted':
                return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        elif request.user.role == 'user':
            if order.customer != request.user:
                return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        elif request.user.role not in ['admin', 'owner']:
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
        
        order_data = {
            'order_number': order.order_number,
            'service_type': order.get_service_type_display(),
            'customer_name': order.customer.get_full_name() or order.customer.username,
            'customer_phone': order.customer.phone or 'N/A',
            'pickup_address': order.pickup_address,
            'shop_name': order.shop.shop_name,
            'pickup_date': order.pickup_date.strftime('%b %d, %Y') if order.pickup_date else '',
            'pickup_time': order.pickup_time.strftime('%I:%M %p') if order.pickup_time else '',
            'weight': float(order.weight),
            'total_amount': f'{order.total_amount:.2f}',
            'status_display': order.get_status_display(),
            'special_instructions': order.special_instructions or '',
        }
        
        return JsonResponse({'success': True, 'order': order_data})
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def get_order_details_by_id_api(request, order_id):
    """API endpoint to get detailed order information by order ID for shop owner"""
    from .models import Order
    
    try:
        order = Order.objects.select_related('customer', 'shop').get(id=order_id)
        
        if hasattr(request.user, 'shop') and order.shop == request.user.shop:
            order_data = {
                'order_number': order.order_number,
                'service_type': order.get_service_type_display(),
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'customer_phone': order.customer.phone or 'N/A',
                'pickup_address': order.pickup_address,
                'shop_name': order.shop.shop_name,
                'pickup_date': order.pickup_date.strftime('%b %d, %Y') if order.pickup_date else '',
                'pickup_time': order.pickup_time.strftime('%I:%M %p') if order.pickup_time else '',
                'weight': float(order.weight),
                'total_amount': f'{order.total_amount:.2f}',
                'status_display': order.get_status_display(),
                'special_instructions': order.special_instructions or '',
            }
            return JsonResponse({'success': True, 'order': order_data})
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ========== RIDER MANAGEMENT APIs FOR SHOP OWNER ==========

@login_required
def get_riders_list_api(request):
    """API endpoint for shop owner to get list of all riders"""
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Shop owners only'}, status=403)
    
    from .models import LaundryShop, Order
    from django.db.models import Count, Q
    
    try:
        shop = LaundryShop.objects.get(owner=request.user)
        
        # Get all approved riders
        riders = User.objects.filter(role='rider', is_approved=True, is_active=True)
        
        rider_data = []
        for rider in riders:
            # Count today's deliveries for this rider from this shop
            today = timezone.now().date()
            today_deliveries = Order.objects.filter(
                rider=rider,
                shop=shop,
                status='delivered',
                delivered_at__date=today
            ).count()
            
            total_deliveries = Order.objects.filter(
                rider=rider,
                shop=shop,
                status='delivered'
            ).count()
            
            # Check if rider has active deliveries for this shop
            active_deliveries = Order.objects.filter(
                rider=rider,
                shop=shop,
                status__in=['accepted', 'rider_accepted', 'picked_up', 'out_for_delivery']
            ).exists()
            
            # Determine rider status
            if active_deliveries:
                status = 'busy'
                status_display = 'On Delivery'
            else:
                status = 'available'
                status_display = 'Available'
            
            rider_data.append({
                'id': rider.id,
                'name': rider.get_full_name() or rider.username,
                'initials': (rider.first_name[0] if rider.first_name else rider.username[0]).upper(),
                'phone': rider.phone or '',
                'email': rider.email,
                'status': status,
                'status_display': status_display,
                'vehicle_type': getattr(rider, 'vehicle_type', 'Motorcycle'),
                'today_deliveries': today_deliveries,
                'total_deliveries': total_deliveries
            })
        
        return JsonResponse({'success': True, 'riders': rider_data})
        
    except LaundryShop.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Shop not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def get_active_deliveries_api(request):
    """API endpoint for shop owner to get active deliveries for their shop"""
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Shop owners only'}, status=403)
    
    from .models import LaundryShop, Order
    
    try:
        shop = LaundryShop.objects.get(owner=request.user)
        
        active_orders = Order.objects.filter(
            shop=shop,
            status__in=['rider_accepted', 'picked_up', 'out_for_delivery']
        ).select_related('customer', 'rider').order_by('-updated_at')
        
        deliveries = []
        for order in active_orders:
            deliveries.append({
                'order_id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'status_display': order.get_status_display(),
                'rider_name': order.rider.get_full_name() or order.rider.username if order.rider else 'Not assigned',
                'rider_initials': (order.rider.first_name[0] if order.rider and order.rider.first_name else 'R').upper() if order.rider else 'R',
                'rider_phone': order.rider.phone if order.rider else '',
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'delivery_address': order.pickup_address,
                'updated_at': order.updated_at.strftime('%I:%M %p'),
            })
        
        today = timezone.now().date()
        today_count = Order.objects.filter(
            shop=shop,
            status='delivered',
            delivered_at__date=today
        ).count()
        
        return JsonResponse({
            'success': True,
            'deliveries': deliveries,
            'today_count': today_count
        })
        
    except LaundryShop.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Shop not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def get_pending_assignments_api(request):
    """API endpoint for shop owner to get orders ready for delivery without rider assigned"""
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Shop owners only'}, status=403)
    
    from .models import LaundryShop, Order
    
    try:
        shop = LaundryShop.objects.get(owner=request.user)
        
        pending_orders = Order.objects.filter(
            shop=shop,
            status='ready',
            rider__isnull=True
        ).select_related('customer').order_by('-created_at')
        
        orders = []
        for order in pending_orders:
            orders.append({
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'customer_initials': (order.customer.first_name[0] if order.customer.first_name else 'C').upper(),
                'customer_phone': order.customer.phone or '',
                'weight': float(order.weight),
                'service_type': order.get_service_type_display(),
                'pickup_address': order.pickup_address,
                'created_at': order.created_at.strftime('%b %d, %Y'),
            })
        
        return JsonResponse({'success': True, 'orders': orders})
        
    except LaundryShop.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Shop not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def assign_rider_to_order_api(request):
    """API endpoint for shop owner to assign a rider to an order"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Shop owners only'}, status=403)
    
    from .models import LaundryShop, Order
    
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        rider_id = data.get('rider_id')
        
        shop = LaundryShop.objects.get(owner=request.user)
        order = Order.objects.get(id=order_id, shop=shop, status='ready', rider__isnull=True)
        rider = User.objects.get(id=rider_id, role='rider', is_approved=True)
        
        # Assign rider to order - Set status to 'accepted' (waiting for rider to accept)
        order.rider = rider
        order.status = 'accepted'  # Change from 'ready' to 'accepted'
        order.save()
        
        # Notify the rider
        create_notification(
            user=rider,
            notification_type='new_assignment',
            title='New Delivery Assignment! 🛵',
            message=f'You have been assigned to deliver order #{order.order_number} from {shop.shop_name}. Please check your dashboard.',
            order=order
        )
        
        # Notify the customer
        notify_customer_about_rider_action(order, 'accepted', rider.get_full_name() or rider.username, rider.phone)
        
        return JsonResponse({
            'success': True,
            'message': f'Rider {rider.get_full_name() or rider.username} has been assigned to order #{order.order_number}'
        })
        
    except LaundryShop.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Shop not found'}, status=404)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found or already assigned'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rider not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@login_required
def notify_rider_api(request):
    """API endpoint for shop owner to send notification to a rider"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)
    
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Shop owners only'}, status=403)
    
    from .models import LaundryShop
    
    try:
        data = json.loads(request.body)
        rider_id = data.get('rider_id')
        message = data.get('message', 'New delivery task available. Please check your dashboard.')
        
        rider = User.objects.get(id=rider_id, role='rider')
        shop = LaundryShop.objects.get(owner=request.user)
        
        create_notification(
            user=rider,
            notification_type='shop_message',
            title=f'Message from {shop.shop_name} 📢',
            message=message,
            order=None
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Notification sent to {rider.get_full_name() or rider.username}'
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rider not found'}, status=404)
    except LaundryShop.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Shop not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def track_rider_deliveries_api(request, rider_id):
    """API endpoint for shop owner to track a rider's deliveries for their shop"""
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Shop owners only'}, status=403)
    
    from .models import LaundryShop, Order
    
    try:
        shop = LaundryShop.objects.get(owner=request.user)
        rider = User.objects.get(id=rider_id, role='rider')
        
        active_deliveries = Order.objects.filter(
            shop=shop,
            rider=rider,
            status__in=['accepted', 'rider_accepted', 'picked_up', 'out_for_delivery']
        ).count()
        
        today = timezone.now().date()
        today_completed = Order.objects.filter(
            shop=shop,
            rider=rider,
            status='delivered',
            delivered_at__date=today
        ).count()
        
        return JsonResponse({
            'success': True,
            'rider_name': rider.get_full_name() or rider.username,
            'active_deliveries': active_deliveries,
            'today_completed': today_completed
        })
        
    except LaundryShop.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Shop not found'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rider not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
def get_rider_deliveries_detail_api(request, rider_id):
    """API endpoint to get detailed delivery information for a specific rider"""
    if request.user.role != 'owner':
        return JsonResponse({'success': False, 'message': 'Unauthorized - Shop owners only'}, status=403)
    
    from .models import LaundryShop, Order
    
    try:
        shop = LaundryShop.objects.get(owner=request.user)
        rider = User.objects.get(id=rider_id, role='rider')
        
        orders = Order.objects.filter(
            shop=shop,
            rider=rider
        ).select_related('customer').order_by('-created_at')[:20]
        
        order_list = []
        for order in orders:
            order_list.append({
                'order_number': order.order_number,
                'status': order.get_status_display(),
                'customer': order.customer.get_full_name() or order.customer.username,
                'total_amount': float(order.total_amount),
                'created_at': order.created_at.strftime('%b %d, %Y'),
                'delivered_at': order.delivered_at.strftime('%b %d, %Y %I:%M %p') if order.delivered_at else 'Not delivered'
            })
        
        return JsonResponse({
            'success': True,
            'rider_name': rider.get_full_name() or rider.username,
            'rider_phone': rider.phone or '',
            'total_orders': len(order_list),
            'orders': order_list
        })
        
    except LaundryShop.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Shop not found'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Rider not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    

@login_required
def update_rider_profile(request):
    """Update rider profile information"""
    if request.method == 'POST' and request.user.role == 'rider':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.address = request.POST.get('address', user.address)
        user.save()
        messages.success(request, 'Profile updated successfully!')
    return redirect('rider_dashboard')


@login_required
def update_rider_vehicle(request):
    """Update rider vehicle information"""
    if request.method == 'POST' and request.user.role == 'rider':
        user = request.user
        user.vehicle_type = request.POST.get('vehicle_type', getattr(user, 'vehicle_type', 'Motorcycle'))
        user.vehicle_model = request.POST.get('vehicle_model', '')
        user.plate_number = request.POST.get('plate_number', '')
        user.save()
        messages.success(request, 'Vehicle information updated successfully!')
    return redirect('rider_dashboard')



# ========== ADMIN ORDER MANAGEMENT APIs ==========

@login_required
@user_passes_test(is_admin_user)
def admin_orders_api(request):
    """API endpoint for admin to get all orders with statistics"""
    from .models import Order
    from django.db.models import Sum
    from django.utils import timezone
    
    try:
        # Get all orders
        orders = Order.objects.all().select_related('customer', 'shop', 'rider').order_by('-created_at')
        
        today = timezone.now().date()
        today_orders = orders.filter(created_at__date=today).count()
        
        total_revenue = orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
        
        completed_orders = orders.filter(status='delivered').count()
        total_orders_count = orders.count()
        completion_rate = int((completed_orders / total_orders_count) * 100) if total_orders_count > 0 else 0
        
        active_orders = orders.filter(status__in=['pending', 'accepted', 'washing', 'drying', 'ready', 'out_for_delivery']).count()
        
        # Payment method display mapping
        payment_display_map = {
            'gcash': 'GCash',
            'paypal': 'PayPal',
            'cod': 'COD'
        }
        
        order_data = []
        for order in orders:
            order_data.append({
                'order_number': order.order_number,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'shop_name': order.shop.shop_name,
                'rider_name': order.rider.get_full_name() or order.rider.username if order.rider else None,
                'service_type': order.get_service_type_display(),
                'weight': float(order.weight),
                'total_amount': float(order.total_amount),
                'payment_method': payment_display_map.get(order.payment_method, order.payment_method),
                'status': order.status,
                'pickup_date': order.pickup_date.strftime('%Y-%m-%d') if order.pickup_date else None,
                'pickup_time': order.pickup_time.strftime('%H:%M') if order.pickup_time else None,
                'pickup_address': order.pickup_address[:50] if order.pickup_address else None,
                'special_instructions': order.special_instructions[:50] if order.special_instructions else '',
                'delivered_at': order.delivered_at.strftime('%Y-%m-%d %H:%M') if order.delivered_at else None
            })
        
        stats = {
            'total_orders': total_orders_count,
            'today_orders': today_orders,
            'total_revenue': float(total_revenue),
            'completion_rate': completion_rate,
            'active_orders': active_orders,
        }
        
        return JsonResponse({'success': True, 'orders': order_data, 'stats': stats})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_user)
def admin_order_detail_api(request, order_number):
    """API endpoint for admin to get detailed order information"""
    from .models import Order
    
    try:
        order = Order.objects.select_related('customer', 'shop', 'rider').get(order_number=order_number)
        
        # Payment method display mapping
        payment_display_map = {
            'gcash': 'GCash',
            'paypal': 'PayPal',
            'cod': 'COD'
        }
        
        order_data = {
            'order_number': order.order_number,
            'customer_name': order.customer.get_full_name() or order.customer.username,
            'customer_phone': order.customer.phone or 'N/A',
            'shop_name': order.shop.shop_name,
            'rider_name': order.rider.get_full_name() or order.rider.username if order.rider else 'Not assigned',
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'pickup_date': order.pickup_date.strftime('%Y-%m-%d') if order.pickup_date else 'N/A',
            'pickup_time': order.pickup_time.strftime('%I:%M %p') if order.pickup_time else 'N/A',
            'pickup_address': order.pickup_address,
            'service_type': order.get_service_type_display(),
            'weight': float(order.weight),
            'total_amount': float(order.total_amount),
            'payment_method': payment_display_map.get(order.payment_method, order.payment_method),
            'status': order.status,
            'status_display': order.get_status_display(),
            'special_instructions': order.special_instructions or '',
            'delivered_at': order.delivered_at.strftime('%Y-%m-%d %H:%M') if order.delivered_at else None,
        }
        
        return JsonResponse({'success': True, 'order': order_data})
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
# Add to your views.py

@login_required
@user_passes_test(is_admin_user)
def admin_analytics_api(request):
    """API endpoint for admin to get analytics data"""
    from .models import Order, User, LaundryShop
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        range_param = request.GET.get('range', 'week')
        today = timezone.now().date()
        
        # Determine date range
        if range_param == 'today':
            start_date = today
            days = 1
        elif range_param == 'week':
            start_date = today - timedelta(days=7)
            days = 7
        elif range_param == 'month':
            start_date = today - timedelta(days=30)
            days = 30
        else:  # year
            start_date = today - timedelta(days=365)
            days = 12
        
        # Get orders in range
        orders_in_range = Order.objects.filter(created_at__date__gte=start_date)
        
        # Calculate revenue trend
        previous_start = start_date - timedelta(days=days)
        previous_orders = Order.objects.filter(created_at__date__gte=previous_start, created_at__date__lt=start_date)
        
        current_revenue = orders_in_range.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
        previous_revenue = previous_orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
        revenue_trend = int(((current_revenue - previous_revenue) / previous_revenue) * 100) if previous_revenue > 0 else 0
        
        # Orders trend
        current_orders = orders_in_range.count()
        previous_orders_count = previous_orders.count()
        orders_trend = int(((current_orders - previous_orders_count) / previous_orders_count) * 100) if previous_orders_count > 0 else 0
        
        # Active users (users who placed orders in last 30 days)
        active_users = User.objects.filter(
            orders__created_at__date__gte=timezone.now().date() - timedelta(days=30),
            role='user'
        ).distinct().count()
        
        # Completion rate
        total_orders_all = Order.objects.count()
        delivered_orders = Order.objects.filter(status='delivered').count()
        completion_rate = int((delivered_orders / total_orders_all) * 100) if total_orders_all > 0 else 0
        
        # Generate time series data
        labels = []
        revenue_data = []
        orders_data = []
        users_data = []
        
        if range_param == 'year':
            for i in range(11, -1, -1):
                month = today - timedelta(days=30 * i)
                labels.append(month.strftime('%b %Y'))
                
                month_orders = Order.objects.filter(
                    created_at__year=month.year,
                    created_at__month=month.month
                )
                revenue_data.append(float(month_orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0))
                orders_data.append(month_orders.count())
                
                month_users = User.objects.filter(
                    date_joined__year=month.year,
                    date_joined__month=month.month,
                    role='user'
                ).count()
                users_data.append(month_users)
        else:
            for i in range(days - 1, -1, -1):
                day = today - timedelta(days=i)
                labels.append(day.strftime('%a, %b %d') if days <= 7 else day.strftime('%b %d'))
                
                day_orders = Order.objects.filter(created_at__date=day)
                revenue_data.append(float(day_orders.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0))
                orders_data.append(day_orders.count())
                
                day_users = User.objects.filter(date_joined__date=day, role='user').count()
                users_data.append(day_users)
        
        # Top shops
        top_shops = LaundryShop.objects.annotate(
            order_count=Count('orders'),
            total_revenue=Sum('orders__total_amount', filter=Q(orders__status='delivered'))
        ).filter(order_count__gt=0).order_by('-order_count')[:5]
        
        shops_data = [{
            'name': shop.shop_name,
            'orders': shop.order_count,
            'revenue': float(shop.total_revenue or 0),
            'rating': float(shop.rating)
        } for shop in top_shops]
        
        # Top riders
        top_riders = User.objects.filter(
            role='rider',
            delivery_orders__isnull=False
        ).annotate(
            deliveries=Count('delivery_orders', filter=Q(delivery_orders__status='delivered')),
            earnings=Sum('delivery_orders__total_amount', filter=Q(delivery_orders__status='delivered'))
        ).filter(deliveries__gt=0).order_by('-deliveries')[:5]
        
        riders_data = [{
            'name': rider.get_full_name() or rider.username,
            'deliveries': rider.deliveries,
            'earnings': float(rider.earnings or 0),
            'rating': 4.9
        } for rider in top_riders]
        
        # Status distribution
        status_counts = {}
        for status, _ in Order.STATUS_CHOICES:
            count = Order.objects.filter(status=status).count()
            if count > 0:
                status_counts[status] = count
        
        # Payment distribution
        payment_counts = {}
        for payment, _ in Order.PAYMENT_CHOICES:
            count = Order.objects.filter(payment_method=payment).count()
            if count > 0:
                payment_counts[payment] = count
        
        return JsonResponse({
            'success': True,
            'labels': labels,
            'revenue': revenue_data,
            'orders': orders_data,
            'users': users_data,
            'total_revenue': float(current_revenue),
            'total_orders': current_orders,
            'active_users': active_users,
            'completion_rate': completion_rate,
            'revenue_trend': revenue_trend,
            'orders_trend': orders_trend,
            'users_trend': orders_trend,
            'completion_trend': 0,
            'top_shops': shops_data,
            'top_riders': riders_data,
            'status_distribution': status_counts,
            'payment_distribution': payment_counts
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def order_status_updates_api(request):
    """Get status updates for user's orders"""
    try:
        from .models import Order
        
        # Get user's recent orders (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        orders = Order.objects.filter(
            customer=request.user,
            created_at__gte=thirty_days_ago
        ).order_by('-updated_at')[:20]
        
        updates = []
        for order in orders:
            shop_name = None
            if hasattr(order, 'shop') and order.shop:
                shop_name = order.shop.shop_name if hasattr(order.shop, 'shop_name') else str(order.shop)
            
            updates.append({
                'order_id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'status_display': order.get_status_display(),
                'shop_name': shop_name,
                'updated_at': order.updated_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'updates': updates
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def shop_announcements_api(request):
    """Get shop announcements and promotions"""
    try:
        from .models import Order
        
        announcements = []
        
        # Check if user has any active orders
        has_active_orders = Order.objects.filter(
            customer=request.user,
            status__in=['pending', 'accepted', 'washing', 'drying', 'ready', 'out_for_delivery']
        ).exists()
        
        # Check if user has any orders at all
        total_orders = Order.objects.filter(customer=request.user).count()
        
        # Welcome announcement for new users without orders
        if total_orders == 0:
            announcements.append({
                'title': '✨ Welcome to LabHatud!',
                'message': 'Get 20% off your first 3 orders! Use code: LABHATUD20',
                'date': datetime.now().isoformat()
            })
        
        # Seasonal promotions
        current_month = datetime.now().month
        if current_month == 12:  # December
            announcements.append({
                'title': '🎄 Holiday Promo',
                'message': '15% off on all services this holiday season!',
                'date': datetime.now().isoformat()
            })
        elif 3 <= current_month <= 5:  # Spring
            announcements.append({
                'title': '🌸 Spring Cleaning',
                'message': 'Get 10% off on all laundry services this spring!',
                'date': datetime.now().isoformat()
            })
        elif 6 <= current_month <= 8:  # Summer
            announcements.append({
                'title': '☀️ Summer Sale',
                'message': 'Get 10% off on express laundry services!',
                'date': datetime.now().isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'announcements': announcements
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_notification_api(request):
    """Save notification to server for cross-device sync"""
    try:
        data = json.loads(request.body)
        # For now, just return success (notifications stored in localStorage)
        # You can optionally create a Notification model later
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mark_notification_read_api_v2(request):
    """Mark a notification as read (expects notification_id in body)"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('notification_id')
        # For now, just return success
        # You can implement Notification model later
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mark_all_notifications_read_api(request):
    """Mark all notifications as read for the user"""
    try:
        # For now, just return success
        # You can implement Notification model later
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def save_admin_settings_api(request):
    """Save admin dashboard settings"""
    try:
        data = json.loads(request.body)
        
        # Get or create settings object in database
        from .models import SystemSetting  # Create this model or use your existing one
        
        # For now, save settings in session or cache
        request.session['admin_settings'] = data
        
        # Or save to database if you have a SystemSetting model
        # for key, value in data.items():
        #     if isinstance(value, dict):
        #         for sub_key, sub_value in value.items():
        #             setting_key = f"{key}_{sub_key}"
        #             SystemSetting.objects.update_or_create(
        #                 key=setting_key,
        #                 defaults={'value': sub_value, 'value_type': type(sub_value).__name__}
        #             )
        
        # Save to localStorage equivalent on server side
        # You can also use Django's cache framework
        from django.core.cache import cache
        cache.set('admin_settings_' + str(request.user.id), data, timeout=86400)  # 24 hours
        
        return JsonResponse({
            'success': True,
            'message': 'Settings saved successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    
@login_required
def shop_analytics_api(request):
    """Get analytics data for the shop owner's shop"""
    try:
        # Get the laundry shop associated with the logged-in user
        from .models import LaundryShop, Order, ShopService
        
        shop = LaundryShop.objects.get(owner=request.user)
        
        # Get date range from request
        date_range = request.GET.get('range', 'week')
        
        # Calculate date range
        today = timezone.now().date()
        if date_range == 'today':
            start_date = today
            end_date = today + timedelta(days=1)
        elif date_range == 'week':
            start_date = today - timedelta(days=7)
            end_date = today + timedelta(days=1)
        elif date_range == 'month':
            start_date = today - timedelta(days=30)
            end_date = today + timedelta(days=1)
        elif date_range == 'year':
            start_date = today - timedelta(days=365)
            end_date = today + timedelta(days=1)
        else:
            start_date = today - timedelta(days=7)
            end_date = today + timedelta(days=1)
        
        # Previous period for trend calculation
        days_diff = (end_date - start_date).days
        prev_start_date = start_date - timedelta(days=days_diff)
        prev_end_date = start_date
        
        # Get all delivered orders for the shop
        delivered_orders = Order.objects.filter(
            shop=shop,
            status='delivered',
            delivered_at__isnull=False
        )
        
        # Current period orders (delivered)
        current_orders = delivered_orders.filter(
            delivered_at__date__gte=start_date,
            delivered_at__date__lt=end_date
        )
        
        # Previous period orders for trends
        prev_orders = delivered_orders.filter(
            delivered_at__date__gte=prev_start_date,
            delivered_at__date__lt=prev_end_date
        )
        
        # Calculate KPIs
        total_revenue = current_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        total_orders = current_orders.count()
        total_weight = current_orders.aggregate(total=Sum('weight'))['total'] or 0
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Calculate trends
        prev_revenue = prev_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        prev_orders_count = prev_orders.count()
        prev_weight = prev_orders.aggregate(total=Sum('weight'))['total'] or 0
        prev_avg = prev_revenue / prev_orders_count if prev_orders_count > 0 else 0
        
        revenue_trend = ((total_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else (100 if total_revenue > 0 else 0)
        orders_trend = ((total_orders - prev_orders_count) / prev_orders_count * 100) if prev_orders_count > 0 else (100 if total_orders > 0 else 0)
        weight_trend = ((total_weight - prev_weight) / prev_weight * 100) if prev_weight > 0 else (100 if total_weight > 0 else 0)
        avg_trend = ((avg_order_value - prev_avg) / prev_avg * 100) if prev_avg > 0 else (100 if avg_order_value > 0 else 0)
        
        # Generate daily data for chart
        chart_data = []
        current_date = start_date
        while current_date < end_date:
            day_orders = delivered_orders.filter(
                delivered_at__date=current_date
            )
            chart_data.append({
                'date': current_date.strftime('%b %d'),
                'revenue': float(day_orders.aggregate(total=Sum('total_amount'))['total'] or 0),
                'orders': day_orders.count(),
                'weight': float(day_orders.aggregate(total=Sum('weight'))['total'] or 0)
            })
            current_date += timedelta(days=1)
        
        # Service distribution (from delivered orders only)
        service_distribution = {}
        service_types = current_orders.values('service_type').annotate(
            count=Count('id')
        )
        
        service_display_map = {
            'mixed': 'Wash & Fold (Mixed Load)',
            'whites': 'Whites Only',
            'delicates': 'Delicates',
            'express': 'Express (2-hour)',
            'dry_clean': 'Dry Clean'
        }
        
        for st in service_types:
            service_name = service_display_map.get(st['service_type'], st['service_type'])
            service_distribution[service_name] = st['count']
        
        # Payment method distribution
        payment_distribution = {}
        payment_methods = current_orders.values('payment_method').annotate(
            count=Count('id')
        )
        
        for pm in payment_methods:
            payment_distribution[pm['payment_method']] = pm['count']
        
        # Status distribution (all orders, not just delivered)
        status_distribution = {}
        statuses = Order.objects.filter(shop=shop).values('status').annotate(
            count=Count('id')
        )
        
        for st in statuses:
            status_distribution[st['status']] = st['count']
        
        # Peak hours analysis (from all orders with pickup_time)
        peak_hours = {}
        all_orders = Order.objects.filter(shop=shop).exclude(pickup_time__isnull=True)
        for order in all_orders:
            if order.pickup_time:
                # Format time to 12-hour format
                hour_key = order.pickup_time.strftime('%I:%M %p')
                peak_hours[hour_key] = peak_hours.get(hour_key, 0) + 1
        
        # Sort peak hours by count (descending) and take top 5
        peak_hours = dict(sorted(peak_hours.items(), key=lambda x: x[1], reverse=True)[:5])
        
        # Top customers (from current period delivered orders)
        top_customers = []
        customer_data = current_orders.values('customer__first_name', 'customer__last_name', 'customer__username').annotate(
            orders_count=Count('id'),
            total_spent=Sum('total_amount'),
            total_weight=Sum('weight')
        ).order_by('-total_spent')[:5]
        
        for cd in customer_data:
            name = f"{cd.get('customer__first_name', '')} {cd.get('customer__last_name', '')}".strip()
            if not name:
                name = cd.get('customer__username', 'Unknown')
            top_customers.append({
                'name': name,
                'orders': cd['orders_count'],
                'total_spent': float(cd['total_spent'] or 0),
                'total_weight': float(cd['total_weight'] or 0)
            })
        
        # Prepare response data
        response_data = {
            'success': True,
            'labels': [d['date'] for d in chart_data],
            'revenue': [d['revenue'] for d in chart_data],
            'orders': [d['orders'] for d in chart_data],
            'weight': [d['weight'] for d in chart_data],
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'total_weight': float(total_weight),
            'avg_order_value': float(avg_order_value),
            'revenue_trend': round(revenue_trend, 1),
            'orders_trend': round(orders_trend, 1),
            'weight_trend': round(weight_trend, 1),
            'avg_trend': round(avg_trend, 1),
            'service_distribution': service_distribution,
            'payment_distribution': payment_distribution,
            'status_distribution': status_distribution,
            'peak_hours': peak_hours,
            'top_customers': top_customers
        }
        
        return JsonResponse(response_data)
        
    except LaundryShop.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'No shop found for this user'
        }, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
@staff_member_required
def admin_reviews_api(request):
    """Get all reviews for admin panel"""
    try:
        # Get all shops with their review counts
        shops = LaundryShop.objects.all()
        shops_data = []
        for shop in shops:
            review_count = ShopReview.objects.filter(shop=shop).count()
            shops_data.append({
                'id': shop.id,
                'name': shop.shop_name,
                'review_count': review_count
            })
        
        # Get all reviews with related data
        reviews = ShopReview.objects.select_related('shop', 'customer', 'order').order_by('-created_at')
        
        reviews_data = []
        for review in reviews:
            reviews_data.append({
                'id': review.id,
                'shop_id': review.shop.id,
                'shop_name': review.shop.shop_name,
                'customer_id': review.customer.id,
                'customer_name': review.customer.get_full_name() or review.customer.username,
                'customer_email': review.customer.email,
                'rating': review.rating,
                'comment': review.comment,
                'order_id': review.order.id if review.order else None,
                'order_number': review.order.order_number if review.order else None,
                'created_at': review.created_at.isoformat()
            })
        
        # Calculate stats
        total_reviews = len(reviews_data)
        overall_rating = ShopReview.objects.aggregate(avg=Avg('rating'))['avg'] or 0
        five_star_count = ShopReview.objects.filter(rating=5).count()
        active_shops = shops.filter(reviews__isnull=False).distinct().count()
        
        stats = {
            'overall_rating': round(overall_rating, 1),
            'total_reviews': total_reviews,
            'five_star_count': five_star_count,
            'active_shops': active_shops
        }
        
        return JsonResponse({
            'success': True,
            'reviews': reviews_data,
            'shops': shops_data,
            'stats': stats
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
def admin_delete_review_api(request, review_id):
    """Delete a review"""
    try:
        from .models import ShopReview
        review = ShopReview.objects.get(id=review_id)
        review.delete()
        return JsonResponse({
            'success': True,
            'message': 'Review deleted successfully'
        })
    except ShopReview.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Review not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
# ========== ADDITIONAL ADMIN APIs ==========
@staff_member_required
def admin_pending_count_api(request):
    """Get count of pending approvals (shops and riders)"""
    try:
        from .models import User
        pending_count = User.objects.filter(
            is_approved=False,
            role__in=['owner', 'rider']
        ).count()
        return JsonResponse({
            'success': True,
            'pending_count': pending_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def admin_recent_users_api(request):
    """Get recent user registrations"""
    try:
        from .models import User
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_users = User.objects.filter(
            date_joined__gte=seven_days_ago
        ).order_by('-date_joined')[:10]
        
        role_display = {
            'user': 'Customer',
            'owner': 'Shop Owner',
            'rider': 'Rider',
            'admin': 'Admin'
        }
        
        users_data = []
        for user in recent_users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'email': user.email,
                'role': user.role,
                'role_display': role_display.get(user.role, user.role),
                'date_joined': user.date_joined.isoformat(),
                'already_notified': False
            })
        
        return JsonResponse({
            'success': True,
            'new_users': users_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def admin_completed_deliveries_api(request):
    """Get recently completed deliveries"""
    try:
        from .models import Order
        today = timezone.now().date()
        recent_deliveries = Order.objects.filter(
            status='delivered',
            delivered_at__date=today
        ).select_related('customer', 'shop')[:10]
        
        deliveries_data = []
        for order in recent_deliveries:
            deliveries_data.append({
                'order_id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'shop_name': order.shop.shop_name,
                'total_amount': float(order.total_amount),
                'delivered_at': order.delivered_at.isoformat() if order.delivered_at else None
            })
        
        return JsonResponse({
            'success': True,
            'completed': deliveries_data,
            'today_count': len(deliveries_data)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def admin_system_health_api(request):
    """Get system health information"""
    try:
        from .models import Order
        two_hours_ago = timezone.now() - timedelta(hours=2)
        stuck_orders = Order.objects.filter(
            status='pending',
            created_at__lte=two_hours_ago
        ).count()
        
        return JsonResponse({
            'success': True,
            'stuck_orders': stuck_orders,
            'api_usage': 45  # Mock percentage - replace with actual if you have metrics
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def admin_recent_orders_api(request):
    """Get recent orders placed"""
    try:
        from .models import Order
        today = timezone.now().date()
        recent_orders = Order.objects.filter(
            created_at__date=today
        ).select_related('customer', 'shop').order_by('-created_at')[:10]
        
        orders_data = []
        for order in recent_orders:
            orders_data.append({
                'order_id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer.get_full_name() or order.customer.username,
                'shop_name': order.shop.shop_name,
                'total_amount': float(order.total_amount),
                'created_at': order.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'new_orders': orders_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@staff_member_required
def admin_daily_summary_api(request):
    """Get daily platform summary"""
    try:
        from .models import Order, User
        today = timezone.now().date()
        
        today_orders = Order.objects.filter(
            created_at__date=today,
            status='delivered'
        ).count()
        
        today_revenue = Order.objects.filter(
            created_at__date=today,
            status='delivered'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        new_users = User.objects.filter(
            date_joined__date=today
        ).count()
        
        pending_approvals = User.objects.filter(
            is_approved=False,
            role__in=['owner', 'rider']
        ).count()
        
        return JsonResponse({
            'success': True,
            'today_orders': today_orders,
            'today_revenue': float(today_revenue),
            'new_users': new_users,
            'pending_approvals': pending_approvals
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import models as db_models

@login_required
@csrf_exempt
def create_review_api(request):
    """Create a review for a shop after order delivery"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        
        order_id = data.get('order_id')
        shop_id = data.get('shop_id')
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        # Validate inputs
        if not order_id or not shop_id or not rating:
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        
        # Check if order exists and belongs to this customer
        from .models import Order, LaundryShop, ShopReview
        
        order = Order.objects.get(id=order_id, customer=request.user)
        
        # Check if order is delivered
        if order.status != 'delivered':
            return JsonResponse({'success': False, 'error': 'You can only review delivered orders'}, status=400)
        
        # Check if review already exists
        if order.has_review:
            return JsonResponse({'success': False, 'error': 'You have already reviewed this order'}, status=400)
        
        # Get the shop
        shop = LaundryShop.objects.get(id=shop_id)
        
        # Create the review
        review = ShopReview.objects.create(
            shop=shop,
            customer=request.user,
            order=order,
            rating=rating,
            comment=comment
        )
        
        # Mark order as reviewed
        order.has_review = True
        order.save()
        
        # Update shop rating
        all_reviews = ShopReview.objects.filter(shop=shop)
        avg_rating = all_reviews.aggregate(db_models.Avg('rating'))['rating__avg'] or 0
        shop.rating = round(avg_rating, 2)
        shop.total_reviews = all_reviews.count()
        shop.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Review submitted successfully',
            'review_id': review.id
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except LaundryShop.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Shop not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
@login_required
@user_passes_test(is_admin_user)
def admin_order_detail_by_id_api(request, order_id):
    """API endpoint for admin to get detailed order information by order ID"""
    from .models import Order
    
    try:
        order = Order.objects.select_related('customer', 'shop', 'rider').get(id=order_id)
        
        # Payment method display mapping
        payment_display_map = {
            'gcash': 'GCash',
            'paypal': 'PayPal',
            'cod': 'COD'
        }
        
        order_data = {
            'order_number': order.order_number,
            'customer_name': order.customer.get_full_name() or order.customer.username,
            'customer_phone': order.customer.phone or 'N/A',
            'shop_name': order.shop.shop_name,
            'rider_name': order.rider.get_full_name() or order.rider.username if order.rider else 'Not assigned',
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'pickup_date': order.pickup_date.strftime('%Y-%m-%d') if order.pickup_date else 'N/A',
            'pickup_time': order.pickup_time.strftime('%I:%M %p') if order.pickup_time else 'N/A',
            'pickup_address': order.pickup_address,
            'service_type': order.get_service_type_display(),
            'weight': float(order.weight),
            'total_amount': float(order.total_amount),
            'payment_method': payment_display_map.get(order.payment_method, order.payment_method),
            'status': order.status,
            'status_display': order.get_status_display(),
            'special_instructions': order.special_instructions or '',
            'delivered_at': order.delivered_at.strftime('%Y-%m-%d %H:%M') if order.delivered_at else None,
        }
        
        return JsonResponse({'success': True, 'order': order_data})
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# Add this to accounts/views.py - near the bottom, before create_review_api

@login_required
@require_http_methods(["GET"])
def get_pending_booking_api(request):
    """
    API endpoint to get pending booking data from session.
    Called by student_home.html after payment success.
    """
    # Retrieve the booking data stored in the session
    pending_booking = request.session.get('pending_booking')
    payment_success = request.session.get('payment_success', False)
    payment_order_id = request.session.get('payment_order_id')
    
    if pending_booking and payment_success:
        response_data = {
            'has_pending_booking': True,
            'booking_data': pending_booking,
            'payment_info': {
                'success': True,
                'order_id': payment_order_id
            }
        }
        # Clear the payment_success flag after retrieval
        # request.session['payment_success'] = False
        return JsonResponse(response_data)
    else:
        return JsonResponse({'has_pending_booking': False})