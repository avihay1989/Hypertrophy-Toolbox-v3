# Changelog

All notable changes to Hypertrophy Toolbox v3.

## Unreleased - April 10, 2026

### Cleanup
- Retired the legacy `utils.business_logic` and `utils.data_handler` modules and deleted their dedicated test files after a zero-caller audit.
- Removed the package-level `get_workout_logs` compatibility export from `utils/__init__.py`.
- Updated `app.py` to import `initialize_database` from `utils.db_initializer` directly.

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
