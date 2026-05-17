from django.urls import path
from . import views
 
urlpatterns = [
    path("checkout/", views.checkout_view, name="checkout"),
    path("result/<int:order_id>/", views.payment_result_view, name="payment_result"),
    path("webhook/", views.paymongo_webhook, name="paymongo_webhook"),
    path("gcash/", views.gcash_checkout_view, name="gcash_checkout"),
    path("gcash/callback/", views.gcash_callback_view, name="gcash_callback"), 
    path("payment-page/", views.payment_page_view, name="payment_page"),
]