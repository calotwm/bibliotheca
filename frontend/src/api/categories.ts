import type { Category } from "../lib/types";
import { apiFetch } from "./client";

export function listCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/categories");
}