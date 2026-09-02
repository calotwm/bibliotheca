export function parsePrice(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === "") return 0;
  const num = typeof value === "number" ? value : Number(value);
  return Number.isFinite(num) ? num : 0;
}

const arsFormatter = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatARS(value: string | number | null | undefined): string {
  return arsFormatter.format(parsePrice(value));
}

// Matches backend date-only values (YYYY-MM-DD). Date-only strings parse as
// UTC midnight in JS, so passing them through `new Date()` shifts the day in
// timezones behind UTC (e.g. Buenos Aires shows the previous day).
const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/;

function formatDateOnly(value: string): string {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  if (DATE_ONLY_RE.test(value)) return formatDateOnly(value);
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  if (DATE_ONLY_RE.test(value)) return formatDateOnly(value);
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
}

// Observaciones fall back to "Juli" when empty (business rule: "las que no
// digan nada son adquiridas por Juli"). This is display-only; the DB value
// stays null.
export function formatObservaciones(obs: string | null | undefined): string {
  const trimmed = obs?.trim();
  return trimmed ? trimmed : "Juli";
}