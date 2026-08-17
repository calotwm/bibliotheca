import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as booksApi from "../api/books";
import type { Book } from "../lib/types";
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
  });

  it("adds a book to the cart and computes the total", async () => {
    const user = userEvent.setup();
    renderVentas();
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
});