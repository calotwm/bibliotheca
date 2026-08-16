import { useState } from "react";
import type { FormEvent } from "react";
import { Modal } from "./Modal";
import type { Book, BookPayload, Category } from "../lib/types";

interface BookFormModalProps {
  categories: Category[];
  initial: Book | null;
  submitting: boolean;
  error: string | null;
  onSave: (payload: BookPayload) => void;
  onCancel: () => void;
}

function toText(value: string | number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

export function BookFormModal({
  categories,
  initial,
  submitting,
  error,
  onSave,
  onCancel,
}: BookFormModalProps) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [author, setAuthor] = useState(initial?.author ?? "");
  const [editorial, setEditorial] = useState(initial?.editorial ?? "");
  const [categoryId, setCategoryId] = useState(
    initial ? String(initial.category_id) : categories[0] ? String(categories[0].id) : ""
  );
  const [price, setPrice] = useState(toText(initial?.price));
  const [stock, setStock] = useState(toText(initial?.stock));
  const [isbn, setIsbn] = useState(initial?.isbn ?? "");
  const [genre, setGenre] = useState(initial?.genre ?? "");
  const [validation, setValidation] = useState<string | null>(null);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setValidation(null);
    if (!title.trim() || !author.trim() || !editorial.trim()) {
      setValidation("Título, autor y editorial son obligatorios.");
      return;
    }
    if (!categoryId) {
      setValidation("Seleccione una categoría.");
      return;
    }
    const parsedPrice = Number(price);
    if (!Number.isFinite(parsedPrice) || parsedPrice < 0) {
      setValidation("Ingrese un precio válido.");
      return;
    }
    const parsedStock = Number.parseInt(stock, 10);
    if (!Number.isInteger(parsedStock) || parsedStock < 0) {
      setValidation("Ingrese un stock válido.");
      return;
    }
    onSave({
      title: title.trim(),
      author: author.trim(),
      editorial: editorial.trim(),
      category_id: Number(categoryId),
      price: parsedPrice,
      stock: parsedStock,
      isbn: isbn.trim() || null,
      genre: genre.trim() || null,
    });
  }

  const inputClass =
    "mt-1 w-full rounded-sm border border-navy/20 bg-paper px-3 py-2 text-sm outline-none focus:border-navy";

  return (
    <Modal
      title={initial ? "Editar libro" : "Nuevo libro"}
      onClose={onCancel}
      wide
    >
      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2" noValidate>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium">Título *</span>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Autor *</span>
          <input type="text" value={author} onChange={(e) => setAuthor(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Editorial *</span>
          <input type="text" value={editorial} onChange={(e) => setEditorial(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Categoría *</span>
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className={inputClass}>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-sm font-medium">Precio (ARS) *</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Stock *</span>
          <input
            type="number"
            min="0"
            step="1"
            value={stock}
            onChange={(e) => setStock(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">ISBN</span>
          <input type="text" value={isbn} onChange={(e) => setIsbn(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Género</span>
          <input type="text" value={genre} onChange={(e) => setGenre(e.target.value)} className={inputClass} />
        </label>
        {(validation || error) && (
          <p className="text-sm text-red-700 sm:col-span-2" role="alert">
            {validation ?? error}
          </p>
        )}
        <div className="flex justify-end gap-2 sm:col-span-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-sm border border-navy/20 px-4 py-2 text-sm font-medium text-ink hover:bg-navy/5"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-60"
          >
            {submitting ? "Guardando…" : initial ? "Guardar cambios" : "Crear libro"}
          </button>
        </div>
      </form>
    </Modal>
  );
}