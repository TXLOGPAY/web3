"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { operationsApi, stellarApi, escrowApi, flagsApi, ragApi, type LogisticFlag, type InvoiceExtraction } from "@/lib/api";
import { InvoiceUpload } from "@/components/logistics/InvoiceUpload";
import { useRouter } from "next/navigation";
import { CheckCircle, AlertCircle, Loader2 } from "lucide-react";

const INCOTERMS = ["EXW","FCA","FOB","CFR","CIF","CPT","CIP","DAP","DPU","DDP"];
const FLAGS: { value: LogisticFlag; label: string }[] = [
  { value: "inco", label: "Incoterm confirmado" },
  { value: "emba", label: "Embarque" },
  { value: "modal", label: "Modal" },
  { value: "dese", label: "Desembarque" },
  { value: "libera", label: "Liberação alfandegária" },
];
const CURRENCIES = ["USD", "EUR", "BRL", "CNY", "GBP"];

interface FormState {
  incoterm: string;
  release_at_flag: LogisticFlag;
  currency: string;
  amount: string;
  invoice_number: string;
  bill_of_lading: string;
  importer_public_key: string;
  exporter_public_key: string;
}

export default function NewOperationPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [extracted, setExtracted] = useState<InvoiceExtraction | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [form, setForm] = useState<FormState>({
    incoterm: "CIF",
    release_at_flag: "dese",
    currency: "USD",
    amount: "",
    invoice_number: "",
    bill_of_lading: "",
    importer_public_key: "",
    exporter_public_key: "",
  });

  const updateForm = (key: keyof FormState, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleExtracted = (data: InvoiceExtraction) => {
    setExtracted(data);
    if (data.invoice_number) updateForm("invoice_number", data.invoice_number);
    if (data.bill_of_lading) updateForm("bill_of_lading", data.bill_of_lading);
    if (data.incoterm) updateForm("incoterm", data.incoterm);
    if (data.total_value_usd) updateForm("amount", String(data.total_value_usd));
    if (data.currency) updateForm("currency", data.currency);
  };

  const createMutation = useMutation({
    mutationFn: async () => {
      const opId = Math.floor(Math.random() * 9000) + 1000;

      // 1. Create operation record
      await operationsApi.create({
        op_id: opId,
        importer_public_key: form.importer_public_key,
        exporter_public_key: form.exporter_public_key,
        incoterm: form.incoterm,
        invoice_number: form.invoice_number,
        bill_of_lading: form.bill_of_lading,
        escrow_amount: parseFloat(form.amount),
        currency: form.currency,
        release_at_flag: form.release_at_flag,
      });

      // 2. Anchor invoice data to blockchain if extracted
      if (extracted?.merkle_root) {
        await ragApi.anchor({
          op_id: opId,
          invoice_number: extracted.invoice_number,
          bill_of_lading: extracted.bill_of_lading ?? "",
          id_incoterm: extracted.incoterm ?? form.incoterm,
          product_type: extracted.product_description ?? "General Cargo",
          total_quantity: extracted.quantity ?? 0,
          total_value_usd: extracted.total_value_usd ?? parseFloat(form.amount),
          currency: extracted.currency ?? form.currency,
          origin_country: extracted.origin_country ?? "BR",
          dest_country: extracted.dest_country ?? "DE",
          siscomex_id: extracted.siscomex_id ?? "",
          merkle_root: extracted.merkle_root,
          caller_secret: "", // set via env/session in production
        }).catch(() => {}); // non-fatal if not configured
      }

      return opId;
    },
    onSuccess: (opId) => {
      setMessage({ type: "success", text: `Operação OP-${opId} criada com sucesso!` });
      setTimeout(() => router.push("/platform"), 2000);
    },
    onError: (e) => {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Erro ao criar operação" });
    },
  });

  const createAccountMutation = useMutation({
    mutationFn: async (role: "importer" | "exporter") => {
      const { data } = await stellarApi.createAccount(role, `Demo ${role}`);
      await stellarApi.fundAccount(data.public_key);
      return data;
    },
    onSuccess: (data) => {
      if (data.role === "importer") updateForm("importer_public_key", data.public_key);
      else updateForm("exporter_public_key", data.public_key);
      setMessage({ type: "success", text: `Conta ${data.role} criada e financiada no testnet!` });
    },
  });

  return (
    <div className="max-w-2xl mx-auto px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Criar nova operação</h1>
        <p className="text-zinc-400 text-sm mt-1">Operação de escrow com rastreamento logístico on-chain</p>
      </div>

      {/* Steps */}
      <div className="flex gap-2">
        {["Dados comerciais", "Upload invoice", "Contas Stellar"].map((s, i) => (
          <button
            key={s}
            onClick={() => setStep((i + 1) as 1 | 2 | 3)}
            className={[
              "flex-1 py-2 text-xs font-medium rounded-lg transition-colors",
              step === i + 1
                ? "bg-blue-600 text-white"
                : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700",
            ].join(" ")}
          >
            {i + 1}. {s}
          </button>
        ))}
      </div>

      {/* ── Step 1: Commercial terms ── */}
      {step === 1 && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Incoterm</label>
              <select
                value={form.incoterm}
                onChange={(e) => updateForm("incoterm", e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                {INCOTERMS.map((i) => <option key={i}>{i}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Libera pagamento em</label>
              <select
                value={form.release_at_flag}
                onChange={(e) => updateForm("release_at_flag", e.target.value as LogisticFlag)}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                {FLAGS.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Moeda</label>
              <select
                value={form.currency}
                onChange={(e) => updateForm("currency", e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white"
              >
                {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Valor</label>
              <input
                type="number"
                value={form.amount}
                onChange={(e) => updateForm("amount", e.target.value)}
                placeholder="0.00"
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Nº Invoice</label>
              <input
                value={form.invoice_number}
                onChange={(e) => updateForm("invoice_number", e.target.value)}
                placeholder="INV-2024-0001"
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-400 mb-1 block">Bill of Lading</label>
              <input
                value={form.bill_of_lading}
                onChange={(e) => updateForm("bill_of_lading", e.target.value)}
                placeholder="MAEU-00000000"
                className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600"
              />
            </div>
          </div>

          {form.amount && (
            <div className="bg-amber-950/30 border border-amber-800 rounded-lg p-3 text-xs">
              <p className="text-amber-300 font-medium">Taxa da plataforma TxLogPay</p>
              <p className="text-zinc-400 mt-1">
                2% = {form.currency} {(parseFloat(form.amount || "0") * 0.02).toFixed(2)} •
                Exportador recebe: {form.currency} {(parseFloat(form.amount || "0") * 0.98).toFixed(2)}
              </p>
            </div>
          )}

          <button
            onClick={() => setStep(2)}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white py-2.5 rounded-lg font-medium transition-colors"
          >
            Próximo →
          </button>
        </div>
      )}

      {/* ── Step 2: Invoice upload ── */}
      {step === 2 && (
        <div className="space-y-4">
          <p className="text-sm text-zinc-400">
            Faça upload da fatura comercial para extração automática via RAG LlamaIndex.
            Os dados serão minerados e ancorados na blockchain via Merkle Tree.
          </p>
          <InvoiceUpload onExtracted={handleExtracted} />
          <div className="flex gap-2">
            <button
              onClick={() => setStep(1)}
              className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white py-2.5 rounded-lg font-medium transition-colors"
            >
              ← Voltar
            </button>
            <button
              onClick={() => setStep(3)}
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white py-2.5 rounded-lg font-medium transition-colors"
            >
              Próximo →
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Stellar accounts ── */}
      {step === 3 && (
        <div className="space-y-4">
          <p className="text-sm text-zinc-400">
            Configure as contas Stellar. Você pode criar novas contas e financiá-las no testnet.
          </p>

          {(["importer", "exporter"] as const).map((role) => (
            <div key={role} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-white capitalize">
                  {role === "importer" ? "Importador" : "Exportador"}
                </label>
                <button
                  onClick={() => createAccountMutation.mutate(role)}
                  disabled={createAccountMutation.isPending}
                  className="text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 px-3 py-1 rounded-lg transition-colors"
                >
                  {createAccountMutation.isPending ? <Loader2 size={12} className="animate-spin" /> : "Criar conta testnet"}
                </button>
              </div>
              <input
                value={role === "importer" ? form.importer_public_key : form.exporter_public_key}
                onChange={(e) =>
                  updateForm(
                    role === "importer" ? "importer_public_key" : "exporter_public_key",
                    e.target.value
                  )
                }
                placeholder="G... (Stellar public key)"
                className="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-zinc-300 font-mono placeholder-zinc-600"
              />
            </div>
          ))}

          {message && (
            <div
              className={[
                "flex items-center gap-2 p-3 rounded-lg text-sm",
                message.type === "success"
                  ? "bg-emerald-950/30 border border-emerald-800 text-emerald-300"
                  : "bg-red-950/30 border border-red-800 text-red-300",
              ].join(" ")}
            >
              {message.type === "success" ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
              {message.text}
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={() => setStep(2)}
              className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white py-2.5 rounded-lg font-medium transition-colors"
            >
              ← Voltar
            </button>
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !form.importer_public_key || !form.exporter_public_key}
              className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
            >
              {createMutation.isPending ? (
                <><Loader2 size={16} className="animate-spin" /> Criando...</>
              ) : (
                "Enviar para exportador"
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
