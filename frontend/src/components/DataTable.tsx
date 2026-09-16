import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
  sortable?: boolean;
  sortKey?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  getRowKey?: (row: T) => string | number;
  emptyMessage?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
  onSort?: (key: string) => void;
  /**
   * When true the rendered <table> uses `table-fixed`, which makes per-column
   * widths authoritative and guarantees the table never grows past its
   * container. Column widths must then be RELATIVE (e.g. `w-[20%]`): a fixed
   * rem width gives the table a hard floor, so it stops adapting when the
   * viewport narrows and the `overflow-x-auto` wrapper scrolls the columns
   * off-screen instead of reflowing them. Defaults to `false` so existing
   * consumers are unaffected.
   */
  fixedLayout?: boolean;
  /**
   * When true, body cells use `whitespace-normal break-words` so long free-
   * text content (e.g. `observaciones`) flows onto extra lines instead of
   * widening the column. Defaults to `false` to preserve today's behavior
   * for `Precios` and other consumers.
   */
  wrapText?: boolean;
  /**
   * Class controlling the table's minimum width. The historical default is
   * `min-w-[640px]`; pass a smaller floor (e.g. `min-w-[520px]`) when the
   * table must keep adapting as the viewport narrows.
   */
  minWidthClass?: string;
}

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  emptyMessage = "Sin datos",
  sortBy,
  sortDir,
  onSort,
  fixedLayout = false,
  wrapText = false,
  minWidthClass = "min-w-[640px]",
}: DataTableProps<T>) {
  if (rows.length === 0) {
    return <p className="py-6 text-center text-sm text-ink-soft">{emptyMessage}</p>;
  }
  const wrapTdClasses = wrapText ? "whitespace-normal break-words align-top " : "";
  const baseTableClass = `w-full ${minWidthClass} text-left text-sm`;
  const tableClass = fixedLayout ? `${baseTableClass} table-fixed` : baseTableClass;
  return (
    <div className="overflow-x-auto rounded-sm border border-navy/10 bg-cream">
      <table className={tableClass}>
        <thead className="bg-navy text-cream">
          <tr>
            {columns.map((column) => {
              const sortKey = column.sortKey ?? column.key;
              const active = onSort && column.sortable && sortBy === sortKey;
              return (
                <th
                  key={column.key}
                  className={`px-3 py-2.5 font-medium ${wrapText ? "align-top " : ""}${column.className ?? ""}`}
                >
                  {column.sortable && onSort ? (
                    <button
                      type="button"
                      onClick={() => onSort(sortKey)}
                      className="inline-flex items-center gap-1 text-left hover:underline"
                    >
                      {column.header}
                      <span aria-hidden="true" className="text-xs">
                        {active ? (sortDir === "asc" ? "▲" : "▼") : ""}
                      </span>
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-navy/10">
          {rows.map((row, index) => (
            <tr key={getRowKey ? getRowKey(row) : index} className="hover:bg-navy/5">
              {columns.map((column) => (
                <td key={column.key} className={`px-3 py-2.5 ${wrapTdClasses}${column.className ?? ""}`}>
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