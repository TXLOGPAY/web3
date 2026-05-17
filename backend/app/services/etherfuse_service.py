"""Etherfuse Ramp API integration for fiat↔Stellar anchoring."""
import httpx
import structlog
from app.core.config import settings

log = structlog.get_logger()

BASE_URL = settings.ETHERFUSE_BASE_URL
HEADERS = {
    "Authorization": f"Bearer {settings.ETHERFUSE_API_KEY}",
    "Content-Type": "application/json",
}


# ─── Onboarding ───────────────────────────────────────────────────────────────

async def create_onboarding_url(
    customer_email: str,
    customer_name: str,
    stellar_public_key: str,
    role: str,
) -> dict:
    """Generate a KYC/onboarding URL for a customer."""
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.post(
            f"{BASE_URL}/onboarding-url",
            json={
                "email": customer_email,
                "name": customer_name,
                "stellar_public_key": stellar_public_key,
                "role": role,
                "redirect_url": "https://txlogpay.app/onboarding/complete",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        log.info("etherfuse_onboarding_created", email=customer_email, role=role)
        return data


# ─── Orders ──────────────────────────────────────────────────────────────────

async def create_order(
    order_type: str,  # "onramp" | "offramp"
    amount: float,
    currency: str,
    stellar_public_key: str,
    memo: str = "",
) -> dict:
    """Create a fiat on/off-ramp order."""
    payload = {
        "type": order_type,
        "amount": amount,
        "currency": currency,
        "stellar_public_key": stellar_public_key,
        "blockchain": "stellar",
    }
    if memo:
        payload["memo"] = memo

    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.post(f"{BASE_URL}/order", json=payload)
        resp.raise_for_status()
        data = resp.json()
        log.info(
            "etherfuse_order_created",
            order_id=data.get("id"),
            type=order_type,
            amount=amount,
        )
        return data


async def get_order(order_id: str) -> dict:
    """Retrieve an order by ID."""
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.get(f"{BASE_URL}/order/{order_id}")
        resp.raise_for_status()
        return resp.json()


async def list_orders(stellar_public_key: str) -> list[dict]:
    """List all orders for a given Stellar account."""
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.post(
            f"{BASE_URL}/orders",
            json={"stellar_public_key": stellar_public_key},
        )
        resp.raise_for_status()
        return resp.json().get("orders", [])


# ─── Wallets ──────────────────────────────────────────────────────────────────

async def list_customer_wallets(stellar_public_key: str) -> list[dict]:
    """List wallets associated with a customer."""
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.post(
            f"{BASE_URL}/wallets",
            json={"stellar_public_key": stellar_public_key},
        )
        resp.raise_for_status()
        return resp.json().get("wallets", [])


# ─── Webhooks ─────────────────────────────────────────────────────────────────

async def create_webhook(url: str, events: list[str]) -> dict:
    """Register a webhook for Etherfuse events."""
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.post(
            f"{BASE_URL}/webhook",
            json={"url": url, "events": events},
        )
        resp.raise_for_status()
        return resp.json()


async def list_webhooks() -> list[dict]:
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.post(f"{BASE_URL}/webhooks", json={})
        resp.raise_for_status()
        return resp.json().get("webhooks", [])


async def delete_webhook(webhook_id: str) -> bool:
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.delete(f"{BASE_URL}/webhooks/{webhook_id}")
        resp.raise_for_status()
        return True


# ─── Webhook event handler ────────────────────────────────────────────────────

async def handle_webhook_event(payload: dict) -> None:
    """Process incoming Etherfuse webhook events."""
    event_type = payload.get("type")
    log.info("etherfuse_webhook_received", event_type=event_type)

    if event_type == "order_updated":
        order = payload.get("data", {})
        status = order.get("status")
        order_id = order.get("id")
        log.info("etherfuse_order_updated", order_id=order_id, status=status)
        # Trigger downstream actions based on order status
        # e.g., update escrow state, notify frontend via WebSocket

    elif event_type == "customer_updated":
        log.info("etherfuse_customer_updated", data=payload.get("data"))

    elif event_type == "bank_account_updated":
        log.info("etherfuse_bank_account_updated", data=payload.get("data"))
