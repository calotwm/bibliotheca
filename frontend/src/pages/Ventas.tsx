import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../api/client";
import * as booksApi from "../api/books";
import { createSale, fetchInvoice } from "../api/sales";
import { StatusBadge } from "../components/StatusBadge";
import {
  CartIcon,
  CheckIcon,
  MinusIcon,
  PlusIcon,
  SearchIcon,
  TrashIcon,
  XIcon,
} from "../components/icons";
import { formatARS, parsePrice } from "../lib/format";
import type { Book, Sale } from "../lib/types";

const PAGE_SIZE = 50;

const SELLERS = ["Cande", "Julieta", "Cande y Julieta"];

interface CartLine {
  book: Book;
  qty: number;
}

function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

async function openInvoice(saleId: number) {
  const blob = await fetchInvoice(saleId);
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

export function Ventas() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);
  const [cart, setCart] = useState<Record<number, number>>({});
  const [paymentMethod, setPaymentMethod] = useState("");
  const [seller, setSeller] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [customerCuit, setCustomerCuit] = useState("");
  const [result, setResult] = useState<Sale | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cartOpen, setCartOpen] = useState(false);

  const { data: books = [], isLoading } = useQuery({
    queryKey: ["pos-books", debouncedSearch],
    queryFn: () =>
      booksApi.listBooks({
        q: debouncedSearch || undefined,
        page: 1,
        page_size: PAGE_SIZE,
      }),
  });

  const bookById = useMemo(() => {
    const map = new Map<number, Book>();
    for (const book of books) map.set(book.id, book);
    return map;
  }, [books]);

  const lines: CartLine[] = useMemo(
    () =>
      Object.entries(cart)
        .map(([id, qty]) => ({ book: bookById.get(Number(id)), qty }))
        .filter((line): line is CartLine => line.book !== undefined),
    [cart, bookById]
  );

  const total = useMemo(
    () => lines.reduce((sum, line) => sum + parsePrice(line.book.price) * line.qty, 0),
    [lines]
  );

  useEffect(() => {
    if (!cartOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setCartOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [cartOpen]);

  function addToCart(book: Book) {
    setError(null);
    const current = cart[book.id] ?? 0;
    if (current >= book.stock) return;
    setCart((prev) => ({ ...prev, [book.id]: current + 1 }));
  }

  function changeQty(bookId: number, delta: number) {
    setError(null);
    setCart((prev) => {
      const current = prev[bookId] ?? 0;
      const book = bookById.get(bookId);
      const next = current + delta;
      if (next <= 0) {
        const copy = { ...prev };
        delete copy[bookId];
        return copy;
      }
      if (book && next > book.stock) return prev;
      return { ...prev, [bookId]: next };
    });
  }

  function removeFromCart(bookId: number) {
    setCart((prev) => {
      const copy = { ...prev };
      delete copy[bookId];
      return copy;
    });
  }

  const saleMutation = useMutation({
    mutationFn: () =>
      createSale({
        items: lines.map((line) => ({ book_id: line.book.id, quantity: line.qty })),
        seller,
        payment_method: paymentMethod.trim() || null,
        customer_name: customerName.trim() || null,
        customer_cuit: customerCuit.trim() || null,
      }),
    onSuccess: (sale) => {
      setResult(sale);
      setCart({});
      setCartOpen(false);
      setSearch("");
      setSeller("");
      setPaymentMethod("");
      setCustomerName("");
      setCustomerCuit("");
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["books"] });
      void queryClient.invalidateQueries({ queryKey: ["pos-books"] });
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError && err.status === 409) {
        setError("Stock insuficiente: la venta supera el stock disponible. Verifique las cantidades.");
      } else {
        setError(err instanceof Error ? err.message : "No se pudo confirmar la venta.");
      }
    },
  });

  function confirmSale() {
    setError(null);
    if (lines.length === 0) {
      setError("El carrito está vacío.");
      return;
    }
    if (!seller) {
      setError("Seleccione el vendedor o la vendedora para confirmar la venta.");
      return;
    }
    saleMutation.mutate();
  }

  const inputClass =
    "min-h-11 w-full rounded-sm border border-navy/20 bg-paper px-3 py-2 text-sm outline-none focus:border-navy";

  function renderCartBody() {
    return (
      <>
        {lines.length === 0 ? (
          <p className="px-4 py-6 text-sm text-ink-soft">
            El carrito está vacío. Agregue libros para iniciar una venta.
          </p>
        ) : (
          <ul className="max-h-72 divide-y divide-navy/10 overflow-y-auto px-4">
            {lines.map((line) => (
              <li key={line.book.id} className="flex items-center justify-between gap-2 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{line.book.title}</p>
                  <p className="text-xs text-ink-soft">
                    {formatARS(line.book.price)} × {line.qty} = {formatARS(parsePrice(line.book.price) * line.qty)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    type="button"
                    onClick={() => changeQty(line.book.id, -1)}
                    className="rounded-sm border border-navy/20 p-3 hover:bg-navy/5 lg:p-1"
                    aria-label={`Disminuir cantidad de ${line.book.title}`}
                  >
                    <MinusIcon className="h-3.5 w-3.5" />
                  </button>
                  <span className="w-6 text-center text-sm font-semibold">{line.qty}</span>
                  <button
                    type="button"
                    onClick={() => changeQty(line.book.id, 1)}
                    disabled={line.qty >= line.book.stock}
                    className="rounded-sm border border-navy/20 p-3 hover:bg-navy/5 disabled:opacity-40 lg:p-1"
                    aria-label={`Aumentar cantidad de ${line.book.title}`}
                  >
                    <PlusIcon className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => removeFromCart(line.book.id)}
                    className="rounded-sm p-3 text-ink-soft hover:text-red-700 lg:p-1"
                    aria-label={`Quitar ${line.book.title}`}
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="border-t border-navy/10 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Total</span>
            <span data-testid="cart-total" className="font-heading text-lg font-black text-navy">
              {formatARS(total)}
            </span>
          </div>

          <div className="mt-3 space-y-2">
            <select
              value={seller}
              onChange={(event) => setSeller(event.target.value)}
              className={inputClass}
              required
              aria-label="Vendedor"
            >
              <option value="" disabled>
                Seleccionar vendedor/a…
              </option>
              {SELLERS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={paymentMethod}
              onChange={(event) => setPaymentMethod(event.target.value)}
              placeholder="Método de pago (opcional)"
              className={inputClass}
            />
            <input
              type="text"
              value={customerName}
              onChange={(event) => setCustomerName(event.target.value)}
              placeholder="Cliente (opcional)"
              className={inputClass}
            />
            <input
              type="text"
              value={customerCuit}
              onChange={(event) => setCustomerCuit(event.target.value)}
              placeholder="CUIT (opcional)"
              className={inputClass}
            />
          </div>

          {error && (
            <p className="mt-3 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          <button
            type="button"
            onClick={confirmSale}
            disabled={saleMutation.isPending || lines.length === 0 || !seller}
            className="mt-3 min-h-10 w-full rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-50"
          >
            {saleMutation.isPending ? "Confirmando…" : "Confirmar venta"}
          </button>
        </div>
      </>
    );
  }

  return (
    <div className="grid gap-4 pb-20 lg:grid-cols-[1fr_320px] lg:pb-0">
      <section>
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar libro para vender…"
            className="w-full rounded-sm border border-navy/20 bg-cream py-2 pl-9 pr-3 text-sm outline-none focus:border-navy"
          />
        </div>

        {isLoading && <p className="mt-4 text-sm text-ink-soft">Cargando…</p>}
        {!isLoading && books.length === 0 && (
          <p className="mt-4 text-sm text-ink-soft">
            {search ? "No se encontraron libros." : "Escriba para buscar libros."}
          </p>
        )}

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {books.map((book) => {
            const inCart = cart[book.id] ?? 0;
            const soldOut = book.stock === 0 || inCart >= book.stock;
            return (
              <div
                key={book.id}
                className="flex flex-col rounded-sm border border-navy/10 bg-cream p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="font-heading font-bold leading-snug">{book.title}</p>
                  <StatusBadge status={book.stock_status} />
                </div>
                <p className="mt-1 text-xs text-ink-soft">
                  {book.author} · {book.editorial}
                </p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-sm font-semibold">{formatARS(book.price)}</span>
                  <span className="text-xs text-ink-soft">Stock: {book.stock}</span>
                </div>
                <button
                  type="button"
                  onClick={() => addToCart(book)}
                  disabled={soldOut}
                  className="mt-3 inline-flex min-h-10 items-center justify-center gap-1 rounded-sm bg-navy px-3 py-1.5 text-sm font-semibold text-cream hover:bg-navy-light disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label={`Agregar ${book.title}`}
                >
                  <PlusIcon className="h-4 w-4" />
                  Agregar
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <aside
        className="hidden h-fit rounded-sm border border-navy/10 bg-cream lg:sticky lg:top-20 lg:block"
        data-testid="checkout-panel"
        aria-label="Panel de venta"
      >
        <h2 className="border-b border-navy/10 px-4 py-3 text-base font-bold">Venta actual</h2>
        {renderCartBody()}
      </aside>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-navy/10 bg-cream px-4 py-2 lg:hidden">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs text-ink-soft">
              {lines.length} {lines.length === 1 ? "ítem" : "ítems"}
            </p>
            <p className="truncate font-heading text-lg font-black text-navy">{formatARS(total)}</p>
          </div>
          <button
            type="button"
            onClick={() => setCartOpen(true)}
            className="inline-flex min-h-10 items-center gap-1 rounded-sm bg-navy px-4 text-sm font-semibold text-cream hover:bg-navy-light"
          >
            <CartIcon className="h-4 w-4" />
            Ver carrito
          </button>
        </div>
      </div>

      {cartOpen && (
        <div
          className="fixed inset-0 z-50 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Venta actual"
        >
          <div
            className="absolute inset-0 bg-navy/50"
            onClick={() => setCartOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 max-h-[85dvh] overflow-y-auto rounded-t-lg border border-navy/10 bg-cream shadow-xl">
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-navy/10 bg-cream px-4 py-3">
              <h2 className="text-base font-bold">Venta actual</h2>
              <button
                type="button"
                onClick={() => setCartOpen(false)}
                aria-label="Cerrar carrito"
                className="rounded-sm p-2 text-ink-soft hover:text-ink"
              >
                <XIcon className="h-5 w-5" />
              </button>
            </div>
            {renderCartBody()}
          </div>
        </div>
      )}

      {result && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-navy/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Venta confirmada"
        >
          <div className="w-full max-w-md rounded-sm border border-navy/10 bg-cream p-6 shadow-xl">
            <div className="flex items-center gap-2 text-green-700">
              <CheckIcon className="h-6 w-6" />
              <h2 className="text-lg font-bold text-green-700">Venta confirmada</h2>
            </div>
            <p className="mt-3 text-sm">
              Venta <span className="font-semibold">#{result.sale_number}</span> registrada por{" "}
              <span className="font-semibold">{formatARS(result.total)}</span>
              {result.seller ? (
                <>
                  , vendida por <span className="font-semibold">{result.seller}</span>
                </>
              ) : null}
              .
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => void openInvoice(result.id)}
                className="rounded-sm border border-navy/20 px-4 py-2 text-sm font-medium text-navy hover:bg-navy/5"
              >
                Ver factura
              </button>
              <button
                type="button"
                onClick={() => setResult(null)}
                className="rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light"
              >
                Nueva venta
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}