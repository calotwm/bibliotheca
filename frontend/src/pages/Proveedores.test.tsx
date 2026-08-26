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

  it("renders the Cond. venta, Notas, and DTO column headers", async () => {
    renderPage();
    expect(await screen.findByText("Cond. venta")).toBeInTheDocument();
    expect(screen.getByText("Notas")).toBeInTheDocument();
    expect(screen.getByText("DTO")).toBeInTheDocument();
  });

  it("renders no Editoriales column", async () => {
    renderPage();
    await screen.findByText("Larria");
    expect(screen.queryByText("Editoriales")).not.toBeInTheDocument();
  });

  it("shows the fixture values in the table cells", async () => {
    renderPage();
    expect(await screen.findByText("Larria")).toBeInTheDocument();
    expect(screen.getByText("50% / 40%")).toBeInTheDocument();
    expect(screen.getByText("Venta directa por whatsapp")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("includes sale_condition, notes, and discount in the create payload and excludes editorials", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: "Nuevo proveedor" }));

    await user.type(screen.getByLabelText(/Nombre/), "Nuevo Distribuidor");
    await user.type(screen.getByLabelText(/DTO/), "30%");
    await user.type(screen.getByLabelText(/Condición de venta/), "Contado");
    await user.type(screen.getByLabelText(/Notas/), "Entrega los jueves");
    await user.click(screen.getByRole("button", { name: "Crear proveedor" }));

    await waitFor(() => {
      const payload = vi.mocked(suppliersApi.createSupplier).mock.calls[0][0] as unknown as Record<string, unknown>;
      expect(payload).toMatchObject({
        name: "Nuevo Distribuidor",
        discount: "30%",
        sale_condition: "Contado",
        notes: "Entrega los jueves",
      });
      expect(payload).not.toHaveProperty("editorials");
    });
  });

  it("includes sale_condition, notes, and discount in the update payload and excludes editorials", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole("button", { name: "Editar Larria" }));

    const discountInput = screen.getByLabelText(/DTO/);
    await user.clear(discountInput);
    await user.type(discountInput, "45%");
    const conditionInput = screen.getByLabelText(/Condición de venta/);
    await user.clear(conditionInput);
    await user.type(conditionInput, "Venta directa por mail");
    const notesInput = screen.getByLabelText(/Notas/);
    await user.clear(notesInput);
    await user.type(notesInput, "Pedido mínimo $5000");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() => {
      const payload = vi.mocked(suppliersApi.updateSupplier).mock.calls[0][1] as unknown as Record<string, unknown>;
      expect(payload).toMatchObject({
        discount: "45%",
        sale_condition: "Venta directa por mail",
        notes: "Pedido mínimo $5000",
      });
      expect(payload).not.toHaveProperty("editorials");
    });
  });
});
