import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as suppliersApi from "../api/suppliers";
import type { Supplier } from "../lib/types";
import { Proveedores } from "./Proveedores";

vi.mock("../api/suppliers", () => ({
  listSuppliers: vi.fn(),
  createSupplier: vi.fn(),
  updateSupplier: vi.fn(),
  deleteSupplier: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <Proveedores />
    </QueryClientProvider>
  );
}

const sampleSupplier: Supplier = {
  id: 1,
  name: "Larria",
  contact_name: "Ariel",
  phone: null,
  email: "wpp: +54 9 11 5602-9957",
  address: null,
  notes: null,
  discount: "50% / 40%",
  sale_condition: "Venta directa por whatsapp",
  editorials: [],
  created_at: "2026-08-26T00:00:00",
  updated_at: "2026-08-26T00:00:00",
};

describe("Proveedores", () => {
  beforeEach(() => {
    vi.mocked(suppliersApi.listSuppliers).mockResolvedValue([sampleSupplier]);
    vi.mocked(suppliersApi.createSupplier).mockResolvedValue(sampleSupplier);
    vi.mocked(suppliersApi.updateSupplier).mockResolvedValue(sampleSupplier);
    vi.mocked(suppliersApi.deleteSupplier).mockResolvedValue(undefined);
  });

  it("renders the Descuento and Condición de venta column headers", async () => {
    renderPage();
    expect(await screen.findByText("Descuento")).toBeInTheDocument();
    expect(screen.getByText("Condición de venta")).toBeInTheDocument();
  });

  it("shows the fixture values in the table cells", async () => {
    renderPage();
    expect(await screen.findByText("Larria")).toBeInTheDocument();
    expect(screen.getByText("50% / 40%")).toBeInTheDocument();
    expect(screen.getByText("Venta directa por whatsapp")).toBeInTheDocument();
  });

  it("includes discount and sale_condition in the create payload", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: "Nuevo proveedor" }));

    await user.type(screen.getByLabelText(/Nombre/), "Nuevo Distribuidor");
    await user.type(screen.getByLabelText(/Descuento/), "30%");
    await user.type(screen.getByLabelText(/Condición de venta/), "Contado");
    await user.click(screen.getByRole("button", { name: "Crear proveedor" }));

    await waitFor(() => {
      expect(suppliersApi.createSupplier).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Nuevo Distribuidor",
          discount: "30%",
          sale_condition: "Contado",
        })
      );
    });
  });
});
