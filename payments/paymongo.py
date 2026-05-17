# payments/paymongo.py - COMPLETE FILE

import base64
import requests
from django.conf import settings

PAYMONGO_BASE_URL = "https://api.paymongo.com/v1"


def get_auth_header():
    secret = settings.PAYMONGO_SECRET_KEY
    encoded = base64.b64encode(f"{secret}:".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def create_payment_link(amount: int, description: str, redirect_url: str) -> dict:
    headers = {**get_auth_header(), "Content-Type": "application/json"}
    payload = {
        "data": {
            "attributes": {
                "amount": amount,
                "description": description,
                "currency": "PHP",
                "redirect": {
                    "success": redirect_url + "?status=success",
                    "failed": redirect_url + "?status=failed",
                },
            }
        }
    }
    response = requests.post(
        f"{PAYMONGO_BASE_URL}/links",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()["data"]
    return {
        "link_id": data["id"],
        "checkout_url": data["attributes"]["checkout_url"],
    }


def retrieve_payment_link(link_id: str) -> dict:
    response = requests.get(
        f"{PAYMONGO_BASE_URL}/links/{link_id}",
        headers=get_auth_header(),
    )
    response.raise_for_status()
    return response.json()["data"]


# ============= ADD THESE FUNCTIONS FOR GCASH =============

def create_gcash_source(amount: int, description: str, success_url: str, failed_url: str) -> dict:
    """
    Create a GCash source for e-wallet payments.
    This generates a checkout_url that redirects to GCash authentication.
    
    Args:
        amount: Amount in centavos (e.g., 10000 = ₱100.00)
        description: Payment description
        success_url: Where to redirect after successful payment
        failed_url: Where to redirect after failed payment
    """
    headers = {**get_auth_header(), "Content-Type": "application/json"}
    
    payload = {
        "data": {
            "attributes": {
                "amount": amount,
                "currency": "PHP",
                "type": "gcash",  # Important: Must be "gcash"
                "redirect": {
                    "success": success_url,
                    "failed": failed_url
                },
                "billing": {
                    "name": "LabHatud Customer",
                    "email": "customer@labhatud.com"
                },
                "description": description
            }
        }
    }
    
    response = requests.post(
        f"{PAYMONGO_BASE_URL}/sources",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()
    data = response.json()["data"]
    
    return {
        "source_id": data["id"],
        "checkout_url": data["attributes"]["redirect"]["checkout_url"],
        "status": data["attributes"]["status"]
    }


def create_payment_from_source(source_id: str, amount: int) -> dict:
    """
    Create a payment using a chargeable source.
    Called from webhook when source.chargeable event is received.
    
    Args:
        source_id: The ID of the chargeable source
        amount: Amount in centavos
    """
    headers = {**get_auth_header(), "Content-Type": "application/json"}
    
    payload = {
        "data": {
            "attributes": {
                "amount": amount,
                "source": {
                    "id": source_id,
                    "type": "source"
                },
                "currency": "PHP",
                "description": "GCash Payment"
            }
        }
    }
    
    response = requests.post(
        f"{PAYMONGO_BASE_URL}/payments",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()
    return response.json()["data"]