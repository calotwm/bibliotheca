import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import * as reportsApi from "../api/reports";
import { DataTable } from "../components/DataTable";
import { formatARS, formatDate } from "../lib/format";
import type { Column } from "../components/DataTable";
import type {
  CategoryMetric,
  DaySummary,
  EditorialMetric,
  SalesDetailRow,
  SalesGroupSummary,
  SellerSummary,
  TopSeller,
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

const topSellerColumns: Column<TopSeller>[] = [
  { key: "title", header: "Título", render: (row) => <span className="font-medium">{row.title}</span> },
  { key: "author", header: "Autor", render: (row) => row.author },
  { key: "editorial", header: "Editorial", render: (row) => row.editorial },
  { key: "quantity_sold", header: "Unidades", render: (row) => row.quantity_sold },
  { key: "revenue", header: "Ingresos", render: (row) => <span className="font-semibold">{formatARS(row.revenue)}</span> },
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

const salesDetailColumns: Column<SalesDetailRow>[] = [
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
  { key: "seller", header: "Observaciones", render: (row) => row.seller ?? "Sin vendedor" },
  { key: "payment_method", header: "Método de pago", render: (row) => row.payment_method ?? "—" },
];

const sellerColumns: Column<SellerSummary>[] = [
  { key: "seller", header: "Vendedor", render: (row) => <span className="font-medium">{row.seller}</span> },
  { key: "sale_count", header: "Ventas", render: (row) => row.sale_count },
  { key: "shared_sale_count", header: "Compartidas", render: (row) => row.shared_sale_count },
  { key: "total_revenue", header: "Total vendido", render: (row) => <span className="font-semibold">{formatARS(row.total_revenue)}</span> },
];

function firstOfMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function todayISO(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export function Reportes() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [groupBy, setGroupBy] = useState("");
  const [detailStart, setDetailStart] = useState("");
  const [detailEnd, setDetailEnd] = useState("");
  const [sellerStart, setSellerStart] = useState(firstOfMonth);
  const [sellerEnd, setSellerEnd] = useState(todayISO);

  const salesQuery = useQuery({
    queryKey: ["reports-sales", startDate, endDate, groupBy],
    queryFn: () => reportsApi.getSalesReport(startDate || undefined, endDate || undefined, groupBy || undefined),
  });

  const salesDetailQuery = useQuery({
    queryKey: ["reports-sales-detail", detailStart, detailEnd],
    queryFn: () => reportsApi.getSalesDetail(detailStart || undefined, detailEnd || undefined),
  });

  const sellersQuery = useQuery({
    queryKey: ["reports-sellers", sellerStart, sellerEnd],
    queryFn: () => reportsApi.getSellersReport(sellerStart || undefined, sellerEnd || undefined),
  });

  const topSellersQuery = useQuery({
    queryKey: ["reports-top-sellers"],
    queryFn: () => reportsApi.getTopSellers(10),
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
        {salesDetailQuery.data && (
          <div className="mt-3">
            <DataTable
              columns={salesDetailColumns}
              rows={salesDetailQuery.data}
              emptyMessage="Sin ventas en el período seleccionado."
            />
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-bold">Top vendedores</h2>
        {topSellersQuery.isLoading && <p className="text-sm text-ink-soft">Cargando…</p>}
        {topSellersQuery.isError && (
          <p className="text-sm text-red-700">
            {topSellersQuery.error instanceof Error ? topSellersQuery.error.message : "No se pudo cargar el reporte."}
          </p>
        )}
        {topSellersQuery.data && (
          <DataTable
            columns={topSellerColumns}
            rows={topSellersQuery.data}
            getRowKey={(row) => row.book_id}
            emptyMessage="Sin ventas registradas."
          />
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-bold">Ventas por vendedor/a</h2>
        <div className="flex flex-wrap items-end gap-2">
          <label className="block">
            <span className="text-xs text-ink-soft">Desde</span>
            <input
              type="date"
              value={sellerStart}
              onChange={(event) => setSellerStart(event.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
          <label className="block">
            <span className="text-xs text-ink-soft">Hasta</span>
            <input
              type="date"
              value={sellerEnd}
              onChange={(event) => setSellerEnd(event.target.value)}
              className={`${inputClass} mt-1`}
            />
          </label>
        </div>
        <p className="mb-2 mt-2 text-xs text-ink-soft">
          Las ventas compartidas ("Cande y Julieta") se dividen 50/50 entre ambas
          vendedoras. Las ventas sin vendedor no se contabilizan.
        </p>

        {sellersQuery.isLoading && <p className="text-sm text-ink-soft">Cargando…</p>}
        {sellersQuery.isError && (
          <p className="text-sm text-red-700">
            {sellersQuery.error instanceof Error
              ? sellersQuery.error.message
              : "No se pudo cargar el reporte."}
          </p>
        )}
        {sellersQuery.data && (
          <DataTable
            columns={sellerColumns}
            rows={sellersQuery.data.sellers}
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
    </div>
  );
}