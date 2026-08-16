import type { Sale, SaleListItem, SalePayload } from "../lib/types";
import { apiFetch } from "./client";

export interface SaleFilters {
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export function createSale(payload: SalePayload): Promise<Sale> {
  return apiFetch<Sale>("/sales", { method: "POST", body: payload });
}

export function listSales(filters: SaleFilters = {}): Promise<SaleListItem[]> {
  const params = new URLSearchParams();
  if (filters.start_date) params.set("start_date", filters.start_date);
  if (filters.end_date) params.set("end_date", filters.end_date);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  const qs = params.toString();
  return apiFetch<SaleListItem[]>(`/sales${qs ? `?${qs}` : ""}`);
}

export async function fetchInvoice(saleId: number): Promise<Blob> {
  return apiFetch<Blob>(`/sales/${saleId}/invoice.pdf`, { raw: true });
}