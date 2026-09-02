import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as reportsApi from "../api/reports";
import { updateSale } from "../api/sales";
import type { Sale, SalesDetailRow } from "../lib/types";
import { Reportes } from "./Reportes";

vi.mock("../api/reports", () => ({
  getSalesReport: vi.fn(),
  getSalesDetail: vi.fn(),
  getSellersReport: vi.fn(),
  getTopSellers: vi.fn(),
  getInventoryReport: vi.fn(),
  getCategoryReport: vi.fn(),
  getEditorialReport: vi.fn(),
}));

vi.mock("../api/sales", () => ({
  updateSale: vi.fn(),
}));

const DETAIL_ROW: SalesDetailRow = {
  sale_id: 1,
  sale_number: 1,
  date: "2026-08-29",
  title: "Rayuela",
  author: "Julio Cortázar",
  editorial: "Sudamericana",
  category: "Novela",
  unit_price: "12000.00",
  quantity: 1,
  subtotal: "12000.00",
  stock: 4,
  seller: "Cande",
  payment_method: null,
  observaciones: null,
};

const UPDATED_SALE: Sale = {
  id: 1,
  sale_number: 1,
  date: "2026-08-29T00:30:00Z",
  total: "12000.00",
  seller: "Julieta",
  payment_method: null,
  customer_name: null,
  customer_cuit: null,
  invoice_pdf_path: null,
  observaciones: null,
  created_by: 1,
  created_at: "2026-08-29T00:30:00Z",
  items: [],
};

function renderReportes() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <Reportes />
    </QueryClientProvider>
  );
}

describe("Reportes — Editar venta", () => {
  beforeEach(() => {
    vi.mocked(reportsApi.getSalesReport).mockResolvedValue({
      start_date: null,
      end_date: null,
      total_sales: 0,
      total_revenue: "0.00",
      by_day: [],
      group_by: null,
      groups: [],
    });
    vi.mocked(reportsApi.getSalesDetail).mockResolvedValue([DETAIL_ROW]);
    vi.mocked(reportsApi.getSellersReport).mockResolvedValue({
      start_date: null,
      end_date: null,
      sellers: [],
    });
    vi.mocked(reportsApi.getTopSellers).mockResolvedValue([]);
    vi.mocked(reportsApi.getInventoryReport).mockResolvedValue({
      total_books: 0,
      total_units: 0,
      stock_value: "0.00",
      status_counts: {},
      threshold: 3,
      category_id: null,
    });
    vi.mocked(reportsApi.getCategoryReport).mockResolvedValue([]);
    vi.mocked(reportsApi.getEditorialReport).mockResolvedValue([]);
    vi.mocked(updateSale).mockReset();
  });

  it("renders an Editar venta button for each detail row", async () => {
    renderReportes();
    expect(await screen.findByText("Rayuela")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Editar venta" })).toHaveLength(1);
  });

  it("opens the modal, edits the seller, saves and refetches detail and sellers", async () => {
    const user = userEvent.setup();
    vi.mocked(updateSale).mockResolvedValue(UPDATED_SALE);
    renderReportes();

    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    const initialDetailCalls = vi.mocked(reportsApi.getSalesDetail).mock.calls.length;
    const initialSellersCalls = vi.mocked(reportsApi.getSellersReport).mock.calls.length;
    await user.click(editButtons[0]);

    const dialog = screen.getByRole("dialog", { name: "Editar venta #1" });
    expect(
      within(dialog).getByRole("combobox", { name: "Vendedor" })
    ).toHaveValue("Cande");
    expect(
      within(dialog).getByRole("option", { name: "Juli" })
    ).toHaveValue("Julieta");
    expect(
      within(dialog).getByRole("option", { name: "Cande y Juli" })
    ).toHaveValue("Cande y Julieta");

    await user.selectOptions(
      within(dialog).getByRole("combobox", { name: "Vendedor" }),
      "Julieta"
    );
    await user.click(within(dialog).getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(updateSale).toHaveBeenCalledTimes(1));
    expect(updateSale).toHaveBeenCalledWith(1, {
      seller: "Julieta",
      payment_method: null,
    });

    await waitFor(() => {
      expect(
        screen.queryByRole("dialog", { name: "Editar venta #1" })
      ).not.toBeInTheDocument();
    });
    expect(screen.getByText("Se guardaron los cambios")).toBeInTheDocument();

    await waitFor(() => {
      expect(
        vi.mocked(reportsApi.getSalesDetail).mock.calls.length
      ).toBeGreaterThan(initialDetailCalls);
    });
    await waitFor(() => {
      expect(
        vi.mocked(reportsApi.getSellersReport).mock.calls.length
      ).toBeGreaterThan(initialSellersCalls);
    });
  });

  it("sends seller null when Sin vendedor is selected", async () => {
    const user = userEvent.setup();
    vi.mocked(updateSale).mockResolvedValue({ ...UPDATED_SALE, seller: null });
    renderReportes();

    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    await user.click(editButtons[0]);

    const dialog = screen.getByRole("dialog", { name: "Editar venta #1" });
    await user.selectOptions(
      within(dialog).getByRole("combobox", { name: "Vendedor" }),
      ""
    );
    await user.click(within(dialog).getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(updateSale).toHaveBeenCalledTimes(1));
    expect(updateSale).toHaveBeenCalledWith(1, {
      seller: null,
      payment_method: null,
    });
  });

  it("closes the modal on Cancelar without calling updateSale", async () => {
    const user = userEvent.setup();
    renderReportes();

    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    await user.click(editButtons[0]);

    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(
      screen.queryByRole("dialog", { name: "Editar venta #1" })
    ).not.toBeInTheDocument();
    expect(updateSale).not.toHaveBeenCalled();
  });

  it("shows Vendido por and Observaciones columns in the sales detail table", async () => {
    vi.mocked(reportsApi.getSalesDetail).mockResolvedValue([
      { ...DETAIL_ROW, observaciones: "Juli y Cande" },
    ]);
    renderReportes();

    expect(await screen.findByText("Rayuela")).toBeInTheDocument();
    expect(screen.getByText("Vendido por")).toBeInTheDocument();
    expect(screen.getByText("Observaciones")).toBeInTheDocument();
    expect(screen.getByText("Juli y Cande")).toBeInTheDocument();
  });

  it("shows Juli for a null observaciones in the sales detail table", async () => {
    renderReportes();

    expect(await screen.findByText("Rayuela")).toBeInTheDocument();
    expect(screen.getByText("Juli")).toBeInTheDocument();
  });
});
