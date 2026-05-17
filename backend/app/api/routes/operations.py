"""Operations routes — unified trade operation management."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import OperationSummary, CreateEscrowRequest, LogisticFlag
from app.core.config import settings
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/operations", tags=["operations"])

# In-memory store for demo (replace with DB in production)
_operations: dict[int, dict] = {}


@router.post("/", summary="Create a new trade operation")
async def create_operation(
    op_id: int,
    importer_public_key: str,
    exporter_public_key: str,
    incoterm: str,
    invoice_number: str,
    bill_of_lading: str,
    escrow_amount: float,
    currency: str,
    release_at_flag: LogisticFlag,
):
    """Initialize a new trade operation in the system."""
    if op_id in _operations:
        raise HTTPException(status_code=409, detail="Operation already exists")

    op = {
        "op_id": op_id,
        "importer": importer_public_key,
        "exporter": exporter_public_key,
        "incoterm": incoterm,
        "invoice_number": invoice_number,
        "bill_of_lading": bill_of_lading,
        "escrow_amount": escrow_amount,
        "currency": currency,
        "current_flag": "none",
        "release_at_flag": release_at_flag.value,
        "escrow_status": "created",
        "flags": {
            "inco": False,
            "emba": False,
            "modal": False,
            "dese": False,
            "libera": False,
        },
        "merkle_root": None,
        "created_at": None,
    }
    _operations[op_id] = op
    log.info("operation_created", op_id=op_id, incoterm=incoterm)
    return op


@router.get("/", summary="List all operations (platform view)")
async def list_operations():
    return {
        "operations": list(_operations.values()),
        "total": len(_operations),
        "in_escrow": sum(
            op["escrow_amount"]
            for op in _operations.values()
            if op["escrow_status"] == "funded"
        ),
        "released": sum(
            op["escrow_amount"]
            for op in _operations.values()
            if op["escrow_status"] == "released"
        ),
    }


@router.get("/importer/{public_key}", summary="List operations for an importer")
async def list_importer_operations(public_key: str):
    ops = [op for op in _operations.values() if op["importer"] == public_key]
    return {"operations": ops, "total": len(ops)}


@router.get("/exporter/{public_key}", summary="List operations for an exporter")
async def list_exporter_operations(public_key: str):
    ops = [op for op in _operations.values() if op["exporter"] == public_key]
    return {"operations": ops, "total": len(ops)}


@router.get("/{op_id}", summary="Get operation details")
async def get_operation(op_id: int):
    op = _operations.get(op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    return op


@router.patch("/{op_id}/flag", summary="Update operation flag state (after on-chain set)")
async def update_flag_state(op_id: int, flag: LogisticFlag):
    op = _operations.get(op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    op["flags"][flag.value] = True
    op["current_flag"] = flag.value
    log.info("operation_flag_updated", op_id=op_id, flag=flag.value)
    return op


@router.patch("/{op_id}/escrow-status", summary="Update escrow status")
async def update_escrow_status(op_id: int, status: str):
    op = _operations.get(op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    op["escrow_status"] = status
    return op


@router.patch("/{op_id}/merkle-root", summary="Set Merkle root after blockchain anchoring")
async def set_merkle_root(op_id: int, merkle_root: str):
    op = _operations.get(op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operation not found")
    op["merkle_root"] = merkle_root
    return op
