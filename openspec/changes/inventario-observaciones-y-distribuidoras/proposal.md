# Proposal: inventario seller buckets, observaciones filter/sort, wrap, supplier rename

## Intent

Four store-owner fixes for Inventario: filter and sort by seller (Juli / Cande / Juli y Cande), wrap long `observaciones`, rename Spanish `Proveedores` → `Distribuidoras` (copy only).

## Scope

### In Scope

- `seller=Juli|Cande|Juli%20y%20Cande` on `GET /api/books`, same rule as `compute_shares`; blank/None → `Juli`.
- `observaciones` joins `SORT_FIELDS`, NULL-stable (`func.lower(func.coalesce(..., ''))`) on PG and SQLite.
- `<select>` labelled `Vendedora` mirroring `Categoría`.
- Optional `wrapText`/`fixedLayout` on `DataTable`; `column.className` reaches `<th>`; Inventario opts in.
- Copy: `Proveedores` → `Distribuidoras`; `proveedora` → `distribuidora`; matching tests.

### Out of Scope

DB migration, code renames, multi-select seller filter, `observaciones` free-text search, pagination, `compute_shares` rework.

## Capabilities

### New Capabilities

- `inventory-seller-filter`: seller bucketing + `observaciones` filter/sort + Inventario wrap.
- `supplier-terminology`: Spanish UI copy reads `Distribuidoras / distribuidora`.

### Modified Capabilities

None. `supplier-distributors` keeps its requirements; only the new capability changes wording.

## Approach

Reuse `compute_shares`: lowercase, test `cande`/`juli`, three buckets. Extract `seller_bucket(text)` + WHERE helpers into `seller_split.py`; router + shares share them. `DataTable` adds optional boolean props + className on `<th>`; defaults unchanged. Rename is copy-only; code rename deferred.

## Affected Areas

- `backend/app/routers/books.py` — `seller` param, `SORT_FIELDS`, filter + sort.
- `backend/app/services/seller_split.py` — `seller_bucket` + helpers (shared).
- `backend/app/schemas/book.py` — `seller: Literal[...]`.
- `backend/tests/test_books.py`, `test_seller_split.py` — filter/sort/bucket incl. blank→`Juli`.
- `frontend/src/components/DataTable.tsx` — optional `fixedLayout`/`wrapText`; className on `<th>`.
- `frontend/src/pages/Inventario.tsx` — `Vendedora`, sortable `observaciones`, wrap.
- `frontend/src/api/books.ts` — `BookFilters.seller`; `listBooks` forwards it.
- `frontend/src/components/{Sidebar,Layout}.tsx` — label/title → `Distribuidoras`.
- `frontend/src/pages/Proveedores.tsx` — heading + strings → `Distribuidoras / distribuidora`.
- `frontend/src/pages/{Inventario,Proveedores,Sidebar,App}.test.tsx` — rename + filter/sort/wrap coverage.

## Risks

DataTable opt-in breaks Precios (Low, props default to today; Precios test regresses). NULL/sort parity PG vs SQLite (Med, coalesce `''` lands empties together on both; integration covers both). Bucket parity with `compute_shares` (Med, shared helpers + paired tests pin the three buckets). Stale `Proveedores` strings (Low, grep gate + App/Sidebar/Proveedores tests updated together).

## Rollback Plan

Single revert on `main`. Drop `seller`; remove `observaciones` from `SORT_FIELDS`/column; drop `wrapText fixedLayout`; revert strings+assertions. No DB migration; no API removal breaks data.

## Dependencies

`compute_shares` lives in `seller_split.py` and `lib/shares.ts`. PR → `main` on `calotwm/bibliotheca`; Railway auto-redeploys.

## Review Workload Forecast

~280–360 LOC across ~14 files, under the 400-line budget as one work unit. If the bucket service grows, split it; cap DataTable + rename at ~120 LOC.

## Success Criteria

- `seller` returns right buckets incl. blank→`Juli`; `sort_by=observaciones` orders by lower(coalesce) with empties together, on both engines.
- Inventario renders `Vendedora`; `observaciones` header sorts; long text wraps in-cell.
- Sidebar + `/proveedores` heading read `Distribuidoras`; tests assert the new strings.
- `py -m pytest` (cwd `backend`), `npm run test`, `npm run build` (cwd `frontend`) pass.
