import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as booksApi from "../api/books";
import * as categoriesApi from "../api/categories";
import { Inventario } from "./Inventario";

vi.mock("../api/books", () => ({
  listBooks: vi.fn(),
  createBook: vi.fn(),
  updateBook: vi.fn(),
  deleteBook: vi.fn(),
}));

vi.mock("../api/categories", () => ({
  listCategories: vi.fn(),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Inventario />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const sampleBook = {
  id: 1,
  title: "Rayuela",
  author: "Julio Cortázar",
  editorial: "Sudamericana",
  category_id: 1,
  category_name: "Novela",
  price: "12.50",
  stock: 3,
  isbn: null,
  genre: null,
  source_sheet: null,
  observaciones: null,
  is_active: true,
  stock_status: "In Stock",
};

describe("Inventario", () => {
  beforeEach(() => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([]);
    vi.mocked(categoriesApi.listCategories).mockResolvedValue([]);
  });

  it("sends combined title, author and editorial filters to listBooks", async () => {
    const user = userEvent.setup();
    renderPage();

    const titleInput = screen.getByRole("searchbox", { name: /título/i });
    const authorInput = screen.getByLabelText("Autor");
    const editorialInput = screen.getByLabelText("Editorial");

    await user.type(titleInput, "Rayuela");
    await user.type(authorInput, "Cortázar");
    await user.type(editorialInput, "Sudamericana");

    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Rayuela",
          author: "Cortázar",
          editorial: "Sudamericana",
        })
      );
    });
  });

  it("shows a visible label for each of the five filters", () => {
    renderPage();

    expect(screen.getByLabelText("Título")).toBeInTheDocument();
    expect(screen.getByLabelText("Autor")).toBeInTheDocument();
    expect(screen.getByLabelText("Editorial")).toBeInTheDocument();
    expect(screen.getByLabelText("Categoría")).toBeInTheDocument();
    expect(screen.getByLabelText("Stock")).toBeInTheDocument();
  });

  it("sorts by category when clicking the Categoría column header", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    const user = userEvent.setup();
    renderPage();

    const categoryHeader = await screen.findByRole("button", { name: /categoría/i });
    await user.click(categoryHeader);

    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ sort_by: "category", sort_dir: "asc" })
      );
    });
  });

  it("renders Sin stock for a zero-stock row and the plain quantity otherwise", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([
      {
        id: 1,
        title: "Agotado",
        author: "A",
        editorial: "E",
        category_id: 1,
        category_name: "Novela",
        price: "10.00",
        stock: 0,
        isbn: null,
        genre: null,
        source_sheet: null,
        observaciones: null,
        is_active: true,
        stock_status: "Out",
      },
      {
        id: 2,
        title: "Disponible",
        author: "B",
        editorial: "F",
        category_id: 1,
        category_name: "Novela",
        price: "12.00",
        stock: 1,
        isbn: null,
        genre: null,
        source_sheet: null,
        observaciones: null,
        is_active: true,
        stock_status: "In Stock",
      },
    ]);
    renderPage();

    expect(await screen.findByText("Agotado")).toBeInTheDocument();
    expect(screen.getAllByText("Sin stock").length).toBeGreaterThan(0);
    expect(screen.getByText("Disponible")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("sends sort_by/sort_dir when clicking a sortable column header", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    const user = userEvent.setup();
    renderPage();

    const titleHeader = await screen.findByRole("button", { name: /título/i });
    await user.click(titleHeader);

    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ sort_by: "title", sort_dir: "asc" })
      );
    });
  });

  it("toggles sort direction asc -> desc when clicking the same header again", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    const user = userEvent.setup();
    renderPage();

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

  it("sorts by a new column with asc default after switching", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /título/i }));
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ sort_by: "title", sort_dir: "asc" })
      );
    });

    await user.click(await screen.findByRole("button", { name: /precio/i }));
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ sort_by: "price", sort_dir: "asc" })
      );
    });
  });

  it("shows an Observaciones column with the book value", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([
      { ...sampleBook, observaciones: "Juli y Cande" },
    ]);
    renderPage();

    // Wait for the table body to render with the row.
    await waitFor(() => {
      const cells = document.querySelectorAll("td");
      expect(Array.from(cells).some((c) => c.textContent === "Juli y Cande")).toBe(true);
    });
    // The header is now a sortable button, so the header text shares the
    // <button> with the sort arrow span — query the underlying <th> directly.
    const headers = Array.from(document.querySelectorAll("th"));
    expect(headers.some((h) => h.textContent?.startsWith("Observaciones"))).toBe(true);
  });

  it("shows Juli for a book with null observaciones", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    renderPage();

    expect(await screen.findByText("Rayuela")).toBeInTheDocument();
    // The Vendedora select also lists "Juli" as an option, so the cell text
    // is one of several matches. Assert at least one match exists in the
    // table body (the cell renders "Juli" via formatObservaciones fallback).
    const cells = document.querySelectorAll("td");
    const cellTexts = Array.from(cells).map((c) => c.textContent);
    expect(cellTexts).toContain("Juli");
  });

  it("includes observaciones in the book create payload", async () => {
    const user = userEvent.setup();
    vi.mocked(categoriesApi.listCategories).mockResolvedValue([
      { id: 1, name: "Novela" },
    ]);
    vi.mocked(booksApi.createBook).mockResolvedValue(sampleBook);
    renderPage();

    await user.click(screen.getByRole("button", { name: "Nuevo libro" }));
    const dialog = screen.getByRole("dialog", { name: "Nuevo libro" });

    await user.type(within(dialog).getByLabelText(/Título/), "Rayuela");
    await user.type(within(dialog).getByLabelText(/Autor/), "Julio Cortázar");
    await user.type(within(dialog).getByLabelText(/Editorial/), "Sudamericana");
    await user.type(within(dialog).getByLabelText(/Precio/), "12.50");
    await user.type(within(dialog).getByLabelText(/Stock/), "3");
    await user.type(within(dialog).getByLabelText("Observaciones"), "Juli y Cande");

    await user.click(within(dialog).getByRole("button", { name: "Crear libro" }));

    await waitFor(() => {
      expect(booksApi.createBook).toHaveBeenCalledWith(
        expect.objectContaining({ observaciones: "Juli y Cande" })
      );
    });
  });

  it("renders a Vendedora select with four options", () => {
    renderPage();
    const select = screen.getByLabelText("Vendedora") as HTMLSelectElement;
    const optionValues = Array.from(select.options).map((o) => o.value);
    const optionLabels = Array.from(select.options).map((o) => o.textContent);
    // Values: empty (Todas) + the three buckets.
    expect(optionValues).toEqual(["", "Juli", "Cande", "Juli y Cande"]);
    // Labels: Todas + bucket names.
    expect(optionLabels).toEqual(["Todas", "Juli", "Cande", "Juli y Cande"]);
  });

  it("sends seller to listBooks and resets page when Vendedora changes", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    const user = userEvent.setup();
    renderPage();

    // Initial call has no seller (Todas).
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalled();
    });
    const sellerSelect = screen.getByLabelText("Vendedora") as HTMLSelectElement;
    await user.selectOptions(sellerSelect, "Cande");

    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ seller: "Cande", page: 1 })
      );
    });
  });

  it("toggles observaciones header sort asc then desc", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    const user = userEvent.setup();
    renderPage();

    const obsHeader = await screen.findByRole("button", { name: /observaciones/i });
    await user.click(obsHeader);
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ sort_by: "observaciones", sort_dir: "asc" })
      );
    });

    await user.click(await screen.findByRole("button", { name: /observaciones/i }));
    await waitFor(() => {
      expect(booksApi.listBooks).toHaveBeenCalledWith(
        expect.objectContaining({ sort_by: "observaciones", sort_dir: "desc" })
      );
    });
  });

  it("renders DataTable with fixedLayout and wrapText enabled", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    renderPage();
    const table = await screen.findByRole("table");
    expect(table.className).toContain("table-fixed");
    // Long observaciones text triggers wrapping on body cells.
    const firstCell = table.querySelector("td");
    expect(firstCell?.className ?? "").toContain("whitespace-normal");
    expect(firstCell?.className ?? "").toContain("break-words");
  });

  it("keeps the table shrinkable so columns adapt instead of being cut off", async () => {
    vi.mocked(booksApi.listBooks).mockResolvedValue([sampleBook]);
    renderPage();
    const table = await screen.findByRole("table");
    // The 640px floor made the table overflow and scroll sideways instead of
    // adapting when the viewport narrowed. Inventario asks for a lower floor.
    expect(table.className).not.toContain("min-w-[640px]");
    expect(table.className).toContain("min-w-[520px]");
    // Under table-fixed every column width must be RELATIVE. A fixed rem width
    // (w-32, w-48, ...) is authoritative and gives the table a hard minimum,
    // which is exactly what reintroduced the horizontal overflow.
    const headers = Array.from(document.querySelectorAll("th"));
    expect(headers).toHaveLength(8);
    for (const header of headers) {
      expect(header.className).not.toMatch(/\bw-\d+\b/);
      expect(header.className).not.toMatch(/\bw-\[[0-9.]+rem\]/);
      expect(header.className).toMatch(/\bw-\[[0-9.]+%\]/);
    }
  });
});
