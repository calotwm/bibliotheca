import { STOCK_LABELS } from "../lib/constants";

const BADGE_STYLES: Record<string, string> = {
  "In Stock": "bg-green-100 text-green-800",
  Low: "bg-amber-100 text-amber-800",
  Out: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: string }) {
  const style = BADGE_STYLES[status] ?? "bg-gray-100 text-gray-700";
  const label = STOCK_LABELS[status] ?? status;
  return (
    <span
      className={`inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-semibold ${style}`}
    >
      {label}
    </span>
  );
}