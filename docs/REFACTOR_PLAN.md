# Deep Refactor Plan — v3 (2026-07-04, full-scan grounded)

**Status: Track A, Phases -1 through 3, and Phase-4 packets WP4.-1, WP4.0a,
WP4.0, WP4.1, WP4.2, and WP4.3a are complete. WP2.2 is committed as `c461840`; optional WP3.6 is
committed as `0cbedac`. WP4.0 measurement provenance remains unchanged head
`e46b67e`, with its ledger committed as `ca725c2`. Local integration verification
is complete through WP4.2: the history-preserving local merge is `d695188`, its
narrow post-merge gates passed, and nothing was pushed. WP4.3a is complete in an
isolated branch based on `e9062bc`, awaiting review and integration; no later page
packet has started.
Track B is mostly shipped; WPB.4 remains unimplemented
and product-risk gated.**

This supersedes v2. It incorporates:

- the v1 council review;
- the complete line-by-line scan on `scan/codebase-grounding` at `a6574b9`;
- `docs/SCAN_PROGRESS.md`, `docs/SCAN_FINDINGS.md`,
  `docs/SCAN_RECOMMENDATIONS.md`, and `docs/scan/PHASE_02.md` through
  `PHASE_22.md` from that scan worktree;
- a second review of high-risk scan claims against `main` at `b5e837d`.

The scan artifacts are merged into this checkout (WP-1.0, 2026-07-04):
`docs/SCAN_FINDINGS.md`, `docs/SCAN_RECOMMENDATIONS.md`, `docs/SCAN_PROGRESS.md`,
and `docs/scan/PHASE_02.md`–`PHASE_22.md`.

The scan's headline is right: the architectural direction survived, but the sizing and
sequencing did not. Python work needs broader schema/route scope, the proposed JS seams
miss real feature clusters and shared state, and CSS cleanup needs cascade and test-harness
prerequisites. The scan also found real bugs. Those belong in a separate behavior-changing
track and must never be smuggled into move-only refactor PRs.

---

## 1. Review disposition

### Accepted scan findings

- Startup and erase repeat the full initializer chain, and the chain has six
  `add_*` functions plus the base initializer, exercise-order migration, and backup
  tables—not the smaller inventory in v2.
- Filter-value behavior is spread across four implementations and two hand-maintained
  allowlists.
- Three additional route modules perform direct DB/domain work:
  `routes/workout_log.py`, `routes/body_composition.py`, and
  `routes/volume_splitter.py`; `routes/exports.py` is also a genuine fat route.
- `profile_estimator.py` has six natural clusters, not the three proposed in v2.
- `workout-plan.js` has roughly 660 lines with no destination in v2 and four mutable
  state variables crossing the guessed boundaries.
- `volume-splitter.js` contains a local `apiFetch` reimplementation that should be
  deleted once its JSON calls use the shared wrapper.
- CSS contains an undeclared `@layer` ordering trap, duplicate token vocabularies,
  six local token namespaces, a four-copy summary/frame block, and misfiled page CSS.
- Phase -1 closed the identified safety-net gaps: catalog tests are hermetic, the named
  vacuous E2E assertions now observe real outcomes, startup backup copying has direct
  tests, and fatigue-context E2E is a required branch-protection context.

### Accepted with stricter safeguards

- `utils.errors.not_found` and `handle_unexpected_error` appear shadowed by later
  registrations in `app.py`; delete only after an isolated runtime registration probe
  proves handler selection for HTML, XHR, 404, HTTPException, and generic Exception.
- `weekly_summary.STATUS_MAP`, `MovementCategory`, `HOME_BASIC_EQUIPMENT`, and the other
  definition-only constants remain safe Phase-0 candidates after a fresh repository-wide
  reference check.
- `scripts/seed_visual_baseline.py` may be archived, but the move must also disposition
  its documentation references and pyright-baseline entry. It is not literally
  reference-free across the repository.
- JavaScript dead code requires import/call-graph and runtime-wiring checks. A symbol
  assigned to `window` is not live merely because grep finds the assignment.

### Not accepted as behavior-preserving deletion

- The second `effective_sets.py` pipeline is production-unreferenced but exported,
  documented, and covered by 26 tests. Removing it changes a callable contract.
- The five HTTP endpoints with no product-frontend callers are pytest/E2E-pinned API
  surfaces. “No frontend caller” is not proof that a route is dead.
- `create_auto_backup_before_erase()` is production-unreferenced but has a tested public
  contract and a deliberately different persistence model from file-copy startup backup.
- `advanced_to_basic` remains test-enshrined. Do not remove it without an explicit
  contract decision.

These items go to the owner-decision queue. If removal is approved, use a deprecation or
contract-removal WP with explicit migration notes and authorized test changes.

### Disposition of remaining scan observations

- Consolidate the duplicate `get_request_id()` implementation onto
  `utils/request_id.py` in WP0.1 after identity/behavior tests.
- Keep `success_response()`/`error_response()` asymmetry unchanged. It is awkward but
  changing return types is a cross-repository response-contract migration, not cleanup.
- Keep the tested-but-unused export streaming helpers pending OD10; do not call them dead
  solely because current routes do not select them.
- Normalize the `<main>` landmark in WP-1.5 with accessibility coverage.
- Record hardcoded assisted-exercise names, missing fatigue landmarks, server-data-to-JS
  conventions, taxonomy mirrors, cache-busting strategy, and long calibration helpers in
  the duplication/deferred registry. They are drift risks, not proven refactor defects.
- Investigate the volume-splitter silent-failure path and backup refresh/confirmation race
  before promoting either to Track A; the scan observed risk but did not provide a complete
  failing regression case.
- Leave `get_related_calibration_candidate` and duplicate generator validation untouched;
  they are outside the current payoff/risk boundary unless later profiling or defects
  justify a dedicated protected-logic WP.

---

## 2. Global rules

1. **Refactor WPs preserve behavior.** Do not change calculations, DB shapes, API shapes,
   status codes, user-visible copy, event timing, or persistence semantics in a refactor PR.
2. **Bug fixes are separate.** Track A below contains behavior changes. One bug or one
   tightly coupled bug family per PR, with a regression test that fails before the fix.
3. **Protected zones may move but may not change:**
   - effective-set factors and informational-only behavior;
   - fatigue thresholds, bands, landmarks, and Stage-4 evidence artifacts;
   - estimator priority chain;
   - progression decisions;
   - weekly/session aggregation and null-routine semantics;
   - volume taxonomy/classification mappings;
   - replace-exercise HTTP-200 error outcomes;
   - the locked fatigue advisory copy;
   - all Phase 2D-D-gated work.
4. **Public/tested is not dead.** Removing a tested function or HTTP endpoint requires an
   owner-approved contract-removal WP. Test deletion is allowed only when that WP names
   the deleted contract and migration impact explicitly.
5. **Dead-code proof is language-aware.** Python checks include decorators, registration
   closures, imports, scripts, tests, CI, and docs. JS checks include imports, DOM wiring,
   inline handlers, dynamic lookup, `window` assignments and actual callers. CSS checks
   include templates, JS-created classes, E2E selectors, and visual-helper overrides.
6. **Gate each source-changing WP.** Record the pytest baseline, run focused tests during
   implementation, then full pytest plus the literal E2E specs named by the WP. Counts may
   change only for explicitly added regression tests or approved contract removals.
   Documentation-only WPs use the repository's docs self-review gate. Phase close uses
   `/verify-suite`.
7. **Preserve import contracts.** Original Python import paths remain valid. Before a
   module split, commit an import/export and import-order characterization test.
8. **One WP = one PR.** Aim for reviewable diffs. Mechanical moves over 400 lines are
   allowed only where marked; do not combine a large move with logic cleanup.
9. **Never stage `data/database.db`; never rename CI job `name:` values.**
10. **Parallel work requires isolation.** Before concurrent work involving the DB, dev
    server, pytest, or E2E, follow `docs/ai_workflow/PARALLEL_WORKFLOW.md` and create
    worktrees with `scripts/new-worktree.ps1`.
11. **Rollback quickly.** If a gate fails and one focused correction does not explain it,
    revert/stash the WP and report rather than widening scope.
12. **Use symbols, not line numbers, as execution anchors.** Scan line numbers are evidence
    pointers only and will drift.

---

## 3. Owner-decision queue — RESOLVED 2026-07-04

All ten decisions recorded with the owner on 2026-07-04.

| ID | Decision | Owner decision (2026-07-04) |
|---|---|---|
| OD1 | Is plan weight `0` valid for bodyweight/assisted exercises? | **Allow 0 kg.** Behavior-change WP: fix the falsy-check family (`exercise_manager.py` weight, plus order=0 in remove/reorder), rewrite `test_add_exercise_missing_weight` accordingly. |
| OD2 | What are canonical server bounds for plan/log updates? | **Add sanity bounds.** Behavior-change WP: define and enforce server-side limits (weight ≥0 with sane cap, RIR 0–10, min-reps ≤ max-reps) on add/update paths; new tests; docs then become true. |
| OD3 | Should `GET /export_to_excel` mutate `exercise_order` while assembling a workbook? | **Fix it.** Behavior-change WP: remove the hidden `recalculate_exercise_order` write from Excel export after WP1.8 extracts it. `/export_to_workout_log` was already POST-only and all repository callers already used POST, so no method or frontend migration is needed. |
| OD4 | Null routines: dropped from weekly frequency or bucketed as `Unassigned`? | **Unify as `Unassigned`.** Behavior-change WP on a protected calc zone: weekly summary gains an Unassigned bucket matching session summary. Golden fixtures (WP2.3) must land first; product-risk review required. |
| OD5 | Is the novice branch in `_calculate_weight_increment` a no-op below 20 kg intentionally? | **Make experience matter.** Behavior-change WP on a protected zone: experienced lifters get +5 kg below 20 kg too. Regression tests on both experience levels around the 20 kg boundary. |
| OD6 | Remove/deprecate the five frontend-unreferenced HTTP endpoints? | **Remove them.** Contract-removal WP: delete `/get_routine_options`, `/get_user_selection`, `/get_exercise_details/<id>`, `/get_filtered_exercises`, `/get_unique_values/<table>/<column>` plus their tests, with migration notes. Sequence AFTER WP1.1/WP1.2 (the last one is in scope there). |
| OD7 | Remove the test-only effective-sets pipeline, `advanced_to_basic`, `create_auto_backup_before_erase`? | **Remove all three.** Contract-removal WP(s) with explicit migration notes; authorized test deletions (~26 effective-sets pipeline tests, taxonomy test, backup-contract tests). Note: the pre-erase **file snapshot** in `/erase-data` is live and stays — only the unused DB-table variant goes. |
| OD8 | Wire or delete `showAutoBackupBanner`? | **Wire it up.** Small feature WP: erase flow shows the banner referencing the live file-copy snapshot in `data/auto_backup/` (NOT the OD7-removed DB-table function). E2E on the erase flow. |
| OD9 | Promote `fatigue-context.spec.ts` into required CI? | **Promote to required.** CI WP: add as a NEW job/context (never rename existing required contexts); land after it has run green as non-required for a few PRs. |
| OD10 | Retire the exported/tested streaming-threshold helpers no route uses? | **Keep them.** WP1.8 gives them a clear home during export extraction. |

Owner decisions produce separate WPs — drafted as **Track B** below (2026-07-04).
They are not permission to fold behavior changes into the refactor packets below.
OD1–OD5 supersede the corresponding "Deferred behavior fixes" entries in Track A;
OD6/OD7 removals must be sequenced after the Phase-1 extractions that touch the same
files. OD10 requires no WP (keep as-is; WP1.8 homes the helpers).

---

## Track A — confirmed bug fixes (before structural refactors)

Each item is a separate, small PR unless two entries explicitly share one root cause.

**Completed 2026-07-04.** A1–A8 landed as PRs #91–#98 (A4–A8 used
#92–#96; A2/A3 used #97/#98). The final integrated gate on PR #98 passed
1629 pytest tests and both required functional E2E shards (202 + 202). Track B
prerequisites that say "Track A complete" are now satisfied.

### A1 Toast severity contract

- Correct all five reversed-signature `app.js` calls: two warnings, one success, and
  two errors.
- Add Vitest or E2E coverage proving success/warning/error classes and messages.
- A warning on legacy misuse is optional; do not remove the legacy API in this PR.
- Gate: JS test plus starter-plan paths in `workout-plan.spec.ts`.

### A2 Workout-log duplicate submission

- Keep the debounced handler and remove the competing inline `onchange` path.
- Prove one edit causes exactly one `/update_workout_log` POST and one calibration update.
- Gate: focused pytest plus `workout-log.spec.ts` and `learned-calibration.spec.ts`.

### A3 Progression badge drift

- Extract the assisted-bodyweight decision used by all three client update paths.
- Add a date-change regression case.
- Gate: JS characterization plus `workout-log.spec.ts` and `progression.spec.ts`.

### A4 Error-page and fatigue error-path fixes

- Align `error.html` with the variables passed by all route error renderers.
- Call `is_xhr_request()` with its actual zero-argument contract.
- These are separate commits/PRs if their focused test surfaces are independent.
- Gate: `tests/test_priority7_error_handling.py`, fatigue route tests, and
  `error-handling.spec.ts`.

### A5 Backup atomicity

- Make `create_backup()` header and item inserts one transaction, following the existing
  restore transaction pattern.
- Add a forced-mid-insert rollback test and item-count invariant.
- Gate: full program-backup pytest plus isolated `program-backup.spec.ts`.

### A6 Event-listener cleanup

- Close every execution-style-picker path through one cleanup function.
- Invoke the existing workout-dropdown cleanup when the owner element is replaced/closed.
- Gate: Playwright listener instrumentation (or Vitest if WP3.1 has landed) plus
  workout-plan interaction E2E.

### A7 Export delay

- Remove the unconditional `time.sleep(0.5)` from workbook cleanup.
- Verify generated workbooks and error cleanup, not elapsed time alone.
- Gate: export pytest and a manual download smoke.

### A8 DatabaseHandler CTE write locking

- Make write detection recognize `WITH ... INSERT/UPDATE/DELETE` statements, including
  `maintenance.REBUILD_EIM_SQL`.
- Add concurrency/dispatch unit cases without changing transaction semantics.
- Gate: database/maintenance pytest and full pytest.

### Deferred behavior fixes

- Weight-zero semantics, update validation, export-GET mutation, null-routine
  bucketing, and novice progression semantics are now decided (OD1–OD5) and drafted
  as WPB.1–WPB.5 in Track B below.
- Token load order is handled as visual-gated WP4.-1, not hidden in Track A.

---

## Track B — owner-decided behavior and contract changes (OD1–OD9)

Drafted 2026-07-04 from the §3 decisions. Each WP is a **separate PR** with migration
notes in the PR description and updated test coverage (refactor invariant, `CLAUDE.md`).
None of these may ride inside a move-only refactor WP. Prerequisites vary per WP — Track B
is interleaved with the phases, not a block; the prerequisite column in each entry governs.
Execution requires the owner's Track-A/Plan-v3 sign-off boxes plus this section's approval
per the sign-off checklist.

**Status at `main` @ `cbd5a25` (2026-07-05):** WPB.1 (#103), WPB.2 (#107),
WPB.5 (#101), WPB.7 (#102), WPB.8 (#104), and WPB.9 are shipped. WPB.9's job
landed in #100 and became required after ten consecutive green PRs (#100–#109),
without renaming or removing an existing context. At that baseline, WPB.3, WPB.4,
and WPB.6 remained prerequisite-gated.

**Current update (2026-07-07):** Phase 1 is complete — WP1.1–WP1.8 all landed
(#123, #126, #127, #130, #124, #125, #121, #122). WPB.3 shipped in #128 and WPB.6
shipped in #129. WPB.4 remains prerequisite-gated (needs WP2.3 golden fixtures).
Integrated `main` @ `f9bfb50`: pytest **1708 passed**; required Chromium functional
shards **205 + 202**; smoke **10**, backup **20**, erase **2**, fatigue-context **6**;
Playwright inventory **504 tests / 30 specs**.

### WPB.1 (OD1) Allow plan weight 0 for bodyweight/assisted exercises

- Fix the falsy-check family in `utils/exercise_manager.py`: weight `0` treated as
  missing on add, and `exercise_order`/`order` `0` treated as missing in remove/reorder.
- Rewrite `test_add_exercise_missing_weight` to assert 0 is accepted and `None`/absent
  is still rejected.
- Prerequisite: Track A complete. Land before Phase 1 touches the same routes/utils.
- Gate: workout-plan pytest family plus `workout-plan.spec.ts`.

### WPB.2 (OD2) Server-side bounds for plan/log updates

- Define canonical limits in one place (`utils/constants.py` or the WP1.1 validator
  module if it has landed): weight ≥ 0 with a sane upper cap, RIR 0–10,
  min-reps ≤ max-reps.
- Enforce on add and update paths for plan and log; reject with `error_response()`.
- New boundary tests per field; update any docs that previously overstated validation.
- Prerequisite: WPB.1 (weight-0 semantics define the lower bound). Coordinate with
  WP1.1 if concurrent — the allowlist/validator module is the natural home.
- Gate: plan/log pytest families plus `workout-plan.spec.ts` and `workout-log.spec.ts`.

### WPB.3 (OD3) Excel export stops mutating exercise order

- Remove the `recalculate_exercise_order` write from `GET /export_to_excel`; workbook
  assembly becomes read-only even when stored order values are duplicate or `NULL`.
- `/export_to_workout_log` was already POST-only, and both live frontend callers plus
  active pytest/E2E callers already used POST. Pin that contract in tests; no method or
  frontend migration is required.
- Migration note: startup `initialize_exercise_order()` still initializes `NULL` values.
  It does not repair duplicate non-NULL order values; those remain unchanged until an
  explicit reorder operation.
- Prerequisite: **WP1.8 first** (landed in #122). **SHIPPED in #128** (`73f40ad`),
  2026-07-07. The plan wording above was partly stale: `/export_to_workout_log` was
  already POST and all callers already used POST, so the only defect fixed was the
  hidden `recalculate_exercise_order` write on `GET /export_to_excel`. Test delta was
  intentional: four obsolete mutation tests removed, three stronger read-only
  preservation tests added.
- Gate: export pytest family plus the export/workout-log E2E paths.

### WPB.4 (OD4) Weekly summary `Unassigned` bucket for null routines

- Protected calc zone. Weekly summary buckets null-routine rows as `Unassigned`,
  matching session summary, instead of dropping them from frequency.
- Prerequisite: **WP2.3 golden fixtures must land first**; product-risk review required
  before merge.
- Gate: weekly-summary pytest + goldens diff reviewed as intentional, plus
  weekly-summary visual/E2E specs.

**Risk-mitigation gate (reviewed 2026-07-17):**

- The production schema makes `routine` `TEXT NOT NULL`; the reachable case is an empty
  string, while `None` remains relevant to mocked/legacy rows. State explicitly that all
  falsy routine values coalesce into one synthetic `Unassigned` session.
- Freeze scope to session-derived metrics only: weekly raw/effective totals, reps, volume,
  status, contribution weights, rounding, response fields, and pattern coverage must not
  change. Decide separately whether `global_sessions` includes the synthetic bucket; do
  not let that denominator change happen implicitly.
- Add focused cases for empty/`None`, above- and below-1.0 frequency thresholds, multiple
  anonymous rows accumulating into one bucket, and mixed named/anonymous routines across
  the full counting-mode x contribution-mode matrix.
- Regenerate the WP2.3 golden only after reviewing the exact delta. For the existing Calves
  sentinel, the intended change is frequency `0 -> 1`; effective-mode `sets_per_session`
  `0.85 -> 5.1`; raw-mode `sets_per_session` `1 -> 6`; and effective-derived average/max
  `0/0 -> 5.1/5.1`. Weekly totals and classifications must remain identical.
- Add route/E2E assertions for the displayed frequency and average/max-per-session values,
  run summary-page functional and visual gates, and include migration notes describing the
  intentional semantic change and the conservative one-bucket assumption.

### WPB.5 (OD5) Experience-aware increment below 20 kg

- Protected calc zone. In `_calculate_weight_increment`, experienced lifters get
  +5 kg below 20 kg too (novice behavior unchanged).
- Regression tests on both experience levels around the 20 kg boundary (just below,
  at, just above).
- Prerequisite: Track A complete; product-risk review required (progression semantics).
- Gate: progression pytest family plus `progression.spec.ts`.

### WPB.6 (OD6) Remove the five frontend-unreferenced endpoints

- Delete `/get_routine_options`, `/get_user_selection`, `/get_exercise_details/<id>`,
  `/get_filtered_exercises`, `/get_unique_values/<table>/<column>` plus their tests.
- Migration notes list each removed route and its replacement (or "none — unused").
- Implementation baseline after WP1.2: pytest collection **1714 → 1694** (20 approved
  endpoint-contract cases removed); Playwright inventory **505 → 504** (the permissive
  routine-options API test removed). Migration replacements are recorded in
  `docs/CHANGELOG.md`.
- Prerequisite: **after WP1.1/WP1.2** — `/get_unique_values` is in WP1.2's scope; removing
  it earlier would churn that extraction. **SHIPPED in #129** (`f9bfb50`), 2026-07-07,
  rebased onto post-WP1.4 `main`. Also removed the endpoint-only
  `fetch_registered_unique_values`; `fetch_filter_values` and
  `ExerciseManager.fetch_unique_values` are preserved.
- Gate: full pytest (expected count drop documented) plus API-integration E2E.

### WPB.7 (OD7) Remove the three dead contracts

- Remove the second (test-only) effective-sets pipeline, `advanced_to_basic`, and the
  **DB-table** `create_auto_backup_before_erase` variant.
- The pre-erase **file snapshot** in `/erase-data` (live copy into `data/auto_backup/`)
  **stays** — verify the erase flow still produces it before merging.
- Authorized test deletions: ~26 effective-sets pipeline tests, the taxonomy test, and
  the DB-table backup-contract tests. Migration notes list every deleted public symbol.
- Prerequisite: after the Phase-1 extraction touching the same file, if any; must land
  **before or independent of** WPB.8 — the banner must never reference the removed
  function.
- Gate: full pytest (expected count drop documented) plus erase-flow smoke.

### WPB.8 (OD8) Wire `showAutoBackupBanner` into the erase flow

- Erase flow shows the banner referencing the **live file-copy snapshot in
  `data/auto_backup/`** — not the DB-table function WPB.7 removes.
- E2E asserting the banner appears post-erase with the snapshot reference.
- Prerequisite: coordinate with WPB.7 (either order, but the banner's data source is
  the file snapshot from day one).
- Gate: erase-flow E2E plus any program-backup pytest touching the banner's data.

### WPB.9 (OD9) Promote `fatigue-context.spec.ts` to required CI

- Add as a **new** job/context — never rename an existing required context (renames
  orphan branch-protection checks and hard-block PRs).
- Land only after the spec has run green as non-required on several consecutive PRs;
  record the observed runs in the PR description.
- Prerequisite: none code-side; timing-gated by the green-run streak.
- Gate: the new context green on the promoting PR itself; branch-protection update is a
  separate, reversible settings change.

---

## Phase -1 — evidence, docs, and gate hardening

**Completed 2026-07-05.** WP-1.0 evidence was already integrated; WP-1.1 through
WP-1.5 shipped in PRs #106, #105, and #108–#110. Final CI on PR #110 passed
1684 pytest tests, functional Chromium shards 206 + 202, fatigue-context 6, and
erase-flow 2. The full Playwright inventory is 505 tests across 30 specs.

### WP-1.0 Merge the scan evidence

- Bring `SCAN_PROGRESS.md`, `SCAN_FINDINGS.md`, `SCAN_RECOMMENDATIONS.md`, and
  `docs/scan/PHASE_*.md` from `scan/codebase-grounding@a6574b9` into the target branch.
- Documentation only; preserve provenance and do not edit findings to match this plan.

### WP-1.1 Documentation truth sync

**Completed in PR #106.**

- Correct the startup initializer inventory, blueprint count, current verified counts,
  handover SHA wording, route-validation claims, E2E spec ledger, and fatigue-context CI row.
- Correct stale `STATUS_MAP` import documentation; current `session_summary.py` imports only
  `EFFECTIVE_STATUS_MAP`.
- Gate: docs self-review and command/example dry run.

### WP-1.2 Hermetic pytest baseline

**Completed in PR #105.**

- Move `test_volume_taxonomy.py` and `test_catalog_invariants.py` off live
  `data/database.db` onto isolated fixtures or committed test fixtures.
- Add a guard test that fails if test DB resolution points at the live path.
- Gate: both files repeatedly, then full pytest with live DB hash unchanged.

### WP-1.3 Close prerequisite unit-test gaps

**Completed in PR #108.**

- Add direct tests for `create_startup_backup`, `lift_matching`, and `exercise_media`.
- Add import-order/export-surface tests needed by the estimator split.
- Extend body-fat JS↔Python parity to all four mandated functions, preferably through a
  shared fixture consumed by pytest and Vitest/E2E.
- Keep these characterization-only; no production changes.

### WP-1.4 Repair vacuous E2E assertions

**Completed in PR #109.**

- Replace `expect(true)`, `x || true`, and equivalent non-assertions in
  `validation-boundary`, `empty-states`, `exercise-interactions`, and
  `superset-edge-cases` with observable outcomes.
- Do not introduce WPB.2's approved-but-not-yet-implemented validation behavior here;
  characterize current behavior or mark the case pending on WPB.2.

### WP-1.5 Normalize the main landmark

**Completed in PR #110.**

- Make `base.html` own the single `<main id="main-content">` landmark and replace nested
  page-level `<main>` elements with neutral containers, or choose the inverse pattern and
  apply it consistently. Never produce nested or duplicate main landmarks.
- Preserve page IDs/classes/data hooks and skip-link target behavior.
- Gate: template pytest plus accessibility and smoke-navigation E2E.

---

## Phase 0 — safe dead code and repository hygiene

### WP0.1 Proven Python dead code/constants

- Runtime-probe the shadowed error handlers; remove only the two proven unreachable
  registrations while preserving live 400/422/500/APIError behavior.
- Recheck and remove definition-only constants:
  `HOME_BASIC_EQUIPMENT`, `DEFAULT_SETS_TARGET`, `MovementCategory`, `REP_RANGE_PCT`,
  and `weekly_summary.STATUS_MAP`.
- Replace the duplicate `utils.errors.get_request_id` helper with an import from
  `utils.request_id`; preserve request-header and generated-ID behavior.
- Do not touch OD6/OD7 candidates.
- Gate: focused error/summary/movement/estimator tests, then full pytest.

### WP0.2 Empty `utils/__init__.py`

- Reconfirm zero facade importers, including function-local and dynamic imports.
- Reduce the file to its package docstring; concrete module imports remain canonical.
- Must land before filter/module relocation work.
- Gate: full pytest plus isolated app boot and `GET /`.

### WP0.3 Archive one-off scripts and root baselines

- Recheck scripts against code, tests, CI, scheduled tasks, pyright baseline, and docs.
- Preserve all Stage-4 observer automation and live mapping/build helpers.
- Archive the v2 candidates plus `seed_visual_baseline.py` only after updating its docs
  and static-analysis disposition; do not confuse it with
  `e2e/scripts/build_visual_seed.py` or `prepare_visual_db.py`.
- Remove root `baseline_e2e.txt`/`baseline_pytest.txt` and ignore future copies.
- Gate: full pytest, pyright baseline diff, visual seed smoke, CI.

### WP0.4 JavaScript dead-code sweep

Handle one coherent cluster per PR, with import/call/runtime proof:

- `charts.js` and its unreachable initializer path;
- `summary.js` no-op exports (coordinate with WP3.2);
- duplicate Add-Exercise flow in `exercises.js`;
- dead workout-log filter block and nonexistent endpoint call;
- dead progression modal/card functions;
- runtime-unreachable table-responsiveness exports;
- `showAutoBackupBanner` only after OD8.

Do not delete CSS here; CSS reachability needs the Phase-4 selector/visual harness.

---

## Phase 1 — route and service boundaries

Goal: routes parse/validate HTTP input, call utils services, and shape responses. Preserve
all endpoint URLs and response envelopes unless an OD-approved contract WP says otherwise.

**STATUS: COMPLETE (2026-07-07).** All eight work packets landed on `main` @ `f9bfb50`
via PRs #123, #126, #127, #130, #124, #125, #121, #122. Integrated CI: pytest **1708
passed**; required Chromium functional shards **205 + 202**; Playwright inventory **504
tests / 30 specs**. Each WP preserved endpoint URLs and response envelopes.

### WP1.1 Central filter allowlist and validators — **SHIPPED (#123)**

- Move `ALLOWED_TABLES`, `ALLOWED_COLUMNS`, and validation into a utils-owned registry.
- Reconcile it explicitly with `FilterPredicates.VALID_FILTER_FIELDS`; encode aliases and
  purpose-specific subsets instead of silently taking a union.
- Keep route-level re-exports for existing tests/callers.
- Add malicious table/column cases and vocabulary parity tests.

### WP1.2 Extract both route-level unique-value contracts — **SHIPPED (#126)**

- Move the workout-plan specialized normalization contract to
  `utils/filter_values.fetch_filter_values`.
- Move `/get_unique_values/<table>/<column>` query behavior to a separate utils function
  using the central registry.
- Keep `ExerciseManager.fetch_unique_values(table, column)` as a distinct generic/internal
  contract for now; do not merge signatures or normalization semantics.
- Gate: filter/exercise-manager pytest plus workout-plan, exercise-interactions, and API E2E.

### WP1.3 Extract replace-exercise service — **SHIPPED (#127)**

- Move candidate selection, deduplication, and swap persistence to
  `utils/exercise_replacement.py`.
- Keep parsing and structurally identical response envelopes in the route, including the
  three HTTP-200 error outcomes.
- Gate: replacement pytest, `replace-exercise-errors.spec.ts`, `workout-plan.spec.ts`.

### WP1.4 Extract superset service — **SHIPPED (#130)**

- Move validation queries, pairing, persistence, and suggestions to `utils/supersets.py`.
- Preserve ID generation, ordering, messages, and response shapes even where improvement
  is tempting.
- Persistence coverage includes the `remove_exercise` partner-unlink, extracted to
  `unlink_partner_for_removal(db, exercise_id, superset_group)`. Unlike the other service
  entry points it reuses the caller's `DatabaseHandler` so the partner-null, log-delete,
  and exercise-delete continue to share one handler (connection + write lock); behavior
  and the removal log are preserved exactly.
- Gate: superset pytest, `superset-edge-cases.spec.ts`, `workout-plan.spec.ts`.

### WP1.5 Workout-log service boundary — **SHIPPED (#124)**

- Move mutations and calibration-trigger orchestration from `routes/workout_log.py` to
  `utils/workout_log_service.py`.
- Do not add validation until OD2 is resolved.
- Gate: workout-log/calibration pytest and workout-log/learned-calibration E2E.

### WP1.6 Body-composition service boundary — **SHIPPED (#125)**

- Move CRUD/query logic to utils while keeping body-fat formulas unchanged.
- Preserve the JS↔Python parity fixture introduced in WP-1.3.
- Gate: body-composition pytest and `body-composition.spec.ts`.

### WP1.7 Volume-splitter service boundary — **SHIPPED (#121)**

- Move history/get/delete, range defaults/sanitization, and export orchestration to utils.
- Document the second classification vocabulary; do not consolidate it with canonical
  volume classes in this behavior-preserving WP.
- Gate: volume-splitter pytest, volume-splitter and volume-progress E2E.

### WP1.8 Export service boundary — **SHIPPED (#122)**

- Move mapping tables, dataframe transforms, query construction, sheet assembly, and
  export-to-log persistence into utils modules.
- Preserved `GET /export_to_excel`'s exercise-order side effect at extraction time;
  WPB.3 (#128) subsequently removed that side effect per OD3.
- Gate: export pytest plus plan export/download and workout-log import flows.

`routes/user_profile.py` needs no extraction WP: its handlers are already thin; the file's
size is mostly static view-model data.

---

## Phase 2 — Python module structure and schema ownership

### WP2.1a Estimator characterization and dependency map

- Freeze the supported export surface, underscore names used by tests, lift-matching alias
  identity, and both import orders with `strength_calibration`.
- Document the six clusters and their dependency direction before moving code.
- No production move in this WP.

### WP2.1b–f Staged `profile_estimator` extraction

Keep `utils/profile_estimator.py` as the stable public facade/orchestrator. Extract leaf
clusters into an internal package such as `utils/_profile_estimator/` in separate PRs:

1. constants and lookup tables;
2. trace builders;
3. accuracy and coverage-guidance helpers;
4. cohort ranges/bars/donut;
5. bodymap `muscle_coverage_state` helpers.

The estimation priority chain remains in the facade/core until leaf moves are stable.
Lazy `strength_calibration` imports stay function-local. Each move is mechanical; no
renaming or “cleanup while here.” This staged shape replaces v2's risky atomic 2,418-line
file-to-package conversion.

- Gate each PR: estimator and calibration pytest; final close adds user-profile and
  learned-calibration E2E plus import-order tests.

### WP2.2 Decompose plan-generator functions

- Extract helpers from `_score_exercise`, `_apply_priority_muscle_boost`, `persist`, and
  `generate_starter_plan` without reordering scoring.
- Preserve `persist()`'s inner swallow/log/continue and outer re-raise tiers exactly.
- Removing the unused `routine` parameter changes a callable signature; defer it unless a
  separate internal-caller proof authorizes it. The unused loop variable may be cleaned.
- Gate: unmodified plan-generator tests plus starter-plan E2E.

**Completed 2026-07-16.** Extracted scoring, priority-allocation, persistence, and
result-assembly helpers without changing the public callable signature, score ordering,
row-order mutation, or the inner-continue/outer-reraise exception tiers. Added explicit
contract tests for those seams. Local gate: **1,723 pytest passed** and the complete
API-integration + workout-plan Chromium pair **92 passed**.

### WP2.3 Weekly-summary decomposition with durable goldens

- First commit deterministic seeded golden fixtures for both public calculations,
  canonicalized as JSON and checked in tests—not pasted only into a PR description.
- Extract private helpers in the same module, using session-summary structure as a model.
- Preserve Effective/Raw side-by-side shape, warning order, rounding, null-routine
  behavior, and movement fallback pending OD4.
- Gate: all summary/pattern/effective-set tests, golden equality, summary-pages and API E2E,
  product-risk review.

### WP2.4 Staged fatigue-module split

- Freeze exports and golden outputs first.
- Move the four banner-delimited concerns—phase-1 core, per-muscle, period-window, SFR—into
  internal modules while `utils/fatigue.py` remains the public facade.
- Do not consolidate duplicated scored-row or tie-break rules in the move PRs; record them
  in the duplication registry below.
- Gate: all fatigue pytest, fatigue/fatigue-context/summary E2E, product-risk review.

### WP2.5 Duplication registry (document-only decisions)

Record owners, current semantic differences, tests, and a future convergence decision for:

- fatigue scored-row and sort tie-break rules;
- estimator/calibration load-basis arithmetic;
- weekly/session aggregations and the exported effective-set pipeline;
- movement-pattern classification forks;
- weekly/session null-routine behavior;
- JS/Python taxonomy lists;
- assisted-bodyweight catalog names and fatigue landmark coverage;
- the three server-data-to-JS conventions and static-asset cache-busting policy;
- volume-splitter silent failures and backup refresh/confirmation interaction;
- response-helper return-type asymmetry and long protected calibration helpers.

Do not consolidate protected logic merely because arithmetic looks identical.

**Shipped** — see [`docs/DUPLICATION_REGISTRY.md`](DUPLICATION_REGISTRY.md) (14 items,
docs-only, zero code change; no consolidation performed). The one drift-removing
consolidation (schema-init manifests) is deferred to WP2.6.

### WP2.6 Schema registry — last Python WP

- Create `utils/schema_registry.py` with
  `run_all_initializers(*, force_base: bool = False)`.
- Call every initializer in current order: base schema, all six `add_*` functions,
  exercise-order migration, then `utils.program_backup.initialize_backup_tables`.
- Remove the duplicate progression-goals instance/module implementation only after caller
  inventory proves one can become a thin compatibility wrapper.
- Startup passes `force_base=False`; erase and isolated test setup pass `True` where they
  currently force base reinitialization.
- Move `initialize_exercise_order`, `column_exists`, and `table_exists` to utils and keep
  temporary route re-exports.
- Define canonical owned-table/drop ordering in utils and consume it from erase paths.
  Preserve child-before-parent drops and the pre-erase file snapshot.
- Reconcile `maintenance.py`'s drifted isolated-muscle schema with the canonical definition;
  do not create a new table shape.
- Classify callers before editing:
  - full-startup mirrors migrate to the registry;
  - isolated initializer/migration tests remain direct;
  - old-schema fixtures deliberately remain partial.
- Keep `create_startup_backup()` outside the registry and after initialization.
- Explicit large cross-cutting WP; architecture and code review required.
- Gate: `/verify-suite`, isolated backup restore, fresh scratch-DB boot, erase/reinitialize
  smoke, legacy-schema fixtures, and proof the live DB was untouched.

---

## Phase 3 — JavaScript characterization, extraction, and transport

Decision remains plain JavaScript + Vitest; no TypeScript conversion.

### WP3.1 Vitest scaffold

- Add pinned `vitest` and `jsdom`, config, `test:js`, and a non-required CI job without
  renaming existing contexts.
- Seed with genuinely pure `exercise-helpers.js` tests. `toast.js` is DOM/Bootstrap code;
  test it only with explicit DOM and Bootstrap fakes, not as a “trivial pure helper.”

### WP3.2a–d Extract inline scripts one page at a time

Separate PRs:

1. weekly summary;
2. session summary;
3. workout plan;
4. welcome/base only if their blocks remain non-trivial after audit.

Preserve script type, placement, DOM-ready timing, globals, and mode defaults. The summary
inline scripts are the live implementation; do not merge them into no-op `summary.js`.
Delete that file only when all imports/callers are proven gone.

- Gate each page with matching pytest and literal feature-map E2E; base/welcome extraction
  additionally runs smoke-navigation, nav-dropdown, and dark-mode.

### WP3.3 Characterize workout-plan seams and shared state

- Write tests for payload builders, formatting, estimate rendering data, execution-style
  decisions, replacement payloads, Add-Exercise validation/payloads, and superset helpers.
- Introduce a named state module or explicit dependency object for
  `selectedExerciseIds`, `supersetColorMap`, `allExercisesCache`, and
  `currentRoutineTabFilter` before feature splitting.
- No DOM feature move until these tests are green.

### WP3.4a–h Split `workout-plan.js` by real feature boundaries

Use separate mechanical PRs, allowing large move-only diffs:

- `state.js` — **delivered by WP3.3 (#147).** The four shared values
  (`selectedExerciseIds`, `supersetColorMap`, `allExercisesCache`,
  `currentRoutineTabFilter`) already live in `workout-plan-state.js` as a singleton the
  monolith mutates inline; no accessor/mutator functions remain to move, so no separate
  `state.js` move-only PR is needed. Routine-tab/table behavior folds into WP3.4b below,
  importing the existing state singleton.
- `table.js` including adjacency/color integration points, plus the routine-tab filter/render
  functions (state singleton imported, not re-declared);
- `estimates.js` including fatigue context/nudge;
- `execution-style.js`;
- `replacement.js`;
- `add-exercise.js`;
- `supersets.js` with table dependencies injected explicitly;
- `media.js` and a thin `index.js` wiring entry.

Preserve the single entry script and event timing. Run Vitest plus workout-plan,
exercise-interactions, superset-edge-cases, fatigue-context, learned-calibration, and
replace-exercise-errors E2E after every boundary-affecting move.

### WP3.5 JSON API transport consolidation

- Re-run a repository-wide raw-fetch inventory after inline extraction.
- Migrate JSON app-endpoint calls to shared `apiFetch`/`api`.
- Delete `volume-splitter.js`'s local envelope/error wrapper rather than layering the
  shared wrapper beneath it.
- **Keep raw fetch** for static SVG/text assets in `bodymap-svg.js` and
  `muscle-selector.js`, and for blob/download exports, because the wrapper has no binary
  contract. Document every intentional exception.
- Coordinate bodymap files with the queued heatmap workstream.
- Gate: Vitest, full pytest, API integration, volume, plan, profile, navigation, and export
  download flows.

### WP3.6 Optional user-profile split

Only after the core JS track: characterize and split the 1,483-line file by demographics,
reference lifts, coverage/bodymap, calibration review, and settings toggles. Consolidating
the two optimistic-toggle paths is a later behavior-aware cleanup, not part of move-only PRs.

**Completed 2026-07-17 in the current working tree.** The original entry module is now a
small coordinator over focused data, forms/autosave, insights, bodymap, settings, and
calibration-review modules. Initialization order, DOM hooks, API endpoints, payloads,
toasts, rollback behavior, and the two distinct optimistic-toggle implementations are
unchanged. Added pure estimator-seam characterization tests. Gate: Vitest **105 passed**,
focused Python **75 passed**, full pytest **1,723 passed**, and profile +
learned-calibration + fatigue-context Chromium **38 passed** against the isolated E2E
database.

---

## Phase 4 — CSS foundation, visual harness, then cleanup

Stay on structured plain CSS. SCSS continues to own Bootstrap customization plus its
existing fatigue/volume-panel partials; remember those selectors are compiled into
`bootstrap.custom.min.css` and are part of the collision audit.

### Visual contract for every CSS WP

- Use `PW_VISUAL_SEED=1`; never seed or rewrite the live DB.
- Windows compares `e2e/__screenshots__/win32`; the manually dispatched `visual-linux`
  deep-gate job compares Linux baselines.
- Run the affected functional specs as well as snapshots. Pixel equality alone cannot
  catch selector-helper mistakes.
- Rebaseline only for intentional, owner-reviewed visual changes on both platforms.

### WP4.-1 Cascade and load-order foundation

- Load `tokens.css` before every consumer bundle.
- Declare one explicit `@layer` order covering existing layers before removing any
  `!important` declarations.
- Inventory selectors compiled into `bootstrap.custom.min.css`.
- No class rename, token-value change, or bulk de-`!important` work here.
- Gate: full functional frontend set plus byte-identical visual comparison.

**Completed 2026-07-16 in the isolated WP4 worktree.** `tokens.css` now loads
before Bootstrap's compiled app partials and every global/route consumer. One
explicit order preserves the prior implicit precedence as `workout`, `navbar`,
`workout-dropdowns`, `welcome`; the 18-bundle cap and all ten route owners are
unchanged. The compiled artifact inventory found 1,429 unique selector entries,
including 58 fatigue and 57 workout-plan volume-panel entries owned by SCSS.
Four focused contracts, blocking static checks, Vitest (93), and the complete
required Chromium set (407) passed. Seeded visual comparison reproduced the
unchanged animated-GIF known-reds with identical mismatch counts; no snapshot
was rebaselined. Full evidence: [`CSS_PHASE4_WP4_-1_EVIDENCE.md`](CSS_PHASE4_WP4_-1_EVIDENCE.md).
WP4.0a followed and is not included in this packet.

### WP4.0a Harden visual and functional selectors

- Replace visual-helper hardcoded presentation classes with stable `data-testid`/data
  hooks where appropriate.
- Replace exact-RGB assertions in nav/summary functional specs with token-aware semantic
  assertions or snapshots without weakening what they prove.
- Add User Profile and Backup to `visual.spec.ts`; v2's page list omitted both while
  scheduling their bundles for cleanup.
- Generate and review both platform baselines before CSS restructuring.

**Completed 2026-07-17 from committed WP4.-1 (`6e0a408`).** Stable
`data-visual-*` hooks replace visual-helper presentation classes, nav/summary
color contracts resolve their owning CSS variables, and Profile/Backup expand
each platform matrix from 48 to 60 images. All 12 new images per platform were
reviewed and passed update-free comparison. The 48 old Windows images stayed
byte-identical; Linux artifact review rejected 17 regenerated legacy variants
and imported only the 12 missing images. The Linux compare's 11 reds were all
confined to pre-existing animated signature/exercise-thumbnail pixels; no new
route failed. Static/unit/Python gates and the full 407-test functional set are
verified. See
[`CSS_PHASE4_WP4_0A_EVIDENCE.md`](CSS_PHASE4_WP4_0A_EVIDENCE.md). WP4.0 followed
and is not included in this packet.

### WP4.0 Fresh known-red ledger

- Run the complete functional and visual deep gates on unchanged `main` after WP4.0a.
- Record exact current reds in this plan and handover. Do not inherit the May ledger.

**Completed 2026-07-17 on unchanged branch head `e46b67e`.** Fresh gates:
selector/cascade contracts **7**, blocking flake8 **0**, tsc passed, Vitest
**93**, full pytest **1,722 passed + 2 visual-seed catalog reds**, and the exact
required Chromium functional list **407/407**. Update-free Windows visual
comparison produced **59 passed + 1 animated-frame red**; its serial thumbnail
companion produced **1 passed + 1 animated-frame red + 16 not run**. Fresh
pinned-Linux compare run
[29539611526](https://github.com/avihay1989/Hypertrophy-Toolbox-v3/actions/runs/29539611526)
produced **51 passed + 11 animated-frame reds + 16 not run**, plus one
initial-attempt profile GIF flake that passed retry. Every report/diff was
inspected; there was no unexplained cascade or layout regression. All 156
snapshot PNGs, generated Bootstrap CSS, the main live DB, and the unrelated
main-checkout WP2.2 edits stayed byte-identical. No snapshot was updated.
Complete ledger:
[`CSS_PHASE4_WP4_0_EVIDENCE.md`](CSS_PHASE4_WP4_0_EVIDENCE.md). WP4.1 is next
and is not included in this packet.

### WP4.1 Token vocabulary consolidation

- Inventory hardcoded values, duplicate spacing vocabularies (`--space-*` vs `--s-*`),
  and six local namespaces (`--wl-*`, `--nav-*`, `--bc-*`, `--backup-*`, `--volume-*`,
  `--fatigue-*`).
- Define alias/deprecation mapping before consumption; adding aliases must be visually
  neutral.
- Add stylelint as non-required measure-only CI with pinned rules and a baseline report.

**Completed 2026-07-17 in the isolated `wt/wp4-1-token-vocabulary`
worktree.** The frozen inventory distinguishes responsive layout spacing from
fixed component spacing: new `--layout-space-*` definitions retain every
former `--space-*` value, while `--space-*` remains a compatibility alias and
`--s-*` remains fixed. Only exact `--wl-*` status/duration and `--nav-*`
spacing matches were aliased; all other local feature namespaces remain
intact. Pinned Stylelint 16.11.0 measures 7,202 pre-change warnings across 21
sources and reports a non-blocking CI delta; no required context was renamed.
Static, unit, Python, functional Chromium, and update-free visual gates passed
with only the exact WP4.0 known reds. All 156 screenshots, generated Bootstrap
CSS, and live databases stayed byte-identical. Evidence:
[`CSS_PHASE4_WP4_1_EVIDENCE.md`](CSS_PHASE4_WP4_1_EVIDENCE.md). WP4.2 is next
and is not included in this packet.

### WP4.2 Shared-frame dedupe and ownership repair

- Extract the four-copy weekly/session/log/plan frame block once into `components.css`.
- Relocate the roughly 600 lines of log/summary content misfiled in
  `pages-workout-plan.css`.
- Delete only template/JS/E2E-proven dead selectors.
- Treat this as cascade-sensitive structural movement with full visual gates.

**Completed 2026-07-18 in the isolated `wt/wp4-2-shared-frame-dedupe`
worktree.** The shared block is owned once in `components.css` under
`:where(#workout, .workout-log-page, .summary-frame)`; route-specific log and
summary surfaces remain later in their route bundles. A diagnostic rejected the
initial document-wide `html:has(...)` gate: it changed masked Chromium
compositing on Progression despite no changed matched rule or computed value.
Direct container scope restores byte-identical Progression output. The five CSS
files shrink by a net **3,668 lines**. Contracts **12/12**, affected Chromium
**84/84**, required Chromium **407/407**, pytest **1,733 + 2 known catalog reds**,
and update-free visual locks all match. Stylelint falls from the 7,202 baseline
to **6,444** with unchanged selector ceiling warning counts and zero parse/config
errors. All 156 snapshots, generated Bootstrap, and protected DBs are unchanged.
Evidence: [`CSS_PHASE4_WP4_2_EVIDENCE.md`](CSS_PHASE4_WP4_2_EVIDENCE.md). The
packet was integrated into local `main` as merge `d695188`; narrow post-merge
gates passed, nothing was pushed, and WP4.3 had not started.

### WP4.3 Page dark-mode/token cleanup

One page per PR, smallest first. Use `pages-user-profile.css` as the target pattern but do
not churn it merely for consistency. Suggested order:

1. backup;
2. body composition;
3. progression;
4. volume splitter;
5. welcome;
6. session summary;
7. weekly summary;
8. user profile (audit/minimal cleanup);
9. workout plan, split into coherent internal sections;
10. workout log, split into multiple WPs because its per-theme colors and 375
    `!important` declarations make it redesign-sized.

**WP4.3a Backup completed 2026-07-18 in isolated
`wt/wp4-3-backup-dark-token-cleanup`.** Five exact repeated Backup values now use
semantic page-local tokens, unused `--backup-warm` was removed, and the existing
exact border token was reused. No shared near-match or page-local dark rule was
mechanically changed. Browser auditing preserved computed values and declaration
owners for 16 representative dynamic targets in both themes. Pinned Stylelint
falls **6,444 → 6,435** with no increase to duplicate, specificity, or important
counts. Contracts **13/13**, focused Backup Chromium **20/20**, required Chromium
**407/407**, and pytest **1,734 + 2 catalog known-reds** match the expected gates;
all six Backup variants pass and the full suites reproduce only the exact WP4.0
known reds. All integrity locks are unchanged. Evidence:
[`CSS_PHASE4_WP4_3A_EVIDENCE.md`](CSS_PHASE4_WP4_3A_EVIDENCE.md). Review and
integrate this packet only; the next WP4.3 page has not started.

### WP4.4 Shared bundles, navbar, and `theme-dark.css`

- Handle base/layout/components/a11y/motion separately from navbar/theme.
- Triage navbar's three live generations rule by rule.
- Triage `theme-dark.css` into legacy values versus legitimate token remaps; do not bulk
  delete it.
- Final goal: theme file contains only justified token swaps or is removed after proof.
- Gate: full visual deep gate, dark-mode, nav-dropdown, accessibility, summary-pages.

### Phase-4 success metrics

- Zero unjustified visual diffs from the WP4.0 ledger.
- No increased maximum specificity or unexplained `!important` count.
- Duplicate-selector/declaration counts decrease monotonically after the measure baseline.
- Total hand-maintained CSS reduction: 30% required target, 40% stretch target. Line count
  is secondary to ownership, cascade safety, and visual equivalence.

---

## Continuous track — pyright baseline burn-down

- One file or tightly coupled diagnostic family per WP.
- Type-only changes; no behavior refactors disguised as typing fixes.
- Baseline diagnostic multiset may only shrink; regenerate with the existing script when
  removals are intentional.
- Gate: zero net-new diagnostics, lower count, focused tests, then full pytest.

---

## Execution order and phase gates

| Order | Track/phase | Prerequisite | Close gate |
|---|---|---|---|
| 1 | Track A safe bug fixes | owner approval of behavior-changing track | focused regression + full pytest/E2E union |
| — | Track B owner-decided changes (WPB.1–WPB.9) | per-WP prerequisites in Track B; interleaved with phases, not a block | per-WP gate + migration notes in every PR |
| 2 | Phase -1 evidence/docs/tests | scan docs merged | `/verify-suite`; live DB unchanged |
| 3 | Phase 0 dead code/hygiene | hermetic baseline | `/verify-suite` + pyright baseline diff |
| 4 | Phase 1 route boundaries | Phase 0 import cleanup | `/verify-suite` + API integration |
| 5 | Phase 2 Python structure/schema | Phase 1; schema WP last | `/verify-suite` + backup/fresh-DB/erase smokes |
| 6 | Phase 3 JS | Vitest scaffold; may overlap Python only in isolated worktrees | Vitest + `/verify-suite` |
| 7 | Phase 4 CSS | WP3.2 scripts stable; WP4.-1/0a/0 complete | both-platform visual deep gate + functional frontend |

At every phase close, update `docs/MASTER_HANDOVER.md`, the verified-count block in
`CLAUDE.md`, and this plan's status. Do not mark a phase complete while follow-up contract
decisions are silently outstanding; either resolve them or leave them explicitly deferred.

## Sign-off checklist

- [x] v1 council findings retained or superseded explicitly.
- [x] Full scan completed at `scan/codebase-grounding@a6574b9`.
- [x] Scan recommendations reviewed rather than copied verbatim.
- [x] Behavior-changing bugs separated from behavior-preserving refactors.
- [x] Prior review gaps incorporated: visual page coverage, static-fetch carve-outs,
  schema force semantics, durable goldens, import characterization, realistic WP sizing,
  and parallel isolation.
- [x] Scan evidence merged into the implementation branch (2026-07-04; WP-1.0).
- [x] Owner decisions OD1–OD10 recorded (2026-07-04; see §3).
- [x] OD follow-ups drafted as Track B work packets WPB.1–WPB.9 (2026-07-04).
- [x] Owner approves Track A execution (2026-07-04).
- [x] Owner approves Track B execution (behavior + contract changes) (2026-07-04).
- [x] Owner approves Plan v3 for refactor execution (2026-07-05).
