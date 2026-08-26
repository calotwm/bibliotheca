# Tasks: Suppliers UI Fields

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~60–100 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (3 files) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | UI: types + Proveedores + test | PR 1 (single) | `cd frontend; npm run test -- Proveedores` + `npm run build` | Open Proveedores page; create/edit supplier; verify columns and payloads | Revert commit; UI-only, no data impact |

## Phase 1: Type Contract

- [x] 1.1 Remove `editorials?: string[]` from `SupplierPayload` in `frontend/src/lib/types.ts`; keep `Supplier.editorials` (backend still returns it) (~1 line)

## Phase 2: Proveedores UI

- [x] 2.1 Remove `parseEditorials` helper and `editorials` state from `SupplierForm` in `frontend/src/pages/Proveedores.tsx` (~6 lines)
- [x] 2.2 Remove the "Editoriales (separadas por coma)" form input and `editorials` from the onSave payload in `handleSubmit` (~6 lines)
- [x] 2.3 Rename the "Descuento" form input label to "DTO"; keep "Condición de venta" and "Notas" labels (~1 line)
- [x] 2.4 Replace the "Descuento"/"Condición de venta" column headers with "DTO"/"Cond. venta" and add a "Notas" column (`row.notes ?? "—"`) after the Cond. venta column; remove the Editoriales column, preserving the exact order Nombre, Contacto, Teléfono, Email, Cond. venta, Notas, DTO, actions (~10 lines)

## Phase 3: Frontend Tests

- [x] 3.1 In `frontend/src/pages/Proveedores.test.tsx`, remove any Editoriales references and rename `screen.getByLabelText(/Descuento/)` and header queries to `/DTO/`; assert "Cond. venta", "Notas", "DTO" column headers render (~15 lines)
- [x] 3.2 Update cell-value assertions to the fixture (e.g. `notes`, `discount`, `sale_condition` values) (~5 lines)
- [x] 3.3 Assert create and update payloads contain `sale_condition`, `notes`, `discount` and exclude `editorials` (~8 lines)

## Phase 4: Verification

- [x] 4.1 Grep `editorials` under `frontend/src` to confirm only the read type reference remains (~0 lines)
- [x] 4.2 Run `cd frontend; npm run test` — Proveedores tests pass (~0 lines)
- [x] 4.3 Run `cd frontend; npm run build` — tsc strict passes (~0 lines)