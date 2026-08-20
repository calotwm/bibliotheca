import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as booksApi from "../api/books";
import * as categoriesApi from "../api/categories";
import * as importApi from "../api/import";
import { AuthProvider } from "../auth/AuthContext";
import { Precios } from "./Precios";

vi.mock("../api/books", () => ({
  listBooks: vi.fn(),
}));

vi.mock("../api/categories", () => ({
  listCategories: vi.fn(),
}));

vi.mock("../api/import", () => ({
  bulkPreview: vi.fn(),
  bulkApply: vi.fn(),
}));

function renderPrecios(role = "admin") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  localStorage.setItem("bibliotheca_token", "test-token");
  localStorage.setItem("bibliotheca_user", JSON.stringify({ username: "caja", role }));
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Precios />
      </AuthProvider>
    </QueryClientProvider>
  );
}

const sampleBook = {
  id: 1,
  title: "Libro A",
  author: "Autor",
  editorial: "Sudamericana",
  category_id: 1,
  category_name: null,
  price: "10000",
  stock: 5,
  isbn: null,
  genre: null,
  source_sheet: null,
  is_active: true,
  stock_status: "In Stock",
};

function makeBook(id: number): typeof sampleBook {
  return { ...sampleBook, id, title: `Libro ${id}` };
}

describe("Precios", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    vi.mocked(booksApi.listBooks).mockImplementation(async (filters = {}) =>
      filters.page_size === 300 ? [sampleBook] : []
    );
    vi.mocked(categoriesApi.listCategories).mockResolvedValue([
      { id: 1, name: "Ficción" },
    ]);
    vi.mocked(importApi.bulkPreview).mockResolvedValue({
      editorial: "Sudamericana",
      category_id: null,
      action: "price_percent",
      amount: "-10",
      affected: 0,
      rows: [],
    });
    vi.mocked(importApi.bulkApply).mockResolvedValue({
      editorial: "Sudamericana",
      category_id: null,
      action: "price_percent",
      amount: "-10",
      affected: 2,
    });
  });

  it("renders the price adjustment form with editorial suggestions", async () => {
    renderPrecios();
    expect(
      screen.getByRole("heading", { name: "Ajuste de precios por editorial" })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Editorial/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Categoría/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Operación/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Monto/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Previsualizar" })
    ).toBeInTheDocument();

    await waitFor(() => {
      const datalist = document.getElementById("editoriales");
      const options = Array.from(datalist?.querySelectorAll("option") ?? []).map(
        (option) => option.getAttribute("value")
      );
      expect(options).toContain("Sudamericana");
    });
  });

  it("sends a negative amount when lowering by percentage", async () => {
    const user = userEvent.setup();
    renderPrecios();
    await user.type(screen.getByLabelText(/Editorial/), "Sudamericana");
    await user.selectOptions(screen.getByLabelText(/Operación/), "lower_percent");
    await user.type(screen.getByLabelText(/Monto/), "10");
    await user.click(screen.getByRole("button", { name: "Previsualizar" }));

    expect(importApi.bulkPreview).toHaveBeenCalledTimes(1);
    expect(importApi.bulkPreview).toHaveBeenCalledWith({
      editorial: "Sudamericana",
      category_id: null,
      action: "price_percent",
      amount: -10,
    });
  });

  it("renders preview rows formatting old and new prices with formatARS", async () => {
    vi.mocked(importApi.bulkPreview).mockResolvedValue({
      editorial: "Sudamericana",
      category_id: null,
      action: "price_percent",
      amount: "-10",
      affected: 1,
      rows: [
        {
          id: 1,
          title: "Libro A",
          editorial: "Sudamericana",
          field: "price",
          old_value: "10000",
          new_value: "9000",
        },
      ],
    });
    const user = userEvent.setup();
    renderPrecios();
    await user.type(screen.getByLabelText(/Editorial/), "Sudamericana");
    await user.selectOptions(screen.getByLabelText(/Operación/), "lower_percent");
    await user.type(screen.getByLabelText(/Monto/), "10");
    await user.click(screen.getByRole("button", { name: "Previsualizar" }));

    expect(
      await screen.findByText(
        (_content: string, node) =>
          node?.textContent === "Se verán afectados 1 libro(s)."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Precio actual")).toBeInTheDocument();
    expect(screen.getByText("Precio nuevo")).toBeInTheDocument();
    expect(screen.getByText(/\$\s*10\.000,00/)).toBeInTheDocument();
    expect(screen.getByText(/\$\s*9\.000,00/)).toBeInTheDocument();
  });

  it("shows a friendly message when no books match and disables apply", async () => {
    const user = userEvent.setup();
    renderPrecios();
    await user.type(screen.getByLabelText(/Editorial/), "Otra Editorial");
    await user.type(screen.getByLabelText(/Monto/), "10");
    await user.click(screen.getByRole("button", { name: "Previsualizar" }));

    expect(
      await screen.findByText("No hay libros activos de esa editorial.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Aplicar cambios" })
    ).toBeDisabled();
  });

  it("blocks cashiers: shows the admin notice and cannot trigger preview", async () => {
    const user = userEvent.setup();
    renderPrecios("cashier");
    expect(
      screen.getByText("Solo administradores pueden modificar precios.")
    ).toBeInTheDocument();

    const previewButton = screen.getByRole("button", { name: "Previsualizar" });
    expect(previewButton).toBeDisabled();
    await user.click(previewButton);
    expect(importApi.bulkPreview).not.toHaveBeenCalled();
  });

  it("renders the bulk price-adjustment form above the book list", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    renderPrecios();

    const headings = screen.getAllByRole("heading", { level: 2 });
    const bulkIndex = headings.findIndex(
      (heading) => heading.textContent === "Ajuste de precios por editorial"
    );
    const listIndex = headings.findIndex(
      (heading) => heading.textContent === "Listado de libros"
    );

    expect(bulkIndex).toBeGreaterThanOrEqual(0);
    expect(listIndex).toBeGreaterThanOrEqual(0);
    expect(bulkIndex).toBeLessThan(listIndex);

    expect(await screen.findByText("Libro A")).toBeInTheDocument();
  });

  it("sends combined author and editorial filters with AND semantics", async () => {
    const user = userEvent.setup();
    renderPrecios();
    const authorInput = screen.getByLabelText("Filtrar por autor");
    const editorialInput = screen.getByLabelText("Filtrar por editorial");
    await user.type(authorInput, "Borges");
    await user.type(editorialInput, "Alpha");

    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ author: "Borges", editorial: "Alpha" })
      );
    });
  });

  it("toggles sort direction asc -> desc on the Título column", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    const user = userEvent.setup();
    renderPrecios();

    const titleHeader = await screen.findByRole("button", { name: /título/i });
    await user.click(titleHeader);
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ sort_by: "title", sort_dir: "asc" })
      );
    });

    await user.click(await screen.findByRole("button", { name: /título/i }));
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ sort_by: "title", sort_dir: "desc" })
      );
    });
  });

  it("appends the next page when Cargar más is clicked", async () => {
    const page1 = Array.from({ length: 100 }, (_, i) => makeBook(i + 1));
    const page2 = [makeBook(101)];
    vi.mocked(booksApi.listBooks).mockImplementation(async (filters = {}) => {
      if (filters.page_size === 300) return [sampleBook];
      return filters.page === 2 ? page2 : page1;
    });
    const user = userEvent.setup();
    renderPrecios();

    await screen.findByText("Libro 1");
    await user.click(screen.getByRole("button", { name: "Cargar más" }));
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 })
      );
    });
    expect(await screen.findByText("Libro 101")).toBeInTheDocument();
  });

  it("shows the read-only list to cashiers while the bulk form stays admin-gated", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    renderPrecios("cashier");

    const headings = screen.getAllByRole("heading", { level: 2 });
    const bulkIndex = headings.findIndex(
      (heading) => heading.textContent === "Ajuste de precios por editorial"
    );
    const listIndex = headings.findIndex(
      (heading) => heading.textContent === "Listado de libros"
    );
    expect(bulkIndex).toBeLessThan(listIndex);

    expect(
      screen.getByRole("heading", { name: "Listado de libros" })
    ).toBeInTheDocument();
    expect(await screen.findByText("Libro A")).toBeInTheDocument();
    expect(
      screen.getByText("Solo administradores pueden modificar precios.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Previsualizar" })
    ).toBeDisabled();
    expect(screen.queryByLabelText(/Editar|Eliminar/)).not.toBeInTheDocument();
  });

  it("resets to page 1 when a filter changes after loading more", async () => {
    const page1 = Array.from({ length: 100 }, (_, i) => makeBook(i + 1));
    const page2 = [makeBook(101)];
    vi.mocked(booksApi.listBooks).mockImplementation(async (filters = {}) => {
      if (filters.page_size === 300) return [sampleBook];
      return filters.page === 2 ? page2 : page1;
    });
    const user = userEvent.setup();
    renderPrecios();

    await screen.findByText("Libro 1");
    await user.click(screen.getByRole("button", { name: "Cargar más" }));
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 })
      );
    });
    expect(await screen.findByText("Libro 101")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Filtrar por autor"), "Borges");

    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ page: 1, author: "Borges" })
      );
    });
    await waitFor(() => {
      expect(screen.queryByText("Libro 101")).not.toBeInTheDocument();
    });
  });
});
