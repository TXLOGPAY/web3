"use client";
import { useQuery } from "@tanstack/react-query";
import { operationsApi, type Operation } from "@/lib/api";
import { OperationCard } from "@/components/logistics/OperationCard";
import { TrendingUp, DollarSign, Users, Activity } from "lucide-react";
import Link from "next/link";

export default function PlatformPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["operations"],
    queryFn: () => operationsApi.list().then((r) => r.data),
  });

  const stats = [
    {
      label: "Operações",
      value: data?.total ?? 0,
      icon: <Activity size={16} />,
      color: "text-blue-400",
    },
    {
      label: "Em escrow",
      value: `USD ${(data?.in_escrow ?? 0).toLocaleString()}`,
      icon: <DollarSign size={16} />,
      color: "text-amber-400",
    },
    {
      label: "Liberadas",
      value: `USD ${(data?.released ?? 0).toLocaleString()}`,
      icon: <TrendingUp size={16} />,
      color: "text-emerald-400",
    },
    {
      label: "Contrapartes",
      value: new Set(
        (data?.operations ?? []).flatMap((op: Operation) => [op.importer, op.exporter])
      ).size,
      icon: <Users size={16} />,
      color: "text-purple-400",
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Visão Consolidada</h1>
          <p className="text-zinc-400 text-sm mt-1">
            Todas as operações de comércio exterior da plataforma
          </p>
        </div>
        <Link
          href="/operations/new"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Nova operação
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-zinc-900 border border-zinc-800 rounded-xl p-4"
          >
            <div className={`flex items-center gap-2 ${stat.color} mb-2`}>
              {stat.icon}
              <span className="text-xs font-medium">{stat.label}</span>
            </div>
            <p className="text-xl font-bold text-white">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Operations table */}
      <div>
        <h2 className="text-lg font-semibold text-white mb-4">Operações em curso</h2>
        {isLoading ? (
          <div className="text-zinc-500 text-sm">Carregando...</div>
        ) : data?.operations.length === 0 ? (
          <div className="text-center py-12 text-zinc-500">
            <p>Nenhuma operação encontrada.</p>
            <Link href="/operations/new" className="text-blue-400 hover:underline text-sm mt-2 inline-block">
              Criar a primeira operação
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {data?.operations.map((op: Operation) => (
              <OperationCard key={op.op_id} operation={op} role="platform" />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
