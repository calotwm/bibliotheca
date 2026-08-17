import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  getRowKey?: (row: T) => string | number;
  emptyMessage?: string;
}

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  emptyMessage = "Sin datos",
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-soft">{emptyMessage}</p>;
  }
  return (
    <div className="overflow-x-auto rounded-sm border border-navy/10 bg-cream">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-navy text-cream">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="px-3 py-2.5 font-medium">
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-navy/10">
          {rows.map((row, index) => (
            <tr key={getRowKey ? getRowKey(row) : index} className="hover:bg-navy/5">
              {columns.map((column) => (
                <td key={column.key} className={`px-3 py-2.5 ${column.className ?? ""}`}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}