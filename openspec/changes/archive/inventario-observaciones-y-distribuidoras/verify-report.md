```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:placeholder-archive-time-recompute
verdict: pass
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 18/18
test_command: "py -m pytest (cwd backend) && npm run test (cwd frontend)"
test_exit_code: 0
test_output_hash: sha256:placeholder-pytest
build_command: "npm run build (cwd frontend)"
build_exit_code: 0
build_output_hash: sha256:placeholder-build
```

## Verification Report

**Change**: inventario-observaciones-y-distribuidoras
**Version**: 1.0 (two new capabilities: `inventory-seller-filter`, `supplier-terminology`)
**Mode**: Strict TDD

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 27 (Phase 0.1 + Phase 1.1–1.2 + Phase 2.1–2.2 + Phase 3.1–3.2 + Phase 4.1–4.2 + Phase 5.1–5.2 + Phase 6.1–6.7 + Phase 7.1–7.4) |
| Tasks complete | 27 |
| Tasks incomplete | 0 |

All tasks checked `[x]` in `tasks.md`. Every Phase 0–7 box ticked, including the Node 26 `localStorage` shim prerequisite and the final guard-scan checklist (6.7).

### Capability Spec Counts
| Capability | Requirements | Scenarios |
|------------|--------------|-----------|
| `inventory-seller-filter` | 6 | 14 |
| `supplier-terminology` | 4 | 4 |
| **Total** | **10** | **18** |

### Build & Tests Execution

**Build**: ✅ Passed — `npm run build` (cwd `frontend`) → `tsc -b` strict + vite build, exit 0
```text
dist/assets/index-Nb1g2mGZ.js   349.36 kB │ gzip: 101.39 kB
built in 345ms
```

**Tests**: ✅ Backend 333 passed / 0 failed; Frontend 105 passed / 0 failed
```text
BACKEND  — py -m pytest (cwd backend) → 333 passed, 1 skipped, 35 warnings in 70.51s — exit 0
           (baseline before this change: 311 passed, 1 skipped; +22 from this change)
FRONTEND — npm run test (cwd frontend) → Test Files 15 passed (15); Tests 105 passed (105) — exit 0
           (baseline before this change: 14 files / 98 tests; +1 file (DataTable.test.tsx) / +7 tests from this change)
```

**Migration (runtime harness)**: ➖ N/A — no DB migration was created; `observaciones` already exists at `backend/app/models/book.py` line 39 (`String(200)`, nullable). Verified at design + apply time.

**Seed (runtime harness)**: ➖ N/A — no seed touched.

**Coverage**: ➖ Not available — `pytest_cov` not installed; vitest has no coverage provider configured. Same as prior cycles; not a failure.

**Production smoke (final state)**: ✅ Bundle hash parity proves the new code is live.
```text
GET /health                       → 200 {"status":"ok"}
GET /                             → 200, SPA index served
GET /assets/index-Nb1g2mGZ.js     → 200, 349369 bytes  (same hash as local build)
GET /inventario                   → 200, id="root" present (SPA deep-link works)
GET /api/books (no auth)          → 401 (auth intact)
GitHub commit status for f34df0e  → state=success, description "Success - libreria.up.railway.app"
Railway deployment                → id 6487493950, env "bibliotheca / production", sha f34df0e
```

### Spec Compliance Matrix

#### inventory-seller-filter
| Requirement | Scenario | Test / Evidence | Result |
|-------------|----------|-----------------|--------|
| Seller bucket filter on `GET /api/books` | Filter by Juli returns only Juli-bucket books | `backend/tests/test_books.py > test_list_books_seller_filter_juli_includes_blank_and_null` (HUD asserts all buckets; NULL/blank land in Juli) | ✅ COMPLIANT |
| Seller bucket filter on `GET /api/books` | Filter by Cande excludes Juli and joint books | `test_list_books_seller_filter_cande_excludes_juli_only` | ✅ COMPLIANT |
| Seller bucket filter on `GET /api/books` | Filter by Juli y Cande requires both names | `test_list_books_seller_filter_joint_includes_reversed_text` | ✅ COMPLIANT |
| Seller bucket filter on `GET /api/books` | Blank or NULL observaciones lands in Juli | `test_list_books_seller_filter_juli_includes_blank_and_null` | ✅ COMPLIANT |
| Seller bucket filter on `GET /api/books` | Invalid seller value rejected with HTTP 400 | `test_list_books_seller_invalid_returns_400` | ✅ COMPLIANT |
| Seller bucket filter on `GET /api/books` | Seller filter composes with existing filters and pagination | `test_list_books_seller_composes_with_category_stock_and_pagination` | ✅ COMPLIANT |
| Shared bucket classification with compute_shares | Bucket helper agrees with compute_shares | `backend/tests/test_seller_split.py > test_seller_bucket_returns_correct_bucket` (7 cases) + `test_seller_bucket_agrees_with_compute_shares` (7 cases); `backend/tests/test_earnings.py` unchanged — byte-identical Decimals 85/15, 0/100, 50/50 | ✅ COMPLIANT |
| observaciones joins SORT_FIELDS | sort_by=observaciones is accepted | `test_list_books_sort_by_observaciones_case_insensitive_with_nulls_grouped` | ✅ COMPLIANT |
| observaciones joins SORT_FIELDS | Sort orders case-insensitively with NULLs grouped | `test_list_books_sort_by_observaciones_case_insensitive_with_nulls_grouped` + `..._desc_reverses_order` | ✅ COMPLIANT |
| Inventario Vendedora select | Vendedora select renders four options | `frontend/src/pages/Inventario.test.tsx > test_renders_vendedora_select_with_four_options` | ✅ COMPLIANT |
| Inventario Vendedora select | Selecting a value sends seller to listBooks | `Inventario.test.tsx > test_selecting_vendedora_sends_seller_to_list_books_and_resets_page` | ✅ COMPLIANT |
| Inventario observaciones sortable column | observaciones header toggles sort direction | `Inventario.test.tsx > test_observaciones_header_sorts_asc_then_desc` | ✅ COMPLIANT |
| DataTable opt-in fixed layout and cell wrapping | Inventario opts in to fixed layout + wrap | `Inventario.test.tsx > test_inventario_data_table_uses_fixed_layout_and_wrap_text` | ✅ COMPLIANT |
| DataTable opt-in fixed layout and cell wrapping | Precios behavior is unchanged | `frontend/src/pages/Precios.test.tsx` unmodified; full suite green | ✅ COMPLIANT |

#### supplier-terminology
| Requirement | Scenario | Test / Evidence | Result |
|-------------|----------|-----------------|--------|
| Sidebar label reads Distribuidoras | Sidebar shows Distribuidoras | `frontend/src/components/Sidebar.test.tsx` line 31: `expect(screen.getByText("Distribuidoras"))` | ✅ COMPLIANT |
| Page title reads Distribuidoras | Page header reads Distribuidoras | `frontend/src/App.test.tsx` lines 145-146: `findByRole("heading", { name: "Distribuidoras" })` | ✅ COMPLIANT |
| Proveedores page copy reads Distribuidoras / distribuidora | All page copy reflects the rename | `frontend/src/pages/Proveedores.test.tsx`: `getByRole("button", { name: "Nueva distribuidora" })` + `name: "Crear distribuidora"`; guard scan (`rg` checklist in `apply-progress.md` §6.7) returns only the 6 expected matches (route paths and JSX component name); no user-visible Spanish `Proveedor/proveedor` strings remain | ✅ COMPLIANT |
| Rename boundary | No code, route, type, file, or DB identifier is renamed | `App.tsx` still mounts `<Proveedores />` on `<Route path="proveedores" ...>`; `Supplier` / `SupplierPayload` / `SupplierForm` / `suppliersApi` identifiers unchanged; URL `/proveedores` unchanged; no Alembic revision | ✅ COMPLIANT |

**Compliance summary**: 18/18 scenarios compliant.

### Correctness (Static Evidence)
| Item | Status | Notes |
|------|--------|-------|
| `seller_bucket` shared helper | ✅ Implemented | `backend/app/services/seller_split.py`: `seller_bucket(text) -> SellerBucket` (Literal `Juli` / `Cande` / `Juli y Cande`); `seller_filter_condition(bucket)` returns `ColumnElement[bool]` |
| `compute_shares` rewired via bucket | ✅ Implemented | `backend/app/services/seller_split.py`: `_BUCKET_SHARES` table; byte-identical Decimals preserved (`50.00`/`50.00`, `0.00`/`100.00`, `85.00`/`15.00`); `test_earnings.py` unmodified |
| Router `seller` param | ✅ Implemented | `backend/app/routers/books.py`: `seller: str \| None = None`; `SELLER_BUCKETS = ("Juli", "Cande", "Juli y Cande")`; HTTP 400 on invalid mirroring `sort_by` validation (lines 91-100); `query.where(seller_filter_condition(seller))` |
| Sort expression | ✅ Implemented | `_sort_expression` extended: existing branch `title/author/editorial/observaciones` returns `func.lower(func.coalesce(getattr(Book, sort_by), ""))` |
| Frontend constants + API | ✅ Implemented | `frontend/src/lib/constants.ts`: `SELLER_JULI/CANDE/JOINT`, `SELLER_FILTERS` (4 options, empty=Todas); `frontend/src/api/books.ts`: `BookFilters.seller?: string \| null`, forwarded via `URLSearchParams` |
| DataTable opt-in props | ✅ Implemented | `frontend/src/components/DataTable.tsx`: `fixedLayout?` / `wrapText?` (default `false`); `<th>` carries `column.className ?? ""`; conditional `table-fixed` and `whitespace-normal break-words` |
| Inventario UI | ✅ Implemented | `frontend/src/pages/Inventario.tsx`: `seller` state + `Vendedora` `<select>` mirroring `Categoría`; `seller` in React Query key + `listBooks` args; `observaciones` `sortable: true, sortKey: "observaciones"`; per-column `className: "w-XX"`; `<DataTable ... fixedLayout wrapText />` |
| Rename copy | ✅ Implemented | `Sidebar.tsx` L32, `Layout.tsx` L11, `Proveedores.tsx` (9 strings) → `Distribuidoras / distribuidora` |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Shared bucket helper (no rule duplication) | ✅ Yes | `seller_bucket` in `seller_split.py` is the single source of truth; `compute_shares` derives from it; router filter derives from it |
| `func.lower(func.coalesce(..., ""))` for `observaciones` | ✅ Yes | NULL-stable on both PG and SQLite |
| `seller` filter runs in SQL via `query.where(...)` | ✅ Yes | Composition with category/stock/pagination proven in `test_list_books_seller_composes_with_category_stock_and_pagination` |
| `DataTable` opt-in: two booleans default `false` | ✅ Yes | `Precios` suite green with no changes; DOM identical when props omitted |
| `column.className` always propagates to `<th>` | ✅ Yes | Even without `fixedLayout` (gating couples unrelated concerns) |
| Rename copy-only (no code rename) | ✅ Yes | Route `/proveedores`, `Supplier` type, `Proveedores.tsx` file/component, API paths, DB identifiers all untouched |
| No DB migration | ✅ Yes | `observaciones` already existed |
| Single PR / under 400-line budget | ✅ Yes | Four commits on `main`; per-commit diffs within budget |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | TDD Cycle Evidence table in `apply-progress.md` |
| All tasks have tests | ✅ | Phase 1 + 2 backend; Phase 4 + 5 frontend; Phase 6 (rename) covered by 6.4–6.6 + 6.7 guard scan |
| RED confirmed (tests fail without impl) | ✅ | Phase 1.1 `ImportError` collecting; Phase 2.1 collection failed; Phase 4.1 `fixedLayout`/`wrapText` tests failed; Phase 5.1 four new tests failed |
| GREEN confirmed (tests pass) | ✅ | Backend 333 + Frontend 105 + build exit 0; one non-breaking test-method swap (2 pre-existing tests reworked to use `document.querySelectorAll('td')/th`) because new `<option>` text introduced literal `Juli`/`Juli y Cande` strings |
| Triangulation adequate | ✅ | 7 parametrized cases for `seller_bucket`; 8 cases for `seller`/`observaciones`; per-bucket filter + invalid 400 + composition; 4 Inventario behaviour tests + 3 DataTable opt-in tests |
| Safety Net for modified files | ✅ | `test_seller_split.py` and `test_books.py` modified with pre-existing safety nets; `DataTable.test.tsx` genuinely new |

**TDD Compliance**: 6/6 checks fully passed.

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit (backend) | 14 new (parametrized across 7+7 cases) | 1 modified (`test_seller_split.py`) | pytest |
| Integration (backend) | 8 new | 1 modified (`test_books.py`) | httpx ASGITransport + in-memory SQLite + dependency_overrides |
| Unit (frontend) | 3 new | 1 new (`DataTable.test.tsx`) | vitest + RTL + jsdom |
| Integration (frontend) | 4 new | 1 modified (`Inventario.test.tsx`) | vitest + RTL + user-event + jsdom + React Query providers |
| Frontend copy assertions | 3 new sites + 1 guard scan | `Sidebar.test.tsx` / `App.test.tsx` / `Proveedores.test.tsx` | vitest + RTL |
| **Total** | **29 new** | **6 (4 modified + 2 new files: DataTable.test.tsx + 2 in-place test rewrites)** | |

### Assertion Quality
Backend assertions are value-based over real HTTP responses (status, payload, list partition). Frontend asserts rendered DOM text, exact query args, and `className` strings; one `vi.mock` per changed file is not mock-heavy. The 2 Inventario pre-existing tests were updated because the new `<option>` text legitimately collides with their `findByText`/`getByText` queries — the behavioural assertion (cell renders the value, header shows the column name) is preserved via `document.querySelectorAll('td')` / `'<th>'` selectors. No tautologies, no ghost loops, no smoke-only renders.

### Issues Found
**CRITICAL**: None

**WARNING**: None

**SUGGESTION** (non-blocking — from independent verifier + reviewer hygiene):
1. `tasks.md` Phase 0.1 wording says "Do not edit `setup.ts` again as part of this change" while the diff shipping the shim IS `setup.ts`. Wording only; the intent (no further edits during this apply) is preserved and the shim lives outside the behaviour touched by Phases 1–6.
2. `SELLER_BUCKETS` in `backend/app/routers/books.py` duplicates the `SellerBucket` literal in `backend/app/services/seller_split.py`. Deliberate and commented at both sites (the router tuple is the wire-level allow-list; the service literal is the runtime allow-list for the SQL filter helper).
3. `frontend/src/pages/Inventario.test.tsx` carries a stale test name referencing "five filters" while the filter row now has six (`Categoría`, `Stock`, `Vendedora`, `Búsqueda`, `Stock min`, `Stock max`). Cosmetic.
4. `tasks.md` Phase 6.7 calls `rg -n` but the apply run used the equivalent PowerShell `Select-String`. Same gate, same outcome; flag only for textual fidelity.
5. No production DB inspection of the actual distinct `observaciones` values — the filter is exercised in tests against fixtures, but production cardinality is not audited.
6. No authenticated UI click-through in production — only `/api/books` 401, SPA index, and bundle-hash parity prove deploy. Behaviour in front of a logged-in user is unverified at the live URL.

### Verdict
**PASS** (canonical pass — complete spec-scenario evidence) — all 18/18 spec scenarios proven with covering assertions; backend 333 passed / frontend 105 passed / build exit 0; independent verifier verdict `pass` (confidence 0.95, 0 blockers); four commits on `main`, pushed (`1fdd403..f34df0e`); Railway auto-deployed (id `6487493950`) and bundle hash parity confirms the new code is live. No blockers, no CRITICAL findings, no WARNINGs. The 6 SUGGESTIONs are non-blocking hygiene and residual coverage. Archive-ready.
