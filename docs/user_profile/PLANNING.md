
# Plan — User Profile tab with weight/rep auto-estimation

> **Two-part document.** Part 1 = planning (this file). Part 2 = `EXECUTION_LOG.md` in this same folder, written by the implementing agents as they tick items off.

> **Sized for small-agent execution.** Each task block lists its own context (files, line refs, exact symbols) so a Sonnet/Codex-mini agent can pick up a single block without reading the whole plan.

---

## Context

The app currently has no per-user personalization layer. When a user adds an exercise on `/workout_plan`, the **Workout Controls** form ([templates/workout_plan.html:69-113](../../templates/workout_plan.html#L69-L113)) is hardcoded to `weight=25, sets=3, RIR=3, RPE=7, min_rep=6, max_rep=8` and never adapts. The user must guess sensible values for every exercise, every time.

**Goal:** add a **User Profile** tab that captures (a) demographics, (b) strength on ~14 reference lifts, and (c) rep-range preference per movement tier (complex / accessory / isolated). When the user picks an exercise on the Plan page, the six Workout Controls fields are pre-filled with an *estimate* derived from the profile + last logged set. The user can override before clicking **Add Exercise** — nothing is auto-applied.

**Confirmed via clarification:**
- Estimation = **reference-lift + ratio** (Epley 1RM × tier ratio × rep-range %).
- **Last logged set wins** when the exercise has logging history; fall back to profile estimate; fall back to existing hardcoded defaults.
- Nav link goes in the **right-side controls** of the navbar (next to dark-mode toggle).
- For excluded equipment (TRX, Bosu_Ball, Cardio, Recovery, Yoga, Vitruvian, Band, Stretches) and missing-data cases, **keep current defaults** — purely additive feature.

**Refactor invariant** (from CLAUDE.md §1): no existing flow may regress. Plan/Log/Analyze/Progress/Distribute/Backup behavior is unchanged. New code is additive.

---

## Prerequisites — design constants (Phase A pins these before any code is written)

These are *decisions* that need to live somewhere reviewable. Phase A produces a single doc (`docs/user_profile/DESIGN.md`) capturing them so smaller agents in Phases B–H reference one place.

> **Phase A complete** — pinned in [DESIGN.md](DESIGN.md). Sections below kept for reference.

### A.1 Tier classification rule
- [x] **Isolated**: `mechanic = 'Isolation'` (case-insensitive) **OR** `movement_pattern IN ('UPPER_ISOLATION','LOWER_ISOLATION')`.
- [x] **Complex**: exercise name matches a curated allowlist of "main lifts" (≈30 names; barbell back/front squat, conventional/sumo/Romanian deadlift, barbell/dumbbell flat/incline bench, OHP/military, weighted dips, weighted pull-ups, barbell row, T-bar row, hip thrust). Allowlist lives in `utils/profile_estimator.py` as a frozenset; can be extended later.
- [x] **Accessory**: everything else (i.e. `Compound`/`Hold` not in the Complex allowlist).
- [x] Excluded for estimation entirely (return "no estimate" sentinel): `equipment IN ('Trx','Bosu_Ball','Cardio','Recovery','Yoga','Vitruvian','Band','Stretches')`. Confirmed equipment values per the codebase exploration.

### A.2 1RM formula
- [x] **Epley**: `1RM = weight × (1 + reps/30)`. Cap reps at 12 (above 12 the formula loses accuracy — clamp).
- [x] If `weight = 0` (bodyweight pull-ups / dips), store reps-only; estimation for similar bodyweight exercises returns `weight=0` and copies reps.

### A.3 Default tier ratios (against the user's complex-lift 1RM for the same muscle)
- [x] Complex tier: 100%
- [x] Accessory tier: 70%
- [x] Isolated tier: 40%
- [x] Stored as constants in `utils/profile_estimator.py`; not user-tunable in v1.

### A.4 Rep-range → working-set % of 1RM (used to convert estimated 1RM → suggested weight)
- [x] 4–6 reps (heavy): **85%** of 1RM, RIR=1, RPE=9
- [x] 6–8 reps (moderate): **77%** of 1RM, RIR=2, RPE=8
- [x] 10–15 reps (light): **65%** of 1RM, RIR=2, RPE=7.5
- [x] Rounding: nearest 1.25 kg for free-weight equipment, nearest 1 kg for machines/cables, nearest 0.5 kg for dumbbells under 10 kg.

### A.5 Reference-lift mapping (primary muscle → key questionnaire lift)
- [x] chest → barbell/dumbbell bench press
- [x] quadriceps → barbell back squat
- [x] hamstrings → leg curl, fallback Romanian deadlift
- [x] glutes → conventional/Romanian deadlift
- [x] lats / mid_back → weighted pull-ups (or bodyweight pull-ups), fallback barbell row
- [x] front_delts / shoulders → military / shoulder press, fallback bench press × 0.6
- [x] side_delts → dumbbell lateral raise
- [x] rear_delts → barbell row × 0.5
- [x] biceps → barbell bicep curl
- [x] triceps → triceps extension, fallback weighted dips × 0.5
- [x] calves, forearms, abs, neck → no reference lift → fall back to hardcoded defaults
- [x] Mapping table lives in `utils/profile_estimator.py` keyed on canonical muscle names from `utils/constants.py:MUSCLE_GROUPS`.

### A.6 Estimation precedence (in order)
- [x] **1. Last logged set** for this exact exercise (most recent row in `workout_log` joined to `user_selection`). Use its weight, copy min_rep/max_rep/sets/RIR/RPE.
- [x] **2. Profile estimate** via reference-lift + ratio + rep-range %.
- [x] **3. Hardcoded defaults** (`weight=25, sets=3, RIR=3, RPE=7, min_rep=6, max_rep=8`) — current behavior.
- [x] All three paths return a struct `{weight, sets, min_rep, max_rep, rir, rpe, source: 'log'|'profile'|'default'}` so the UI can show provenance.

---

## Phase B — Data layer

Three new tables, idempotent. Follow the existing pattern at [utils/database.py:443-485](../../utils/database.py#L443-L485) (`add_progression_goals_table`, `add_volume_tracking_tables`).

> *** codex 5.5*** Add a tiny DB-level guard for the "one row only" rule instead of relying only on route discipline. Recommended shape: `id INTEGER PRIMARY KEY CHECK (id = 1)` for `user_profile`, and every demographics upsert writes `id = 1`. This makes accidental multi-profile rows impossible even if a future route/test bypasses the intended helper.

> *** codex 5.5*** Prefer `INSERT ... ON CONFLICT(...) DO UPDATE SET ...` for profile/lift/preference upserts instead of `INSERT OR REPLACE`. `REPLACE` is delete-then-insert in SQLite, which can churn `id`, reset implicit metadata, and surprise future foreign-key relationships. The current schema has no dependent FK yet, but this is a cheap safety improvement.

### B.1 Schema — `user_profile`
- [x] One row only. Columns: `id INTEGER PRIMARY KEY CHECK (id = 1)`, `gender TEXT`, `age INTEGER`, `height_cm REAL`, `weight_kg REAL`, `experience_years REAL`, `updated_at DATETIME`.
- [x] All non-`id` columns nullable (questionnaire is optional).
- [x] Demographics upsert MUST write `id = 1` literally; the `CHECK (id = 1)` makes accidental multi-profile rows impossible even if a future route bypasses the helper. (Per codex 5.5 — accepted by Opus 4.7 2026-04-26.)

### B.2 Schema — `user_profile_lifts`
- [x] Columns: `id INTEGER PK`, `lift_key TEXT UNIQUE NOT NULL` (slug like `barbell_bench_press`), `weight_kg REAL`, `reps INTEGER`, `updated_at DATETIME`.
- [x] Slugs come from a frozenset of ~14 canonical keys defined in `utils/profile_estimator.py` (the questionnaire lifts).
- [x] UNIQUE on `lift_key`. Upserts use `INSERT INTO user_profile_lifts (...) VALUES (...) ON CONFLICT(lift_key) DO UPDATE SET weight_kg=excluded.weight_kg, reps=excluded.reps, updated_at=excluded.updated_at`. **Do NOT use `INSERT OR REPLACE`** — `REPLACE` is delete-then-insert in SQLite and churns `id`. (Per codex 5.5 — accepted by Opus 4.7 2026-04-26.)

### B.3 Schema — `user_profile_preferences`
- [x] Columns: `id INTEGER PK`, `tier TEXT UNIQUE CHECK(tier IN ('complex','accessory','isolated'))`, `rep_range TEXT CHECK(rep_range IN ('heavy','moderate','light'))`, `updated_at DATETIME`.
- [x] Three rows max. Defaults if missing: complex=heavy, accessory=moderate, isolated=light.
- [x] Upserts use `ON CONFLICT(tier) DO UPDATE SET rep_range=excluded.rep_range, updated_at=excluded.updated_at`. Same rationale as B.2.

### B.3a Demographics upsert — `user_profile`
- [x] Use `INSERT INTO user_profile (id, ...) VALUES (1, ...) ON CONFLICT(id) DO UPDATE SET ...`. No `REPLACE`. (Same rationale.)

### B.4 Wire startup
- [x] Add `add_user_profile_tables()` module function in `utils/database.py` (mirroring `add_volume_tracking_tables`).
- [x] Call it from `app.py:50-54` startup block, after `add_volume_tracking_tables()`.
- [x] Register the same call in `tests/conftest.py` initializer (search for `add_volume_tracking_tables` in conftest — same place).
- [x] **Add the 3 new tables to the `erase-data` route DROP list** in `app.py:144-152` (currently only drops `user_selection`, `progression_goals`, `muscle_volumes`, `volume_plans`, `workout_log`, `program_backup*`). Without this, a full data reset leaves stale profile data.
- [x] **Add the 3 new tables to the `clean_db` fixture DELETE list** in `tests/conftest.py:147-157`. Without this, profile data leaks between tests.
- [x] **Call `add_user_profile_tables()` in the `erase-data` reinitialize block** at `app.py:160-168` (after `add_volume_tracking_tables()`), same as startup.

> 🔍 **REVIEW (Opus 2026-04-26):** BLOCKING ISSUE #1 — The original plan missed 3 critical wiring points. The `POST /erase-data` route in `app.py` drops ALL tables and reinitializes — if the new tables aren't in the DROP list and the reinit block, a user reset will either fail (FK errors) or leave orphaned profile data. Similarly, `tests/conftest.py:clean_db` fixture deletes from a hardcoded table list — new tables must be added or tests will leak state. Verified against live `app.py:130-168` and `tests/conftest.py:142-161`.

**Files to touch:** `utils/database.py`, `app.py`, `tests/conftest.py`.
**Tests:** unit test that creates an empty DB, runs the initializers, then asserts each table+columns exist (use `PRAGMA table_info`). Pattern: see existing tests in `tests/test_database*.py`. **Also add a test that verifies `erase-data` correctly drops and recreates the 3 profile tables.**

---

## Phase C — Estimation utility (`utils/profile_estimator.py`)

Pure-Python module; no Flask imports. All logic lives here so it's unit-testable in isolation.

### C.1 Constants
- [x] `KEY_LIFTS: frozenset[str]` — 14 slugs matching questionnaire.
- [x] `COMPLEX_ALLOWLIST: frozenset[str]` — exercise-name keywords (lowercase, substring match) for tier classification.
- [x] `EXCLUDED_EQUIPMENT: frozenset[str]` — `{'Trx','Bosu_Ball','Cardio','Recovery','Yoga','Vitruvian','Band','Stretches'}`.
- [x] `TIER_RATIOS: dict[str,float]` and `REP_RANGE_PCT: dict[str,float]` per A.3/A.4.
- [x] `MUSCLE_TO_KEY_LIFT: dict[str, list[str]]` per A.5 (ordered fallback chain).

### C.2 Public functions
- [x] `classify_tier(exercise_row: dict) -> Literal['complex','accessory','isolated','excluded']` — uses A.1.
- [x] `epley_1rm(weight: float, reps: int) -> float` — clamp reps to 12.
- [x] `estimate_for_exercise(exercise_name: str, *, db: DatabaseHandler) -> dict` — orchestrates A.6 precedence and returns the result struct. Reads exercises table, profile tables, and `workout_log` via the passed-in handler.
- [x] `_lookup_last_logged(exercise_name, db) -> dict | None` — most recent log row from `workout_log` (query directly — **no JOIN to `user_selection` needed**).
- [x] `_estimate_from_profile(exercise_row, profile_lifts, preferences) -> dict | None` — pure function (no DB), easy to unit-test.

> 🔍 **REVIEW (Opus 2026-04-26):** BLOCKING ISSUE #2 — The original description said "most recent log row joined to `user_selection`". This is unnecessary. The `workout_log` table already stores all needed fields directly: `scored_weight`, `scored_min_reps`, `scored_max_reps`, `scored_rir`, `scored_rpe`, and `planned_sets` (see `tests/conftest.py:274-278` for the full column list). **Corrected to query `workout_log` directly.**
>
> **Column selection for `_lookup_last_logged`:** Use `scored_*` columns with `planned_*` fallbacks via `COALESCE`:
> - `weight = COALESCE(scored_weight, planned_weight)`
> - `min_rep = COALESCE(scored_min_reps, planned_min_reps)`
> - `max_rep = COALESCE(scored_max_reps, planned_max_reps)`
> - `rir = COALESCE(scored_rir, planned_rir)`
> - `rpe = COALESCE(scored_rpe, planned_rpe)`
> - `sets = planned_sets` (sets aren't "scored" — they're structural)
>
> Order by `id DESC LIMIT 1`. Verified `workout_log.created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` exists (`utils/db_initializer.py:250`), but `id` is strictly monotonic AUTOINCREMENT and tie-free, so prefer it. (Resolved by Opus 4.7, 2026-04-26.)

### C.3 Logging / errors
- [x] Use `from utils.logger import get_logger`. No exceptions out of `estimate_for_exercise` — it always returns *some* struct (worst case `source='default'`).

**Files to touch (new):** `utils/profile_estimator.py`, `tests/test_profile_estimator.py`.
**Tests:** ≥10 unit cases covering every branch — log-hit, profile-hit, default-hit, excluded equipment, isolation tier, complex allowlist, missing muscle map, 1RM clamp, rounding rules.

---

## Phase D — Backend routes (`routes/user_profile.py`)

Blueprint pattern from [routes/progression_plan.py](../../routes/progression_plan.py) (helper validators, `success_response`/`error_response`, `DatabaseHandler`, `get_logger`).

### D.1 Blueprint
- [x] `user_profile_bp = Blueprint('user_profile', __name__)`.
- [x] Register in `app.py:60-71` blueprint block AND in `tests/conftest.py` (CLAUDE.md §4.A warns: missing either is a 404 in tests).

### D.2 Routes
- [x] `GET /user_profile` → renders `templates/user_profile.html` with current profile/lifts/preferences (or empty state).
- [x] `POST /api/user_profile` → upsert demographics. JSON shape `{gender, age, height_cm, weight_kg, experience_years}`. All optional. Validate types/ranges (age 10–100, height 100–250, weight 30–300, experience 0–80).
- [x] `POST /api/user_profile/lifts` → upsert one or many lift entries. Body `[{lift_key, weight_kg, reps}, ...]`. Reject unknown `lift_key`. Allow `null`/missing values to clear an entry.
- [x] `POST /api/user_profile/preferences` → upsert tier preferences. Body `{complex: 'heavy'|'moderate'|'light', accessory: ..., isolated: ...}`.
- [x] `GET /api/user_profile/estimate?exercise=<name>` → calls `profile_estimator.estimate_for_exercise(name)` and returns the struct. **This is the endpoint the workout-plan JS will call.**

> 🔍 **REVIEW (Opus 2026-04-26):** Exercise names in this app contain spaces, parentheses, slashes — e.g. `"Barbell Bench Press (Flat)"`. Ensure the implementing agent: (1) URL-encodes on the client side via `encodeURIComponent()`, and (2) reads via `request.args.get('exercise')` (not `request.args['exercise']` which would 400 on missing key).

### D.3 Response contract
- [x] All endpoints return `success_response(data=...)` / `error_response(code, message, status)` per [utils/errors.py](../../utils/errors.py). No legacy `{success: true}` shape.

**Files to touch (new):** `routes/user_profile.py`, `tests/test_user_profile_routes.py`.
**Tests:** Flask test client coverage for each endpoint — happy path, validation errors, missing data, unknown lift_key, estimate endpoint with all three precedence sources.

---

## Phase E — Frontend: profile page

### E.1 Template — `templates/user_profile.html`
- [x] Extends `base.html`.
- [x] Three collapsible sections matching `collapsible-frame action-frame frame-calm-glass` pattern from `workout_plan.html`:
  1. **Demographics** — gender (M/F/Other), age, height (cm), weight (kg), experience (years).
  2. **Reference lifts** — 14 rows, each with weight + reps inputs. Label per the user's spec (e.g., "Barbell or Dumbbell Bench Press" for the first row). Inputs may be left blank.
  3. **Rep-range preferences** — 3 radio groups (one per tier: complex/accessory/isolated) with three options each (heavy 4–6 / moderate 6–8 / light 10–15).
- [x] Single **Save** button per section (saves only that section). Use `apiFetch` (or `api.post()`) from `fetch-wrapper.js`.
- [x] Create **`pages-user-profile.css`** as a new route-scoped CSS bundle loaded from the template's `{% block page_css %}`. Update `.claude/rules/frontend.md` to reflect 8 route bundles instead of 7.
- [x] **Update `.claude/rules/frontend.md` to fix stale `apiCall` references.** Per codex 5.5 (accepted by Opus 4.7 2026-04-26): `apiCall` does not exist as an export. Slice-E must replace every occurrence of `apiCall` in `frontend.md` with `apiFetch` (or `api.post()` / `api.get()` where appropriate), specifically in:
  - the "Adding a JS module + CSS" / module-skeleton example section,
  - the API response / fetch-wrapper section,
  - any `import { apiCall } from './fetch-wrapper.js'` snippet.
  - Run `Grep -i apicall .claude/rules/frontend.md` after the edit to confirm zero matches remain.

> 🔍 **REVIEW (Opus 2026-04-26):** BLOCKING ISSUE #3 — CSS strategy. The original plan said "no new CSS bundle: extend `pages-workout-plan.css`". This conflicts with `.claude/rules/frontend.md` line 16 and the route-scope isolation contract established during the Calm Glass 2026 redesign (conversation `92929842`). Stuffing User Profile styles into `pages-workout-plan.css` violates route-level scope.
>
> **Resolution:** Create `pages-user-profile.css` as a new route bundle. The 7-file limit was a consolidation target, not a permanent cap. A new route = new bundle. Update `frontend.md` line 14 to include `pages-user-profile.css` and change the count from 7 to 8.

> 🔍 **REVIEW (Opus 2026-04-26):** BLOCKING ISSUE #4 — `apiCall` does not exist. The actual `fetch-wrapper.js` exports:
> - `apiFetch` (main function, line 121)
> - `api` object with `.get()`, `.post()`, `.put()`, `.patch()`, `.delete()` (line 252)
> - `isHandledApiError` and `logApiError` helpers
>
> There is NO `apiCall` export anywhere. **Corrected to `apiFetch` / `api.post()` above.** This same fix applies to Phase F and the "Existing functions/utilities to reuse" list at the bottom.

### E.2 JS module — `static/js/modules/user-profile.js`
- [x] ES6 module. Imports `apiFetch` (or `api`) from `./fetch-wrapper.js` and `showToast` from `./toast.js`.
- [x] On submit of each section, POSTs to the matching `/api/user_profile*` endpoint.
- [x] Toast on success/failure. No window reload.

### E.3 Nav link
- [x] Add a person/profile icon (`<i class="fas fa-user"></i>`) in the right-side controls block of [templates/base.html:152-195](../../templates/base.html#L152-L195). **Insert between the `muscleModeToggle` `<li>` (line 182-187) and the `darkModeToggle` `<li>` (line 189-194)**, with a `nav-divider` before it. Link target `/user_profile`. Add `id="nav-user-profile"` for testability.

> 🔍 **REVIEW (Opus 2026-04-26):** The original phrasing "to the left of the dark-mode toggle" was ambiguous — the right-side controls block has 4 items (Signature, Scale, Muscle Mode, Dark Mode). Made the insertion point explicit: between `muscleModeToggle` and `darkModeToggle`.

**Files to touch:** `templates/user_profile.html` (new), `static/js/modules/user-profile.js` (new), `static/css/pages-user-profile.css` (new), `.claude/rules/frontend.md` (update count), `templates/base.html`.

---

## Phase F — Workout-Plan integration

This is the value-delivery phase: pre-filling the Workout Controls when the user selects an exercise.

### F.1 Hook the exercise-change event
> **Corrected by Opus 4.7 2026-04-26 per codex 5.5:** the original "no existing change handler" claim was stale. `static/js/modules/workout-plan.js` already exports `handleExerciseSelection()` and wires it via `initializeWorkoutPlanHandlers()`. Slice-F must **modify the existing handler**, not register a second `change` listener (which would double-fetch and race the form-field writes).

- [x] **Add a shared helper** in `static/js/modules/workout-plan.js`:
  ```js
  async function applyUserProfileEstimateForSelectedExercise() { ... }
  ```
  Responsibilities, in one place: read `#exercise` value (no-op if empty), call `apiFetch('/api/user_profile/estimate?exercise=' + encodeURIComponent(name))`, set the six form fields (`#weight, #sets, #min_rep, #max_rep_range, #rir, #rpe`), update the provenance caption based on the response `source`, swallow network errors and fall through to the HTML defaults via the `source: 'default'` branch on the server side.
- [x] **Modify the existing `handleExerciseSelection()`** to call `applyUserProfileEstimateForSelectedExercise()` after its existing `updateExerciseDetails(selectedExercise)` call. **Preserve** the `updateExerciseDetails` call — do not delete it.
- [x] Add a small caption element near the Workout Controls form (subtle muted text under the controls, e.g. inside the `action-frame`) that the helper writes into. Strings: `from your last set` / `from your profile` / `default values`, picked off the response `source`.
- [x] Do **not** disable any field — user can still edit before clicking Add.
- [x] Do **not** add a second `change` listener on `#exercise`. Verify with a Playwright trace that only one fetch fires per change event.

### F.2 Don't break the existing add flow
> **Corrected by Opus 4.7 2026-04-26 per codex 5.5:** the active Add Exercise button (`#add_exercise_btn`) is currently wired in `workout-plan.js` to `handleAddExercise()` and its own local `resetFormFields()`. `static/js/modules/exercises.js:addExercise()` is a legacy global path imported in `app.js` but **not invoked by the template button**. Slice-F's **primary write target is `workout-plan.js`**; `exercises.js` is secondary/legacy context — only modify it if a test proves a legacy caller still reaches it.

- [x] **Primary:** in `workout-plan.js`, replace the body of the local `resetFormFields()` (the one called from `handleAddExercise()` after a successful add) with a single call to `applyUserProfileEstimateForSelectedExercise()` (defined in F.1). The legacy `weight=100, sets=1, rir=0, min_rep=3, max_rep=5, rpe=''` reset values are deleted.
- [x] If `#exercise` is empty post-add (rare — only if the user manually cleared it), the helper calls the estimate endpoint with an empty string; the server returns the `default` struct (`source: 'default'`, HTML defaults), which the helper writes into the form. No client-side branching needed.
- [x] **Secondary:** `addExercise()` in [exercises.js:81-148](../../static/js/modules/exercises.js#L81-L148) — payload, POST `/add_exercise`, validation — stays untouched. Only consider editing `exercises.js:resetFormFields` if Playwright proves a legacy code path still calls it; otherwise leave it (the template button does not reach it).
- [x] Confirm with a Playwright run that the workout-plan add/remove/clear flow has no regression.

> 🔍 **REVIEW (Opus 2026-04-26):** BLOCKING ISSUE #5 — `resetFormFields()` discrepancy. The current `resetFormFields()` in `exercises.js:229-237` sets:
> ```js
> sets=1, rir=0, weight=100, min_rep=3, max_rep_range=5, rpe=''   // ← post-add reset
> ```
> But the HTML `value=` attributes in `workout_plan.html:88-108` are:
> ```
> weight=25, sets=3, rir=3, rpe=7, min_rep=6, max_rep=8            // ← initial page-load
> ```
> And the plan's stated "hardcoded defaults" (Phase A.6 / DESIGN.md §8) are:
> ```
> weight=25, sets=3, rir=3, rpe=7, min_rep=6, max_rep=8            // ← matches HTML
> ```
> **There are TWO sets of defaults in the codebase.** The implementing agent needs to know:
> 1. HTML `value=` attributes are the initial page-load defaults
> 2. `resetFormFields()` sets DIFFERENT values after an exercise is added
>
> **Recommendation:** After adding an exercise, re-fetch the estimate for the currently selected exercise (the plan's intent). If no exercise is selected, reset to the HTML defaults (`weight=25, sets=3, rir=3, rpe=7, min_rep=6, max_rep=8`), NOT the current `resetFormFields` values.
>
> **Resolved (Opus 4.7, 2026-04-26):** Sign-off on Opus 4.6's recommendation. The implementing agent for Slice-F must:
> 1. Replace the body of `resetFormFields()` so that, post-add, it re-runs the same estimate handler the `#exercise` change event uses (with the still-selected exercise name). The handler internally falls through to HTML defaults via the `source: 'default'` branch when no estimate is available.
> 2. The legacy `weight=100, sets=1, rir=0, min_rep=3, max_rep=5, rpe=''` reset is **deleted**. There is no scenario where those values are correct.
> 3. If `#exercise` is empty after add (rare — only if the user manually cleared it), call the same handler with an empty string; the estimate endpoint returns the `default` struct, which yields the HTML defaults.

> *** codex 5.5*** The active Add Exercise button (`#add_exercise_btn`) is currently wired in `workout-plan.js` to `handleAddExercise()` and its local `resetFormFields()`; `static/js/modules/exercises.js:addExercise()` appears to be a legacy/global path imported in `app.js` but not used by the template button. Slice-F should treat `workout-plan.js` as the primary write target and only touch `exercises.js` if a test proves a legacy caller still reaches it.

> *** codex 5.5*** The plan should add one focused regression test around this exact flow: select exercise -> fields receive profile estimate -> click Add Exercise -> fields are still estimated for the selected exercise, not reset to either legacy defaults or stale hardcoded values.

**Files to touch:** `static/js/modules/workout-plan.js` (add the shared estimate helper, update the existing exercise-change handler, and route the local post-add `resetFormFields()` through the helper). Treat `static/js/modules/exercises.js` as legacy/secondary context only; edit it only if Playwright proves a live caller still reaches its reset path.

---

## Phase G — Tests

### G.1 Unit tests
- [x] `tests/test_profile_estimator.py` — Phase C cases (≥10).
- [x] `tests/test_user_profile_routes.py` — Phase D endpoints.
- [x] `tests/test_database_user_profile.py` — Phase B tables exist after init.

### G.2 Integration / Playwright E2E
- [x] New spec `e2e/user-profile.spec.ts` — fill profile, save each section, navigate to `/workout_plan`, pick an exercise, assert form fields are pre-filled with expected values, and Add Exercise still succeeds.
- [x] **Post-add reset regression test** (per codex 5.5, accepted by Opus 4.7 2026-04-26) — in the same spec or in `e2e/workout-plan.spec.ts`: select an exercise that has a profile-derived estimate, assert the six form fields show that estimate, click **Add Exercise**, then assert the six form fields **still show the same estimate** (i.e. the post-add reset re-fetched and re-applied via `applyUserProfileEstimateForSelectedExercise()`) — NOT the legacy `weight=100, sets=1` reset and NOT stale-blanked values. Pin the asserted weight to a deterministic value by seeding `user_profile_lifts` via the API in test setup.
- [x] Smoke run of `e2e/workout-plan.spec.ts` and `e2e/volume-progress.spec.ts` to confirm no regression in the existing flows.

### G.3 Verification gate (run via `/verify-suite` skill)
- [x] Full pytest passes (996 passed on 2026-04-26).
- [x] Chromium Playwright passes for the relevant specs (64 passed on 2026-04-26: workout-plan, volume-progress, user-profile, volume-splitter).

---

## Phase H — Documentation (the "executions" half)

### H.1 Living execution log
- [x] `docs/user_profile/EXECUTION_LOG.md` (already created as a stub) is appended by each implementing agent with:
  - the phase tag (B/C/D/...),
  - the actual files changed,
  - any constants or thresholds the agent had to guess,
  - test-suite delta after their phase.
- [x] Each phase's checkboxes in *this* plan get ticked only after the corresponding `EXECUTION_LOG.md` entry is added.

### H.2 Brief feature note
- [x] One short page `docs/user_profile/README.md` linking to: the design constants doc, the execution log, the route file, the estimator file. Single source of truth for future Claudes / users.

### H.3 CLAUDE.md
- [x] Add the User Profile route to the blueprint table in CLAUDE.md §2.
- [x] Re-verify and update the "Verified test counts" line in CLAUDE.md §5.

---

## Critical files (full list, for reference)

**New files:**
- `utils/profile_estimator.py`
- `routes/user_profile.py`
- `templates/user_profile.html`
- `static/js/modules/user-profile.js`
- `tests/test_profile_estimator.py`
- `tests/test_user_profile_routes.py`
- `tests/test_database_user_profile.py`
- `e2e/user-profile.spec.ts`
- `docs/user_profile/DESIGN.md`
- `docs/user_profile/EXECUTION_LOG.md` *(stub created in Phase 0)*
- `docs/user_profile/README.md`

**Modified files:**
- `utils/database.py` — add `add_user_profile_tables()`
- `app.py` — call init + register blueprint
- `tests/conftest.py` — call init + register blueprint
- `templates/base.html` — add nav icon
- `static/js/modules/workout-plan.js` — primary owner for exercise-change estimate call and post-add reset re-fetch
- `static/js/modules/exercises.js` — legacy/secondary context only; edit only if a test proves the template reaches it
- `CLAUDE.md` — blueprint table + test counts

**Existing functions/utilities to reuse (do not duplicate):**
- `DatabaseHandler` context manager — [utils/database.py:185](../../utils/database.py#L185)
- `success_response` / `error_response` — [utils/errors.py](../../utils/errors.py)
- `get_logger` — [utils/logger.py:121](../../utils/logger.py#L121)
- `apiFetch` / `api.post()` (frontend) — `static/js/modules/fetch-wrapper.js` *(not `apiCall` — that export does not exist)*
- `showToast` — `static/js/modules/toast.js`
- `MUSCLE_GROUPS`, `MUSCLE_ALIAS` — `utils/constants.py`
- `normalize_muscle`, `normalize_equipment` — `utils/normalization.py`
- Existing exercises-table query patterns in `routes/filters.py` and `utils/filter_predicates.py`

> 🔍 **REVIEW (Opus 2026-04-26):** Corrected `apiCall` → `apiFetch` / `api.post()`. The fetch-wrapper exports `apiFetch` (line 121) and `api` convenience object (line 252) — no `apiCall` export exists.

---

## Agent-sized task slicing (so smaller models can pick up one block)

Each numbered slice is self-contained — give a small agent only this slice + the referenced files. Approximate context budget per slice: < 30k tokens.

1. **Slice-A**: Phase A — write `docs/user_profile/DESIGN.md` per §A.1–A.6. Context: this plan + `utils/constants.py`, `utils/movement_patterns.py`, `utils/normalization.py`. No code edits.
2. **Slice-B**: Phase B — DB tables + startup wiring + DB tests. Context: `utils/database.py:443-485`, `app.py:50-58` (startup) + `app.py:130-168` (erase-data), `tests/conftest.py:30-36` (init) + `tests/conftest.py:142-161` (clean_db).
3. **Slice-C1**: Phase C constants + pure functions (`classify_tier`, `epley_1rm`, `_estimate_from_profile`). Context: DESIGN.md + `utils/constants.py` + `utils/movement_patterns.py`.
4. **Slice-C2**: Phase C DB-touching code (`_lookup_last_logged`, `estimate_for_exercise`) + tests. Context: C1 output + `utils/database.py` + `workout_log` table schema (see `tests/conftest.py:274-278` for columns — **no `user_selection` JOIN needed**).
5. **Slice-D**: Phase D — blueprint + 4 endpoints + route tests. Context: `routes/progression_plan.py` (template), `utils/errors.py`, Slice-C output.
6. **Slice-E**: Phase E — template + JS module + nav icon + **new CSS bundle**. Context: `templates/workout_plan.html` (frame markup), `templates/base.html:152-195`, `static/js/modules/fetch-wrapper.js` (exports `apiFetch`/`api`, NOT `apiCall`), `.claude/rules/frontend.md`.
7. **Slice-F**: Phase F — workout-plan exercise-change hook. **Primary owner:** `static/js/modules/workout-plan.js` — it owns the active `handleExerciseSelection()` change handler AND the active `resetFormFields()` reached from `handleAddExercise()`. **Secondary / legacy context:** `static/js/modules/exercises.js` — `addExercise()` is imported by `app.js` but not invoked by the template button; only edit if a Playwright trace proves a legacy caller still reaches its `resetFormFields`. Slice-F must (a) add a shared `applyUserProfileEstimateForSelectedExercise()` helper in `workout-plan.js`, (b) call it from inside the existing `handleExerciseSelection()` (do NOT add a second listener), and (c) call it from the post-add `resetFormFields` path. Plus context: `/api/user_profile/estimate` endpoint shape from Slice-D. (Per codex 5.5, accepted by Opus 4.7 2026-04-26.)
8. **Slice-G**: Phase G — Playwright spec + verify suite. Context: existing `e2e/workout-plan.spec.ts` as a template.
9. **Slice-H**: Phase H — docs + CLAUDE.md edits + `frontend.md` update (8 route bundles). Context: this plan + `EXECUTION_LOG.md`.

> 🔍 **REVIEW (Opus 2026-04-26):** Updated slice contexts to reflect all review corrections: Slice-B now includes `erase-data` and `clean_db` scope; Slice-C2 drops the unnecessary `user_selection` JOIN reference; Slice-E adds CSS bundle creation and corrects `apiCall` → `apiFetch`; Slice-F adds the `resetFormFields` discrepancy context; Slice-H adds `frontend.md` update.

---

## Verification — how a human can confirm it works end-to-end

- [x] `python app.py` boots without error; check `logs/app.log` for the startup `add_user_profile_tables` line.
- [x] Visit `/user_profile` — fill demographics, save → toast "saved". Reload page — values persist.
- [x] Fill in 3–4 reference lifts (e.g. bench 100 kg × 5, squat 140 kg × 5, deadlift 180 kg × 5, bicep curl 35 kg × 8) and save.
- [x] Set preferences: complex=heavy, accessory=moderate, isolated=light. Save.
- [x] Visit `/workout_plan`, pick **EZ Bar Preacher Curl**: weight should be ≈ `epley(35, 8) × 0.40 × 0.65` ≈ 11 kg, sets=3, min_rep=10, max_rep=15, RIR=2, RPE≈7.5. Provenance caption: "from your profile". *(API returned 11.25 kg — verified via `/api/user_profile/estimate`.)*
- [x] Pick **Barbell Bench Press**: weight should be ≈ `epley(100, 5) × 1.00 × 0.85` ≈ 99 kg, min_rep=4, max_rep=6, RIR=1, RPE=9. Provenance: "from your profile". *(API returned 98.75 kg — verified via `/api/user_profile/estimate`.)*
- [x] Log a set against any exercise. Re-pick that exercise on Plan page → provenance now reads "from your last set". *(Verified via direct DB insert + estimate endpoint: returned source='log', reason='log'.)*
- [x] Pick a TRX or Bosu exercise → fields revert to hardcoded defaults; caption: "default values". *(TRX Pushup and Bosu Ball Curl both returned source='default', reason='default_excluded', weight=25, sets=3.)*
- [x] Run `/verify-suite` equivalent — full pytest + relevant Chromium E2E green. Update CLAUDE.md test counts.
- [x] Manually verify nothing on `/workout_plan`, `/workout_log`, `/weekly_summary`, `/session_summary`, `/progression`, `/volume_splitter`, `/backup` regressed — all returned HTTP 200. *(Visual click-through requires a browser; API-level smoke confirmed.)*
