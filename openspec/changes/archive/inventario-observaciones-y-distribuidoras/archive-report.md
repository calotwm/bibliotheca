# Archive Report: inventario-observaciones-y-distribuidoras

**Change**: inventario-observaciones-y-distribuidoras
**Date**: 2026-09-16
**Artifact store**: openspec
**Status**: ARCHIVED (final state at close)

---

## Change Summary

Three store-owner fixes for Inventario plus a copy-only Spanish rename on the
suppliers UI:

- **Seller bucket filter** — `GET /api/books?seller=Juli|Cande|Juli%20y%20Cande`
  partitions the catalog using the same rule as `compute_shares`. Blank/NULL
  `observaciones` lands in `Juli`. Invalid `seller` returns HTTP 400. The
  bucket predicate is shared between the router and `compute_shares` via a
  single `seller_bucket` helper in `backend/app/services/seller_split.py`,
  with `compute_shares` byte-identical on every input shape.
- **`observaciones` sort and wrap** — `observaciones` joins `SORT_FIELDS` with
  a NULL-stable, case-insensitive expression (`func.lower(func.coalesce(..., ""))`).
  Inventario marks the column sortable and wraps long text in-cell via two new
  opt-in `DataTable` props (`fixedLayout`, `wrapText`) that default to `false`
  so `Precios` and other consumers are byte-identical to today.
- **Rename copy only** — `Sidebar`, `Layout`, and `Proveedores.tsx` user-visible
  Spanish strings read `Distribuidoras / distribuidora`. Route, file, component
  name, type, API paths, and DB identifiers are untouched.

No DB migration; `observaciones` already existed.

## Final State Facts (at close)

Per the Final-State Authority hierarchy, the launch-prompt final-state facts
outrank intermediate snapshots. The numbers below are the terminal values for
the change.

### Verification Verdict

**PASS — 18/18 scenarios** (10/10 requirements), 0 blockers, 0 CRITICAL findings.

- `verify-report.md` reports `verdict: pass`, 6 SUGGESTIONs (non-blocking).
- Independent verifier (fresh context, not the author) verdict: `pass`,
  confidence 0.95, zero blockers.
- No CRITICAL verification issues; archive proceeds.

### Final Suite Counts (terminal)

| Suite | Result |
|-------|--------|
| Backend `py -m pytest` | **333 passed, 1 skipped, 35 warnings in 70.51s** (baseline before this change: 311 passed, 1 skipped; **+22 new tests**) |
| Frontend `npm run test` | **Test Files 15 passed (15) / Tests 105 passed (105)** (baseline before this change: 14 files / 98 tests; **+1 file / +7 tests**) |
| Frontend `npm run build` | **Passes** — tsc strict + vite, exit 0; bundle `dist/assets/index-Nb1g2mGZ.js 349.36 kB │ gzip: 101.39 kB` |

The `apply-progress.md` snapshot ("62.87s") is an earlier observation; the
launch-prompt final-state "70.51s" supersedes it. All other suite numbers are
stable across snapshots.

### Delivery / Production State (terminal)

| Artifact | Value |
|----------|-------|
| Repository | `calotwm/bibliotheca` |
| Branch | `main` |
| Commits (4) | `3107352` `fix(test): provide localStorage shim for Node 26 jsdom runs`; `01fbea0` `feat(inventory): seller filter, observaciones sort and wrapped cells`; `64619b2` `feat(ui): rename Proveedores to Distribuidoras`; `f34df0e` `chore(sdd): record inventario-observaciones-y-distribuidoras artifacts` |
| Push range | `1fdd403..f34df0e  main -> main` |
| Railway deployment | id `6487493950`, env `bibliotheca / production`, created by `railway-app[bot]` for sha `f34df0e` |
| GitHub commit status (`f34df0e`) | `state=success`, description `Success - libreria.up.railway.app` |
| Production `/health` | `200 {"status":"ok"}` |
| Production `/` | `200`, SPA index served |
| Production bundle (`/assets/index-Nb1g2mGZ.js`) | `200`, 349369 bytes — **same hash as local build** (proof the new code is live) |
| Production `/inventario` | `200`, `id="root"` present (SPA deep-link works) |
| Production `/api/books` (no token) | `401` (auth intact) |

No DB migration was required or created.

### Phase 0 Prerequisite (already applied and verified BEFORE this apply run)

`frontend/src/test/setup.ts` gained a minimal in-memory `localStorage` shim
(guarded by `typeof globalThis.localStorage === "undefined"`). Root cause:
Node 26.7.0 ships an experimental built-in `localStorage` global whose getter
already lives on `globalThis`, blocking the vitest+jsdom install of its own
implementation. `sessionStorage` was unaffected. The shim restored
`npm run test` from `Test Files 5 failed | 9 passed (14) / Tests 28 failed |
70 passed (98)` to `Test Files 14 passed (14) / Tests 98 passed (98)` before
this change started. Committed as `3107352` and is part of the push range.

## Task Completion

`tasks.md` shows **27/27 tasks complete** (all `[x]`, every Phase 0–7 box
ticked). No unchecked implementation tasks remain. Task Completion Gate
passes — no stale-checkbox reconciliation required.

## Spec Sync

Two new capabilities (`inventory-seller-filter`, `supplier-terminology`) were
added. Both delta specs in
`openspec/changes/inventario-observaciones-y-distribuidoras/specs/**/spec.md`
are full specs (not deltas); no main spec existed for either domain. They
were mechanically copied byte-identically into the canonical store:

```text
$ diff -r openspec/changes/inventario-observaciones-y-distribuidoras/specs/inventory-seller-filter/spec.md \
        openspec/specs/inventory-seller-filter/spec.md
(empty — byte-identical)

$ diff -r openspec/changes/inventario-observaciones-y-distribuidoras/specs/supplier-terminology/spec.md \
        openspec/specs/supplier-terminology/spec.md
(empty — byte-identical)

inv-src hash F5A7CB5D9557E2291E29C1F8C30ED84560B385149EE6BE42029ACAC2EE3BB9C7
inv-dst hash F5A7CB5D9557E2291E29C1F8C30ED84560B385149EE6BE42029ACAC2EE3BB9C7 (MATCH)
sup-src hash 433F21BFD18E2B230FFC3E02142E353FA4CFBFE244E14321106F9E576941B668
sup-dst hash 433F21BFD18E2B230FFC3E02142E353FA4CFBFE244E14321106F9E576941B668 (MATCH)
```

| Domain | Action | Details |
|--------|--------|---------|
| inventory-seller-filter | Created | 6 requirements, 14 scenarios — byte-identical full-spec copy |
| supplier-terminology | Created | 4 requirements, 4 scenarios — byte-identical full-spec copy |
| supplier-distributors | Untouched | This change adds a separate wording capability; `supplier-distributors` is not modified. (Note: the two prior archived cycles `supplier-distributors` and `suppliers-ui-fields` still sit in `openspec/changes/` rather than in `openspec/changes/archive/`; this archive leaves them exactly where they are per explicit instruction.) |

## Deviations from Design

Per `apply-progress.md §Deviations`, all three are intentional side effects of
the spec change, not bugs:

1. Two pre-existing Inventario tests (`shows an Observaciones column with the
   book value`, `shows Juli for a book with null observaciones`) had to be
   reworked to query `document.querySelectorAll('td')` / `'<th>'` because the
   new `Vendedora` `<select>` introduces literal `Juli` / `Juli y Cande`
   strings as `<option>` text, which would otherwise satisfy the prior
   `getByText` / `findByText` queries prematurely.
2. `test_list_books_sort_by_observaciones_desc_reverses_order` asserts the
   actual contract (`NULL/blank` grouped at the end on DESC; `juli y cande` >
   `juli` > `cande` reverse-sorted) instead of a strict
   `list(reversed(asc))` — more accurate against ties, more robust.
3. `func.lower(func.coalesce(..., ""))` was applied to `title` / `author` /
   `editorial` alongside `observaciones` because the existing `_sort_expression`
   branch was extended to share one coalesced expression. Behaviour for the
   existing fixtures is unchanged (all seeded values non-null).

## Independent Verification (fresh context)

- Verdict: `pass`. Confidence 0.95. Zero blockers.
- Proven: the three seller buckets partition the table exactly and NULL
  `observaciones` lands in `Juli`; `compute_shares` outputs unchanged
  (85/15, 0/100, 50/50) and `backend/tests/test_earnings.py` is unmodified;
  `sort_by=observaciones` is case-insensitive and NULL-stable via
  `func.lower(func.coalesce(..., ""))`; `DataTable` is backwards-compatible
  (new props default false, no other consumer passes `className`, Precios
  suite green); the seller filter runs in SQL and composes with pagination;
  an invalid `seller` returns 400; the wrap is Inventario-only; the rename
  leaves zero user-visible old-wording strings and changes no route/type/
  component/API/DB identifier; no DB migration was added.
- Non-blocking concerns raised (6 SUGGESTIONs in `verify-report.md`): see
  `verify-report.md §Issues Found → SUGGESTION`.

## Residual Gaps (honestly recorded)

- No production DB inspection of the actual distinct `observaciones` values —
  the filter is exercised in tests against fixtures, but production
  cardinality is not audited.
- No authenticated UI click-through in production — only `/api/books` 401,
  SPA index, and bundle-hash parity prove deploy. Behaviour in front of a
  logged-in user is unverified at the live URL.
- Pre-existing safety nets, not new findings: backend `pytest-cov` and
  frontend `@vitest/coverage-v8` are not installed; same coverage posture as
  prior cycles.

## Archive Disposition

Per orchestrator instruction, the change folder
`openspec/changes/inventario-observaciones-y-distribuidoras/` is moved
mechanically to `openspec/changes/archive/inventario-observaciones-y-distribuidoras/`
(no date prefix per the explicit instruction). The `openspec/changes/archive/.gitkeep`
is preserved.

```text
$ diff -r openspec/changes/inventario-observaciones-y-distribuidoras/ \
        openspec/changes/archive/inventario-observaciones-y-distribuidoras/
(empty — byte-identical)
```

(The `archive-report.md` written in this folder is additive and excluded from
the readback; it did not exist in the source snapshot.)

Note: the two earlier changes (`supplier-distributors`, `suppliers-ui-fields`)
still sit in `openspec/changes/` rather than in `archive/`. This archive
leaves them exactly where they are per the orchestrator instruction; the
prior cycles each shipped their own `archive-report.md` in place and were
not folder-moved either.

## Close-out

The SDD cycle for `inventario-observaciones-y-distribuidoras` is complete:
planned (proposal + design + 27 tasks), implemented (commits `3107352`,
`01fbea0`, `64619b2`), verified (PASS 18/18 by author + independent
verifier), deployed to production (Railway id `6487493950`, bundle hash
parity), and archived (this report). Ready for the next change.
