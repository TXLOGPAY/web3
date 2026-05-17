import Link from "next/link";
import { Ship, Anchor, FileText, Globe, Zap, Lock } from "lucide-react";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-zinc-950">
      {/* Nav */}
      <nav className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <span className="font-bold text-white text-lg">TxLogPay</span>
        </div>
        <div className="flex items-center gap-1">
          <Link href="/platform" className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors">
            Plataforma
          </Link>
          <Link href="/importer" className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors">
            Importador
          </Link>
          <Link href="/exporter" className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors">
            Exportador
          </Link>
          <Link
            href="/operations/new"
            className="ml-2 px-4 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
          >
            Nova operação
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-24 pb-16 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-950 border border-blue-800 rounded-full text-xs text-blue-300 mb-6">
          <Zap size={12} /> Powered by Stellar Soroban
        </div>
        <h1 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
          Comércio Exterior<br />
          <span className="text-blue-400">na Blockchain</span>
        </h1>
        <p className="text-xl text-zinc-400 mb-10 max-w-2xl mx-auto">
          Escrow inteligente, rastreamento logístico on-chain e ancoragem de documentos
          via Merkle Tree — tudo conectado ao Siscomex.
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <Link
            href="/operations/new"
            className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold text-lg transition-colors"
          >
            Criar operação
          </Link>
          <Link
            href="/platform"
            className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl font-semibold text-lg transition-colors"
          >
            Ver plataforma
          </Link>
        </div>
      </section>

      {/* Logistics flow */}
      <section className="max-w-5xl mx-auto px-6 py-12">
        <h2 className="text-2xl font-bold text-white mb-8 text-center">Fluxo Logístico</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { flag: "inco", label: "Incoterm", desc: "Acordo comercial confirmado", color: "blue" },
            { flag: "emba", label: "Embarque", desc: "Carga embarcada na origem", color: "violet" },
            { flag: "modal", label: "Modal", desc: "Em trânsito pelo modal", color: "indigo" },
            { flag: "dese", label: "Desembarque", desc: "Chegada no destino", color: "cyan" },
            { flag: "libera", label: "Liberação", desc: "Alfandega liberada", color: "emerald" },
          ].map((step) => (
            <div
              key={step.flag}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-center"
            >
              <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center mx-auto mb-3">
                <span className="text-xs font-mono text-zinc-400">{step.flag}</span>
              </div>
              <p className="text-sm font-semibold text-white">{step.label}</p>
              <p className="text-xs text-zinc-500 mt-1">{step.desc}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 text-center text-xs text-zinc-600">
          Cada flag é registrada on-chain via smart contract Soroban • FlagsReceptor
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 py-12">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: <Lock size={20} />,
              title: "Escrow Soroban",
              desc: "Pagamento liberado somente quando a flag acordada é atingida. Taxa 2% TxLogPay.",
            },
            {
              icon: <FileText size={20} />,
              title: "RAG + Merkle Tree",
              desc: "Invoices processadas por LlamaIndex. Dados minerados e ancorados na blockchain via Merkle root.",
            },
            {
              icon: <Globe size={20} />,
              title: "Ancoragem Etherfuse",
              desc: "On/off-ramp fiat↔Stellar via Etherfuse. Suporte a USDC, USDT e moedas locais.",
            },
          ].map((feat) => (
            <div
              key={feat.title}
              className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 space-y-3"
            >
              <div className="w-10 h-10 rounded-lg bg-blue-950 border border-blue-800 flex items-center justify-center text-blue-400">
                {feat.icon}
              </div>
              <h3 className="font-semibold text-white">{feat.title}</h3>
              <p className="text-sm text-zinc-400">{feat.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
