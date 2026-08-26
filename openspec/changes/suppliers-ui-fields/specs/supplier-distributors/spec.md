# Delta for supplier-distributors

## MODIFIED Requirements

### Requirement: Proveedores UI surfaces fields

The Proveedores page MUST render table columns in this exact order: Nombre, Contacto, Teléfono, Email, Cond. venta, Notas, DTO, followed by the actions column. The "Condición de venta" header MUST be shortened to "Cond. venta" and the "Descuento" header MUST be renamed to "DTO". The page MUST NOT render any Editoriales column. The supplier form MUST include "Condición de venta", "Notas", and "DTO" inputs and MUST NOT include an "Editoriales" input. The create/update payload MUST include `sale_condition`, `notes`, and `discount` and MUST NOT include `editorials`.
(Previously: the page rendered "Descuento" and "Condición de venta" columns plus an "Editoriales" column and an "Editoriales (separadas por coma)" form input, and the payload included `editorials`.)

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

## ADDED Requirements

### Requirement: Existing tests updated and green

The `Proveedores.test.tsx` suite MUST assert the renamed column headers ("Cond. venta", "Notas", "DTO"), the fixture cell values, and the create/update payloads containing `sale_condition`, `notes`, and `discount` while excluding `editorials`. It MUST NOT reference "Editoriales".
(Note: replaces the prior "Test coverage" frontend assertion; the backend `test_suppliers.py` assertions are unchanged.)

#### Scenario: Frontend assertions reflect new surface

- GIVEN the updated `Proveedores.test.tsx`
- WHEN the frontend tests run
- THEN the column headers "Cond. venta", "Notas", and "DTO" render and the payload assertions pass without any Editoriales reference
- AND `npm run build` passes tsc strict
