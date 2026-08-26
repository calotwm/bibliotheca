# Tasks: Supplier Distributors Extension

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~250–280 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR (11 files, <400 lines) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Backend: model + migration + schemas + router + tests | PR 1 (single) | `cd backend; py -m pytest tests/test_suppliers.py -v` | `POST /api/suppliers` with discount/sale_condition fields; verify 201 + audit row | Revert commit; nullable columns drop-safe |
| 2 | Seed script + CSV | PR 2 (single, optional split) | Manual: `cd C:\repo; py scripts/seed_suppliers.py` | Run against dev DB; verify `inserted=17 skipped=0` then re-run `inserted=0 skipped=17` | Delete script + CSV; no schema impact |
| 3 | Frontend: types + Proveedores UI + test + README | PR 3 (single) | `cd frontend; npm run test -- Proveedores` + `npm run build` | Open Proveedores page; create/edit supplier with both fields | Revert commit; UI-only, no data impact |

## Phase 1: Model + Migration (Foundation)

- [x] 1.1 Add `discount: Mapped[str | None] = mapped_column(Text)` and `sale_condition: Mapped[str | None] = mapped_column(Text)` after `notes` in `backend/app/models/supplier.py` (~5 lines)
- [x] 1.2 Create Alembic migration `backend/alembic/versions/<rev>_add_supplier_sale_condition_and_discount.py` with two `op.add_column(... sa.Text(), nullable=True)` and matching `down_revision`; **confirm current head with `py -m alembic heads` before writing `down_revision`** (~25 lines)

## Phase 2: Schemas + Router + Audit

- [x] 2.1 Add `discount: str | None = None` and `sale_condition: str | None = None` to `SupplierBase`, `SupplierUpdate`, and `SupplierRead` in `backend/app/schemas/supplier.py` (~6 lines)
- [x] 2.2 Update `_to_read()` in `backend/app/routers/suppliers.py` to pass `discount` and `sale_condition` to `SupplierRead` (~2 lines)
- [x] 2.3 Update `create_supplier()` in `backend/app/routers/suppliers.py`: pass `discount`/`sale_condition` to `Supplier(...)` constructor and add both to audit `changes` dict (~4 lines)
- [x] 2.4 Verify update auto-diff: the generic `for field, value in data.items()` loop already handles new fields — no router change needed (confirm via code review, 0 lines)

## Phase 3: Backend Tests (TDD: extend existing suite)

- [x] 3.1 Add `discount: "50% / 40%"` and `sale_condition: "Neto 30 días"` to `SUPPLIER_PAYLOAD` in `backend/tests/test_suppliers.py` (~2 lines)
- [x] 3.2 In `test_supplier_crud_happy_path`, assert `data["discount"]` and `data["sale_condition"]` on create response; assert updated values after PUT (~8 lines)
- [x] 3.3 Add `test_supplier_nullable_fields_omit`: create supplier without discount/sale_condition, assert both return `None` (~15 lines)
- [x] 3.4 In `test_supplier_audited_on_create_and_delete`, assert audit `changes` dict includes `discount` and `sale_condition` keys on create (~5 lines)

## Phase 4: Seed Script + CSV

- [x] 4.1 Create `scripts/seed_suppliers.csv` with 17 rows; header: `name,contact_name,email,sale_condition,notes,discount`; values copied verbatim from source (preserve `50% / 40%`, `;`-emails, malformed SBS email row 15, empty→NULL) (~20 lines)
- [x] 4.2 Create `scripts/seed_suppliers.py` following `import_excel.py` pattern: async entry, `os.environ.setdefault`, `sys.path` insert, `create_all`, `csv.DictReader`, insert-if-missing by `name` (coerce empty→`None`), print summary `inserted=X skipped=Y total=17` (~60 lines)

## Phase 5: Frontend Types

- [x] 5.1 Add `discount: string | null` and `sale_condition: string | null` to `Supplier` interface in `frontend/src/lib/types.ts` (~2 lines)
- [x] 5.2 Add `discount?: string | null` and `sale_condition?: string | null` to `SupplierPayload` interface in `frontend/src/lib/types.ts` (~2 lines)

## Phase 6: Proveedores UI

- [x] 6.1 Add `discount` and `sale_condition` state variables + `.trim() || null` handling in `SupplierForm` component in `frontend/src/pages/Proveedores.tsx` (~10 lines)
- [x] 6.2 Add two form inputs ("Descuento", "Condición de venta") after Email field in `SupplierForm` (~10 lines)
- [x] 6.3 Add "Descuento" and "Condición de venta" columns to the `columns` array in `Proveedores` component (after `email` column) (~6 lines)
- [x] 6.4 Include both fields in `onSave` payload in `SupplierForm.handleSubmit` (~2 lines)

## Phase 7: Frontend Tests

- [x] 7.1 Create `frontend/src/pages/Proveedores.test.tsx`: mock `api/suppliers.listSuppliers` with fixture including discount/sale_condition; assert "Descuento" and "Condición de venta" column headers render (~30 lines)
- [x] 7.2 In `Proveedores.test.tsx`, assert table cells show fixture values for both columns (~15 lines)
- [x] 7.3 In `Proveedores.test.tsx`, test form submission includes both fields in payload (~15 lines)

## Phase 8: Documentation

- [x] 8.1 Add post-deploy seed step to `README.md`: document `py scripts/seed_suppliers.py` as Railway one-off (or equivalent), explain idempotent re-run safety (~8 lines)

## Phase 9: Verification

- [x] 9.1 Run `cd backend; py -m pytest tests/test_suppliers.py -v` — all supplier tests pass (~0 lines changed)
- [x] 9.2 Run `cd frontend; npm run test` — Proveedores tests pass (~0 lines changed)
- [x] 9.3 Run `cd frontend; npm run build` — tsc strict passes, no type errors (~0 lines changed)
- [x] 9.4 Run `cd backend; py -m alembic upgrade head` then `downgrade -1` — migration up/down clean (~0 lines changed)
