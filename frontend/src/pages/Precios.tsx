import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as importApi from "../api/import";
import * as booksApi from "../api/books";
import { listCategories } from "../api/categories";
import { useAuth } from "../auth/AuthContext";
import { DataTable } from "../components/DataTable";
import { AlertIcon, CheckIcon } from "../components/icons";
import { formatARS } from "../lib/format";
import type { Column } from "../components/DataTable";
import type { BulkApplyResult, BulkPreview, BulkPreviewRow } from "../lib/types";

type PriceOperation = "price_set" | "raise_percent" | "lower_percent";

const OPERATIONS: { value: PriceOperation; label: string; placeholder: string }[] = [
  { value: "price_set", label: "Fijar precio", placeholder: "Ej.: 25000" },
  { value: "raise_percent", label: "Subir porcentaje", placeholder: "Ej.: 10" },
  { value: "lower_percent", label: "Bajar porcentaje", placeholder: "Ej.: 10" },
];

const previewColumns: Column<BulkPreviewRow>[] = [
  { key: "title", header: "Título", render: (row) => <span className="font-medium">{row.title}</span> },
  { key: "editorial", header: "Editorial", render: (row) => row.editorial },
  { key: "old_value", header: "Precio actual", render: (row) => formatARS(row.old_value) },
  {
    key: "new_value",
    header: "Precio nuevo",
    render: (row) => <span className="font-semibold">{formatARS(row.new_value)}</span>,
  },
];

const inputClass =
  "min-h-11 w-full rounded-sm border border-navy/20 bg-paper px-3 py-2 text-sm outline-none focus:border-navy disabled:opacity-50";

export function Precios() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [editorial, setEditorial] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [operation, setOperation] = useState<PriceOperation>("price_set");
  const [amount, setAmount] = useState("");
  const [preview, setPreview] = useState<BulkPreview | null>(null);
  const [result, setResult] = useState<BulkApplyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
  });

  const { data: books = [] } = useQuery({
    queryKey: ["books", "editorials"],
    queryFn: () => booksApi.listBooks({ page_size: 300 }),
  });

  const editorials = useMemo(() => {
    const unique = new Set<string>();
    for (const book of books) {
      const name = book.editorial?.trim();
      if (name) unique.add(name);
    }
    return Array.from(unique).sort((a, b) => a.localeCompare(b));
  }, [books]);

  const selectedOperation =
    OPERATIONS.find((item) => item.value === operation) ?? OPERATIONS[0];

  function buildPayload(): importApi.BulkPayload | null {
    if (!editorial.trim()) {
      setError("Indique la editorial.");
      return null;
    }
    const parsedAmount = Number(amount);
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setError("Ingrese un monto mayor a cero.");
      return null;
    }
    let action: importApi.BulkAction;
    let finalAmount: number;
    if (operation === "price_set") {
      action = "price_set";
      finalAmount = parsedAmount;
    } else {
      action = "price_percent";
      finalAmount = operation === "raise_percent" ? parsedAmount : -parsedAmount;
    }
    return {
      editorial: editorial.trim(),
      category_id: categoryId ? Number(categoryId) : null,
      action,
      amount: finalAmount,
    };
  }

  async function runPreview() {
    setError(null);
    setResult(null);
    const payload = buildPayload();
    if (!payload) return;
    setBusy(true);
    try {
      setPreview(await importApi.bulkPreview(payload));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No se pudo previsualizar la actualización."
      );
    } finally {
      setBusy(false);
    }
  }

  async function runApply() {
    setError(null);
    const payload = buildPayload();
    if (!payload) return;
    setBusy(true);
    try {
      const applied = await importApi.bulkApply(payload);
      setResult(applied);
      void queryClient.invalidateQueries({ queryKey: ["books"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "No se pudo aplicar la actualización."
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="rounded-sm border border-navy/10 bg-cream p-4">
        <h2 className="text-lg font-bold">Ajuste de precios por editorial</h2>
        <p className="mt-1 text-sm text-ink-soft">
          Fije un precio en ARS o aplique un porcentaje (subir o bajar) a todos
          los libros activos de una editorial, opcionalmente restringida a una
          categoría. Revise el resultado antes de aplicar.
        </p>

        {!isAdmin && (
          <p className="mt-3 flex items-center gap-1 rounded-sm border border-navy/10 bg-paper p-3 text-sm text-ink-soft">
            <AlertIcon className="h-4 w-4 shrink-0" />
            Solo administradores pueden modificar precios.
          </p>
        )}

        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="block">
            <span className="text-sm font-medium">Editorial *</span>
            <input
              type="text"
              value={editorial}
              onChange={(event) => setEditorial(event.target.value)}
              disabled={!isAdmin}
              className={inputClass}
              placeholder="Ej.: Sudamericana"
              list="editoriales"
            />
            <datalist id="editoriales">
              {editorials.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Categoría</span>
            <select
              value={categoryId}
              onChange={(event) => setCategoryId(event.target.value)}
              disabled={!isAdmin}
              className={inputClass}
            >
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
            <select
              value={operation}
              onChange={(event) =>
                setOperation(event.target.value as PriceOperation)
              }
              disabled={!isAdmin}
              className={inputClass}
            >
              {OPERATIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm font-medium">Monto *</span>
            <input
              type="number"
              step="any"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              disabled={!isAdmin}
              className={inputClass}
              placeholder={selectedOperation.placeholder}
            />
          </label>
          <div className="flex items-end">
            <button
              type="button"
              onClick={() => void runPreview()}
              disabled={busy || !isAdmin}
              className="min-h-11 w-full rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
            >
              {busy ? "Procesando…" : "Previsualizar"}
            </button>
          </div>
        </div>

        {error && (
          <p className="mt-3 flex items-center gap-1 text-sm text-red-700" role="alert">
            <AlertIcon className="h-4 w-4 shrink-0" />
            {error}
          </p>
        )}

        {preview && (
          <div className="mt-4 space-y-3">
            {preview.affected === 0 ? (
              <p className="text-sm text-ink-soft">
                No hay libros activos de esa editorial.
              </p>
            ) : (
              <>
                <p className="text-sm">
                  Se verán afectados{" "}
                  <span className="font-semibold">{preview.affected}</span>{" "}
                  libro(s).
                </p>
                <DataTable
                  columns={previewColumns}
                  rows={preview.rows.slice(0, 100)}
                  getRowKey={(row) => row.id}
                  emptyMessage="Ningún libro coincide con el filtro."
                />
                {preview.rows.length > 100 && (
                  <p className="text-sm text-ink-soft">
                    Mostrando las primeras 100 de {preview.rows.length} filas.
                  </p>
                )}
              </>
            )}
            {isAdmin && (
              <button
                type="button"
                onClick={() => void runApply()}
                disabled={busy || preview.affected === 0}
                className="inline-flex min-h-11 items-center gap-1 rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
              >
                {busy ? "Aplicando…" : "Aplicar cambios"}
              </button>
            )}
          </div>
        )}

        {result && (
          <div className="mt-4 rounded-sm border border-green-200 bg-green-50 p-3">
            <p className="flex items-center gap-1 text-sm font-semibold text-green-800">
              <CheckIcon className="h-4 w-4" />
              {result.affected} libro(s) actualizado(s).
            </p>
          </div>
        )}
      </section>
    </div>
  );
}