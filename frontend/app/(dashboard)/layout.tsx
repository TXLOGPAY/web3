import Link from "next/link";
import { Zap } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-zinc-950">
      <nav className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between sticky top-0 bg-zinc-950/95 backdrop-blur z-50">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <span className="font-bold text-white text-lg">TxLogPay</span>
        </Link>
        <div className="flex items-center gap-1">
          <Link href="/operations/new" className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors">
            Nova operação
          </Link>
          <Link href="/importer" className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors">
            Importador
          </Link>
          <Link href="/exporter" className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors">
            Exportador
          </Link>
          <Link href="/platform" className="px-3 py-1.5 text-sm text-zinc-400 hover:text-white transition-colors">
            Plataforma
          </Link>
        </div>
      </nav>
      <main className="py-6">{children}</main>
    </div>
  );
}
