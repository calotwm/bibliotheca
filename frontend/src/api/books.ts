import type { Book, BookPayload } from "../lib/types";
import { apiFetch } from "./client";

export interface BookFilters {
  q?: string;
  title?: string;
  category_id?: number | null;
  stock_status?: string | null;
  author?: string | null;
  editorial?: string | null;
  sort_by?: string | null;
  sort_dir?: string | null;
  page?: number;
  page_size?: number;
}

export function listBooks(filters: BookFilters = {}): Promise<Book[]> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.title) params.set("title", filters.title);
  if (filters.category_id) params.set("category_id", String(filters.category_id));
  if (filters.stock_status) params.set("stock_status", filters.stock_status);
  if (filters.author) params.set("author", filters.author);
  if (filters.editorial) params.set("editorial", filters.editorial);
  if (filters.sort_by) params.set("sort_by", filters.sort_by);
  if (filters.sort_dir) params.set("sort_dir", filters.sort_dir);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  const qs = params.toString();
  return apiFetch<Book[]>(`/books${qs ? `?${qs}` : ""}`);
}

export function createBook(payload: BookPayload): Promise<Book> {
  return apiFetch<Book>("/books", { method: "POST", body: payload });
}

export function updateBook(
  id: number,
  payload: Partial<BookPayload>
): Promise<Book> {
  return apiFetch<Book>(`/books/${id}`, { method: "PUT", body: payload });
}

export function deleteBook(id: number): Promise<void> {
  return apiFetch<void>(`/books/${id}`, { method: "DELETE" });
}