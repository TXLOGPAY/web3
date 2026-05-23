"""Escrow routes — manage payment escrow between importer and exporter."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    CreateEscrowRequest, FundEscrowRequest,
    ReleaseEscrowRequest, EscrowStateResponse,
    BuildReleaseXdrRequest,
)
from app.services import stellar_service
from app.core.config import settings
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/escrow", tags=["escrow"])

RELEASE_FLAG_TO_ENUM = {
    "inco": 0, "emba": 1, "modal": 2, "dese": 3, "libera": 4,
}


@router.post("/create", summary="Create a new escrow operation")
async def create_escrow(req: CreateEscrowRequest):
    """
    Create a new escrow between importer and exporter.
    Platform fee of 2% (TxLogPay) is automatically calculated.
    """
    if not settings.ESCROW_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="ESCROW_CONTRACT_ID not configured")

    from stellar_sdk import scval, Keypair

    release_flag_idx = RELEASE_FLAG_TO_ENUM.get(req.release_at_flag.value, 4)
    platform_fee = (req.total_amount * settings.PLATFORM_FEE_BPS) // 10_000

    args = [
        scval.to_address(req.importer_public_key),
        scval.to_uint64(req.op_id),
        scval.to_address(req.exporter_public_key),
        scval.to_address(req.token_address),
        scval.to_int128(req.total_amount),
        scval.to_enum("ReleaseFlag", release_flag_idx, None),
        scval.to_symbol(req.incoterm.value),
        scval.to_symbol(req.invoice_number),
    ]

    try:
        result = await stellar_service.invoke_soroban_contract(
            contract_id=settings.ESCROW_CONTRACT_ID,
            function_name="create_escrow",
            args=args,
            caller_secret=req.importer_secret,
        )
        return {
            "op_id": req.op_id,
            "transaction_hash": result.get("hash"),
            "total_amount": req.total_amount,
            "platform_fee": platform_fee,
            "net_amount": req.total_amount - platform_fee,
            "release_at_flag": req.release_at_flag,
            "status": "created",
        }
    except Exception as e:
        log.error("escrow_create_failed", op_id=req.op_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fund", summary="Fund the escrow (importer deposits tokens)")
async def fund_escrow(req: FundEscrowRequest):
    """Transfer tokens from importer to the escrow contract."""
    if not settings.ESCROW_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="ESCROW_CONTRACT_ID not configured")

    from stellar_sdk import scval, Keypair

    caller_pk = Keypair.from_secret(req.importer_secret).public_key
    args = [
        scval.to_address(caller_pk),
        scval.to_uint64(req.op_id),
    ]

    try:
        result = await stellar_service.invoke_soroban_contract(
            contract_id=settings.ESCROW_CONTRACT_ID,
            function_name="fund",
            args=args,
            caller_secret=req.importer_secret,
        )
        return {"op_id": req.op_id, "transaction_hash": result.get("hash"), "status": "funded"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/release", summary="Release payment to exporter after flag verification")
async def release_escrow(req: ReleaseEscrowRequest):
    """
    Release escrow funds to exporter.
    Verifies the required logistics flag is set on FlagsReceptor before releasing.
    Platform automatically receives 2% fee.
    """
    if not settings.ESCROW_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="ESCROW_CONTRACT_ID not configured")

    from stellar_sdk import scval, Keypair

    caller_pk = Keypair.from_secret(req.caller_secret).public_key
    args = [
        scval.to_address(caller_pk),
        scval.to_uint64(req.op_id),
    ]

    try:
        result = await stellar_service.invoke_soroban_contract(
            contract_id=settings.ESCROW_CONTRACT_ID,
            function_name="release",
            args=args,
            caller_secret=req.caller_secret,
        )
        log.info("escrow_released", op_id=req.op_id, tx=result.get("hash"))
        return {
            "op_id": req.op_id,
            "transaction_hash": result.get("hash"),
            "status": "released",
            "message": "Payment released to exporter. 2% fee sent to TxLogPay platform.",
        }
    except Exception as e:
        log.error("escrow_release_failed", op_id=req.op_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/build-release", summary="Build unsigned release transaction XDR")
async def build_release_xdr(req: BuildReleaseXdrRequest):
    """
    Build and simulate a release transaction; return unsigned prepared XDR.
    The caller signs the XDR client-side and submits via POST /stellar/submit.
    No secret key is required or accepted.
    """
    if not settings.ESCROW_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="ESCROW_CONTRACT_ID not configured")

    from stellar_sdk import scval

    args = [
        scval.to_address(req.caller_public_key),
        scval.to_uint64(req.op_id),
    ]

    try:
        xdr = await stellar_service.build_soroban_transaction_xdr(
            contract_id=settings.ESCROW_CONTRACT_ID,
            function_name="release",
            args=args,
            caller_public_key=req.caller_public_key,
        )
        return {"xdr": xdr, "network_passphrase": stellar_service.NETWORK_PASSPHRASE}
    except Exception as e:
        log.error("escrow_build_release_failed", op_id=req.op_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/dispute/{op_id}", summary="Open a dispute on an escrow")
async def dispute_escrow(op_id: int, caller_secret: str):
    from stellar_sdk import scval, Keypair

    caller_pk = Keypair.from_secret(caller_secret).public_key
    args = [scval.to_address(caller_pk), scval.to_uint64(op_id)]

    try:
        result = await stellar_service.invoke_soroban_contract(
            contract_id=settings.ESCROW_CONTRACT_ID,
            function_name="dispute",
            args=args,
            caller_secret=caller_secret,
        )
        return {"op_id": op_id, "transaction_hash": result.get("hash"), "status": "disputed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/fee/{amount}", summary="Calculate platform fee for an amount")
async def calculate_fee(amount: int):
    """Calculate the 2% TxLogPay platform fee for a given amount."""
    fee = (amount * settings.PLATFORM_FEE_BPS) // 10_000
    return {
        "total_amount": amount,
        "platform_fee_bps": settings.PLATFORM_FEE_BPS,
        "platform_fee": fee,
        "net_amount": amount - fee,
        "fee_percent": settings.PLATFORM_FEE_BPS / 100,
    }
