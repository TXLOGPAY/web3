"""Logistics flags routes — trigger FlagsReceptor smart contract."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import SetFlagRequest, FlagsState, LogisticFlag, BuildSetFlagXdrRequest
from app.services import stellar_service
from app.core.config import settings
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/flags", tags=["flags"])

# Maps flag name to contract function name
FLAG_TO_FN = {
    LogisticFlag.inco: "set_inco",
    LogisticFlag.emba: "set_emba",
    LogisticFlag.modal: "set_modal",
    LogisticFlag.dese: "set_dese",
    LogisticFlag.libera: "set_libera",
}


@router.post("/set", summary="Set a logistics flag on-chain")
async def set_flag(req: SetFlagRequest):
    """
    Invoke FlagsReceptor contract to set the given logistics flag.
    Flags follow the sequential order: inco → emba → modal → dese → libera
    """
    if not settings.FLAGS_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="FLAGS_CONTRACT_ID not configured")

    fn_name = FLAG_TO_FN.get(req.flag)
    if not fn_name:
        raise HTTPException(status_code=400, detail="Unknown flag")

    from stellar_sdk import scval

    args = [
        scval.to_address(stellar_service.Keypair.from_secret(req.caller_secret).public_key),
        scval.to_uint64(req.op_id),
    ]

    try:
        result = await stellar_service.invoke_soroban_contract(
            contract_id=settings.FLAGS_CONTRACT_ID,
            function_name=fn_name,
            args=args,
            caller_secret=req.caller_secret,
        )
        log.info("flag_set", flag=req.flag, op_id=req.op_id, tx=result.get("hash"))
        return {
            "flag": req.flag,
            "op_id": req.op_id,
            "transaction_hash": result.get("hash"),
            "status": "set",
        }
    except Exception as e:
        log.error("flag_set_failed", flag=req.flag, op_id=req.op_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/build", summary="Build unsigned set-flag transaction XDR")
async def build_set_flag_xdr(req: BuildSetFlagXdrRequest):
    """
    Build and simulate a set-flag transaction; return unsigned prepared XDR.
    The caller signs the XDR client-side and submits via POST /stellar/submit.
    No secret key is required or accepted.
    """
    if not settings.FLAGS_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="FLAGS_CONTRACT_ID not configured")

    fn_name = FLAG_TO_FN.get(req.flag)
    if not fn_name:
        raise HTTPException(status_code=400, detail="Unknown flag")

    from stellar_sdk import scval

    args = [
        scval.to_address(req.caller_public_key),
        scval.to_uint64(req.op_id),
    ]

    try:
        xdr = await stellar_service.build_soroban_transaction_xdr(
            contract_id=settings.FLAGS_CONTRACT_ID,
            function_name=fn_name,
            args=args,
            caller_public_key=req.caller_public_key,
        )
        return {"xdr": xdr, "network_passphrase": stellar_service.NETWORK_PASSPHRASE}
    except Exception as e:
        log.error("flag_build_failed", flag=req.flag, op_id=req.op_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{op_id}", summary="Get current flags state for an operation")
async def get_flags(op_id: int):
    """Query the current flags state from FlagsReceptor contract."""
    if not settings.FLAGS_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="FLAGS_CONTRACT_ID not configured")

    from stellar_sdk import scval

    try:
        result = await stellar_service.invoke_soroban_contract(
            contract_id=settings.FLAGS_CONTRACT_ID,
            function_name="get_flags",
            args=[scval.to_uint64(op_id)],
            caller_secret=settings.PLATFORM_SECRET_KEY,
        )
        return {"op_id": op_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/init/{op_id}", summary="Initialize a new operation slot in FlagsReceptor")
async def init_operation(op_id: int, caller_secret: str):
    """Create a new operation slot in the FlagsReceptor contract."""
    if not settings.FLAGS_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="FLAGS_CONTRACT_ID not configured")

    from stellar_sdk import scval, Keypair

    caller_pk = Keypair.from_secret(caller_secret).public_key
    args = [
        scval.to_address(caller_pk),
        scval.to_uint64(op_id),
    ]

    try:
        result = await stellar_service.invoke_soroban_contract(
            contract_id=settings.FLAGS_CONTRACT_ID,
            function_name="init_operation",
            args=args,
            caller_secret=caller_secret,
        )
        return {"op_id": op_id, "transaction_hash": result.get("hash"), "status": "initialized"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
