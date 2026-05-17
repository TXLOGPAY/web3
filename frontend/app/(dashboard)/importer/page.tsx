"use client";
import { useQuery } from "@tanstack/react-query";
import { operationsApi, escrowApi, type Operation, type LogisticFlag } from "@/lib/api";
import { OperationCard } from "@/components/logistics/OperationCard";
import { DollarSign, Clock, Activity } from "lucide-react";
import Link from "next/link";

// Demo importer public key — replace with auth system
const DEMO_IMPORTER = process.env.NEXT_PUBLIC_DEMO_IMPORTER_PK || "";

export default function ImporterPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["importer-operations"],
    queryFn: () =>
      DEMO_IMPORTER
        ? operationsApi.listByImporter(DEMO_IMPORTER).then((r) => r.data)
        : operationsApi.list().then((r) => r.data),
  });

  const operations: Operation[] = data?.operations ?? [];
  const inEscrow = operations
    .filter((op) => op.escrow_status === "funded")
    .reduce((sum, op) => sum + op.escrow_amount, 0);

  const handleRelease = async (opId: number) => {
    const secret = prompt("Chave secreta do importador:");
    if (!secret) return;
    try {
      await escrowApi.release(opId, secret);
      await refetch();
    } catch (e) {
      alert("Erro ao liberar: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Suas Operações</h1>
          <p className="text-zinc-400 text-sm mt-1">
            Operações como importador
          </p>
        </div>
        <Link
          href="/operations/new"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Nova operação
        </Link>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Operações ativas", value: operations.filter((o) => o.escrow_status === "funded").length, icon: <Activity size={16} />, color: "text-blue-400" },
          { label: "Total em escrow", value: `USD ${inEscrow.toLocaleString()}`, icon: <DollarSign size={16} />, color: "text-amber-400" },
          { label: "Prazo médio", value: "14 dias", icon: <Clock size={16} />, color: "text-purple-400" },
        ].map((stat) => (
          <div key={stat.label} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className={`flex items-center gap-2 ${stat.color} mb-2`}>
              {stat.icon}
              <span className="text-xs">{stat.label}</span>
            </div>
            <p className="text-xl font-bold text-white">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Operations */}
      {isLoading ? (
        <div className="text-zinc-500">Carregando...</div>
      ) : operations.length === 0 ? (
        <div className="text-center py-12 text-zinc-500">
          <p>Nenhuma operação encontrada.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {operations.map((op) => (
            <OperationCard
              key={op.op_id}
              operation={op}
              role="importer"
              onRelease={handleRelease}
            />
          ))}
        </div>
      )}
    </div>
  );
}
