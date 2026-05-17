"use client";
import { LogisticsTimeline } from "./LogisticsTimeline";
import type { Operation, LogisticFlag } from "@/lib/api";

const FLAG_LABELS: Record<string, string> = {
  inco: "Incoterm",
  emba: "Embarque",
  modal: "Modal",
  dese: "Desembarque",
  libera: "Liberação",
};

const STATUS_COLORS: Record<string, string> = {
  created: "bg-zinc-700 text-zinc-300",
  funded: "bg-blue-900 text-blue-300",
  released: "bg-emerald-900 text-emerald-300",
  refunded: "bg-amber-900 text-amber-300",
  disputed: "bg-red-900 text-red-300",
};

const STATUS_LABELS: Record<string, string> = {
  created: "Criado",
  funded: "Em escrow",
  released: "Liberado",
  refunded: "Reembolsado",
  disputed: "Em disputa",
};

interface Props {
  operation: Operation;
  onAdvance?: (opId: number, nextFlag: LogisticFlag) => void;
  onRelease?: (opId: number) => void;
  role?: "importer" | "exporter" | "platform";
}

const NEXT_FLAG: Record<string, LogisticFlag | null> = {
  none: "inco",
  inco: "emba",
  emba: "modal",
  modal: "dese",
  dese: "libera",
  libera: null,
};

export function OperationCard({ operation, onAdvance, onRelease, role = "platform" }: Props) {
  const nextFlag = NEXT_FLAG[operation.current_flag] as LogisticFlag | null;
  const canAdvance = role === "exporter" && nextFlag && operation.escrow_status === "funded";
  const canRelease =
    operation.flags[operation.release_at_flag as LogisticFlag] &&
    operation.escrow_status === "funded";

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 space-y-4 hover:border-zinc-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono text-zinc-400">
              OP-{operation.op_id}
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                STATUS_COLORS[operation.escrow_status]
              }`}
            >
              {STATUS_LABELS[operation.escrow_status]}
            </span>
            {operation.merkle_root && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-900 text-purple-300 font-medium">
                Ancorado
              </span>
            )}
          </div>
          <p className="text-sm text-zinc-300 mt-1">
            {operation.importer.slice(0, 8)}...
            {" → "}
            {operation.exporter.slice(0, 8)}...
          </p>
        </div>

        <div className="text-right">
          <p className="text-lg font-bold text-white">
            {operation.currency}{" "}
            {operation.escrow_amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
          </p>
          <p className="text-xs text-zinc-500">
            Libera em: <span className="text-amber-400 font-medium">{FLAG_LABELS[operation.release_at_flag]}</span>
          </p>
        </div>
      </div>

      {/* Trade info */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        <div>
          <p className="text-zinc-500">Incoterm</p>
          <p className="text-zinc-200 font-mono">{operation.incoterm}</p>
        </div>
        <div>
          <p className="text-zinc-500">Invoice</p>
          <p className="text-zinc-200 font-mono">{operation.invoice_number}</p>
        </div>
        {operation.bill_of_lading && (
          <div>
            <p className="text-zinc-500">BL</p>
            <p className="text-zinc-200 font-mono">{operation.bill_of_lading}</p>
          </div>
        )}
        {operation.merkle_root && (
          <div>
            <p className="text-zinc-500">Merkle Root</p>
            <p className="text-emerald-400 font-mono text-[10px] truncate" title={operation.merkle_root}>
              {operation.merkle_root.slice(0, 16)}...
            </p>
          </div>
        )}
      </div>

      {/* Timeline */}
      <LogisticsTimeline
        flags={operation.flags}
        releaseAtFlag={operation.release_at_flag}
        currentFlag={operation.current_flag}
      />

      {/* Actions */}
      {(canAdvance || canRelease) && (
        <div className="flex gap-2 pt-2">
          {canAdvance && nextFlag && (
            <button
              onClick={() => onAdvance?.(operation.op_id, nextFlag)}
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Avançar para {FLAG_LABELS[nextFlag]}
            </button>
          )}
          {canRelease && (
            <button
              onClick={() => onRelease?.(operation.op_id)}
              className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Liberar Pagamento
            </button>
          )}
        </div>
      )}
    </div>
  );
}
