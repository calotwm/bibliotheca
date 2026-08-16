import type { Supplier, SupplierPayload } from "../lib/types";
import { apiFetch } from "./client";

export function listSuppliers(): Promise<Supplier[]> {
  return apiFetch<Supplier[]>("/suppliers?page_size=200");
}

export function createSupplier(payload: SupplierPayload): Promise<Supplier> {
  return apiFetch<Supplier>("/suppliers", { method: "POST", body: payload });
}

export function updateSupplier(
  id: number,
  payload: Partial<SupplierPayload>
): Promise<Supplier> {
  return apiFetch<Supplier>(`/suppliers/${id}`, { method: "PUT", body: payload });
}

export function deleteSupplier(id: number): Promise<void> {
  return apiFetch<void>(`/suppliers/${id}`, { method: "DELETE" });
}