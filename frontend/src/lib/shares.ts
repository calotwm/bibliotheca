// Automatic per-seller percentage split derived from a book's observaciones.
// Mirrors the backend rule in backend/app/services/seller_split.py.

export interface Shares {
  juli: number;
  cande: number;
}

// Default split: blank/None means Juli. "cande" + "juli" both present -> 50/50;
// "cande" only -> 0/100 (Cande 100%); otherwise (Juli, blank, no name) -> 85/15.
export function defaultSharesFromObservaciones(
  obs: string | null | undefined
): Shares {
  const text = (obs ?? "").toLowerCase();
  const hasCande = text.includes("cande");
  const hasJuli = text.includes("juli");
  if (hasCande && hasJuli) return { juli: 50, cande: 50 };
  if (hasCande) return { juli: 0, cande: 100 };
  return { juli: 85, cande: 15 };
}

// Display label for a sale's STORED split (the earnings source of truth).
// The sales-detail table shows this when the sale itself has no observaciones
// text, so a book sold 50/50 no longer displays as plain "Juli". 50/50 ->
// "Juli y Cande"; Cande-only -> "Cande"; Juli-only / default 85/15 -> "Juli";
// any other split shows the explicit percentages.
export function sellerLabelFromShares(
  juli: number | string | null | undefined,
  cande: number | string | null | undefined
): string {
  const j = juli == null || juli === "" ? 85 : Math.round(Number(juli));
  const c = cande == null || cande === "" ? 15 : Math.round(Number(cande));
  if (j === 50 && c === 50) return "Juli y Cande";
  if (c === 100) return "Cande";
  if (j === 100) return "Juli";
  if (j === 85 && c === 15) return "Juli";
  return `Juli ${j}% / Cande ${c}%`;
}

// Extract the HH:MM:SS time-of-day portion from an ISO datetime string so an
// edited sale keeps its original time when only the date changes.
export function timeOfDay(value: string | null | undefined): string {
  if (!value) return "00:00:00";
  const match = /T(\d{2}:\d{2}:\d{2})/.exec(value);
  return match ? match[1] : "00:00:00";
}
