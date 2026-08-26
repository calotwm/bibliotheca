# Proposal: Suppliers UI Fields

## Intent

The Proveedores section still shows an "Editoriales" column and form input, but the field was never populated (`editorials: []`) and is meaningless to users. Clean up the UI: drop Editoriales, add a Notas column, and use compact column headers ("Cond. venta", "DTO") so the table reads cleanly.

## Scope

### In Scope
- Remove the Editoriales column, the "Editoriales (separadas por coma)" form input, the `parseEditorials` helper, and `editorials` from `SupplierPayload` and the form's onSave payload.
- Rename table headers: "Condición de venta" → "Cond. venta", "Descuento" → "DTO"; add a "Notas" column (`supplier.notes`). Final column order: Nombre, Contacto, Teléfono, Email, Cond. venta, Notas, DTO, then actions.
- Rename the form "Descuento" input label to "DTO"; keep "Condición de venta" and "Notas" labels.
- Update `frontend/src/pages/Proveedores.test.tsx` for headers, cell values, and create/update payloads.

### Out of Scope
- Backend changes: `SupplierRead` still returns `editorials: []`; the UI simply ignores it.
- Re-seeding distributors (data already in production).
- Data migration or schema changes.
- Numeric discount computation or import UI.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `supplier-distributors`: the Proveedores UI surface requirement changes (Editoriales removed, Notas column added, headers renamed, payload constraints).

## Approach

UI-only edit of three frontend files. Remove Editoriales artifacts from `Proveedores.tsx` and from `SupplierPayload`; keep `Supplier.editorials` on the read type because the backend still returns it (avoids tsc/API-contract drift). Update the colocated test to the new surface.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/pages/Proveedores.tsx` | Modified | Remove Editoriales column/input/helper/state/payload field; add Notas column; rename headers and "Descuento" label |
| `frontend/src/lib/types.ts` | Modified | Remove `editorials?: string[]` from `SupplierPayload` |
| `frontend/src/pages/Proveedores.test.tsx` | Modified | Header, cell, and payload assertions |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Stray Editoriales reference breaks build/tests | Low | Grep `editorials` in `frontend/src`; `npm run build` gate |
| Payload type contract drift | Low | Only `SupplierPayload` changes; `Supplier` read type untouched |

## Rollback Plan

Revert the single commit. UI-only change with no schema, data, or API impact.

## Dependencies

- None. Data already in prod; no re-seed.

## Success Criteria

- [ ] Proveedores table shows exactly Nombre, Contacto, Teléfono, Email, Cond. venta, Notas, DTO + actions; no Editoriales column.
- [ ] Form has no Editoriales input; "Descuento" label reads "DTO".
- [ ] Create/update payloads include `sale_condition`, `notes`, `discount` and exclude `editorials`.
- [ ] `npm run test` and `npm run build` pass.
