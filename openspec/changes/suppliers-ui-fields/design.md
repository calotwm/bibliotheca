# Design: Suppliers UI Fields

## Technical Approach

UI-only edit of three frontend files under `frontend/src`. Remove all Editoriales artifacts from the Proveedores page (column, form input, `parseEditorials` helper, state, and payload field) and from `SupplierPayload`; add a Notas column; shorten headers to "Cond. venta" and "DTO". The backend is untouched — `SupplierRead` still returns `editorials: []`, so the read type `Supplier.editorials` stays and the UI ignores it.

## Architecture Decisions

| Decision | Option | Tradeoff | Chosen |
|---|---|---|---|
| Backend involvement | Change backend to drop `editorials` vs leave it | Dropping touches model/schemas/router + migration (out of scope, data risk); leaving it means UI ignores an unused field | Leave backend; UI ignores `editorials` |
| `Supplier.editorials` read type | Remove vs keep | Removing causes tsc/API-contract drift since backend still returns the field; keeping avoids type churn | Keep on `Supplier`, remove only from `SupplierPayload` |
| Column order | Append Notas vs insert before DTO | Requirement fixes exact order; insert Notas after Cond. venta | Nombre, Contacto, Teléfono, Email, Cond. venta, Notas, DTO, actions |
| Header naming | Full vs compact | Compact matches source data header "DTO."/"COND. VENTA" and reduces table width | "Cond. venta", "DTO" |
| Form label for discount | "DTO" vs keep "Descuento" | Spec requires "DTO" label | Rename to "DTO" |
| Test strategy | Edit existing `Proveedores.test.tsx` in place | Colocated per convention; extends rather than rewrites | Modify existing test file |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/Proveedores.tsx` | Modify | Remove `parseEditorials`, `editorials` state, Editoriales input + column, `editorials` from onSave payload; rename "Descuento" label to "DTO"; rename "Descuento"/"Condición de venta" headers to "DTO"/"Cond. venta"; add Notas column after Cond. venta |
| `frontend/src/lib/types.ts` | Modify | Remove `editorials?: string[]` from `SupplierPayload`; leave `Supplier.editorials` |
| `frontend/src/pages/Proveedores.test.tsx` | Modify | Remove Editoriales refs; rename `/Descuento/` queries to `/DTO/`; assert Cond. venta/Notas/DTO headers + cells + create/update payloads |

## Interfaces / Contracts

```ts
// types.ts — SupplierPayload (after)
name: string;
contact_name?: string | null;
phone?: string | null;
email?: string | null;
address?: string | null;
notes?: string | null;
discount?: string | null;
sale_condition?: string | null;
// editorials removed
```

## Testing Strategy

| Layer | What to test | Approach |
|-------|--------------|----------|
| Frontend unit | Renamed headers (Cond. venta, Notas, DTO) render, no Editoriales column, cell values, create/update payloads | Edit `Proveedores.test.tsx` (RTL + mocked `api/suppliers`) |
| Build | Strict tsc | `npm run build` |

## Threat Matrix

N/A — no routing, shell command, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. Pure React UI change.

## Migration / Rollout

No migration required. Data already in prod; no re-seed. Rollback: revert the single commit (UI-only, no data/API impact).

## Open Questions

None blocking.
