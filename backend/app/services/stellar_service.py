"""Stellar account management, funding, and contract invocation."""
import httpx
from stellar_sdk import (
    Keypair,
    Network,
    Server,
    TransactionBuilder,
    Asset,
    SorobanServer,
)
from stellar_sdk.soroban_rpc import GetTransactionStatus
from stellar_sdk import xdr as stellar_xdr
from app.core.config import settings
import structlog

log = structlog.get_logger()

NETWORK_PASSPHRASE = (
    Network.TESTNET_NETWORK_PASSPHRASE
    if settings.STELLAR_NETWORK == "testnet"
    else Network.PUBLIC_NETWORK_PASSPHRASE
)


# ─── Account management ───────────────────────────────────────────────────────

def create_stellar_account(role: str, label: str) -> dict:
    """Generate a new Stellar keypair."""
    keypair = Keypair.random()
    return {
        "public_key": keypair.public_key,
        "secret_key": keypair.secret,
        "role": role,
        "label": label,
        "funded": False,
    }


async def fund_account_friendbot(public_key: str) -> dict:
    """Fund a testnet account using Stellar Friendbot."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            settings.STELLAR_FRIENDBOT_URL,
            params={"addr": public_key},
        )
        resp.raise_for_status()
        log.info("friendbot_funded", public_key=public_key)
        return {"funded": True, "public_key": public_key, "response": resp.json()}


async def get_account_balance(public_key: str) -> dict:
    """Fetch account balances from Horizon."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{settings.STELLAR_HORIZON_URL}/accounts/{public_key}"
        )
        if resp.status_code == 404:
            return {"public_key": public_key, "balances": [], "exists": False}
        resp.raise_for_status()
        data = resp.json()
        balances = [
            {
                "asset": b.get("asset_type") if b.get("asset_type") == "native"
                         else f"{b.get('asset_code')}/{b.get('asset_issuer')}",
                "balance": float(b["balance"]),
            }
            for b in data.get("balances", [])
        ]
        return {"public_key": public_key, "balances": balances, "exists": True}


async def create_platform_accounts() -> dict:
    """Create importer, exporter, and platform accounts, fund them on testnet."""
    accounts = {}
    for role in ["platform", "importer_demo", "exporter_demo"]:
        kp = Keypair.random()
        accounts[role] = {
            "public_key": kp.public_key,
            "secret_key": kp.secret,
            "role": role,
        }
        # Fund each via Friendbot
        await fund_account_friendbot(kp.public_key)
        log.info("account_created_and_funded", role=role, pk=kp.public_key)

    return accounts


async def transfer_xlm(
    sender_secret: str,
    destination_public: str,
    amount: str,
    memo: str = "",
) -> str:
    """Transfer XLM between accounts. Returns transaction hash."""
    sender_keypair = Keypair.from_secret(sender_secret)
    server = Server(settings.STELLAR_HORIZON_URL)

    sender_account = server.load_account(sender_keypair.public_key)
    base_fee = server.fetch_base_fee()

    tx_builder = (
        TransactionBuilder(
            source_account=sender_account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=base_fee,
        )
        .append_payment_op(
            destination=destination_public,
            asset=Asset.native(),
            amount=amount,
        )
        .set_timeout(30)
    )
    if memo:
        tx_builder.add_text_memo(memo)

    transaction = tx_builder.build()
    transaction.sign(sender_keypair)

    response = server.submit_transaction(transaction)
    log.info("xlm_transferred", hash=response["hash"], amount=amount)
    return response["hash"]


# ─── Soroban contract invocation ─────────────────────────────────────────────

async def invoke_soroban_contract(
    contract_id: str,
    function_name: str,
    args: list,
    caller_secret: str,
) -> dict:
    """Invoke a Soroban smart contract function."""
    caller_kp = Keypair.from_secret(caller_secret)

    soroban_server = SorobanServer(settings.STELLAR_RPC_URL)
    horizon_server = Server(settings.STELLAR_HORIZON_URL)

    source_account = horizon_server.load_account(caller_kp.public_key)

    tx = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=1_000_000,
        )
        .append_invoke_contract_function_op(
            contract_id=contract_id,
            function_name=function_name,
            parameters=args,
        )
        .set_timeout(60)
        .build()
    )

    # Simulate first
    simulate_resp = soroban_server.simulate_transaction(tx)
    if hasattr(simulate_resp, "error"):
        raise RuntimeError(f"Simulation failed: {simulate_resp.error}")

    tx = soroban_server.prepare_transaction(tx)
    tx.sign(caller_kp)

    send_resp = soroban_server.send_transaction(tx)
    tx_hash = send_resp.hash

    # Poll for confirmation
    import time
    for _ in range(30):
        get_resp = soroban_server.get_transaction(tx_hash)
        if get_resp.status == GetTransactionStatus.SUCCESS:
            log.info("contract_invoked", fn=function_name, hash=tx_hash)
            return {"hash": tx_hash, "status": "success", "result": str(get_resp.return_value)}
        if get_resp.status == GetTransactionStatus.FAILED:
            raise RuntimeError(f"Contract call failed: {tx_hash}")
        time.sleep(2)

    raise TimeoutError(f"Transaction {tx_hash} not confirmed after 60s")


async def build_soroban_transaction_xdr(
    contract_id: str,
    function_name: str,
    args: list,
    caller_public_key: str,
) -> str:
    """Build and simulate a Soroban transaction; return unsigned prepared XDR.

    The caller must sign the XDR client-side and submit via submit_signed_transaction_xdr.
    """
    soroban_server = SorobanServer(settings.STELLAR_RPC_URL)
    horizon_server = Server(settings.STELLAR_HORIZON_URL)

    source_account = horizon_server.load_account(caller_public_key)

    tx = (
        TransactionBuilder(
            source_account=source_account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=1_000_000,
        )
        .append_invoke_contract_function_op(
            contract_id=contract_id,
            function_name=function_name,
            parameters=args,
        )
        .set_timeout(60)
        .build()
    )

    simulate_resp = soroban_server.simulate_transaction(tx)
    if hasattr(simulate_resp, "error"):
        raise RuntimeError(f"Simulation failed: {simulate_resp.error}")

    prepared_tx = soroban_server.prepare_transaction(tx)
    return prepared_tx.to_xdr()


async def submit_signed_transaction_xdr(signed_xdr: str) -> dict:
    """Submit a pre-signed Soroban transaction XDR to the network."""
    from stellar_sdk import TransactionEnvelope

    soroban_server = SorobanServer(settings.STELLAR_RPC_URL)
    tx = TransactionEnvelope.from_xdr(signed_xdr, network_passphrase=NETWORK_PASSPHRASE)

    send_resp = soroban_server.send_transaction(tx)
    tx_hash = send_resp.hash

    import time
    for _ in range(30):
        get_resp = soroban_server.get_transaction(tx_hash)
        if get_resp.status == GetTransactionStatus.SUCCESS:
            log.info("contract_invoked_via_xdr", hash=tx_hash)
            return {"hash": tx_hash, "status": "success", "result": str(get_resp.return_value)}
        if get_resp.status == GetTransactionStatus.FAILED:
            raise RuntimeError(f"Contract call failed: {tx_hash}")
        time.sleep(2)

    raise TimeoutError(f"Transaction {tx_hash} not confirmed after 60s")
