"""RAG routes — invoice upload, extraction, and Merkle anchoring."""
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.models.schemas import InvoiceExtractionResponse, TradeRecordRequest
from app.services.rag_service import extract_invoice_data
from app.services.merkle_tree import build_trade_merkle_tree, compute_merkle_root
from app.services import stellar_service
from app.core.config import settings
import structlog

log = structlog.get_logger()
router = APIRouter(prefix="/rag", tags=["rag"])


@router.post(
    "/extract",
    response_model=InvoiceExtractionResponse,
    summary="Upload invoice and extract trade data via RAG",
)
async def extract_invoice(
    file: UploadFile = File(..., description="Invoice PDF, DOCX or TXT"),
):
    """
    Process an uploaded invoice document through LlamaIndex RAG pipeline.
    Extracts: invoice number, BL, incoterm, product, quantities, values, countries.
    Returns extracted data + Merkle root hash for blockchain anchoring.
    """
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use PDF, DOCX, or TXT.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    try:
        extracted = await extract_invoice_data(file_bytes, file.filename)
        return InvoiceExtractionResponse(**extracted)
    except Exception as e:
        log.error("rag_extraction_error", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/merkle/compute", summary="Compute Merkle root from trade data dict")
async def compute_merkle(data: dict):
    """
    Compute a Merkle root from a trade data dictionary.
    Use this to verify data integrity before anchoring to blockchain.
    """
    try:
        tree = build_trade_merkle_tree(data)
        return {
            "root": tree.root_hex,
            "leaves": tree.leaves_raw,
            "leaf_count": len(tree.leaves_raw),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/merkle/verify", summary="Verify Merkle proof for a leaf")
async def verify_merkle(
    leaf_value: str = Form(...),
    proof: str = Form(..., description="JSON array of proof steps"),
    root_hex: str = Form(...),
):
    """Verify that a leaf value is part of a Merkle tree given its proof."""
    import json
    from app.services.merkle_tree import MerkleTree

    try:
        proof_list = json.loads(proof)
        dummy_tree = MerkleTree([leaf_value])
        valid = dummy_tree.verify_proof(leaf_value, proof_list, root_hex)
        return {"valid": valid, "leaf": leaf_value, "root": root_hex}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/anchor", summary="Anchor Merkle root to blockchain via TradeInfo contract")
async def anchor_to_blockchain(req: TradeRecordRequest):
    """
    Register extracted trade data and its Merkle root on the Stellar blockchain
    via the TradeInfo contract.
    """
    if not settings.TRADE_INFO_CONTRACT_ID:
        raise HTTPException(status_code=503, detail="TRADE_INFO_CONTRACT_ID not configured")

    from stellar_sdk import scval, Keypair
    import bytes as _bytes

    merkle_bytes = bytes.fromhex(req.merkle_root.replace("0x", ""))
    if len(merkle_bytes) != 32:
        raise HTTPException(status_code=400, detail="merkle_root must be 32 bytes hex")

    caller_pk = Keypair.from_secret(req.caller_secret).public_key

    args = [
        scval.to_address(caller_pk),
        scval.to_uint64(req.op_id),
        scval.to_symbol(req.invoice_number),
        scval.to_symbol(req.bill_of_lading),
        scval.to_symbol(req.id_incoterm),
        scval.to_symbol(req.product_type),
        scval.to_int128(int(req.total_quantity * 1000)),  # fixed-point ×1000
        scval.to_int128(int(req.total_value_usd * 100)),  # cents
        scval.to_symbol(req.currency),
        scval.to_symbol(req.origin_country),
        scval.to_symbol(req.dest_country),
        scval.to_symbol(req.siscomex_id),
        scval.to_bytes_n(merkle_bytes),
    ]

    try:
        result = await stellar_service.invoke_soroban_contract(
            contract_id=settings.TRADE_INFO_CONTRACT_ID,
            function_name="register_trade",
            args=args,
            caller_secret=req.caller_secret,
        )
        log.info("trade_anchored", op_id=req.op_id, merkle=req.merkle_root, tx=result.get("hash"))
        return {
            "op_id": req.op_id,
            "merkle_root": req.merkle_root,
            "transaction_hash": result.get("hash"),
            "status": "anchored",
        }
    except Exception as e:
        log.error("anchor_failed", op_id=req.op_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
