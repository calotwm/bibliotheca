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

The Proveedores page MUST render "Descuento" and "Condición de venta" table
columns and MUST include form inputs for both, editable on create and update.

#### Scenario: Render columns

- GIVEN a supplier with both fields set
- WHEN Proveedores renders the table
- THEN both columns show their values

#### Scenario: Edit fields

- GIVEN the supplier form
- WHEN the user enters "Descuento" and "Condición de venta" and saves
- THEN the payload includes both fields and the update persists them

### Requirement: Test coverage

`test_suppliers.py` MUST assert the new fields, and a new `Proveedores.test.tsx`
MUST cover rendering and editing.

#### Scenario: Backend assertions

- GIVEN the supplier test suite
- WHEN tests run
- THEN create, update, and list assertions include both fields

#### Scenario: Frontend assertions

- GIVEN `Proveedores.test.tsx`
- WHEN tests run
- THEN both columns render and the form persists both fields
