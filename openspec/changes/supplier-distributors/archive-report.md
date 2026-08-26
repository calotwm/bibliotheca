# Archive Report: supplier-distributors

**Change**: supplier-distributors
**Date**: 2026-08-26
**Artifact store**: openspec
**Status**: ARCHIVED (final state at close)

---

## Change Summary

Extended the Supplier domain with two optional distributor-commercial fields
(`discount`, `sale_condition`), seeded 17 distributor records idempotently via a
standalone script, and surfaced both fields in the Spanish Proveedores UI.

- **Model/schema/router**: `discount` + `sale_condition` as nullable `Text`
  columns carried through Base/Create/Update/Read schemas; router read/create
  and audit diffs include both fields.
- **Migration**: additive Alembic migration `bbd4ff3e1647` (nullable columns,
  downgrade drops both; `down_revision='7e82d91dbe21'`).
- **Seed**: `scripts/seed_suppliers.py` + versioned CSV, insert-if-missing by
  `name`, raw 1:1 fidelity (preserves `50% / 40%`, `;`-emails, malformed email).
- **UI**: Proveedores form inputs + table columns "Descuento"/"Condición de venta".
- **Tests**: extended `backend/tests/test_suppliers.py`; new
  `frontend/src/pages/Proveedores.test.tsx`.

Out of scope (unchanged): numeric discount math, import UI, editorial mapping,
auto-seed on deploy, source-data cleanup.

## Final State Facts (at close)

These are the terminal facts for the change, per the Final-State Authority
hierarchy. Where intermediate snapshots (`apply-progress.md`, `verify-report.md`)
differed, the higher-ranked final-state facts prevail.

### Verification Verdict

**PASS — 13/13 scenarios** (7/7 requirements), 0 blockers, 0 CRITICAL findings.

- `verify-report.md` refreshed to `verdict: pass`, scenarios 13/13,
  evidence_revision `sha256:983710a2677d1b31f167b1db517e6c4efa802e969d7256f26a33ef595d56f541`,
  admitted by the native validator (`gentle-ai sdd-verify-validate`).
- No CRITICAL verification issues; archive proceeds.

### Remediation Commit (after intermediate snapshots persisted)

After `apply-progress.md` and the earlier `verify-report` were persisted, a
remediation commit `fb3a0f4` ("test(suppliers): cover list payload, update audit
diff, edit flow") added 3 coverage assertions:

1. Backend list-payload fields (`discount`/`sale_condition`).
2. Backend update-audit old/new diff.
3. Frontend edit-flow `updateSupplier` payload.

`apply-progress.md`'s earlier "20/20" task-count prose was corrected to 26/26
(stale intermediate value; final value is 26/26).

### Final Suite Counts

| Suite | Result |
|-------|--------|
| Backend `py -m pytest` | **233 passed** (9 supplier tests), exit 0 |
| Frontend `npm run test` | **61 passed** (4 Proveedores tests), exit 0 |
| Build `npm run build` (tsc strict) | **Passes**, exit 0 |

These final counts are carried from the highest-ranked source (launch-prompt
final-state facts + refreshed `verify-report.md`), not from the older
`apply-progress.md` snapshot.

## Task Completion

`tasks.md` shows **26/26 tasks complete** (all `[x]`). No unchecked
implementation tasks remain. Task Completion Gate passes — no stale-checkbox
reconciliation required.

## Spec Sync

The capability spec at `openspec/specs/supplier-distributors/spec.md` was
confirmed **in sync** with the change delta spec at
`openspec/changes/supplier-distributors/specs/supplier-distributors/spec.md`:
**byte-identical** full-spec copies (7 requirements, 13 scenarios). This is a
new capability; the delta spec IS a full spec, so no delta merge was required.
No requirements were added, modified, or removed beyond the synced copy.

| Domain | Action | Details |
|--------|--------|---------|
| supplier-distributors | Verified in sync (already synced) | 7 requirements, 13 scenarios — identical full-spec copy |

## Archive Disposition

Per explicit orchestrator instruction, the change folder
`openspec/changes/supplier-distributors/` was **NOT moved** to
`openspec/changes/archive/`. The orchestrator handles the artifact commit + push
and directed the change folder to remain in place for now. This archive-report.md
records the final state as the audit trail for this cycle.

## Close-out

The SDD cycle for `supplier-distributors` is complete: planned, implemented
(commits `c242b4c`, `bf3c0df`, `8e45ac6`, `fb3a0f4`), verified (PASS 13/13), and
archived. Ready for the next change.
