import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "../api/client";
import * as reportsApi from "../api/reports";
import { updateSale } from "../api/sales";
import { DataTable } from "../components/DataTable";
import { formatARS, formatDate, formatObservaciones } from "../lib/format";
import { defaultSharesFromObservaciones, timeOfDay } from "../lib/shares";
import type { Column } from "../components/DataTable";
import type {
  CategoryMetric,
  DaySummary,
  EarningsRow,
  EditorialMetric,
  SalesDetailRow,
  SalesGroupSummary,
  SaleUpdatePayload,
} from "../lib/types";

const dayColumns: Column<DaySummary>[] = [
  { key: "date", header: "Fecha", render: (row) => formatDate(row.date) },
  { key: "sales", header: "Ventas", render: (row) => row.sales },
  { key: "revenue", header: "Ingresos", render: (row) => <span className="font-semibold">{formatARS(row.revenue)}</span> },
];

const groupColumns: Column<SalesGroupSummary>[] = [
  { key: "key", header: "Grupo", render: (row) => <span className="font-medium">{row.key}</span> },
  { key: "sales", header: "Ventas", render: (row) => row.sales },
  { key: "units", header: "Unidades", render: (row) => row.units },
  { key: "revenue", header: "Ingresos", render: (row) => <span className="font-semibold">{formatARS(row.revenue)}</span> },
];

const earningsColumns: Column<EarningsRow>[] = [
  { key: "seller", header: "Vendedora", render: (row) => <span className="font-medium">{row.seller}</span> },
  { key: "sale_count", header: "Ventas", render: (row) => row.sale_count },
  { key: "revenue", header: "Total", render: (row) => <span className="font-semibold">{formatARS(row.revenue)}</span> },
];

const categoryColumns: Column<CategoryMetric>[] = [
  { key: "category", header: "Categoría", render: (row) => <span className="font-medium">{row.category}</span> },
  { key: "sales", header: "Ventas", render: (row) => row.sales },
  { key: "units", header: "Unidades", render: (row) => row.units },
  { key: "revenue", header: "Ingresos", render: (row) => <span className="font-semibold">{formatARS(row.revenue)}</span> },
];

const editorialColumns: Column<EditorialMetric>[] = [
  { key: "editorial", header: "Editorial", render: (row) => <span className="font-medium">{row.editorial}</span> },
  { key: "sales", header: "Ventas", render: (row) => row.sales },
  { key: "units", header: "Unidades", render: (row) => row.units },
  { key: "revenue", header: "Ingresos", render: (row) => <span className="font-semibold">{formatARS(row.revenue)}</span> },
];

function salesDetailColumns(
  onEdit: (row: SalesDetailRow) => void
): Column<SalesDetailRow>[] {
  return [
    { key: "sale_number", header: "N°", render: (row) => row.sale_number },
    { key: "date", header: "Fecha", render: (row) => formatDate(row.date) },
    { key: "title", header: "Título", render: (row) => <span className="font-medium">{row.title}</span> },
    { key: "author", header: "Autor", render: (row) => row.author },
    { key: "editorial", header: "Editorial", render: (row) => row.editorial },
    { key: "category", header: "Categoría", render: (row) => row.category ?? "—" },
    { key: "unit_price", header: "Precio", render: (row) => formatARS(row.unit_price) },
    { key: "quantity", header: "Cantidad", render: (row) => row.quantity },
    { key: "subtotal", header: "Subtotal", render: (row) => formatARS(row.subtotal) },
    { key: "stock", header: "Stock", render: (row) => row.stock },
    { key: "observaciones", header: "Observaciones", render: (row) => formatObservaciones(row.observaciones) },
    { key: "payment_method", header: "Método de pago", render: (row) => row.payment_method ?? "—" },
    {
      key: "actions",
      header: "Acciones",
      render: (row) => (
        <button
          type="button"
          onClick={() => onEdit(row)}
          className="rounded-sm border border-navy/20 px-3 py-1 text-sm font-medium text-navy hover:bg-navy/5"
        >
          Editar venta
        </button>
      ),
    },
  ];
}

function firstOfMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function Reportes() {
  const queryClient = useQueryClient();
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [groupBy, setGroupBy] = useState("");
  const [detailStart, setDetailStart] = useState("");
  const [detailEnd, setDetailEnd] = useState("");
  const [earningsStart, setEarningsStart] = useState(firstOfMonth);
  const [earningsEnd, setEarningsEnd] = useState(todayISO);
  const [editingSale, setEditingSale] = useState<SalesDetailRow | null>(null);
  const [editFields, setEditFields] = useState({
    payment_method: "",
    customer_name: "",
    customer_cuit: "",
    date: "",
    juli_share: "",
    cande_share: "",
  });
  const [editError, setEditError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const editMutation = useMutation({
    mutationFn: ({
      saleId,
      payload,
    }: {
      saleId: number;
      payload: SaleUpdatePayload;
    }) => updateSale(saleId, payload),
    onSuccess: () => {
      setEditingSale(null);
      setSaved(true);
      void salesDetailQuery.refetch();
      void earningsQuery.refetch();
      void queryClient.invalidateQueries({ queryKey: ["reports-sales"] });
    },
    onError: (err: unknown) => {
      setEditError(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "No se pudieron guardar los cambios."
      );
    },
  });

  function openEditModal(row: SalesDetailRow) {
    setEditingSale(row);
    const storedJuli = row.juli_share;
    const storedCande = row.cande_share;
    const shares =
      storedJuli !== null && storedCande !== null
        ? { juli: Number(storedJuli), cande: Number(storedCande) }
        : defaultSharesFromObservaciones(row.observaciones);
    setEditFields({
      payment_method: row.payment_method ?? "",
      customer_name: "",
      customer_cuit: "",
      date: row.date ?? "",
      juli_share: String(shares.juli),
      cande_share: String(shares.cande),
    });
    setEditError(null);
    setSaved(false);
  }

  function buildEditPayload(): SaleUpdatePayload {
    // Payment and shares are always sent (pre-filled); customer fields are
    // only sent when typed, so untouched customer data is never cleared.
    const payload: SaleUpdatePayload = {
      payment_method: editFields.payment_method.trim() || null,
      juli_share: Number(editFields.juli_share),
      cande_share: Number(editFields.cande_share),
    };
    // Only send the date when the user actually changed it, so a payment/shares
    // edit never rewrites the stored instant (which would drift the BA day).
    if (editFields.date && editFields.date !== editingSale?.date) {
      payload.date = `${editFields.date}T${timeOfDay(editingSale?.sale_datetime)}`;
    }
    const customerName = editFields.customer_name.trim();
    if (customerName) payload.customer_name = customerName;
    const customerCuit = editFields.customer_cuit.trim();
    if (customerCuit) payload.customer_cuit = customerCuit;
    return payload;
  }

  function handleEditSave() {
    if (!editingSale) return;
    setEditError(null);
    const juli = Number(editFields.juli_share);
    const cande = Number(editFields.cande_share);
    if (Number.isNaN(juli) || Number.isNaN(cande) || juli + cande !== 100) {
      setEditError("Los porcentajes de Juli y Cande deben sumar 100.");
      return;
    }
    editMutation.mutate({ saleId: editingSale.sale_id, payload: buildEditPayload() });
  }

  const salesQuery = useQuery({
    queryKey: ["reports-sales", startDate, endDate, groupBy],
    queryFn: () => reportsApi.getSalesReport(startDate || undefined, endDate || undefined, groupBy || undefined),
  });

  const salesDetailQuery = useQuery({
    queryKey: ["reports-sales-detail", detailStart, detailEnd],
    queryFn: () => reportsApi.getSalesDetail(detailStart || undefined, detailEnd || undefined),
  });

  const earningsQuery = useQuery({
    queryKey: ["reports-earnings", earningsStart, earningsEnd],
    queryFn: () => reportsApi.getEarningsReport(earningsStart || undefined, earningsEnd || undefined),
  });

  const inventoryQuery = useQuery({
    queryKey: ["reports-inventory"],
    queryFn: () => reportsApi.getInventoryReport(null),
  });

  const categoryQuery = useQuery({
    queryKey: ["reports-category"],
    queryFn: reportsApi.getCategoryReport,
  });

  const editorialQuery = useQuery({
    queryKey: ["reports-editorial"],
    queryFn: reportsApi.getEditorialReport,
  });

  const inputClass =
    "min-h-11 rounded-sm border border-navy/20 bg-cream px-3 py-2 text-sm outline-none focus:border-navy";

  const statusLabels: Record<string, string> = {
    "In Stock": "En stock",
    Low: "Stock bajo",
    Out: "Sin stock",
  };

  const inventory = inventoryQuery.data;
  const statusCards = inventory
    ? Object.entries(inventory.status_counts).map(([key, count]) => ({
        label: statusLabels[key] ?? key,
        value: count,
      }))
    : [];

  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-2 text-lg font-bold">Ventas por período</h2>
        <div className="flex flex-wrap items-end gap-2">
          <label className="block">
            <span className="text-xs text-ink-soft">Desde</span>
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className="block">
            <span className="text-xs text-ink-soft">Hasta</span>
            <input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className="block">
            <span className="text-xs text-ink-soft">Agrupar por</span>
            <select
              value={groupBy}
              onChange={(event) => setGroupBy(event.target.value)}
              className={`${inputClass} mt-1`}
            >
              <option value="">Sin agrupar</option>
              <option value="category">Categoría</option>
              <option value="editorial">Editorial</option>
            </select>
          </label>
        </div>

        {salesQuery.isLoading && <p className="mt-3 text-sm text-ink-soft">Cargando…</p>}
        {salesQuery.isError && (
          <p className="mt-3 text-sm text-red-700">
            {salesQuery.error instanceof Error ? salesQuery.error.message : "No se pudo generar el reporte."}
          </p>
        )}
        {salesQuery.data && (
          <div className="mt-3 space-y-3">
            <div className="grid grid-cols-2 gap-3 md:w-96">
              <div className="rounded-sm border border-navy/10 bg-cream p-3">
                <p className="truncate text-xs text-ink-soft">Ventas</p>
                <p className="truncate text-lg font-bold">{salesQuery.data.total_sales}</p>
              </div>
              <div className="rounded-sm border border-navy/10 bg-cream p-3">
                <p className="truncate text-xs text-ink-soft">Ingresos</p>
                <p className="truncate text-lg font-bold">{formatARS(salesQuery.data.total_revenue)}</p>
              </div>
            </div>
            <DataTable
              columns={dayColumns}
              rows={salesQuery.data.by_day}
              getRowKey={(row) => row.date}
              emptyMessage="Sin ventas en el período seleccionado."
            />
            {groupBy && (
              <DataTable
                columns={groupColumns}
                rows={salesQuery.data.groups}
                getRowKey={(row) => row.key}
                emptyMessage="Sin datos para el agrupamiento seleccionado."
              />
            )}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-bold">Detalle de ventas</h2>
        <div className="flex flex-wrap items-end gap-2">
          <label className="block">
            <span className="text-xs text-ink-soft">Desde</span>
            <input
              type="date"
              value={detailStart}
              onChange={(event) => setDetailStart(event.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className="block">
            <span className="text-xs text-ink-soft">Hasta</span>
            <input
              type="date"
              value={detailEnd}
              onChange={(event) => setDetailEnd(event.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
        </div>

        {salesDetailQuery.isLoading && <p className="mt-3 text-sm text-ink-soft">Cargando…</p>}
        {salesDetailQuery.isError && (
          <p className="mt-3 text-sm text-red-700">
            {salesDetailQuery.error instanceof Error
              ? salesDetailQuery.error.message
              : "No se pudo cargar el reporte."}
          </p>
        )}
        {saved && (
          <p className="mt-3 text-sm text-green-700">Se guardaron los cambios</p>
        )}
        {salesDetailQuery.data && (
          <div className="mt-3">
            <DataTable
              columns={salesDetailColumns(openEditModal)}
              rows={salesDetailQuery.data}
              emptyMessage="Sin ventas en el período seleccionado."
            />
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-bold">Ventas por vendedora</h2>
        <div className="flex flex-wrap items-end gap-2">
          <label className="block">
            <span className="text-xs text-ink-soft">Desde</span>
            <input
              type="date"
              value={earningsStart}
              onChange={(event) => setEarningsStart(event.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className="block">
            <span className="text-xs text-ink-soft">Hasta</span>
            <input
              type="date"
              value={earningsEnd}
              onChange={(event) => setEarningsEnd(event.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
        </div>
        <p className="mb-2 mt-2 text-xs text-ink-soft">
          El reparto se calcula según quién adquirió cada libro (85/15, 100/0, 50/50).
        </p>

        {earningsQuery.isLoading && <p className="text-sm text-ink-soft">Cargando…</p>}
        {earningsQuery.isError && (
          <p className="text-sm text-red-700">
            {earningsQuery.error instanceof Error
              ? earningsQuery.error.message
              : "No se pudo cargar el reporte."}
          </p>
        )}
        {earningsQuery.data && (
          <DataTable
            columns={earningsColumns}
            rows={earningsQuery.data.rows}
            getRowKey={(row) => row.seller}
            emptyMessage="Sin ventas registradas en el período."
          />
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-bold">Estado del inventario</h2>
        {inventoryQuery.isLoading && <p className="text-sm text-ink-soft">Cargando…</p>}
        {inventoryQuery.isError && (
          <p className="text-sm text-red-700">
            {inventoryQuery.error instanceof Error ? inventoryQuery.error.message : "No se pudo cargar el reporte."}
          </p>
        )}
        {inventory && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            <div className="rounded-sm border border-navy/10 bg-cream p-3">
              <p className="truncate text-xs text-ink-soft">Libros</p>
              <p className="truncate text-lg font-bold">{inventory.total_books}</p>
            </div>
            <div className="rounded-sm border border-navy/10 bg-cream p-3">
              <p className="truncate text-xs text-ink-soft">Unidades</p>
              <p className="truncate text-lg font-bold">{inventory.total_units}</p>
            </div>
            <div className="rounded-sm border border-navy/10 bg-cream p-3">
              <p className="truncate text-xs text-ink-soft">Valor del stock</p>
              <p className="truncate text-lg font-bold">{formatARS(inventory.stock_value)}</p>
            </div>
            {statusCards.map((card) => (
              <div key={card.label} className="rounded-sm border border-navy/10 bg-cream p-3">
                <p className="truncate text-xs text-ink-soft">{card.label}</p>
                <p className="truncate text-lg font-bold">{card.value}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-bold">Ventas por categoría</h2>
        {categoryQuery.isLoading && <p className="text-sm text-ink-soft">Cargando…</p>}
        {categoryQuery.isError && (
          <p className="text-sm text-red-700">
            {categoryQuery.error instanceof Error ? categoryQuery.error.message : "No se pudo cargar el reporte."}
          </p>
        )}
        {categoryQuery.data && (
          <DataTable
            columns={categoryColumns}
            rows={categoryQuery.data}
            getRowKey={(row) => row.category_id}
            emptyMessage="Sin datos."
          />
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-bold">Ventas por editorial</h2>
        {editorialQuery.isLoading && <p className="text-sm text-ink-soft">Cargando…</p>}
        {editorialQuery.isError && (
          <p className="text-sm text-red-700">
            {editorialQuery.error instanceof Error ? editorialQuery.error.message : "No se pudo cargar el reporte."}
          </p>
        )}
        {editorialQuery.data && (
          <DataTable
            columns={editorialColumns}
            rows={editorialQuery.data}
            getRowKey={(row) => row.editorial}
            emptyMessage="Sin datos."
          />
        )}
      </section>

      {editingSale && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-navy/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-label={`Editar venta #${editingSale.sale_number}`}
        >
          <div className="w-full max-w-md rounded-sm border border-navy/10 bg-cream p-6 shadow-xl">
            <h2 className="text-lg font-bold">Editar venta #{editingSale.sale_number}</h2>
            <p className="mt-1 text-xs text-ink-soft">
              Se editan fecha, pago, datos del cliente y porcentajes. Ítems y
              total no se modifican.
            </p>
            <div className="mt-4 space-y-4">
              <label className="block">
                <span className="text-xs text-ink-soft">Fecha</span>
                <input
                  type="date"
                  value={editFields.date}
                  onChange={(event) =>
                    setEditFields({ ...editFields, date: event.target.value })
                  }
                  className={`${inputClass} mt-1`}
                />
              </label>
              <label className="block">
                <span className="text-xs text-ink-soft">Método de pago</span>
                <input
                  type="text"
                  value={editFields.payment_method}
                  onChange={(event) =>
                    setEditFields({ ...editFields, payment_method: event.target.value })
                  }
                  placeholder="Método de pago (opcional)"
                  className={`${inputClass} mt-1`}
                />
              </label>
              <label className="block">
                <span className="text-xs text-ink-soft">Cliente</span>
                <input
                  type="text"
                  value={editFields.customer_name}
                  onChange={(event) =>
                    setEditFields({ ...editFields, customer_name: event.target.value })
                  }
                  placeholder="Cliente (opcional)"
                  className={`${inputClass} mt-1`}
                />
              </label>
              <label className="block">
                <span className="text-xs text-ink-soft">CUIT</span>
                <input
                  type="text"
                  value={editFields.customer_cuit}
                  onChange={(event) =>
                    setEditFields({ ...editFields, customer_cuit: event.target.value })
                  }
                  placeholder="CUIT (opcional)"
                  className={`${inputClass} mt-1`}
                />
              </label>
              <div className="block">
                <span className="text-xs text-ink-soft">Porcentajes (Juli / Cande)</span>
                <div className="mt-1 flex items-center gap-2">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={editFields.juli_share}
                    onChange={(event) =>
                      setEditFields({ ...editFields, juli_share: event.target.value })
                    }
                    aria-label="Juli %"
                    className={`${inputClass} mt-1`}
                  />
                  <span className="text-sm text-ink-soft">/</span>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={editFields.cande_share}
                    onChange={(event) =>
                      setEditFields({ ...editFields, cande_share: event.target.value })
                    }
                    aria-label="Cande %"
                    className={`${inputClass} mt-1`}
                  />
                </div>
              </div>

              {editError && (
                <p className="text-sm text-red-700" role="alert">
                  {editError}
                </p>
              )}
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditingSale(null)}
                className="rounded-sm border border-navy/20 px-4 py-2 text-sm font-medium text-navy hover:bg-navy/5"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleEditSave}
                disabled={editMutation.isPending}
                className="rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
              >
                {editMutation.isPending ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}