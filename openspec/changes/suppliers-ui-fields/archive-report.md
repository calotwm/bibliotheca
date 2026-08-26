# Archive Report: suppliers-ui-fields

**Change**: suppliers-ui-fields
**Status**: Archived
**Date**: 2026-08-26

## Summary
UI-only change to the Proveedores section: removed all Editoriales artifacts
from the frontend (payload field, form input, table column, helper, state),
renamed column headers to "Cond. venta" / "DTO", added a "Notas" column, and
updated the Proveedores test suite to the new surface. Backend untouched.

## Final State Facts
- Verify verdict: **PASS** — 2/2 requirements, 4/4 scenarios, admitted by
  `gentle-ai sdd-verify-validate` (evidence_revision sha256:bc699da0...).
- Frontend tests: 62 passed (11 files; Proveedores suite = 5 tests).
- `npm run build` (tsc strict + vite): passes.
- Commit: `6d637b0` "feat(suppliers): replace editoriales with Cond. venta, Notas, DTO columns" (3 files, +38/−48). Not pushed yet at archive time (orchestrator pushes; Railway auto-deploys via GitHub source).

## Spec Sync
Delta spec at `openspec/changes/suppliers-ui-fields/specs/supplier-distributors/spec.md`
applied to the capability spec `openspec/specs/supplier-distributors/spec.md`:
- Requirement "Proveedores UI surfaces fields" updated (exact column order,
  renamed headers, Notas column, no Editoriales, payload contract).
- Requirement "Test coverage" updated (backend assertions unchanged; frontend
  assertions now cover the renamed surface without Editoriales reference).

## Deviations
None. Backend intentionally untouched; `Supplier.editorials` read type kept
because the API still returns `editorials: []`.

## Rollback
Revert commit `6d637b0`. UI-only, no data or schema impact.