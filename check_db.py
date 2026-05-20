import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labhatud_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import LaundryShop, Order, ShopService
from payments.models import Order as PaymentOrder

User = get_user_model()

print("=" * 50)
print("DATABASE STATUS CHECK")
print("=" * 50)

# Check users
users = User.objects.all()
print(f"\n[OK] Users: {users.count()}")
for user in users:
    print(f"   - {user.username} ({user.email}) - Role: {user.role}")

# Check laundry shops
shops = LaundryShop.objects.all()
print(f"\n[OK] Laundry Shops: {shops.count()}")
for shop in shops:
    print(f"   - {shop.name}")

# Check orders
orders = Order.objects.all()
print(f"\n[OK] Orders: {orders.count()}")

# Check payment orders
payment_orders = PaymentOrder.objects.all()
print(f"\n[OK] Payment Orders: {payment_orders.count()}")

print("\n" + "=" * 50)
print("DATABASE IS WORKING!")
print("=" * 50)
