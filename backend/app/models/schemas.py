from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


# ─── Logistics flags ──────────────────────────────────────────────────────────

class LogisticFlag(str, Enum):
    inco = "inco"
    emba = "emba"
    modal = "modal"
    dese = "dese"
    libera = "libera"


class FlagsState(BaseModel):
    op_id: int
    inco: bool = False
    emba: bool = False
    modal: bool = False
    dese: bool = False
    libera: bool = False
    updated_at: Optional[int] = None
    setter: Optional[str] = None


class SetFlagRequest(BaseModel):
    op_id: int
    flag: LogisticFlag
    caller_secret: str = Field(description="Secret key of authorized setter")


# ─── Incoterm ─────────────────────────────────────────────────────────────────

class Incoterm(str, Enum):
    EXW = "EXW"
    FCA = "FCA"
    FOB = "FOB"
    CFR = "CFR"
    CIF = "CIF"
    CPT = "CPT"
    CIP = "CIP"
    DAP = "DAP"
    DPU = "DPU"
    DDP = "DDP"


# ─── Escrow ───────────────────────────────────────────────────────────────────

class EscrowStatus(str, Enum):
    created = "created"
    funded = "funded"
    released = "released"
    refunded = "refunded"
    disputed = "disputed"


class CreateEscrowRequest(BaseModel):
    op_id: int
    importer_public_key: str
    exporter_public_key: str
    token_address: str
    total_amount: int = Field(description="Amount in stroops (1 XLM = 10_000_000)")
    release_at_flag: LogisticFlag
    incoterm: Incoterm
    invoice_number: str
    importer_secret: str


class FundEscrowRequest(BaseModel):
    op_id: int
    importer_secret: str


class ReleaseEscrowRequest(BaseModel):
    op_id: int
    caller_secret: str


class EscrowStateResponse(BaseModel):
    op_id: int
    importer: str
    exporter: str
    token: str
    total_amount: int
    platform_fee: int
    net_amount: int
    release_at_flag: str
    status: EscrowStatus
    funded_at: Optional[int] = None
    released_at: Optional[int] = None
    incoterm: str
    invoice_number: str


# ─── Trade Info ───────────────────────────────────────────────────────────────

class TradeRecordRequest(BaseModel):
    op_id: int
    invoice_number: str
    bill_of_lading: str
    id_incoterm: str
    product_type: str
    total_quantity: float
    total_value_usd: float
    currency: str = "USD"
    origin_country: str
    dest_country: str
    siscomex_id: str
    merkle_root: str = Field(description="32-byte hex Merkle root")
    caller_secret: str


class TradeRecordResponse(BaseModel):
    op_id: int
    invoice_number: str
    bill_of_lading: str
    id_incoterm: str
    product_type: str
    total_quantity: float
    total_value_usd: float
    currency: str
    origin_country: str
    dest_country: str
    siscomex_id: str
    merkle_root: str
    registered_at: int
    registered_by: str


# ─── Stellar account ──────────────────────────────────────────────────────────

class CreateAccountRequest(BaseModel):
    role: Literal["importer", "exporter"]
    label: str = Field(description="Human-friendly label, e.g. company name")


class AccountInfo(BaseModel):
    public_key: str
    secret_key: str
    role: str
    label: str
    balance_xlm: Optional[float] = None
    funded: bool = False


class FundAccountRequest(BaseModel):
    public_key: str
    amount_xlm: float = Field(default=10000.0, description="Amount to fund (testnet)")


# ─── RAG / Invoice ───────────────────────────────────────────────────────────

class InvoiceExtractionResponse(BaseModel):
    invoice_number: str
    bill_of_lading: Optional[str] = None
    exporter: Optional[str] = None
    importer: Optional[str] = None
    incoterm: Optional[str] = None
    product_description: Optional[str] = None
    hs_code: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price_usd: Optional[float] = None
    total_value_usd: Optional[float] = None
    currency: Optional[str] = None
    origin_country: Optional[str] = None
    dest_country: Optional[str] = None
    siscomex_id: Optional[str] = None
    raw_text: Optional[str] = None
    merkle_root: Optional[str] = None
    merkle_leaves: Optional[list[str]] = None


# ─── Etherfuse ───────────────────────────────────────────────────────────────

class EtherfuseOnboardRequest(BaseModel):
    customer_email: str
    customer_name: str
    role: Literal["importer", "exporter"]
    stellar_public_key: str


class EtherfuseOrderRequest(BaseModel):
    type: Literal["onramp", "offramp"]
    amount: float
    currency: str = "USD"
    stellar_public_key: str
    op_id: Optional[int] = None


class EtherfuseOrderResponse(BaseModel):
    order_id: str
    status: str
    type: str
    amount: float
    currency: str
    stellar_public_key: str
    created_at: str


# ─── XDR build / submit (client-side signing) ────────────────────────────────

class BuildSetFlagXdrRequest(BaseModel):
    op_id: int
    flag: LogisticFlag
    caller_public_key: str = Field(description="Caller public key (G...) — no secret sent")


class BuildReleaseXdrRequest(BaseModel):
    op_id: int
    caller_public_key: str = Field(description="Caller public key (G...) — no secret sent")


class SubmitXdrRequest(BaseModel):
    signed_xdr: str = Field(description="Base64 signed transaction XDR")


# ─── Operation (unified) ─────────────────────────────────────────────────────

class OperationSummary(BaseModel):
    op_id: int
    importer: str
    exporter: str
    incoterm: str
    invoice_number: str
    bill_of_lading: Optional[str] = None
    escrow_amount: float
    currency: str
    current_flag: str
    release_at_flag: str
    escrow_status: str
    created_at: Optional[str] = None
    merkle_root: Optional[str] = None
