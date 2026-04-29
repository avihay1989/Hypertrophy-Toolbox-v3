# Changelog

All notable changes to Hypertrophy Toolbox v3.

## Unreleased - April 30, 2026

### workout.cool Integration §5 — Exercise Reference Video Modal

- Added a per-row reference-video play button on `/workout_plan` and `/workout_log` that opens a shared Bootstrap modal (one instance, included once via `templates/partials/exercise_video_modal.html` in `base.html`).
- New nullable `youtube_video_id TEXT` column on `exercises`, applied via the standard guarded-`ALTER` migration in `utils/db_initializer.py`. Fully additive — every existing row defaults to NULL and renders the search-fallback variant.
- `/get_workout_plan` and `/get_workout_logs` JSON, plus the server-rendered `/workout_log` template, now include `youtube_video_id` via `LEFT JOIN exercises ... COLLATE NOCASE`.
- New `static/js/modules/exercise-video-modal.js` exports `openExerciseVideoModal()` and `buildPlayButton()`. Iframe `src` is set only on open and blanked on close so playback stops; focus returns to the triggering button; malformed/NULL ids fall through to a YouTube search CTA.
- New `scripts/apply_youtube_curated.py` reads `data/youtube_curated_top_n.csv` (header-only by default) and populates `youtube_video_id` with strict, all-or-nothing validation: 11-char id regex (`^[A-Za-z0-9_-]{11}$`), no duplicates (case-insensitive), no blanks, no unknown exercise names. Idempotent — re-running with the same content produces no DB delta.
- ToS-compliance posture: embed only via `https://www.youtube.com/embed/<id>`; "Watch on YouTube" link present on every embed surface with `target="_blank"` + `rel="noopener noreferrer"`; no thumbnail or video-data caching/rehosting.

### workout.cool Integration §3 — Simple-Mode Body Map Hybrid Swap

- Replaced the simple-mode muscle-selector SVG art on `/workout_plan` with workout.cool's anatomy art (vendored under `static/vendor/workout-cool/` at pinned upstream SHA `77f25a922b51be7d96bd051c5d2096959f0d61a8`, MIT). Advanced mode still uses `react-body-highlighter` — both views share the same canonical muscle keys.
- Added `SVG_PATHS[mode][side]` + `getSvgPathForMode()` in `static/js/modules/muscle-selector.js`; `switchViewMode()` now reloads the SVG variant and preserves selection across the swap.
- Multi-key region support: workout.cool's `BACK` region maps to three of our simple keys (`lats`, `upper-back`, `lowerback`), expanded through `SIMPLE_TO_ADVANCED_MAP` to five advanced children. Region renders `selected` / `partial` / unselected based on how many of those advanced children are in `selectedMuscles`.
- Profile coverage body map (§3.6) intentionally untouched — `static/js/modules/bodymap-svg.js` is unchanged and continues to back the user-profile coverage view.

### Validation
- pytest: 1216 passed (~2m 59s) — 40 new in `tests/test_youtube_video_id.py`, plus the §3 mapping tests already in `tests/test_muscle_selector_mapping.py`.
- Playwright (Chromium): `e2e/workout-plan.spec.ts` 33/33 (5 §5 + 3 §3 + 25 prior); `e2e/workout-log.spec.ts` 22/22 (3 §5 + 19 prior).

### Migration Notes
- New databases get `youtube_video_id` automatically. Existing local databases pick it up on next app start via the guarded `ALTER TABLE` in `utils/db_initializer.py`. No manual migration required.
- `data/youtube_curated_top_n.csv` ships header-only — the app is fully functional with every row's `youtube_video_id` NULL. Drop curated rows into the CSV and run `.venv/Scripts/python.exe scripts/apply_youtube_curated.py` to populate.

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
