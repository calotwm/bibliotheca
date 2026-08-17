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
  SalesGroupSummary,
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

export function Reportes() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [groupBy, setGroupBy] = useState("");

  const salesQuery = useQuery({
    queryKey: ["reports-sales", startDate, endDate, groupBy],
    queryFn: () => reportsApi.getSalesReport(startDate || undefined, endDate || undefined, groupBy || undefined),
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