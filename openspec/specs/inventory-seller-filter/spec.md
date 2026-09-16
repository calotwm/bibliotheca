# inventory-seller-filter Specification

## Purpose

Extend the book catalog with a per-seller bucket filter (`Juli`, `Cande`,
`Juli y Cande`) derived from the free-text `observaciones` column, enable
case-insensitive NULL-stable sorting by `observaciones`, and let Inventario
wrap long `observaciones` cells so the table stays readable.

## Requirements

### Requirement: Seller bucket filter on GET /api/books

`GET /api/books` MUST accept an optional `seller` query parameter that
restricts results to one of three buckets: `Juli`, `Cande`, `Juli y Cande`.
Invalid `seller` values MUST be rejected with HTTP 400, matching the
existing validation pattern used by `sort_by` and `stock_status`.

#### Scenario: Filter by Juli returns only Juli-bucket books

- GIVEN books with `observaciones` of `Juli`, `Cande`, `Juli y Cande`, and `NULL`
- WHEN the client requests `GET /api/books?seller=Juli`
- THEN the response contains only books whose lower-cased `observaciones`
  contains `juli` OR is blank/NULL
- AND books containing `cande` but not `juli` are excluded

#### Scenario: Filter by Cande excludes Juli and joint books

- GIVEN books with `observaciones` of `Juli`, `Cande`, and `Juli y Cande`
- WHEN the client requests `GET /api/books?seller=Cande`
- THEN the response contains only books whose lower-cased `observaciones`
  contains `cande` but NOT `juli`

#### Scenario: Filter by Juli y Cande requires both names

- GIVEN books with `observaciones` of `Juli`, `Cande`, `Cande y Juli`,
  and `Juli y Cande`
- WHEN the client requests `GET /api/books?seller=Juli%20y%20Cande`
- THEN the response contains `Juli y Cande` and `Cande y Juli`
- AND `Juli` and `Cande` are excluded

#### Scenario: Blank or NULL observaciones lands in Juli

- GIVEN a book with `observaciones = NULL` and a book with
  `observaciones = ""`
- WHEN the client requests `GET /api/books?seller=Juli`
- THEN both books appear in the response

#### Scenario: Invalid seller value rejected with HTTP 400

- GIVEN any request
- WHEN the client requests `GET /api/books?seller=Otro`
- THEN the response is HTTP 400
- AND the detail names the three allowed values

#### Scenario: Seller filter composes with existing filters and pagination

- GIVEN a catalog spanning two categories and mixed stock states
- WHEN the client requests
  `GET /api/books?seller=Juli&category_id=1&stock_status=In%20Stock&page=1&page_size=10`
- THEN the result is the AND of all filters with seller applied in SQL
- AND pagination `page` and `page_size` continue to work

### Requirement: Shared bucket classification with compute_shares

The three-bucket rule MUST be implemented exactly once in
`backend/app/services/seller_split.py`. Both the existing
`compute_shares(observaciones)` (used by earnings) and the new
`GET /api/books?seller=...` filter MUST derive from the same predicate so the
money split and the UI filter can never drift. The existing
`compute_shares` outputs for `Juli / Juli-only / blank / NULL / other-text`
(85/15), `Cande` (0/100), and `Juli y Cande / Cande y Juli` (50/50) MUST
remain byte-identical.

#### Scenario: Bucket helper agrees with compute_shares

- GIVEN inputs `Juli`, `Cande`, `Juli y Cande`, `Cande y Juli`,
  `Consignación Juli y Cande`, `""`, `None`, `En consignación 30%`
- WHEN `seller_bucket(text)` and `compute_shares(text)` are evaluated
- THEN the bucket is `Juli` for `Juli`, `""`, `None`, and `En consignación 30%`
- AND the bucket is `Cande` for `Cande`
- AND the bucket is `Juli y Cande` for `Juli y Cande`, `Cande y Juli`, and
  `Consignación Juli y Cande`
- AND the share tuple is `(85.00, 15.00)` for every `Juli` bucket,
  `(0.00, 100.00)` for `Cande`, and `(50.00, 50.00)` for `Juli y Cande`

### Requirement: observaciones joins SORT_FIELDS

`observaciones` MUST be accepted as a `sort_by` value on `GET /api/books`.
Sorting MUST be case-insensitive and MUST keep `NULL` rows grouped together
on both PostgreSQL (prod) and SQLite (test). The router MUST extend
`_sort_expression` so the existing call sites (`title`, `author`,
`editorial`, `category`, `price`, `stock`) keep their current behavior.

#### Scenario: sort_by=observaciones is accepted

- GIVEN any request
- WHEN the client requests `GET /api/books?sort_by=observaciones`
- THEN the response is HTTP 200
- AND the response detail lists `observaciones` among allowed values

#### Scenario: Sort orders case-insensitively with NULLs grouped

- GIVEN books with `observaciones` of `NULL`, `"juli"`, `"Juli"`, `"CANDE"`,
  and `"Juli y Cande"`
- WHEN the client requests `GET /api/books?sort_by=observaciones&sort_dir=asc`
- THEN the order is case-insensitive
- AND `NULL` rows appear consecutively
- AND `sort_dir=desc` reverses the order

### Requirement: Inventario Vendedora select

The Inventario page MUST render a `<select>` labelled `Vendedora` with four
options: `Todas` (empty value), `Juli`, `Cande`, `Juli y Cande`. The
selected value MUST be sent to `listBooks` as `seller`, MUST participate in
the React Query key, MUST reset the page to 1 on change, and MUST NOT break
existing filters or sort.

#### Scenario: Vendedora select renders four options

- GIVEN the Inventario page
- WHEN the user views the filter row
- THEN a `<select>` with label text `Vendedora` renders
- AND its options are exactly `Todas`, `Juli`, `Cande`, `Juli y Cande`

#### Scenario: Selecting a value sends seller to listBooks

- GIVEN the Inventario page with `Vendedora` set to `Cande`
- WHEN the books query runs
- THEN `listBooks` is called with `seller: "Cande"`
- AND the React Query key includes `seller`
- AND `page` is reset to 1

### Requirement: Inventario observaciones sortable column

The `observaciones` column in Inventario MUST be sortable: clicking its
header MUST toggle `sort_by=observaciones` and `sort_dir`. The default order
MUST remain ASC on first click, matching the other sortable columns.

#### Scenario: observaciones header toggles sort direction

- GIVEN the Inventario page
- WHEN the user clicks the `Observaciones` header
- THEN the next `listBooks` call uses `sort_by=observaciones&sort_dir=asc`
- AND clicking again uses `sort_dir=desc`

### Requirement: DataTable opt-in fixed layout and cell wrapping

`DataTable` MUST grow two optional boolean props, `fixedLayout` and
`wrapText`, that default to `false`. When `fixedLayout` is `true`, the
rendered `<table>` MUST use `table-fixed` and `column.className` MUST be
applied to the column header `<th>` (in addition to the existing `<td>`
behavior) so per-column widths work. When `wrapText` is `true`, body cells
MUST render multi-line text by allowing wrapping, so long `observaciones`
flows onto extra lines instead of widening the column. Default behavior
(`fixedLayout=false`, `wrapText=false`) MUST be unchanged so `Precios` and
other consumers keep today's layout.

#### Scenario: Inventario opts in to fixed layout + wrap

- GIVEN the Inventario page renders a `DataTable` with both props `true`
- WHEN the table mounts
- THEN the rendered `<table>` has class `table-fixed`
- AND body cells wrap (`whitespace-normal break-words`)
- AND each `observaciones` `<th>` and `<td>` carry the column's `className`

#### Scenario: Precios behavior is unchanged

- GIVEN the Precios page renders a `DataTable` without the new props
- WHEN the table mounts
- THEN no `table-fixed` class is present
- AND no wrapping class is present on body cells

## Constraints

- No DB migration. `observaciones` already exists at
  `backend/app/models/book.py` line 39.
- `compute_shares` outputs MUST stay byte-identical (decimal values, two
  decimal places) — guarded by `test_seller_split.py` and
  `test_earnings.py`.
- Out of scope: multi-select seller filter, free-text search on
  `observaciones`, pagination redesign, seller-specific dashboards.