import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
});

// ─── Types ────────────────────────────────────────────────────────────────────

export type LogisticFlag = "inco" | "emba" | "modal" | "dese" | "libera";
export type EscrowStatus = "created" | "funded" | "released" | "refunded" | "disputed";

export interface FlagsState {
  op_id: number;
  inco: boolean;
  emba: boolean;
  modal: boolean;
  dese: boolean;
  libera: boolean;
  updated_at?: number;
  setter?: string;
}

export interface Operation {
  op_id: number;
  importer: string;
  exporter: string;
  incoterm: string;
  invoice_number: string;
  bill_of_lading?: string;
  escrow_amount: number;
  currency: string;
  current_flag: string;
  release_at_flag: string;
  escrow_status: EscrowStatus;
  flags: Record<LogisticFlag, boolean>;
  merkle_root?: string;
  created_at?: string;
}

export interface PlatformStats {
  total: number;
  in_escrow: number;
  released: number;
}

export interface AccountInfo {
  public_key: string;
  secret_key: string;
  role: string;
  label: string;
  funded: boolean;
}

export interface InvoiceExtraction {
  invoice_number: string;
  bill_of_lading?: string;
  exporter?: string;
  importer?: string;
  incoterm?: string;
  product_description?: string;
  hs_code?: string;
  quantity?: number;
  unit?: string;
  unit_price_usd?: number;
  total_value_usd?: number;
  currency?: string;
  origin_country?: string;
  dest_country?: string;
  siscomex_id?: string;
  merkle_root?: string;
  merkle_leaves?: string[];
}

// ─── Operations API ───────────────────────────────────────────────────────────

export const operationsApi = {
  list: () => api.get<{ operations: Operation[]; total: number; in_escrow: number; released: number }>("/operations"),
  get: (opId: number) => api.get<Operation>(`/operations/${opId}`),
  listByImporter: (pk: string) => api.get<{ operations: Operation[] }>(`/operations/importer/${pk}`),
  listByExporter: (pk: string) => api.get<{ operations: Operation[] }>(`/operations/exporter/${pk}`),
  create: (params: {
    op_id: number;
    importer_public_key: string;
    exporter_public_key: string;
    incoterm: string;
    invoice_number: string;
    bill_of_lading: string;
    escrow_amount: number;
    currency: string;
    release_at_flag: LogisticFlag;
  }) => api.post<Operation>("/operations/", undefined, { params }),
  updateFlag: (opId: number, flag: LogisticFlag) =>
    api.patch<Operation>(`/operations/${opId}/flag`, undefined, { params: { flag } }),
  updateEscrowStatus: (opId: number, status: string) =>
    api.patch<Operation>(`/operations/${opId}/escrow-status`, undefined, { params: { status } }),
  setMerkleRoot: (opId: number, merkleRoot: string) =>
    api.patch<Operation>(`/operations/${opId}/merkle-root`, undefined, { params: { merkle_root: merkleRoot } }),
};

// ─── Flags API ────────────────────────────────────────────────────────────────

export const flagsApi = {
  setFlag: (opId: number, flag: LogisticFlag, callerSecret: string) =>
    api.post("/flags/set", { op_id: opId, flag, caller_secret: callerSecret }),
  getFlags: (opId: number) => api.get<FlagsState>(`/flags/${opId}`),
  initOperation: (opId: number, callerSecret: string) =>
    api.post(`/flags/init/${opId}`, undefined, { params: { caller_secret: callerSecret } }),
};

// ─── Escrow API ───────────────────────────────────────────────────────────────

export const escrowApi = {
  create: (data: {
    op_id: number;
    importer_public_key: string;
    exporter_public_key: string;
    token_address: string;
    total_amount: number;
    release_at_flag: LogisticFlag;
    incoterm: string;
    invoice_number: string;
    importer_secret: string;
  }) => api.post("/escrow/create", data),
  fund: (opId: number, importerSecret: string) =>
    api.post("/escrow/fund", { op_id: opId, importer_secret: importerSecret }),
  release: (opId: number, callerSecret: string) =>
    api.post("/escrow/release", { op_id: opId, caller_secret: callerSecret }),
  dispute: (opId: number, callerSecret: string) =>
    api.post(`/escrow/dispute/${opId}`, undefined, { params: { caller_secret: callerSecret } }),
  calculateFee: (amount: number) => api.get(`/escrow/fee/${amount}`),
};

// ─── Stellar API ──────────────────────────────────────────────────────────────

export const stellarApi = {
  createAccount: (role: "importer" | "exporter", label: string) =>
    api.post<AccountInfo>("/stellar/accounts", { role, label }),
  fundAccount: (publicKey: string) =>
    api.post("/stellar/accounts/fund", { public_key: publicKey }),
  getBalance: (publicKey: string) => api.get(`/stellar/accounts/${publicKey}/balance`),
  setupDemo: () => api.post("/stellar/accounts/setup-demo"),
};

// ─── RAG API ─────────────────────────────────────────────────────────────────

export const ragApi = {
  extractInvoice: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<InvoiceExtraction>("/rag/extract", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  computeMerkle: (data: Record<string, unknown>) => api.post("/rag/merkle/compute", data),
  anchor: (data: {
    op_id: number;
    invoice_number: string;
    bill_of_lading: string;
    id_incoterm: string;
    product_type: string;
    total_quantity: number;
    total_value_usd: number;
    currency: string;
    origin_country: string;
    dest_country: string;
    siscomex_id: string;
    merkle_root: string;
    caller_secret: string;
  }) => api.post("/rag/anchor", data),
};

// ─── Etherfuse API ────────────────────────────────────────────────────────────

export const etherfuseApi = {
  onboard: (data: {
    customer_email: string;
    customer_name: string;
    role: "importer" | "exporter";
    stellar_public_key: string;
  }) => api.post("/etherfuse/onboard", data),
  createOrder: (data: {
    type: "onramp" | "offramp";
    amount: number;
    currency: string;
    stellar_public_key: string;
    op_id?: number;
  }) => api.post("/etherfuse/orders", data),
  getOrder: (orderId: string) => api.get(`/etherfuse/orders/${orderId}`),
};

export default api;
