# Tasks: Inventario seller filter, observaciones sort/wrap, Distribuidoras rename

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~300–360 (backend ~80, frontend ~120, tests ~120, copy/rename ~40) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No (single PR per proposal forecast) |
| Suggested split | Single PR; if review friction grows, split into (a) backend + DataTable + Inventario + tests, (b) rename + frontend tests |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | All backend (service, router, tests) + frontend (constants, api, DataTable, Inventario) + rename + tests | PR 1 (single) | `cd backend; py -m pytest` + `cd frontend; npm run test` + `cd frontend; npm run build` | `GET /api/books?seller=Cande` against dev DB; toggle Inventario `Vendedora` | Single revert; additive params + opt-in props keep old behaviour on default |

## Phase 0: Prerequisites (already done)

- [x] 0.1 Local Node 26 `localStorage` global shim is installed in `frontend/src/test/setup.ts` so vitest+jsdom get a working `localStorage`. Evidence: 28 tests across `App`, `ProtectedRoute`, `Cuenta`, `Login`, `Precios` were broken on Node 26.7.0 before; baseline now green (`py -m pytest` 311 passed, 1 skipped; `npm run test` 98 passed across 14 files). Do not edit `setup.ts` again as part of this change.

## Phase 1: Backend — shared bucket service (RED → GREEN)

- [x] 1.1 RED: add `test_seller_bucket_returns_correct_bucket` and `test_seller_bucket_agrees_with_compute_shares` to `backend/tests/test_seller_split.py`. Cover `Juli`, `Cande`, `Juli y Cande`, `Cande y Juli`, `""`, `None`, `En consignación 30%`. Verify: `cd backend; py -m pytest tests/test_seller_split.py -v` FAILS with `ImportError`/`AttributeError`.
- [x] 1.2 GREEN: add `seller_bucket(observaciones)` and `seller_filter_condition(bucket)` to `backend/app/services/seller_split.py`; rewrite `compute_shares` to derive from `seller_bucket`. Verify: `cd backend; py -m pytest tests/test_seller_split.py tests/test_earnings.py -v` PASSES (existing byte-identical Decimal outputs preserved).

## Phase 2: Backend — router filter + sort (RED → GREEN)

- [x] 2.1 RED: in `backend/tests/test_books.py` add: `test_list_books_seller_filter_juli_includes_blank_and_null`, `test_list_books_seller_filter_cande_excludes_juli_only`, `test_list_books_seller_filter_joint_includes_reversed_text`, `test_list_books_seller_invalid_returns_400`, `test_list_books_seller_composes_with_category_stock_and_pagination`, `test_list_books_sort_by_observaciones_case_insensitive_with_nulls_grouped`, `test_list_books_sort_by_observaciones_desc_reverses_order`, `test_list_books_sort_by_observaciones_in_invalid_list_returns_400`. Verify the file FAILS to collect (`NameError`/`ImportError`) before changes.
- [x] 2.2 GREEN: in `backend/app/routers/books.py`, add `seller: str | None = None` to `list_books`, define `SELLER_BUCKETS = ("Juli", "Cande", "Juli y Cande")`, reject invalid with HTTP 400 (mirror lines 91-100), apply `seller_filter_condition(...)` via `query.where(...)`. Extend `SORT_FIELDS` with `"observaciones"`; extend `_sort_expression` to return `func.lower(func.coalesce(getattr(Book, sort_by), ""))` for the existing `title/author/editorial/observaciones` branch. Verify: `cd backend; py -m pytest tests/test_books.py tests/test_seller_split.py tests/test_earnings.py -v` PASSES.

## Phase 3: Frontend — api + constants

- [x] 3.1 In `frontend/src/lib/constants.ts`, add `SELLER_JULI = "Juli"`, `SELLER_CANDE = "Cande"`, `SELLER_JOINT = "Juli y Cande"`, and `SELLER_FILTERS` with four options (empty `""` = `Todas`). Verify: `cd frontend; npx tsc -b --noEmit` clean.
- [x] 3.2 In `frontend/src/api/books.ts`, add `seller?: string | null` to `BookFilters` and forward via `URLSearchParams` in `listBooks`. Verify: `cd frontend; npx tsc -b --noEmit` clean.

## Phase 4: Frontend — DataTable opt-in props (RED → GREEN)

- [x] 4.1 RED: create `frontend/src/components/DataTable.test.tsx` with: `test_default_renders_identical_dom_to_today` (no `table-fixed`/`whitespace-normal` without props); `test_fixed_layout_adds_table_fixed_and_propagates_className_to_th`; `test_wrap_text_adds_wrapping_classes_to_td`. Verify: `cd frontend; npm run test -- DataTable` FAILS to collect before changes.
- [x] 4.2 GREEN: in `frontend/src/components/DataTable.tsx`, add `fixedLayout?: boolean` and `wrapText?: boolean` props (default `false`); apply `column.className ?? ""` to `<th>`; conditionally add `table-fixed` to `<table>` when `fixedLayout`; conditionally add `whitespace-normal break-words` to `<td>` when `wrapText`. Verify: `cd frontend; npm run test -- DataTable` PASSES and full `cd frontend; npm run test` still passes (Precios/Dashboard/etc. unchanged).

## Phase 5: Frontend — Inventario UI (RED → GREEN)

- [x] 5.1 RED: extend `frontend/src/pages/Inventario.test.tsx` with: `test_renders_vendedora_select_with_four_options`, `test_selecting_vendedora_sends_seller_to_list_books_and_resets_page`, `test_observaciones_header_sorts_asc_then_desc`, `test_inventario_data_table_uses_fixed_layout_and_wrap_text`. Verify the specific tests FAIL before changes.
- [x] 5.2 GREEN: in `frontend/src/pages/Inventario.tsx`, add `seller` state mirroring the `Categoría` markup (same `inputClass`, same `resetPageOnFilterChange` call); include `seller` in the React Query key and `listBooks({ seller, ... })` args; mark `observaciones` column `sortable: true, sortKey: "observaciones"`; add narrow `className: "w-XX"` per column; render `<DataTable ... fixedLayout wrapText />`. Verify: `cd frontend; npm run test -- Inventario` PASSES and `cd frontend; npm run build` (tsc strict) clean.

## Phase 6: Frontend — Distribuidoras rename (copy + tests)

- [x] 6.1 `frontend/src/components/Sidebar.tsx` line 32: `label: "Proveedores"` → `"Distribuidoras"`.
- [x] 6.2 `frontend/src/components/Layout.tsx` line 11: `"/proveedores": "Proveedores"` → `"/proveedores": "Distribuidoras"`.
- [x] 6.3 `frontend/src/pages/Proveedores.tsx` lines 54, 106, 138, 203, 210, 218, 238, 239: replace user-visible Spanish strings with `Distribuidora(s)` / `distribuidora(s)` wording.
- [x] 6.4 `frontend/src/components/Sidebar.test.tsx` line 31: `expect(screen.getByText("Proveedores"))` → `"Distribuidoras"`.
- [x] 6.5 `frontend/src/App.test.tsx` lines 145-146: `getByText("Proveedores")` and `findByRole("heading", { name: "Proveedores" })` → `"Distribuidoras"`.
- [x] 6.6 `frontend/src/pages/Proveedores.test.tsx`: `screen.getByRole("button", { name: "Nuevo proveedor" })` → `"Nueva distribuidora"`; `name: "Crear proveedor"` → `"Crear distribuidora"`; rename other wording references that the page copy changed.
- [x] 6.7 Guard scan (checklist, verified manually before marking done): `rg -n "\b[Pp]roveedor(es)?\b" frontend/src` must return NO matches except for the route `/proveedores` in `App.tsx` and the JSX component name `Proveedores` (file and component, both unchanged). The `Supplier` type, the `proveedoresApi` API surface, and any test fixture strings stay. If any user-visible Spanish string remains, fix and re-run. Verify: `cd frontend; npm run test` and `cd frontend; npm run build` both PASS.

## Phase 7: Verification

- [x] 7.1 `cd backend; py -m pytest` — expect 311 + new tests PASSED, 1 skipped. (RESULT: 333 passed, 1 skipped; +22 over baseline.)
- [x] 7.2 `cd frontend; npm run test` — expect 98 + new tests PASSED across the existing 14 + new DataTable file. (RESULT: 15 files, 105 tests passed; +1 file / +7 tests over baseline.)
- [x] 7.3 `cd frontend; npm run build` — tsc strict + Vite build clean. (RESULT: built in 345ms; no type errors.)
- [x] 7.4 Manual checklist (code review; runtime harness deferred to sdd-verify): the seller filter, observaciones sort/wrap, and Distribuidoras copy wiring are verified by the passing test assertions; the rest of the smoke flow is unchanged and covered by the unchanged routing tests.