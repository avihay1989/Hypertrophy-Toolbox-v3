# Deep Refactor Plan — v2 (2026-07-03, council-reviewed)

**Status: Plan v2 — awaiting owner sign-off.**
v1 was reviewed by the plan council (architecture-reviewer: *blocking*, test-strategist:
*needs-revision*, product-risk-reviewer: *needs-revision*). All findings are dispositioned
in the response matrix below; this body is the revised plan. Owner decisions locked in:
full CSS cleanup · plain JS + Vitest (no TypeScript).

This plan is written so each work packet (WP) can be executed by a smaller model in one
sitting. Every WP states its goal, exact scope, steps, invariants, and verification gate.
Executors: do not improvise beyond the WP scope; if a step contradicts what you find in
the code, stop and report instead of adapting. Prefer the function/symbol names given
here over line numbers — line numbers drift.

---

## Council response matrix (v1 → v2)

| # | Finding | Reviewer(s) | Disposition | Action in v2 |
|---|---|---|---|---|
| 1 | `bad_request`/`unprocessable_entity`/`handle_api_error`/`log_request_info` are live decorator-registered closures (`@app.errorhandler`, `@app.before_request`), not dead code; grep heuristic structurally blind to them | arch (blocking), test, product | **accept** | Removed from WP0.1; new global rule 8 (decorator registration = live reference) |
| 2 | `advanced_to_basic` is enshrined by `tests/test_volume_taxonomy.py` | arch, test, product | **accept** | Moved to explicit do-NOT-delete list; test refs count as refs |
| 3 | `DEFAULT_FATIGUE_CONTEXT_ENABLED`, `MIN_RELATED_CONFIDENCE`, `CONFIDENCE_NONE` are spec-locked anchors for gated 2D-D / Stage-4 surfaces | product | **accept** | Removed from WP0.2 deletion list |
| 4 | WP1.1 merge of the two `fetch_unique_values` is contradictory (different signatures, both test-enshrined) and risks filter-vocabulary drift + SQL-injection surface via `ExerciseManager`'s unguarded f-string | arch, test, product | **accept** | WP1.1 rewritten: routes version moves to utils as `fetch_filter_values` (new name); `ALLOWED_COLUMNS`/`validate_column_name` relocate to utils first with re-exports; `ExerciseManager.fetch_unique_values` + its tests untouched; no merge |
| 5 | `generate_starter_plan_route` is already thin — nothing to extract | arch | **accept** | WP1.3 reduced to superset extraction only + a verify note |
| 6 | WP2.4 wiring ambiguous: registry must call `utils.program_backup.initialize_backup_tables` (not the routes wrapper); `column_exists`/`table_exists` must move with re-exports; caller list is 6 files not 3; `create_startup_backup()`/erase-snapshot ordering unstated | arch, product | **accept** | WP2.4 rewritten with explicit function names, caller list, ordering invariant |
| 7 | WP2.4 gate under-scoped (touches app.py + conftest ⇒ QUALITY_GATE says `/verify-suite`) | test | **accept** | WP2.4 sequenced last in Phase 2; phase-close `/verify-suite` is its gate; architecture-reviewer named |
| 8 | WP2.1 split must preserve lazy `strength_calibration` imports (circular-import guard), underscore/test-imported names, and mid-file `lift_matching` re-exports | arch | **accept** | Added to WP2.1 invariants; export list generated, not hand-written |
| 9 | WP2.3 no-drift proof under-specified; gate missing `summary-pages.spec.ts`; product-risk-reviewer required | test, product | **accept** | WP2.3 gate rewritten with exact test files + golden before/after capture |
| 10 | Phase 4 visual-gate mechanics wrong: seeding is `PW_VISUAL_SEED=1` (not a manual script run); baselines are platform-split (win32 local / linux CI via `deep-gate.yml` dispatch); known-red ledger stale (predates PRs #87/#88) | test | **accept** | Phase 4 verification rewritten; new WP4.0 records a fresh red ledger on `main` before any CSS edit |
| 11 | WP4.2 page list incomplete (`pages-progression.css`, `pages-body-composition.css` missing); shared bundles + `theme-dark.css` retirement have no owning WP | arch | **accept** | Both pages added; new WP4.2-final for shared bundles + `theme-dark.css` |
| 12 | `fatigue_calibration_report.py` must stay (Stage 4 open; guardrails + deferred `hard_4d` retune reference it) | test, product | **accept** | Moved to must-stay list |
| 13 | WP3.2/WP3.5 E2E gates under-scoped; name literal specs per QUALITY_GATE feature map | test, product | **accept** | Gates rewritten with literal spec names |
| 14 | WP3.5 touches `bodymap-svg.js`/`muscle-selector.js` while the committed fatigue heatmap is queued on those surfaces | product | **accept** | Sequencing note added |
| 15 | §0 protected-zone list incomplete (progression logic, summary aggregation, volume taxonomy, Stage-4 artifacts, locked 2D-A advisory copy) | product | **accept** | Rule 2 extended |
| 16 | WP0.3 grep anchors too strict; WP0.3 must land before WP1.1 | arch | **accept** | Fixed; ordering noted |
| 17 | Stale line refs (`initialize_exercise_order` is ~line 634 not 614); prefer symbol names | arch, test | **accept** | Symbol names used throughout; CLAUDE.md correction folded into WP0.5 |
| 18 | Reviewer mapping per WP absent | test | **accept** | Reviewer column added to sequencing table |
| 19 | Amend global rule 3 to permit documented test deletions broadly | test | **defer** | Not needed after findings 2/4 removed the cases that required it; revisit only if a future WP genuinely needs a test rewrite (note carried in handover) |

---

## 0. Global rules (apply to every WP)

1. **Behavior-preserving only.** No change to calculation semantics, DB schema shapes,
   API response shapes, or user-visible copy. The CLAUDE.md refactor invariant applies:
   plan/log/analyze/progress/distribute/backup behavior must not drift.
2. **Protected zones — moving code is allowed; editing its logic is not:**
   - `utils/effective_sets.py` factors; effective sets stay informational-only
   - `utils/fatigue.py` thresholds/bands/landmarks; `tests/test_fatigue.py` boundary tests
   - estimator priority chain (`exact learned → exact log → related learned → Profile → cold-start → default`)
   - `utils/progression_plan.py` double-progression decision logic
   - `utils/weekly_summary.py` / `utils/session_summary.py` aggregation semantics
   - `utils/volume_taxonomy.py` / volume splitter / classifier mappings
   - replace-exercise `status_code=200` error pattern (`NO_CANDIDATES`/`DUPLICATE`/`SELECTION_FAILED`)
   - Stage-4 artifacts: `scripts/fatigue_calibration_report.py::SCENARIOS`, observer automation
   - locked 2D-A advisory copy `"This does not change your suggestion."` (`utils/fatigue_context.py`)
   - anything gated by the Phase 2D-D block (BLOCKED — do not start)
3. **Gate per WP:** record baseline (`.venv/Scripts/python.exe -m pytest tests/ -q`),
   make the change, re-run full pytest — count must match baseline exactly (or baseline
   + new tests; test deletions/rewrites are not authorized unless a WP says so
   explicitly). Phase-specific E2E gates are listed per WP. Phase close = `/verify-suite`.
4. **One WP = one PR**, squash-merged per the established PR workflow (auto-create,
   auto-merge on green CI + clean + no change-requests; stop on any blocker).
   Target diff size ≤ ~400 lines except where a WP says otherwise.
5. **Never stage `data/database.db`.** Never rename CI job `name:` values
   (branch-protection required-check contexts are exact-match).
6. **Rollback rule:** if the gate goes red and the fix isn't obvious within one attempt,
   `git stash push` / revert the WP and report.
7. **Import-stability rule for module splits:** the original module path keeps working
   via re-exports until a later WP migrates callers. Splits never break
   `from utils.x import y` for existing callers in the same PR.
8. **Dead-code rule:** a symbol is deletable only if a repo-wide grep
   (`grep -rn "\b<name>\b" routes/ utils/ static/ templates/ tests/ scripts/ e2e/ app.py .github/`)
   returns only its definition, **and** it is not decorator-registered or nested inside a
   registration function — `@app.errorhandler`, `@app.before_request`, `@bp.route`,
   `@app.template_filter`, and closures inside `register_*`/`setup_*` functions are live
   even at zero name-references. Test references count as references.

---

## Phase 0 — Dead code & docs sweep (low risk, 4 PRs)

### WP0.1 Delete dead functions
- Delete (each re-verified per rule 8 before deleting):
  - `utils/errors.py`: **none** — `handle_api_error`, `bad_request`, `not_found`,
    `unprocessable_entity` are all live `@app.errorhandler` closures inside
    `register_error_handlers()`. Do not touch.
  - `utils/logger.py`: **do not delete** `log_request_info` — live `@app.before_request` closure.
  - Deletable after re-verification: none of the v1 function candidates survived review.
    This WP is now **merged into WP0.2** (constants only).
- **Do NOT delete:** `advanced_to_basic` (`utils/volume_taxonomy.py`) — enshrined by
  `tests/test_volume_taxonomy.py`.

### WP0.2 Delete dead constants (single Phase-0 code PR)
- Candidates confirmed definition-only. Re-verify each per rule 8 before deleting:
  `movement_patterns.HOME_BASIC_EQUIPMENT`, `movement_patterns.DEFAULT_SETS_TARGET`,
  `movement_patterns.MovementCategory` (class), `profile_estimator.REP_RANGE_PCT`.
- **Do NOT delete** (spec-locked anchors for gated workstreams, kept deliberately):
  `strength_calibration.MIN_RELATED_CONFIDENCE`, `strength_calibration.CONFIDENCE_NONE`
  (LEARNED_CALIBRATION_PLAN §confidence vocabulary),
  `fatigue_context.DEFAULT_FATIGUE_CONTEXT_ENABLED` (2D-A locked defaults).
- **Do NOT delete** (real refs): `KEY_LIFT_SIDE`, `EXPORT_BATCH_SIZE`, `APP_TITLE`,
  `ERROR_CODES`, `REFERENCE_LIFT_LABELS`, `STATUS_MAP`, `rpe_to_rir`, `rir_to_rpe`,
  `set_calibration_mode`, `validate_filter_field`, `should_use_streaming`,
  `get_effective_volume_label`.
- Gate: full pytest == baseline; `flake8` blocking set stays 0.

### WP0.3 Empty the `utils/__init__.py` facade — **must land before WP1.1**
- Zero importers of the facade remain (verified 2026-07-03, unanchored grep). Reduce
  `utils/__init__.py` to the docstring only.
- Re-verify first (no `^` anchors; include function-level imports):
  `grep -rn "from utils import \|import utils$\|import utils " routes/ utils/ tests/ scripts/ e2e/ app.py`
  — module-style imports like `import utils.config` survive an emptied `__init__` and are fine.
- Gate: full pytest == baseline; app boots (`python app.py` starts, `GET /` 200).

### WP0.4 Archive completed one-off scripts + repo-root hygiene
- Follow the documented archive procedure: **grep code, tests, and workflows — not just
  docs — before archiving anything.**
- Must stay (referenced by tests/CI/docs or live automation):
  `pyright_baseline_diff.py`, `fatigue_stage4_observer.py`, `fatigue_stage4_status.py`,
  **`fatigue_calibration_report.py`** (Stage 4 OPEN — guardrails + deferred `hard_4d`
  retune reference it; keep until owner closes Stage 4),
  `apply_free_exercise_db_mapping.py`, `apply_youtube_curated.py`,
  `build_musclemap_svgs.py`, `fatigue_movement_pattern_cleanup.py`,
  `fatigue_stage1_cleanup.py`, `seed_visual_baseline.py`, the `run-*.ps1` /
  `new-worktree.ps1` helpers, and **all Stage-4 observer automation**
  (`install_fatigue_stage4_observer_task.ps1`, `run_fatigue_stage4_observer.bat`,
  `check_fatigue_stage4_automation.ps1`) — a Windows scheduled task runs these.
- Archive candidates (verified zero refs in `e2e/`, `.github/`, `tests/`; re-verify at
  execution time): `fatigue_stage1_cleanup_dryrun.py`,
  `fatigue_movement_pattern_cleanup_dryrun.py`, `curate_free_exercise_db_mapping.py`,
  `map_free_exercise_db.py`, `fatigue_stage4_mutation_smoke.py`,
  `fatigue_stage4_remaining_smokes.py`, `fatigue_stage4_restore_smoke.py`
  (`e2e/fatigue-stage4-smokes.spec.ts` is an independent Playwright port, not a caller).
- Also: remove root-level `baseline_e2e.txt`, `baseline_pytest.txt`; add to `.gitignore`.
- Gate: full pytest == baseline; CI green (proves no workflow referenced an archived file).

### WP0.5 CLAUDE.md / docs sync
- Fix blueprint table (13 registered: add `body_composition_bp`, `fatigue_bp`); refresh
  verified-count section to current reality; correct the stale
  `initialize_exercise_order` line reference (now ~`routes/workout_plan.py:634`); note
  this refactor plan doc.
- Gate: docs-only; CI green.

---

## Phase 1 — Routes layer slim-down (3 PRs)

Goal: `routes/*.py` = validate input → call utils → return response. Nothing else.

### WP1.1 Move the filter-values logic out of `routes/workout_plan.py` (no merge)
- **Step 1:** relocate `ALLOWED_COLUMNS` + `validate_column_name` from
  `routes/filters.py` into `utils/filter_predicates.py`; keep re-exports in
  `routes/filters.py` (imported by `tests/test_priority0_filters.py` and
  `routes/workout_plan.py`).
- **Step 2:** move the routes-level `fetch_unique_values(column)` function
  (`routes/workout_plan.py`, ~line 20; enum-map + Force title-case normalization +
  isolated-muscles sourcing) into utils under the **new name `fetch_filter_values`**
  (suggested home: `utils/exercise_manager.py` or a new `utils/filter_values.py`).
  It must call `validate_column_name` internally (utils-level guard — the function
  interpolates a column name into SQL).
- **Do not touch** `ExerciseManager.fetch_unique_values(table, column)` or
  `tests/test_exercise_manager.py` — different signature, different tested contract,
  deliberately kept separate. No merge in this WP.
- Route keeps a thin call to `fetch_filter_values`.
- Gate: full pytest == baseline; `e2e/workout-plan.spec.ts` + `e2e/exercise-interactions.spec.ts`.

### WP1.2 Extract replace-exercise business logic
- `replace_exercise` in `routes/workout_plan.py` (~126 lines): move candidate selection /
  dedup / swap persistence into a new `utils/exercise_replacement.py`. Route keeps
  request parsing + the **byte-identical** response contract, including
  `NO_CANDIDATES` / `DUPLICATE` / `SELECTION_FAILED` as `error_response(..., status_code=200)`.
- Gate: full pytest; `e2e/replace-exercise-errors.spec.ts` + `e2e/workout-plan.spec.ts`.

### WP1.3 Extract superset route logic
- `link_superset` / `unlink_superset` / `suggest_supersets` + their helpers in
  `routes/workout_plan.py`: move pairing and persistence logic to a new
  `utils/supersets.py`. Routes keep validation + response shaping.
- `generate_starter_plan_route`: **verified already thin** (validation → one call to
  `utils.plan_generator.generate_starter_plan` → response) — no extraction; executor
  should confirm and move on.
- Gate: full pytest; `e2e/superset-edge-cases.spec.ts` + `e2e/workout-plan.spec.ts`.

After WP1.3, audit `routes/user_profile.py` and `routes/exports.py` for the same
pattern; if violations are found, file one follow-up WP each (same template).

---

## Phase 2 — Python module splits (4 PRs; WP2.4 goes LAST)

### WP2.1 Split `utils/profile_estimator.py` (2,418 lines)
- Convert to a package, preserving the public import path:
  - `utils/profile_estimator/__init__.py` — re-exports the **full current module
    namespace, including underscore names imported by tests** (e.g. `_load_basis_factor`)
    and the mid-file `lift_matching` re-exports (`DIRECT_LIFT_MATCHERS`,
    `match_direct_lift_key`). Generate the export list from the current module's
    public + test-imported names — do not hand-write it.
  - `core.py` — estimation chain (`_estimate_from_profile`, load-basis, priority logic)
  - `trace.py` — `_build_profile_trace`, `_build_cold_start_trace`, "show the math" builders
  - `cohort.py` — `cohort_ranges`, `muscle_coverage_state`
- **Circular-import invariant:** `strength_calibration` imports this module at top level;
  this module imports `strength_calibration` **lazily inside functions** (commented in
  source). Those imports must stay function-local in whichever submodule receives them —
  do not hoist to module top.
- Pure moves; no signature or logic edits. `tests/test_profile_estimator.py` passes
  unmodified.
- Gate: full pytest; `e2e/user-profile.spec.ts` + `e2e/learned-calibration.spec.ts`.

### WP2.2 Decompose long functions in `utils/plan_generator.py`
- `_score_exercise`, `_apply_priority_muscle_boost`, `persist`, `generate_starter_plan`:
  extract named helpers within the same module. No reordering of scoring math; helpers
  must be extract-method only.
- Gate: full pytest (`tests/test_plan_generator.py` unmodified); generator flow in
  `e2e/workout-plan.spec.ts`.

### WP2.3 Decompose `utils/weekly_summary.py` monster functions — **product-risk-reviewer on the diff**
- `calculate_weekly_summary` (~178 lines) and `calculate_pattern_coverage` (~172 lines):
  extract-method into private helpers, same module, identical outputs. **Protected calc
  zone — no numeric/semantic drift.**
- No-drift proof (all required):
  - `tests/test_weekly_summary.py`, `tests/test_weekly_summary_routes.py`,
    `tests/test_pattern_coverage.py`, `tests/test_effective_sets.py` — all pass unmodified
  - Golden capture: run both functions on seeded data before and after; paste identical
    JSON output in the PR description
  - Explicit statement that the Effective/Raw side-by-side output shape is unchanged
- Gate: full pytest; `e2e/summary-pages.spec.ts` + `e2e/api-integration.spec.ts`;
  `product-risk-reviewer` on the staged diff.

### WP2.4 Consolidate schema initialization (single registry) — **last WP of Phase 2; architecture-reviewer on the diff**
- Today schema setup is spread across: `utils/db_initializer.py`, three `add_*_table()`
  in `utils/database.py`, `add_fatigue_context_settings_table`, `initialize_exercise_order()`
  in `routes/workout_plan.py` (ALTER TABLE in a routes file), and backup-table init.
- Create `utils/schema_registry.py` exposing `run_all_initializers()` that calls the
  existing functions in the current startup order. Explicit wiring:
  - Backup tables: call `utils.program_backup.initialize_backup_tables` **directly**
    (not the `routes/program_backup.init_backup_tables` wrapper — utils must not import
    from routes).
  - Move `initialize_exercise_order` AND its helpers `column_exists` / `table_exists`
    into utils; keep deprecation re-exports in `routes/workout_plan.py` (helpers are
    imported by `routes/exports.py`, `tests/test_exports.py`, `tests/test_program_backup.py`).
  - **Ordering invariant:** `create_startup_backup()` and the `/erase-data` pre-erase
    snapshot stay outside `run_all_initializers()`, in their current positions relative
    to schema init.
- Known callers to update or cover via re-exports (enumerate in the PR): `app.py`,
  `tests/conftest.py`, the `/erase-data` handler, `e2e/scripts/prepare_visual_db.py`,
  `tests/test_harness_isolation.py`, `tests/test_priority7_error_handling.py`,
  `tests/test_program_backup.py`. **`conftest.py` mirrors startup — both must change
  together or tests 404/miss tables.**
- No table shapes change; orchestration-only.
- Gate: **`/verify-suite`** (this WP doubles as the Phase-2 close), plus
  `e2e/program-backup.spec.ts` run in isolation (restores a pre-refactor snapshot —
  covers the backup contract), plus fresh-DB boot smoke (delete scratch DB, start app,
  hit `/workout_plan`); `architecture-reviewer` on the staged diff.

---

## Phase 3 — JS test scaffold, then split (5 PRs)

Decision locked: plain JavaScript + Vitest. No TypeScript conversion.

### WP3.1 Add Vitest scaffold + CI (measure-only)
- `npm i -D vitest jsdom`; `vitest.config.js` targeting `static/js/tests/**`; npm script
  `test:js`. Seed with 2–3 trivial tests against pure helpers (`exercise-helpers.js`,
  `toast.js`).
- CI: add a **new, non-required** job (do not touch existing required contexts), following
  the repo's proven measure-first → promote-later pattern.
- Gate: `npm run test:js` green locally + in CI; no production JS changed.

### WP3.2 Extract inline template scripts
- `templates/weekly_summary.html` (~395 inline JS lines) → `static/js/modules/weekly-summary-page.js`;
  `templates/workout_plan.html` (~211) → merge into existing plan modules or a new
  `workout-plan-page.js`. Load via `<script src>` with the same execution timing
  (`defer`/placement preserved). `session_summary.html` / `welcome.html` / `base.html`
  inline blocks: audit, extract if non-trivial.
- **Mode-semantics pin:** the weekly-summary inline JS wires the CountingMode /
  ContributionMode toggles. Defaults (`EFFECTIVE`, `TOTAL`) and the Effective/Raw
  side-by-side display must be timing-identical after extraction.
- Gate: full pytest; `e2e/summary-pages.spec.ts` + `e2e/workout-plan.spec.ts` +
  `e2e/api-integration.spec.ts`; **if `base.html`/`welcome.html` blocks are extracted**,
  also `e2e/smoke-navigation.spec.ts` + `e2e/nav-dropdown.spec.ts` + `e2e/dark-mode.spec.ts`.

### WP3.3 Characterize then extract pure logic from `workout-plan.js`
- Identify pure functions inside `static/js/modules/workout-plan.js` (payload builders,
  formatting, estimate/trace rendering data prep, superset pairing helpers). Write Vitest
  characterization tests against current behavior FIRST, then move those functions to
  small modules (`workout-plan/logic-*.js`), importing back. DOM-touching code stays put
  this WP.
- Gate: new Vitest suite green; full pytest; `e2e/workout-plan.spec.ts` +
  `e2e/fatigue-context.spec.ts` + `e2e/learned-calibration.spec.ts`.

### WP3.4 Split `workout-plan.js` by feature
- Target shape: `workout-plan/` folder — `table.js` (render + row events), `estimates.js`
  (Workout Controls + fatigue-context section + nudge), `supersets.js`, `media.js`
  (YouTube modal + image preview glue), `index.js` (wiring). Keep global entry identical
  (same script tags / event timing).
- Depends on WP3.3 tests. Diff will exceed 400 lines — allowed, but it must be move-only.
- Gate: Vitest green; E2E block: `e2e/workout-plan.spec.ts`,
  `e2e/exercise-interactions.spec.ts`, `e2e/superset-edge-cases.spec.ts`,
  `e2e/fatigue-context.spec.ts`, `e2e/learned-calibration.spec.ts`,
  `e2e/replace-exercise-errors.spec.ts`.

### WP3.5 Unify raw `fetch()` → `apiFetch`
- Migrate raw fetch calls to the `fetch-wrapper.js` contract: `volume-splitter.js` (7),
  `exercises.js` (3), `exports.js` (2), `filters.js`, `muscle-selector.js`,
  `bodymap-svg.js`, `app.js` (1 each). Exports/downloads that stream blobs may keep raw
  fetch if the wrapper doesn't support blobs — note each exception in the PR.
- **Sequencing note:** the owner-committed fatigue body-heatmap workstream reuses
  `bodymap-svg.js` / `muscle-selector.js`. This WP must land **before** heatmap work
  starts, or the bodymap/muscle-selector portion is deferred until after it ships —
  check `docs/MASTER_HANDOVER.md` at execution time.
- Gate: full pytest; `e2e/volume-splitter.spec.ts` + `e2e/volume-progress.spec.ts` +
  `e2e/api-integration.spec.ts` + `e2e/workout-plan.spec.ts` +
  `e2e/exercise-interactions.spec.ts` + `e2e/user-profile.spec.ts` +
  `e2e/smoke-navigation.spec.ts`; export flow covered by `tests/test_exports.py` under
  full pytest.
- Follow-up (optional, same pattern as WP3.3/3.4): `user-profile.js` (1,483 lines).

---

## Phase 4 — CSS full cleanup (staged, visual-gated)

Owner chose **full cleanup**. Current state: 29,880 lines hand-maintained CSS in
`static/css/` (16 bundles; `pages-workout-plan.css` alone 8,226), SCSS pipeline covers
only ~880 lines, dark mode is hand-duplicated (`theme-dark.css` + scattered dark rules).

**Architecture decision (council did not object):** stay on **plain CSS, structured** —
do NOT migrate everything into SCSS. Tokens (CSS custom properties) + per-page bundles
kept, duplication removed, dark mode driven by custom-property swaps. The existing
`scss/` pipeline continues to own only the Bootstrap customization + the files it
already owns.

**Verification for every WP in this phase (exact mechanics):**
- Local: `PW_VISUAL_SEED=1 npx playwright test e2e/visual.spec.ts e2e/visual-baseline-thumbnails.spec.ts --project=chromium --reporter=line`
  — `PW_VISUAL_SEED=1` makes the Playwright webServer seed the throwaway DB
  (`artifacts/e2e/database.e2e.db`) before Flask opens it. Do NOT run the seed script
  manually against the live DB.
- Baselines are **platform-split**: local runs prove `e2e/__screenshots__/win32/` only;
  CI compares `linux/` via the `visual-linux` job in `.github/workflows/deep-gate.yml`
  (opt-in `workflow_dispatch` — never a PR check). **Each CSS WP must dispatch the deep
  gate**, and any justified re-baseline must update **both** platform baseline sets.
- Pixel diffs = failure unless the WP explicitly re-baselines with justification against
  the WP4.0 ledger.

### WP4.0 Fresh known-red ledger (no code change)
- The documented visual known-reds predate PRs #87/#88 (MuscleMap unification, image
  previews, YouTube modal). Before any CSS edit: run the full visual deep gate on
  current `main` (both platforms), record the red ledger in this doc + handover. That
  ledger — not the stale 2026-05-24 snapshot — is the Phase-4 comparison baseline.
  (`nav-dropdown.spec.ts` is no longer a known red; do not carry it forward.)

### WP4.1 Tokenization audit + stylelint
- Add `stylelint` (dev-only, non-required CI job, measure-only) with a minimal config:
  duplicate-selector and declaration-block-no-duplicate-properties warnings.
- Expand `static/css/tokens.css`: inventory hardcoded colors/spacing/radii across all
  bundles (scripted count in the PR description); define missing tokens. **No visual
  change** — tokens added but not yet consumed.
- Gate: visual deep gate byte-identical vs WP4.0 ledger (no re-baseline allowed).

### WP4.2 Dark-mode unification, page by page (one PR per page)
- Order (smallest → largest risk): `pages-backup.css`, `pages-body-composition.css`,
  `pages-progression.css`, `pages-volume-splitter.css`, `pages-welcome.css`,
  `pages-session-summary.css`, `pages-weekly-summary.css`, `pages-user-profile.css`,
  `pages-workout-log.css`, `pages-workout-plan.css`.
- Per page: replace hardcoded light/dark rule pairs with token-consuming rules; dark
  mode overrides collapse into theme-scoped custom-property swaps; delete the now-dead
  duplicated dark blocks (from both the page bundle and `theme-dark.css`).
- Gate per PR: visual deep gate for that page's screens, light AND dark, both platforms.

### WP4.2-final Shared bundles + `theme-dark.css` retirement
- Same treatment for the shared bundles: `components.css`, `navbar.css`, `layout.css`,
  `a11y.css`, `base.css`/`motion.css` if present, and whatever remains of
  `theme-dark.css`. Goal: `theme-dark.css` deleted or reduced to the token-swap block.
- Gate: full visual deep gate (both platforms) + `e2e/dark-mode.spec.ts` +
  `e2e/accessibility.spec.ts`.

### WP4.3 Cross-bundle dedupe
- Move rules duplicated across ≥2 page bundles into `components.css`; shrink page bundles
  to page-specific rules only. Scripted before/after line counts in each PR.
- Gate: full visual deep gate + `e2e/accessibility.spec.ts`.

Success metric for Phase 4: total `static/css` line count reduced ≥ 30% with zero
unjustified visual diffs vs the WP4.0 ledger.

---

## Continuous track — pyright baseline burn-down (filler tasks)

- 190 diagnostics / 58 keys frozen in `docs/ci_cd_phase3/pyright-baseline.json`.
- Between phases, small-model filler WPs: pick one file's diagnostics, fix types only
  (no behavior change), regenerate baseline via
  `scripts/pyright_baseline_diff.py --write-baseline` — baseline may only shrink.
- Gate: pyright net-new = 0, count strictly lower; full pytest == baseline.

---

## Sequencing & effort map

| Phase | PRs | Risk | Prereqs | Diff-time reviewers |
|---|---|---|---|---|
| 0 dead code/docs | 4 | Low | none (WP0.3 before WP1.1) | `/unslop` |
| 1 routes slim-down | 3 (+2 audit) | Medium | Phase 0 merged | `/unslop`; code-reviewer on WP1.2 |
| 2 module splits | 4 | Medium | Phase 1; WP2.4 last | product-risk-reviewer (WP2.3); architecture-reviewer (WP2.4) |
| 3 JS scaffold+split | 5 | Medium-High | none (parallel to 1–2 OK) | `/unslop` |
| 4 CSS cleanup | ~13 | High (visual) | WP3.2 first; WP4.0 before any edit | `/unslop`; deep-gate dispatch every WP |
| pyright filler | ad hoc | Low | none | `/unslop` |

Phase close ritual: `/verify-suite`, then update `docs/MASTER_HANDOVER.md` and the
CLAUDE.md verified-counts block.

## Sign-off checklist
- [x] Every council finding has a disposition (matrix above; #19 deferred with reason).
- [ ] Owner approved Plan v2.
- [ ] Ready to implement.
