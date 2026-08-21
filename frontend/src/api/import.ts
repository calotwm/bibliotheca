import type {
  BulkApplyResult,
  BulkPreview,
  ImportApplyResult,
  ImportPreview,
} from "../lib/types";
import { apiFetch } from "./client";

export type BulkAction = "stock_add" | "stock_set" | "price_set" | "price_percent";

export interface BulkPayload {
  editorial: string | null;
  author?: string | null;
  category_id?: number | null;
  action: BulkAction;
  amount: number;
}

export function uploadPreview(file: File): Promise<ImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<ImportPreview>("/import/preview", {
    method: "POST",
    isFormData: true,
    body: formData,
  });
}

export function applyImport(preview: ImportPreview): Promise<ImportApplyResult> {
  return apiFetch<ImportApplyResult>("/import/apply", {
    method: "POST",
    body: {
      token: preview.token,
      filename: preview.filename,
      sheets: preview.sheets,
    },
  });
}

export function bulkPreview(payload: BulkPayload): Promise<BulkPreview> {
  return apiFetch<BulkPreview>("/editorial-bulk-update/preview", {
    method: "POST",
    body: payload,
  });
}

export function bulkApply(payload: BulkPayload): Promise<BulkApplyResult> {
  return apiFetch<BulkApplyResult>("/editorial-bulk-update/apply", {
    method: "POST",
    body: payload,
  });
}