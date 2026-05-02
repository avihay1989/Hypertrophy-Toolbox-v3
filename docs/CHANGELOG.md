# Changelog

All notable changes to Hypertrophy Toolbox v3.

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

- pytest: TBD — to be filled in after the post-rebase pytest run from `feat/fatigue-meter-phase-1-rebased`.
- Playwright (Chromium): TBD — to be filled in after the post-rebase Playwright run.
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
