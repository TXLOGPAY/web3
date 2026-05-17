//! TradeInfo — receptor de dados de comércio exterior minerados via RAG.
//! Armazena: hash Merkle root, quantidades, tipo de produto, incoterm, invoice.
#![no_std]

use soroban_sdk::{
    bytes, contract, contractimpl, contracttype, symbol_short, Address, Bytes, BytesN, Env,
    String, Symbol,
};

// ─── storage keys ─────────────────────────────────────────────────────────────
#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    TradeRecord(u64), // op_id → TradeRecord
    MerkleRoot(u64),  // op_id → Bytes32
}

// ─── trade record ─────────────────────────────────────────────────────────────
#[contracttype]
#[derive(Clone)]
pub struct CargoItem {
    pub description: Symbol,
    pub hs_code: Symbol,       // NCM/HS code
    pub quantity: i128,
    pub unit: Symbol,          // KG, TON, UN, etc.
    pub unit_value_usd: i128,  // cents
}

#[contracttype]
#[derive(Clone)]
pub struct TradeRecord {
    pub op_id: u64,
    pub invoice_number: Symbol,
    pub bill_of_lading: Symbol,
    pub id_incoterm: Symbol,
    pub product_type: Symbol,
    pub total_quantity: i128,
    pub total_value_usd: i128,  // cents
    pub currency: Symbol,
    pub origin_country: Symbol,
    pub dest_country: Symbol,
    pub siscomex_id: Symbol,
    pub merkle_root: BytesN<32>,
    pub registered_at: u64,
    pub registered_by: Address,
}

// ─── events ───────────────────────────────────────────────────────────────────
const EVT_REGISTERED: Symbol = symbol_short!("registered");
const EVT_MERKLE_UPD: Symbol = symbol_short!("merkle_upd");

#[contract]
pub struct TradeInfoContract;

#[contractimpl]
impl TradeInfoContract {
    // ── Initialize ────────────────────────────────────────────────────────────
    pub fn initialize(env: Env, admin: Address) {
        if env.storage().instance().has(&DataKey::Admin) {
            panic!("already initialized");
        }
        env.storage().instance().set(&DataKey::Admin, &admin);
    }

    // ── Register trade data (called by backend after RAG extraction) ──────────
    pub fn register_trade(
        env: Env,
        caller: Address,
        op_id: u64,
        invoice_number: Symbol,
        bill_of_lading: Symbol,
        id_incoterm: Symbol,
        product_type: Symbol,
        total_quantity: i128,
        total_value_usd: i128,
        currency: Symbol,
        origin_country: Symbol,
        dest_country: Symbol,
        siscomex_id: Symbol,
        merkle_root: BytesN<32>,
    ) {
        caller.require_auth();
        Self::require_admin(&env, &caller);

        if env
            .storage()
            .persistent()
            .has(&DataKey::TradeRecord(op_id))
        {
            panic!("trade record already exists");
        }

        let record = TradeRecord {
            op_id,
            invoice_number,
            bill_of_lading,
            id_incoterm,
            product_type,
            total_quantity,
            total_value_usd,
            currency,
            origin_country,
            dest_country,
            siscomex_id,
            merkle_root: merkle_root.clone(),
            registered_at: env.ledger().timestamp(),
            registered_by: caller.clone(),
        };

        env.storage()
            .persistent()
            .set(&DataKey::TradeRecord(op_id), &record);
        env.storage()
            .persistent()
            .set(&DataKey::MerkleRoot(op_id), &merkle_root);

        env.events()
            .publish((EVT_REGISTERED, op_id), (caller, merkle_root));
    }

    // ── Update Merkle root (after new cargo items are added) ──────────────────
    pub fn update_merkle_root(
        env: Env,
        caller: Address,
        op_id: u64,
        new_root: BytesN<32>,
    ) {
        caller.require_auth();
        Self::require_admin(&env, &caller);

        let mut record: TradeRecord = Self::get_record(&env, op_id);
        record.merkle_root = new_root.clone();
        env.storage()
            .persistent()
            .set(&DataKey::TradeRecord(op_id), &record);
        env.storage()
            .persistent()
            .set(&DataKey::MerkleRoot(op_id), &new_root);

        env.events()
            .publish((EVT_MERKLE_UPD, op_id), (caller, new_root));
    }

    // ── Queries ───────────────────────────────────────────────────────────────
    pub fn get_trade_record(env: Env, op_id: u64) -> TradeRecord {
        Self::get_record(&env, op_id)
    }

    pub fn get_merkle_root(env: Env, op_id: u64) -> BytesN<32> {
        env.storage()
            .persistent()
            .get(&DataKey::MerkleRoot(op_id))
            .unwrap_or_else(|| panic!("merkle root not found"))
    }

    pub fn verify_merkle_root(env: Env, op_id: u64, expected_root: BytesN<32>) -> bool {
        let stored: BytesN<32> = env
            .storage()
            .persistent()
            .get(&DataKey::MerkleRoot(op_id))
            .unwrap_or_else(|| panic!("not found"));
        stored == expected_root
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    fn get_record(env: &Env, op_id: u64) -> TradeRecord {
        env.storage()
            .persistent()
            .get(&DataKey::TradeRecord(op_id))
            .unwrap_or_else(|| panic!("record not found"))
    }

    fn require_admin(env: &Env, caller: &Address) {
        let admin: Address = env
            .storage()
            .instance()
            .get(&DataKey::Admin)
            .unwrap_or_else(|| panic!("not initialized"));
        if caller != &admin {
            panic!("only admin");
        }
    }
}
