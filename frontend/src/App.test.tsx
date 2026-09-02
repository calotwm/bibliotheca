import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as booksApi from "./api/books";
import * as categoriesApi from "./api/categories";
import * as dashboardApi from "./api/dashboard";
import * as reportsApi from "./api/reports";
import * as salesApi from "./api/sales";
import * as suppliersApi from "./api/suppliers";
import App from "./App";
import { AuthProvider } from "./auth/AuthContext";

vi.mock("./api/books", () => ({
  listBooks: vi.fn(),
  createBook: vi.fn(),
  updateBook: vi.fn(),
  deleteBook: vi.fn(),
}));

vi.mock("./api/categories", () => ({
  listCategories: vi.fn(),
}));

vi.mock("./api/dashboard", () => ({
  getDashboard: vi.fn(),
}));

vi.mock("./api/import", () => ({
  uploadPreview: vi.fn(),
  applyImport: vi.fn(),
  bulkPreview: vi.fn(),
  bulkApply: vi.fn(),
}));

vi.mock("./api/reports", () => ({
  getSalesReport: vi.fn(),
  getEarningsReport: vi.fn(),
  getInventoryReport: vi.fn(),
  getCategoryReport: vi.fn(),
  getEditorialReport: vi.fn(),
}));

vi.mock("./api/sales", () => ({
  createSale: vi.fn(),
  listSales: vi.fn(),
  fetchInvoice: vi.fn(),
}));

vi.mock("./api/suppliers", () => ({
  listSuppliers: vi.fn(),
  createSupplier: vi.fn(),
  updateSupplier: vi.fn(),
  deleteSupplier: vi.fn(),
}));

function renderApp(initialEntries: string[]) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("App routing", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("bibliotheca_token", "test-token");
    localStorage.setItem("bibliotheca_user", JSON.stringify({ username: "admin", role: "admin" }));

    vi.mocked(dashboardApi.getDashboard).mockResolvedValue({
      total_books: 3,
      total_units: 12,
      stock_value: "100.00",
      today_sales: { count: 1, revenue: "10.00" },
      low_stock: [],
      out_of_stock_count: 0,
      recent_sales: [],
    });
    vi.mocked(booksApi.listBooks).mockResolvedValue([]);
    vi.mocked(categoriesApi.listCategories).mockResolvedValue([]);
    vi.mocked(salesApi.listSales).mockResolvedValue([]);
    vi.mocked(suppliersApi.listSuppliers).mockResolvedValue([]);
    vi.mocked(reportsApi.getSalesReport).mockResolvedValue({
      start_date: null,
      end_date: null,
      total_sales: 0,
      total_revenue: "0.00",
      by_day: [],
      group_by: null,
      groups: [],
    });
    vi.mocked(reportsApi.getEarningsReport).mockResolvedValue({
      start_date: null,
      end_date: null,
      rows: [],
    });
    vi.mocked(reportsApi.getInventoryReport).mockResolvedValue({
      total_books: 0,
      total_units: 0,
      stock_value: "0.00",
      status_counts: {},
      threshold: 5,
      category_id: null,
    });
    vi.mocked(reportsApi.getCategoryReport).mockResolvedValue([]);
    vi.mocked(reportsApi.getEditorialReport).mockResolvedValue([]);
  });

  it("redirects unauthenticated users to /login", async () => {
    localStorage.clear();
    renderApp(["/"]);
    expect(
      await screen.findByRole("img", { name: "Ojo de Poeta - Libros" })
    ).toBeInTheDocument();
  });

  it("renders the dashboard for an authenticated user", async () => {
    renderApp(["/"]);
    expect(await screen.findByText("Libros activos")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Inicio" })
    ).toBeInTheDocument();
  });

  it("renders every module route from the sidebar", async () => {
    const user = userEvent.setup();
    renderApp(["/"]);
    expect(await screen.findByText("Libros activos")).toBeInTheDocument();

    await user.click(screen.getByText("Inventario"));
    expect(await screen.findByRole("heading", { name: "Inventario" })).toBeInTheDocument();

    await user.click(screen.getByText("Ventas"));
    expect(await screen.findByRole("heading", { name: "Ventas (POS)" })).toBeInTheDocument();

    await user.click(screen.getByText("Proveedores"));
    expect(await screen.findByRole("heading", { name: "Proveedores" })).toBeInTheDocument();

    await user.click(screen.getByText("Reportes"));
    expect(await screen.findByRole("heading", { name: "Reportes" })).toBeInTheDocument();

    await user.click(screen.getByText("Importar Excel"));
    expect(await screen.findByRole("heading", { name: "Importar Excel" })).toBeInTheDocument();

    await user.click(screen.getByText("Precios"));
    expect(await screen.findByRole("heading", { name: "Precios" })).toBeInTheDocument();
  });
});