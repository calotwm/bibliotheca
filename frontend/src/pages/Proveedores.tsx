import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import * as suppliersApi from "../api/suppliers";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { DataTable } from "../components/DataTable";
import { Modal } from "../components/Modal";
import { PencilIcon, PlusIcon, TrashIcon } from "../components/icons";
import type { Column } from "../components/DataTable";
import type { Supplier, SupplierPayload } from "../lib/types";

function parseEditorials(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

interface SupplierFormProps {
  initial: Supplier | null;
  submitting: boolean;
  error: string | null;
  onSave: (payload: SupplierPayload) => void;
  onCancel: () => void;
}

function SupplierForm({ initial, submitting, error, onSave, onCancel }: SupplierFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [contactName, setContactName] = useState(initial?.contact_name ?? "");
  const [phone, setPhone] = useState(initial?.phone ?? "");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [address, setAddress] = useState(initial?.address ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [discount, setDiscount] = useState(initial?.discount ?? "");
  const [saleCondition, setSaleCondition] = useState(initial?.sale_condition ?? "");
  const [editorials, setEditorials] = useState((initial?.editorials ?? []).join(", "));
  const [validation, setValidation] = useState<string | null>(null);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setValidation(null);
    if (!name.trim()) {
      setValidation("El nombre es obligatorio.");
      return;
    }
    onSave({
      name: name.trim(),
      contact_name: contactName.trim() || null,
      phone: phone.trim() || null,
      email: email.trim() || null,
      address: address.trim() || null,
      notes: notes.trim() || null,
      discount: discount.trim() || null,
      sale_condition: saleCondition.trim() || null,
      editorials: parseEditorials(editorials),
    });
  }

  const inputClass =
    "mt-1 min-h-11 w-full rounded-sm border border-navy/20 bg-paper px-3 py-2 text-sm outline-none focus:border-navy";

  return (
    <Modal title={initial ? "Editar proveedor" : "Nuevo proveedor"} onClose={onCancel}>
      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2" noValidate>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium">Nombre *</span>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Contacto</span>
          <input type="text" value={contactName} onChange={(e) => setContactName(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Teléfono</span>
          <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Email</span>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Descuento</span>
          <input type="text" value={discount} onChange={(e) => setDiscount(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Condición de venta</span>
          <input type="text" value={saleCondition} onChange={(e) => setSaleCondition(e.target.value)} className={inputClass} />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Dirección</span>
          <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} className={inputClass} />
        </label>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium">Editoriales (separadas por coma)</span>
          <input type="text" value={editorials} onChange={(e) => setEditorials(e.target.value)} className={inputClass} />
        </label>
        <label className="block sm:col-span-2">
          <span className="text-sm font-medium">Notas</span>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} className={inputClass} />
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
            className="min-h-10 rounded-sm border border-navy/20 px-4 py-2 text-sm font-medium text-ink hover:bg-navy/5"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="min-h-10 rounded-sm bg-navy px-4 py-2 text-sm font-semibold text-cream hover:bg-navy-light disabled:opacity-60"
          >
            {submitting ? "Guardando…" : initial ? "Guardar cambios" : "Crear proveedor"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function Proveedores() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [deleting, setDeleting] = useState<Supplier | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const { data: suppliers = [], isLoading, isError, error } = useQuery({
    queryKey: ["suppliers"],
    queryFn: suppliersApi.listSuppliers,
  });

  const saveMutation = useMutation({
    mutationFn: (payload: SupplierPayload) =>
      editing
        ? suppliersApi.updateSupplier(editing.id, payload)
        : suppliersApi.createSupplier(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      setShowForm(false);
      setEditing(null);
      setFormError(null);
    },
    onError: (err: unknown) => {
      setFormError(err instanceof Error ? err.message : "No se pudo guardar el proveedor.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => suppliersApi.deleteSupplier(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      setDeleting(null);
    },
  });

  const columns: Column<Supplier>[] = [
    { key: "name", header: "Nombre", render: (row) => <span className="font-medium">{row.name}</span> },
    { key: "contact_name", header: "Contacto", render: (row) => row.contact_name ?? "—" },
    { key: "phone", header: "Teléfono", render: (row) => row.phone ?? "—" },
    { key: "email", header: "Email", render: (row) => row.email ?? "—" },
    { key: "discount", header: "Descuento", render: (row) => row.discount ?? "—" },
    { key: "sale_condition", header: "Condición de venta", render: (row) => row.sale_condition ?? "—" },
    {
      key: "editorials",
      header: "Editoriales",
      render: (row) =>
        row.editorials.length > 0 ? (
          <span className="text-xs text-ink-soft">{row.editorials.join(", ")}</span>
        ) : (
          "—"
        ),
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <div className="flex justify-end gap-1">
          <button
            type="button"
            onClick={() => {
              setEditing(row);
              setFormError(null);
              setShowForm(true);
            }}
            className="rounded-sm p-3 text-ink-soft hover:bg-navy/5 hover:text-navy lg:p-1.5"
            aria-label={`Editar ${row.name}`}
            title="Editar"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => setDeleting(row)}
            className="rounded-sm p-3 text-ink-soft hover:bg-red-50 hover:text-red-700 lg:p-1.5"
            aria-label={`Eliminar ${row.name}`}
            title="Eliminar"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
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
          Nuevo proveedor
        </button>
      </div>

      {isLoading && <p className="text-sm text-ink-soft">Cargando…</p>}
      {isError && (
        <p className="text-sm text-red-700">
          {error instanceof Error ? error.message : "No se pudieron cargar los proveedores."}
        </p>
      )}
      {!isLoading && !isError && (
        <DataTable
          columns={columns}
          rows={suppliers}
          getRowKey={(row) => row.id}
          emptyMessage="No hay proveedores registrados."
        />
      )}

      {showForm && (
        <SupplierForm
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
          title="Eliminar proveedor"
          message={`¿Desea eliminar el proveedor "${deleting.name}"? Esta acción no se puede deshacer.`}
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