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
  { value: STOCK_OUT, label: STOCK_LABELS[STOCK_OUT] },
];

export const SELLER_JULI = "Juli";
export const SELLER_CANDE = "Cande";
export const SELLER_JOINT = "Juli y Cande";

export const SELLER_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Todas" },
  { value: SELLER_JULI, label: SELLER_JULI },
  { value: SELLER_CANDE, label: SELLER_CANDE },
  { value: SELLER_JOINT, label: SELLER_JOINT },
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