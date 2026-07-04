# Codebase Grounding Scan — Recommendations (Phase 23 Synthesis)

**Basis:** line-by-line read of the entire codebase, 2026-07-03 (see [SCAN_PROGRESS.md](SCAN_PROGRESS.md),
per-phase evidence in [scan/PHASE_*.md](scan/), distilled ledger in [SCAN_FINDINGS.md](SCAN_FINDINGS.md)).
Every claim below carries a phase tag (P1–P22) pointing at file:line evidence.

**Headline verdict on `docs/REFACTOR_PLAN.md` v2:** direction is sound, sizing and sequencing are not.
Phases 0–2 (Python) survive the scan with amendments. Phase 3 (JS) has two WPs whose proposed seams
don't match the real file. Phase 4 (CSS) is under-scoped in payoff AND risk: the duplication is much
larger than assumed, but three structural traps (@layer order, token load-order, hardcoded classes in
visual helpers) must be defused first. Separately, the scan surfaced a **bug-fix track** that should NOT
wait for — or be mixed into — behavior-preserving refactor PRs.

---

## A. Bug-fix track (fix first, small PRs, each with a test)

Confirmed defects, ordered by user impact. None are refactors; all change behavior and need owner sign-off
where marked ⚠.

| # | Bug | Evidence | Fix shape |
|---|---|---|---|
| A1 | Toast severity: warnings/errors render as green success toasts (app.js:99,111,158,162 via toast.js:17 legacy-arg coercion) | P17, P12 | Switch 4 call sites to object-style; add console.warn on legacy misuse |
| A2 | Double-submission on every scored-value edit: inline onchange races debounced input handler → 2 identical POSTs + double calibration recompute | P15 | Remove one of the two handlers (keep the debounced path) |
| A3 | Progression badge wrong for assisted-bodyweight after date change: handleDateChange omits isWeightProgression() that its 2 sibling copies apply | P15 | Extract the check once, call from all 3 sites |
| A4 | error.html renders near-blank on real 500s: 6 of 7 routes pass message= but template reads error_message/error_title | P10, P11 | Align template variable names; add a route test |
| A5 | routes/fatigue.py:26 calls is_xhr_request(request) — zero-arg function → TypeError on the error path | P10 | Drop the argument |
| A6 | ⚠ weight==0 rejected as "missing required field" (exercise_manager falsy check) — blocks bodyweight exercises; currently ENSHRINED by a test and inconsistent with logging-side scored_weight=0.0 | P8, P21 | Owner decision: `is None` checks + rewrite the enshrining test |
| A7 | ⚠ No validation anywhere on update paths: server update_exercise/update_workout_log check nothing; client is cosmetic; routes.md documents bounds that don't exist | P8, P15, P21, P22 | Owner decision on canonical bounds → enforce in utils, document, test |
| A8 | create_backup() non-atomic (N+1 commits): crash mid-loop leaves header overstating item_count | P7 | Wrap in one transaction like restore_backup |
| A9 | tokens.css loaded AFTER its consumer bundles in base.html (cascade inversion) | P19 | Reorder link tags; visual-gate the change |
| A10 | Event-listener leaks: execution-style picker (3 of 4 close paths), workout-dropdowns _cleanupHandler never invoked | P12, P15 | Wire cleanups; cheap |
| A11 | Unconditional time.sleep(0.5) in every Excel export | P7 | Delete; verify export tests still pass |
| A12 | Export GET mutates exercise_order (side effect in nominally read-only export_to_workout_log) + N+1 loop | P9 | Owner decision: move mutation or document intent |

Also file (docs-only): CLAUDE.md startup lists 6 of 8 initializers (P1); MASTER_HANDOVER stale SHA anchor
(P1); routes.md phantom validation claims (P8); testing.md spec ledger 17/315 vs actual 28 (P22);
e2e/CLAUDE.md missing fatigue-context.spec.ts row (P22).

## B. Amendments to existing REFACTOR_PLAN WPs

- **WP0.1/0.2 (dead code):** errors.py `not_found` + `handle_unexpected_error` ARE dead (shadowed by
  app.py's later registrations — later registration wins in Flask; runtime-probe before deleting) (P1).
  Add: effective_sets.py:349-575 second pipeline (+ its 26 tests in test_effective_sets.py — needs the
  plan's test-deletion authorization, council finding #19 revisit) (P3, P21); 5 unreferenced route
  endpoints (P8); create_auto_backup_before_erase + its 7 tests (P7, P21); weekly_summary.STATUS_MAP,
  MovementCategory, HOME_BASIC_EQUIPMENT confirmed (P3).
- **NEW WP0.x (JS dead code):** the plan's Phase 0 is Python-only. Add a JS sweep: charts.js whole file,
  summary.js no-op exports, exercises.js duplicate Add-Exercise flow, workout-log.js:595-690,
  progression-plan.js:523-573, showAutoBackupBanner (or wire it — owner call), table-responsiveness dead
  exports, dead CSS blocks inventoried in P18/P19/P20. NOTE: rule-8 grep is insufficient for JS —
  "window-assigned but never called" needs call-site verification (P12, P14, P16).
- **WP0.4 (scripts):** move seed_visual_baseline.py from "must stay" to archive candidates — zero
  code/CI/e2e refs, fails the plan's own standard (P22).
- **WP1.1:** account for FOUR fetch-unique-values implementations (adds routes/filters.py:356
  get_unique_values with its own allowlists), and unify toward ONE allowlist source in
  utils/filter_predicates (two hand-synced lists today) (P2, P8).
- **WP1.x scope:** add routes/volume_splitter.py, routes/workout_log.py, routes/body_composition.py to
  the routes slim-down (3-file DB-in-routes pattern the plan misses); drop the user_profile.py
  extraction audit (handlers already thin — fatness is static data) (P9, P10).
- **WP2.1 (profile_estimator split):** re-group cohort.py (cohort_ranges belongs with
  cohort_bars/coverage_donut, NOT muscle_coverage_state); add two missing clusters (constants block
  lines 22-740; accuracy/coverage-guidance 1772-1968) or core.py bloats (P5).
- **WP2.2:** add explicit no-drift item for persist()'s two-tier exception handling; fold in the two
  trivial dead params (P6).
- **WP2.4 (schema registry):** scope is bigger than written — SIX add_* functions (not three), the
  duplicate add_progression_goals_table method/function pair, erase_data's duplicated init block + its
  hardcoded 16-table DROP list, and maintenance.py's drifted exercise_isolated_muscles definition. The
  registry should own a canonical table list consumed by both startup and erase (P1, P2).
- **WP3.2 (inline template JS):** extraction is a MOVE not a merge — summary.js exports are permanent
  no-ops; the inline code is the only live implementation. Delete summary.js in the same WP (P16).
- **WP3.3/3.4 (workout-plan.js split):** re-draw the target shape: add homes for the ~660 homeless lines
  (execution-style picker, swap/replace, Add-Exercise cluster) and a named shared-state module for the
  4 cross-boundary mutable vars. Superset logic is interleaved with table rendering — WP3.4's
  table/supersets seam needs the P12 line map, not the plan's guess (P12).
- **WP3.5 (apiFetch migration):** volume-splitter.js needs its ~50-line apiFetch reimplementation
  DELETED, not call-sites swapped; blob carve-out confirmed mandatory (fetch-wrapper has zero blob
  support) (P14, P17).
- **Phase 4 (CSS) — re-sequence with three new prerequisite WPs:**
  1. **WP4.-1 (new):** declare explicit @layer order; fix tokens.css load order (A9); then begin
     de-!important-ing (P18, P19).
  2. **WP4.0a (new):** replace exact-RGB assertions in nav-dropdown/summary-pages specs with
     token-aware or snapshot checks; refactor e2e/visual-helpers.ts's ~25 hardcoded class names to
     data-testid hooks BEFORE any class renames (P22).
  3. **WP4.1:** merge the duplicate spacing vocabularies (--space-* vs --s-*) and plan the six siloed
     namespaces (--wl-*, --nav-*, --bc-*, --backup-*, --volume-*, --fatigue-*) into the token
     consolidation — the real duplication is above the hardcoded-color level (P18, P20).
  4. **WP4.2:** use pages-user-profile.css as the template (already the target end-state); treat
     workout-log.css as a redesign-sized job (dark values differ per theme, not swappable); navbar +
     theme-dark need per-rule triage (3 live generations / 2 layers) (P19, P20).
  5. **WP4.3:** the single biggest win is the 4× ~1350-line frame block (weekly/session/log/plan) —
     extract once into components.css; add a "relocate misfiled page content" step (~600 lines in
     pages-workout-plan.css belong to other pages) (P18, P19).
  6. Sizing: with the 4× block + dead CSS + dark-pair collapse, the ≥30% reduction target is
     conservative; 40%+ is realistic (P18–P20).

## C. New items the plan has no home for

- **Duplication registry (Python):** scored-row rule + tie-break (fatigue.py↔fatigue_data.py, P4);
  _promotion_basis_factor↔_load_basis_factor exact arithmetic (P5); weekly↔session hand-rolled
  aggregation + the dead pipeline that was meant to unify them (P3); movement-pattern classification
  fork (P3); null-routine semantic divergence weekly-vs-session (⚠ owner: which semantic is right?) (P3).
- **utils/fatigue.py 4-way split** (Phase-1 core / per-muscle / period-window / SFR) — same shape as
  WP2.1, absent from plan; protected-zone rules apply (move-only) (P4).
- **Test-gap pre-steps** (before refactoring the module): create_startup_backup (live, zero tests);
  lift_matching + exercise_media (no direct unit tests); body-fat parity is Playwright-only and covers
  1 of 4 mandated functions — add the missing 3 to the e2e parity test or a pytest mirror (P16, P21).
- **Test-suite hygiene:** two pytest files read the LIVE data/database.db (non-hermetic baseline gate)
  (P21); vacuous E2E assertion sweep (expect(true) patterns across 4 specs) (P22); fatigue-context.spec.ts
  runs in no CI path — promote or document (P22).
- **DatabaseHandler:** CTE-prefixed writes bypass write-lock detection (one live instance:
  maintenance.py REBUILD_EIM_SQL) (P2).
- **a11y:** unify the `<main>` landmark (7 pages have none) (P11).
- **Owner-decision queue** (protected zones — do not touch without sign-off): progression
  _calculate_weight_increment novice no-op branch (P4); weight==0 semantics (A6); null-routine
  semantics (P3); validation bounds (A7); export-GET mutation (A12); ANTAGONIST_PAIRS casing was
  CLEARED — no bug (P8).

## D. Suggested execution order

1. **Bug-fix track A1–A5, A8–A11** (small, test-backed, immediate user value; A6/A7/A12 after owner
   decisions).
2. **Docs sync batch** (CLAUDE.md, routes.md, testing.md, e2e/CLAUDE.md, handover).
3. **Test-gap pre-steps** (C: startup-backup tests, parity coverage, de-vacuous E2E, hermetic-DB fix) —
   these harden the gate every later WP relies on.
4. **Phase 0 amended** (Python + new JS dead-code WP + scripts).
5. **Phases 1–2 amended** (routes slim-down incl. 3 extra files; module splits with corrected WP2.1
   grouping; WP2.4 registry with full scope).
6. **Phase 3 amended** (Vitest scaffold unchanged; WP3.2 move+delete; WP3.3/3.4 with the P12 seam map;
   WP3.5 with the delete-the-clone amendment).
7. **Phase 4 re-sequenced** (WP4.-1 → WP4.0a → WP4.0 ledger → 4.1 → 4.2 → 4.3).

All global rules of REFACTOR_PLAN v2 (behavior-preserving, protected zones, gates, one-WP-one-PR,
never stage data/database.db, never rename CI job names) remain in force and are REAFFIRMED by scan
evidence (P21's non-hermetic finding makes the baseline-gate rule *more* important, not less).
