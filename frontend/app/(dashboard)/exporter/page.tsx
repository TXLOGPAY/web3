"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { operationsApi, flagsApi, escrowApi, type Operation, type LogisticFlag } from "@/lib/api";
import { OperationCard } from "@/components/logistics/OperationCard";
import { CheckCircle, Clock, Inbox } from "lucide-react";

const DEMO_EXPORTER = process.env.NEXT_PUBLIC_DEMO_EXPORTER_PK || "";

export default function ExporterPage() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["exporter-operations"],
    queryFn: () =>
      DEMO_EXPORTER
        ? operationsApi.listByExporter(DEMO_EXPORTER).then((r) => r.data)
        : operationsApi.list().then((r) => r.data),
  });

  const operations: Operation[] = data?.operations ?? [];
  const pending = operations.filter((op) => op.escrow_status === "created");
  const inProgress = operations.filter((op) => op.escrow_status === "funded");
  const completed = operations.filter((op) => op.escrow_status === "released");

  const advanceMutation = useMutation({
    mutationFn: async ({ opId, nextFlag }: { opId: number; nextFlag: LogisticFlag }) => {
      const secret = prompt(`Avançar para ${nextFlag}. Chave secreta do exportador:`);
      if (!secret) throw new Error("Cancelado");
      await flagsApi.setFlag(opId, nextFlag, secret);
      await operationsApi.updateFlag(opId, nextFlag);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["exporter-operations"] }),
    onError: (e) => alert("Erro: " + (e instanceof Error ? e.message : String(e))),
  });

  const handleAdvance = (opId: number, nextFlag: LogisticFlag) => {
    advanceMutation.mutate({ opId, nextFlag });
  };

  const tabs = [
    { label: "Aguardando aceite", count: pending.length, ops: pending, icon: <Inbox size={14} /> },
    { label: "Em andamento", count: inProgress.length, ops: inProgress, icon: <Clock size={14} /> },
    { label: "Concluídas", count: completed.length, ops: completed, icon: <CheckCircle size={14} /> },
  ];

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Operações recebidas</h1>
        <p className="text-zinc-400 text-sm mt-1">
          Aceite operações e avance as etapas logísticas para liberar os pagamentos
        </p>
      </div>

      {isLoading ? (
        <div className="text-zinc-500">Carregando...</div>
      ) : (
        <div className="space-y-8">
          {tabs.map((tab) => (
            <div key={tab.label}>
              <div className="flex items-center gap-2 mb-4">
                <span className="text-zinc-400">{tab.icon}</span>
                <h2 className="text-base font-semibold text-white">{tab.label}</h2>
                <span className="text-xs bg-zinc-800 text-zinc-400 rounded-full px-2 py-0.5">
                  {tab.count}
                </span>
              </div>
              {tab.ops.length === 0 ? (
                <div className="text-zinc-600 text-sm py-4 px-4 bg-zinc-900/50 rounded-lg">
                  Nada por aqui
                </div>
              ) : (
                <div className="space-y-4">
                  {tab.ops.map((op) => (
                    <OperationCard
                      key={op.op_id}
                      operation={op}
                      role="exporter"
                      onAdvance={handleAdvance}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
