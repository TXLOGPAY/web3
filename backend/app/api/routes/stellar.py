"""Stellar account management routes."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    CreateAccountRequest, AccountInfo,
    FundAccountRequest, SubmitXdrRequest,
)
from app.services import stellar_service

router = APIRouter(prefix="/stellar", tags=["stellar"])


@router.post("/accounts", response_model=AccountInfo, summary="Create Stellar account")
async def create_account(req: CreateAccountRequest):
    """Generate a new Stellar keypair for importer or exporter."""
    account = stellar_service.create_stellar_account(req.role, req.label)
    return account


@router.post("/accounts/fund", summary="Fund testnet account via Friendbot")
async def fund_account(req: FundAccountRequest):
    """Fund a Stellar testnet account using Friendbot."""
    try:
        result = await stellar_service.fund_account_friendbot(req.public_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts/{public_key}/balance", summary="Get account balance")
async def get_balance(public_key: str):
    """Fetch account balances from Stellar Horizon."""
    try:
        return await stellar_service.get_account_balance(public_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/setup-demo", summary="Create demo platform + importer + exporter accounts")
async def setup_demo_accounts():
    """
    Create and fund three demo accounts on testnet:
    - Platform (TxLogPay fee wallet)
    - Importer demo
    - Exporter demo
    """
    try:
        accounts = await stellar_service.create_platform_accounts()
        return {
            "message": "Demo accounts created and funded on Stellar testnet",
            "accounts": accounts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit", summary="Submit a pre-signed transaction XDR")
async def submit_transaction(req: SubmitXdrRequest):
    """Submit a Soroban transaction that was signed client-side."""
    try:
        result = await stellar_service.submit_signed_transaction_xdr(req.signed_xdr)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer", summary="Transfer XLM between accounts")
async def transfer_xlm(
    sender_secret: str,
    destination_public: str,
    amount: str,
    memo: str = "",
):
    """Transfer XLM from one account to another."""
    try:
        tx_hash = await stellar_service.transfer_xlm(
            sender_secret, destination_public, amount, memo
        )
        return {"transaction_hash": tx_hash, "amount": amount, "destination": destination_public}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
