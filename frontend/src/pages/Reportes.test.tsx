import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as reportsApi from "../api/reports";
import { updateSale } from "../api/sales";
import type { Sale, SalesDetailRow } from "../lib/types";
import { Reportes } from "./Reportes";

vi.mock("../api/reports", () => ({
  getSalesReport: vi.fn(),
  getSalesDetail: vi.fn(),
  getEarningsReport: vi.fn(),
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
  // Backend-consistent pair: stored UTC 2026-08-29T00:30:00 == BA 2026-08-28T21:30:00.
  date: "2026-08-28",
  sale_datetime: "2026-08-28T21:30:00",
  title: "Rayuela",
  author: "Julio Cortázar",
  editorial: "Sudamericana",
  category: "Novela",
  unit_price: "12000.00",
  quantity: 1,
  subtotal: "12000.00",
  stock: 4,
  payment_method: null,
  observaciones: null,
  juli_share: null,
  cande_share: null,
};

const UPDATED_SALE: Sale = {
  id: 1,
  sale_number: 1,
  date: "2026-08-29T00:30:00Z",
  total: "12000.00",
  juli_share: "85.00",
  cande_share: "15.00",
  payment_method: "Efectivo",
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

describe("Reportes", () => {
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

  it("opens the modal, edits the payment, saves and refetches detail and earnings", async () => {
    const user = userEvent.setup();
    vi.mocked(updateSale).mockResolvedValue(UPDATED_SALE);
    renderReportes();

    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    const initialDetailCalls = vi.mocked(reportsApi.getSalesDetail).mock.calls.length;
    const initialEarningsCalls = vi.mocked(reportsApi.getEarningsReport).mock.calls.length;
    await user.click(editButtons[0]);

    const dialog = screen.getByRole("dialog", { name: "Editar venta #1" });
    await user.type(
      within(dialog).getByLabelText("Método de pago"),
      "Efectivo"
    );
    await user.click(within(dialog).getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(updateSale).toHaveBeenCalledTimes(1));
    // The date input is untouched, so `date` must NOT be sent (avoids silently
    // rewriting the stored instant).
    expect(updateSale).toHaveBeenCalledWith(1, {
      payment_method: "Efectivo",
      juli_share: 85,
      cande_share: 15,
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
        vi.mocked(reportsApi.getEarningsReport).mock.calls.length
      ).toBeGreaterThan(initialEarningsCalls);
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

  it("prefills stored shares in the edit modal", async () => {
    vi.mocked(reportsApi.getSalesDetail).mockResolvedValue([
      { ...DETAIL_ROW, juli_share: "50.00", cande_share: "50.00" },
    ]);
    renderReportes();

    const user = userEvent.setup();
    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    await user.click(editButtons[0]);

    const dialog = screen.getByRole("dialog", { name: "Editar venta #1" });
    expect(within(dialog).getByLabelText("Juli %")).toHaveValue(50);
    expect(within(dialog).getByLabelText("Cande %")).toHaveValue(50);
  });

  it("prefills derived shares for legacy rows with null shares", async () => {
    vi.mocked(reportsApi.getSalesDetail).mockResolvedValue([
      { ...DETAIL_ROW, juli_share: null, cande_share: null, observaciones: "Cande" },
    ]);
    renderReportes();

    const user = userEvent.setup();
    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    await user.click(editButtons[0]);

    const dialog = screen.getByRole("dialog", { name: "Editar venta #1" });
    expect(within(dialog).getByLabelText("Juli %")).toHaveValue(0);
    expect(within(dialog).getByLabelText("Cande %")).toHaveValue(100);
  });

  it("rejects saving when shares do not sum to 100", async () => {
    renderReportes();

    const user = userEvent.setup();
    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    await user.click(editButtons[0]);

    const dialog = screen.getByRole("dialog", { name: "Editar venta #1" });
    const juliInput = within(dialog).getByLabelText("Juli %");
    await user.clear(juliInput);
    await user.type(juliInput, "60");
    await user.click(within(dialog).getByRole("button", { name: "Guardar" }));

    expect(within(dialog).getByText(/deben sumar 100/)).toBeInTheDocument();
    expect(updateSale).not.toHaveBeenCalled();
  });

  it("sends date and shares when saving", async () => {
    vi.mocked(updateSale).mockResolvedValue(UPDATED_SALE);
    renderReportes();

    const user = userEvent.setup();
    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    await user.click(editButtons[0]);

    const dialog = screen.getByRole("dialog", { name: "Editar venta #1" });
    fireEvent.change(within(dialog).getByLabelText("Fecha"), {
      target: { value: "2026-09-01" },
    });
    await user.click(within(dialog).getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(updateSale).toHaveBeenCalledTimes(1));
    expect(updateSale).toHaveBeenCalledWith(1, {
      payment_method: null,
      juli_share: 85,
      cande_share: 15,
      // Picked date + preserved BA-local time-of-day (21:30:00).
      date: "2026-09-01T21:30:00",
    });
  });

  it("does not send date when the date input is untouched", async () => {
    vi.mocked(updateSale).mockResolvedValue(UPDATED_SALE);
    renderReportes();

    const user = userEvent.setup();
    const editButtons = await screen.findAllByRole("button", { name: "Editar venta" });
    await user.click(editButtons[0]);
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(updateSale).toHaveBeenCalledTimes(1));
    const [saleId, payload] = vi.mocked(updateSale).mock.calls[0];
    expect(saleId).toBe(1);
    expect(payload).not.toHaveProperty("date");
  });

  it("renders the earnings table with Juli and Cande rows", async () => {
    vi.mocked(reportsApi.getEarningsReport).mockResolvedValue({
      start_date: "2026-08-01",
      end_date: "2026-08-31",
      rows: [
        { seller: "Juli", sale_count: 3, revenue: "850.00" },
        { seller: "Cande", sale_count: 2, revenue: "150.00" },
      ],
    });
    renderReportes();

    expect(
      await screen.findByRole("heading", { name: "Ventas por vendedora" })
    ).toBeInTheDocument();
    // "Juli" also appears in the sales-detail observaciones column, so assert
    // via "Cande" (unique to the earnings table) plus the sale counts.
    expect(await screen.findByText("Cande")).toBeInTheDocument();
    expect(screen.getAllByText("Juli").length).toBeGreaterThan(0);
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("shows Observaciones column in the sales detail table", async () => {
    vi.mocked(reportsApi.getSalesDetail).mockResolvedValue([
      { ...DETAIL_ROW, observaciones: "Juli y Cande" },
    ]);
    renderReportes();

    expect(await screen.findByText("Rayuela")).toBeInTheDocument();
    expect(screen.getByText("Observaciones")).toBeInTheDocument();
    expect(screen.getByText("Juli y Cande")).toBeInTheDocument();
    expect(screen.queryByText("Vendido por")).not.toBeInTheDocument();
  });

  it("shows Juli for a null observaciones in the sales detail table", async () => {
    renderReportes();

    expect(await screen.findByText("Rayuela")).toBeInTheDocument();
    expect(screen.getByText("Juli")).toBeInTheDocument();
  });
});
