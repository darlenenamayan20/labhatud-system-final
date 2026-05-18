# Testing Payment Flow

## Steps to Test Order Creation

1. **Start the server and check logs:**
   ```bash
   venv\Scripts\python.exe manage.py runserver
   ```

2. **As a student, create a booking:**
   - Go to student home
   - Select a laundry shop (e.g., personal4's Laundry Shop)
   - Fill in booking details
   - Click "Proceed to Payment"

3. **Check browser console (F12):**
   - Look for: `pending_booking` data being stored
   - Look for: redirect to `/payments/payment-page/`

4. **Complete payment:**
   - Click "Pay with GCash"
   - Click "Confirm Payment" on the GCash page

5. **Check Django server logs for:**
   ```
   === PAYMENT PAGE VIEW ===
   === GCASH CALLBACK ===
   === GET PENDING BOOKING API ===
   === CREATE BOOKING API ===
   ```

6. **Verify order creation:**
   - Check if "Order Placed Successfully!" toast appears
   - Login as shop owner (personal4)
   - Check "Incoming Orders" section

## Common Issues

### Issue: Order not showing in shop dashboard
**Possible causes:**
- `pending_booking` not stored in session
- `finalConfirmBooking()` not called after payment
- API endpoint `/api/booking/create/` failing

### Issue: Payment success but no booking modal
**Possible causes:**
- Session data lost during redirect
- `payment_success` flag not set
- Browser sessionStorage cleared

## Debug Commands

```bash
# Check if orders exist in database
venv\Scripts\python.exe manage.py shell
>>> from accounts.models import Order
>>> Order.objects.all()
>>> Order.objects.filter(status='pending')
```
