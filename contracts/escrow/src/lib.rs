//! Escrow — pagamento entre importador e exportador com taxa 2% TxLogPay.
//! O valor é liberado conforme a flag acordada no Siscomex (release_at_flag).
#![no_std]

use soroban_sdk::{
    contract, contractimpl, contracttype, symbol_short, token, Address, Env, Symbol,
};

// ── Plataforma recebe 2% de fee ──────────────────────────────────────────────
const PLATFORM_FEE_BPS: i128 = 200; // 200 basis points = 2%
const BPS_DIVISOR: i128 = 10_000;

// ─── storage keys ────────────────────────────────────────────────────────────
#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    Platform,       // TxLogPay fee wallet
    FlagsContract,  // address of FlagsReceptor contract
    Escrow(u64),    // op_id → EscrowState
    Locked(u64),    // reentrancy guard per operation
}

// ─── release trigger flags ───────────────────────────────────────────────────
/// Maps to the logistics flags in FlagsReceptor.
#[contracttype]
#[derive(Clone, PartialEq)]
pub enum ReleaseFlag {
    Inco,
    Emba,
    Modal,
    Dese,
    Libera,
}

// ─── escrow states ───────────────────────────────────────────────────────────
#[contracttype]
#[derive(Clone, PartialEq)]
pub enum EscrowStatus {
    Created,
    Funded,
    Released,
    Refunded,
    Disputed,
}

#[contracttype]
#[derive(Clone)]
pub struct EscrowState {
    pub op_id: u64,
    pub importer: Address,
    pub exporter: Address,
    pub token: Address,
    pub total_amount: i128,
    pub platform_fee: i128,
    pub net_amount: i128,
    pub release_at_flag: ReleaseFlag,
    pub status: EscrowStatus,
    pub funded_at: u64,
    pub released_at: u64,
    pub incoterm: Symbol,
    pub invoice_number: Symbol,
}

// ─── events ──────────────────────────────────────────────────────────────────
const EVT_FUNDED: Symbol = symbol_short!("funded");
const EVT_RELEASED: Symbol = symbol_short!("released");
const EVT_REFUNDED: Symbol = symbol_short!("refunded");
const EVT_DISPUTED: Symbol = symbol_short!("disputed");

#[contract]
pub struct EscrowContract;

#[contractimpl]
impl EscrowContract {
    // ── Initialize ────────────────────────────────────────────────────────────
    pub fn initialize(
        env: Env,
        admin: Address,
        platform: Address,
        flags_contract: Address,
    ) {
        if env.storage().instance().has(&DataKey::Admin) {
            panic!("already initialized");
        }
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage().instance().set(&DataKey::Platform, &platform);
        env.storage()
            .instance()
            .set(&DataKey::FlagsContract, &flags_contract);
    }

    // ── Create escrow ─────────────────────────────────────────────────────────
    pub fn create_escrow(
        env: Env,
        importer: Address,
        op_id: u64,
        exporter: Address,
        token: Address,
        total_amount: i128,
        release_at_flag: ReleaseFlag,
        incoterm: Symbol,
        invoice_number: Symbol,
    ) {
        importer.require_auth();
        Self::require_not_locked(&env, op_id);

        if total_amount <= 0 {
            panic!("amount must be positive");
        }
        if env.storage().persistent().has(&DataKey::Escrow(op_id)) {
            panic!("escrow already exists");
        }

        let platform_fee = (total_amount * PLATFORM_FEE_BPS) / BPS_DIVISOR;
        let net_amount = total_amount - platform_fee;

        let state = EscrowState {
            op_id,
            importer,
            exporter,
            token,
            total_amount,
            platform_fee,
            net_amount,
            release_at_flag,
            status: EscrowStatus::Created,
            funded_at: 0,
            released_at: 0,
            incoterm,
            invoice_number,
        };
        env.storage()
            .persistent()
            .set(&DataKey::Escrow(op_id), &state);
    }

    // ── Fund escrow (importer deposits tokens) ────────────────────────────────
    pub fn fund(env: Env, importer: Address, op_id: u64) {
        importer.require_auth();
        Self::require_not_locked(&env, op_id);
        Self::set_locked(&env, op_id);

        let mut state: EscrowState = Self::get_escrow(&env, op_id);
        if state.importer != importer {
            panic!("only importer can fund");
        }
        if state.status != EscrowStatus::Created {
            panic!("escrow already funded or closed");
        }

        let token_client = token::Client::new(&env, &state.token);
        token_client.transfer(
            &importer,
            &env.current_contract_address(),
            &state.total_amount,
        );

        state.status = EscrowStatus::Funded;
        state.funded_at = env.ledger().timestamp();
        env.storage()
            .persistent()
            .set(&DataKey::Escrow(op_id), &state);

        Self::clear_locked(&env, op_id);
        env.events().publish((EVT_FUNDED, op_id), state.total_amount);
    }

    // ── Release payment to exporter ───────────────────────────────────────────
    /// Called after verifying that the required logistics flag is set on FlagsReceptor.
    pub fn release(env: Env, caller: Address, op_id: u64) {
        caller.require_auth();
        Self::require_not_locked(&env, op_id);
        Self::set_locked(&env, op_id);

        let mut state: EscrowState = Self::get_escrow(&env, op_id);
        if state.status != EscrowStatus::Funded {
            panic!("escrow not funded");
        }

        // Cross-contract call to verify the required flag is set
        Self::verify_flag_on_receptor(&env, op_id, &state.release_at_flag);

        let platform: Address = env
            .storage()
            .instance()
            .get(&DataKey::Platform)
            .unwrap_or_else(|| panic!("not initialized"));

        let token_client = token::Client::new(&env, &state.token);

        // Transfer platform fee (2%) to TxLogPay
        token_client.transfer(
            &env.current_contract_address(),
            &platform,
            &state.platform_fee,
        );

        // Transfer net amount to exporter
        token_client.transfer(
            &env.current_contract_address(),
            &state.exporter,
            &state.net_amount,
        );

        state.status = EscrowStatus::Released;
        state.released_at = env.ledger().timestamp();
        env.storage()
            .persistent()
            .set(&DataKey::Escrow(op_id), &state);

        Self::clear_locked(&env, op_id);
        env.events()
            .publish((EVT_RELEASED, op_id), (state.net_amount, state.platform_fee));
    }

    // ── Refund to importer (admin only, for disputes) ─────────────────────────
    pub fn refund(env: Env, admin: Address, op_id: u64) {
        admin.require_auth();
        Self::require_admin(&env, &admin);
        Self::require_not_locked(&env, op_id);
        Self::set_locked(&env, op_id);

        let mut state: EscrowState = Self::get_escrow(&env, op_id);
        if state.status != EscrowStatus::Funded {
            panic!("escrow not funded");
        }

        let token_client = token::Client::new(&env, &state.token);
        token_client.transfer(
            &env.current_contract_address(),
            &state.importer,
            &state.total_amount,
        );

        state.status = EscrowStatus::Refunded;
        env.storage()
            .persistent()
            .set(&DataKey::Escrow(op_id), &state);

        Self::clear_locked(&env, op_id);
        env.events()
            .publish((EVT_REFUNDED, op_id), state.total_amount);
    }

    // ── Dispute ───────────────────────────────────────────────────────────────
    pub fn dispute(env: Env, caller: Address, op_id: u64) {
        caller.require_auth();
        let mut state: EscrowState = Self::get_escrow(&env, op_id);
        if caller != state.importer && caller != state.exporter {
            panic!("only parties can dispute");
        }
        if state.status != EscrowStatus::Funded {
            panic!("cannot dispute");
        }
        state.status = EscrowStatus::Disputed;
        env.storage()
            .persistent()
            .set(&DataKey::Escrow(op_id), &state);
        env.events().publish((EVT_DISPUTED, op_id), caller);
    }

    // ── Queries ───────────────────────────────────────────────────────────────
    pub fn get_escrow_state(env: Env, op_id: u64) -> EscrowState {
        Self::get_escrow(&env, op_id)
    }

    pub fn get_platform_fee(env: Env, amount: i128) -> i128 {
        (amount * PLATFORM_FEE_BPS) / BPS_DIVISOR
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    fn get_escrow(env: &Env, op_id: u64) -> EscrowState {
        env.storage()
            .persistent()
            .get(&DataKey::Escrow(op_id))
            .unwrap_or_else(|| panic!("escrow not found"))
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

    // ── Reentrancy guard ──────────────────────────────────────────────────────
    fn require_not_locked(env: &Env, op_id: u64) {
        if env.storage().temporary().has(&DataKey::Locked(op_id)) {
            panic!("reentrant call detected");
        }
    }

    fn set_locked(env: &Env, op_id: u64) {
        env.storage().temporary().set(&DataKey::Locked(op_id), &true);
    }

    fn clear_locked(env: &Env, op_id: u64) {
        env.storage().temporary().remove(&DataKey::Locked(op_id));
    }

    // ── Cross-contract flag verification ──────────────────────────────────────
    fn verify_flag_on_receptor(env: &Env, op_id: u64, required: &ReleaseFlag) {
        let flags_addr: Address = env
            .storage()
            .instance()
            .get(&DataKey::FlagsContract)
            .unwrap_or_else(|| panic!("flags contract not set"));

        let flag_sym = match required {
            ReleaseFlag::Inco => symbol_short!("inco"),
            ReleaseFlag::Emba => symbol_short!("emba"),
            ReleaseFlag::Modal => symbol_short!("modal"),
            ReleaseFlag::Dese => symbol_short!("dese"),
            ReleaseFlag::Libera => symbol_short!("libera"),
        };

        let is_set: bool = env.invoke_contract(
            &flags_addr,
            &Symbol::new(env, "is_flag_set"),
            soroban_sdk::vec![
                env,
                soroban_sdk::IntoVal::<Env, soroban_sdk::Val>::into_val(&op_id, env),
                soroban_sdk::IntoVal::<Env, soroban_sdk::Val>::into_val(&flag_sym, env),
            ],
        );

        if !is_set {
            panic!("required flag not yet set — payment cannot be released");
        }
    }
}

// ─── tests ────────────────────────────────────────────────────────────────────
#[cfg(test)]
mod test {
    use super::*;
    use soroban_sdk::{
        testutils::{Address as _, Ledger},
        token::{Client as TokenClient, StellarAssetClient},
        Env,
    };

    fn setup_token(env: &Env, admin: &Address) -> Address {
        let token_id = env.register_stellar_asset_contract_v2(admin.clone());
        StellarAssetClient::new(env, &token_id.address()).set_admin(admin);
        token_id.address()
    }

    #[test]
    fn test_escrow_fee_calculation() {
        let env = Env::default();
        let contract_id = env.register_contract(None, EscrowContract);
        let client = EscrowContractClient::new(&env, &contract_id);
        // 2% of 10000 = 200
        assert_eq!(client.get_platform_fee(&10_000i128), 200i128);
        // 2% of 184500 = 3690
        assert_eq!(client.get_platform_fee(&184_500i128), 3_690i128);
    }
}
