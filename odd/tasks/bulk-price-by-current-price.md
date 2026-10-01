# Bulk price update by current price

## Objective
Let the admin raise (or set) the price of every book that currently has the same price, in one operation, from the existing "Precios" page.

## Problem / Why
The client must edit books one by one when they want to change all books priced e.g. $25.000. The bulk update subsystem (`editorial_bulk.py`, `editorial_service.preview_bulk/apply_bulk`, `Precios.tsx`) only filters by editorial, author, or category.

## Scope
- Backend: optional `price_equals` filter in `BulkUpdateRequest`, applied in preview and apply (exact `Decimal` match on `Numeric(12,2)`).
- Backend: admin-only endpoint returning distinct current prices with book counts.
- Frontend: "Precio actual" selector in `Precios.tsx` listing every distinct price with its count, combinable with existing filters.
- Out of scope: row checkboxes in `Inventario.tsx`, price history table.

## Constraints
- Reuse existing preview-before-apply, admin-only, rate-limit, and audit-log machinery.
- English code; Spanish UI copy.
- TDD: strict (source: `openspec/config.yaml` `strict_tdd: true`). Runners: backend `py -m pytest` (cwd `backend`), frontend `npm run test` and `npm run build` (cwd `frontend`).
- Delivery strategy: `ask-on-risk`, budget ~400 authored lines. Forecast: ~250-350 lines.

## Tasks
- [x] T1 Backend: `price_equals` filter + distinct-prices endpoint, with pytest tests. Route: delegated direct (writer trigger: schema + service + router + tests).
- [x] T2 Frontend: API client + "Precio actual" selector in `Precios.tsx`, with vitest tests. Route: delegated direct (writer trigger: api + page + tests).

## Acceptance criteria
- Preview with `price_equals=25000` returns only books priced exactly 25000 (combined with other filters via AND).
- Apply with `price_percent` or `price_set` changes only those books and writes audit entries.
- Distinct-prices endpoint lists every current price with its count, admin-only.
- The selector shows every price as "$25.000 (14 libros)" and filters the preview.
- All backend and frontend tests pass; `npm run build` passes.

## Progress / Evidence
- T1: commit `5912e77` (4 files, +151/-7). RED observed: 5 new tests failing (422/404). GREEN: `py -m pytest` 340 passed, 1 skipped (re-run by parent). Review: high risk, user declined for this candidate.
  - API: `BulkUpdateRequest.price_equals` (decimal string, > 0, valid alone or AND with other filters). `GET /api/editorial-bulk-update/price-groups` (admin) returns `[{"price": "25000.00", "count": 14}]`, ascending, active books only.
- T2: commit `4e4a50d` (4 files, +111/-5). RED observed: 3 tests failing ("Unable to find a label with the text of: Precio actual"). GREEN: `npm run test` 117 passed (re-run by parent); `npm run build` passed (writer report). Review: medium risk, `under_budget`, no review due.
- Engram mirror: pending (`.engram/config.json` missing `project_name`).

## Next step
Manual check in the running app, then push + PR (user decision).
