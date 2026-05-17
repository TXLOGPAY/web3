"""Etherfuse on/off-ramp routes."""
from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import (
    EtherfuseOnboardRequest, EtherfuseOrderRequest, EtherfuseOrderResponse,
)
from app.services import etherfuse_service
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/etherfuse", tags=["etherfuse"])


@router.post("/onboard", summary="Generate KYC onboarding URL")
async def create_onboarding(req: EtherfuseOnboardRequest):
    """Generate an Etherfuse KYC/onboarding URL for a customer."""
    try:
        result = await etherfuse_service.create_onboarding_url(
            customer_email=req.customer_email,
            customer_name=req.customer_name,
            stellar_public_key=req.stellar_public_key,
            role=req.role,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders", response_model=EtherfuseOrderResponse, summary="Create ramp order")
async def create_order(req: EtherfuseOrderRequest):
    """
    Create a fiat on-ramp (fiat→Stellar) or off-ramp (Stellar→fiat) order
    via Etherfuse.
    """
    try:
        result = await etherfuse_service.create_order(
            order_type=req.type,
            amount=req.amount,
            currency=req.currency,
            stellar_public_key=req.stellar_public_key,
            memo=f"OP-{req.op_id}" if req.op_id else "",
        )
        return EtherfuseOrderResponse(
            order_id=result.get("id", ""),
            status=result.get("status", "pending"),
            type=req.type,
            amount=req.amount,
            currency=req.currency,
            stellar_public_key=req.stellar_public_key,
            created_at=result.get("created_at", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/{order_id}", summary="Get order status")
async def get_order(order_id: str):
    try:
        return await etherfuse_service.get_order(order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/orders/list", summary="List orders for a Stellar account")
async def list_orders(stellar_public_key: str):
    try:
        orders = await etherfuse_service.list_orders(stellar_public_key)
        return {"orders": orders, "count": len(orders)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/wallets", summary="List customer wallets")
async def list_wallets(stellar_public_key: str):
    try:
        wallets = await etherfuse_service.list_customer_wallets(stellar_public_key)
        return {"wallets": wallets}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhooks", summary="Register webhook")
async def create_webhook(url: str, events: list[str]):
    """Register a webhook to receive Etherfuse events."""
    try:
        return await etherfuse_service.create_webhook(url, events)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook/receive", summary="Receive Etherfuse webhook events", include_in_schema=False)
async def receive_webhook(request: Request):
    """Endpoint for Etherfuse to POST webhook events."""
    payload = await request.json()
    await etherfuse_service.handle_webhook_event(payload)
    return {"received": True}
