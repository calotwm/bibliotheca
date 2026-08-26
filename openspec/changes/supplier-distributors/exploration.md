## Exploration: Supplier Distributors Extension

### Current State

The suppliers module is fully implemented with CRUD operations, editorial mapping, and audit logging. The Supplier model currently has: `id`, `name`, `contact_name`, `phone`, `email`, `address`, `notes`, plus a relationship to `SupplierEditorial`. The frontend displays suppliers in a DataTable with Spanish UI copy ("Proveedores"). All mutations are audited and require admin role.

### Affected Areas

#### Backend
- `backend/app/models/supplier.py` (lines 9-22) — Add `sale_condition` and `discount` fields to Supplier model
- `backend/app/schemas/supplier.py` (lines 8-50) — Add fields to SupplierBase, SupplierUpdate, SupplierRead
- `backend/app/routers/suppliers.py` (lines 50-62, 160-167) — Update `_to_read()` and `create_supplier()` to handle new fields
- `backend/alembic/versions/` — New migration file to add columns
- `backend/tests/test_suppliers.py` — Update test payload and assertions

#### Frontend
- `frontend/src/lib/types.ts` (lines 103-124) — Add `sale_condition` and `discount` to Supplier and SupplierPayload interfaces
- `frontend/src/pages/Proveedores.tsx` (lines 28-34, 44-52, 151-196) — Add form fields and table columns
- No existing test file for Proveedores.tsx (gap to address)

#### Scripts
- `scripts/` — New seed script for 17 distributor records
- `scripts/import_excel.py` — Reference pattern for standalone scripts

#### Deployment
- `Dockerfile` (line 21) — Already runs `alembic upgrade head` before starting app
- `.railwayignore` — Scripts directory is NOT ignored (good, seed data will be deployed)

### Approaches

#### 1. **Seed Script as Standalone Python Script** (Recommended)
Create `scripts/seed_suppliers.py` following the `import_excel.py` pattern:
- Use `asyncio.run()` entry point
- Load env vars with `os.environ.setdefault()` for dev defaults
- Import from `app.db`, `app.models`, `app.config`
- Read CSV/JSON data from versioned file (e.g., `scripts/seed_suppliers.csv`)
- Idempotent: check if supplier exists by name before insert, skip or update
- Run manually via `py scripts/seed_suppliers.py` or as Railway one-off command

**Pros:**
- Follows existing pattern in the codebase
- Easy to test locally
- Can be re-run safely (idempotent)
- Data is versioned in repo (reproducible)

**Cons:**
- Requires manual execution or Railway one-off command
- No automatic seeding on deploy

**Effort:** Low

#### 2. **Seed Script as Alembic Data Migration**
Create a data migration in `backend/alembic/versions/` that inserts the 17 distributors after schema migration.

**Pros:**
- Runs automatically with `alembic upgrade head`
- Tied to schema version

**Cons:**
- Mixes schema and data concerns
- Harder to make idempotent (need to check existence)
- Not reusable if data needs to be updated later
- Alembic data migrations are discouraged in SQLAlchemy docs

**Effort:** Medium

#### 3. **Seed Script as FastAPI Startup Event**
Add a startup hook in `backend/app/main.py` that seeds suppliers on app boot.

**Pros:**
- Automatic on every deploy
- Can check and seed only if missing

**Cons:**
- Slows down app startup
- Runs on every boot (even if already seeded)
- Harder to control when seeding happens
- Not suitable for one-time data load

**Effort:** Medium

### Recommendation

**Use Approach 1: Standalone seed script** (`scripts/seed_suppliers.py` + `scripts/seed_suppliers.csv`).

Rationale:
- Follows the existing `import_excel.py` pattern
- Idempotent by design (check before insert)
- Data is versioned and reproducible
- Can be run manually during development or as a Railway one-off command
- Separates concerns: schema migrations (Alembic) vs data seeding (standalone script)
- Easy to test and debug

For Railway deployment, add a one-off command in the Railway dashboard or use the Railway CLI to run `py scripts/seed_suppliers.py` after the first deploy. Alternatively, document it in the README as a post-deploy step.

### Implementation Details

#### Backend Changes
1. **Model** (`backend/app/models/supplier.py`):
   ```python
   sale_condition: Mapped[str | None] = mapped_column(Text)
   discount: Mapped[str | None] = mapped_column(Text)
   ```

2. **Schemas** (`backend/app/schemas/supplier.py`):
   - Add to `SupplierBase`: `sale_condition: str | None = None`, `discount: str | None = None`
   - Add to `SupplierUpdate`: same fields as optional
   - Add to `SupplierRead`: same fields as optional

3. **Router** (`backend/app/routers/suppliers.py`):
   - Update `_to_read()` (line 50-62) to include new fields
   - Update `create_supplier()` (line 160-167) to pass new fields to Supplier constructor
   - Audit log should include new fields in changes dict

4. **Migration**:
   - Create new migration: `alembic revision --autogenerate -m "add_supplier_sale_condition_and_discount"`
   - Or manually write migration with `op.add_column()` for both fields

5. **Tests** (`backend/tests/test_suppliers.py`):
   - Update `SUPPLIER_PAYLOAD` to include `sale_condition` and `discount`
   - Add assertions for new fields in CRUD test

#### Frontend Changes
1. **Types** (`frontend/src/lib/types.ts`):
   ```typescript
   export interface Supplier {
     // ... existing fields
     sale_condition: string | null;
     discount: string | null;
   }
   
   export interface SupplierPayload {
     // ... existing fields
     sale_condition?: string | null;
     discount?: string | null;
   }
   ```

2. **Proveedores.tsx**:
   - Add form fields for `sale_condition` and `discount` (lines 28-34, 44-52)
   - Add table columns for new fields (lines 151-196)
   - Spanish labels: "Condición de venta", "Descuento"

3. **Tests**:
   - Create `frontend/src/pages/Proveedores.test.tsx` (currently missing)
   - Test form submission with new fields
   - Test table rendering with new columns

#### Seed Script
1. **Data file** (`scripts/seed_suppliers.csv`):
   - Export from Excel to CSV
   - Columns: name, contact_name, phone, email, address, notes, sale_condition, discount, editorials (semicolon-separated)

2. **Script** (`scripts/seed_suppliers.py`):
   - Follow `import_excel.py` pattern
   - Read CSV with `csv.DictReader`
   - For each row: check if supplier exists by name, skip if exists, else create
   - Parse editorials from semicolon-separated string
   - Print summary: inserted, skipped, errors

### Risks

1. **Data loss on re-seed**: Mitigated by idempotent design (check before insert)
2. **Migration conflicts**: Low risk — adding nullable columns is backward-compatible
3. **Frontend breaking changes**: Low risk — new fields are optional, existing suppliers will show "—"
4. **Railway deployment**: Seed script must be run manually after first deploy (document in README)

### Ready for Proposal

**Yes** — sufficient information gathered to proceed with proposal phase.

The orchestrator should tell the user:
- Exploration complete, all affected areas mapped
- Recommended approach: standalone seed script following existing pattern
- New fields are optional and backward-compatible
- Frontend UI is in Spanish, new labels will be "Condición de venta" and "Descuento"
- No existing Proveedores test file (will be created)
- Seed data will be versioned in repo for reproducibility
