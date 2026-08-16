import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { ChangeEvent } from "react";
import * as importApi from "../api/import";
import { listCategories } from "../api/categories";
import { DataTable } from "../components/DataTable";
import { AlertIcon, CheckIcon, RefreshIcon, UploadIcon } from "../components/icons";
import { BULK_ACTIONS } from "../lib/constants";
import { formatARS } from "../lib/format";
import type { Column } from "../components/DataTable";
import type {
  BulkApplyResult,
  BulkPreview,
  BulkPreviewRow,
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
  {
    key: "is_new",
    header: "Tipo",
    render: (row) => (row.is_new ? "Nueva" : "Actualización"),
  },
];

const bulkRowColumns: Column<BulkPreviewRow>[] = [
  { key: "title", header: "Título", render: (row) => <span className="font-medium">{row.title}</span> },
  { key: "field", header: "Campo", render: (row) => row.field },
  { key: "old_value", header: "Antes", render: (row) => row.old_value },
  { key: "new_value", header: "Después", render: (row) => <span className="font-semibold">{row.new_value}</span> },
];

export function ImportarExcel() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [importResult, setImportResult] = useState<ImportApplyResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [applyBusy, setApplyBusy] = useState(false);

  const [bulkEditorial, setBulkEditorial] = useState("");
  const [bulkCategory, setBulkCategory] = useState("");
  const [bulkAction, setBulkAction] = useState("stock_add");
  const [bulkAmount, setBulkAmount] = useState("");
  const [bulkPreviewResult, setBulkPreviewResult] = useState<BulkPreview | null>(null);
  const [bulkResult, setBulkResult] = useState<BulkApplyResult | null>(null);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
  });

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

  function buildBulkPayload(): importApi.BulkPayload | null {
    if (!bulkEditorial.trim()) {
      setBulkError("Indique la editorial.");
      return null;
    }
    const amount = Number(bulkAmount);
    if (!Number.isFinite(amount)) {
      setBulkError("Ingrese un monto válido.");
      return null;
    }
    return {
      editorial: bulkEditorial.trim(),
      category_id: bulkCategory ? Number(bulkCategory) : null,
      action: bulkAction as importApi.BulkAction,
      amount,
    };
  }

  async function runBulkPreview() {
    setBulkError(null);
    setBulkResult(null);
    const payload = buildBulkPayload();
    if (!payload) return;
    setBulkBusy(true);
    try {
      setBulkPreviewResult(await importApi.bulkPreview(payload));
    } catch (err) {
      setBulkError(err instanceof Error ? err.message : "No se pudo previsualizar la actualización.");
    } finally {
      setBulkBusy(false);
    }
  }

  async function runBulkApply() {
    setBulkError(null);
    const payload = buildBulkPayload();
    if (!payload) return;
    setBulkBusy(true);
    try {
      const result = await importApi.bulkApply(payload);
      setBulkResult(result);
      invalidateCatalog();
    } catch (err) {
      setBulkError(err instanceof Error ? err.message : "No se pudo aplicar la actualización.");
    } finally {
      setBulkBusy(false);
    }
  }

  const totals = preview?.totals;
  const previewRows = (preview?.sheets ?? []).flatMap((sheet) => sheet.rows).slice(0, 50);

  const inputClass =
    "mt-1 w-full rounded-sm border border-navy/20 bg-paper px-3 py-2 text-sm outline-none focus:border-navy";

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
            className="rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
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
                  <p className="text-xs text-ink-soft">{item.label}</p>
                  <p className={`text-lg font-bold ${item.label === "Con error" && item.value > 0 ? "text-red-700" : ""}`}>
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
                className="inline-flex items-center gap-1 rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
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

      <section className="rounded-sm border border-navy/10 bg-cream p-4">
        <h2 className="flex items-center gap-2 text-lg font-bold">
          <RefreshIcon className="h-5 w-5" />
          Actualización por editorial
        </h2>
        <p className="mt-1 text-sm text-ink-soft">
          Aplique una operación de stock o precio a todos los libros de una editorial
          (opcionalmente restringida a una categoría). Revise el resultado antes de aplicar.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="block">
            <span className="text-sm font-medium">Editorial *</span>
            <input
              type="text"
              value={bulkEditorial}
              onChange={(event) => setBulkEditorial(event.target.value)}
              className={inputClass}
              placeholder="Ej.: Sudamericana"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">Categoría</span>
            <select value={bulkCategory} onChange={(event) => setBulkCategory(event.target.value)} className={inputClass}>
              <option value="">Todas</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Operación *</span>
            <select value={bulkAction} onChange={(event) => setBulkAction(event.target.value)} className={inputClass}>
              {BULK_ACTIONS.map((action) => (
                <option key={action.value} value={action.value}>
                  {action.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Monto *</span>
            <input
              type="number"
              step="any"
              value={bulkAmount}
              onChange={(event) => setBulkAmount(event.target.value)}
              className={inputClass}
              placeholder={bulkAction === "price_percent" ? "Ej.: 5" : "Ej.: 100"}
            />
          </label>
          <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={() => void runBulkPreview()}
              disabled={bulkBusy}
              className="rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
            >
              {bulkBusy ? "Procesando…" : "Previsualizar"}
            </button>
          </div>
        </div>

        {bulkError && (
          <p className="mt-3 text-sm text-red-700" role="alert">
            {bulkError}
          </p>
        )}

        {bulkPreviewResult && (
          <div className="mt-4 space-y-3">
            <p className="text-sm">
              Se verán afectados{" "}
              <span className="font-semibold">{bulkPreviewResult.affected}</span> libro(s) de{" "}
              <span className="font-semibold">{bulkPreviewResult.editorial}</span>.
            </p>
            <DataTable
              columns={bulkRowColumns}
              rows={bulkPreviewResult.rows.slice(0, 100)}
              getRowKey={(row) => row.id}
              emptyMessage="Ningún libro coincide con el filtro."
            />
            {bulkPreviewResult.rows.length > 100 && (
              <p className="text-sm text-ink-soft">
                Mostrando las primeras 100 de {bulkPreviewResult.rows.length} filas.
              </p>
            )}
            <button
              type="button"
              onClick={() => void runBulkApply()}
              disabled={bulkBusy || bulkPreviewResult.affected === 0}
              className="inline-flex items-center gap-1 rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
            >
              {bulkBusy ? "Aplicando…" : "Aplicar cambios"}
            </button>
          </div>
        )}

        {bulkResult && (
          <div className="mt-4 rounded-sm border border-green-200 bg-green-50 p-3">
            <p className="flex items-center gap-1 text-sm font-semibold text-green-800">
              <CheckIcon className="h-4 w-4" />
              Actualización aplicada
            </p>
            <p className="mt-1 text-sm text-green-700">
              {bulkResult.affected} libro(s) actualizados de {bulkResult.editorial}.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}