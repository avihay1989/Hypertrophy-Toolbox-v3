# Changelog

All notable changes to Hypertrophy Toolbox v3.

## Unreleased - May 23, 2026

### Fatigue Meter — Phase 2 Stage 2 (Path 1)

- New dedicated `/fatigue` page with **per-muscle local-fatigue accumulator**, **two Stimulus-to-Fatigue Ratio cards** (planned + logged), and a **period selector** (`this session` / `this week` / `last 4 weeks`). Implements the locked Path 1 scope from PR #33 — additive only, no schema change, no `/api/fatigue/*`, no edits to Phase-1 fatigue math, calibration scenarios, or volume modules.
- **Per-muscle math** (`utils/fatigue.py`): each exercise contributes to its primary / secondary / tertiary muscle buckets weighted by the standard `MUSCLE_CONTRIBUTION_WEIGHTS` ladder (1.0 / 0.5 / 0.25, mirrored from `utils/effective_sets.py` but kept local so the math layer stays pure). Raw set count per D2.4 — CountingMode-invariant. New symbols: `canonicalize_muscle_for_fatigue`, `MUSCLE_VOLUME_LANDMARKS` (BRAINSTORM §5 verbatim — 12 muscles), `classify_muscle_fatigue`, `muscle_percent_of_mrv`, `aggregate_muscles_for_session`, `aggregate_logged_muscles`, `summarize_muscle_bars`, `normalize_period`, `compute_period_window`, `filter_rows_by_date_window`, `adapt_logged_row`, `compute_sfr`.
- **Unassigned-bucket invariant** (load-bearing): the Stage 1 sentinel `"Unassigned"` stays its own bar in the fatigue page and is **never** folded into Abdominals, even though `volume_taxonomy.COARSE_TO_BASIC` routes it that way for the volume-rollup invariant. Guarded by an explicit `TestUnassignedIsItsOwnBucket` unit class and a route-level `TestFatigueUnassignedInvariantThroughRoute` integration test.
- **Six muscles missing from §5** (Front-Shoulder, Rear-Shoulder, Lower Back, Hip-Adductors, Middle-Traps, Neck) + the `Unassigned` sentinel render at the bottom with neutral styling and "—" for the % column. **Phase-3 follow-up**: add owner-vetted MEV / MAV / MRV defaults for these six labels (deferred from Stage 2 by owner decision; do not invent thresholds without a fresh override).
- **Data layer** (`utils/fatigue_data.py`): `load_planned_exercises_with_muscles()` + `load_logged_exercises_with_muscles(start, end)` re-query `user_selection` and `workout_log` (D2.9 / D13 — don't reuse aggregated rows; SQL date filter matches the `utils/session_summary.py` `DATE(wl.created_at)` convention). `build_fatigue_page_context(period)` assembles the full template context including merged `muscle_rows` for the dual planned/logged bar partial.
- **UI** (server-rendered, no new JS module): `routes/fatigue.py` blueprint, `templates/fatigue.html`, `templates/_fatigue_muscle_bar.html` (dual sub-bars sorted by % MRV descending), two `.fatigue-sfr-card` cards reusing the existing `.fatigue-{band}` color tokens, period `<select>` with `onchange="this.form.submit()"` + `<noscript>` fallback. Bar SCSS extended in `scss/_fatigue.scss` (no new route bundle — the frontend 17-bundle cap is preserved). Nav: new `nav-fatigue` link inside the Analyze dropdown after `nav-session-summary`. Badge: existing `_fatigue_badge.html` partial gains a "View per-muscle breakdown →" link in a new grid row (consequence: 12 weekly+session visual baselines re-baseline once, matching the PR #28 pattern).
- **Tests**: +91 (1351 → 1442). 79 unit tests in `tests/test_fatigue.py` (per-muscle math, logged-side, period windows, threshold classification, % MRV sort, SFR sentinel, Unassigned invariant, MUSCLE_CONTRIBUTION_WEIGHTS mirror); 12 integration tests in `tests/test_fatigue_routes.py` (route 200 on empty DB, period round-trip + invalid fallback, populated bars, unranked muscles render `—`, SFR cards present + numeric/sentinel, context shape stable, Unassigned-via-route invariant). New `e2e/fatigue.spec.ts` (8 specs, ~7.7s Chromium) covers page load, both SFR cards, period-selector toggle, invalid-period fallback, empty-state, dark-mode parity, 375px viewport, navigation.

### §4.6 Visual Baseline Thumbnails — Locked via `toHaveScreenshot()`

- `e2e/visual-baseline-thumbnails.spec.ts` converted from inspection-only PNGs (saved to `e2e/artifacts/visual-baseline/`) to committed `toHaveScreenshot()` baselines under `e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots/`. 18 PNGs cover the full §4.6 matrix (`/workout_plan` desktop / tablet / mobile × light / dark × simple / advanced = 12 + `/workout_log` desktop / tablet / mobile × light / dark = 6). Tolerance set at `maxDiffPixelRatio: 0.01` to absorb minor sub-pixel jitter without masking real regressions.
- Verification: snapshot+migrate the seed via `e2e/scripts/prepare_visual_db.py --output artifacts/visual/database.visual-thumbnails.db`, apply `data/free_exercise_db_mapping.csv` (108 rows), run `scripts/seed_visual_baseline.py` (6 plan rows, 4 with `media_path`), then `DB_FILE=artifacts/visual/database.visual-thumbnails.db npx playwright test e2e/visual-baseline-thumbnails.spec.ts --project=chromium --reporter=line` → **18 passed in 14.3s**. Closes `LEFTOVERS_BY_PRIORITY.md` row #13.

### KI-001 — Filter Cache Removed as Dormant Code

- Triage of the long-standing KI-001 "filter cache TTL-only invalidation" risk found the module was dormant: zero `from utils.filter_cache` imports in `routes/`, `utils/`, or `app.py`; `get_cached_unique_values()` only called by `warm_cache()`, which itself was never wired into startup; the route that *would* consume it (`routes/filters.py::get_unique_values`) hit `DatabaseHandler` directly.
- Resolved by deletion. `utils/filter_cache.py` and `tests/test_filter_cache.py` removed. The latent SQLi exposure on `f"SELECT DISTINCT {column} FROM {table}"` (line 85) goes away with the module. Mentions purged from `CLAUDE.md §5`, `routes/CLAUDE.md`, `utils/CLAUDE.md`, `.claude/rules/routes.md`, `.claude/agents/code-reviewer.md`, `.claude/agents/architecture-reviewer.md`, and `docs/UI_SCENARIOS_GAP_ANALYSIS.md` (KI-001 row flipped to ✅ Resolved).

### Profile Page — Body Composition Display Hooks (Issues #17 + #18)

- Added a "Body fat: X% · {ACE band}" line and a "Lean mass: Y kg" sub-line on the Profile insights card. Both read the most recent `body_composition_snapshots` row (Navy BFP when present, else BMI) and only render when a snapshot exists. Display-only — never alters estimator output. Local commit `de3e4d0`.

### Profile Coverage Bodymap — workout-cool Art (§3.6)

- Switched the Profile coverage card from `react-body-highlighter` to the vendored workout-cool SVG art. New `loadWorkoutCoolBodymapSvg()` + `annotateWorkoutCoolBodymapPolygons()` + `CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES` table in `static/js/modules/bodymap-svg.js`; the original react-body-highlighter exports remain in place for `muscle-selector.js`'s Advanced view. Local commit `18ad223`.
- Multi-muscle BACK regions (workout-cool ships `lats,upper-back,lowerback`) now carry both `data-bodymap-muscle` (representative singular) and `data-bodymap-muscles` (plural, comma-joined). `aggregateCoverageForRegion()` returns the worst coverage state across the set so the polygon fill reflects the least-confident muscle. Locked by `tests/test_profile_estimator.py::test_workout_cool_*` and `e2e/user-profile.spec.ts` (§3.6 case).

### Navbar — Hover Dropdowns + Icon Polish

- Desktop pointer-hover users now open Bootstrap dropdowns on `mouseenter` / `focusin`. Gated on `(hover: hover) and (pointer: fine) and (min-width: 992px)` so touch and mobile remain click-to-open. Keyboard handling (ArrowDown / Enter / Space / Escape) routes through the same open/close timers. Local commit `ef475cc`.
- Added saturated brand-color accents (violet / teal / amber) and a hover/focus pop-and-rotate keyframe to the static nav icons (`#nav-user-profile`, `#nav-body-composition`, `#nav-backup`). Dark-theme overrides and `prefers-reduced-motion` opt-out included. Swapped the Profile icon from `fa-user-circle` to `fa-user-alt`. Local commit `89561df`.

### workout.cool §5 — Curated YouTube IDs (Second Batch + Curation Closed)

- `data/youtube_curated_top_n.csv` expanded from 36 to **56 curated rows + header** with 20 owner-vetted additions; `scripts/apply_youtube_curated.py` re-applied so matching `exercises.youtube_video_id` cells are populated. Commit `ff244aa`.
- Curation closed by diminishing returns. Usage triage against `user_selection` + `workout_log` showed all remaining ~1,841 uncurated catalogue rows sit at 0–1 combined uses except `Barbell Close Grip Bench Press` at 2 uses; the 56-row set already covers every common/core lift with meaningful usage signal. Further expansion would require fabricating unvalidated IDs, which is worse UX than the search fallback. The designed hybrid behavior (curate top-N, search-fallback the long tail) stands. Closes `LEFTOVERS_BY_PRIORITY.md` row #12.

### Visual + Hardening

- Added Body Composition page baselines to `e2e/visual.spec.ts` (6 PNGs: desktop / tablet / mobile × light / dark). The visual-DB seed script now applies `add_body_composition_snapshots_table()` so the page renders without 500ing under the harness. Local commit `40d7dd2`.
- New `e2e/ui-hardening.spec.ts` (12 tests) locks medium-risk smoke contracts: toast stacking (single `#liveToast`, last-message-wins, stale `bg-*` cleared), form-state persistence (reload resets, routine cascade preserves, visibility-change preserves), modal keyboard/focus (open with `aria-modal=true`, `aria-labelledby` resolves, focus moves inside on shown, first Tab stays inside, close removes show + backdrop + `body.modal-open`). `docs/UI_SCENARIOS_GAP_ANALYSIS.md` gains a §0 Known Issues table (KI-001..KI-008). Local commit `0ae5b39`.

## Unreleased - May 22, 2026

### workout.cool §5 — Curated YouTube IDs (First Batch)

- `data/youtube_curated_top_n.csv` populated from header-only to **36 curated rows + header**; `scripts/apply_youtube_curated.py` applied so matching `exercises.youtube_video_id` cells are populated. Matched rows now open the embedded iframe; everything else still uses the YouTube search fallback (designed hybrid behavior). Commit `cf21191`.

## Unreleased - May 21, 2026

### Body Composition Issue #21 Hardening (PR #32)

- `captured_at` ISO format validation added to the snapshot create endpoint with two new pytest cases (one accept, one reject).
- New Playwright JS↔Python numeric parity case in `e2e/body-composition.spec.ts` walks the four formulas (`compute_navy` male + female, `compute_bmi` adult M / F) end-to-end against the JS mirror and asserts byte-identical rounded outputs.
- pytest baseline: 1374 passed (~2m 53s) on `main` post-merge.

### Response Contract Migration

- `/api/pattern_coverage` and the `routes/workout_plan.py` replace-exercise fallback branches (`no_candidates`, `selection_failed`, `duplicate`) now use `success_response()` / `error_response()`. The "no result" cases keep HTTP 200 by passing `status_code=200` to `error_response()` — they're user-facing "couldn't be processed" outcomes that pytest and the JS swap handler treat as 200 + `ok:false`. Commit `cbf745a`. CLAUDE_MD_AUDIT.md §2 exception list is now empty.

## Unreleased - May 20, 2026

### Body Composition Issue #21 (PR #31)

- New `/body_composition` page (standalone tab between Profile and Distribute) with tape-measurement inputs, U.S. Navy + BMI methods, ACE band tick + Jackson & Pollock comparison, trend SVG, and snapshot history table with per-row delete.
- New blueprint `routes/body_composition.py` (`GET /body_composition`, `POST/GET /api/body_composition/snapshot[s]`, `DELETE /api/body_composition/snapshots/<id>`); all four endpoints use the standard `success_response()` / `error_response()` envelopes.
- New pure-math module `utils/body_fat.py` with the four formulas (`compute_navy`, `compute_bmi`, `ace_category`, `jackson_pollock_ideal`) carrying the "must match JS mirror" comment from Issue #17. New JS mirror in `static/js/modules/body-composition.js`.
- New migration `add_body_composition_snapshots_table()` (14 columns; 6 NOT NULL; descending captured_at index) registered in the startup sequence and in `tests/conftest.py`.
- New tests: `tests/test_body_fat.py` (42 cases), `tests/test_body_composition_routes.py` (18 cases), `tests/test_db_migration.py` (7 cases), `e2e/body-composition.spec.ts` (4 Chromium specs).
- Source of truth: `docs/body_composition/development_issues.md` (Issue #21, now Resolved).

### Fatigue Badge Polish (PR #28)

- Presentation-only restructure of `templates/_fatigue_badge.html` (drops `.card`/`.card-body`, switches to a `<section>` grid; eyebrow + info-icon header row, score + band readout row, period label right column on desktop / stacked on mobile). Rewrites `scss/_fatigue.scss` for a translucent surface harmonized with `.summary-frame` glass; score 2.1rem/700 tabular-nums; band pill chip; dashed-outline empty-state pill. Refreshes 12 visual snapshots. No `utils/fatigue.py`, no thresholds, no APIs, no calibration changes.

### Fatigue Stage 4 Close (Docs Only)

- Owner-approved felt-label calibration review walked PLANNING.md §4.1 → §4.3 to a no-change decision. 4 of 5 anchors agreed with computed bands; the lone disagreement on the `hard_4d` synthetic generator scenario only is treated as scenario under-shoot (Hypothesis B), not threshold drift. `utils/fatigue.py` thresholds remain the §24.B defaults. STAGE4_PARKED_HANDOFF.md is superseded; authoritative status lives in `docs/fatigue_meter/calibration-notes.md`. Phase 2 entry remains a separate owner decision.

## Unreleased - May 18, 2026

### workout.cool §4.6 + Post-§4 Housekeeping (PR #22 + PR #23)

- `e2e/visual-baseline-thumbnails.spec.ts` (18 tests) + `scripts/seed_visual_baseline.py` cover the §4.6 matrix: `/workout_plan` desktop / tablet / mobile × light / dark × simple / advanced (12) + `/workout_log` desktop / tablet / mobile × light / dark (6). Behavioural assertions only — screenshot PNGs are inspection artifacts, not committed pixel baselines.
- Nav-dropdown e2e off-viewport dark-mode-toggle stabilization, dependency pin bumps (Flask 3.1.1→3.1.3, pandas 2.2.3→3.0.3, click 8.1.7→8.3.3, Playwright 1.58.1→1.60.0, sass 1.69→1.94, TypeScript 5.3→5.9, node engine ≥18, XlsxWriter removed).

## Unreleased - May 15, 2026

### workout.cool §4 — free-exercise-db Exercise Thumbnails (PR #20)

- Vendored `static/vendor/free-exercise-db/` (873 `0.jpg` images, `exercises.json`, LICENSE, NOTICE.md, VERSION).
- New mapping pipeline (`scripts/map_free_exercise_db.py`, `scripts/curate_free_exercise_db_mapping.py`, `data/free_exercise_db_mapping.csv` — 1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed). Apply via `scripts/apply_free_exercise_db_mapping.py`.
- Surfaces `media_path` in `/get_workout_plan` and `/get_workout_logs` JSON. `static/js/modules/exercise-helpers.js` adds `escapeHtml()` + `resolveExerciseMediaSrc()`. Workout-log template uses a new `safe_media_path` Jinja filter for server-side defense in depth.
- Renders 32×32 rounded thumbnails on `/workout_plan` (JS row renderer) and `/workout_log` (server-rendered). `static/css/components.css` adds `.exercise-cell .exercise-thumbnail`.

## Unreleased - May 11, 2026

### AI Workflow Refit

- Completed the local second-brain T3.1 closeout: lightweight ADR format in `docs/DECISIONS.md`, documentation retention rules in `docs/ai_workflow/DOC_RETENTION.md`, and refreshed workflow/doc indexes.
- Marked `.claude/SHARED_PLAN.md` as local audit history in `.gitignore`; active workflow truth is now `docs/MASTER_HANDOVER.md` plus `docs/ai_workflow/INDEX.md`.

### workout.cool Integration §5 — Exercise Reference Video Modal

- Added nullable `youtube_video_id TEXT` support for `exercises`, route contracts for `/get_workout_plan` and `/get_workout_logs`, and a strict header-only curated CSV/apply script path for future manual video IDs.
- Added a shared Bootstrap reference-video modal and per-row play buttons on `/workout_plan` and `/workout_log`. NULL or malformed IDs open a YouTube search fallback; valid IDs use official `https://www.youtube.com/embed/<id>` embeds and clear the iframe on close.
- Content note: curated video IDs are not populated by this ship. Until `data/youtube_curated_top_n.csv` is filled and `scripts/apply_youtube_curated.py` is run, every exercise uses the search fallback. See `docs/workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md`.
- Verification: `tests/test_youtube_video_id.py` 40/40 passed; Chromium Playwright `e2e/workout-plan.spec.ts` + `e2e/workout-log.spec.ts` 52/52 passed.

## Unreleased - May 2, 2026

### Muscle Selector — First-Party Advanced Body Map

- Replaced the workout-plan Advanced-mode SVG source with original first-party body maps under `static/bodymaps/hypertrophy-advanced/`. Simple-mode (workout.cool) art is unchanged.
- Advanced map regions now target sub-muscles directly via `data-canonical-muscles`, so clicking the SVG can select one child such as `upper-chest`, `rhomboids`, or `erector-spinae` without selecting the whole parent group.
- Updated selector hover matching so parent legend rows highlight all covered child regions in the first-party advanced SVGs.
- `static/vendor/react-body-highlighter/` is **retained** — `static/js/modules/bodymap-svg.js` still uses it for the `/user_profile` coverage bodymap. Swapping that surface to first-party art is deferred to a future PR.

### Fatigue Meter Phase 1 — Server-Rendered Projected-Fatigue Badge

- Added a single-score fatigue badge to `/weekly_summary` and `/session_summary`. Computed server-side and rendered as a Bootstrap-card partial (`templates/_fatigue_badge.html`), it surfaces one of four bands — `light`, `moderate`, `heavy`, `very_heavy` — for the planned program.
- New pure-math module `utils/fatigue.py` (stdlib-only, no DB) implements the §24.B model: movement-pattern weights, rep-range and load-bucket multipliers, RIR multipliers, per-set / session / weekly aggregation, and threshold classification. Backed by 55 tests in `tests/test_fatigue.py`.
- New DB shim `utils/fatigue_data.py` runs the badge's read — a fresh `SELECT us.routine, us.sets, us.min_rep_range, us.max_rep_range, us.rir, e.movement_pattern FROM user_selection us LEFT JOIN exercises e …` — per the locked D13 override (do not reuse already-aggregated summary rows).
- Counting Mode invariant — fatigue uses raw set count unconditionally and ignores `?counting_mode=raw|effective` (locked D3 override). `/session_summary` returns byte-identical fatigue HTML under both modes.
- New SCSS partial `scss/_fatigue.scss` provides one accent color per band, dark-mode parity, and a 576px mobile breakpoint. Wired via a single `@import "fatigue";` in `scss/custom-bootstrap.scss`.
- Source for everything that landed: `docs/fatigue_meter/PLANNING.md` (Stage 0 → Stage 2 Chapter 1.6) and the locked decisions in `docs/fatigue_meter/BRAINSTORM.md §13` and §24.A–E.

### Validation

- pytest: 1160 passed (~2m 25s, 2026-05-03) on `feat/fatigue-meter-phase-1-rebased` — 1080 origin/main baseline + 80 new (55 in `tests/test_fatigue.py` covering per-set math, aggregation, threshold classification at band boundaries, and the §24.B worked example "6 exercises × 3 sets at RIR 2, 8–12 reps, mostly compound" → ≈ 32 ± 1; remainder from `tests/test_priority0_filters.py` extensions and rebased prerequisites). Lower than the 1345 figure produced from the original feat-branch tree because origin/main does not carry workout-cool §3+§4+§5 or body composition.
- Playwright (Chromium full suite, 2026-05-03 from clean DB, post-drop of `a0a0a18`): **408 passed, 2 failed in 10.6m**. The single repeatable red is `nav-dropdown.spec.ts:117 dark mode toggle still works after navbar restructure` — a pre-existing failure on `origin/main` itself, unrelated to the fatigue meter (the dark-mode toggle bounding box renders off-viewport at 1440 width; this is what the dropped commit had been masking via `dispatchEvent('click')`). The second failure (`program-backup.spec.ts:79 can create a backup from the dedicated page`) is a DB-state-pollution flake from sequential full-suite execution — passes in isolation from a clean DB. **Effective post-drop state: 409 / 1.** The 12 weekly+session-summary visual snapshots (mobile + tablet + desktop, light + dark) were refreshed in a separate `test(fatigue §1.4)` commit; all other visual baselines remain at origin/main's authoritative copies. See `docs/fatigue_meter/PLANNING.md §2.7` post-drop addendum.
- Copy verified prescriptive-language-free across rendered badge HTML on `/weekly_summary`, `/session_summary`, and the `?counting_mode=raw|effective` variants. Whole-word scan for `should | must | reduce | deload | too | MRV | MEV` returned zero matches.

### Non-Goals (intentionally not in Phase 1)

- No `/fatigue` page, no `/api/fatigue/*` endpoints — server-rendered badge only.
- No DB schema changes — the first schema change in this feature is reserved for Phase 3 (user-calibrated thresholds).
- No prescriptive guidance, no auto-adjusted plans, no blocked actions. Per `BRAINSTORM.md §1`, the badge is descriptive only and never gates a user action.
- No per-muscle / Local-vs-Systemic-vs-Joint channels — deferred to Phase 2.

### Migration Notes

- Pre-flight backup recorded as `/api/backups` row id 5 (`pre-fatigue-meter-2026-05-01`). This is the rollback floor; do not delete until Phase 1 has been live and clean for ≥2 weeks.
- No new Python or JS dependencies. SCSS partial routed through the existing `npm run build:css` pipeline; `static/css/bootstrap.custom.min.css` rebuilt and committed.
- The `feat/fatigue-meter-phase-1` branch was rebased onto `origin/main` via cherry-pick into `feat/fatigue-meter-phase-1-rebased` to lift fatigue commits cleanly onto the post-§3+§4+§5 main without carrying workout-cool §4 image assets or §5 YouTube modal scope. See `docs/fatigue_meter/PLANNING.md §1.5` for the original branch rationale.

## Unreleased - April 24, 2026

### UI / Redesign
- Completed the Calm Glass redesign cleanup and merged the redesigned CSS/runtime surface to `main`.
- Consolidated runtime CSS to 8 global bundles plus 8 route-specific page bundles, including the Backup Center page.
- Removed the legacy CSS sources after the P9/P10 migration and refreshed visual baselines.

### Backup Center
- Hardened the dedicated `/backup` workspace with restore safety, save-current-plan-first flow, inline restore results, skipped-exercise visibility, warning state for zero-restored restores, metadata editing, search, sorting, empty-save warning, and program auto-backup retention support.
- Added Backup Center route/navigation coverage and focused backup E2E coverage.

### Data / Recovery
- Retired the old `SEED_DB_PATH` contract after seed recovery was replaced with quarantine-only recovery plus normal startup initialization.
- Added startup database snapshots under `data/auto_backup/` for local disaster recovery.

### Documentation
- Removed completed execution plans and obsolete redesign/backup handoff artifacts from the active `docs/` surface.
- Refreshed the docs index, CSS ownership map, E2E inventory, Backup Center doc, and live Claude audit snapshot.

## Unreleased - April 11, 2026

### Cleanup
- Closed the spring-cleanup Phase 4 validation path covering `4A`, `4F`, `4G`, `4H`, `4J`, `4K`, `4L`, `4M`, `4N`, and `4O`.
- Landed the 3a-3h cleanup rollup in `12c90ac` and the 4J orphan frontend-module removal in `596acde`.
- Reduced `utils/` Python files from 34 to 27, template files from 15 to 9, `static/js/modules/` files from 24 to 21, and total Python LOC from roughly 27,000 to 25,546.
- Retired the legacy `utils.business_logic` and `utils.data_handler` modules and deleted their dedicated test files after a zero-caller audit.
- Removed the package-level `get_workout_logs` compatibility export from `utils/__init__.py`.
- Updated `app.py` to import `initialize_database` from `utils.db_initializer` directly.

### Bug Fixes
- Fixed plan-only Progression suggestions and current-value prefill before workout-log history exists in `ec748ba`.
- Closed the 4M Weekly/Session summary counter UX follow-up by showing Effective Sets and Raw Sets side-by-side and keeping contribution mode as the only summary-page selector.

### Data
- Regenerated the catalog-only seed database in `0e0ca3b` and verified the seed path hardening against `data/backup/database.db`.

### Validation
- Current pytest baseline: `938 passed, 1 skipped`.
- Full Chromium Playwright's latest recorded full run remains `315 passed`; summary-page Playwright is green at `20 passed`.
- 4M summary follow-up reverified on 2026-04-15 with focused summary pytest (`95 passed`) and summary-page Playwright (`20 passed`).

### Migration Notes
- Stop importing `DataHandler` or `BusinessLogic`; use the concrete live modules that now own those responsibilities instead.
- Stop relying on `from utils import get_workout_logs`; import `get_workout_logs` from `utils.workout_log` directly.
- New code should prefer concrete module imports over package-level re-exports from `utils/__init__.py`.

## v1.5.0 - February 5, 2026

### New Features: Auto Starter Plan Generator Phase 2

#### Double Progression Logic
- Smart progression suggestions based on rep range performance
- When hitting top of rep range (e.g., 12 reps in 8-12 range) → suggests weight increase
- When below minimum (e.g., 6 reps in 8-12 range) → suggests pushing reps back into range
- Detects repeated failures and suggests weight reduction
- Conservative increments for novices (2.5kg) vs experienced lifters (5kg)
- Considers effort (RIR 1-3 or RPE 7-9) before suggesting weight increase

#### Priority Muscle Reallocation
- New `priority_muscles` parameter in plan generator API
- Automatically boosts volume for selected muscle groups
- Adds +1 set to existing accessories targeting priority muscles
- "Clear volume for volume" strategy: reduces non-essential work to make room
- Never removes core movement patterns (squat, hinge, push, pull)
- Available via `/get_generator_options` endpoint

#### Movement Pattern Coverage Analysis
- New `/api/pattern_coverage` endpoint
- Analyzes workout plan for movement pattern balance
- Tracks sets per routine (warns if outside 15-24 range)
- Detects missing core patterns (squat, hinge, horizontal/vertical push/pull)
- Warns about push/pull imbalance (>50% skew)
- Flags excessive isolation-to-compound ratio
- Returns actionable recommendations with severity levels

### API Changes
- `POST /generate_starter_plan`: Added `priority_muscles` parameter
- `GET /get_generator_options`: Added `priority_muscles.available` with all muscle groups
- `GET /api/pattern_coverage`: New endpoint for program analysis
- `POST /get_exercise_suggestions`: Enhanced with double progression logic

### Tests
- Added 25 tests for double progression logic
- Added 15 tests for priority muscle and pattern coverage
- Total test coverage: 294 tests passing

### Documentation
- New `docs/archive/PLAN_GENERATOR_IMPLEMENTATION.md` tracking document
- Documents Phase 1 (complete) and Phase 2 features

---

## v1.4.1 - November 10, 2025

### Bug Fixes
- Fixed Columns button dropdown overlap in Workout Plan table
- Fixed Compact/Comfortable density toggle not responding to clicks

### Improvements
- Added Escape key support to close column menu
- Better ARIA labels and keyboard accessibility
- Mobile-responsive menu positioning

---

## v1.4.0 - November 2, 2025

### Dependency Optimization
- Removed jQuery dependency (~85KB saved)
- Removed unused `requests` package
- Set up custom Bootstrap build infrastructure (~50% size reduction when activated)
- Pinned all package versions for reproducible builds

### New
- Native JavaScript table sorting (replaced jQuery DataTables)
- Custom Bootstrap SCSS build system (`npm run build:css`)

---

## v1.3.0 - 2025

### Workout Plan Dropdowns Refresh
- Modern dropdown UI with progressive enhancement
- Full keyboard navigation (Arrow keys, Home/End, Escape, typeahead)
- WCAG 2.2 AA+ accessibility compliance
- Mobile sheet-style dropdowns
- Search functionality for long option lists

---

## v1.2.0 - 2025

### Workout Plan Modernization
- Modern 2025 visual refresh
- CSS custom properties (`--wp-*` tokens)
- Enhanced semantic HTML and ARIA attributes
- Improved form controls and table styling
- Dark mode support
- Reduced motion support

---

## v1.1.0 - 2025

### Navbar Modernization
- Modern 2025 visual refresh with fluid typography
- Sticky header with compact mode on scroll
- Enhanced mobile menu (full-screen overlay, focus trap)
- CSS custom properties (`--nav-*` tokens)
- WCAG 2.2 AA+ accessibility compliance
- Dark mode support

---

## v1.0.0 - 2025

### Welcome Screen Refresh
- Modern 2025 visual design
- Fluid typography with `clamp()`
- CSS custom properties (`--welcome-*` tokens)
- Enhanced accessibility (ARIA labels, keyboard navigation)
- Dark mode and reduced motion support
- Container queries for responsive card layouts
