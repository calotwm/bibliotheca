import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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
    const authorInput = screen.getByPlaceholderText("Autor");
    const editorialInput = screen.getByPlaceholderText("Editorial");

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
});
