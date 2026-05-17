"use client";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { ragApi, type InvoiceExtraction } from "@/lib/api";

interface Props {
  onExtracted: (data: InvoiceExtraction) => void;
}

export function InvoiceUpload({ onExtracted }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extracted, setExtracted] = useState<InvoiceExtraction | null>(null);

  const onDrop = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;

      setLoading(true);
      setError(null);
      setExtracted(null);

      try {
        const { data } = await ragApi.extractInvoice(file);
        setExtracted(data);
        onExtracted(data);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Falha na extração";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [onExtracted]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    disabled: loading,
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={[
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
          isDragActive
            ? "border-blue-500 bg-blue-950/30"
            : "border-zinc-700 hover:border-zinc-500 bg-zinc-900/50",
          loading ? "opacity-50 cursor-not-allowed" : "",
        ].join(" ")}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          {loading ? (
            <Loader2 className="text-blue-400 animate-spin" size={32} />
          ) : (
            <Upload className="text-zinc-500" size={32} />
          )}
          <div>
            <p className="text-sm font-medium text-zinc-300">
              {loading
                ? "Processando invoice via RAG LlamaIndex..."
                : isDragActive
                ? "Solte o arquivo aqui"
                : "Arraste ou clique para fazer upload da invoice"}
            </p>
            <p className="text-xs text-zinc-500 mt-1">PDF, DOCX ou TXT • máx 20MB</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-400 bg-red-950/30 border border-red-800 rounded-lg p-3">
          <AlertCircle size={16} />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {extracted && (
        <div className="bg-zinc-900 border border-emerald-800 rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle size={16} />
            <span className="text-sm font-medium">Dados extraídos com sucesso</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            {[
              { label: "Invoice Nº", value: extracted.invoice_number },
              { label: "BL", value: extracted.bill_of_lading },
              { label: "Incoterm", value: extracted.incoterm },
              { label: "Exportador", value: extracted.exporter },
              { label: "Importador", value: extracted.importer },
              { label: "Produto", value: extracted.product_description },
              { label: "HS Code", value: extracted.hs_code },
              { label: "Quantidade", value: extracted.quantity ? `${extracted.quantity} ${extracted.unit}` : undefined },
              { label: "Valor Total", value: extracted.total_value_usd ? `${extracted.currency} ${extracted.total_value_usd?.toLocaleString()}` : undefined },
              { label: "Origem", value: extracted.origin_country },
              { label: "Destino", value: extracted.dest_country },
              { label: "Siscomex ID", value: extracted.siscomex_id },
            ]
              .filter((f) => f.value)
              .map((field) => (
                <div key={field.label}>
                  <p className="text-zinc-500">{field.label}</p>
                  <p className="text-zinc-200 font-mono truncate">{field.value}</p>
                </div>
              ))}
          </div>

          {extracted.merkle_root && (
            <div className="pt-2 border-t border-zinc-800">
              <p className="text-xs text-zinc-500">Merkle Root</p>
              <p className="text-xs text-purple-400 font-mono break-all">{extracted.merkle_root}</p>
              <p className="text-[10px] text-zinc-600 mt-1">
                {extracted.merkle_leaves?.length} folhas • pronto para ancoragem na blockchain
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
