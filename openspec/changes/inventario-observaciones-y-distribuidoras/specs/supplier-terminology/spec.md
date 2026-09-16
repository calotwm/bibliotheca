# supplier-terminology Specification

## Purpose

Rename the user-visible Spanish terminology from `Proveedores / proveedor` to
`Distribuidoras / distribuidora` so the UI label matches the actual domain
(distributors, not generic suppliers). The change is copy-only: no code,
route, type, file, component, API path, or DB identifier is renamed.

## Requirements

### Requirement: Sidebar label reads Distribuidoras

The Sidebar entry that points to `/proveedores` MUST render its visible label
as `Distribuidoras`. The `to` value, the icon, the order in `NAV_ITEMS`, and
the route itself MUST NOT change.

#### Scenario: Sidebar shows Distribuidoras

- GIVEN an authenticated user
- WHEN the Sidebar renders
- THEN the navigation entry for the suppliers module shows the label
  `Distribuidoras`
- AND clicking it still navigates to `/proveedores`

### Requirement: Page title reads Distribuidoras

The `PAGE_TITLES` map for the `/proveedores` route MUST render the page
title as `Distribuidoras` in both the mobile and desktop headers rendered by
`Layout`.

#### Scenario: Page header reads Distribuidoras

- GIVEN an authenticated user on `/proveedores`
- WHEN `Layout` renders the sticky header
- THEN both the mobile and desktop `<h1>`/title text show `Distribuidoras`

### Requirement: Proveedores page copy reads Distribuidoras / distribuidora

The Proveedores page MUST replace the user-visible Spanish strings in this
exact set of locations with the `Distribuidoras / distribuidora` wording:

- the form modal title (`Editar proveedor` / `Nuevo proveedor`)
- the submit button label (`Crear proveedor` / `Guardar cambios`)
- the `No se pudo guardar el proveedor` error fallback
- the `Nuevo proveedor` action button
- the `No se pudieron cargar los proveedores` error fallback
- the `No hay proveedores registrados` empty-state message
- the `Eliminar proveedor` confirm-dialog title
- the `¿Desea eliminar el proveedor "${name}"?` confirm-dialog message

#### Scenario: All page copy reflects the rename

- GIVEN a distributor list with at least one row
- WHEN the Proveedores page renders
- THEN the `+ Nueva distribuidora` action button shows that label
- AND opening the create modal shows `Nueva distribuidora` as title and
  `Crear distribuidora` on submit
- AND opening the edit modal shows `Editar distribuidora` as title and
  `Guardar cambios` on submit
- AND the empty state, loading-error fallback, save-error fallback, and
  delete confirm dialog all use the `distribuidora / distribuidoras` wording

### Requirement: Rename boundary

The rename MUST be limited to user-visible Spanish strings. The route
`/proveedores`, the `Proveedores.tsx` file and exported `Proveedores`
component, the `Supplier` type, all API paths, all DB identifiers, and the
URL must remain unchanged. Renaming these is OUT OF SCOPE for this change.

#### Scenario: No code, route, type, file, or DB identifier is renamed

- GIVEN the rename is applied
- WHEN the app boots and the user navigates
- THEN `App.tsx` still mounts `<Proveedores />` on `<Route path="proveedores" ...>`
- AND `Supplier`, `SupplierPayload`, `SupplierForm`, and `suppliersApi` keep
  their identifiers
- AND the URL bar still shows `/proveedores`
- AND no Alembic migration is created