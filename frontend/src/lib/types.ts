export interface UserInfo {
  username: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: string;
}

export interface Category {
  id: number;
  name: string;
}

export interface Book {
  id: number;
  title: string;
  author: string;
  editorial: string;
  category_id: number;
  category_name: string | null;
  price: string;
  stock: number;
  isbn: string | null;
  genre: string | null;
  source_sheet: string | null;
  is_active: boolean;
  stock_status: string;
}

export interface BookPayload {
  title: string;
  author: string;
  editorial: string;
  category_id: number;
  price: number;
  stock: number;
  isbn?: string | null;
  genre?: string | null;
}

export interface SaleItem {
  id: number;
  book_id: number;
  book_title: string | null;
  quantity: number;
  unit_price: string;
  subtotal: string;
}

export interface Sale {
  id: number;
  sale_number: number;
  date: string;
  total: string;
  payment_method: string | null;
  customer_name: string | null;
  customer_cuit: string | null;
  invoice_pdf_path: string | null;
  created_by: number | null;
  created_at: string;
  items: SaleItem[];
}

export interface SaleListItem {
  id: number;
  sale_number: number;
  date: string;
  total: string;
  payment_method: string | null;
  customer_name: string | null;
  customer_cuit: string | null;
  created_by: number | null;
  created_at: string;
  item_count: number;
}

export interface SalePayloadItem {
  book_id: number;
  quantity: number;
}

export interface SalePayload {
  items: SalePayloadItem[];
  payment_method?: string | null;
  customer_name?: string | null;
  customer_cuit?: string | null;
}

export interface Supplier {
  id: number;
  name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  notes: string | null;
  editorials: string[];
  created_at: string;
  updated_at: string;
}

export interface SupplierPayload {
  name: string;
  contact_name?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  notes?: string | null;
  editorials?: string[];
}

export interface DaySummary {
  date: string;
  sales: number;
  revenue: string;
}

export interface SalesGroupSummary {
  key: string;
  sales: number;
  units: number;
  revenue: string;
}

export interface SalesReport {
  start_date: string | null;
  end_date: string | null;
  total_sales: number;
  total_revenue: string;
  by_day: DaySummary[];
  group_by: string | null;
  groups: SalesGroupSummary[];
}

export interface TopSeller {
  book_id: number;
  title: string;
  author: string;
  editorial: string;
  quantity_sold: number;
  revenue: string;
}

export interface InventoryReport {
  total_books: number;
  total_units: number;
  stock_value: string;
  status_counts: Record<string, number>;
  threshold: number;
  category_id: number | null;
}

export interface CategoryMetric {
  category_id: number;
  category: string;
  sales: number;
  units: number;
  revenue: string;
}

export interface EditorialMetric {
  editorial: string;
  sales: number;
  units: number;
  revenue: string;
}

export interface LowStockItem {
  book_id: number;
  title: string;
  author: string;
  editorial: string;
  stock: number;
  stock_status: string;
}

export interface RecentSale {
  id: number;
  sale_number: number;
  date: string;
  total: string;
  payment_method: string | null;
  customer_name: string | null;
  created_by: number | null;
  item_count: number;
}

export interface Dashboard {
  total_books: number;
  total_units: number;
  stock_value: string;
  today_sales: { count: number; revenue: string };
  low_stock: LowStockItem[];
  out_of_stock_count: number;
  recent_sales: RecentSale[];
}

export interface ImportRow {
  row_number: number;
  title: string;
  author: string;
  editorial: string;
  genre: string | null;
  price: string;
  stock: number;
  is_new: boolean;
}

export interface ImportSheetData {
  sheet: string;
  category: string;
  rows: ImportRow[];
}

export interface ImportSheetSummary {
  sheet: string;
  category: string | null;
  parsed: number;
  inserts: number;
  updates: number;
  skips: number;
  errors: number;
}

export interface ImportTotals {
  parsed: number;
  inserts: number;
  updates: number;
  skips: number;
  errors: number;
}

export interface ImportRowError {
  sheet: string;
  row_number: number;
  message: string;
}

export interface ImportPreview {
  token: string;
  filename: string;
  sheets: ImportSheetData[];
  summaries: ImportSheetSummary[];
  errors: ImportRowError[];
  totals: ImportTotals;
}

export interface ImportApplyResult {
  sheets: ImportSheetSummary[];
  totals: ImportTotals;
}

export interface BulkPreviewRow {
  id: number;
  title: string;
  editorial: string;
  field: string;
  old_value: string;
  new_value: string;
}

export interface BulkPreview {
  editorial: string;
  category_id: number | null;
  action: string;
  amount: string;
  affected: number;
  rows: BulkPreviewRow[];
}

export interface BulkApplyResult {
  editorial: string;
  category_id: number | null;
  action: string;
  amount: string;
  affected: number;
}