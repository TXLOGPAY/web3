"""TxLogPay FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.api.routes import stellar, flags, escrow, rag, etherfuse, operations

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="""
## TxLogPay — Plataforma de Comércio Exterior na Blockchain Stellar

Fluxo logístico com bandeiras on-chain:
- **inco** → Acordo Incoterm
- **emba** → Embarque da carga
- **modal** → Transporte modal
- **dese** → Desembarque
- **libera** → Liberação alfandegária

Smart contracts Soroban:
- **FlagsReceptor** — receptor de bandeiras logísticas
- **Escrow** — pagamento com taxa 2% TxLogPay, liberado por flag
- **TradeInfo** — dados de comércio exterior + Merkle root
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://txlogpay.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(stellar.router, prefix=settings.API_V1_PREFIX)
app.include_router(flags.router, prefix=settings.API_V1_PREFIX)
app.include_router(escrow.router, prefix=settings.API_V1_PREFIX)
app.include_router(rag.router, prefix=settings.API_V1_PREFIX)
app.include_router(etherfuse.router, prefix=settings.API_V1_PREFIX)
app.include_router(operations.router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["health"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "network": settings.STELLAR_NETWORK,
        "contracts": {
            "flags_receptor": settings.FLAGS_CONTRACT_ID or "not_deployed",
            "escrow": settings.ESCROW_CONTRACT_ID or "not_deployed",
            "trade_info": settings.TRADE_INFO_CONTRACT_ID or "not_deployed",
        },
    }


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
