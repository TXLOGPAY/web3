//! FlagsReceptor — recebe as bandeiras logísticas do fluxo de comércio exterior.
//! Flags: inco | emba | modal | dese | libera
#![no_std]

use soroban_sdk::{
    contract, contractimpl, contracttype, symbol_short, Address, Env, Map, Symbol,
};

// ─── storage keys ──────────────────────────────────────────────────────────────
#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    OperationFlags(u64), // op_id → FlagsState
    AuthorizedSetter,
}

// ─── flag state per operation ───────────────────────────────────────────────────
#[contracttype]
#[derive(Clone, Default)]
pub struct FlagsState {
    /// Acordo Incoterm confirmado
    pub inco: bool,
    /// Embarque da carga realizado
    pub emba: bool,
    /// Modal de transporte em curso
    pub modal: bool,
    /// Desembarque concluído
    pub dese: bool,
    /// Liberação alfandegária concluída
    pub libera: bool,
    /// Timestamp da última atualização
    pub updated_at: u64,
    /// Quem setou a última flag
    pub setter: Address,
}

// ─── events ────────────────────────────────────────────────────────────────────
const EVT_FLAG_SET: Symbol = symbol_short!("flag_set");
const EVT_OP_INIT: Symbol = symbol_short!("op_init");

#[contract]
pub struct FlagsReceptorContract;

#[contractimpl]
impl FlagsReceptorContract {
    // ── Init ──────────────────────────────────────────────────────────────────
    pub fn initialize(env: Env, admin: Address, authorized_setter: Address) {
        if env.storage().instance().has(&DataKey::Admin) {
            panic!("already initialized");
        }
        env.storage().instance().set(&DataKey::Admin, &admin);
        env
            .storage()
            .instance()
            .set(&DataKey::AuthorizedSetter, &authorized_setter);
    }

    // ── Create a new operation slot ───────────────────────────────────────────
    pub fn init_operation(env: Env, caller: Address, op_id: u64) {
        caller.require_auth();
        Self::require_admin_or_setter(&env, &caller);
        let key = DataKey::OperationFlags(op_id);
        if env.storage().persistent().has(&key) {
            panic!("operation already exists");
        }
        let state = FlagsState {
            inco: false,
            emba: false,
            modal: false,
            dese: false,
            libera: false,
            updated_at: env.ledger().timestamp(),
            setter: caller.clone(),
        };
        env.storage().persistent().set(&key, &state);
        env.events().publish((EVT_OP_INIT, op_id), caller);
    }

    // ── Set individual flags ───────────────────────────────────────────────────

    pub fn set_inco(env: Env, caller: Address, op_id: u64) {
        caller.require_auth();
        Self::require_admin_or_setter(&env, &caller);
        let mut state = Self::get_state(&env, op_id);
        state.inco = true;
        state.updated_at = env.ledger().timestamp();
        state.setter = caller.clone();
        env.storage()
            .persistent()
            .set(&DataKey::OperationFlags(op_id), &state);
        env.events()
            .publish((EVT_FLAG_SET, symbol_short!("inco"), op_id), &caller);
    }

    pub fn set_emba(env: Env, caller: Address, op_id: u64) {
        caller.require_auth();
        Self::require_admin_or_setter(&env, &caller);
        let mut state = Self::get_state(&env, op_id);
        if !state.inco {
            panic!("inco flag must be set first");
        }
        state.emba = true;
        state.updated_at = env.ledger().timestamp();
        state.setter = caller.clone();
        env.storage()
            .persistent()
            .set(&DataKey::OperationFlags(op_id), &state);
        env.events()
            .publish((EVT_FLAG_SET, symbol_short!("emba"), op_id), &caller);
    }

    pub fn set_modal(env: Env, caller: Address, op_id: u64) {
        caller.require_auth();
        Self::require_admin_or_setter(&env, &caller);
        let mut state = Self::get_state(&env, op_id);
        if !state.emba {
            panic!("emba flag must be set first");
        }
        state.modal = true;
        state.updated_at = env.ledger().timestamp();
        state.setter = caller.clone();
        env.storage()
            .persistent()
            .set(&DataKey::OperationFlags(op_id), &state);
        env.events()
            .publish((EVT_FLAG_SET, symbol_short!("modal"), op_id), &caller);
    }

    pub fn set_dese(env: Env, caller: Address, op_id: u64) {
        caller.require_auth();
        Self::require_admin_or_setter(&env, &caller);
        let mut state = Self::get_state(&env, op_id);
        if !state.modal {
            panic!("modal flag must be set first");
        }
        state.dese = true;
        state.updated_at = env.ledger().timestamp();
        state.setter = caller.clone();
        env.storage()
            .persistent()
            .set(&DataKey::OperationFlags(op_id), &state);
        env.events()
            .publish((EVT_FLAG_SET, symbol_short!("dese"), op_id), &caller);
    }

    pub fn set_libera(env: Env, caller: Address, op_id: u64) {
        caller.require_auth();
        Self::require_admin_or_setter(&env, &caller);
        let mut state = Self::get_state(&env, op_id);
        if !state.dese {
            panic!("dese flag must be set first");
        }
        state.libera = true;
        state.updated_at = env.ledger().timestamp();
        state.setter = caller.clone();
        env.storage()
            .persistent()
            .set(&DataKey::OperationFlags(op_id), &state);
        env.events()
            .publish((EVT_FLAG_SET, symbol_short!("libera"), op_id), &caller);
    }

    // ── Queries ────────────────────────────────────────────────────────────────

    pub fn get_flags(env: Env, op_id: u64) -> FlagsState {
        Self::get_state(&env, op_id)
    }

    pub fn is_flag_set(env: Env, op_id: u64, flag: Symbol) -> bool {
        let state = Self::get_state(&env, op_id);
        match flag {
            f if f == symbol_short!("inco") => state.inco,
            f if f == symbol_short!("emba") => state.emba,
            f if f == symbol_short!("modal") => state.modal,
            f if f == symbol_short!("dese") => state.dese,
            f if f == symbol_short!("libera") => state.libera,
            _ => panic!("unknown flag"),
        }
    }

    pub fn update_authorized_setter(env: Env, admin: Address, new_setter: Address) {
        admin.require_auth();
        Self::require_admin(&env, &admin);
        env.storage()
            .instance()
            .set(&DataKey::AuthorizedSetter, &new_setter);
    }

    // ── Internal helpers ───────────────────────────────────────────────────────

    fn get_state(env: &Env, op_id: u64) -> FlagsState {
        env.storage()
            .persistent()
            .get(&DataKey::OperationFlags(op_id))
            .unwrap_or_else(|| panic!("operation not found"))
    }

    fn require_admin_or_setter(env: &Env, caller: &Address) {
        let admin: Address = env
            .storage()
            .instance()
            .get(&DataKey::Admin)
            .unwrap_or_else(|| panic!("not initialized"));
        let setter: Address = env
            .storage()
            .instance()
            .get(&DataKey::AuthorizedSetter)
            .unwrap_or_else(|| panic!("not initialized"));
        if caller != &admin && caller != &setter {
            panic!("unauthorized");
        }
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

// ─── tests ─────────────────────────────────────────────────────────────────────
#[cfg(test)]
mod test {
    use super::*;
    use soroban_sdk::testutils::{Address as _, Ledger};
    use soroban_sdk::Env;

    #[test]
    fn test_full_flow() {
        let env = Env::default();
        env.mock_all_auths();
        let contract_id = env.register_contract(None, FlagsReceptorContract);
        let client = FlagsReceptorContractClient::new(&env, &contract_id);

        let admin = Address::generate(&env);
        let setter = Address::generate(&env);

        client.initialize(&admin, &setter);
        client.init_operation(&setter, &1u64);

        client.set_inco(&setter, &1u64);
        client.set_emba(&setter, &1u64);
        client.set_modal(&setter, &1u64);
        client.set_dese(&setter, &1u64);
        client.set_libera(&setter, &1u64);

        let flags = client.get_flags(&1u64);
        assert!(flags.inco);
        assert!(flags.emba);
        assert!(flags.modal);
        assert!(flags.dese);
        assert!(flags.libera);
    }
}
