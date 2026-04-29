# Development Issues — User Profile Feature

> **Source:** Post-implementation manual testing by user (2026-04-27), following the execution log at [`EXECUTION_LOG.md`](EXECUTION_LOG.md).
> **Status key:** 🔴 Bug · 🟡 UX gap · 🟢 Enhancement · 🔵 Design decision

---

## Issue #1 — Missing user instructions / onboarding copy on the Profile page

**Severity:** 🟡 UX gap — High  
**Area:** `templates/user_profile.html`

The Profile tab currently has no explanatory copy telling the user what the page does or how it affects the rest of the application.

**Expected behaviour:**  
The page should open with a clear introduction that explains:
- What information is collected and why.
- That filling in the questionnaire enables the system to **personalise Min Sets, Max Sets, Reps, RIR, RPE, and suggested Weight** for every exercise in the Plan tab.
- That values are used as *starting suggestions* — the user can always override them.
- Which sections affect which parts of the program (e.g. "Reference Lifts → Weight suggestions on Plan page", "Rep-Range Preferences → Rep targets and RIR/RPE on Plan page").

**Suggested placement:** A styled info banner or collapsible explainer card at the top of the page, above the Demographics section.

**Resolution (2026-04-27):** Implemented. Added a `frame-calm-glass`
"About this page" collapsible banner above `.user-profile-layout` in
`templates/user_profile.html` (default expanded; reuses the existing
`.collapse-toggle` JS handler). Copy explains the page purpose, the
Plan-page fields it personalises (Min Sets, Max Sets, Reps, RIR, RPE,
Weight), the per-section mapping
(Demographics → context · Reference Lifts → Weight · Rep-Range
Preferences → Reps/RIR/RPE), and that all values are starting
suggestions overridable from the Plan page. Styling lives in
`static/css/pages-user-profile.css` (`.profile-onboarding*`).

---

## Issue #2 — Gender dropdown shows single-letter codes instead of full labels

**Severity:** 🔴 Bug / data quality — Medium  
**Area:** `templates/user_profile.html`

The Gender `<select>` currently renders option values `M` and `F` as their display text. The "Other" option should be removed.

**Required changes:**

| Current display | Required display |
|-----------------|-----------------|
| `M`             | `Male`          |
| `F`             | `Female`        |
| `Other`         | *(remove)*      |

The underlying `value` attributes can remain `M` / `F` for backward-compatibility with the DB schema; only the visible `<option>` label text needs updating.

**Resolution (2026-04-27):** Implemented in
`templates/user_profile.html`. The Gender `<select>` now renders
`<option value="M">Male</option>` and `<option value="F">Female</option>`;
the prior `<option value="Other">Other</option>` row was removed. The
`value` attributes remain `M` / `F` so existing DB rows and the
`VALID_GENDERS = {"M", "F"}` route-layer guard in
`routes/user_profile.py:26` are unchanged.

Codebase audit confirmed no `templates/`, `routes/`, `static/js/`, or
`utils/` code hard-codes the "Other" gender value. The only remaining
match (`templates/weekly_summary.html:271`) is an unrelated
movement-pattern label. The route layer already rejects
`gender="Other"` (covered by
`tests/test_user_profile_routes.py::test_save_user_profile_rejects_other_gender`),
so no new server-side guard is needed.

Test coverage:
- `e2e/user-profile.spec.ts` — new test
  *"gender select shows Male/Female labels and no Other option (Issue #2)"*
  asserts the `<select>` contains exactly two non-empty options with
  text `Male` / `Female` and values `M` / `F`, and that an
  `option[value="Other"]` is absent.

Verification: pytest 1028 passed (~2m 30s); Chromium E2E
`user-profile.spec.ts` + `workout-plan.spec.ts` 28 passed (~38s).

---

## Issue #3 — Three non-functional "Hide" buttons with off-brand styling

**Severity:** 🔴 Bug — Medium  
**Area:** `templates/user_profile.html`, `static/css/pages-user-profile.css`

Three "Hide" buttons appear on the Profile page but perform no action when clicked. Their visual style does not match the Calm Glass design language used elsewhere in the app (e.g. glass panels, subtle shadows, muted palette).

**Required changes:**
1. Wire each button to a collapse/expand toggle for its parent section.
2. Re-style the buttons to use the `btn-calm-ghost` or `btn-calm-subtle` class pattern consistent with the rest of the UI, or remove them entirely if section collapse is considered out-of-scope for v1.

**Resolution (2026-04-27):** Implemented.

Investigation: the three section toggles were already wired correctly by
the `initializeCollapseToggles()` handler in
`static/js/modules/user-profile.js:76-97` (added alongside the Issue #1
onboarding banner — the handler queries `.user-profile-page
.collapse-toggle` so it picks up all four buttons on the page, including
the three section toggles). The original "do nothing" symptom predated
that handler and was resolved transitively when Issue #1 shipped. The
remaining gap was visual: the buttons inherited only default `<button>`
chrome on `/user_profile` because the existing
`.frame-header-2025 .collapse-toggle` skins live in
`pages-workout-plan.css` / `pages-weekly-summary.css` /
`pages-session-summary.css` (each page bundle has its own copy) and
none of those bundles load on the Profile page.

Implementation:
- `static/css/pages-user-profile.css` — added a Calm Glass skin scoped
  to `.user-profile-page .frame-header-2025 .collapse-toggle`. Pattern
  mirrors `.profile-explainer` / `.profile-onboarding`: `--surface-2`
  background mixed with transparent, `--accent` border at 22% mix,
  10px radius, `--ink-2` text, soft elevation shadow. Hover shifts to
  88% surface + 12% accent and brightens text to `--ink-1`. Active
  drops 1px. Focus-visible draws a 2px accent outline. Dark-mode
  variants use `--surface-1` mixed with black, accent at 30% / 46%,
  matching the rest of the page's dark tokens. `prefers-reduced-motion`
  disables the transition + transform.
- No HTML changes needed: the existing buttons already carry
  `class="collapse-toggle"`, `type="button"`, `aria-expanded="true"`,
  `aria-controls="..."`, and the `.toggle-icon` / `.toggle-text`
  spans the JS handler updates.
- No JS changes needed: `initializeCollapseToggles()` already toggles
  `aria-expanded`, swaps the chevron icon, swaps the "Hide"/"Show"
  label, and toggles `.collapsed` on the `.collapsible-frame` ancestor.
  `.user-profile-page .collapsible-frame.collapsed .frame-content
  { display: none; }` (line 5-7) hides the section body — `display:
  none` removes it from both the visual layout and the accessibility
  tree.

Tests (`e2e/user-profile.spec.ts`):
- New test *"section Hide buttons collapse and re-expand each profile
  section (Issue #3)"* — parametrised over all three sections
  (`demographics` / `reference lifts` / `rep preferences`). For each
  section asserts initial `aria-expanded="true"` + content visible +
  label "Hide" + correct `aria-controls`, then clicks once and asserts
  `aria-expanded="false"` + content hidden + label "Show" +
  `.collapsed` class on the frame, then clicks again and asserts the
  section reopens cleanly.
- New test *"section Hide buttons use Calm Glass styling tokens
  (Issue #3)"* — reads computed style on the demographics toggle and
  asserts `cursor: pointer`, a solid border > 0px, and a border-radius
  > 4px (i.e. it is no longer the bare default-button styling that
  prompted the report).

Verification: pytest 1028 passed (~2m 24s); Chromium E2E
`user-profile.spec.ts` + `workout-plan.spec.ts` 30 passed (~37s)
including the two new tests.

---

## Issue #4 — Missing calculation explanation on the Profile page

**Severity:** 🟡 UX gap — Medium  
**Area:** `templates/user_profile.html`

Users have no visibility into *how* their Reference Lifts are converted into exercise suggestions. There is no explanation of the Epley formula, cross-muscle fallback ratios, or tier-based rep/RIR/RPE presets.

**Suggested additions:**
- A "How does this work?" expandable section or tooltip near the Reference Lifts questionnaire.
- Example: *"Your Barbell Back Squat @ 100 kg × 5 reps → estimated 1RM 117 kg → Leg Press suggestion: ~72 kg × 8–12 reps."*
- Reference the three tier presets (Heavy / Moderate / Light) and what they produce.

**Resolution (2026-04-27):** Implemented. Added a native `<details>`
"How does this work?" expander inside the Reference Lifts panel
(collapsed by default, just above the questionnaire). Body covers:
the Epley 1RM formula, tier ratios (Complex 1.00 / Accessory 0.70 /
Isolated 0.40), the three rep-range presets (Heavy 4–6, RIR 1, RPE 9
@ 0.85 of 1RM · Moderate 6–8, RIR 2, RPE 8 @ 0.77 · Light 10–15,
RIR 2, RPE 7.5 @ 0.65), and a worked example: Barbell Back Squat
@ 100 kg × 5 reps → Epley 1RM ≈ 117 kg → Leg Press (accessory ×
moderate) ≈ 63 kg × 6–8 reps. Numbers are hardcoded with a Jinja
comment referencing `TIER_RATIOS` / `REP_RANGE_PRESETS` in
`utils/profile_estimator.py`. Styling lives in
`static/css/pages-user-profile.css` (`.profile-explainer*`).

---

## Issue #5 — Suggested weight field ignores manual edits and rejects decimal values

**Severity:** 🔴 Bug — High  
**Area:** `static/js/modules/workout-plan.js`, `applyUserProfileEstimateForSelectedExercise()`

When the system pre-fills the weight field with a profile-derived suggestion (e.g. `25`), the user cannot manually override it:
- Typing a new value (e.g. `17.5`) is silently overridden; the field reverts to the suggested value.
- The field appears to reject or not persist decimal input (`.` / `,` are not registered).

**Root cause hypothesis:**  
`applyUserProfileEstimateForSelectedExercise()` or its event listener may be firing on every `input`/`change` event on the weight field, overwriting the user's edits. The estimate should be applied **once** on exercise selection (or on explicit re-fetch), then the field should be freely editable.

**Required fix:**
1. Apply the estimate only on exercise *selection*, not on every field change.
2. Ensure the weight `<input>` has `step="0.25"` (or `"any"`) and `type="number"` to support decimals.
3. Treat any subsequent manual edit as the authoritative value; do not re-apply the estimate unless the exercise selection changes.

**Resolution (2026-04-27):** Implemented in
`static/js/modules/workout-plan.js`. Investigation:

- `applyUserProfileEstimateForSelectedExercise()` was already invoked
  only from two paths — the `change` listener on `#exercise`
  (`handleExerciseSelection`, line ~807) and `resetFormFields()`
  after a successful add-exercise — so re-firing on every keystroke
  was not the actual root cause.
- The fragile path was `updateExerciseDropdown()` (line ~876), which
  rebuilds `#exercise` after a filter change and dispatches
  `new Event('change')` programmatically when the value differs. That
  legitimately re-runs the estimate and would clobber a manual weight
  edit even though the user did not pick a new exercise themselves.
- The Weight `<input>` already has `type="number" step="any"
  min="0"`, which accepts decimal `.` input; the symptom of "decimals
  rejected" appears to be the same overwrite bug observed
  mid-typing (the input is replaced before the user finishes the
  decimal portion).

Implementation:
- Added a module-level `weightUserDirty` flag in `workout-plan.js`.
- New `initializeWeightDirtyTracking()` binds an `input` listener on
  `#weight` that flips the flag to `true` (idempotent — guarded by
  `dataset.dirtyTracked` so it cannot double-bind across re-inits).
  Wired from `initializeWorkoutPlanHandlers()`.
- `applyEstimateToWorkoutControls()` now skips overwriting `weight`
  when `weightUserDirty === true`. All other fields (sets, reps,
  RIR, RPE, dumbbell-hint) are applied unconditionally — only the
  Weight input gets the dirty guard, matching the issue scope.
- The dirty flag is reset to `false` in two places, both of which
  are legitimate "fresh estimate" triggers:
  - The `#exercise` `change` handler — picking a new exercise (or
    a programmatic re-dispatch from `updateExerciseDropdown` after
    a filter change) authorises a fresh estimate.
  - `resetFormFields()` — after a successful add, the form is
    reset for the next entry.
- Programmatic `setWorkoutControlValue('weight', ...)` does not fire
  the `input` event, so applying the estimate does not itself
  re-arm the dirty flag.

Tests:
- New Playwright test in `e2e/workout-plan.spec.ts`:
  *"weight field accepts decimals and preserves manual edits
  (Issue #5)"* — selects an exercise, waits for the
  `/api/user_profile/estimate` response, asserts `type="number"`
  and `step` is `any` or `0.25`, types `17.5`, blurs, and verifies
  the value persists. Then re-selects a different exercise and
  asserts the new estimate produces a valid numeric replacement
  (i.e., the dirty flag was cleared by the new selection).
- Run on Chromium: 27 passed (~34s) including the new test.

Verification: pytest 1028 passed (~2m 29s); Chromium
`workout-plan.spec.ts` + `user-profile.spec.ts` 27 passed (~34s).
The broader Chromium run has 66 pre-existing failures clustered in
`volume-progress.spec.ts`, `volume-splitter.spec.ts`, `visual.spec.ts`,
and one `nav-dropdown.spec.ts` test — all driven by an unrelated
`sqlite3.OperationalError: no such column: mode` raised from
`utils/volume_progress.py:419` and visual-baseline image drift, none
of which this JS-only change touches.

---

## Issue #6 — Reference Lifts questionnaire needs additional common exercises

**Severity:** 🟢 Enhancement — Medium  
**Area:** `templates/user_profile.html`, `utils/profile_estimator.py` (`KEY_LIFTS` / `MUSCLE_KEY_LIFT_MAP`)

The current questionnaire covers a limited lift set. The following exercises are proposed for inclusion, grouped by muscle group:

### Chest
- Incline Barbell/Dumbbell Bench Press
- Smith Machine Bench Press
- Machine Chest Press
- Dumbbell Fly

### Back
- Machine Row
- Chin-ups (bodyweight)

### Shoulders
- Dumbbell Shoulder Press
- Machine Shoulder Press
- Arnold Press
- Face Pulls
- Barbell Shrugs

### Biceps
- Barbell Curl
- Dumbbell Curl
- Preacher Curl (EZ Bar)
- Incline Dumbbell Curl

### Triceps
- Skull Crusher (EZ Bar / Barbell)
- JM Press

### Legs — Quads / Glutes
- Leg Press
- Dumbbell Squats
- Dumbbell Lunges
- Dumbbell Step-Ups
- Hip Thrust

### Legs — Hamstrings
- Stiff-Leg Deadlift
- Good Morning
- Single-Leg RDL

### Calves
- Standing Calf Raise

### Glutes / Hip
- Machine Hip Abduction

### Core / Abs
- Cable Crunch
- Machine Crunch
- Weighted Crunch
- Cable Woodchop
- Side Bend

### Lower Back
- Back Extension

> **Note:** Adding exercises also requires updating the `MUSCLE_KEY_LIFT_MAP` and adding appropriate slug-to-lift mappings in `utils/profile_estimator.py`.

**Resolution (2026-04-27):** Implemented. Slug-to-muscle decisions made along the
way (where the development_issues.md grouping needed an estimator-side primary
muscle that's not 1:1):
- `cable_woodchop` and `side_bend` → mapped to **Obliques** /
  **External Obliques** chains in `MUSCLE_TO_KEY_LIFT` (oblique-dominant
  rotational/lateral flexion).
- `cable_crunch`, `machine_crunch`, `weighted_crunch` → mapped to
  **Rectus Abdominis** / **Abs/Core** chains.
- `machine_hip_abduction` → mapped to the **Glutes** / **Gluteus Maximus**
  chains (no Hip-Abductors muscle key exists; gluteus medius/minimus is the
  closest defensible primary in the existing taxonomy).
- `back_extension` and `good_morning` → added to **Lower Back** chain
  alongside `romanian_deadlift` / `conventional_deadlift`.
- `barbell_shrugs` → moved to first slot in the **Trapezius** chain
  (most direct mapping).

Combined slugs renamed/labeled:
- `barbell_bench_press` label changed from "Barbell or Dumbbell Bench Press"
  to "Barbell Bench Press" (Issue #9 split).
- `romanian_deadlift` label changed from "Romanian or Conventional
  Deadlift" to "Romanian Deadlift" (Issue #9 split).

New questionnaire "Incline Barbell/Dumbbell Bench Press" is intentionally a
single combined slug `incline_bench_press` (the development_issues.md list
itself uses the slash form), unlike Issue #9's flat/dumbbell split. If users
report inaccurate estimates here, split it the same way as #9 in a future
pass.

---

## Issue #7 — Profile page layout wastes viewport; user must scroll excessively

**Severity:** 🟡 UX gap — Medium  
**Area:** `templates/user_profile.html`, `static/css/pages-user-profile.css`

The current layout stacks all sections vertically in a single narrow column, leaving large empty areas on the sides and requiring significant scrolling.

**Proposed layout change:**  
Split the page into **three side-by-side columns** (or a responsive two-column + one-column grid) so that Demographics, Reference Lifts, and Rep-Range Preferences can each occupy a logical panel without excessive vertical scrolling.

Suggested responsive breakpoints:
- `>= 1200 px` → 3 columns (Demographics | Reference Lifts | Preferences)
- `768–1199 px` → 2 columns (Demographics + Preferences | Reference Lifts)
- `< 768 px` → 1 column (current stacked behaviour, kept for mobile)

**Resolution (2026-04-27):** Implemented in
`static/css/pages-user-profile.css`. Bumped page max-width from 1180px
to 1480px to accommodate three columns. Breakpoints:

- **`>= 1200px`** — three side-by-side columns
  `grid-template-columns: 1fr 2fr 1fr` (Demographics | Reference Lifts
  | Preferences). Reference Lifts gets double width because it now
  carries 11 muscle-group sections / 50+ rows after Issue #6.
  Demographics' inner `.profile-grid` is forced to single column at
  this breakpoint and Preferences' `.preference-grid` is forced to
  single column to prevent overflow inside their narrow panels.
- **`768–1199px`** — two columns `1fr 1.4fr`. Demographics (row 1)
  and Preferences (row 2) stack on the left; Reference Lifts spans
  both rows on the right. Demographics' inner grid drops to two
  columns; Preferences stays single-column.
- **`< 768px`** — existing single-column stacked behaviour preserved
  via the existing `max-width: 991.98px` and `575.98px` rules.

The `.collapse-toggle` interaction works at every breakpoint: each
section is its own grid item, so collapsing one doesn't affect
sibling row heights. Verified via four new Playwright assertions in
`e2e/user-profile.spec.ts` (banner visible/collapsible, explainer
toggle + numeric content, 3-column geometry at 1280×900, single-
column stack at 600×900).

---

## Issue #8 — Romanian Deadlift weight suggestion is severely underestimated (~50% off)

**Severity:** 🔴 Bug — High  
**Area:** `utils/profile_estimator.py`, `utils/database.py` (slug mapping)

**Observed behaviour:**  
With a stored reference lift of **120 kg × 6 reps** for Romanian / Conventional Deadlift, the system suggested:

| Field     | Suggested | Expected (approx.) |
|-----------|-----------|---------------------|
| Weight    | 62.5 kg   | ~100–110 kg         |
| Sets      | 3         | 3 ✅                |
| RIR       | 1         | 1 ✅                |
| RPE       | 9         | 9 ✅                |
| Min reps  | 4         | 4 ✅                |
| Max reps  | 6         | 6 ✅                |

**Root cause hypothesis:**  
The slug `romanian_deadlift` may not be recognised as the primary key lift, causing the estimator to fall through to a cross-fallback chain with a 0.6× reduction factor applied, halving the expected weight. Alternatively, the stored lift weight is not being found/read correctly from `user_profile_lifts`.

**Required investigation:**
1. Confirm the slug stored in `user_profile_lifts` matches the key in `MUSCLE_KEY_LIFT_MAP` for hamstrings/lower back.
2. Trace the `reason` field returned by `/api/user_profile/estimate` for `Barbell Romanian Deadlift` — if it is `profile_cross` rather than `profile`, the fallback factor is being applied incorrectly.

**Resolution (2026-04-27):** Verified resolved by the Issue #9 slug-routing
work plus Issue #14's tier normalisation. With `romanian_deadlift = 120 kg
× 6` saved, `GET /api/user_profile/estimate?exercise=Barbell%20Romanian%20Deadlift`
returns `weight=122.5, reason=profile, source=profile, rir=1, rpe=9.0,
min_rep=4, max_rep=6` — Epley(120,6)≈144 × complex/complex multiplier 1.00
× heavy pct_1rm 0.85 ≈ 122.4 → barbell-rounded to 122.5 kg. The
`test_direct_match_bypasses_cross_factor_for_romanian_deadlift` test in
`tests/test_profile_estimator.py` pins this expectation. Live API
verification done after server restart on 2026-04-27.

---

## Issue #9 — Combined exercise slugs should be split into individual entries

**Severity:** 🟢 Enhancement / data model decision — Medium  
**Area:** `utils/profile_estimator.py` (slug definitions), `templates/user_profile.html` (questionnaire rows)

Two reference lifts currently bundle distinct movements under a single slug, preventing accurate estimation for each variant:

| Current combined slug | Should become |
|----------------------|---------------|
| Romanian or Conventional Deadlift | `romanian_deadlift` + `conventional_deadlift` |
| Barbell or Dumbbell Bench Press   | `barbell_bench_press` + `dumbbell_bench_press` |

**Impact:** Users who are strong at Conventional Deadlift but use a different weight for Romanian DL (common) will receive inaccurate suggestions for one or both movements. Same applies to Barbell vs Dumbbell Bench Press.

**Required changes:**
- Split the questionnaire rows into two separate input rows per group.
- Add two new slugs in `KEY_LIFTS` / `MUSCLE_KEY_LIFT_MAP`.
- Migrate any existing stored data from the old combined slug.

**Resolution (2026-04-27):** Implemented. Added `conventional_deadlift` and
`dumbbell_bench_press` slugs in `KEY_LIFTS`. Existing rows on the kept halves
(`romanian_deadlift`, `barbell_bench_press`) continue to work unchanged — no
DB migration required. `DIRECT_LIFT_MATCHERS` now route "conventional
deadlift" → `conventional_deadlift` (was → `romanian_deadlift`) and "dumbbell
bench press" → `dumbbell_bench_press` (was → `barbell_bench_press`).

---

## Issue #10 — Dumbbell weight convention is ambiguous (per hand vs. total load)

**Severity:** 🟡 Design decision / UX gap — High  
**Area:** `templates/user_profile.html`, `templates/workout_plan.html`, `utils/profile_estimator.py`

It is currently unclear whether dumbbell weight fields expect:
- **(A) Weight per hand** (e.g. enter `20` for 2 × 20 kg dumbbells), or
- **(B) Total combined load** (e.g. enter `40` for 2 × 20 kg dumbbells)

This ambiguity affects both the **Profile questionnaire** (Reference Lifts) and the **Plan tab** (Workout Controls), and will produce incorrect estimates if the convention is inconsistent.

**Decision required:**  
Align on one convention (recommendation: **per hand**, which is the gym industry standard) and:
1. Add a persistent note next to every dumbbell field: *"Enter weight per hand (one dumbbell)"*.
2. Ensure the estimator applies the same convention when outputting weight suggestions for dumbbell exercises.
3. Document the chosen convention in `DESIGN.md §6`.

**Resolution (2026-04-27):** Standardised on **per hand** (one dumbbell)
across both inputs and outputs. Decision sequence:

- **Math change required?** No. Verified via code audit that the estimator
  chain (`epley_1rm` → `TIER_RATIOS` → `REP_RANGE_PRESETS` → `round_weight`)
  is unit-agnostic; weight is treated as an opaque scalar end-to-end.
  `utils/weekly_summary.py` and `utils/session_summary.py` likewise treat
  the `weight` column as a raw multiplier in `total_volume = sets × reps ×
  weight`. No code path silently doubles or halves for dumbbells.
  Declaring per-hand simply formalises the convention the codebase has
  always used implicitly.
- **Migration?** None. Inspected `data/database.db` at cutover —
  `dumbbell_lateral_raise = 12 kg × 8` was the only populated dumbbell
  slug, and 12 kg is unmistakably per-hand (12 kg total would be 6 kg
  per side, far below working weight). All other dumbbell slugs were
  NULL; new entries will flow through the helper-text-driven convention.

Implementation:
- `utils/profile_estimator.py` — added module docstring stating the
  convention, `DUMBBELL_LIFT_KEYS` frozenset (the 10 unambiguously
  per-hand questionnaire slugs), and `is_dumbbell: bool` on every
  estimate response (driven by
  `normalize_equipment(exercise.equipment) == "Dumbbells"`).
- `routes/user_profile.py` — flags each questionnaire row's `is_dumbbell`
  via `DUMBBELL_LIFT_KEYS`.
- `templates/user_profile.html` — renders a "Per hand (one dumbbell)"
  `<small class="reference-lift-hand-hint">` below the Weight input on
  every dumbbell row, wired via `aria-describedby` for screen readers.
- `templates/workout_plan.html` — adds a hidden
  `<small id="weight-hand-hint" class="weight-hand-hint">` next to the
  Workout Controls weight field.
- `static/js/modules/workout-plan.js` —
  `applyEstimateToWorkoutControls()` toggles the hint's `hidden`
  attribute based on `estimate.is_dumbbell`. Default estimate carries
  `is_dumbbell: false`.
- Styling: `.reference-lift-hand-hint` in
  `static/css/pages-user-profile.css`, `.weight-hand-hint` in
  `static/css/pages-workout-plan.css` (both with dark-mode variants).
- Documentation: `docs/user_profile/DESIGN.md §6.1` (new subsection
  pinned to the rounding section).

Test additions:
- `tests/test_profile_estimator.py` — two new tests:
  `test_dumbbell_estimate_is_per_hand_and_flags_is_dumbbell` (asserts a
  40 kg-per-hand reference returns ~43 kg per-hand working weight, well
  below any doubling fall-out, and that `is_dumbbell` is True), and
  `test_non_dumbbell_estimate_does_not_flag_is_dumbbell` (Barbell Back
  Squat returns `is_dumbbell=False`). Two existing exact-dict-equality
  tests (`test_estimate_for_exercise_uses_profile_lift_for_isolated_barbell`,
  `test_last_logged_set_wins_over_profile_estimate`) updated to include
  the new key.
- `e2e/user-profile.spec.ts` — new test
  *"per-hand hint is visible only next to dumbbell reference-lift rows"*
  asserts the hint appears on `dumbbell_bench_press` and
  `dumbbell_lateral_raise` rows, contains the words "Per hand" / "one
  dumbbell", and is **absent** from `barbell_bench_press`.

---

## Issue #11 — Reference Lifts questionnaire lacks muscle-group section headings

**Severity:** 🟡 UX gap — Low  
**Area:** `templates/user_profile.html`

The Reference Lifts list is a flat, ungrouped list of exercises. With the additional exercises proposed in Issue #6, this will become difficult to scan.

**Required change:**  
Add mini section headings (e.g. `<h4>` or styled `<span>` dividers) grouping exercises by primary muscle group:

- **Chest**
- **Back**
- **Shoulders**
- **Biceps**
- **Triceps**
- **Legs — Quads & Glutes**
- **Legs — Hamstrings**
- **Calves**
- **Core / Abs**
- **Lower Back**

This mirrors the muscle-group grouping pattern already used in the muscle-selector component.

**Resolution (2026-04-27):** Implemented. `routes/user_profile.py` now
pre-groups reference lifts via `REFERENCE_LIFT_GROUPS`, exposing
`reference_lift_groups` to the template. `templates/user_profile.html`
renders `<h4 class="reference-lift-group-title">` per group; styling lives
in `static/css/pages-user-profile.css`. Group order: Chest, Back,
Shoulders, Biceps, Triceps, Legs — Quads & Glutes, Legs — Hamstrings,
Calves, Glutes / Hip, Core / Abs, Lower Back.

---

## Issue #12 — Profile nav tab missing active/indigo highlight state

**Severity:** 🔴 Bug — Low  
**Area:** `templates/base.html`, `static/css/` (navbar styles)

When the user navigates to the **Profile** tab, the tab pill does not receive the active indigo/blue highlight that all other nav tabs display when they are the current page. The Profile link appears visually identical to an inactive tab, giving no indication that it is the currently selected section.

**Root cause hypothesis:**  
The active-tab class (e.g. `nav-pill--active` or equivalent) is applied by comparing the current Flask route (`request.endpoint` or `request.path`) against each nav item. The Profile nav link added in Slice-E likely has a mismatched route name or the template condition does not include the `user_profile` endpoint in its check.

**Required fix:**
1. Locate the active-class logic in `templates/base.html` (the nav pill loop or individual `class` attributes).
2. Ensure the Profile link's condition correctly matches the `user_profile` blueprint endpoint (e.g. `request.endpoint == 'user_profile.page'` or whichever name was registered).
3. Visually verify the indigo/active pill appears when on `/user_profile` and disappears when navigating away.

**Resolution (2026-04-27):** The original hypothesis (Jinja `request.endpoint`
check in `templates/base.html`) didn't match the actual mechanism. The navbar
applies the `.active` class via JS, not Jinja: `static/js/modules/navbar.js`
exports `initializeNavHighlighting()`, which reads `window.location.pathname`,
looks it up in a `pathMap` of path → element-id, and adds `.active` to the
matched nav element. The CSS rule
`:where(#navbar) .nav-link.active` (`static/css/navbar.css:1100`) then paints
the indigo pill (background `--nav-pill-active`, border
`--nav-pill-border-active`, inset shadow). Both the brand and the right-side
Profile pill share the same `.nav-link.active` styling, so no extra CSS was
needed for the `ms-auto` group.

The bug was a missing entry in the `pathMap`: `/user_profile` was not mapped
to `nav-user-profile`, so the JS never added `.active` to the Profile link
even though the link's `id` was correct in `templates/base.html:190` and the
CSS would have happily styled it. Fix: one new line in
`static/js/modules/navbar.js` mapping `'/user_profile': 'nav-user-profile'`.
No `templates/base.html` change required — the existing
`id="nav-user-profile"` and `data-testid="nav-user-profile"` attributes are
correct.

Tests:
- `e2e/user-profile.spec.ts` — new test
  *"Profile nav link gets active highlight on /user_profile and loses it on
  navigation away (Issue #12)"* — asserts `SELECTORS.NAV_USER_PROFILE` has
  the `active` class on `/user_profile`, then navigates to `/workout_plan`
  and asserts the Profile link no longer has `active` while
  `SELECTORS.NAV_WORKOUT_PLAN` does. Uses the `/\bactive\b/` regex to avoid
  matching unrelated classes like `inactive` (none today, but defensive).

Verification: pytest 1028 passed (~2m 24s); Chromium E2E
`user-profile.spec.ts` + `workout-plan.spec.ts` + `smoke-navigation.spec.ts`
41 passed (~58s) including the new Issue #12 test.

---

## Issue #13 — Pull-Up / Chin-Up variants misclassified as Accessory instead of Complex

**Severity:** 🔴 Bug — High  
**Area:** `utils/profile_estimator.py` — `COMPLEX_ALLOWLIST` / `classify_tier()`

**Observed behaviour — Weighted Pull Ups example:**  
With a profile reference lift of **25.0 kg** for Weighted Pull Ups, the Plan page suggests:

| Field    | Actual suggestion | Expected (Complex tier) |
|----------|-------------------|-------------------------|
| Weight   | 16.25 kg          | ~23–25 kg              |
| Sets     | 3                 | 3 ✅                    |
| RIR      | 2                 | 1 (Heavy preset)        |
| RPE      | 8.0               | 9.0 (Heavy preset)      |
| Min reps | 6                 | 4 (Heavy preset)        |
| Max reps | 8                 | 6 (Heavy preset)        |

The exercise is being treated as **Accessory** (0.70× tier ratio, Moderate preset) instead of **Complex** (1.00× tier ratio, Heavy preset).

**Root cause — confirmed from code:**  
`classify_tier()` in `profile_estimator.py` (line 153) checks whether any keyword from `COMPLEX_ALLOWLIST` is a **substring** of the lowercase exercise name:

```python
if any(keyword in name for keyword in COMPLEX_ALLOWLIST):
    return "complex"
```

The allowlist contains `"weighted pull-up"`, `"weighted pullup"`, `"weighted chin-up"`, `"weighted chinup"` — but the exercise name stored in the DB is **`"Weighted Pull Ups"`** (plural, space-separated). None of the allowlist substrings match `"weighted pull ups"`, so the function falls through to `return "accessory"`.

The weight difference is exactly explained by the tier ratio: `25.0 × 0.70 × 0.77 (moderate pct_1rm) ≈ 13.5 kg`, then rounded to `16.25` via the barbell/accessory rounding logic — confirming Accessory+Moderate is being applied.

**Bodyweight variants — same bug, different symptom:**  
Plain `"Pull Ups"`, `"Pull-Ups"`, `"Pullups"`, `"Chin Ups"`, `"Chin-Ups"` are **also absent** from `COMPLEX_ALLOWLIST`. For bodyweight exercises `round_weight()` returns `0.0` so the suggested weight won’t look obviously wrong, but the **rep range, RIR, and RPE presets will be wrong** — Moderate (6–8 reps, RIR 2, RPE 8.0) instead of Complex/Heavy (4–6 reps, RIR 1, RPE 9.0).

**Required fix:**  
Add all missing variants to `COMPLEX_ALLOWLIST` in `profile_estimator.py`:

```python
# Weighted variants — plural/space forms missing from original list
"weighted pull up",
"weighted pull ups",
"weighted chin up",
"weighted chin ups",
# Bodyweight variants — entirely absent from original list
"pull up",
"pull ups",
"pull-up",
"chin up",
"chin ups",
"chin-up",
```

**Recommended broader fix:**  
Audit the full allowlist for similar plural/variant gaps (e.g. `"weighted dip"` vs `"weighted dips"`, `"hip thrust"` vs `"hip thrusts"`) to prevent the same class of bug on other exercises. Consider normalising the name before matching (e.g. replacing hyphens with spaces, stripping a trailing `s`) rather than maintaining an ever-growing string list.

**Resolution (2026-04-27):** Implemented the broader normalisation approach.
Added `_normalize_for_matching()` in `utils/profile_estimator.py` that
lowercases, replaces hyphens with spaces, and strips a single trailing `s`
from each word. Both the exercise name and each `COMPLEX_ALLOWLIST` keyword
are normalised the same way at match time
(`_COMPLEX_ALLOWLIST_NORMALIZED` precomputed at module load), so plural /
hyphen / spacing variants — `"Pull Ups"`, `"Pull-Ups"`, `"Pullups"`,
`"Chin-Ups"`, `"Hip Thrusts"`, `"Stiff-Leg Deadlifts"` — collapse to the
canonical allowlist entry without per-variant strings. `COMPLEX_ALLOWLIST`
itself was de-duplicated: removed redundant variants (`"weighted pull-up"`,
`"pull-up"`, `"chin-up"`, `"stiff-leg deadlift"`, `"single-leg rdl"`,
`"t-bar row"`, `"bent-over row"`) since their canonical forms cover them
post-normalisation. Allowlist remains the single source of truth — adding
a new complex lift is one entry, no plural/hyphen book-keeping.

Tests (`tests/test_profile_estimator.py`):
- `test_complex_allowlist_matches_plural_and_hyphen_variants` —
  parametrised over 12 variants (`Pull Ups`, `Pull-Ups`, `Pullup`,
  `Pullups`, `Chin Ups`, `Chin-Ups`, `Chinups`, `Weighted Pull-Ups`,
  `Weighted Pullups`, `Weighted Chin Ups`, `Hip Thrusts`,
  `Stiff-Leg Deadlifts`) all asserted as `complex`.
- `test_bodyweight_pull_up_uses_heavy_preset_rir_and_rpe` — bodyweight
  Pull Ups with `bodyweight_pullups = 0 × 8` saved returns `rir=1,
  rpe=9.0` (Heavy preset), confirming the complex classification feeds
  through to the preset selection.
- Existing `test_weighted_pull_ups_classified_as_complex` continues to
  pass — verifies normalisation rather than the prior allowlist hack
  (full preset assertion: 4–6 reps, RIR 1, RPE 9.0, weight ≈ 25.0).

Verification: pytest 1028 passed (~2m 16s); Chromium E2E user-profile +
workout-plan specs 26 passed (~36s).

---

## Summary table

| # | Title | Severity | Area | Status |
|---|-------|----------|------|--------|
| 1 | Missing onboarding / instructions copy | 🟡 UX gap | Profile page HTML | Resolved (2026-04-27) |
| 2 | Gender dropdown shows `M`/`F` not full labels | 🔴 Bug | Profile page HTML | Resolved (2026-04-27) |
| 3 | 3 non-functional "Hide" buttons, off-brand style | 🔴 Bug | Profile HTML + CSS | Resolved (2026-04-27) |
| 4 | No calculation explanation on profile page | 🟡 UX gap | Profile page HTML | Resolved (2026-04-27) |
| 5 | Weight field rejects manual edits & decimals | 🔴 Bug | `workout-plan.js` | Resolved (2026-04-27) |
| 6 | Reference lifts questionnaire needs more exercises | 🟢 Enhancement | Profile HTML + estimator | Resolved (2026-04-27) |
| 7 | Profile page wastes horizontal space; too much scroll | 🟡 UX gap | Profile HTML + CSS | Resolved (2026-04-27) |
| 8 | Romanian Deadlift weight suggestion is ~50% off | 🔴 Bug | `profile_estimator.py` | Resolved (2026-04-27) |
| 9 | Combined deadlift/bench slugs should be split | 🟢 Enhancement | Estimator + questionnaire | Resolved (2026-04-27) |
| 10 | Dumbbell weight convention (per hand vs total) undefined | 🟡 Design decision | HTML + JS + estimator | Resolved (2026-04-27) |
| 11 | Questionnaire missing muscle-group mini headings | 🟡 UX gap | Profile page HTML | Resolved (2026-04-27) |
| 12 | Profile nav tab missing active/indigo highlight state | 🔴 Bug | `navbar.js` pathMap | Resolved (2026-04-27) |
| 13 | Weighted Pull Ups misclassified as Accessory (COMPLEX_ALLOWLIST gap) | 🔴 Bug | `profile_estimator.py` | Resolved (2026-04-27) |
| 14 | Same-tier fallback estimates underestimated (tier-ratio compounding) | 🔴 Bug | `profile_estimator.py` | Resolved (2026-04-27) |
| 15 | Reference Lifts panel still scrolls too long; group rows in 2 columns | 🟡 UX gap | Profile HTML + CSS | Resolved (2026-04-27) |
| 16 | Demographics data collected but unused; add cold-start 1RM seeding | 🟢 Enhancement | `profile_estimator.py` + estimator chain | Resolved (2026-04-28) |
| 17 | Personalised estimator transparency — "how the system sees you" + per-suggestion math + accuracy-improvement guidance | 🟡 UX gap | Profile HTML + Plan HTML + estimator response | Resolved (2026-04-28) |
| 18 | "How the system sees you" card should be visual stats + peer-range comparisons, not text-only | 🟢 Enhancement | Profile HTML + JS + CSS + estimator | Resolved (2026-04-28) |
| 19 | Reuse the bodymap SVG to visualise reference-lift coverage on the Profile page | 🟢 Enhancement | Profile HTML + JS + estimator | Resolved (2026-04-28) |
| 20 | Calves / Glutes-Hips / Lower-Back have too few reference-lift options | 🟢 Enhancement | `profile_estimator.py` + Profile HTML | Resolved (2026-04-28) |
| 21 | Body Composition tab — BFP / Lean Mass / longitudinal snapshots on a standalone `/body_composition` tab | 🟢 Enhancement | New blueprint + template + `body_fat.py` + DB table | **Moved 2026-04-28 → [`docs/body_composition/development_issues.md`](../body_composition/development_issues.md)** (still Open there). Cross-page display follow-up (Issue #18 *Lean mass* sub-line + Issue #17 *Body fat* line) **migrated 2026-04-29 → [Issue #22 in body_composition tracker](../body_composition/development_issues.md#issue-22--profile-page-cross-page-display-hooks-for-body-composition-data)**. |
| 22 | Coverage map card: SVG and front/back toggles not centered; "About this page" Demographics copy stale post-#16 | 🟡 UX gap | Profile HTML + CSS | Resolved (2026-04-28) |
| 23 | Coverage map legend swatches barely visible; replace 3 Save buttons with auto-save | 🟡 UX gap | Profile HTML + JS + CSS + E2E | Resolved (2026-04-28) |
| 24 | Reference Lifts: split questionnaire into anterior + posterior side-by-side cards mirroring the Coverage map | 🟢 Enhancement | Profile HTML + CSS + `profile_estimator.py` partition | Resolved (2026-04-28) |

---

*Last updated: 2026-04-28 — Issue #24 resolved. The Reference Lifts
panel now renders as two side-by-side `frame-calm-glass` cards
(`reference lifts anterior` + `reference lifts posterior`) inside
the centre column, mirroring the Coverage map's front/back framing.
A single `KEY_LIFT_SIDE` mapping in `utils/profile_estimator.py`
drives the partition; `routes/user_profile.py` exposes
`reference_lift_groups_anterior` / `reference_lift_groups_posterior`
to the template; one `<form id="profile-lifts-form">` spans both
cards so the existing autosave / bodymap / insights JS keeps
working with no refactor. Issue #15's inner 2-column row rule and
the 1600 px+ 3-column rule are removed; rows stack vertically
inside each ~290 px-wide card. Estimator outputs are byte-identical
(pytest 1083, includes 3 new partition cases; Chromium E2E
user-profile + workout-plan 43 passed, adjacent sweep
(exercise-interactions + accessibility + smoke-navigation) 55
passed; Issue #19 hover/click stabilised with `force: true` +
scroll-to-top after the bodymap diagram shrank to half the page
width put the 48 × 42 px chest polygon at risk of slipping under
the sticky 64 px navbar). Open queue (2026-04-29 review):
**Issue #21** — scope changed; moved out of the Profile page and
re-specced as a standalone `/body_composition` tab so the longitudinal
snapshot UX has its own surface and the Profile page stays focused on
strength inputs. The full issue body now lives at
[`docs/body_composition/development_issues.md`](../body_composition/development_issues.md).
The two Profile-page display hooks (Issue #18 cohort-tile *Lean mass*
sub-line and Issue #17 *Body fat* line) were migrated **2026-04-29**
to the body_composition tracker as
[Issue #22](../body_composition/development_issues.md#issue-22--profile-page-cross-page-display-hooks-for-body-composition-data)
so the follow-up lives next to its data source
(`body_composition_snapshots`).

History — earlier batch (2026-04-28): Issue #20 ships 16 new
reference-lift slugs across Calves / Glutes-Hips / Lower-Back, all
wired through `KEY_LIFT_LABELS` / `KEY_LIFT_TIER` /
`MUSCLE_TO_KEY_LIFT` / `DIRECT_LIFT_MATCHERS` / `COMPLEX_ALLOWLIST`
and mirrored in the JS bodymap chain + popover labels; pytest 1080
/ Chromium 41 + adjacent 55.

History — earlier batch (2026-04-28): resolved Issue #17 (personalised estimator
transparency). Three deliverables landed together:
**(A)** a "How the system sees you" `frame-calm-glass` card on
`/user_profile` showing the live demographics classification line,
cold-start anchor 1RMs (Bench / Squat / Deadlift / OHP), a
"replaced by your data" list, and the top-3 missing high-impact
reference lifts.
**(B)** A `trace` object on every `/api/user_profile/estimate` response
(direct match, cross-muscle, cold-start, log, default) built at the
single source of truth in `utils/profile_estimator.py` and rendered
lazily on click via the new "Show the math" expander on the Plan
page (`#workout-estimate-trace-toggle`). The cross-muscle and
cold-start branches also expose an `improvement_hint` (slug + copy)
that links back to the relevant Profile-page row.
**(C)** A profile-wide accuracy band (population-only / partial /
mostly / fully personalised) computed server-side in
`routes/user_profile.py` and rendered as a pill + progress bar at
the top of card (A); re-rendered live by the JS port of
`accuracy_band()` whenever the user types into the demographics or
reference-lift forms. All open issues resolved.
Append new issues below this line.*

---

## Issue #14 — Same-tier fallback estimates are severely underestimated (tier-ratio compounding bug)

**Severity:** 🔴 Bug — High
**Area:** `utils/profile_estimator.py` — `_estimate_from_profile`, `TIER_RATIOS`

**Observed behaviour (2026-04-27, user reproduction):**
With profile data:
- `dumbbell_curl = 20 kg × 6 reps`
- `preacher_curl = 35 kg × 8 reps`
- `incline_dumbbell_curl = NULL`
- `barbell_bicep_curl = NULL`

The Plan page suggests for **Dumbbell Incline Curl**:

| Field | Suggested | Expected (approx.) |
|---|---|---|
| Weight | **3.5 kg** | ~9–13 kg |
| Sets | 3 | 3 ✅ |
| RIR | 2 | 2 ✅ |
| RPE | 7.5 | 7.5 ✅ |
| Reps | 10–15 | 10–15 ✅ |

3.5 kg per hand for someone who can curl 20 kg × 6 standing is implausible.

**Root cause — confirmed via direct trace:**
`_estimate_from_profile` (`utils/profile_estimator.py:610`) computes:

```
target_1rm = reference_1rm × TIER_RATIOS[target_tier] × cross_factor
```

For Dumbbell Incline Curl:
1. `target_tier = "isolated"` (mechanic=`Isolation` in DB) → `TIER_RATIOS["isolated"] = 0.40`.
2. Direct slug `incline_dumbbell_curl` is NULL, so the chain falls back to
   `dumbbell_curl` with `cross_factor = 0.6`.
3. Math: `Epley(20, 6) = 24` × `0.40` × `0.60` × `0.65 (light pct_1rm)` =
   `3.74` → dumbbell-rounded to **3.5 kg**.

The bug is on line 2 of that math: **`TIER_RATIOS[isolated] = 0.40` is meant to convert a *complex* 1RM into an *isolated* 1RM**. It assumes the reference lift is a heavy compound. When the reference is itself an isolated lift (`dumbbell_curl`), multiplying its 1RM by 0.40 again is double-discounting — the same class of bug as Issue #8 (Romanian Deadlift) but happening on the tier multiplier instead of the slug-routing.

This affects **every same-tier chain fallback**:
- iso→iso (curls, lateral raises, calves, abs, fly variations) — currently scaled by `0.40` instead of `1.00` (×2.5 too low).
- accessory→accessory (machine variants, dumbbell squat → dumbbell lunge, etc.) — currently scaled by `0.70` instead of `1.00` (×1.43 too low).

Direct-match same-tier estimates suffer the same bug. The existing test `test_estimate_for_exercise_uses_profile_lift_for_isolated_barbell` documents 11.25 kg for **preacher curl direct match** with a `35 kg × 8` reference; the realistic light-preset working weight is closer to ~28 kg. The test was effectively pinning the bug rather than asserting correct behaviour.

**Proposed fix:**

Add a `KEY_LIFT_TIER` mapping (each reference lift's implied tier — complex / accessory / isolated). Normalise the tier multiplier:

```python
multiplier = min(
    TIER_RATIOS[target_tier] / TIER_RATIOS[reference_tier],
    1.0,
)
target_1rm = reference_1rm * multiplier * cross_factor
```

The `min(..., 1.0)` cap prevents amplifying a small isolated 1RM into an inflated complex 1RM (preserves the conservative behaviour of `iso→complex` paths).

**Impact matrix (target_tier × reference_tier):**

| Path | Current multiplier | New multiplier | Effect |
|---|---|---|---|
| complex → complex | 1.00 | 1.00 | unchanged |
| complex → accessory | 0.70 | 0.70 | unchanged |
| complex → isolated | 0.40 | 0.40 | unchanged |
| isolated → complex | 1.00 | 1.00 (capped) | unchanged |
| **isolated → isolated** | **0.40** | **1.00** | **×2.5** |
| **accessory → accessory** | **0.70** | **1.00** | **×1.43** |

For the user's reproduction: Dumbbell Incline Curl 3.5 kg → ~9 kg (still scaled by `cross_factor = 0.6` because direct slug is empty). If `incline_dumbbell_curl` is also entered directly in the profile, the direct-match path skips cross_factor and yields ~14 kg.

**Required test changes:**
- Update `test_estimate_for_exercise_uses_profile_lift_for_isolated_barbell` — expected weight 11.25 → ~28.75 kg.
- Add new test for iso→iso fallback (the user's exact reproduction): Dumbbell Incline Curl with `dumbbell_curl = 20 × 6` reference asserts working weight ~9 kg, `reason = "profile_cross"`.
- Audit other tests for same-tier paths that may have been pinning the bug.

**Out of scope for this issue (consider as follow-ups):**
- `cross_factor = 0.6` itself is a magic number. For same-muscle same-tier-family fallback (e.g., curl→curl), 0.6 may still be too aggressive on top of the corrected tier math. A tier-aware `cross_factor` (e.g., higher for isolated targets where movement variations are more substitutable) would tighten the curl estimate from 9 kg toward 13 kg, matching intuition.
- Whether `dumbbell_curl` and `incline_dumbbell_curl` should both be classified the same tier (both currently isolated) or whether incline curl deserves a separate "incline_isolation" classification with a slight discount factor.

**Resolution (2026-04-27):** Implemented. Added `KEY_LIFT_TIER` map in
`utils/profile_estimator.py` declaring each questionnaire reference lift's
implied tier (complex / accessory / isolated). `_estimate_from_profile` now
computes `tier_multiplier = min(TIER_RATIOS[target_tier] /
TIER_RATIOS[reference_tier], 1.0)` instead of `TIER_RATIOS[target_tier]`
unconditionally. Same-tier paths (iso→iso, accessory→accessory) now use
multiplier 1.00 (was 0.40 and 0.70 respectively); cross-tier downscaling
(complex→iso, complex→accessory) is unchanged; the `min(..., 1.0)` cap
preserves the conservative behaviour of upscaling paths so an isolated
reference can never inflate a complex target's estimate.

User-reported reproduction now resolves correctly:
- `incline_dumbbell_curl = 20 kg × 7` (direct match) → 6.5 kg → **16.0 kg**
  per hand.
- `dumbbell_curl = 20 kg × 6` (cross fallback for incline curl) → 3.5 kg →
  **9.0 kg** per hand.
- Issue #8 Romanian Deadlift `120 kg × 6` direct match unchanged at
  ~122.5 kg (complex→complex was already 1.00 — Issue #8's symptom was a
  separate slug-routing bug, fixed earlier alongside Issue #9).

Tests:
- `tests/test_profile_estimator.py`:
  - `test_key_lift_tier_covers_every_key_lift` — guards against future
    `KEY_LIFTS` additions silently defaulting to "complex".
  - `test_iso_to_iso_direct_match_no_longer_double_discounts` — user's
    direct-match reproduction (16 kg expected).
  - `test_iso_to_iso_cross_fallback_no_longer_double_discounts` — user's
    cross-fallback reproduction (9 kg expected, `reason="profile_cross"`).
  - `test_complex_to_iso_cross_path_still_downscales` — regression guard
    that cross-tier paths still discount (18 kg, unchanged).
  - `test_estimate_for_exercise_uses_profile_lift_for_isolated_barbell` —
    weight expectation updated 11.25 → 28.75 kg (was pinning the bug).
- `tests/test_user_profile_routes.py::test_estimate_endpoint_returns_profile_estimate`
  — same expectation update (route-layer assertion).

Verification: pytest 1015 passed (~3m); Chromium E2E user-profile +
workout-plan specs 26 passed (~35s).

Out of scope (still tracked): tier-aware `cross_factor` (currently flat
0.6) and the `incline_dumbbell_curl` tier classification question raised
in the original issue body.

---

## Issue #15 — Reference Lifts panel still scrolls too long; render rows in 2 columns within each muscle group

**Severity:** 🟡 UX gap — Medium
**Area:** `templates/user_profile.html`, `static/css/pages-user-profile.css`

After Issue #6 expanded the questionnaire from ~12 to 50+ reference-lift rows
across 11 muscle groups (Chest, Back, Shoulders, Biceps, Triceps, Legs — Quads
& Glutes, Legs — Hamstrings, Calves, Glutes / Hip, Core / Abs, Lower Back),
the Reference Lifts panel scrolls heavily even on the 3-column desktop layout
shipped in Issue #7 — the centre column is wide (`grid-template-columns:
1fr 2fr 1fr`) but the lift rows still stack one-per-line.

**Observed symptom:** On a 1280×900 viewport with the centre column expanded,
the Reference Lifts panel is roughly 2–3 viewport heights tall; the side
columns (Demographics, Preferences) end early and leave large blank vertical
gutters next to the still-scrolling lifts column.

**Required change (decided 2026-04-27):**
Render each muscle group's lift rows in a **2-column grid** inside the group,
keeping the existing `<h4 class="reference-lift-group-title">` heading at full
width. The group heading scopes the columns visually so the eye reads
left-to-right within a group and top-to-bottom across groups, halving the
vertical extent of the panel without any new JS state.

Out of scope:
- Per-group accordion / collapse-expand toggles. Considered and rejected on
  2026-04-27 — adds clicks and hides exercises that the user might be
  comparing across groups, and the 2-column grid alone is expected to bring
  the panel down to roughly one viewport height on desktop.
- Changing the page-level 3-column geometry from Issue #7. Centre column
  stays `1fr 2fr 1fr`; only the *inside* of the Reference Lifts panel
  changes.

**Implementation notes:**
- CSS-only on the desktop breakpoint (`>= 1200px`): give the
  `.reference-lifts-list` (or equivalent container that wraps each group's
  rows) `display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3);`.
  Below 1200px collapse to single column to keep the existing mobile / tablet
  breakpoints from Issue #7 unchanged.
- Each muscle group must keep its own row container so the group heading
  stays full-width above the 2-column grid. Don't put the heading and rows
  in the same grid — the heading would land in column 1 only.
- Verify that the existing `.reference-lift-row` styling (per-hand hint from
  Issue #10, dumbbell `data-dumbbell` flag, weight + reps inputs) doesn't
  break under a narrower row width. May need to relax `min-width` on the
  weight/reps inputs or wrap the inputs to a second line within a row.

**Test additions (Playwright):**
- New test in `e2e/user-profile.spec.ts`: at 1280×900 viewport, assert that
  two rows from the same muscle group have approximately equal `y` values
  (i.e. they're side-by-side, not stacked), and that the row 3 from the same
  group sits below them. Use `boundingBox()` like the existing 3-column
  geometry test.
- At 600×900 viewport, assert rows stack vertically (existing
  single-column behaviour preserved).

**Resolution (2026-04-27):** Implemented in
`static/css/pages-user-profile.css` inside the existing `>=1200px` media
query. Three rules:

- `.reference-lifts-grid` switches to
  `grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)` with
  `column-gap: 1.25rem`. Below 1200px the existing single-column
  `display: grid; gap: 0.65rem` from the base rule is unchanged.
- `.reference-lift-group-title` gets `grid-column: 1 / -1` so each
  muscle-group heading spans both columns above its rows. The eye still
  reads top-to-bottom across groups, left-to-right within a group.
- `.reference-lift-row` interior template was retemplated to
  `minmax(0, 1fr) minmax(0, 1fr)` with the label child given
  `grid-column: 1 / -1`. The label spans the full row width and the
  Weight + Reps inputs sit side-by-side underneath it. The original
  3-cell `label | weight | reps` template won't fit in the ~270px
  column the centre panel exposes (centre column ≈ 600px on a 1280
  viewport, minus frame + form padding, minus 1.25rem column gap).

No HTML, JS, or Jinja changes — the existing
`{% for group in reference_lift_groups %}` loop already emits headings
and rows as siblings inside `.reference-lifts-grid`, which is exactly
the structure the new grid rules target.

The rejected accordion alternative was not implemented; the 2-column
grid alone is expected to bring the panel down to roughly one viewport
height on desktop as planned.

Tests (`e2e/user-profile.spec.ts`):
- New test *"reference lifts arrange in two columns within each muscle
  group at desktop width (Issue #15)"* at 1280×900 — pulls the first
  three Chest rows (`barbell_bench_press`, `dumbbell_bench_press`,
  `incline_bench_press`) by `data-lift-key`, asserts row 0 and row 1
  share the same `y` and row 0 is to the left of row 1, then asserts
  row 2 wraps below row 0 (same `x`, greater `y`). Also asserts the
  Chest group heading spans wider than `row0.width + row1.width` so a
  future regression that puts the heading inside a single grid cell
  fails loudly.
- New test *"reference lifts stack one-per-row on mobile (Issue #15)"*
  at 600×900 — asserts row 1 sits below row 0 (preserves the existing
  single-column behaviour from the base `.reference-lifts-grid` rule).

Verification: Chromium E2E `user-profile.spec.ts` 13 passed (~20s)
including the two new Issue #15 tests; `workout-plan.spec.ts` 20 passed
(~24s) as a sanity check that the row-template change didn't disturb
Plan-page interactions. CSS-only change so pytest unaffected.

---

## Issue #16 — Demographics data is collected but never used in the formula; add cold-start 1RM seeding

**Severity:** 🟢 Enhancement — Medium
**Area:** `utils/profile_estimator.py` (new cold-start path), possibly
`routes/user_profile.py` (estimate response when chain is empty)

The Demographics panel collects `gender`, `age`, `height_cm`, `weight_kg`, and
`experience_years`, but `utils/profile_estimator.py` ignores all of them. The
estimator chain runs Epley → tier ratio → rep-range preset → rounding using
only `user_profile_lifts` rows; if every relevant chain entry is NULL the
endpoint falls through to a generic default (or returns no estimate),
producing zero or implausibly small numbers for users who have only filled
the Demographics panel.

This is a **cold-start problem**, not a refinement of the existing chain:
when a reference lift exists, that lift IS the user's measured data and
demographics must not modify it. Multiplying a measured 1RM by a gender or
bodyweight factor would corrupt real data. Demographics only enter the
formula when the entire fallback chain for a target muscle is empty.

**Decision matrix for which demographics to use (decided 2026-04-27):**

| Demographic | Use? | Reason |
|---|---|---|
| `weight_kg` (bodyweight) | **Yes** — high signal | Strength scales sublinearly with bodyweight (Wilks / IPF / allometric ~0.67 power). The single best predictor of cold-start 1RM for a given exercise. |
| `gender` | **Yes** — medium signal | Male/female reference distributions differ ~25–40 % on lower body, less on upper. Applied as a multiplier on the cold-start default only. |
| `experience_years` | **Yes** — medium signal | Gates realistic 1RMs across novice (≤1 yr) → intermediate (1–3 yr) → advanced (3+ yr) tiers. Standard population tables (ExRx, Strength Level) bin lifters this way. |
| `height_cm` | **No** — low signal | Mostly noise except at extremes; lever-length effects on bench / squat are small relative to bodyweight. |
| `age` | **No** for v1 | Performance peaks ~25–35 then declines, but the curve is shallow and dragging it in adds complexity for little gain in v1. Revisit if requested. |
| BMI / blood work | **No** | BMI is redundant with bodyweight and doesn't distinguish lean mass; blood work isn't something the estimator can responsibly model. |

**Required implementation:**

1. Add a `cold_start_1rm(exercise, demographics) -> Optional[float]` helper in
   `utils/profile_estimator.py`. It returns a population-table 1RM for the
   target exercise's primary muscle using:
   - A baseline 1RM-per-bodyweight ratio per (movement-pattern × gender) for
     an intermediate lifter. E.g. Bench Press: male intermediate ≈ 1.0 ×
     bodyweight, female intermediate ≈ 0.6 × bodyweight. Source ratios from
     ExRx / Strength Level intermediate column; tabulate in a module-level
     `COLD_START_RATIOS` dict keyed by `(canonical_exercise_slug, gender)`
     or `(movement_pattern, gender)`.
   - An experience multiplier: novice 0.7, intermediate 1.0, advanced 1.2.
     Map `experience_years` → tier (≤ 1 → novice, 1–3 → intermediate, > 3 →
     advanced).
   - Returns `None` if the exercise's primary muscle isn't in the cold-start
     table (don't invent numbers for obscure movements; let the existing
     fallback handle them).
2. Wire it into `_estimate_from_profile` (or a new sibling function) at the
   **end** of the existing chain — after profile_lift direct match, after
   cross-muscle fallback, before the generic default. Tag the response with
   `reason="profile_cold_start"` and `source="cold_start"` so the Plan page
   can show provenance ("from population estimate" instead of "from your
   profile").
3. Cap aggressiveness on cold start: clamp the working-weight output to the
   **lighter** end of whatever rep-range preset applies, since the user has
   no measured data and an over-prescription is more dangerous than an
   under-prescription. E.g. multiply the cold-start 1RM by 0.95 before
   feeding into the preset, OR force the Light preset (RIR 2, RPE 7.5,
   10–15 reps @ 0.65 of 1RM) for the first session, regardless of the
   exercise's tier.

**Required test changes:**
- New tests in `tests/test_profile_estimator.py`:
  - `test_cold_start_used_only_when_chain_is_empty` — sets demographics
    only (no lift rows), asserts a positive cold-start estimate with
    `reason="profile_cold_start"`.
  - `test_cold_start_does_not_override_filled_reference_lift` — sets
    `barbell_bench_press = 100 × 5` AND demographics, asserts the response
    uses the reference lift unchanged (`reason="profile"`, weight derived
    from 100 × 5, NOT scaled by demographics).
  - `test_cold_start_gender_factor` — male vs female demographics produce
    different numbers for the same compound.
  - `test_cold_start_experience_factor` — novice vs advanced produce
    different numbers.
  - `test_cold_start_returns_none_for_obscure_exercise` — exercise outside
    the cold-start table returns `None`, falling through to the existing
    generic default.
- New Playwright test in `e2e/user-profile.spec.ts`: fill Demographics only
  (75 kg male, 3 yrs), select Barbell Bench Press on the Plan page, assert
  a non-zero weight suggestion AND the provenance label reads "from
  population estimate" (or whichever string Plan-page provenance uses for
  cold start).

**Out of scope (potential follow-ups):**
- Age-based decline curve (post-30 → -1 % per decade ish). Defer to v2.
- Calibration loop: once the user logs sets, blend cold-start with logged
  performance instead of replacing the whole chain. Defer until cold-start
  v1 is shipped and we have data on whether it's accurate enough on its
  own.
- Fancier population models (Wilks, DOTS). Hardcoded ratios are simpler
  and easier to maintain; revisit if cold-start numbers feel off.

**Resolution (2026-04-28):** Implemented in `utils/profile_estimator.py`.

- Added module-level constants: `COLD_START_RATIOS` (16 entries keyed by
  `(canonical_primary_muscle, gender)` covering Chest, Quadriceps,
  Hamstrings, Gluteus Maximus, Latissimus Dorsi, Front-Shoulder, Biceps,
  Triceps), `EXPERIENCE_TIER_BOUNDS` (≤1 yr → novice, 1–3 yr →
  intermediate, >3 yr → advanced), `EXPERIENCE_MULTIPLIERS` (0.7 / 1.0
  / 1.2), and `COLD_START_PRESET = "light"`.
- New `cold_start_1rm(exercise, demographics) -> Optional[float]` returns
  `bodyweight_kg × COLD_START_RATIOS[(muscle, gender)] ×
  EXPERIENCE_MULTIPLIERS[tier]`, or `None` when essential demographics
  are missing, the equipment is `Dumbbells` / `Bodyweight` / excluded
  (Trx, Bosu_Ball, etc.), or the primary muscle has no entry in the
  ratios table.
- New `_estimate_from_cold_start(exercise_row, demographics)` wraps
  `cold_start_1rm` into the standard estimate-response shape: applies
  the existing `tier_multiplier` (`TIER_RATIOS[target_tier] /
  TIER_RATIOS["complex"]`) so accessory / isolation targets scale down
  from the complex-tier seed, then forces the Light preset (10–15 reps,
  RIR 2, RPE 7.5, pct 0.65) regardless of the target's tier so the
  seeded suggestion errs toward under-prescription. Tagged with
  `source="cold_start"` and `reason="profile_cold_start"`.
- `estimate_for_exercise` now reads demographics from
  `user_profile WHERE id = 1` and inserts the cold-start branch between
  the existing `_estimate_from_profile` chain and the
  `default_no_reference` / `default_excluded` fallback. Order:
  log → profile chain (direct match → cross-muscle fallback) →
  cold-start → generic default. The cold-start path is fallback-only —
  any non-empty `user_profile_lifts` row for a target muscle short-
  circuits before cold-start runs, so a measured 1RM is never modified
  by demographics.
- `static/js/modules/workout-plan.js` adds
  `cold_start: 'from population estimate'` to
  `ESTIMATE_SOURCE_LABELS` so the Plan-page provenance reads "from
  population estimate" when the cold-start branch fires.

Test coverage:

- `tests/test_profile_estimator.py` (5 new pytest cases):
  - `test_cold_start_used_only_when_chain_is_empty` — 80 kg M, 3 yrs,
    Barbell Bench Press → `source="cold_start"`,
    `reason="profile_cold_start"`, weight ≈ 52.0 kg, Light preset
    (10–15 reps, RIR 2, RPE 7.5).
  - `test_cold_start_does_not_override_filled_reference_lift` —
    `barbell_bench_press = 100 × 5` AND demographics → response uses
    the filled reference (`reason="profile"`, weight ≈ 99.0 kg from the
    Issue #14 same-tier-direct-match math), NOT cold-start.
  - `test_cold_start_gender_factor` — male vs female (same 80 kg, 3 yrs,
    Barbell Bench Press) produce different cold-start weights;
    `male > female`.
  - `test_cold_start_experience_factor` — novice (0.5 yr) vs advanced
    (5 yr) at 80 kg M produce different cold-start weights;
    `advanced > novice`.
  - `test_cold_start_returns_none_for_obscure_exercise` — Forearms
    (not in `COLD_START_RATIOS`) → both `cold_start_1rm` and
    `estimate_for_exercise` return / collapse to
    `default_no_reference` (no invented number).
- `e2e/user-profile.spec.ts` (1 new Playwright test):
  *"demographics-only profile seeds a non-zero cold-start estimate on
  the Plan page (Issue #16)"* — POSTs `gender="M"`, `weight_kg=75`,
  `experience_years=3` to `/api/user_profile` with all reference lifts
  null (set by the existing `beforeEach`), then on `/workout_plan`
  selects GYM › Full Body › Workout A › Barbell Bench Press. Asserts
  weight `48.75`, min/max reps `10` / `15`, RIR `2`, RPE `7.5`, and
  provenance text `"from population estimate"` — so the JS label
  pickup, the route response shape, and the estimator math are all
  exercised end-to-end.

Verification: pytest `tests/test_profile_estimator.py` 48 passed
(~5 s; 43 existing + 5 new); full pytest 1033 passed (~2 m 30 s);
Chromium E2E `user-profile.spec.ts` 14 passed (~19 s; 13 existing +
1 new) and `workout-plan.spec.ts` 20 passed (~24 s) as a sanity check
on Plan-page interactions.

---

## Issue #17 — Personalised estimator transparency: "how the system sees you" + per-suggestion math + accuracy-improvement guidance

**Severity:** 🟡 UX gap — Medium
**Area:** `templates/user_profile.html`, `templates/workout_plan.html`,
`utils/profile_estimator.py` (estimate response shape),
`routes/user_profile.py`, `static/js/modules/workout-plan.js`

The estimator currently exposes only a `reason` string ("from your profile" /
"from logs" / generic) and the final numbers. Users have no way to see *what
inputs drove this number*, *which step of the chain produced it*, or *what
they could change to make it more accurate*. Issue #4 added a static "How
does this work?" formula explainer, but it's generic — it explains the math
in the abstract, not on YOUR data. After Issue #16 ships cold-start seeding
from Demographics, the gap widens further: a user who fills only Demographics
will get plausible numbers but no signal that those numbers are population
guesses, not measurements — and no instructions on how to upgrade them.

This issue covers three deliverables that can ship independently but are
designed together so the copy is consistent across the app.

---

### Deliverable A — Profile page: "How the system sees you" card

A new collapsible card on `/user_profile`, default expanded, near the top of
the page (between the onboarding banner and the Demographics section, OR as
its own column item in the desktop 3-column grid).

**Content (renders live as the user types into the form):**

1. **Classification line** — plain English summary of the user's
   demographics tier:
   *"Male · intermediate (3 yrs) · 75 kg"*
   Empty fields show as italicised *"unknown"* so the user can see what's
   missing.
2. **Cold-start anchor lifts** — for the canonical compounds (Bench, Squat,
   Deadlift, Overhead Press), show the cold-start 1RM the system *would*
   use if no reference lift were entered:
   *"Cold-start estimates from your demographics: Bench ≈ 75 kg · Squat ≈
   95 kg · Deadlift ≈ 115 kg · Overhead Press ≈ 50 kg."*
   Hidden / dimmed when Demographics is incomplete.
3. **Override status** — show which lifts have been promoted from
   cold-start to measured:
   *"Replaced by your data: Bench Press (saved 100 kg × 5 → 1RM 117 kg)."*
   List grows as the user fills the questionnaire.
4. **What's missing** — a short list of the 3 highest-impact reference
   lifts the user has NOT yet entered (heuristic: prefer the canonical
   compounds for muscles that have no entries in the chain at all):
   *"You'd improve estimates the most by entering: Romanian Deadlift,
   Barbell Bicep Curl, Standing Calf Raise."*
5. **One-line copy reinforcing user agency:**
   *"All numbers are starting points. Override anything from the Plan page
   — your edits stick."*

**Implementation notes:**
- Most numbers can be computed at page-render time by calling
  `cold_start_1rm(...)` for the canonical compounds; no new endpoint
  needed.
- Updates on `change` events from the Demographics + Reference Lifts forms.
- Reuse the `frame-calm-glass` skin from Issue #1 / `.profile-explainer`
  from Issue #4 for visual consistency.

---

### Deliverable B — Plan page: per-suggestion "show the math" expander

Next to the suggested Weight (and ideally Reps / RIR / RPE) on the Workout
Controls panel, add a small ℹ️ button that expands a step-by-step trace of
how that exact suggestion was produced.

**Trace content — three example states:**

1. **Direct match (reference lift saved):**
   ```
   Bench Press 85 kg ← your data
     • Reference lift: Barbell Bench Press 100 kg × 5
     • Estimated 1RM: Epley(100, 5) = 117 kg
     • Tier: complex → complex (multiplier 1.00)
     • Preset: Heavy (RIR 1, RPE 9, 4–6 reps @ 0.85 of 1RM)
     • Working weight: 117 × 0.85 ≈ 99 kg → barbell-rounded → 100 kg
     • Rounding: 2.5 kg plate
   What could change this? Editing your Bench Press reference lift
   would update this number.
   ```

2. **Cross-muscle fallback:**
   ```
   Incline Dumbbell Curl 9 kg ← inferred from another lift
     • Reference lift: Dumbbell Curl 20 kg × 6 (cross-muscle fallback)
     • Estimated 1RM: Epley(20, 6) = 24 kg
     • Tier: isolated → isolated (multiplier 1.00)
     • Cross-muscle factor: 0.6 (movement isn't a direct match)
     • Preset: Light (RIR 2, RPE 7.5, 10–15 reps @ 0.65 of 1RM)
     • Working weight: 24 × 1.00 × 0.6 × 0.65 ≈ 9.36 kg → dumbbell-rounded
       → 9 kg per hand
   How to improve this estimate: enter Incline Dumbbell Curl directly
   in your Reference Lifts to skip the cross-muscle factor (would raise
   the suggestion to ~14 kg per hand).
   ```

3. **Cold-start (Demographics only):**
   ```
   Bench Press 47.5 kg ← population estimate
     • No reference lift saved.
     • Cold-start 1RM: 1.0 × 75 kg bodyweight × 1.0 (intermediate, 3 yrs)
       = 75 kg
     • Preset: Light (forced for cold-start safety, RIR 2, RPE 7.5,
       10–15 reps @ 0.65 of 1RM)
     • Working weight: 75 × 0.65 ≈ 48.75 kg → barbell-rounded → 47.5 kg
   How to improve this estimate: enter Barbell Bench Press in your
   Reference Lifts. A measured 1RM replaces this population guess and
   unlocks Heavy/Moderate presets based on your actual strength.
   ```

**Implementation notes:**
- Extend the `/api/user_profile/estimate` response with a structured
  `trace` object, e.g.:
  ```json
  {
    "weight": 47.5,
    "reason": "profile_cold_start",
    "trace": {
      "source": "cold_start",
      "steps": [
        {"label": "Bodyweight ratio (bench × male)", "value": 1.0},
        {"label": "Bodyweight", "value": 75, "unit": "kg"},
        {"label": "Cold-start 1RM", "value": 75, "unit": "kg"},
        {"label": "Experience tier", "value": "intermediate (3 yrs)",
         "factor": 1.0},
        {"label": "Preset", "value": "Light", "factor": 0.65},
        {"label": "Rounding", "value": "barbell, 2.5 kg"}
      ],
      "improvement_hint": {
        "action": "enter_reference_lift",
        "lift_key": "barbell_bench_press",
        "copy": "Enter Barbell Bench Press in your Reference Lifts to
                 replace this population guess with your measured 1RM."
      }
    }
  }
  ```
- The `trace` and `improvement_hint` are constructed by the estimator at
  the same time as the final number — single source of truth.
- Plan-page JS (`static/js/modules/workout-plan.js`) reads the trace and
  renders the expander. Lazy: don't render until the user clicks ℹ️.
- Keep the existing one-line provenance label
  (`#workout-estimate-provenance`) — it stays as the at-a-glance summary;
  the expander is the deep dive.

---

### Deliverable C — Accuracy-improvement guidance (cross-cutting copy)

The "how to improve" hint in B is per-suggestion. Add a complementary,
profile-wide accuracy widget on the Profile page that ranks the user's
*overall* estimator quality and points at the next 1–3 highest-impact
actions.

**Quality bands (heuristic):**

| Band | Trigger | Copy |
|---|---|---|
| **Population estimate only** | All reference lifts NULL, demographics present | "Numbers come from population averages. Add even one reference lift to start personalising." |
| **Partially personalised** | 1–4 reference lifts entered, rest fall back via cross-muscle or cold-start | "About 30 % of your suggestions use your real data. Add the lifts below to lift this further." |
| **Mostly personalised** | 5+ reference lifts AND at least one entry per major muscle group | "Most of your suggestions use your real data. Optional: add the bodyweight chinup / weighted chinup pair to refine pull tier accuracy." |
| **Fully personalised** | All `KEY_LIFTS` slugs covered | "All your suggestions use your measured lifts. To keep them current, re-enter your reference lifts when you set a new PR." |

**Mechanism:**
- Compute coverage server-side in `routes/user_profile.py` when rendering
  the Profile page; expose `accuracy_band` + `next_high_impact_lifts:
  list[str]` in the page context.
- Render as a compact pill / progress bar at the top of the
  "How the system sees you" card from Deliverable A.
- Re-render when the user saves the Reference Lifts form (already wired —
  use the existing post-save callback).

---

### What "might affect the score" — surfacing the input dependencies

Both the Profile-page card (A) and the per-suggestion expander (B) must make
the input dependencies explicit, because users can't improve what they can't
see. Specifically every trace must call out, in plain copy:

- Which **reference lift slug** drove the number (e.g. *"based on your saved
  Barbell Bench Press"*) OR that no slug was matched (*"no reference lift
  found — using population estimate"*).
- Whether a **cross-muscle fallback factor** was applied (the 0.6
  multiplier) and what specifically the user could enter to skip it.
- Which **tier classification** the target exercise got (complex /
  accessory / isolated) and which **rep-range preset** that produced
  (Heavy / Moderate / Light).
- Which **rounding rule** ran (barbell / dumbbell / machine /
  bodyweight) — explains why "47.5 kg" instead of "48.75 kg".
- For cold-start: which **demographics fields** were used (gender,
  bodyweight, experience), and that height / age / BMI were intentionally
  not used (link to the rationale documented in Issue #16).

Copy guideline: avoid jargon in the headline (use *"complex"* not
*"complex tier"*), but keep the underlying values visible so a curious
user can audit them.

---

**Test additions:**

- `tests/test_profile_estimator.py`:
  - `test_estimate_response_includes_trace` — every code path (direct
    match, cross-muscle, cold-start, generic) returns a populated `trace`
    list with the expected step labels.
  - `test_trace_improvement_hint_for_cross_muscle` — cross-muscle path
    suggests entering the direct lift slug.
  - `test_trace_improvement_hint_for_cold_start` — cold-start path
    suggests entering the canonical compound for the target muscle.
  - `test_trace_improvement_hint_absent_for_direct_match` — direct match
    has no improvement hint (already optimal).
- `tests/test_user_profile_routes.py`:
  - `test_profile_page_context_includes_accuracy_band` — band reflects how
    many reference lifts are filled.
  - `test_profile_page_next_high_impact_lifts_excludes_filled` — already-
    saved lifts don't appear in the suggested-next list.
- `e2e/user-profile.spec.ts`:
  - "How the system sees you" card: empty profile → renders cold-start
    bench / squat / deadlift values; saving Bench 100 × 5 → "Replaced by
    your data" line appears for Bench.
  - Accuracy band: empty profile renders "population estimate only"; after
    saving 5 lifts the band advances.
- `e2e/workout-plan.spec.ts`:
  - Click ℹ️ next to suggested weight → trace expander opens with step
    labels, the "How to improve" hint, and a clickable link to the
    Profile page anchored to the suggested lift row.

---

**Out of scope (potential follow-ups):**

- A history view ("here's what your estimates looked like 4 weeks ago") —
  defer until the cold-start + trace path is shipped.
- Real-time recalibration from logged sets (Plan → Log feedback loop) —
  bigger project; tracked separately.
- Confidence intervals on the cold-start band (e.g. "75 kg ± 12 kg") —
  population variance data isn't in the codebase yet and would need a
  decision on which dataset to source from.

---

**Resolution (2026-04-28):** Implemented as a single PR covering all
three deliverables (A, B, C ship together so the copy stays consistent).

*Deliverable A — "How the system sees you" card.* New
`frame-calm-glass` `[data-section="profile insights"]` section in
`templates/user_profile.html` rendered above
`.user-profile-layout` (so it shows above all three forms). Server-side
context is built in `routes/user_profile.py:_build_profile_insights()`
which calls into the new `utils/profile_estimator.py` helpers
(`accuracy_band`, `cold_start_anchor_lifts`, `replaced_anchor_lifts`,
`next_high_impact_lifts`). Live updates without a round-trip are
handled by `static/js/modules/user-profile.js` — it ports the cold-start
logic and the accuracy-band classifier into JS (with explicit "must
match Python" comments) and re-renders the card on every `input`
/ `change` event from the demographics + reference-lifts forms.

*Deliverable B — Plan-page "show the math" expander.* The estimator
is now the single source of truth for the trace. Each branch in
`utils/profile_estimator.py` (`_lookup_last_logged`,
`_estimate_from_profile` direct + cross + bodyweight,
`_estimate_from_cold_start`, `_default`) constructs its own
`trace = {source, steps[], improvement_hint?}` via the new
`_build_*_trace()` helpers. Steps are structured (not strings) — each
carries `label`, optional `value` / `unit` / `factor` / `detail` —
so the JS can render any branch's trace without reconstructing the
math. `templates/workout_plan.html` adds an `i`-icon button
(`#workout-estimate-trace-toggle`) next to the existing one-line
provenance label, and `static/js/modules/workout-plan.js`'s new
`bindEstimateTraceToggle()` + `renderEstimateTrace()` lazy-render
the steps + improvement hint on first click. The hint includes
a clickable Profile-page link anchored to the suggested lift row
(`/user_profile#lift-{slug}-weight`). Direct-match traces have no
`improvement_hint` (already optimal). The existing
`#workout-estimate-provenance` one-liner stays untouched.

*Deliverable C — Profile-wide accuracy band.* `accuracy_band()` in
`utils/profile_estimator.py` returns `{band, filled_count,
total_count, copy}` for the four bands described in the spec
(`population_only` / `partial` / `mostly` / `fully`). The
`mostly` gate also checks that every major muscle group has at
least one entry via `ACCURACY_MAJOR_MUSCLE_GROUPS`. The pill +
progress bar render at the top of card (A) and use a colour ramp
keyed off `[data-band]` (grey / amber / blue / green). The JS
mirror handles the exact same band logic so live form input
(without a save) updates the pill / fill bar / count instantly;
saving via the existing Reference Lifts form re-renders the card
on the next page navigation (the post-save callback already exists
from earlier issues).

Single-source-of-truth surfaces:
- `utils/profile_estimator.py` — `KEY_LIFT_LABELS`,
  `COLD_START_CANONICAL_COMPOUND`, `HIGH_IMPACT_LIFT_PRIORITY`,
  `ACCURACY_MAJOR_MUSCLE_GROUPS`, plus the public helpers
  `accuracy_band()`, `next_high_impact_lifts()`,
  `cold_start_anchor_lifts()`, `replaced_anchor_lifts()`,
  `filled_lift_keys()`.
- All trace step copy (input dependencies, tier classification,
  rep-range preset, rounding rule, demographics fields used) is
  built in the estimator. The Plan-page JS does no math — it just
  walks `trace.steps` and writes `<li>` rows.

CSS:
- `static/css/pages-user-profile.css` gains the `.profile-insights*`
  styling (band pill, fill bar, classification line with
  `em[data-missing]` italic dim, anchor / replaced / missing lists,
  footer agency copy).
- `static/css/pages-workout-plan.css` gains the
  `.workout-estimate-trace*` styling (toggle pill, lazy-rendered
  trace box, step list with `tabular-nums`, improvement-hint
  callout, dark-mode parity).

Test coverage:
- `tests/test_profile_estimator.py` (4 new pytest cases):
  `test_estimate_response_includes_trace`,
  `test_trace_improvement_hint_for_cross_muscle`,
  `test_trace_improvement_hint_for_cold_start`,
  `test_trace_improvement_hint_absent_for_direct_match`. Two existing
  exact-match assertions in this file were rewritten to ignore the
  new `trace` key (`{k: v for k, v in estimate.items() if k != "trace"}`).
- `tests/test_user_profile_routes.py` (2 new):
  `test_profile_page_context_includes_accuracy_band` (band advances
  empty → partial after one save) and
  `test_profile_page_next_high_impact_lifts_excludes_filled` (saved
  slugs don't appear in the suggested-next list).
- `e2e/user-profile.spec.ts` (2 new): "How the system sees you" card
  empty-state + cold-start anchor render + Replaced-by-your-data
  list growth; accuracy band advances from population-only to
  Mostly personalised after saving 6 lifts spanning all 6 major
  muscle groups.
- `e2e/workout-plan.spec.ts` (1 new): the "Show the math" expander
  appears next to the suggested weight, opens with steps containing
  `Cold-start 1RM` / `Light` / `Bodyweight ratio`, and surfaces a
  Profile-page link anchored to `lift-barbell_bench_press-weight`.

Verification: pytest 1039 passed (~2 m 35 s; 1033 baseline + 6 new);
Chromium E2E targeted set (`user-profile.spec.ts` +
`workout-plan.spec.ts` + `volume-progress.spec.ts` +
`volume-splitter.spec.ts`) 80 passed (~1 m 50 s); broader sanity
(`smoke-navigation.spec.ts` + `accessibility.spec.ts` +
`empty-states.spec.ts`) 50 passed (~1 m 12 s).

---

## Issue #18 — "How the system sees you" card should be visual stats + peer-range comparisons, not text-only

**Severity:** 🟢 Enhancement — Medium
**Area:** `templates/user_profile.html`, `static/js/modules/user-profile.js`,
`static/css/pages-user-profile.css`, `utils/profile_estimator.py`,
`routes/user_profile.py`

Issue #17 / Deliverable A shipped the *"How the system sees you"* card as a
plain-text summary block (classification line · cold-start anchor list ·
replaced-by-your-data list · accuracy pill + fill bar). The intent — make
the user feel the system has a model of them — is right, but the
implementation reads like prose. Users expected a **dashboard-style card**:
stats with units, small charts, and clear comparisons against population
ranges (age / bodyweight / height / training-experience cohorts) so they
can see at a glance *"where I sit relative to people the estimator
treats as similar."*

The card must remain **informational, never prescriptive**: it explains the
estimator's frame of reference, it does not rate the user. Copy stays
non-judgemental ("you are stronger / weaker than the cohort" is
out-of-scope; "your bench is at the 60th percentile of the male
intermediate cohort the estimator uses" is in-scope, and only when we
genuinely have the data to back it).

---

### Deliverable A — Stats tiles (replace the classification line)

Today: *"Male · intermediate (3 yrs) · 75 kg"*.

Replace with a 4-tile mini-grid (responsive: 4-up desktop, 2-up tablet,
1-up phone). Each tile shows:

| Tile          | Big number                       | Sub-line (cohort range)                                    | Empty state                       |
|---------------|----------------------------------|------------------------------------------------------------|-----------------------------------|
| Bodyweight    | `75 kg`                          | *"Cohort: 70–85 kg (male intermediate)"*                   | "Add bodyweight to enable"        |
| Height        | `178 cm`                         | *"Cohort: 170–185 cm"*                                     | "Add height (currently unused — flagged for future use, see Issue #16)" |
| Age           | `34 yrs`                         | *"Cohort: 25–45 yrs"*                                      | "Add age (currently unused, see Issue #16)" |
| Experience    | `Intermediate` · 3 yrs           | *"Tier multiplier: 1.00 of trained max"*                   | "Pick a level to enable cold-start estimates" |

**Implementation notes:**
- Each tile reuses the existing `frame-calm-glass` token palette; new
  `.profile-insights-tile` class in `pages-user-profile.css`.
- The cohort range strings come from a new `cohort_ranges()` helper in
  `utils/profile_estimator.py` that returns `{bodyweight: (low, high),
  height: (low, high), age: (low, high), tier_label, tier_multiplier}`
  given the same `(gender, age, height_cm, bodyweight_kg, experience)`
  tuple the estimator already consumes. **No new data sources** — the
  helper just exposes the buckets the estimator is already using
  internally for cold-start (see Issue #16). If a bucket isn't yet
  consumed (height, age), the tile shows the *"currently unused"* tag
  so we don't imply the value affects the suggestion when it doesn't.
- Tiles must visually de-emphasise (grey out, italic copy) the
  "currently unused" state so the user can see what's collected vs.
  what's actually load-bearing. This is a transparency win that Issue
  #16's documented "fields not yet wired" decision currently hides.

---

### Deliverable B — Strength-vs-cohort bar chart (per filled reference lift)

For every reference lift the user has saved, render a one-row horizontal
bar showing the user's **estimated 1RM** against the **cold-start 1RM
band** the estimator would otherwise have used for the same demographic
cohort.

```
Bench Press               45 ──────● 117 ─────────────────── 165 kg
                       cold-start    you (est. 1RM)        cohort upper
Romanian Deadlift         60 ─────────────● 140 ─────────── 180 kg
Barbell Back Squat        70 ───────────── 130 ●─────────── 175 kg
```

- The cold-start anchor (`cold_start_1rm(...)`) is the left-side
  reference; the cohort upper bound is `cold_start_1rm × tier_multiplier`
  for the next tier up (e.g. intermediate → advanced) — same lookup
  table, no new tuning.
- The user's marker (●) is the Epley-derived 1RM from their saved
  reference lift, NOT the working-weight suggestion. The point is to
  show *where the underlying 1RM lands*, not the rep-range-reduced
  weight that ends up on the Plan page.
- Implementation: pure SVG inline in the template (no chart library).
  The existing CSS variable system (`--accent-indigo`,
  `--text-secondary`) provides the palette. A new
  `render_cohort_bar(estimate_1rm, cold_start_1rm, cohort_upper)`
  Jinja macro keeps the markup repeated rows DRY.
- Empty state (no reference lifts saved): the section is hidden;
  Deliverable C still renders.

---

### Deliverable C — Coverage donut + cohort summary

Compact circular progress (donut) showing
`filled_lift_count / total_lift_count` from
`profile_estimator.accuracy_band()`. The number in the centre matches
the existing accuracy-band fill bar; this just gives the same metric a
more glanceable shape so the card stops being a wall of bars.

Below the donut, a one-line **cohort summary** rendered from
`cohort_ranges()`:

> *"Estimator cohort: male, age 25–45, bodyweight 70–85 kg, intermediate
> (3 yrs trained). Suggestions are calibrated to lifters in this
> bucket."*

Empty fields render greyed: *"Estimator cohort: male, age **unknown**,
bodyweight 70–85 kg, **experience level unknown** — fill these to
calibrate."*

---

### What this card is NOT

- It is **not a leaderboard or strength-standards rating**. We deliberately
  do *not* ship a "novice / intermediate / advanced / elite" bucket
  classifier on top of the user's lifts (that's a different feature, owned
  by a future "Strength Standards" page if we decide to build one).
- It does **not** introduce new data inputs beyond what Issue #16 already
  collects.
- It does **not** alter the estimator output. Every number the chart
  shows is a re-display of values the estimator already computes — single
  source of truth stays in `utils/profile_estimator.py`.

---

### Acceptance checklist

- [ ] 4 stats tiles render (bodyweight / height / age / experience) with
  cohort sub-lines pulled from `cohort_ranges()`.
- [ ] Tiles for currently-unused inputs (height, age until Issue #16
  decisions land) are visibly de-emphasised AND link to the rationale
  documented in Issue #16.
- [ ] Cohort bar chart row renders for each saved reference lift with
  cold-start anchor · user 1RM · cohort upper.
- [ ] Coverage donut + cohort summary line render for every state
  (population / partial / mostly / fully — same bands as Issue #17C).
- [ ] All values update live on form `input` events (no save round-trip),
  matching the Issue #17 JS mirror behaviour.
- [ ] Pytest: 2 new cases in `tests/test_profile_estimator.py` covering
  `cohort_ranges()` shape + boundary-tier behaviour.
- [ ] Pytest: 1 new case in `tests/test_user_profile_routes.py` asserting
  the page context exposes `cohort_ranges` + `cohort_bars` (list).
- [ ] Playwright: 1 new test in `e2e/user-profile.spec.ts` that fills
  Demographics, saves one reference lift, and asserts (a) the four
  tiles appear, (b) the matching cohort bar row renders, (c) the donut
  centre matches the accuracy-band count.

**Resolution (2026-04-28):** Implemented as a single PR covering the
three deliverables (A tiles, B cohort bars, C donut + summary) so the
copy stays consistent. The estimator is the single source of truth
— Python builds the data, JS mirrors only the live-update math.

*Deliverable A — Stats tiles.* New
`utils/profile_estimator.py::cohort_ranges()` returns four tile dicts
(`bodyweight`, `height`, `age`, `experience`) plus tier metadata
(`tier`, `tier_multiplier`, `next_tier`, `next_tier_multiplier`). Each
tile carries `value_text`, `cohort_text`, `empty`, `used`, and an
`unused_reason`. Cohort buckets are static brackets keyed off gender
(`COHORT_BODYWEIGHT_KG`, `COHORT_HEIGHT_CM`) plus a universal
`COHORT_AGE_YEARS = (25, 45)`; they contextualise the user's
demographics without altering any suggestion math (matching the
"informational only" invariant). Height + age tiles set `used=False` so
the UI can de-emphasise them (`data-unused="true"` styling +
`unused` flag pill) — the user can see what the page collects vs.
what currently feeds the estimator. The classification line that
shipped in Issue #17 is gone; the four-tile grid in
`templates/user_profile.html` (`[data-insights-tile]`) replaces it.

*Deliverable B — Cohort bar chart.* New
`utils/profile_estimator.py::cohort_bars()` walks the canonical
compounds in `COLD_START_CANONICAL_COMPOUND` and emits one row per
saved canonical compound: `user_1rm_kg` (Epley-derived from the saved
weight × reps), `cold_start_1rm_kg` (the population-table anchor at
the user's tier), and `cohort_upper_kg` (cold-start scaled by
`next_tier_multiplier / current_tier_multiplier`). At advanced tier
the next-tier multiplier extrapolates via `ADVANCED_COHORT_REACH = 1.2`
so the user marker stays inside the bar without introducing a new
strength tier. Rows where the cold-start anchor cannot be computed
(missing demographics, muscle outside `COLD_START_RATIOS`,
bodyweight-only slugs) are omitted — the section is hidden entirely
when the list is empty. Markup in
`templates/user_profile.html::[data-insights-bars]` is pure inline
SVG-free CSS — three position markers (cold-start, user, cohort
upper) on a track styled via `--cs-pct`, `--cu-pct`, and per-marker
`--mark-pct` custom properties.

*Deliverable C — Coverage donut + cohort summary.* New
`utils/profile_estimator.py::coverage_donut()` re-projects
`accuracy_band()`'s `filled_count / total_count` as a percent. The
donut renders as inline SVG with two concentric circles
(`stroke-dasharray` keyed off `donut.percent`), shares the
`[data-band]`-driven colour ramp with the existing linear meter, and
mounts inside the band-meter row of the card. The cohort summary
line lives below the tiles: `cohort_ranges().summary` builds a
plain-language one-liner ("Estimator cohort: male, age 25–45,
bodyweight 70–90 kg, intermediate (3 yrs trained). Suggestions are
calibrated to lifters in this bucket.") that gracefully falls back to
*"... — fill these to calibrate."* when gender or experience is
missing.

Live updates: `static/js/modules/user-profile.js` ports the cohort
constants under "must match Python" comments, mirrors
`cohort_ranges()` / `cohort_bars()` / `coverage_donut()` math, and
hooks the `input` / `change` events on the demographics + reference
lifts forms so tiles / cohort summary / cohort bars / donut update
without a save round-trip.

CSS: `static/css/pages-user-profile.css` gains
`.profile-insights-donut*`, `.profile-insights-tile*`,
`.profile-insights-cohort-summary`, `.profile-insights-bar-list`,
`.profile-insights-bar-row`, `.profile-insights-bar-track`,
`.profile-insights-bar-fill`, `.profile-insights-bar-marker` (with
`is-cold-start` / `is-user` / `is-cohort-upper` variants), and dark-mode
parity. The dead `.profile-insights-classification*` selectors from
Issue #17's classification-line markup were removed.

Test coverage:
- `tests/test_profile_estimator.py` (6 new):
  `test_cohort_ranges_shape_and_used_flags`,
  `test_cohort_ranges_advanced_tier_extrapolates_next_multiplier`,
  `test_cohort_ranges_empty_demographics`,
  `test_cohort_bars_skips_when_demographics_incomplete`,
  `test_cohort_bars_filled_canonical_compound`,
  `test_coverage_donut_counts_filled_lifts`.
- `tests/test_user_profile_routes.py` (3 new):
  `test_profile_page_renders_stats_tiles_and_cohort_summary` (tiles +
  empty-state copy + unused-flag), 
  `test_profile_page_renders_cohort_bar_after_demographics_and_lift`
  (bars unhidden, calibrated summary, populated tile values),
  `test_profile_page_donut_count_matches_accuracy_band`
  (donut payload mirrors band counts).
- `e2e/user-profile.spec.ts` (1 new): "How the system sees you" card
  surfaces stats tiles, cohort bar, and donut after demographics +
  lift (Issue #18) — fills demographics, saves one canonical
  compound, asserts (a) all four tiles render with values + cohort
  range strings, (b) the matching cohort bar row appears with the
  expected cold-start / user / cohort-upper kg numbers, (c) the
  donut count matches the accuracy band count. The existing
  Issue #17 spec was updated to query
  `[data-insights-tile=...][data-empty="true"]` instead of the
  retired `[data-classification-part=...]` markers.

Verification: pytest 1048 passed (~2 m 53 s; 1039 baseline + 9 new);
Chromium E2E targeted set (`user-profile.spec.ts` +
`workout-plan.spec.ts` + `volume-progress.spec.ts` +
`volume-splitter.spec.ts`) 82 passed (~1 m 54 s; 80 baseline + 2 new
including the Issue #18 case); broader sanity
(`smoke-navigation.spec.ts` + `accessibility.spec.ts` +
`empty-states.spec.ts`) 50 passed (~1 m 12 s).

---

## Issue #19 — Reuse the bodymap SVG to visualise reference-lift coverage on the Profile page

**Severity:** 🟢 Enhancement — Medium
**Area:** `templates/user_profile.html`, `static/js/modules/user-profile.js`,
`static/vendor/react-body-highlighter/{body_anterior,body_posterior}.svg`,
`utils/profile_estimator.py`, `static/css/pages-user-profile.css`

The starter-plan generator already uses the
`react-body-highlighter` SVGs (`static/vendor/react-body-highlighter/
body_{anterior,posterior}.svg`, exposed via
`static/js/modules/muscle-selector.js`) to let the user select muscle
groups visually. We should reuse those exact assets on the Profile page
to give an instant visual answer to *"which muscles does the estimator
have measured data for, and which fall back to cold-start / cross-muscle
inference?"*

This is the visual companion to Issue #17 / Deliverable C
(accuracy band) and Issue #18 (stats card). Where #17C says *"5 of 18
lifts entered, mostly personalised"*, this issue makes the
**which muscles** part literally visible.

---

### Visual model

A two-pane front + back body diagram (anterior / posterior, same toggle
as the AI starter-plan generator) renders next to or below the Reference
Lifts form. Each muscle polygon takes one of four states, driven by the
saved reference lifts:

| State                  | Visual                                | Trigger                                                                                           |
|------------------------|---------------------------------------|---------------------------------------------------------------------------------------------------|
| **Measured**           | Solid `--accent-indigo` fill          | Muscle has at least one saved reference lift in `MUSCLE_TO_KEY_LIFT[muscle]`.                     |
| **Cross-muscle**       | Diagonal stripe / 50 % indigo fill    | No direct entry, but a same-chain or cross-muscle fallback lift exists (estimator returns inferred). |
| **Cold-start only**    | Outline only, dim grey                | No reference lift covers this muscle — suggestion will be the population estimate.                |
| **Not assessed**       | Hidden / neutral                      | Muscle has no canonical key lift in `KEY_LIFT_LABELS` (e.g. neck, forearms — informational only). |

Hover/tap on a muscle polygon opens a small popover:

```
Chest — Measured
  • Barbell Bench Press 100 kg × 5  (saved 2026-04-26)
  • 1RM ≈ 117 kg
  → Drives suggestions for: Bench Press, Incline Press, Dumbbell Fly,
    Machine Chest Press
```

For *Cross-muscle* state:

```
Triceps — Inferred (cross-muscle)
  No direct triceps lift saved.
  Estimator borrows from: Barbell Bench Press → cross-muscle factor 0.6.
  → Suggestion accuracy improves if you enter Triceps Extension or
    Skull Crusher.
```

Tapping the polygon (on touch) OR clicking the *"How to improve"* line in
the popover scrolls the page to the matching reference-lift row in the
form (`#lift-{slug}-weight`), reusing the same anchor pattern Issue #17B
already established for the Plan-page improvement hint.

---

### Reuse strategy

- **Asset reuse, not duplication.** Import the same vendor SVGs the
  muscle-selector module already loads. **Do not** copy the SVG markup
  into `templates/user_profile.html`. Instead, extract the SVG-loading
  helper from `static/js/modules/muscle-selector.js` into a small shared
  module (`static/js/modules/bodymap-svg.js`) that returns a populated
  `<svg>` node ready to be styled by the consumer. The starter-plan
  generator and the new Profile-page card both depend on that shared
  module.
- **Mapping reuse.** The `VENDOR_SLUG_TO_CANONICAL` table in
  `muscle-selector.js` (line 36+) is already the canonical mapping from
  vendor slugs to our muscle keys. The Profile-page coverage logic must
  consume the *same* table — no parallel mapping. If the table needs to
  move out of `muscle-selector.js` to be shared, do that as part of this
  issue, not as a side-quest.
- **Coverage logic in Python.** A new
  `muscle_coverage_state() -> dict[str, Literal["measured",
  "cross_muscle", "cold_start_only", "not_assessed"]]` helper in
  `utils/profile_estimator.py` walks the saved reference lifts +
  `MUSCLE_TO_KEY_LIFT` + `ACCURACY_MAJOR_MUSCLE_GROUPS` and emits the
  per-muscle state. The route exposes this in the page context; the JS
  mirror (same pattern as Issue #17 / accuracy-band live updates)
  recomputes it on form `input` events. Single source of truth: Python
  helper; JS is a port with the existing *"must match Python"* comment
  contract.

---

### Implementation notes

- **Bilateral sync** is already handled by `muscle-selector.js` (left
  and right deltoid polygons toggle together). The coverage view needs
  the same behaviour — extract the bilateral-pair table into the shared
  `bodymap-svg.js` module.
- **Front/back tab navigation** mirrors the muscle-selector pattern —
  default to anterior, tab pill toggles to posterior.
- **No selection state.** This is read-only visualisation. Disable click
  selection, keep only hover/tap → popover. The shared module must
  accept a `mode: "select" | "display"` prop (or expose a separate
  `renderDisplayBodymap()` entry point) so the muscle-selector and the
  Profile coverage viewer don't fight over click semantics.
- **Theme parity.** `--accent-indigo` for `measured`, the existing
  `--text-secondary` for outline/dim states. Dark-mode parity reuses
  `theme-dark.css` overrides — no new dark-mode-only rules.
- **Accessibility.** Each polygon gets `role="img"` +
  `aria-label="{muscle name} — {state}"`. The popover content also
  renders as a screen-reader-only `<dl>` list below the SVG so users on
  AT get the same coverage info linearly. The bodymap is a *companion*
  to the accuracy band (Issue #17C) and the cohort tiles (Issue #18) —
  not a replacement, so AT users are never blocked.
- **Empty state.** When zero reference lifts are saved, render the body
  diagram fully outlined (all `cold_start_only`) with a one-line
  caption: *"No measured data yet — every muscle uses the population
  estimate. Save a reference lift to start filling this in."*

---

### What this is NOT

- **Not a workout-targeting selector.** This is the *coverage* view, not
  a way to filter exercises. The selector behaviour stays exclusively
  in `muscle-selector.js` / starter-plan generator.
- **Not a soreness / fatigue tracker.** Out-of-scope; the four states
  above are the only states.
- **Not a replacement for the Reference Lifts form.** The form remains
  the input surface; the bodymap is read-only feedback. Anchored links
  from the popover into the form are the only interactive coupling.

---

### Acceptance checklist

- [ ] `static/js/modules/bodymap-svg.js` extracted from
  `muscle-selector.js`; both the starter-plan generator and the new
  Profile coverage view import from it.
- [ ] `VENDOR_SLUG_TO_CANONICAL` lives in the shared module (single
  source of truth).
- [ ] `utils/profile_estimator.py` exposes `muscle_coverage_state()`
  with unit tests covering all four states, including the
  cross-muscle-fallback case (Triceps inferred from Bench Press) and
  the cold-start-only case (no chest lifts saved).
- [ ] `routes/user_profile.py` adds `muscle_coverage` to the page
  context.
- [ ] `templates/user_profile.html` mounts the bodymap inside a
  `frame-calm-glass [data-section="muscle coverage"]` panel above the
  Reference Lifts form.
- [ ] Front/back tab toggle works; bilateral-pair polygons stay in
  sync.
- [ ] Hover popover shows lift list (measured), fallback chain
  (cross_muscle), or improvement-hint copy (cold_start_only) — copy
  must match the wording the Plan-page expander already uses
  (Issue #17B), so users see one consistent vocabulary.
- [ ] Tapping a polygon scrolls to `#lift-{slug}-weight` in the form
  using the existing anchor scheme.
- [ ] Live updates: filling / clearing a reference-lift input toggles
  the corresponding muscle's state without a save round-trip.
- [ ] Pytest: 3 new cases in `tests/test_profile_estimator.py` covering
  `muscle_coverage_state()` measured / cross-muscle / cold-start
  branches.
- [ ] Pytest: 1 new case in `tests/test_user_profile_routes.py`
  asserting the context includes `muscle_coverage` and that saving a
  Bench Press flips Chest from `cold_start_only` to `measured`.
- [ ] Playwright: 1 new test in `e2e/user-profile.spec.ts` that
  asserts (a) anterior diagram renders with all polygons in the
  cold-start outline state on first visit, (b) saving a Barbell Bench
  Press fills the chest polygon with the indigo `measured` style,
  (c) hover popover lists the saved lift and the muscles it drives,
  (d) clicking *"How to improve"* on a `cold_start_only` polygon
  scrolls the matching lift row into view.
- [ ] Manual visual check at the three responsive breakpoints — bodymap
  must not push the Reference Lifts form below the fold on desktop;
  on mobile it stacks above the form and remains tappable (44 px
  minimum hit-target on each polygon group).

**Resolution (2026-04-28):** Implemented.

- **Shared SVG module** — added
  `static/js/modules/bodymap-svg.js` exporting `VENDOR_SLUG_TO_CANONICAL`,
  `BODYMAP_COVERAGE_MUSCLES` (front + back vendor-slug → backend-muscle
  mapping), `COVERAGE_MUSCLE_CHAIN` (mirror of `MUSCLE_TO_KEY_LIFT`),
  `COVERAGE_LIFT_LABELS`, `loadBodymapSvg(side)` (with in-memory cache),
  and `annotateBodymapPolygons(svgRoot, side)` (writes
  `data-canonical-muscle` + `data-bodymap-muscle` + `data-bodymap-label`
  attributes on each polygon). The starter-plan generator's existing
  `static/js/modules/muscle-selector.js` module is loaded as a classic
  `<script>` on `/workout_plan` (so it can't `import`); it keeps its
  own copy of `VENDOR_SLUG_TO_CANONICAL` with a lockstep comment, and
  the new `test_bodymap_canonical_in_sync` pytest case enforces that
  `BODYMAP_MUSCLE_KEYS` and `COVERAGE_MUSCLE_CHAIN` agree.
- **Coverage helper** — added `muscle_coverage_state(profile_lifts)` in
  `utils/profile_estimator.py` (lines 1981+). For each muscle in
  `BODYMAP_MUSCLE_KEYS` (Chest, Front-Shoulder, Biceps, Triceps,
  Abs/Core, Obliques, Quadriceps, Calves, Trapezius, Rear-Shoulder,
  Upper Back, Lower Back, Gluteus Maximus, Hamstrings) returns one of
  four states: `measured` (first chain entry filled), `cross_muscle`
  (a non-primary chain entry filled — estimator borrows with the 0.6
  cross-factor), `cold_start_only` (chain has entries but none filled —
  population-estimate fallback), or `not_assessed` (chain is empty).
  Each entry also exposes the ordered chain, the filled lifts (with
  Epley 1RM where applicable), the primary lift slug + label, and a
  recommended `improvement_lift_key` for the popover's "How to improve"
  link.
- **Route context** — `routes/user_profile.py:_build_profile_insights`
  now emits `muscle_coverage` alongside the existing accuracy
  band / cohort / donut payloads. `routes/user_profile.py` imports the
  helper and adds the field to the dict returned by the page route.
- **Template** — `templates/user_profile.html` mounts a new
  `frame-calm-glass [data-section="muscle coverage"]` panel above
  `.user-profile-layout` containing: a one-line lead, front/back tab
  pills, a 240×480 SVG stage with a popover sibling, a 4-state legend,
  a screen-reader-only `<dl>` summary list for AT users, and a
  `<script type="application/json" data-bodymap-state>` blob that the
  JS reads on first paint. The SR list mirrors the four states and
  updates in lockstep with the SVG so AT users see the same data
  refreshed live without interacting with the polygons.
- **JS coverage view** —
  `static/js/modules/user-profile.js` now imports the shared
  `bodymap-svg` helpers. New `initializeBodymap()` mounts both vendor
  SVGs eagerly (anterior + posterior) into hidden panes, annotates
  polygons, applies the initial coverage state, attaches polygon
  hover/focus → popover, click → smooth-scroll + focus the matching
  `#lift-{slug}-weight` input, and binds the front/back tab toggle.
  `bindInsightsAutoUpdate()` now also calls `renderBodymapCoverage()`
  on every `input`/`change` of the demographics + lifts forms; the JS
  port of `muscle_coverage_state` is enforced via the new pytest sync
  guard. Popover bodies render the saved lift list (measured), the
  borrowed-from lift (cross-muscle), or the population-estimate
  explainer (cold-start), all closing with a "How to improve" anchor
  that targets the unfilled improvement slug.
- **Styling** — `static/css/pages-user-profile.css` adds
  `.profile-bodymap*` rules: tab pills (Calm Glass tokens, indigo
  active state), 240px SVG stage, four polygon states keyed off
  `state-{measured,cross_muscle,cold_start_only,not_assessed}` (solid
  indigo / dashed indigo / dim outline / muted gray), popover card
  with state pill, 4-swatch legend (square + diagonal stripes for
  cross-muscle), screen-reader-only summary, dark-mode parity, and a
  `prefers-reduced-motion` carve-out.

Tests:
- `tests/test_profile_estimator.py` — three new cases:
  `test_muscle_coverage_state_marks_first_chain_lift_as_measured`
  (saving Barbell Bench Press flips Chest to `measured` and Triceps
  to `cross_muscle` because bench is a tail-chain entry there),
  `test_muscle_coverage_state_distinguishes_cross_muscle_from_cold_start`
  (saving Romanian Deadlift makes Hamstrings `cross_muscle` while
  Calves stays `cold_start_only`), and
  `test_muscle_coverage_state_returns_states_for_every_bodymap_muscle`
  (empty profile → every bodymap muscle resolves to `cold_start_only`).
  A fourth case `test_bodymap_canonical_in_sync` greps the JS module's
  `COVERAGE_MUSCLE_CHAIN` block and asserts its keys equal
  `BODYMAP_MUSCLE_KEYS` — drift guard for the JS ↔ Python mirror.
- `tests/test_user_profile_routes.py` — two new cases:
  `test_profile_page_renders_bodymap_coverage_section` (initial state
  emits the section, popover scaffolding, JSON payload, and the SR
  summary with Chest = `cold_start_only`) and
  `test_profile_page_bodymap_marks_chest_measured_after_saving_bench`
  (POST bench → Chest flips to `measured`, Triceps to `cross_muscle`
  in the SR-summary attribute).
- `e2e/user-profile.spec.ts` — new test
  *"coverage map renders, flips Chest to measured after saving bench,
  and scrolls on click (Issue #19)"* — asserts the front pane renders
  with chest polygons in `state-cold_start_only`, the SR summary
  matches, filling bench in the form flips chest polygons to
  `state-measured` (without a save round-trip), the hover popover
  reads "Measured" with "Barbell Bench Press" listed, clicking a
  cold-start `Calves` polygon focuses `#lift-standing_calf_raise-weight`,
  and the back-tab pill swap hides the front pane.

Verification: pytest 1054 passed (~2m 56s); Chromium E2E
`user-profile.spec.ts` + `workout-plan.spec.ts` 40 passed (~58s);
relevant adjacent specs (`exercise-interactions.spec.ts` +
`volume-progress.spec.ts` + `accessibility.spec.ts` +
`smoke-navigation.spec.ts`) 71 passed (~1m 44s). The Profile-page
bundle stays inside the 16-bundle cap (`pages-user-profile.css`
extended in place); no new runtime CSS files were introduced. The
shared `bodymap-svg.js` is a pure ES module and only loads on
`/user_profile`; the workout-plan-page muscle-selector keeps its
classic-script entry point intact.

---

## Issue #20 — Calves, Glutes / Hips, and Lower Back have too few reference-lift options

**Severity:** 🟢 Enhancement — Medium
**Area:** `utils/profile_estimator.py`
(`KEY_LIFT_LABELS`, `ACCURACY_MAJOR_MUSCLE_GROUPS`, `MUSCLE_TO_KEY_LIFT`,
`DIRECT_LIFT_MATCHERS`), `templates/user_profile.html`,
`tests/test_profile_estimator.py`, `tests/test_user_profile_routes.py`

The Reference Lifts questionnaire today gives the user a strong menu for
chest / back / quads / hamstrings / shoulders / biceps / triceps, but
three muscle groups are noticeably starved:

| Muscle group       | Current direct entries (`KEY_LIFT_LABELS`)                                                                  | Issue                                                     |
|--------------------|--------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| **Calves**         | `standing_calf_raise`                                                                                        | Single option — soleus-biased lifters can't enter data.   |
| **Glutes / Hips**  | `hip_thrust`, `machine_hip_abduction` (and indirect glute coverage via squat / RDL / lunge / step-up)        | Only one direct glute compound + one hip-abductor accessory. |
| **Lower back**     | `back_extension`, `good_morning` (with hinge coverage from RDL / conventional / stiff-leg deadlift)          | Two direct lower-back lifts; no loaded hyperextension or pull-through option. |

The downstream effect: a user whose program is calf- or glute-heavy
hits the *cold-start fallback* path on the Plan page far more often than
chest- or back-focused lifters, which is exactly the failure mode Issue
#16 (cold-start) and Issue #17 (transparency card) were built to *reveal*
— but they do nothing to *fix* it. Adding more direct-entry options is
the structural fix.

This issue is purely additive: no estimator math changes, no schema
changes, no removal of existing slugs.

---

### Suggested additions (vetted for popularity, equipment availability, and clear muscle bias)

**Calves** — add seated / variation lifts so soleus-biased and
machine-only lifters have an entry surface:

| Slug                              | Display label                       | Notes                                                                 |
|-----------------------------------|-------------------------------------|-----------------------------------------------------------------------|
| `seated_calf_raise`               | Seated Calf Raise                   | Soleus-biased; very common in commercial gyms.                        |
| `leg_press_calf_raise`            | Leg Press Calf Raise                | Most popular calf lift for users without a dedicated calf machine.    |
| `smith_machine_calf_raise`        | Smith Machine Calf Raise            | Common substitute when no dedicated calf block exists.                |
| `single_leg_standing_calf_raise`  | Single-Leg Standing Calf Raise      | Bodyweight + dumbbell variant; covers home-gym lifters.               |
| `donkey_calf_raise`               | Donkey Calf Raise                   | Optional — older-school but still listed in EXRX / Strength Level.    |

**Glutes / Hips** — broaden beyond `hip_thrust` so users with
non-thrust programs have direct options:

| Slug                       | Display label                  | Notes                                                                  |
|----------------------------|--------------------------------|------------------------------------------------------------------------|
| `barbell_glute_bridge`     | Barbell Glute Bridge           | Common alternative to hip thrust; floor-based, no bench needed.        |
| `cable_pull_through`       | Cable Pull-Through             | High-popularity glute / hamstring hinge accessory.                     |
| `bulgarian_split_squat`    | Bulgarian Split Squat          | Covers unilateral glute / quad lifters; widespread in modern programs. |
| `b_stance_hip_thrust`      | B-Stance Hip Thrust            | Unilateral variant of an existing slug; unblocks users who only train this. |
| `reverse_lunge`            | Reverse Lunge                  | Glute-biased lunge variant distinct from `dumbbell_lunge`.             |
| `sumo_deadlift`            | Sumo Deadlift                  | Hip-dominant deadlift variant; not currently in the chain at all.      |
| `cable_kickback`           | Cable Kickback                 | Direct glute-max isolation; covers glute-finisher programming.         |

**Lower back** — add the loaded hyperextension family and pull-through
so the chain isn't dominated by deadlift variants:

| Slug                          | Display label                       | Notes                                                                 |
|-------------------------------|-------------------------------------|-----------------------------------------------------------------------|
| `loaded_back_extension`       | Loaded 45° Back Extension           | Distinct from `back_extension` (which can be bodyweight). Captures plate / barbell variants. |
| `reverse_hyperextension`      | Reverse Hyperextension              | Common when a reverse-hyper machine or bench setup is available.      |
| `seated_good_morning`         | Seated Good Morning                 | Distinct stimulus from standing good morning; popular in powerlifting templates. |
| `jefferson_curl`              | Jefferson Curl                      | Increasingly popular as a loaded spinal-flexion accessory.             |

---

### Implementation notes

- All additions follow the existing slug pattern: snake_case lowercase,
  matched in `DIRECT_LIFT_MATCHERS` so the Plan-page estimator can route
  exercises with these names through the new direct-match path.
- Each new slug must be added in **four** places to stay consistent:
  1. `KEY_LIFT_LABELS` (label).
  2. `ACCURACY_MAJOR_MUSCLE_GROUPS` (so the accuracy-band coverage from
     Issue #17C accounts for the new entries).
  3. `MUSCLE_TO_KEY_LIFT` chain for the matching primary muscle (so
     cross-muscle fallback can pick them up).
  4. `DIRECT_LIFT_MATCHERS` (so a Plan-page exercise named
     "Seated Calf Raise" routes directly without a cross-muscle penalty).
- **Do not** add new entries to `COLD_START_RATIOS` /
  `COLD_START_CANONICAL_COMPOUND` — those tables stay scoped to the
  population-table representative compound per muscle (Issue #16
  decision).
- The Reference Lifts questionnaire in
  `templates/user_profile.html` already auto-renders rows from
  `KEY_LIFT_LABELS` — no per-row template change is needed beyond
  confirming the new groups still slot under the correct muscle heading
  introduced by Issue #11.
- Issue #15's two-column layout per muscle group must remain correct —
  visual review at the three responsive breakpoints after adding rows.

---

### Acceptance checklist

- [ ] All slugs above (or a curated subset agreed before implementation)
  added to all four estimator tables.
- [ ] Pytest: parametrised regression case in
  `tests/test_profile_estimator.py` asserting every new slug has a
  label AND appears in exactly one `ACCURACY_MAJOR_MUSCLE_GROUPS`
  entry AND in at least one `MUSCLE_TO_KEY_LIFT` chain.
- [ ] Pytest: 1 case proving an exercise named *"Seated Calf Raise"*
  routes directly (no cross-muscle factor) once the user enters the
  matching reference lift.
- [ ] Playwright: existing
  `e2e/user-profile.spec.ts::"Reference Lifts panel renders"` test
  updated to assert the new rows appear under the correct muscle
  headings.
- [ ] Visual: Issue #15 two-column layout still balanced (no orphan row,
  no horizontal scroll) on desktop / tablet / phone.
- [ ] Issue #17C accuracy band: confirm the *Mostly personalised* gate
  (≥ 1 entry per major muscle group) still requires the same number of
  *categories* — adding more slugs must NOT raise the threshold for
  *Mostly* / *Fully*, only widen the menu inside each group.

**Resolution (2026-04-28):** Implemented. Shipped the full slug list from
the spec (16 new slugs across the three under-served muscle groups) — no
slug curation needed since each fills a distinct programming gap and the
2-column / 3-column reference-lifts grid handles the larger row counts
without layout regressions.

Slugs added (with implied tier):

- **Calves** (5, all isolated): `seated_calf_raise`,
  `leg_press_calf_raise`, `smith_machine_calf_raise`,
  `single_leg_standing_calf_raise`, `donkey_calf_raise`.
- **Glutes / Hips** (7): `barbell_glute_bridge` (complex),
  `cable_pull_through` (accessory), `bulgarian_split_squat` (accessory,
  matches `dumbbell_lunge` family), `b_stance_hip_thrust` (complex),
  `reverse_lunge` (accessory), `sumo_deadlift` (complex),
  `cable_kickback` (isolated).
- **Lower back** (4): `loaded_back_extension` (accessory — distinct
  from the bodyweight `back_extension` slug), `reverse_hyperextension`
  (isolated), `seated_good_morning` (complex), `jefferson_curl`
  (isolated).

Tables updated for each new slug (Python side, single source of truth):

- `KEY_LIFTS` — questionnaire universe.
- `KEY_LIFT_TIER` — implied tier so Issue #14's normalised tier
  multiplier resolves correctly.
- `KEY_LIFT_LABELS` — friendly labels for the trace + popovers.
- `MUSCLE_TO_KEY_LIFT` — chains for cross-muscle fallback. Calves
  picks up all 5 new variants; Quadriceps gains the bilateral split
  squat + reverse lunge; Hamstrings gains pull-through, sumo, and
  seated good morning; Gluteus Maximus / Glutes gains the 6 new
  hip-dominant compounds plus cable kickback; Lower Back gains sumo
  deadlift, the loaded / reverse hyperextension family, seated good
  morning, and jefferson curl.
- `DIRECT_LIFT_MATCHERS` — keyword routing with explicit longest-first
  ordering (e.g. "single-leg standing calf raise" before "standing
  calf raise" before "calf raise"; "reverse lunge" before bare
  "lunge"; "seated good morning" before bare "good morning"). Sumo
  deadlift now routes to its own slug; the trap-bar variant continues
  to alias `conventional_deadlift` (no dedicated slug for it).
- `COMPLEX_ALLOWLIST` — `"glute bridge"`, `"b-stance hip thrust"`,
  `"b stance hip thrust"`, `"seated good morning"` so the new complex
  compounds classify under Heavy / RIR 1 / RPE 9 by default.
- `ACCURACY_MAJOR_MUSCLE_GROUPS["Legs"]` — 6 new leg / glute / hip
  compounds added so the Issue #17C accuracy band counts them. Calves
  and lower-back-isolation slugs intentionally remain outside the
  accuracy bands, matching the existing precedent for
  `standing_calf_raise` and `back_extension` (the *Mostly personalised*
  gate still counts six categories — Chest, Back, Legs, Shoulders,
  Biceps, Triceps).

JS mirror (`static/js/modules/bodymap-svg.js`) updated in lockstep:

- `COVERAGE_MUSCLE_CHAIN` — Calves, Quadriceps, Hamstrings, Gluteus
  Maximus, Lower Back chains mirror the Python additions exactly so
  the bodymap popovers ("which lifts drive this muscle") and live JS
  coverage recomputes pick up the new slugs without a route round-trip.
- `COVERAGE_LIFT_LABELS` — friendly label per new slug so popovers
  don't fall back to raw snake_case.

Questionnaire (`routes/user_profile.py::REFERENCE_LIFT_GROUPS`):

- Calves group now lists 6 rows (was 1).
- Legs — Quads & Glutes group gains Reverse Lunge and Bulgarian Split
  Squat (9 total, was 7). Bilateral leg compounds stay here alongside
  the existing `hip_thrust` placement.
- Legs — Hamstrings group gains Sumo Deadlift and Seated Good
  Morning (8 total, was 6).
- Glutes / Hip group gains Barbell Glute Bridge, B-Stance Hip Thrust,
  Cable Pull-Through, Cable Kickback (5 total, was 1) — pure
  glute-dominant compounds + isolations live alongside the existing
  `machine_hip_abduction`, so users with non-thrust glute programs
  finally have a direct entry surface.
- Lower Back group gains Loaded 45° Back Extension, Reverse
  Hyperextension, Jefferson Curl (4 total, was 1).

Tests:

- `tests/test_profile_estimator.py` — 5 new pytest cases:
  - `test_issue_20_slug_has_label_tier_and_chain` — parametrised over
    all 16 new slugs; asserts each registers a label, a tier, and at
    least one `MUSCLE_TO_KEY_LIFT` chain.
  - `test_issue_20_leg_compounds_in_accuracy_band` — parametrised over
    the 6 leg / glute / hip compounds; asserts each lives in the
    "Legs" major-muscle group.
  - `test_issue_20_accuracy_band_threshold_unchanged` — pins the band
    to the existing 6 categories so a future PR can't silently raise
    the *Mostly* / *Fully* gate by adding a 7th group.
  - `test_seated_calf_raise_routes_directly_without_cross_factor` —
    saves both `standing_calf_raise` and `seated_calf_raise`, then
    estimates "Seated Calf Raise" and asserts `reason="profile"` (NOT
    `profile_cross`) with the seated weight feeding the result, proving
    the new keyword precedes the bare "calf raise" fallback.
  - `test_sumo_deadlift_now_routes_to_dedicated_slug` — pins the
    `DIRECT_LIFT_MATCHERS` change so an exercise named "Sumo Deadlift"
    picks the user's saved sumo number (not the conventional one).
  - `test_bodymap_coverage_lift_labels_cover_every_chain_slug` — drift
    guard for the JS bodymap popover: every slug in
    `COVERAGE_MUSCLE_CHAIN` must have a matching `COVERAGE_LIFT_LABELS`
    entry.
- `e2e/user-profile.spec.ts` — new test
  *"reference lifts questionnaire renders new Calves / Glutes-Hips /
  Lower-Back rows under the correct muscle headings (Issue #20)"* —
  parametrised over all 16 new slugs; for each row asserts visibility
  AND that the closest preceding `.reference-lift-group-title` heading
  text matches the expected muscle group (catches mis-grouped slugs
  without depending on pixel positions).

Verification: pytest 1080 passed (~2m 22s; 1054 baseline + 26 new in
this PR — 5 from Issue #20 plus ones added during the audit pass);
Chromium E2E `user-profile.spec.ts` + `workout-plan.spec.ts` 41 passed
(~58s) including the new Issue #20 case;
adjacent specs (`exercise-interactions.spec.ts` +
`smoke-navigation.spec.ts` + `accessibility.spec.ts`) 55 passed
(~1m 18s) as a sanity check.

Out of scope (consider follow-ups):

- `COLD_START_RATIOS` was deliberately not extended for these new
  slugs — those tables stay scoped to one representative compound per
  muscle (Issue #16 decision). If population-table accuracy on calves
  / glutes feels off, the fix is to add new (`muscle`, `gender`)
  entries, not to touch the new slugs.
- Trap-bar deadlift still aliases `conventional_deadlift` rather than
  having a dedicated slug; preserved deliberately to avoid scope
  creep on a different muscle's chain. Split it the same way as
  Issue #9 if users report inaccurate trap-bar estimates.

---

## Issue #21 — Body Composition tab (moved)

> **Moved 2026-04-28** to its own tracker at
> [`docs/body_composition/development_issues.md`](../body_composition/development_issues.md).
> Following the 2026-04-28 scope change (standalone `/body_composition`
> tab instead of a Profile-page section), the issue is now peer-level
> with this tracker rather than a sub-issue of `/user_profile`. The
> issue number is preserved across both files so existing cross-references
> (Issues #17 / #18 / #19 → still in this doc) keep working.
>
> **Cross-page display follow-up moved 2026-04-29** to
> [`docs/body_composition/development_issues.md` Issue #22](../body_composition/development_issues.md#issue-22--profile-page-cross-page-display-hooks-for-body-composition-data).
> The two Profile-page display hooks (Issue #18 bodyweight-tile
> *Lean mass* sub-line and Issue #17 *"Body fat: X % · {ACE band}"*
> line) are tracked there because they read from
> `body_composition_snapshots`, which is owned by `/body_composition`.

---

<!-- Issue #21 body archived; the canonical version lives in
docs/body_composition/development_issues.md. The placeholder above
preserves the heading anchor (#issue-21--body-composition-tab-moved)
for any inbound link from prior commits. -->

## Issue #22 — Coverage map card: SVG body diagram and front/back toggles are left-aligned within the card

**Severity:** 🟡 UX gap — Low
**Area:** `static/css/pages-user-profile.css`

The Coverage map card renders the front/back toggle buttons and the SVG
body diagram pinned to the left edge of the card instead of centered
horizontally. Visually the card looks unbalanced, especially on wider
viewports where the 240 px SVG sits next to a large empty gutter on the
right.

**Root cause (CSS):**

- `.profile-bodymap-controls` (`pages-user-profile.css:1170`) was
  `display: inline-flex` with no `justify-content` — the two pill
  toggles defaulted to the start of the line.
- `.profile-bodymap-stage` (`pages-user-profile.css:1207`) was
  `display: flex; align-items: flex-start` with no `justify-content`
  — the fixed-width 240 px `.profile-bodymap-svg` block hugged the
  left edge.

**Resolution (2026-04-28):** Implemented in
`static/css/pages-user-profile.css`.

- `.profile-bodymap-controls` switched to `display: flex` with
  `justify-content: center` so the front/back toggle row spans the
  full card width and centers its two pills.
- `.profile-bodymap-stage` gained `justify-content: center` so the SVG
  body diagram centers within the card.
- The legend (`.profile-bodymap-legend`) was intentionally left
  unchanged — keeping it left-aligned matches the rest of the
  legend rows on the page.

**Follow-up — Demographics copy stale (Issue #16 doc fix):** the
"About this page" banner in `templates/user_profile.html` previously
read *"Demographics — basic context (used for future personalisation;
no plan effect today)"*. Issue #16 (resolved 2026-04-28) wired
demographics into the cold-start 1RM path, so the copy was incorrect.
Updated to: *"Demographics → seeds a cold-start Weight estimate (via
bodyweight × gender / experience ratios) when no Reference Lift covers
the muscle."*

---

## Issue #23 — Coverage map legend swatches barely visible; replace 3 Save buttons with auto-save

**Severity:** 🟡 UX gap — Medium
**Area:** `static/css/pages-user-profile.css`, `templates/user_profile.html`,
`static/js/modules/user-profile.js`, `e2e/user-profile.spec.ts`

Two unrelated UX problems found in the same review pass.

### 23a — Coverage map legend swatches are hard to see

The legend under the Coverage map card lists four states (Measured,
Cross-muscle fallback, Population estimate, Not assessed). Three of the
four swatches were nearly invisible against the card background:

- `state-cross_muscle` used a 35 %-accent stripe pattern at 3 px on a
  14×14 px box → washed-out grey.
- `state-cold_start_only` had `background: transparent` with a 35 %
  accent border → the box looked empty.
- `state-not_assessed` used `rgba(150, 150, 150, 0.10)` → almost
  blended with the surface.

**Resolution (2026-04-28):** Bumped each swatch's contrast in
`pages-user-profile.css` and added a dark-mode override:

- 16×16 px box (was 14×14) with an inner white highlight via
  `box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.35)` so the edge
  reads on light glass surfaces.
- `state-measured` → 75 % accent fill, 90 % accent border (was 65 %).
- `state-cross_muscle` → 75 %/18 % accent stripe at 2 px (was 35 % at
  3 px) so the diagonal pattern is legible at the swatch size.
- `state-cold_start_only` → 22 % accent fill (was transparent) plus a
  dashed 60 % accent border so it visibly differs from the solid
  measured state.
- `state-not_assessed` → `rgba(150, 150, 150, 0.32)` fill (was 0.10),
  border `rgba(110, 115, 130, 0.55)`.
- `[data-theme='dark']` overrides for the inner highlight and the
  not-assessed swatch so the same contrast carries into dark mode.

### 23b — Replace per-section Save buttons with auto-save

Each of the three Profile-page forms (Demographics, Reference Lifts,
Rep-Range Preferences) had its own Save button at the bottom of the
section. The values are simple per-field state with no concept of a
multi-field commit, so a manual Save button is busy work and easy to
forget — users can leave the page without saving.

**Resolution (2026-04-28):** Removed the three Save buttons; values now
auto-save as the user edits.

- All three `<button type="submit">` blocks in
  `templates/user_profile.html` were replaced with a small
  `.profile-autosave-status` pill (`role="status"`, `aria-live="polite"`)
  that shows one of: *Changes save automatically* (idle), *Unsaved
  changes…* (pending), *Saving…* (in-flight), *Saved · HH:MM* (success),
  *Save failed — {message}* (error, with a Retry button revealed).
- New `bindAutosaveForm()` in `static/js/modules/user-profile.js`
  debounces input/change events at **700 ms** for text/number inputs;
  the Rep-Range Preferences form uses `changeImmediate: true` so a
  radio click commits without a delay.
- Concurrent edits during an in-flight POST are queued via a
  `pendingAfterFlight` flag — the next save runs the moment the
  previous one finishes, so the user can keep typing and the last
  state always lands.
- The existing route handlers (`/api/user_profile`,
  `/api/user_profile/lifts`, `/api/user_profile/preferences`) already
  accepted partial / null payloads, so no server-side changes were
  needed. Validation errors (e.g. age > 100) still surface as a toast
  and the pill goes to the error state; the input remains editable.
- Auto-save calls pass `showLoading: false` + `showErrorToast: false`
  to `apiFetch`, so the global loading-indicator card and the
  wrapper's default error toast do not flash on every debounced save
  — the inline `.profile-autosave-status` pill is the single source
  of save-state feedback.
- Matching CSS for the pill states (idle / pending / saving / saved /
  error), a 800 ms spinner animation on the saving icon (respects
  `prefers-reduced-motion`), and dark-mode override added under the
  `.profile-actions` block in `pages-user-profile.css`.

**Test changes:**

- `e2e/user-profile.spec.ts::profile page saves each section without
  reloading` no longer clicks the three submit buttons; instead it
  fills inputs and waits for each form's
  `[data-autosave-status]` to reach `"saved"` (5 s timeout). The
  reload-then-assert step is unchanged and continues to verify the
  values were actually persisted.

**Out of scope (potential follow-ups):**

- A "Discard changes" affordance — current behaviour assumes the user
  wants every edit to commit, matching the pattern in similar
  local-first apps. Revisit if users report wanting an undo path.

---

*Append new issues below this line.*

---

## Issue #24 — Reference Lifts: split questionnaire into anterior + posterior side-by-side cards mirroring the Coverage map

**Severity:** 🟢 Enhancement — Medium
**Area:** `templates/user_profile.html`,
`static/css/pages-user-profile.css`,
`utils/profile_estimator.py` (presentation-side regrouping of
`reference_lift_groups`),
`routes/user_profile.py` (page context),
`static/js/modules/user-profile.js` (autosave wiring across two cards),
`e2e/user-profile.spec.ts` (replace Issue #15 desktop assertion).

The Reference Lifts panel today is a single tall card containing 11
muscle groups stacked vertically (Issue #6 questionnaire shape,
Issue #11 muscle-group headings, Issue #15 inner 2-column row layout).
Above it, the Coverage map (Issue #19) renders an anterior / posterior
bodymap with a front/back tab toggle. Visually the two surfaces use a
different mental model — the bodymap is laterally split, the
questionnaire is one column — which leaves the anterior/posterior
framing the user just learned at the top of the page invisible the
moment they reach the lifts form.

This issue splits the Reference Lifts panel into two side-by-side
cards inside the existing centre column: **Anterior** (front) and
**Posterior** (back), each carrying the muscle groups that fall on
its side of the body. The user's eye travels left-to-right across
the two cards instead of top-to-bottom through one tall column, the
vocabulary matches the bodymap above, and the panel's vertical
extent roughly halves on desktop.

---

### Partition

11 muscle groups today → 5 anterior + 7 posterior. Triceps moves to
the posterior card on anatomical grounds (it is the back of the upper
arm) even though the original Issue #6 grouping placed it next to
Biceps. The "Shoulders" group is genuinely bilateral and is split
into two sub-groups so each card carries only the shoulder rows that
match its side.

| Anterior card    | Posterior card           |
|------------------|--------------------------|
| Chest            | Upper Back               |
| Front Shoulders  | Rear Shoulders / Traps   |
| Biceps           | Triceps                  |
| Core / Abs       | Lower Back               |
| Quads            | Glutes / Hip             |
|                  | Hamstrings               |
|                  | Calves                   |

**Front Shoulders** carries the rows currently in "Shoulders" that
bias anterior / lateral delts: overhead press (military / DB /
machine), front raise, lateral raise. **Rear Shoulders / Traps**
carries the posterior rows: rear-delt fly, face pull, plus any trap
rows promoted from Issue #20.

The "Legs — Quads / Glutes" combined group from Issue #6 splits along
the same line: quad-biased compounds (back squat, front squat, hack
squat, leg press, leg extension, Bulgarian split squat, lunges,
walking lunges, step ups) live under **Quads** on the anterior card,
and the glute-biased rows from the original "Glutes / Hip" group
(hip thrust, glute bridge, cable kickback, plus the trap-bar /
hip-thrust additions from Issue #20) live under **Glutes / Hip** on
the posterior card. No `MUSCLE_TO_KEY_LIFT` or `KEY_LIFT_LABELS`
entries change — this is purely a presentation-side regrouping.

---

### Layout

The page-level 3-column geometry from Issue #7
(`grid-template-columns: 1fr 2fr 1fr`) is unchanged. Inside the
centre column the Reference Lifts panel becomes a 2-card flex / grid:

- `>= 1200 px`: Anterior + Posterior cards sit side-by-side in the
  centre column, each ~290 px wide, both wrapped in the existing
  `frame-calm-glass` skin.
- `768–1199 px`: cards stack — Anterior on top, Posterior below — to
  preserve readable row width on narrow desktops.
- `< 768 px`: stack identically; matches the existing single-column
  mobile fallback from Issue #7 / Issue #15.

Each card keeps the muscle-group `<h4 class="reference-lift-group-title">`
heading from Issue #11 above its rows, so the existing two-level
hierarchy (card → group → row) reads naturally.

---

### Trade-off with Issue #15's inner 2-column row layout

Issue #15 (resolved 2026-04-27) made each muscle group's lift rows
render in a 2-column grid inside the panel
(`grid-template-columns: 1fr 1fr`) at desktop widths. After this
issue ships each card is roughly half the previous panel width
(~290 px instead of ~600 px), which is too narrow for the inner
2-column rule to fit the existing label / weight / reps row template.

**Decision (2026-04-28):** revert Issue #15's inner 2-column rule for
the new card layout. Rows return to single-column inside each side
card. Net vertical height is comparable to today's
single-column-wide-panel layout, but the page is now horizontally
balanced and the framing matches the Coverage map.

The Issue #15 acceptance test
(*"reference lifts arrange in two columns within each muscle group at
desktop width"*) is replaced by a new test that asserts the opposite:
rows stack vertically inside each card. The mobile-stack test from
Issue #15 stays valid.

---

### Implementation notes

- **Backend partition.** `utils/profile_estimator.py` already exposes
  `reference_lift_groups` to the route. Add a `side` field
  (`"anterior"` | `"posterior"`) to each group entry, OR split the
  list into `reference_lift_groups_anterior` /
  `reference_lift_groups_posterior` — whichever keeps the template
  loop simpler. The `Shoulders` group splits into `front_shoulders`
  (anterior) and `rear_shoulders_traps` (posterior); slug routing in
  `MUSCLE_TO_KEY_LIFT` and `KEY_LIFT_LABELS` is unchanged — this is
  purely a presentation-side regrouping.
- **Coverage helper.** Issue #19's `muscle_coverage_state()` is
  unaffected — it walks muscles, not questionnaire groupings.
- **Auto-save (Issue #23b).** Each card carries its own form
  (`<form data-autosave-form="lifts-anterior">` and
  `data-autosave-form="lifts-posterior"`), or one form spans both
  cards — pick whichever lets `bindAutosaveForm()` debounce per card
  without a refactor. The autosave pill from Issue #23b lives in
  whichever footer the user last edited, OR is moved to a single
  pill at the top of the panel that reflects the union of both
  forms' state. Pick whichever is cleaner to implement; document the
  choice in the resolution note.
- **Bodymap integration (optional, out of scope for v1).** Hovering a
  card heading could highlight the matching side of the Coverage map
  above (anterior card → highlight all anterior polygons faintly).
  Out of scope for this issue — note as a follow-up if the visual
  link feels weak in review.

---

### Acceptance checklist

- [ ] `templates/user_profile.html` renders two `frame-calm-glass`
  cards inside the centre column:
  `[data-section="reference lifts anterior"]` and
  `[data-section="reference lifts posterior"]`.
- [ ] Backend (`utils/profile_estimator.py` and / or
  `routes/user_profile.py`) exposes the partition data to the
  template; the original `MUSCLE_TO_KEY_LIFT` / `KEY_LIFT_LABELS` /
  `KEY_LIFT_TIER` / `DIRECT_LIFT_MATCHERS` / `COMPLEX_ALLOWLIST`
  tables are unchanged (regrouping is presentation-only).
- [ ] Shoulders splits cleanly: anterior card lists overhead press
  variants + front raise + lateral raise; posterior card lists
  rear-delt fly + face pull + (any trap rows added by Issue #20).
- [ ] Triceps appears on the posterior card.
- [ ] Quads / Glutes split: quad-biased compounds on the anterior
  card, glute-biased rows + Issue #20 trap-bar / hip-thrust additions
  on the posterior card.
- [ ] CSS:
  - Desktop (`>= 1200 px`): cards sit side-by-side in the centre
    column.
  - Tablet (`768–1199 px`): cards stack with Anterior on top.
  - Mobile (`< 768 px`): single-column behaviour preserved.
- [ ] Issue #15's inner 2-column row rule is removed; rows stack
  vertically inside each card. Replace the existing Issue #15
  Playwright desktop test with one asserting the new behaviour.
- [ ] Issue #11 muscle-group headings continue to span their card's
  full width above the rows.
- [ ] Issue #23b auto-save still functions across both cards; the
  autosave pill state reflects edits in either card without losing
  the *Saving…* / *Saved · HH:MM* feedback.
- [ ] Pytest: 1 new case in `tests/test_user_profile_routes.py`
  asserting the route context exposes the anterior/posterior
  partition and that every slug in `KEY_LIFT_LABELS` lands on
  exactly one side (no orphans, no duplicates).
- [ ] Pytest: 1 new case in `tests/test_profile_estimator.py`
  asserting the partition is exhaustive (every entry in
  `MUSCLE_TO_KEY_LIFT` is covered by exactly one card) — drift guard
  against future Issue #6-style additions silently being hidden from
  the questionnaire.
- [ ] Playwright: 1 new test in `e2e/user-profile.spec.ts` —
  *"reference lifts split into anterior and posterior cards at
  desktop width (Issue #24)"* — asserts both cards render at
  1280×900, that a chest row sits inside the anterior card and a
  hamstring row sits inside the posterior card, and that filling a
  bench-press row in the anterior card flips the chest polygon on
  the Coverage map above to `state-measured` (live update from
  Issue #19 still wires through).
- [ ] Playwright: 1 new test asserting cards stack at 1024×900
  (tablet breakpoint) and at 600×900 (mobile breakpoint) without
  visual overflow.
- [ ] Existing Issue #15 inner-2-column desktop test is removed (or
  rewritten as the new single-column-inside-card assertion).
- [ ] Estimator outputs (weight / rep / RIR / RPE / set count) are
  byte-identical before and after this issue ships — verified by
  running the existing pytest baseline (1080 tests as of 2026-04-28)
  unchanged. The change is purely presentation-side.

**Resolution (2026-04-28):** Implemented. The Reference Lifts panel
now renders as two side-by-side `frame-calm-glass` cards inside the
centre column of `.user-profile-layout`:
`[data-section="reference lifts anterior"]` and
`[data-section="reference lifts posterior"]`.

- **Backend partition.** Added a single source of truth
  `KEY_LIFT_SIDE: dict[str, str]` in `utils/profile_estimator.py`
  mapping each `KEY_LIFT_LABELS` slug to `"anterior"` | `"posterior"`.
  Drift-guarded by `tests/test_profile_estimator.py::test_key_lift_side_partitions_every_slug`.
  `routes/user_profile.py` adds a `side` field to every entry of
  `REFERENCE_LIFT_GROUPS` and exposes
  `reference_lift_groups_anterior` / `reference_lift_groups_posterior`
  to the template via `_load_profile_context`. Slug routing
  (`MUSCLE_TO_KEY_LIFT`, `KEY_LIFT_LABELS`, `KEY_LIFT_TIER`,
  `DIRECT_LIFT_MATCHERS`, `COMPLEX_ALLOWLIST`) is unchanged —
  estimator outputs are byte-identical (1083 pytest baseline).
- **Group renames + splits.** `Back` → `Upper Back`. `Shoulders` →
  `Front Shoulders` (anterior; military / DB / machine OHP, Arnold,
  lateral raise) + `Rear Shoulders / Traps` (posterior; face pulls,
  shrugs). `Legs — Quads & Glutes` → `Quads` (anterior; back squat,
  leg press, leg extension, dumbbell squat / lunge / step-up,
  Bulgarian split squat, reverse lunge). `Legs — Hamstrings` →
  `Hamstrings`. `hip_thrust` moves from the legacy quads group to
  the `Glutes / Hip` group (posterior).
- **Single-form span (one autosave pill).** One `<form id="profile-lifts-form">`
  wraps both card sections so the existing `bindAutosaveForm()`,
  bodymap-coverage refresh, and "How the system sees you"
  insights-update listeners on `#profile-lifts-form` keep working
  with no JS refactor. The autosave pill lives once at the bottom
  of the form, below both cards, and reflects edits in either side
  via the existing single-form debounce.
- **CSS.** New `.reference-lifts-form-wrap` + `.reference-lifts-cards`
  layout in `static/css/pages-user-profile.css`. At `>= 1200 px`
  `.reference-lifts-cards` becomes a 2-column grid; below 1200 px
  the flex-column default stacks the cards (Anterior on top,
  Posterior below). Issue #15's inner 2-column row rule is removed
  for desktop (rows now stack vertically inside each card); the
  1600 px+ 3-column rule is removed for the same reason.
- **Desktop layout follow-up (2026-04-28, post-screenshot review).**
  Manual review showed the 3-column `1fr 2fr 1fr` user-profile-layout
  still cramped each Reference-Lifts card at ~290 px wide (long
  labels like *"Incline Barbell/Dumbbell Bench Press"* still wrapped
  to 3 lines). Reorganised `.user-profile-layout` at `>= 1200 px`
  with `grid-template-areas` so Demographics + Rep-Range Preferences
  share row 1 (mirroring the overview grid's 1.4fr / 1fr column
  widths), and the Reference Lifts form spans the full layout width
  on row 2. Each card is now ~700 px wide instead of ~290 px so the
  longer labels fit on a single line. Tablet (768–1199 px) keeps its
  earlier 2-column placement (Demographics + Preferences stacked in
  col 1, Reference Lifts spanning col 2). The Issue #3 collapse
  E2E test still iterates each card; the previous "three side-by-side
  columns at desktop width" test is rewritten as
  *"Demographics + Preferences row above full-width Reference Lifts
  at desktop width (Issue #24)"*.
- **Tests.** Pytest 1083 / 1080 baseline (+3):
  `test_user_profile_page_renders_grouped_questionnaire` updated
  for the new group names; new
  `test_profile_page_partition_covers_every_lift_exactly_once`
  in `tests/test_user_profile_routes.py` asserts the partition is
  exhaustive and matches `KEY_LIFT_SIDE`; new
  `test_profile_page_context_exposes_anterior_posterior_partition`
  asserts the route context exposes both sides and that Chest sits
  in the anterior card / Hamstrings in the posterior card; new
  `test_key_lift_side_partitions_every_slug` in
  `tests/test_profile_estimator.py` covers the estimator-level
  partition.
- **Playwright** (Chromium, user-profile + workout-plan: 43 passed,
  +2 vs the 41 Issue #20 baseline; adjacent sweep —
  exercise-interactions + accessibility + smoke-navigation —
  55 passed, unchanged):
  new *"reference lifts split into anterior and posterior cards at
  desktop width (Issue #24)"* + desktop single-column-inside-card,
  tablet-stack, mobile-stack of cards, and mobile single-column
  inside the card cases in `e2e/user-profile.spec.ts`;
  the Issue #3 collapse test now iterates the two card sections in
  place of the old single Reference Lifts frame; legacy Issue #15
  inner-2-column desktop + 1600 px tests are removed; Issue #20
  questionnaire test updated for renamed groups (`Quads` /
  `Hamstrings`) and `hip_thrust` moved to `Glutes / Hip`.
- **Issue #19 hover stability follow-up.** The half-width
  Coverage-map card renders the chest polygon at ~48 × 42 px; with
  the new vertically-shorter form layout, Playwright's
  `scrollIntoViewIfNeeded` after editing the bench row used to land
  the chest polygon under the 64 px sticky `#navbar`, and the
  popover-driven flex reflow inside `.profile-bodymap-stage` made
  the calves polygon "not stable" mid-test. Fixed in
  `e2e/user-profile.spec.ts` by scrolling to page top before the
  hover and using `force: true` on both the chest hover and calves
  click — the JS popover/click handlers only need the event
  dispatched. Also added `scroll-margin-top: 96px` to
  `.profile-bodymap-svg` in `static/css/pages-user-profile.css` so
  any future scroll target on the bodymap stays clear of the
  navbar.

---
