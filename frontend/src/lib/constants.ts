export const STOCK_IN_STOCK = "In Stock";
export const STOCK_LOW = "Low";
export const STOCK_OUT = "Out";

export const STOCK_LABELS: Record<string, string> = {
  [STOCK_IN_STOCK]: "En stock",
  [STOCK_LOW]: "Stock bajo",
  [STOCK_OUT]: "Sin stock",
};

export const STOCK_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Todos los estados" },
  { value: STOCK_IN_STOCK, label: STOCK_LABELS[STOCK_IN_STOCK] },
  { value: STOCK_LOW, label: STOCK_LABELS[STOCK_LOW] },
  { value: STOCK_OUT, label: STOCK_LABELS[STOCK_OUT] },
];

export const BULK_ACTIONS: { value: string; label: string }[] = [
  { value: "stock_add", label: "Sumar stock" },
  { value: "stock_set", label: "Fijar stock" },
  { value: "price_set", label: "Fijar precio" },
  { value: "price_percent", label: "Ajustar precio (%)" },
];

export const BULK_ACTION_FIELD: Record<string, string> = {
  stock_add: "stock",
  stock_set: "stock",
  price_set: "price",
  price_percent: "price",
};