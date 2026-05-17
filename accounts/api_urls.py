# accounts/api_urls.py
from django.urls import path
from .views import (
    # Existing admin APIs
    admin_users_api,
    get_user_detail_api,
    approve_user_api,
    reject_user_api,
    suspend_user_api,
    reactivate_user_api,
    delete_user_api,
    # New laundry shop and order management APIs
    save_shop_profile_api,
    save_shop_settings_api,
    get_shop_details_api,
    order_tracking_api,
    get_order_details_api,
    rider_update_order_status_api,
    accept_order_api,
    reject_order_api,
    update_order_status_api,
    rider_accept_order_api,
    create_booking_api,
    get_notifications_api,
    mark_notification_read_api,
    clear_all_notifications_api,
    get_pending_orders_api,
    get_rider_notifications_api,
    get_order_details_by_id_api,
    # Rider Management APIs for Shop Owner
    get_riders_list_api,
    get_active_deliveries_api,
    get_pending_assignments_api,
    assign_rider_to_order_api,
    notify_rider_api,
    track_rider_deliveries_api,
    get_rider_deliveries_detail_api,
    # Admin Order Management APIs
    admin_orders_api,
    admin_order_detail_api,
    # Admin Analytics API
    admin_analytics_api,
    # NEW NOTIFICATION SYSTEM APIs
    order_status_updates_api,
    shop_announcements_api,
    save_notification_api,
    mark_notification_read_api_v2,
    mark_all_notifications_read_api,
    save_admin_settings_api,
    shop_analytics_api,
    admin_reviews_api,
    admin_delete_review_api,
    # ADD THESE MISSING APIS:
    admin_pending_count_api,
    admin_recent_users_api,
    admin_completed_deliveries_api,
    admin_system_health_api,
    admin_recent_orders_api,
    admin_daily_summary_api,
    create_review_api,
    admin_order_detail_by_id_api,
)

app_name = 'api'

urlpatterns = [
    # ========== ADMIN USER MANAGEMENT APIs ==========
    path('admin/users/', admin_users_api, name='admin_users_api'),
    path('admin/users/<int:user_id>/detail/', get_user_detail_api, name='get_user_detail_api'),
    path('admin/users/<int:user_id>/approve/', approve_user_api, name='approve_user_api'),
    path('admin/users/<int:user_id>/reject/', reject_user_api, name='reject_user_api'),
    path('admin/users/<int:user_id>/suspend/', suspend_user_api, name='suspend_user_api'),
    path('admin/users/<int:user_id>/reactivate/', reactivate_user_api, name='reactivate_user_api'),
    path('admin/users/<int:user_id>/delete/', delete_user_api, name='delete_user_api'),
    
    # ========== ADMIN ORDER MANAGEMENT APIs ==========
    path('admin/orders/', admin_orders_api, name='admin_orders_api'),
    path('admin/orders/<str:order_number>/detail/', admin_order_detail_api, name='admin_order_detail_api'),
    
    # ========== ADMIN ANALYTICS API ==========
    path('admin/analytics/', admin_analytics_api, name='admin_analytics_api'),
    
    # ========== ADDITIONAL ADMIN APIs (NOTIFICATION SYSTEM) ==========
    path('admin/users/pending-count/', admin_pending_count_api, name='admin_pending_count_api'),
    path('admin/users/recent/', admin_recent_users_api, name='admin_recent_users_api'),
    path('admin/completed-deliveries/', admin_completed_deliveries_api, name='admin_completed_deliveries_api'),
    path('admin/system/health/', admin_system_health_api, name='admin_system_health_api'),
    path('admin/orders/recent/', admin_recent_orders_api, name='admin_recent_orders_api'),
    path('admin/daily-summary/', admin_daily_summary_api, name='admin_daily_summary_api'),
    
    # ========== ADMIN REVIEWS APIs ==========
    path('admin/reviews/', admin_reviews_api, name='admin_reviews_api'),
    path('admin/reviews/<int:review_id>/delete/', admin_delete_review_api, name='admin_delete_review_api'),
    
    # ========== RIDER APIs ==========
    path('rider/pending-orders/', get_pending_orders_api, name='get_pending_orders_api'),
    path('rider/notifications/', get_rider_notifications_api, name='get_rider_notifications_api'),
    path('order/<int:order_id>/details/', get_order_details_by_id_api, name='get_order_details_by_id_api'),
    
    # ========== RIDER MANAGEMENT APIs FOR SHOP OWNER ==========
    path('riders/list/', get_riders_list_api, name='get_riders_list_api'),
    path('orders/active-deliveries/', get_active_deliveries_api, name='get_active_deliveries_api'),
    path('orders/pending-assignments/', get_pending_assignments_api, name='get_pending_assignments_api'),
    path('orders/assign-rider/', assign_rider_to_order_api, name='assign_rider_to_order_api'),
    path('riders/notify/', notify_rider_api, name='notify_rider_api'),
    path('riders/<int:rider_id>/deliveries/', track_rider_deliveries_api, name='track_rider_deliveries_api'),
    path('riders/<int:rider_id>/deliveries-detail/', get_rider_deliveries_detail_api, name='get_rider_deliveries_detail_api'),
    
    # ========== LAUNDRY SHOP MANAGEMENT APIs ==========
    # Shop Profile & Settings
    path('shop/save-profile/', save_shop_profile_api, name='save_shop_profile_api'),
    path('shop/save-settings/', save_shop_settings_api, name='save_shop_settings_api'),
    path('shop/<int:shop_id>/details/', get_shop_details_api, name='get_shop_details_api'),
    
    # Order Tracking & Details
    path('order/<str:order_number>/track/', order_tracking_api, name='order_tracking_api'),
    path('rider/order/<str:order_number>/details/', get_order_details_api, name='rider_order_details_api'),
    path('rider/order/<str:order_number>/update-status/', rider_update_order_status_api, name='rider_update_order_status_api'),
    
    # Order Management
    path('order/accept/<int:order_id>/', accept_order_api, name='accept_order_api'),
    path('order/reject/<int:order_id>/', reject_order_api, name='reject_order_api'),
    path('order/update-status/<int:order_id>/', update_order_status_api, name='update_order_status_api'),
    path('rider/order/accept/<int:order_id>/', rider_accept_order_api, name='rider_accept_order_api'),
    path('booking/create/', create_booking_api, name='create_booking_api'),
    
    # Notifications
    path('notifications/', get_notifications_api, name='get_notifications_api'),
    path('notifications/mark-read/<int:notification_id>/', mark_notification_read_api, name='mark_notification_read_api'),
    path('notifications/clear/', clear_all_notifications_api, name='clear_all_notifications_api'),
    
    # ========== NEW NOTIFICATION SYSTEM APIs ==========
    path('orders/status-updates/', order_status_updates_api, name='order_status_updates_api'),
    path('shops/announcements/', shop_announcements_api, name='shop_announcements_api'),
    path('notifications/save/', save_notification_api, name='save_notification_api'),
    path('notifications/mark-read/', mark_notification_read_api_v2, name='mark_notification_read_api_v2'),
    path('notifications/mark-all-read/', mark_all_notifications_read_api, name='mark_all_notifications_read_api'),
    
    # ========== SETTINGS APIs ==========
    path('admin/settings/save/', save_admin_settings_api, name='save_admin_settings_api'),
    
    # ========== SHOP ANALYTICS API ==========
    path('shop/analytics/', shop_analytics_api, name='shop_analytics_api'),
    path('admin/orders/detail/<int:order_id>/', admin_order_detail_by_id_api, name='admin_order_detail_by_id_api'),
    path('review/create/', create_review_api, name='create_review_api'),
    path('admin/reviews/<int:review_id>/delete/', admin_delete_review_api, name='admin_delete_review_api'),
]