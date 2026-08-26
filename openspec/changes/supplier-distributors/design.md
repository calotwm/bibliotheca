# Design: Supplier Distributors Extension

## Technical Approach

Extend `Supplier` with two nullable TEXT fields (`discount`, `sale_condition`) carried end-to-end: model → Base/Create/Update/Read schemas → router read/create/audit → additive Alembic migration. Seed 17 distributor records idempotently via a standalone script (versioned CSV + insert-if-missing by `name`), and surface both fields in the Spanish Proveedores UI. Out of scope: numeric math, import UI, editorial mapping, auto-seed on deploy, source-data cleanup.

## Architecture Decisions

| Decision | Option | Tradeoff | Chosen |
|---|---|---|---|
| Field type | `String(255)` vs `Text` | String truncates long conditions/credentials and forces a max_length; Text mirrors `notes` (free-form, unbounded) | `Text` |
| Seed approach | Standalone script vs Alembic data migration vs startup hook | Script: manual/idempotent/versioned data; migration mixes schema+data; hook runs every boot | Standalone script |
| Data fidelity | Clean/split vs raw 1:1 | Cleaning risks loss/typos; raw preserves source verbatim, editable later via UI | Raw 1:1 |
| Idempotency key | `name` | `name` is unique-constrained and the only natural identifier | `name` |
| UI placement | New columns/fields near `email` (commercial grouping) | Form stays 2-col; table already scrolls horizontally | After `email` |
| Test strategy | Extend existing + new page test | No Proveedores test exists; colocate per convention | Extend `test_suppliers.py`; new `Proveedores.test.tsx` |

`Text` chosen for both because `sale_condition` may hold URLs/credentials and `discount` holds multi-value strings like `50% / 40%`; a fixed length cap is inconsistent with free-form commercial data.

## Data Flow / Sequence Diagrams

(a) Create/update with audit log:

```
POST /api/suppliers (admin)
  _name_taken(name) → 409?
  Supplier(name,..., discount, sale_condition)      # +2 fields
  flush → log_audit(changes={..., discount, sale_condition}) → commit
  _to_read(supplier) → response (both fields)

PUT /api/suppliers/{id}
  model_dump(exclude_unset=True)
  for field,value in data.items():    # generic loop already diffing
    old=getattr(supplier,field); old!=value → changes[field]={old,new}; setattr
  log_audit(changes) → commit → _to_read
```

(b) Seed run (first vs re-run):

```
py scripts/seed_suppliers.py
  create_all → read seed_suppliers.csv (csv.DictReader)
  existing = {name for name in select(Supplier.name)}
  for row: row.name in existing → skip++ else insert++ (empty→None)
  commit → print "inserted=X skipped=Y total=17"

first run: existing=∅        → inserted=17 skipped=0
re-run:    existing=17 names → inserted=0  skipped=17
```

## File Changes

| File | Action | Implementation notes |
|---|---|---|
| `backend/app/models/supplier.py` | Modify | Add `discount` + `sale_condition` as `Mapped[str \| None] = mapped_column(Text)` after `notes` |
| `backend/app/schemas/supplier.py` | Modify | Add both to `SupplierBase`, `SupplierUpdate`, `SupplierRead` (`str \| None = None`, no max_length) |
| `backend/app/routers/suppliers.py` | Modify | `_to_read()` +2; `create_supplier()` pass fields to `Supplier(...)` and add to audit `changes` dict; update loop auto-diffs (no change) |
| `backend/alembic/versions/<rev>_add_supplier_sale_condition_and_discount.py` | Create | Two `op.add_column('suppliers', sa.Column(..., sa.Text(), nullable=True))`; `down` drops both; `down_revision='7e82d91dbe21'` |
| `scripts/seed_suppliers.csv` | Create | 17 rows; header = target fields `name,contact_name,email,sale_condition,notes,discount` (values copied verbatim from `Distribuidoras.xlsx`) |
| `scripts/seed_suppliers.py` | Create | Follow `import_excel.py`: async entry, `os.environ.setdefault`, `sys.path` insert, `csv.DictReader`, insert-if-missing by name, printed summary |
| `backend/tests/test_suppliers.py` | Modify | Payload + create/update/list assertions for both fields |
| `frontend/src/lib/types.ts` | Modify | `Supplier` +2 `string \| null`; `SupplierPayload` +2 optional |
| `frontend/src/pages/Proveedores.tsx` | Modify | 2 form inputs ("Descuento", "Condición de venta") + 2 columns after `email` |
| `frontend/src/pages/Proveedores.test.tsx` | Create | Mock `api/suppliers`; assert columns render + form persists both fields |
| `README.md` | Modify | Document `py scripts/seed_suppliers.py` post-deploy step |

## Interfaces / Contracts

```python
# schemas/supplier.py — added to Base/Update/Read
discount: str | None = None
sale_condition: str | None = None
```
```ts
// types.ts
discount: string | null;          // Supplier
sale_condition: string | null;    // Supplier
discount?: string | null;         // SupplierPayload
sale_condition?: string | null;   // SupplierPayload
```

## Edge Cases

| Case | Handling |
|---|---|
| Empty/omitted values | Omitted→`None` (schema default); seed coerces empty CSV cell→`None`; form uses `.trim() \|\| null` |
| `;`-separated emails | `email` is `String(255)`; stored raw, no split |
| Malformed SBS email (row 15) | Preserved raw; editable via UI |
| Double DTO (`50% / 40%`, `30%-35%`) | `Text` stores exact string |
| Existing name on seed | Skipped (insert-if-missing) |

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Backend unit/integration | create/update/list return + persist both fields; audit diff records old/new; migration up/down clean | Extend `test_suppliers.py` (httpx ASGITransport + StaticPool fixtures) |
| Frontend unit | Columns render "Descuento"/"Condición de venta"; form persists both | New `Proveedores.test.tsx` (RTL + mocked `api/suppliers`) |
| Build | Strict tsc | `npm run build` |

## Threat Matrix

N/A — no routing, shell command, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The seed script is a data-loading utility (DB writes via SQLAlchemy), not an untrusted-input boundary.

## Migration / Rollout

Additive nullable columns; `alembic upgrade head` (already in Dockerfile) applies schema; seed runs as manual/Railway one-off after deploy. Rollback: `alembic downgrade` or revert commit; re-running seed is safe.

## Apply must NOT do

- No silent data fixes (email splitting, credential reformatting, cleanup)
- No `supplier_editorials` seeding (no source column)
- No auto-seed on deploy (no startup hook, Alembic data migration, or Dockerfile change)
- No numeric discount math, import UI, or backend `""→NULL` coercion
- Do not change existing `notes` create-audit behavior

## Open Questions

None blocking.
