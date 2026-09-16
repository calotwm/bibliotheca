# Design: Inventario seller filter, observaciones sort/wrap, Distribuidoras rename

## Technical Approach

Three backend files, six frontend files, plus colocated tests. Single PR
within the 400-line budget.

1. **Backend** — share the bucket rule once in `seller_split.py`; expose
   `seller` query param on `GET /api/books` enforced in SQL; add
   `observaciones` to `SORT_FIELDS` with a NULL-stable, case-insensitive
   ordering expression.
2. **Frontend** — feed `seller` through `BookFilters`/`listBooks`; render
   the `Vendedora` select on Inventario; make `observaciones` sortable; give
   `DataTable` two opt-in boolean props (`fixedLayout`, `wrapText`) and
   propagate `column.className` to `<th>` so Inventario can wrap and fix its
   column widths.
3. **Rename** — copy-only edits on `Sidebar.tsx`, `Layout.tsx`,
   `Proveedores.tsx`; update colocated tests + a guard scan that no
   user-visible Spanish `Proveedor/proveedor` string survives.

## Architecture Decisions

| Decision | Option | Tradeoff | Chosen |
|---|---|---|---|
| Bucket classification location | New helper in `seller_split.py` shared by router + `compute_shares` | Filter and earnings drift otherwise | Shared `seller_bucket` + SQL condition helper, both in `seller_split.py` |
| `compute_shares` rewrite | Derive from `seller_bucket` vs duplicate the rule | Duplication is the failure mode the proposal exists to prevent | `compute_shares` calls `seller_bucket`; Decimal outputs stay verbatim |
| Seller filter SQL form | Three hard-coded `LIKE` clauses vs generalised predicate | Rule is tiny and fixed | Three branches in `seller_filter_condition(bucket)` returning `ColumnElement[bool]` |
| Sort expression for `observaciones` | `func.lower(Book.observaciones)` vs `func.lower(func.coalesce(Book.observaciones, ""))` | Coalesce removes PG/SQLite NULLS-LAST/FIRST ambiguity | `func.lower(func.coalesce(...))` |
| `_sort_expression` extension | New branch for `observaciones` vs special-case at call site | Special-casing leaks the rule | Extend existing branch so `title/author/editorial/observaciones` all share the coalesced expression |
| DataTable opt-in shape | Two boolean props vs single layout enum | Two booleans match Inventario's binary needs | `fixedLayout?: boolean`, `wrapText?: boolean`, default `false` |
| `column.className` to `<th>` | Always vs only when `fixedLayout` | Widths need propagation; gating couples unrelated concerns | Always propagate; defaults unchanged for existing tables |
| Rename scope | Copy-only vs also rename route/type/file | Code rename requires router + nav + type audit + Alembic + seed; out of scope | Copy-only; route, type, file, component name, API paths, DB identifiers unchanged |

## Data Flow

### A. Seller filter on `GET /api/books`

```
client ──GET /api/books?seller=Cande──▶ list_books()
                                            │
                                  invalid seller → HTTP 400
                                            │
                                  seller_filter_condition("Cande")
                                  text = func.lower(coalesce(observaciones,""))
                                  has_cande = text LIKE '%cande%'
                                  has_juli  = text LIKE '%juli%'
                                  Cande = and_(has_cande, ~has_juli)
                                  Juli  = ~has_cande
                                  Joint = and_(has_cande, has_juli)
                                            │
                                  query.where(condition) + offset/limit
```

### B. Same predicate drives earnings via `compute_shares`

```
sale_service.create_sale ──▶ compute_shares(observaciones)
                                  │
                                  seller_bucket(observaciones)
                                  │
                                  bucket → Decimal split
                                    "Juli y Cande" → (50.00, 50.00)
                                    "Cande"        → (0.00, 100.00)
                                    "Juli"         → (85.00, 15.00)
                                    (covers blank/None/Juli-only/other-text)
```

Guard: byte-identical decimal output. Any drift fails
`test_seller_split.py` (signature) and `test_earnings.py` (numeric totals).

### C. Inventario wrap + fixed layout

```
Inventario columns: each Column<T> gains className: "w-XX whitespace-normal"
                    + sortable: true, sortKey: "observaciones" on obs col
                                      │
DataTable props:      fixedLayout={true} wrapText={true}
                                      │
<table class="w-full min-w-[640px] text-left text-sm table-fixed">   ← opt-in
<thead>  <th className={column.className ?? ""}>                       ← propagated
<tbody>  <td className={`px-3 py-2.5 whitespace-normal break-words ${column.className ?? ""}`}>
                                      │
Long observaciones text → flows onto extra lines, column width stays fixed.
```

`Precios` and other consumers pass no new prop → defaults `false` → identical
DOM to today.

## File Changes

| File | Action | Implementation notes |
|---|---|---|
| `backend/app/services/seller_split.py` | Modify | Add `seller_bucket` + `seller_filter_condition`; rewrite `compute_shares` to derive from `seller_bucket`; outputs (`Decimal("50.00")`, `Decimal("0.00")`, `Decimal("100.00")`, `Decimal("85.00")`, `Decimal("15.00")`) stay byte-identical |
| `backend/app/routers/books.py` | Modify | Add `seller: str \| None = None` param; reject invalid with HTTP 400 (mirror `sort_by` validation at lines 91-100); apply `seller_filter_condition(...)` via `query.where(...)`; extend `SORT_FIELDS` to include `"observaciones"`; extend `_sort_expression` so `observaciones` returns `func.lower(func.coalesce(Book.observaciones, ""))` |
| `backend/tests/test_books.py` | Modify | New tests per bucket incl. blank/NULL → Juli; invalid → 400; composes with `category_id`/`stock_status`/pagination; `sort_by=observaciones` accepted, case-insensitive, NULLs grouped, `desc` reverses |
| `backend/tests/test_seller_split.py` | Modify | New tests: `seller_bucket` agrees with `compute_shares` on the three bucket shapes + blank/None/other-text |
| `frontend/src/lib/constants.ts` | Modify | Add `SELLER_JULI/CANDE/JOINT` constants and `SELLER_FILTERS` with four options (single source of truth) |
| `frontend/src/api/books.ts` | Modify | `BookFilters.seller?: string \| null`; `listBooks` forwards via `URLSearchParams` |
| `frontend/src/components/DataTable.tsx` | Modify | Add `fixedLayout?`/`wrapText?` props (default `false`); propagate `column.className` to `<th>`; conditional `table-fixed` and `whitespace-normal break-words`. Defaults preserve today's DOM exactly |
| `frontend/src/pages/Inventario.tsx` | Modify | Add `seller` state + `Vendedora` `<select>` mirroring `Categoría`; include `seller` in query key + `listBooks` args; mark `observaciones` sortable; per-column `className: "w-XX"`; render `DataTable` with `fixedLayout wrapText` |
| `frontend/src/components/Sidebar.tsx` | Modify | Line 32: `label: "Proveedores"` → `"Distribuidoras"` |
| `frontend/src/components/Layout.tsx` | Modify | Line 11: `"/proveedores": "Proveedores"` → `"Distribuidoras"` |
| `frontend/src/pages/Proveedores.tsx` | Modify | Lines 54, 106, 138, 203, 210, 218, 238, 239: user-visible Spanish strings → `Distribuidora(s)` / `distribuidora(s)` |
| `frontend/src/components/Sidebar.test.tsx` | Modify | Line 31: `expect(screen.getByText("Proveedores"))` → `"Distribuidoras"` |
| `frontend/src/App.test.tsx` | Modify | Lines 145-146: `"Proveedores"` → `"Distribuidoras"` for both click and heading queries |
| `frontend/src/pages/Proveedores.test.tsx` | Modify | `Nuevo proveedor` → `Nueva distribuidora`; `Crear proveedor` → `Crear distribuidora`; other wording references that the page copy changed |

## Interfaces / Contracts

```python
# backend/app/services/seller_split.py
from typing import Literal
from sqlalchemy import and_, func, not_
from sqlalchemy.sql.elements import ColumnElement
from ..models import Book

SellerBucket = Literal["Juli", "Cande", "Juli y Cande"]

def seller_bucket(observaciones: str | None) -> SellerBucket:
    text = (observaciones or "").lower()
    has_cande = "cande" in text
    has_juli = "juli" in text
    if has_cande and has_juli:
        return "Juli y Cande"
    if has_cande:
        return "Cande"
    return "Juli"

def seller_filter_condition(bucket: SellerBucket) -> ColumnElement[bool]:
    text = func.lower(func.coalesce(Book.observaciones, ""))
    has_cande = text.like("%cande%")
    has_juli = text.like("%juli%")
    if bucket == "Juli":
        return ~has_cande
    if bucket == "Cande":
        return and_(has_cande, ~has_juli)
    if bucket == "Juli y Cande":
        return and_(has_cande, has_juli)
    raise ValueError(f"Invalid seller bucket: {bucket!r}")

def compute_shares(observaciones: str | None) -> tuple[Decimal, Decimal]:
    bucket = seller_bucket(observaciones)
    table: dict[SellerBucket, tuple[Decimal, Decimal]] = {
        "Juli y Cande": (Decimal("50"), Decimal("50")),
        "Cande":        (Decimal("0"),  Decimal("100")),
        "Juli":         (Decimal("85"), Decimal("15")),
    }
    juli_share, cande_share = table[bucket]
    return (juli_share.quantize(_TWO_PLACES), cande_share.quantize(_TWO_PLACES))
```

```python
# backend/app/routers/books.py — additions
SELLER_BUCKETS = ("Juli", "Cande", "Juli y Cande")
SORT_FIELDS = ("title", "author", "editorial", "category", "price", "stock", "observaciones")

def _sort_expression(sort_by: str):
    if sort_by == "category":
        return func.lower(Category.name)
    if sort_by in ("title", "author", "editorial", "observaciones"):
        return func.lower(func.coalesce(getattr(Book, sort_by), ""))
    return getattr(Book, sort_by)

# In list_books():
async def list_books(..., seller: str | None = None, ...):
    if seller is not None and seller not in SELLER_BUCKETS:
        raise HTTPException(400, f"Invalid seller: {seller!r}; expected one of {list(SELLER_BUCKETS)}")
    ...
    if seller:
        query = query.where(seller_filter_condition(seller))
```

```ts
// frontend/src/lib/constants.ts
export const SELLER_JULI = "Juli";
export const SELLER_CANDE = "Cande";
export const SELLER_JOINT = "Juli y Cande";
export const SELLER_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "Todas" },
  { value: SELLER_JULI, label: SELLER_JULI },
  { value: SELLER_CANDE, label: SELLER_CANDE },
  { value: SELLER_JOINT, label: SELLER_JOINT },
];

// frontend/src/api/books.ts
export interface BookFilters { /* ... */ seller?: string | null; }
// in listBooks(): if (filters.seller) params.set("seller", filters.seller);
```

```ts
// frontend/src/components/DataTable.tsx
interface DataTableProps<T> {
  /* existing fields unchanged */
  fixedLayout?: boolean;   // NEW (default false → DOM unchanged)
  wrapText?: boolean;      // NEW (default false → DOM unchanged)
}
// <th className={`px-3 py-2.5 font-medium ${column.className ?? ""}`}>
// <td className={`px-3 py-2.5 ${wrapText ? "whitespace-normal break-words " : ""}${column.className ?? ""}`}>
// <table className={`w-full min-w-[640px] text-left text-sm ${fixedLayout ? "table-fixed " : ""}`}>
```

## Edge Cases

| Case | Handling |
|---|---|
| `observaciones IS NULL` under `seller=Juli` | Coalesce to `""`, `LIKE '%cande%'` false → `~has_cande` true → included |
| `observaciones IS NULL` under `seller=Cande` / `Juli y Cande` | Excluded (no `cande` match) |
| `"Cande y Juli"` vs `"Juli y Cande"` | Both contain both tokens → both go to `Juli y Cande` |
| `"Consignación Juli y Cande"` | Contains both tokens → `Juli y Cande` |
| `"En consignación 30%"` | Neither token → `Juli` |
| Mixed-case text | `func.lower()` normalises on both engines |
| `seller` omitted or `""` | Filter not applied (existing behaviour preserved) |
| Invalid `seller` | HTTP 400 with the three allowed values in the detail |
| Sort by `observaciones` with NULL rows | Coalesced to `""` → NULLs and empties sort together on PG and SQLite |
| Precios with no new props | DOM identical; tests pass unchanged |
| Sidebar/Layout rename | Only label text changes; `/proveedores` route stays |

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Backend unit | `seller_bucket` returns correct bucket for the three shapes + blank/None/other-text | Extend `test_seller_split.py` |
| Backend unit | `compute_shares` byte-identical on every bucket shape (regression) | Existing `test_seller_split.py` + `test_earnings.py` |
| Backend integration | `seller` filter per bucket incl. blank/NULL → Juli; invalid → 400; composes with `category_id`/`stock_status`/pagination | Extend `test_books.py` |
| Backend integration | `sort_by=observaciones` accepted, case-insensitive, NULLs grouped, `sort_dir=desc` reverses | Extend `test_books.py` |
| Frontend unit | Inventario `Vendedora` renders four options; selection forwards `seller`; observations header sorts; DataTable defaults unchanged | Extend `Inventario.test.tsx`; new `DataTable.test.tsx` smoke |
| Frontend unit | Sidebar/Layout/Proveedores page copy reads `Distribuidoras / Nueva distribuidora / Editar distribuidora / Eliminar distribuidora` | Update `Sidebar.test.tsx`, `App.test.tsx`, `Proveedores.test.tsx` |
| Frontend guard | No user-visible Spanish `Proveedor / proveedor / proveedores` string in `frontend/src` production code (JSX component name `Proveedores`, route, type, test fixtures allowed) | `rg` checklist in `tasks.md` before merge |
| Build | tsc strict | `npm run build` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. Backend adds an HTTP filter;
frontend changes are UI labels and opt-in props. Local environment fix
(`frontend/src/test/setup.ts` localStorage shim) is already applied;
recorded as Phase 0 prerequisite.

## Migration / Rollout

No DB migration. `observaciones` already exists (`backend/app/models/book.py`
line 39, `String(200)`, nullable). `seller` filter and `observaciones` sort
are additive query params; rename is copy-only. Railway auto-redeploys on PR
merge to `main`.

Rollback: single `git revert`. Old clients continue to work without the new
params. `Distribuidoras` strings revert to `Proveedores`. `DataTable` props
default to `false` so the old DOM is restored. No data impact.

## Apply must NOT do

- No DB migration, no Alembic revision
- No rename of route `/proveedores`, `Supplier` type, `Proveedores.tsx`
  file/component, API paths, or DB identifiers
- No change to `compute_shares` output values (byte-identical Decimals)
- No change to `BookRead` schema
- No special-casing of `observaciones` at the call site — extend
  `_sort_expression` instead
- No hardcoded seller filter in the Inventario page — must come from
  `SELLER_FILTERS` in `lib/constants.ts`
- No change to `frontend/src/test/setup.ts` (localStorage shim is Phase 0)

## Open Questions

None blocking. The bucket rule, sort NULL handling, and rename boundary are
all specified by the proposal.