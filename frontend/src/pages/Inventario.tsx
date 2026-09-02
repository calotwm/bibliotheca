import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import * as booksApi from "../api/books";
import { listCategories } from "../api/categories";
import { BookFormModal } from "../components/BookFormModal";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { DataTable } from "../components/DataTable";
import { PencilIcon, PlusIcon, SearchIcon, TrashIcon } from "../components/icons";
import { STOCK_FILTERS } from "../lib/constants";
import { formatARS, formatObservaciones } from "../lib/format";
import type { Column } from "../components/DataTable";
import type { Book, BookPayload } from "../lib/types";

const PAGE_SIZE = 100;

const columns: Column<Book>[] = [
  {
    key: "title",
    header: "Título",
    sortable: true,
    sortKey: "title",
    render: (row) => <span className="font-medium">{row.title}</span>,
  },
  { key: "author", header: "Autor", sortable: true, sortKey: "author", render: (row) => row.author },
  { key: "editorial", header: "Editorial", sortable: true, sortKey: "editorial", render: (row) => row.editorial },
  { key: "category_name", header: "Categoría", sortable: true, sortKey: "category", render: (row) => row.category_name ?? "—" },
  { key: "price", header: "Precio", sortable: true, sortKey: "price", render: (row) => <span className="font-semibold">{formatARS(row.price)}</span> },
  {
    key: "stock",
    header: "Stock",
    sortable: true,
    sortKey: "stock",
    render: (row) =>
      row.stock === 0 ? (
        <span className="text-xs font-semibold text-red-700">Sin stock</span>
      ) : (
        <span className="text-xs text-ink-soft">{row.stock}</span>
      ),
  },
  { key: "observaciones", header: "Observaciones", render: (row) => formatObservaciones(row.observaciones) },
];

interface RowActionsProps {
  row: Book;
  onEdit: (book: Book) => void;
  onDelete: (book: Book) => void;
}

function RowActions({ row, onEdit, onDelete }: RowActionsProps) {
  return (
    <div className="flex justify-end gap-1">
      <button
        type="button"
        onClick={() => onEdit(row)}
        className="rounded-sm p-3 text-ink-soft hover:bg-navy/5 hover:text-navy lg:p-1.5"
        aria-label={`Editar ${row.title}`}
        title="Editar"
      >
        <PencilIcon className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => onDelete(row)}
        className="rounded-sm p-3 text-ink-soft hover:bg-red-50 hover:text-red-700 lg:p-1.5"
        aria-label={`Eliminar ${row.title}`}
        title="Eliminar"
      >
        <TrashIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

export function Inventario() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const [title, setTitle] = useState("");
  const [debouncedTitle, setDebouncedTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [stockStatus, setStockStatus] = useState(searchParams.get("stock_status") ?? "");
  const [author, setAuthor] = useState("");
  const [debouncedAuthor, setDebouncedAuthor] = useState("");
  const [editorial, setEditorial] = useState("");
  const [debouncedEditorial, setDebouncedEditorial] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [editing, setEditing] = useState<Book | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [deleting, setDeleting] = useState<Book | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedTitle(title), 300);
    return () => clearTimeout(timer);
  }, [title]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedAuthor(author), 300);
    return () => clearTimeout(timer);
  }, [author]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedEditorial(editorial), 300);
    return () => clearTimeout(timer);
  }, [editorial]);

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
  });

  const { data: books = [], isLoading, isError, error } = useQuery({
    queryKey: ["books", debouncedTitle, categoryId, stockStatus, debouncedAuthor, debouncedEditorial, sortBy, sortDir, page],
    queryFn: () =>
      booksApi.listBooks({
        title: debouncedTitle || undefined,
        category_id: categoryId ? Number(categoryId) : null,
        stock_status: stockStatus || null,
        author: debouncedAuthor || null,
        editorial: debouncedEditorial || null,
        sort_by: sortBy || null,
        sort_dir: sortDir || null,
        page,
        page_size: PAGE_SIZE,
      }),
  });

  const invalidateCatalog = () => {
    void queryClient.invalidateQueries({ queryKey: ["books"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const saveMutation = useMutation({
    mutationFn: (payload: BookPayload) =>
      editing ? booksApi.updateBook(editing.id, payload) : booksApi.createBook(payload),
    onSuccess: () => {
      invalidateCatalog();
      setShowForm(false);
      setEditing(null);
      setFormError(null);
    },
    onError: (err: unknown) => {
      setFormError(err instanceof Error ? err.message : "No se pudo guardar el libro.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => booksApi.deleteBook(id),
    onSuccess: () => {
      invalidateCatalog();
      setDeleting(null);
    },
  });

  const resetPageOnFilterChange = () => setPage(1);

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortDir("asc");
    }
    resetPageOnFilterChange();
  };

  const inputClass =
    "min-h-11 w-full rounded-sm border border-navy/20 bg-cream px-3 py-2 text-sm outline-none focus:border-navy";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <button
          type="button"
          onClick={() => {
            setEditing(null);
            setFormError(null);
            setShowForm(true);
          }}
          className="inline-flex min-h-10 items-center gap-1 rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light"
        >
          <PlusIcon className="h-4 w-4" />
          Nuevo libro
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="block">
          <label htmlFor="inv-title" className="text-sm font-medium">
            Título
          </label>
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" />
            <input
              id="inv-title"
              type="search"
              value={title}
              onChange={(event) => {
                setTitle(event.target.value);
                resetPageOnFilterChange();
              }}
              placeholder="Buscar por título…"
              className={`${inputClass} pl-9`}
            />
          </div>
        </div>
        <div className="block">
          <label htmlFor="inv-author" className="text-sm font-medium">
            Autor
          </label>
          <input
            id="inv-author"
            type="text"
            value={author}
            onChange={(event) => {
              setAuthor(event.target.value);
              resetPageOnFilterChange();
            }}
            placeholder="Autor"
            className={inputClass}
          />
        </div>
        <div className="block">
          <label htmlFor="inv-editorial" className="text-sm font-medium">
            Editorial
          </label>
          <input
            id="inv-editorial"
            type="text"
            value={editorial}
            onChange={(event) => {
              setEditorial(event.target.value);
              resetPageOnFilterChange();
            }}
            placeholder="Editorial"
            className={inputClass}
          />
        </div>
        <div className="block">
          <label htmlFor="inv-category" className="text-sm font-medium">
            Categoría
          </label>
          <select
            id="inv-category"
            value={categoryId}
            onChange={(event) => {
              setCategoryId(event.target.value);
              resetPageOnFilterChange();
            }}
            className={inputClass}
          >
            <option value="">Todas las categorías</option>
            {(categories ?? []).map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </div>
        <div className="block">
          <label htmlFor="inv-stock" className="text-sm font-medium">
            Stock
          </label>
          <select
            id="inv-stock"
            value={stockStatus}
            onChange={(event) => {
              setStockStatus(event.target.value);
              resetPageOnFilterChange();
            }}
            className={inputClass}
          >
            {STOCK_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <p className="text-sm text-ink-soft">Cargando…</p>}
      {isError && (
        <p className="text-sm text-red-700">
          {error instanceof Error ? error.message : "No se pudo cargar el catálogo."}
        </p>
      )}
      {!isLoading && !isError && (
        <>
          <DataTable
            columns={[
              ...columns,
              {
                key: "actions",
                header: "",
                render: (row) => (
                  <RowActions
                    row={row}
                    onEdit={(book) => {
                      setEditing(book);
                      setFormError(null);
                      setShowForm(true);
                    }}
                    onDelete={(book) => setDeleting(book)}
                  />
                ),
              },
            ]}
            rows={books}
            getRowKey={(row) => row.id}
            emptyMessage="No se encontraron libros con esos filtros."
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={handleSort}
          />
          {books.length === page * PAGE_SIZE && (
            <div className="text-center">
              <button
                type="button"
                onClick={() => setPage((current) => current + 1)}
                className="min-h-10 rounded-sm border border-navy/20 bg-cream px-4 py-2 text-sm font-medium text-navy hover:bg-navy/5"
              >
                Cargar más
              </button>
            </div>
          )}
        </>
      )}

      {showForm && (
        <BookFormModal
          categories={categories ?? []}
          initial={editing}
          submitting={saveMutation.isPending}
          error={formError}
          onSave={(payload) => saveMutation.mutate(payload)}
          onCancel={() => {
            setShowForm(false);
            setEditing(null);
            setFormError(null);
          }}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title="Eliminar libro"
          message={`¿Desea eliminar "${deleting.title}" del catálogo? Esta acción no se puede deshacer.`}
          confirmLabel="Eliminar"
          cancelLabel="Cancelar"
          danger
          onConfirm={() => deleteMutation.mutate(deleting.id)}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}