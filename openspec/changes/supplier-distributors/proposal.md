# Proposal: Supplier Distributors Extension

## Intent
The suppliers module lacks distributor commercial data; 17 distributor records live only in `Distribuidoras.xlsx`. Extend Supplier with two optional text fields, seed the records idempotently, and surface both fields in the Spanish Proveedores UI.

## Scope
### In Scope
- Nullable `discount` + `sale_condition` TEXT columns (model, schemas, router, migration).
- Idempotent `scripts/seed_suppliers.py` + versioned `scripts/seed_suppliers.csv` (17 rows, 1:1 mapping).
- Proveedores form inputs + table columns ("Descuento", "Condición de venta").
- Backend tests for new fields; new `Proveedores.test.tsx`.

### Out of Scope
- Numeric discount computation; import UI; editorial mapping seeding; auto-seeding on deploy; source-data cleanup (email splitting, credential reformatting).

## Capabilities
> Contract for sdd-spec; `openspec/specs/` is empty.

### New Capabilities
- `supplier-distributors`: Supplier `discount`/`sale_condition` fields, idempotent distributor seeding, Proveedores UI surface.

### Modified Capabilities
- None.

## Approach
Standalone seed script following `scripts/import_excel.py` (async entry, env defaults, `csv.DictReader`, insert-if-missing by name, printed summary). Run manually or as Railway one-off.
Alternatives: (a) Alembic data migration — rejected: mixes schema/data, weak idempotency, discouraged; (b) startup hook — rejected: slows boot, runs every deploy, contradicts no-auto-seed decision.

## Data Mapping & Quality
Columns map 1:1, no split/reformat: DISTRIBUIDORA→name, CONTACTO→contact_name, EMAIL→email, COND. VENTA→sale_condition, NOTAS→notes, DTO.→discount. `supplier_editorials` NOT populated (no source column).

| Row | Issue | Handling |
|-----|-------|----------|
| 14 | DTO. `50% / 40%` | Preserve exactly |
| 15 | `30%-35%`; malformed email; creds in NOTAS | Preserve raw; editable via UI |
| 4,11,15 | COND. VENTA "Plataforma:" URL, creds in NOTAS | Map as-is |
| 1–17 | `;`-separated emails | Keep raw string (email is String(255)) |

## Affected Areas
| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/models/supplier.py` | Modified | +2 nullable Text fields |
| `backend/app/schemas/supplier.py` | Modified | Base/Update/Read |
| `backend/app/routers/suppliers.py` | Modified | `_to_read()`, `create_supplier()`, audit diff |
| `backend/alembic/versions/*` | New | `add_supplier_sale_condition_and_discount` |
| `backend/tests/test_suppliers.py` | Modified | payload + assertions |
| `frontend/src/lib/types.ts` | Modified | Supplier/Payload types |
| `frontend/src/pages/Proveedores.tsx` | Modified | form + columns |
| `frontend/src/pages/Proveedores.test.tsx` | New | form + render |
| `scripts/seed_suppliers.py`, `.csv` | New | idempotent seed |
| `README.md` | Modified | post-deploy seed step |

## Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Migration conflict | Low | Additive nullable columns |
| Re-seed duplicates | Low | Idempotent by name |
| Source-data quality | Med | Documented mapping; preserve raw |
| Forgot seed on deploy | Med | Documented Railway one-off |

## Rollback Plan
Additive/nullable migration → revert commit (or `alembic downgrade`). No destructive deltas. Re-running seed is safe.

## Dependencies
- One-time CSV export from `Distribuidoras.xlsx`.
- `scripts/import_excel.py` as pattern reference.

## Success Criteria
- [ ] Backend tests pass; migration up/down clean.
- [ ] Seed run twice → second run inserts 0 / skips 17.
- [ ] Proveedores renders both columns; form persists both fields.
- [ ] `npm run build` (tsc strict) passes.

## Open Questions
None blocking.
