#!/usr/bin/env bash
# TxLogPay — Soroban contract build & deploy script (Stellar testnet)
# Usage: bash deploy.sh
# Prerequisites: stellar CLI, Rust + wasm32 target, funded deployer account

set -euo pipefail

NETWORK="testnet"
RPC_URL="https://soroban-testnet.stellar.org"
NETWORK_PASSPHRASE="Test SDF Network ; September 2015"
DEPLOYER_SECRET="${STELLAR_DEPLOYER_SECRET:?Set STELLAR_DEPLOYER_SECRET env var}"
ADMIN_PUBLIC="${STELLAR_ADMIN_PUBLIC:?Set STELLAR_ADMIN_PUBLIC env var}"
PLATFORM_PUBLIC="${STELLAR_PLATFORM_PUBLIC:?Set STELLAR_PLATFORM_PUBLIC env var}"

echo "═══════════════════════════════════════════"
echo "  TxLogPay — Soroban Deploy (testnet)"
echo "═══════════════════════════════════════════"

# ── 1. Build contracts ────────────────────────────────────────────────────────
echo ""
echo "▶ Building contracts..."
cargo build --manifest-path=Cargo.toml --target wasm32-unknown-unknown --release

FLAGS_WASM="./target/wasm32-unknown-unknown/release/flags_receptor.wasm"
ESCROW_WASM="./target/wasm32-unknown-unknown/release/escrow.wasm"
TRADE_WASM="./target/wasm32-unknown-unknown/release/trade_info.wasm"

# ── 2. Deploy FlagsReceptor ───────────────────────────────────────────────────
echo ""
echo "▶ Deploying FlagsReceptor..."
FLAGS_ID=$(stellar contract deploy \
    --wasm "$FLAGS_WASM" \
    --source "$DEPLOYER_SECRET" \
    --network "$NETWORK" \
    --network-passphrase "$NETWORK_PASSPHRASE" \
    --rpc-url "$RPC_URL")

echo "   FlagsReceptor deployed: $FLAGS_ID"

# Initialize FlagsReceptor
stellar contract invoke \
    --id "$FLAGS_ID" \
    --source "$DEPLOYER_SECRET" \
    --network "$NETWORK" \
    -- initialize \
    --admin "$ADMIN_PUBLIC" \
    --authorized_setter "$ADMIN_PUBLIC"

echo "   FlagsReceptor initialized ✓"

# ── 3. Deploy Escrow ──────────────────────────────────────────────────────────
echo ""
echo "▶ Deploying Escrow..."
ESCROW_ID=$(stellar contract deploy \
    --wasm "$ESCROW_WASM" \
    --source "$DEPLOYER_SECRET" \
    --network "$NETWORK" \
    --network-passphrase "$NETWORK_PASSPHRASE" \
    --rpc-url "$RPC_URL")

echo "   Escrow deployed: $ESCROW_ID"

# Initialize Escrow
stellar contract invoke \
    --id "$ESCROW_ID" \
    --source "$DEPLOYER_SECRET" \
    --network "$NETWORK" \
    -- initialize \
    --admin "$ADMIN_PUBLIC" \
    --platform "$PLATFORM_PUBLIC" \
    --flags_contract "$FLAGS_ID"

echo "   Escrow initialized ✓"

# ── 4. Deploy TradeInfo ───────────────────────────────────────────────────────
echo ""
echo "▶ Deploying TradeInfo..."
TRADE_ID=$(stellar contract deploy \
    --wasm "$TRADE_WASM" \
    --source "$DEPLOYER_SECRET" \
    --network "$NETWORK" \
    --network-passphrase "$NETWORK_PASSPHRASE" \
    --rpc-url "$RPC_URL")

echo "   TradeInfo deployed: $TRADE_ID"

# Initialize TradeInfo
stellar contract invoke \
    --id "$TRADE_ID" \
    --source "$DEPLOYER_SECRET" \
    --network "$NETWORK" \
    -- initialize \
    --admin "$ADMIN_PUBLIC"

echo "   TradeInfo initialized ✓"

# ── 5. Output .env update ──────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  Deployment complete! Update your .env:"
echo "═══════════════════════════════════════════"
echo ""
echo "FLAGS_CONTRACT_ID=$FLAGS_ID"
echo "ESCROW_CONTRACT_ID=$ESCROW_ID"
echo "TRADE_INFO_CONTRACT_ID=$TRADE_ID"
echo ""

# Write to .env.contracts for convenience
cat > ../.env.contracts <<EOF
FLAGS_CONTRACT_ID=$FLAGS_ID
ESCROW_CONTRACT_ID=$ESCROW_ID
TRADE_INFO_CONTRACT_ID=$TRADE_ID
EOF

echo "Contract IDs written to ../.env.contracts"
