from django.urls import path, include
from .views import (
    login_view, 
    register_view, 
    student_home_view, 
    logout_view, 
    shop_dashboard, 
    rider_dashboard, 
    admin_dashboard,
    index_view,
    login_register_view,
    update_shop_profile,
    update_rider_profile,
    update_rider_vehicle,
    get_pending_booking_api,
    create_review_api,  # ADD THIS LINE
)

urlpatterns = [
    # Landing page (this handles the root URL '/')
    path('', index_view, name='index'),
    
    # Combined auth page
    path('auth/', login_register_view, name='login_register'),
    
    # Authentication URLs
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    
    # Dashboard URLs
    path('student-home/', student_home_view, name='student_home'),
    path('shop/dashboard/', shop_dashboard, name='shop_dashboard'),  
    path('rider/dashboard/', rider_dashboard, name='rider_dashboard'),
    path('admin-panel/', admin_dashboard, name='admin_dashboard'),
    
    # Alternative dashboard URLs for consistency
    path('home/', student_home_view, name='student_home_alt'),
    path('shop/', shop_dashboard, name='shop_dashboard_alt'),
    path('rider/', rider_dashboard, name='rider_dashboard_alt'),
    
    # Profile update URLs
    path('shop/update-profile/', update_shop_profile, name='update_shop_profile'),
    path('rider/update-profile/', update_rider_profile, name='update_rider_profile'),
    path('rider/update-vehicle/', update_rider_vehicle, name='update_rider_vehicle'),
    
    # API endpoints (clean and organized)
    path('api/', include('accounts.api_urls')),
    path('api/get-pending-booking/', get_pending_booking_api, name='get_pending_booking'),
    path('create-review/', create_review_api, name='create_review'),  # USE THE FUNCTION DIRECTLY
]