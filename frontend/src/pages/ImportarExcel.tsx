import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { ChangeEvent } from "react";
import { Link } from "react-router-dom";
import * as importApi from "../api/import";
import { DataTable } from "../components/DataTable";
import { AlertIcon, CheckIcon, UploadIcon } from "../components/icons";
import { formatARS } from "../lib/format";
import type { Column } from "../components/DataTable";
import type {
  ImportApplyResult,
  ImportPreview,
  ImportRow,
  ImportSheetSummary,
} from "../lib/types";

const summaryColumns: Column<ImportSheetSummary>[] = [
  { key: "sheet", header: "Hoja", render: (row) => <span className="font-medium">{row.sheet}</span> },
  { key: "category", header: "Categoría", render: (row) => row.category ?? "—" },
  { key: "parsed", header: "Parseadas", render: (row) => row.parsed },
  { key: "inserts", header: "Nuevas", render: (row) => row.inserts },
  { key: "updates", header: "Actualizadas", render: (row) => row.updates },
  { key: "skips", header: "Omitidas", render: (row) => row.skips },
  { key: "errors", header: "Errores", render: (row) => (row.errors > 0 ? <span className="font-semibold text-red-700">{row.errors}</span> : row.errors) },
];

const rowColumns: Column<ImportRow>[] = [
  { key: "row_number", header: "Fila", render: (row) => row.row_number },
  { key: "title", header: "Título", render: (row) => <span className="font-medium">{row.title}</span> },
  { key: "author", header: "Autor", render: (row) => row.author },
  { key: "editorial", header: "Editorial", render: (row) => row.editorial },
  { key: "price", header: "Precio", render: (row) => formatARS(row.price) },
  { key: "stock", header: "Stock", render: (row) => row.stock },
  { key: "observaciones", header: "Observaciones", render: (row) => row.observaciones ?? "—" },
  {
    key: "is_new",
    header: "Tipo",
    render: (row) => (row.is_new ? "Nueva" : "Actualización"),
  },
];

export function ImportarExcel() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [importResult, setImportResult] = useState<ImportApplyResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [applyBusy, setApplyBusy] = useState(false);

  const invalidateCatalog = () => {
    void queryClient.invalidateQueries({ queryKey: ["books"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setPreview(null);
    setImportResult(null);
    setImportError(null);
  }

  async function runPreview() {
    setImportError(null);
    setImportResult(null);
    setPreview(null);
    if (!file) {
      setImportError("Seleccione un archivo .xlsx.");
      return;
    }
    setPreviewBusy(true);
    try {
      setPreview(await importApi.uploadPreview(file));
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "No se pudo previsualizar el archivo.");
    } finally {
      setPreviewBusy(false);
    }
  }

  async function runApply() {
    setImportError(null);
    if (!preview) return;
    setApplyBusy(true);
    try {
      const result = await importApi.applyImport(preview);
      setImportResult(result);
      invalidateCatalog();
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "No se pudo aplicar la importación.");
    } finally {
      setApplyBusy(false);
    }
  }

  const totals = preview?.totals;
  const previewRows = (preview?.sheets ?? []).flatMap((sheet) => sheet.rows).slice(0, 50);

  return (
    <div className="space-y-8">
      <section className="rounded-sm border border-navy/10 bg-cream p-4">
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <UploadIcon className="h-5 w-5" />
          Importar catálogo (Excel)
        </h2>
        <p className="mt-1 text-sm text-ink-soft">
          Suba un archivo .xlsx para previsualizar los cambios antes de aplicarlos. La
          importación se aplica en una sola transacción: si hay errores, no se escribe nada.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <input
            type="file"
            accept=".xlsx,.xlsm"
            onChange={handleFileChange}
            className="block w-full max-w-md text-sm file:mr-3 file:rounded-sm file:border-0 file:bg-navy file:px-3 file:py-2 file:text-sm file:font-semibold file:text-cream hover:file:bg-navy-light"
          />
          <button
            type="button"
            onClick={() => void runPreview()}
            disabled={previewBusy || !file}
            className="min-h-10 rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
          >
            {previewBusy ? "Analizando…" : "Previsualizar"}
          </button>
        </div>

        {importError && (
          <p className="mt-3 flex items-center gap-1 text-sm text-red-700" role="alert">
            <AlertIcon className="h-4 w-4" />
            {importError}
          </p>
        )}

        {preview && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              {[
                { label: "Parseadas", value: totals?.parsed ?? 0 },
                { label: "Nuevas", value: totals?.inserts ?? 0 },
                { label: "Actualizadas", value: totals?.updates ?? 0 },
                { label: "Omitidas", value: totals?.skips ?? 0 },
                { label: "Con error", value: totals?.errors ?? 0 },
              ].map((item) => (
                <div key={item.label} className="rounded-sm border border-navy/10 bg-paper p-3">
                  <p className="truncate text-xs text-ink-soft">{item.label}</p>
                  <p className={`truncate text-lg font-bold ${item.label === "Con error" && item.value > 0 ? "text-red-700" : ""}`}>
                    {item.value}
                  </p>
                </div>
              ))}
            </div>

            <DataTable
              columns={summaryColumns}
              rows={preview.summaries}
              getRowKey={(row) => row.sheet}
              emptyMessage="Sin hojas procesadas."
            />

            {(preview.errors ?? []).length > 0 && (
              <div className="rounded-sm border border-red-200 bg-red-50 p-3">
                <p className="text-sm font-semibold text-red-800">
                  {preview.errors.length} fila(s) con errores:
                </p>
                <ul className="mt-1 list-inside list-disc text-sm text-red-700">
                  {preview.errors.slice(0, 20).map((err) => (
                    <li key={`${err.sheet}-${err.row_number}`}>
                      {err.sheet} · fila {err.row_number}: {err.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {previewRows.length > 0 && (
              <div>
                <p className="mb-1 text-sm text-ink-soft">Primeras {previewRows.length} filas:</p>
                <DataTable
                  columns={rowColumns}
                  rows={previewRows}
                  getRowKey={(row) => `${row.row_number}`}
                />
              </div>
            )}

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => void runApply()}
                disabled={applyBusy}
                className="inline-flex min-h-10 items-center gap-1 rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
              >
                {applyBusy ? "Aplicando…" : "Aplicar importación"}
              </button>
            </div>
          </div>
        )}

        {importResult && (
          <div className="mt-4 rounded-sm border border-green-200 bg-green-50 p-3">
            <p className="flex items-center gap-1 text-sm font-semibold text-green-800">
              <CheckIcon className="h-4 w-4" />
              Importación aplicada
            </p>
            <p className="mt-1 text-sm text-green-700">
              {importResult.totals.inserts} nuevas · {importResult.totals.updates} actualizadas ·{" "}
              {importResult.totals.skips} omitidas · {importResult.totals.errors} con error.
            </p>
          </div>
        )}
      </section>

      <p className="text-sm text-ink-soft">
        ¿Ajustar precios por editorial?{" "}
        <Link to="/precios" className="font-semibold text-accent hover:underline">
          Ir a la sección Precios
        </Link>
        .
      </p>
    </div>
  );
}