# supplier-distributors Specification

## Purpose

Extend the Supplier domain with two optional distributor-commercial fields
(`discount`, `sale_condition`), seed 17 distributor records idempotently, and
surface both fields in the Spanish Proveedores UI.

## Requirements

### Requirement: Supplier distributor fields

The Supplier model MUST expose two nullable TEXT fields, `discount` and
`sale_condition`, carried through Base/Create/Update/Read schemas.

#### Scenario: Create supplier with new fields

- GIVEN an authenticated admin and a valid payload including `discount` and `sale_condition`
- WHEN the supplier is created
- THEN both fields persist
- AND the response returns their values

#### Scenario: Fields omitted

- GIVEN a create or update payload that omits both fields
- WHEN the operation runs
- THEN both fields persist as NULL without error

### Requirement: Supplier API surfaces new fields

Reads and writes MUST return and accept `discount` and `sale_condition`; the
audit log MUST record diffs for both fields.

#### Scenario: List returns new fields

- GIVEN suppliers with `discount` and `sale_condition` set
- WHEN suppliers are listed
- THEN each read payload includes both fields

#### Scenario: Update new fields

- GIVEN a supplier and an update setting both fields
- WHEN the update applies
- THEN both fields persist
- AND the audit diff records old and new for each changed field

### Requirement: Additive migration

A new Alembic migration MUST add `discount` and `sale_condition` as nullable
columns and MUST NOT alter existing columns or data.

#### Scenario: Migration up and down clean

- GIVEN an existing database
- WHEN the migration upgrades and then downgrades
- THEN both columns are added and then removed without data loss

### Requirement: Idempotent distributor seeding

`scripts/seed_suppliers.py` MUST insert CSV rows missing by supplier `name` and
MUST skip rows whose name already exists, so re-runs are safe.

#### Scenario: First run inserts 17

- GIVEN an empty suppliers table
- WHEN the seed runs
- THEN 17 suppliers are inserted
- AND the printed summary reports 17 inserts

#### Scenario: Second run skips 17

- GIVEN all 17 suppliers already present
- WHEN the seed runs again
- THEN zero suppliers are inserted and all 17 are skipped
- AND no duplicates are created

#### Scenario: Existing name skipped

- GIVEN one distributor name already exists
- WHEN the seed runs
- THEN that row is skipped and the remaining rows are inserted

### Requirement: Raw-fidelity mapping

The seed MUST map source columns 1:1 to supplier fields without splitting or
reformatting, preserving raw values such as `50% / 40%` and `;`-separated emails.

#### Scenario: Preserve raw values

- GIVEN a CSV row with `DTO.` equal to `50% / 40%` and a `;`-separated EMAIL
- WHEN the seed inserts it
- THEN `discount` stores `50% / 40%` exactly and `email` keeps the raw string

### Requirement: Proveedores UI surfaces fields

The Proveedores page MUST render table columns in this exact order: Nombre,
Contacto, Teléfono, Email, Cond. venta, Notas, DTO, followed by the actions
column. The "Condición de venta" header MUST be shortened to "Cond. venta" and
the "Descuento" header MUST be renamed to "DTO". The page MUST NOT render any
Editoriales column. The supplier form MUST include "Condición de venta",
"Notas", and "DTO" inputs and MUST NOT include an "Editoriales" input. The
create/update payload MUST include `sale_condition`, `notes`, and `discount`
and MUST NOT include `editorials`.

#### Scenario: Render columns

- GIVEN a supplier with `discount`, `sale_condition`, and `notes` set
- WHEN Proveedores renders the table
- THEN columns "Cond. venta", "Notas", and "DTO" show their values
- AND no "Editoriales" column is present

#### Scenario: Edit fields

- GIVEN the supplier form
- WHEN the user enters "DTO", "Condición de venta", and "Notas" and saves
- THEN the payload includes `sale_condition`, `notes`, and `discount`
- AND the payload excludes `editorials`
- AND the update persists the three fields

#### Scenario: Create supplier payload

- GIVEN the supplier form for a new supplier
- WHEN the user fills "Condición de venta", "Notas", and "DTO" and submits
- THEN the create payload includes `sale_condition`, `notes`, and `discount`
- AND the create payload excludes `editorials`

### Requirement: Test coverage

`test_suppliers.py` MUST assert the new fields, and the Proveedores test suite
MUST assert the renamed column headers ("Cond. venta", "Notas", "DTO"), the
fixture cell values, and the create/update payloads containing `sale_condition`,
`notes`, and `discount` while excluding `editorials`, without referencing
"Editoriales".

#### Scenario: Backend assertions

- GIVEN the supplier test suite
- WHEN tests run
- THEN create, update, and list assertions include both fields

#### Scenario: Frontend assertions

- GIVEN the updated `Proveedores.test.tsx`
- WHEN the frontend tests run
- THEN the column headers "Cond. venta", "Notas", and "DTO" render and the payload assertions pass without any Editoriales reference
- AND `npm run build` passes tsc strict
