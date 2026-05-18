# payments/views.py - COMPLETE FIXED VERSION

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
import json
import hmac
import hashlib
import logging

from .models import Order
from .paymongo import (
    create_payment_link, 
    retrieve_payment_link, 
    create_payment_from_source,
    create_gcash_source  # ADD THIS - was missing!
)


# Set up logging
logger = logging.getLogger(__name__)


def checkout_view(request):
    if request.method == "POST":
        description = request.POST.get("description", "Order")
        amount_pesos = float(request.POST.get("amount", 0))
        amount_centavos = int(amount_pesos * 100)
 
        order = Order.objects.create(
            description=description,
            amount=amount_centavos,
            status="pending",
        )
 
        redirect_url = request.build_absolute_uri(
            reverse("payment_result", args=[order.pk])
        )
 
        try:
            link_data = create_payment_link(
                amount=amount_centavos,
                description=description,
                redirect_url=redirect_url,
            )
            order.paymongo_link_id = link_data["link_id"]
            order.checkout_url = link_data["checkout_url"]
            order.save()
            return redirect(link_data["checkout_url"])
        except Exception as e:
            messages.error(request, f"Payment initialization failed: {str(e)}")
            return redirect("checkout")
 
    return render(request, "payments/checkout.html")
 
 
def payment_result_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    status_param = request.GET.get("status")
 
    if status_param == "success" and order.paymongo_link_id:
        try:
            link_data = retrieve_payment_link(order.paymongo_link_id)
            payments = link_data["attributes"].get("payments", [])
            if payments and payments[0]["attributes"]["status"] == "paid":
                order.status = "paid"
            else:
                order.status = "pending"
        except Exception:
            order.status = "pending"
    elif status_param == "failed":
        order.status = "failed"
 
    order.save()
    return render(request, "payments/result.html", {"order": order})


@csrf_exempt
@require_POST
def paymongo_webhook(request):
    """Updated webhook handler that processes source.chargeable events for GCash"""
    payload = request.body
    sig_header = request.headers.get("Paymongo-Signature", "")
    
    # Verify signature
    webhook_secret = getattr(settings, 'PAYMONGO_WEBHOOK_SECRET', None)
    
    if webhook_secret:
        secret = webhook_secret.encode()
        computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(computed, sig_header):
            logger.warning(f"Invalid webhook signature. Expected: {computed}, Got: {sig_header}")
            return JsonResponse({"error": "Invalid signature"}, status=400)
    else:
        logger.warning("PAYMONGO_WEBHOOK_SECRET not set - skipping signature verification")
    
    try:
        event_data = json.loads(payload)
        event_type = event_data["data"]["attributes"]["type"]
        
        logger.info(f"Webhook received: {event_type}")
        
        # Handle source.chargeable event - This is crucial for GCash!
        if event_type == "source.chargeable":
            source_data = event_data["data"]["attributes"]["data"]
            source_id = source_data["id"]
            amount = source_data["attributes"]["amount"]
            
            logger.info(f"Source chargeable! Source ID: {source_id}, Amount: {amount}")
            
            # Create a Payment from the chargeable source
            try:
                payment_result = create_payment_from_source(source_id, amount)
                logger.info(f"Payment created from source {source_id}: {payment_result.get('id')}")
                
                # Update order status if you stored source_id
                # Uncomment and use paymongo_source_id if you added this field to Order model
                try:
                    order = Order.objects.get(paymongo_source_id=source_id)
                    order.status = "paid"
                    order.save()
                    logger.info(f"Order {order.pk} marked as PAID via source.chargeable")
                except Order.DoesNotExist:
                    logger.warning(f"No order found with paymongo_source_id: {source_id}")
                except AttributeError:
                    # If paymongo_source_id field doesn't exist yet
                    logger.warning("paymongo_source_id field not found in Order model")
                
            except Exception as e:
                logger.error(f"Failed to create payment from source: {str(e)}")
            
        # Keep your existing payment.paid handler
        elif event_type == "payment.paid":
            payment_data = event_data["data"]["attributes"]["data"]
            payment_id = payment_data.get("id")
            payment_attrs = payment_data.get("attributes", {})
            link_id = payment_attrs.get("link_id")
            
            logger.info(f"Payment.paid received - Payment ID: {payment_id}, Link ID: {link_id}")
            
            # Update order status
            if link_id:
                try:
                    order = Order.objects.get(paymongo_link_id=link_id)
                    order.status = "paid"
                    order.save()
                    logger.info(f"Order {order.pk} marked as PAID via webhook")
                except Order.DoesNotExist:
                    logger.error(f"Order not found for link_id: {link_id}")
        
        elif event_type == "payment.failed":
            payment_data = event_data["data"]["attributes"]["data"]
            payment_attrs = payment_data.get("attributes", {})
            link_id = payment_attrs.get("link_id")
            
            logger.info(f"Payment.failed received for link: {link_id}")
            
            if link_id:
                try:
                    order = Order.objects.get(paymongo_link_id=link_id)
                    order.status = "failed"
                    order.save()
                    logger.info(f"Order {order.pk} marked as FAILED via webhook")
                except Order.DoesNotExist:
                    logger.error(f"Order not found for failed payment: {link_id}")
        
        else:
            logger.info(f"Unhandled event type: {event_type}")
        
        return JsonResponse({"received": True})
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return JsonResponse({"error": "Internal server error"}, status=500)
    

def gcash_checkout_view(request):
    """Handle GCash payment initiation - MOCK MODE for demo"""
    if request.method == "POST":
        description = request.POST.get("description", "LabHatud Laundry Order")
        amount_pesos = float(request.POST.get("amount", 0))
        amount_centavos = int(amount_pesos * 100)
        
        # Get expected amount from session
        payment_data = request.session.get('gcash_payment_data', {})
        expected_amount = float(payment_data.get('amount', 0))
        
        # Validate exact amount
        if abs(amount_pesos - expected_amount) > 0.01:  # Allow 1 cent tolerance for rounding
            messages.error(request, f"Payment amount must be exactly ₱{expected_amount:.2f}. You entered ₱{amount_pesos:.2f}")
            context = {
                'amount': payment_data.get('amount', '100.00'),
                'description': payment_data.get('description', 'LabHatud Laundry Order'),
            }
            return render(request, "payments/gcash_checkout.html", context)
        
        # Create order
        order = Order.objects.create(
            description=description,
            amount=amount_centavos,
            status="pending",
        )
        
        # Build redirect URLs
        base_url = request.build_absolute_uri("/")
        success_url = base_url + f"payments/gcash/callback/?order_id={order.pk}&status=success"
        failed_url = base_url + f"payments/gcash/callback/?order_id={order.pk}&status=failed"
        
        # MOCK MODE: Show simulated GCash page instead of real PayMongo
        context = {
            'order': order,
            'amount': f"{amount_pesos:.2f}",
            'description': description,
            'success_url': success_url,
            'failed_url': failed_url,
        }
        return render(request, "payments/mock_gcash.html", context)
    
    # GET request - show form with pre-filled data from session
    payment_data = request.session.get('gcash_payment_data', {})
    context = {
        'amount': payment_data.get('amount', '100.00'),
        'description': payment_data.get('description', 'LabHatud Laundry Order'),
    }
    return render(request, "payments/gcash_checkout.html", context)


def gcash_callback_view(request):
    """Callback after GCash payment - Redirects back to student home with booking data"""
    order_id = request.GET.get("order_id")
    status = request.GET.get("status")
    
    logger.info(f"=== GCASH CALLBACK ===")
    logger.info(f"Order ID: {order_id}, Status: {status}")
    
    # Get the pending booking data from session
    pending_booking = request.session.get('pending_booking', {})
    logger.info(f"pending_booking from session: {pending_booking}")
    
    if status == "success" and order_id:
        try:
            order = Order.objects.get(pk=order_id)
            order.status = "paid"
            order.save()
            
            logger.info(f"Payment Order {order_id} marked as paid")
            
            # Store payment success in session for frontend to read
            request.session['payment_success'] = True
            request.session['payment_order_id'] = order_id
            
            # Keep the booking data if it exists
            if pending_booking:
                request.session['pending_booking'] = pending_booking
                logger.info(f"Kept pending_booking in session for order creation")
            else:
                logger.warning(f"No pending_booking found in session!")
            
        except Order.DoesNotExist:
            logger.error(f"Payment Order {order_id} not found!")
    
    logger.info(f"Redirecting to /student-home/?payment=success&tab=booking")
    # CHANGE THIS LINE - redirect to student-home instead of root
    return redirect(f"/student-home/?payment=success&tab=booking")

def payment_page_view(request):
    """Display payment page with query parameters - Redirect to GCash checkout"""
    
    # Get pending_booking from URL parameter
    pending_booking_param = request.GET.get('pending_booking')
    
    logger.info(f"=== PAYMENT PAGE VIEW ===")
    logger.info(f"pending_booking_param received: {pending_booking_param[:100] if pending_booking_param else 'None'}...")
    
    if pending_booking_param:
        import json
        try:
            booking_data = json.loads(pending_booking_param)
            # Store in session for later use
            request.session['pending_booking'] = booking_data
            logger.info(f"Stored booking_data in session: {booking_data}")
        except Exception as e:
            logger.error(f"Failed to parse pending_booking: {e}")
    
    # Get payment method from URL
    payment_method = request.GET.get('payment_method', '').lower()
    amount = request.GET.get('amount', '0')
    description = request.GET.get('description', 'LabHatud Laundry Order')
    
    logger.info(f"Payment method: {payment_method}, Amount: {amount}")
    
    # If payment method is GCash, redirect to GCash checkout
    if payment_method == 'gcash':
        # Create a POST-like redirect by storing data in session and redirecting to GCash view
        request.session['gcash_payment_data'] = {
            'amount': amount,
            'description': description,
            'payment_method': payment_method
        }
        logger.info(f"Redirecting to gcash_checkout with session data")
        return redirect('gcash_checkout')
    
    # For other payment methods, show the regular checkout page
    context = {
        'amount': amount,
        'description': description,
        'payment_method': payment_method,
    }
    return render(request, 'payments/checkout.html', context)