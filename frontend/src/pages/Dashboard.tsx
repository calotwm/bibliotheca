import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getDashboard } from "../api/dashboard";
import { DataTable } from "../components/DataTable";
import { StatusBadge } from "../components/StatusBadge";
import { formatARS, formatDateTime } from "../lib/format";
import type { Column } from "../components/DataTable";
import type { LowStockItem, RecentSale } from "../lib/types";

const lowStockColumns: Column<LowStockItem>[] = [
  { key: "title", header: "Título", render: (row) => <span className="font-medium">{row.title}</span> },
  { key: "author", header: "Autor", render: (row) => row.author },
  { key: "editorial", header: "Editorial", render: (row) => row.editorial },
  { key: "stock", header: "Stock", render: (row) => <span className="font-semibold">{row.stock}</span> },
  { key: "status", header: "Estado", render: (row) => <StatusBadge status={row.stock_status} /> },
];

const recentSaleColumns: Column<RecentSale>[] = [
  { key: "sale_number", header: "N°", render: (row) => `#${row.sale_number}` },
  {
    key: "date",
    header: "Fecha",
    render: (row) => <span className="whitespace-nowrap">{formatDateTime(row.date)}</span>,
  },
  {
    key: "total",
    header: "Total",
    render: (row) => <span className="font-semibold">{formatARS(row.total)}</span>,
  },
  { key: "payment_method", header: "Pago", render: (row) => row.payment_method ?? "—" },
  { key: "item_count", header: "Ítems", render: (row) => row.item_count },
];

export function Dashboard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  if (isLoading) {
    return <p className="text-sm text-ink-soft">Cargando…</p>;
  }
  if (isError || !data) {
    return (
      <p className="text-sm text-red-700">
        {error instanceof Error ? error.message : "No se pudo cargar el tablero."}
      </p>
    );
  }

  const cards = [
    { label: "Libros activos", value: String(data.total_books) },
    { label: "Unidades en stock", value: String(data.total_units) },
    { label: "Valor de inventario", value: formatARS(data.stock_value) },
    {
      label: "Ventas de hoy",
      value: `${data.today_sales.count} · ${formatARS(data.today_sales.revenue)}`,
    },
    { label: "Sin stock", value: String(data.out_of_stock_count) },
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-sm border border-navy/10 bg-cream p-3"
          >
            <p className="text-xs text-ink-soft">{card.label}</p>
            <p className="mt-1 truncate text-lg font-bold text-navy">{card.value}</p>
          </div>
        ))}
      </div>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-bold">Stock bajo</h2>
          <Link to="/inventario?stock_status=Low" className="text-sm text-accent hover:underline">
            Ver inventario
          </Link>
        </div>
        <DataTable
          columns={lowStockColumns}
          rows={data.low_stock}
          getRowKey={(row) => row.book_id}
          emptyMessage="Sin alertas de stock bajo."
        />
      </section>

      <section>
        <h2 className="mb-2 text-lg font-bold">Ventas recientes</h2>
        <DataTable
          columns={recentSaleColumns}
          rows={data.recent_sales}
          getRowKey={(row) => row.id}
          emptyMessage="Aún no hay ventas registradas."
        />
      </section>
    </div>
  );
}