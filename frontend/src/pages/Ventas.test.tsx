import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as booksApi from "../api/books";
import { createSale } from "../api/sales";
import type { Book, Sale } from "../lib/types";
import { Ventas } from "./Ventas";

vi.mock("../api/books", () => ({
  listBooks: vi.fn(),
}));

vi.mock("../api/sales", () => ({
  createSale: vi.fn(),
  fetchInvoice: vi.fn(),
}));

const MOCK_BOOKS: Book[] = [
  {
    id: 1,
    title: "Cien años de soledad",
    author: "García Márquez",
    editorial: "Sudamericana",
    category_id: 1,
    category_name: "Novela",
    price: "12000.00",
    stock: 5,
    isbn: null,
    genre: null,
    source_sheet: null,
    observaciones: null,
    is_active: true,
    stock_status: "In Stock",
  },
  {
    id: 2,
    title: "El principito",
    author: "Saint-Exupéry",
    editorial: "Emecé",
    category_id: 5,
    category_name: "Infantil y Juvenil",
    price: "8000.00",
    stock: 0,
    isbn: null,
    genre: null,
    source_sheet: null,
    observaciones: null,
    is_active: true,
    stock_status: "Out",
  },
];

function renderVentas() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <Ventas />
    </QueryClientProvider>
  );
}

function checkoutPanel() {
  return screen.getByTestId("checkout-panel");
}

describe("Ventas (POS)", () => {
  beforeEach(() => {
    vi.mocked(booksApi.listBooks).mockResolvedValue(MOCK_BOOKS);
    vi.mocked(createSale).mockReset();
  });

  it("adds a book to the cart and computes the total", async () => {
    const user = userEvent.setup();
    renderVentas();
    // First render in a file can be slow on a cold worker (module transform +
    // debounced search); wait for real content instead of racing the 1s default.
    await screen.findByText("Cien años de soledad");
    const addButtons = await screen.findAllByRole("button", { name: /Agregar/ });
    await user.click(addButtons[0]);

    const panel = checkoutPanel();
    expect(within(panel).getByText("Cien años de soledad")).toBeInTheDocument();
    expect(within(panel).getByTestId("cart-total")).toHaveTextContent("12.000");
  });

  it("updates the total when quantity is increased", async () => {
    const user = userEvent.setup();
    renderVentas();
    const addButtons = await screen.findAllByRole("button", { name: /Agregar/ });
    await user.click(addButtons[0]);

    await user.click(
      screen.getByRole("button", { name: "Aumentar cantidad de Cien años de soledad" })
    );

    const panel = checkoutPanel();
    expect(within(panel).getByTestId("cart-total")).toHaveTextContent("24.000");
  });

  it("does not allow adding an out-of-stock book", async () => {
    renderVentas();
    const addButtons = await screen.findAllByRole("button", { name: /Agregar/ });
    expect(addButtons[1]).toBeDisabled();
    expect(addButtons[0]).toBeEnabled();
  });

  it("shows an empty-cart message when no items are added", async () => {
    renderVentas();
    await screen.findAllByRole("button", { name: /Agregar/ });
    expect(
      within(checkoutPanel()).getByText(/El carrito está vacío/)
    ).toBeInTheDocument();
  });

  it("opens the mobile cart as a bottom sheet from the bar", async () => {
    const user = userEvent.setup();
    renderVentas();
    const addButtons = await screen.findAllByRole("button", { name: /Agregar/ });
    await user.click(addButtons[0]);

    await user.click(screen.getByRole("button", { name: "Ver carrito" }));
    const sheet = screen.getByRole("dialog", { name: "Venta actual" });
    expect(sheet).toBeInTheDocument();
    expect(within(sheet).getByText("Cien años de soledad")).toBeInTheDocument();
    expect(within(sheet).getByTestId("cart-total")).toHaveTextContent("12.000");
  });

  it("requires a seller to confirm and sends it with createSale", async () => {
    const user = userEvent.setup();
    const SOLD: Sale = {
      id: 1,
      sale_number: 1,
      date: "2026-08-29T00:30:00Z",
      total: "12000.00",
      seller: "Cande",
      payment_method: null,
      customer_name: null,
      customer_cuit: null,
      invoice_pdf_path: null,
      observaciones: null,
      created_by: null,
      created_at: "2026-08-29T00:30:00Z",
      items: [],
    };
    vi.mocked(createSale).mockResolvedValue(SOLD);
    renderVentas();

    const addButtons = await screen.findAllByRole("button", { name: /Agregar/ });
    await user.click(addButtons[0]);

    const confirm = screen.getByRole("button", { name: "Confirmar venta" });
    expect(confirm).toBeDisabled();

    await user.selectOptions(screen.getByRole("combobox", { name: "Vendedor" }), "Cande");
    expect(confirm).toBeEnabled();
    await user.click(confirm);

    expect(createSale).toHaveBeenCalledTimes(1);
    expect(createSale).toHaveBeenCalledWith(
      expect.objectContaining({ seller: "Cande" })
    );
    const dialog = screen.getByRole("dialog", { name: "Venta confirmada" });
    expect(within(dialog).getByText("Cande")).toBeInTheDocument();
  });

  it("shows Juli and Cande y Juli as seller labels while keeping backend values", async () => {
    renderVentas();
    const combobox = screen.getByRole("combobox", { name: "Vendedor" });
    const juliOption = within(combobox).getByRole("option", {
      name: "Juli",
    }) as HTMLOptionElement;
    expect(juliOption.value).toBe("Julieta");
    const sharedOption = within(combobox).getByRole("option", {
      name: "Cande y Juli",
    }) as HTMLOptionElement;
    expect(sharedOption.value).toBe("Cande y Julieta");
  });

  it("does not confirm a sale when no seller is selected", async () => {
    const user = userEvent.setup();
    renderVentas();
    const addButtons = await screen.findAllByRole("button", { name: /Agregar/ });
    await user.click(addButtons[0]);

    expect(
      within(checkoutPanel()).getByRole("button", { name: "Confirmar venta" })
    ).toBeDisabled();
    expect(createSale).not.toHaveBeenCalled();
  });

  it("shows the observaciones line in the confirmed-sale modal", async () => {
    const user = userEvent.setup();
    vi.mocked(createSale).mockResolvedValue({
      id: 1,
      sale_number: 1,
      date: "2026-08-29T00:30:00Z",
      total: "12000.00",
      seller: "Cande",
      payment_method: null,
      customer_name: null,
      customer_cuit: null,
      invoice_pdf_path: null,
      observaciones: "Juli y Cande",
      created_by: null,
      created_at: "2026-08-29T00:30:00Z",
      items: [],
    });
    renderVentas();

    const addButtons = await screen.findAllByRole("button", { name: /Agregar/ });
    await user.click(addButtons[0]);
    await user.selectOptions(screen.getByRole("combobox", { name: "Vendedor" }), "Cande");
    await user.click(screen.getByRole("button", { name: "Confirmar venta" }));

    const dialog = await screen.findByRole("dialog", { name: "Venta confirmada" });
    expect(within(dialog).getByText(/Observaciones:/)).toBeInTheDocument();
    expect(within(dialog).getByText("Juli y Cande")).toBeInTheDocument();
  });

  it("shows Juli in the confirmed-sale modal when observaciones is null", async () => {
    const user = userEvent.setup();
    vi.mocked(createSale).mockResolvedValue({
      id: 1,
      sale_number: 1,
      date: "2026-08-29T00:30:00Z",
      total: "12000.00",
      seller: "Cande",
      payment_method: null,
      customer_name: null,
      customer_cuit: null,
      invoice_pdf_path: null,
      observaciones: null,
      created_by: null,
      created_at: "2026-08-29T00:30:00Z",
      items: [],
    });
    renderVentas();

    const addButtons = await screen.findAllByRole("button", { name: /Agregar/ });
    await user.click(addButtons[0]);
    await user.selectOptions(screen.getByRole("combobox", { name: "Vendedor" }), "Cande");
    await user.click(screen.getByRole("button", { name: "Confirmar venta" }));

    const dialog = await screen.findByRole("dialog", { name: "Venta confirmada" });
    expect(within(dialog).getByText(/Observaciones:/)).toBeInTheDocument();
    expect(within(dialog).getByText("Juli")).toBeInTheDocument();
  });
});
