from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
        ('rider', 'Rider'),
        ('owner', 'Owner'),  # Shop owner
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    
    # Add these missing fields ↓↓↓
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    is_approved = models.BooleanField(default=False)  # For shops and riders
    
    # Additional fields for better tracking
    last_active = models.DateTimeField(auto_now=True)
    total_orders = models.IntegerField(default=0)
    
    # Shop-specific fields (for role='owner')
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_permit = models.FileField(upload_to='permits/', blank=True, null=True)
    
    # Rider-specific fields (for role='rider')
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    plate_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def status(self):
        """Return status based on is_approved and is_active"""
        if not self.is_approved:
            return 'pending'
        if not self.is_active:
            return 'suspended'
        return 'active'
    

class LaundryShop(models.Model):
    """Extended shop information for owners"""
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop', limit_choices_to={'role': 'owner'})
    
    # Basic Information
    shop_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='shop_logos/', blank=True, null=True)
    
    # Location
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Operating Hours
    days_open = models.CharField(max_length=100, default='Monday – Saturday')
    opening_time = models.TimeField(default='07:00')
    closing_time = models.TimeField(default='20:00')
    
    # Business Settings
    daily_order_limit = models.IntegerField(default=10)
    is_open = models.BooleanField(default=True)
    
    # Contact Info (override user's contact)
    shop_phone = models.CharField(max_length=20, blank=True, null=True)
    shop_email = models.EmailField(blank=True, null=True)
    
    # Ratings & Stats
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.IntegerField(default=0)
    total_orders_served = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.shop_name
    
    def get_working_hours_display(self):
        return f"{self.opening_time.strftime('%I:%M %p')} – {self.closing_time.strftime('%I:%M %p')}"
    
    @property
    def is_accepting_orders(self):
        """Check if shop is accepting new orders"""
        return self.is_open and self.is_approved
    
    @property
    def is_approved(self):
        """Check if owner is approved"""
        return self.owner.is_approved
    
    class Meta:
        verbose_name_plural = "Laundry Shops"


class ShopService(models.Model):
    SERVICE_TYPES = [
        ('mixed', 'Wash & Fold (Mixed Load)'),
        ('whites', 'Whites Only'),
        ('delicates', 'Delicates'),
        ('express', 'Express (2-hour)'),
        ('dry_clean', 'Dry Clean'),
    ]
    
    shop = models.ForeignKey(LaundryShop, on_delete=models.CASCADE, related_name='services')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    price_per_kg = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['shop', 'service_type']
    
    def __str__(self):
        return f"{self.shop.shop_name} - {self.get_service_type_display()}"


class ShopAddon(models.Model):
    shop = models.ForeignKey(LaundryShop, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} (₱{self.price})"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rider_accepted', 'Rider Accepted'),
        ('picked_up', 'Picked Up'),
        ('delivered_to_shop', 'Delivered to Shop'),  # ← ADD THIS
        ('washing', 'Washing'),
        ('drying', 'Drying'),
        ('ready', 'Ready for Delivery'),
        ('picked_up_from_shop', 'Picked Up from Shop'),  # ← ADD THIS
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    
    PAYMENT_CHOICES = [
        ('gcash', 'GCash'),
        ('paypal', 'PayPal'),
        ('cod', 'Cash on Delivery'),
    ]
    
    order_number = models.CharField(max_length=20, unique=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', limit_choices_to={'role': 'user'})
    shop = models.ForeignKey(LaundryShop, on_delete=models.CASCADE, related_name='orders')
    rider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivery_orders', limit_choices_to={'role': 'rider'})
    
    # Order Details
    service_type = models.CharField(max_length=20, choices=ShopService.SERVICE_TYPES)
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    special_instructions = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    has_review = models.BooleanField(default=False)
    
    # Schedule
    pickup_date = models.DateField()
    pickup_time = models.TimeField()
    pickup_address = models.TextField()
    delivery_date = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Status Tracking
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')  # ← Increased max_length to 25
    status_updated_at = models.DateTimeField(auto_now=True)
    
    # Timestamps for shop and rider progress tracking
    ready_at = models.DateTimeField(null=True, blank=True)  # When shop marks order as 'ready'
    picked_up_at = models.DateTimeField(null=True, blank=True)  # When rider picks up dirty laundry from customer
    delivered_to_shop_at = models.DateTimeField(null=True, blank=True)  # ← ADD THIS - When rider delivers dirty laundry to shop
    picked_up_from_shop_at = models.DateTimeField(null=True, blank=True)  # ← ADD THIS - When rider picks up clean laundry from shop
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)  # When order is out for delivery
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            import random
            # Generate unique order number: LH-XXXXXX
            self.order_number = f"LH-{random.randint(1000, 9999)}{uuid.uuid4().hex[:4].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.order_number} - {self.customer.username}"
    
    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('new_order', 'New Order'),
        ('status_update', 'Status Update'),
        ('rider_assigned', 'Rider Assigned'),
        ('order_delivered', 'Order Delivered'),
        ('order_rejected', 'Order Rejected'),
        ('shop_update', 'Shop Update'),
        ('order_accepted', 'Order Accepted'),
        ('ready_for_delivery', 'Ready for Delivery'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Add metadata field as JSON (optional, for future use)
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']


class ShopReview(models.Model):
    shop = models.ForeignKey(LaundryShop, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', limit_choices_to={'role': 'user'})
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review', null=True, blank=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review for {self.shop.shop_name} - {self.rating}⭐"
    
    class Meta:
        unique_together = ['shop', 'customer', 'order']