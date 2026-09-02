import type {
  CategoryMetric,
  EarningsReport,
  EditorialMetric,
  InventoryReport,
  SalesDetailRow,
  SalesReport,
} from "../lib/types";
import { apiFetch } from "./client";

export function getSalesReport(
  start_date?: string,
  end_date?: string,
  group_by?: string
): Promise<SalesReport> {
  const params = new URLSearchParams();
  if (start_date) params.set("start_date", start_date);
  if (end_date) params.set("end_date", end_date);
  if (group_by) params.set("group_by", group_by);
  const qs = params.toString();
  return apiFetch<SalesReport>(`/reports/sales${qs ? `?${qs}` : ""}`);
}

export function getSalesDetail(
  start_date?: string,
  end_date?: string
): Promise<SalesDetailRow[]> {
  const params = new URLSearchParams();
  if (start_date) params.set("start_date", start_date);
  if (end_date) params.set("end_date", end_date);
  const qs = params.toString();
  return apiFetch<SalesDetailRow[]>(`/reports/sales-detail${qs ? `?${qs}` : ""}`);
}

export function getEarningsReport(
  start_date?: string,
  end_date?: string
): Promise<EarningsReport> {
  const params = new URLSearchParams();
  if (start_date) params.set("start_date", start_date);
  if (end_date) params.set("end_date", end_date);
  const qs = params.toString();
  return apiFetch<EarningsReport>(`/reports/earnings${qs ? `?${qs}` : ""}`);
}

export function getInventoryReport(
  category_id?: number | null
): Promise<InventoryReport> {
  return apiFetch<InventoryReport>(
    `/reports/inventory${category_id ? `?category_id=${category_id}` : ""}`
  );
}

export function getCategoryReport(): Promise<CategoryMetric[]> {
  return apiFetch<CategoryMetric[]>("/reports/category");
}

export function getEditorialReport(): Promise<EditorialMetric[]> {
  return apiFetch<EditorialMetric[]>("/reports/editorial");
}
