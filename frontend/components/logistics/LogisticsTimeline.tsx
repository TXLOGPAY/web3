"use client";
import { CheckCircle, Circle, Clock, Anchor, Ship, Truck, Package, FileCheck } from "lucide-react";
import type { LogisticFlag } from "@/lib/api";

interface Step {
  key: string;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const STEPS: Step[] = [
  {
    key: "criada",
    label: "Criada",
    description: "Operação registrada pelo importador",
    icon: <FileCheck size={18} />,
  },
  {
    key: "inco",
    label: "Incoterm",
    description: "Acordo Incoterm confirmado",
    icon: <FileCheck size={18} />,
  },
  {
    key: "emba",
    label: "Embarque",
    description: "Carga embarcada na origem",
    icon: <Ship size={18} />,
  },
  {
    key: "modal",
    label: "Modal",
    description: "Em trânsito pelo modal acordado",
    icon: <Truck size={18} />,
  },
  {
    key: "dese",
    label: "Desembarque",
    description: "Chegada no porto de destino",
    icon: <Anchor size={18} />,
  },
  {
    key: "libera",
    label: "Liberação",
    description: "Liberação alfandegária concluída",
    icon: <Package size={18} />,
  },
  {
    key: "pagamento",
    label: "Pagamento",
    description: "Pagamento liberado ao exportador",
    icon: <CheckCircle size={18} />,
  },
];

interface Props {
  flags: Record<string, boolean>;
  releaseAtFlag: string;
  currentFlag: string;
}

export function LogisticsTimeline({ flags, releaseAtFlag, currentFlag }: Props) {
  const getStepStatus = (stepKey: string): "completed" | "current" | "pending" => {
    if (stepKey === "criada") return "completed";
    if (stepKey === "pagamento") {
      return flags["libera"] ? "completed" : "pending";
    }
    if (flags[stepKey as LogisticFlag]) return "completed";
    if (stepKey === currentFlag) return "current";
    return "pending";
  };

  return (
    <div className="flex items-start gap-0 w-full overflow-x-auto py-2">
      {STEPS.map((step, idx) => {
        const status = getStepStatus(step.key);
        const isReleaseTrigger = step.key === releaseAtFlag;

        return (
          <div key={step.key} className="flex items-start flex-1 min-w-[80px]">
            <div className="flex flex-col items-center flex-1">
              {/* Step node */}
              <div className="relative flex flex-col items-center">
                <div
                  className={[
                    "w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all z-10",
                    status === "completed"
                      ? "bg-emerald-500 border-emerald-500 text-white"
                      : status === "current"
                      ? "bg-blue-500 border-blue-500 text-white animate-pulse"
                      : "bg-zinc-800 border-zinc-600 text-zinc-500",
                    isReleaseTrigger ? "ring-2 ring-amber-400 ring-offset-1 ring-offset-zinc-900" : "",
                  ].join(" ")}
                >
                  {status === "completed" ? (
                    <CheckCircle size={16} />
                  ) : status === "current" ? (
                    <Clock size={16} />
                  ) : (
                    step.icon
                  )}
                </div>
                {isReleaseTrigger && (
                  <span className="absolute -top-5 text-[10px] font-bold text-amber-400 whitespace-nowrap">
                    Libera aqui
                  </span>
                )}
              </div>

              {/* Label */}
              <div className="mt-2 text-center">
                <p
                  className={[
                    "text-[11px] font-semibold",
                    status === "completed"
                      ? "text-emerald-400"
                      : status === "current"
                      ? "text-blue-400"
                      : "text-zinc-500",
                  ].join(" ")}
                >
                  {step.label}
                </p>
                <p className="text-[9px] text-zinc-600 hidden md:block max-w-[80px] text-center">
                  {step.description}
                </p>
              </div>
            </div>

            {/* Connector line */}
            {idx < STEPS.length - 1 && (
              <div
                className={[
                  "h-0.5 flex-1 mt-[18px] mx-1 transition-all",
                  status === "completed" ? "bg-emerald-500" : "bg-zinc-700",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
