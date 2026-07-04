# Phase 15 — JS: log / filters / dropdowns

Line-by-line read of `static/js/modules/workout-log.js` (818),
`static/js/modules/filter-view-mode.js` (725), `static/js/modules/workout-dropdowns.js`
(646), `static/js/modules/routine-cascade.js` (414), plus `static/js/CLAUDE.md` and
`.claude/rules/frontend.md` for context. Cross-checked against `docs/REFACTOR_PLAN.md`
(WP3.1 Vitest scaffold, WP3.5 raw-fetch migration list), the real `templates/workout_log.html`
markup (to separate live wiring from dead selectors), `static/js/app.js` (import graph +
`window.*` bridge), `static/js/modules/ui-handlers.js` (the file that actually owns
click-to-edit behavior for the log table), `routes/workout_log.py` (server-side validation
surface), and `utils/constants.py` (canonical `MUSCLE_GROUPS`).

---

## static/js/modules/workout-log.js (818 lines)

**Verdict: imported piecemeal into `app.js` (six separate import statements, `app.js:3,14-22`)
and exposes real business logic (`updateScoredValue`, calibration-outcome toasts,
progression-badge math). But a meaningful fraction of the file is either (a) dead —
targets DOM selectors/endpoints that don't exist in the shipped template — or (b) a third,
subtly-wrong copy of duplicated progression logic. No raw `fetch()` anywhere; 100% via
`api` from `fetch-wrapper.js`.** `[CONFIRMS-PLAN]` on the fetch-wrapper discipline (this
file is correctly absent from WP3.5's raw-fetch inventory).

- **`workout-log.js:620-690` — dead code, front-to-back.** `initializeWorkoutLogFilters()`
  wires `change` listeners on `#date-filter`/`#routine-filter`; `filterWorkoutLogs()` then
  POSTs to `/filter_workout_logs` and repaints the table via `updateWorkoutLogTable()`/
  `createWorkoutLogRow()`. Confirmed by reading `templates/workout_log.html` in full: **no
  element with id `date-filter` or `routine-filter` exists anywhere in the template** (the
  `if (dateFilter)`/`if (routineFilter)` guards silently no-op, so nothing crashes — it just
  never runs). Independently confirmed `/filter_workout_logs` **does not exist anywhere in
  `routes/`** — repo-wide grep finds only this one JS call site. So even if the missing
  elements were restored, the endpoint would 404. This is ~70 lines (8.5% of the file) of a
  fully-formed feature (filter dropdowns → API call → row template → delete button wiring)
  that is unreachable in the shipped page. `[RISK]` / `[NEW]` — stronger than a typical
  dead-constant finding (rule 8 in the plan): it's a complete vertical slice (UI hook +
  network call + re-render) with zero live callers, one abandoned non-existent backend
  route, and it was still being called unconditionally-safe (never throws) from
  `initializeWorkoutLogFilters()`, itself called unconditionally from
  `initializeWorkoutLog()` (`:60`) on every page load. Safe to delete `:620-690` plus its
  call site at `:60`.
- **`workout-log.js:595-618` (`initializeEditableCells`) — also dead, same root cause.**
  Targets `.editable-cell` cells with an `input` + `.display-value` pair. The real template
  (`templates/workout_log.html:126-224`) uses class `.editable` (not `.editable-cell`) with
  `.editable-input` + `.editable-text` (not `.display-value`) — confirmed via grep across
  the whole template, zero matches for `editable-cell` or `display-value`. The real
  click-to-edit / blur / Enter / Escape / spinner-button wiring for these cells lives
  entirely in `static/js/modules/ui-handlers.js:96-329` (`initializeUIHandlers`), a
  different module. `initializeEditableCells()` is called unconditionally at
  `initializeWorkoutLog():57` and silently matches zero elements every time. `[RISK]` /
  `[NEW]` — this means **two modules (`workout-log.js` and `ui-handlers.js`) both claim
  ownership of "wire the editable log cells,"** and only one of them (`ui-handlers.js`) is
  actually connected to the real markup. A future editor changing `workout-log.js`'s
  `initializeEditableCells()` expecting it to affect the log page's edit behavior would be
  editing dead code without any signal that it's dead.
- **Real edit flow confirmed, and it double-fires on every scored-value edit.** The real
  wiring for the five scored-value number inputs (`scored_min_reps`, `scored_max_reps`,
  `scored_rir`, `scored_rpe`, `scored_weight`) is a **race between two independent paths**:
  1. `templates/workout_log.html:131,151,172,193,215` — each input carries an inline
     `onchange="updateScoredValue('{{ log.id }}', 'field', this.value)"` that calls
     `workout-log.js:351`'s `updateScoredValue` **immediately** when the native `change`
     event fires (blur-with-changed-value, or a synthetic dispatch).
  2. `ui-handlers.js:219-258` — the same inputs (matched by `.editable-input:not(.date-input)`,
     which includes all five `type="number"` fields) get an `input`-event listener that
     **debounces 500 ms** and then also calls `window.updateScoredValue(logId, fieldName, value)`
     (`ui-handlers.js:253-256`).
  3. `ui-handlers.js:302-308` (Enter-key handler) makes the collision near-certain: on
     Enter it explicitly does `this.dispatchEvent(new Event('change', { bubbles: true }))`
     — which fires path (1)'s inline `onchange` immediately — **and then calls
     `this.blur()`**, while path (2)'s 500 ms debounce timer (started by the keystrokes
     that produced the value) is very likely still pending and will fire `updateScoredValue`
     again with the identical `(logId, field, value)` a few hundred ms later.
  Net effect: a normal "type a value, press Enter (or click away)" edit **posts
  `/update_workout_log` twice** for the same field with the same value. Each POST
  independently re-runs `recompute_calibration_after_log` server-side
  (`routes/workout_log.py:80`) and, client-side, each response triggers
  `notifyCalibrationOutcome()` (`workout-log.js:412-427`) — so the user can see **two
  toast notifications for one edit** (e.g. "Calibration updated..." followed a moment
  later by a duplicate). Not data-corrupting (idempotent same-value write), but real
  duplicate work and a visible double-toast UX bug. `[RISK]` — high confidence, directly
  observable from reading both files' event wiring against the literal template markup;
  not verified in a live browser this phase (no app/test runs per phase rules).
- **`workout-log.js:537-557` (`validateScoredValue`) is real but non-blocking.** Confirmed
  this is the *only* range/type validation for scored values anywhere in the request path —
  `routes/workout_log.py:49-57` (`update_workout_log`) allowlists **field names** only
  (`valid_fields = {"scored_weight", "scored_min_reps", ...}`) and does zero range/type
  checking on the values themselves before the raw `UPDATE ... SET` (`:59-61`). But
  `validateScoredValue` is only ever called from `ui-handlers.js:225` to toggle
  `.is-invalid`/`.is-valid` CSS classes (`ui-handlers.js:226-227`) — **the same `input`
  handler unconditionally proceeds to schedule the debounced `updateScoredValue` save
  regardless of the validation result** (`ui-handlers.js:237-258` runs whether or not
  `isValid` was true at `:225`). So the "only validation in the request path" is purely
  cosmetic: an out-of-range value (e.g. `scored_rir = 99`, `scored_weight = -50`) shows a
  red border but is saved anyway, and the server persists it with no check at all.
  `[CONFIRMS-PLAN]` on "no server-side validation exists" from the backend scan, `[RISK]`
  refinement: the client-side validation that exists doesn't block the write either, so
  there is effectively **no enforcement anywhere** in this path — `validateScoredValue`'s
  ranges (`workout-log.js:544-556`: sets 0–10, reps 0–100, weight 0–1000, RIR 0–5, RPE
  0–10) are display-only guidance.
- **Progression-math triplication, and the third copy is wrong for assisted-bodyweight
  exercises.** The "is this scored value a progression over planned" logic
  (RIR lower-is-better / RPE higher-is-better / reps higher-is-better / weight
  higher-is-better-except-assisted) is implemented **three times**, near-verbatim:
  - `updateScoredValue` (`:388-395`) — correct, calls `isWeightProgression(row, planned_weight, scored_weight)` (`:27-32`), which special-cases `ASSISTED_BODYWEIGHT_EXERCISES` (`:5-12`) so that for assisted machines, a *lower* scored weight (less assistance) counts as progress.
  - `checkProgressiveOverload` (`:580-586`) — correct, same `isWeightProgression()` call.
  - `handleDateChange` (`:801-807`) — **wrong**: uses a bare
    `(scored_weight && planned_weight && scored_weight > planned_weight)` comparison,
    never calling `isWeightProgression()` and never consulting `isAssistedBodyweightRow()`.
    This function fires whenever the user only edits the "Last Progression" date
    (`ui-handlers.js:155-162` → `handleDateChange`), and it independently recomputes and
    repaints the same `.badge` (Achieved/Pending) that `updateScoredValue`/
    `checkProgressiveOverload` also own. For an assisted-bodyweight exercise (e.g. "Machine
    Assisted Pull Up"), editing only the date after a *reduced-assistance* (lower weight)
    scored set will flip the badge to "Pending" here even though the other two code paths
    would correctly call it "Achieved." `[RISK]` — genuine logic-drift bug from
    hand-copy-pasting the same block three times (`:376-395`, `:566-586`, `:788-807` are
    ~90% textually identical) instead of extracting a shared `computeProgressionBadge(row)`
    helper; also uses `parseFloat` for planned/scored weight here (`:793,799`) instead of
    the `parseOptionalNumber()` helper (`:34-37`) the other two copies use, though that
    difference has no behavioral consequence given the `&&` truthiness guards.
- **Two more dead/orphaned exported functions, refining Phase 17's blanket claim.**
  Phase 17 (`docs/scan/PHASE_17.md:130-145`) lists all 21 `app.js` `window.*` assignments as
  existing "to satisfy inline `onclick=...` handlers in templates." Reading this file
  end-to-end plus grepping `templates/` shows that's not true for two of them:
  `updateProgressionStatus` (`workout-log.js:335-349`) and `checkProgressionStatus`
  (`:692-709`) are exported, imported into `app.js` (`:14-16,19-21`), and assigned to
  `window` (`app.js:53,55`), but **zero call sites exist anywhere** — not in
  `templates/workout_log.html`, not in any other JS file, not as an inline `onclick`.
  (`updateProgressionDate` and the `.progression-date`-driven `initializeDateInputs()`
  at `:296-309` are the actually-live date-progression path — a *different*, correctly-wired
  function with a similar name, which likely explains how these two got stranded.)
  `[NEW]` — corrects Phase 17's characterization for these two specific globals; genuinely
  dead exports, safe to delete along with their `app.js` import/window lines, distinct from
  the legitimate inline-`onclick` bridge pattern Phase 17 correctly identifies for the other
  19.
- **`showToast` call-site hygiene: clean.** Every `showToast(...)` call in this file
  (18 call sites, e.g. `:167,176,214,223,318,404,419,422,425,613,644,707,721,724,756,813,816`)
  correctly passes the type string first (`'success'|'error'|'warning'|'info'`) — this file
  does **not** exhibit the legacy-arg trap documented for `app.js` (Phase 17,
  `PHASE_17.md:158-`, `showToast(message, 'error')` silently rendering green). One outlier:
  `:414` calls the bare single-arg legacy form `showToast('Value updated successfully')`
  (no type at all) — this happens to resolve correctly to `'success'` (the legacy-path
  fallback when `legacyIsError` is false), so it is *not* a bug, but it's a stylistic
  inconsistency worth normalizing to `showToast('success', 'Value updated successfully')`
  for consistency with every other call in the file. `[NEW]` (very low severity).
- **Table sort assumes the current column layout.** `sortTableByColumn` (`:249-283`) sorts
  by `a.cells[columnIndex]?.textContent`, which for badge/button columns sorts on rendered
  text (e.g. "Achieved"/"Pending", or the "Delete" button's text). Not a bug today (only
  live header is `.workout-log-table`, confirmed present at `templates/workout_log.html:64-65`),
  just a fragility note: adding/reordering a `<th>` silently changes what "sort by column 3"
  means with no test coverage. `[NEW]` (informational, low severity).
- **Good Vitest-scaffold (WP3.1) candidates hiding in this file.** `normalizeExerciseName`
  (`:14-16`), `isAssistedBodyweightRow` (`:18-25`), `isWeightProgression` (`:27-32`),
  `parseOptionalNumber` (`:34-37`), `validateScoredValue` (`:537-557`), and
  `formatToDDMMYY` (`:733-738`) are all pure/near-pure functions with no DOM dependency
  beyond an optional `row` param already isolated for the first two. WP3.1 seeds Vitest with
  `exercise-helpers.js`/`toast.js`; this file has at least as many good targets and isn't
  named. `[NEW]` — cheap, high-value characterization-test candidates for WP3.1/WP3.3-style
  work, and characterizing `isWeightProgression`/`isAssistedBodyweightRow` first would have
  caught the `handleDateChange` drift bug above immediately.

## static/js/modules/filter-view-mode.js (725 lines)

**Verdict: a global (non-ES-module) IIFE, loaded directly via `<script>` in `base.html`
(not imported by `app.js` like the other three files in this phase), publishing
`window.FilterViewMode`. It owns the Simple/Advanced muscle-naming toggle used by
`workout-plan.js`, `weekly_summary.html`, `session_summary.html`, and an inline script in
`workout_plan.html`. About a third of its public API has zero callers.** `[NEW]` on the
loading-pattern inconsistency; `[RISK]` on allowlist drift; `[NEW]` on dead exports.

- **`filter-view-mode.js` is architecturally the odd one out in this phase.** `base.html:303`
  loads it as a classic `<script src="...">` (not `type="module"`), the only one of this
  phase's four files not wired through `app.js`'s import graph. It relies on a plain IIFE +
  `window.FilterViewMode = {...}` (`:693-722`) instead of ES module exports, which is why
  templates reach it via `window.FilterViewMode.xxx(...)` rather than an import. Per
  `static/js/CLAUDE.md`'s own convention ("Modules are loaded with `<script type="module">`
  ... export named symbols, not defaults"), this file doesn't follow the documented
  convention — though the reason is understandable: `templates/workout_plan.html`,
  `templates/weekly_summary.html`, and `templates/session_summary.html` all call it from
  inline `<script>` blocks that aren't themselves modules, so a global was the pragmatic
  choice at the time. `[NEW]` — worth a note for whichever WP eventually tackles WP3.2
  ("extract inline template scripts"): once those inline blocks become real modules, this
  file could convert to a normal `import`/`export` module and drop the `window.FilterViewMode`
  global entirely.
- **Cache-busting via `?v={{ range(1, 1000000) | random }}` (`base.html:303`, shared with
  `app.js:298` and two other global scripts) means this ~26 KB file is re-fetched fresh on
  every single page load for every user** — the random query string changes per request, so
  the browser can never serve it from cache. Given it's loaded on **every page** (it's in
  `base.html`, not a route bundle) and rarely changes, this is a real (if currently
  low-traffic, single-user-local) performance/caching anti-pattern that's out of scope to
  fix in this file but worth flagging since it directly affects how "safe" this file is to
  touch — every edit forces a full re-download for the next request regardless of any real
  versioning. `[NEW]` (informational; the fix belongs to `base.html`/build tooling, not this
  file).
- **Three-way hand-synced muscle-name allowlist, drift confirmed.** `DB_TO_SIMPLE`
  (`:116-156`) and `DB_TO_ADVANCED` (`:163-204`) both hand-map raw database
  `primary_muscle_group` strings to display groupings. Cross-checked against the canonical
  `MUSCLE_GROUPS` list in `utils/constants.py:4-25` (20 entries): `DB_TO_SIMPLE` and
  `DB_TO_ADVANCED` both contain keys that are **not** in the canonical list — e.g.
  `'Upper Chest'`, `'Abs/Core'`, `'Core'`, `'Rectus Abdominis'`, `'Upper Traps'`, `'Glutes'`
  (in `DB_TO_ADVANCED` only) — while `utils/constants.py` only has `'Chest'`,
  `'Rectus Abdominis'`, `'Trapezius'`, `'Gluteus Maximus'` for those groupings respectively.
  This is either (a) legacy/pre-normalization DB values these maps still defensively cover,
  or (b) genuine drift where the JS-side allowlist has entries the backend constant doesn't
  (or vice versa) — not resolved further this phase since it requires checking actual stored
  `primary_muscle_group` values in `data/database.db`, out of scope for a JS-only phase.
  `[RISK]` — this is a **third** hand-synced muscle-taxonomy list (alongside the "two
  hand-synced allowlists" already flagged in the filters layer per this task's brief),
  raising the total to at least three independently-maintained muscle-name mappings that
  must agree: `utils/constants.py::MUSCLE_GROUPS`, the filters-layer allowlist (Phase-scoped
  elsewhere), and this file's `DB_TO_SIMPLE`/`DB_TO_ADVANCED`/`SIMPLE_TO_DB`/
  `ADVANCED_TO_DB_ISOLATED` (four separate maps, `:116-289`).
- **Dead public API — confirmed zero callers repo-wide.** `getFilterQueryConfig`
  (`:494-534`), `simpleToDbValues` (`:483-485`), and the "legacy" toggle-button builder pair
  `createToggleButton`/`updateToggleUI` (`:609-676`) are all exported on
  `window.FilterViewMode` (`:706,707,710,711`) but grepping every `.html`/`.js` file in the
  repo for these four names outside their own definitions finds nothing. By contrast,
  `resolveFilterSelection`/`getMuscleFilterOptions` (used by an inline script in
  `templates/workout_plan.html:598,602`) and `transformMuscleDisplay`/
  `transformIsolatedMuscleDisplay` (used by `workout-plan.js:26,39` and
  `weekly_summary.html:589` / `session_summary.html:490`) are genuinely live. `[NEW]` — about
  110 of 725 lines (`:483-534` query-config helpers, `:604-676` legacy toggle UI) are
  unreferenced; `getFilterQueryConfig`/`simpleToDbValues` look like they were built for a
  server-query-building responsibility that filters.js (a different phase's file) may have
  since taken over independently — worth cross-checking against whatever Phase covers
  `filters.js` for whether it duplicates this logic instead of calling it (the "4
  fetch-unique-values implementations" already flagged suggests it does).
- **`initNavbarToggle`/`updateNavbarToggleUI` (`:544-602`) is the live implementation behind
  `#muscleModeToggle`**, the exact element named in `docs/MASTER_HANDOVER.md`'s
  known-E2E-flake note ("2 `workout-plan.spec.ts` tests on `#muscleModeToggle` off-viewport
  at 1280 width"). The dataset-flag re-entry guard (`:552-556`,
  `toggleBtn.dataset.initialized === 'true'`) is correctly defensive against double-init
  (this script has no explicit cleanup/unmount, and could conceivably run its
  `DOMContentLoaded` handler more than once if the script were ever loaded twice), but
  the underlying off-viewport E2E flake is a CSS/layout issue, not something in this file's
  logic. `[NEW]` (informational cross-reference only, no defect in this file).

## static/js/modules/workout-dropdowns.js (646 lines)

**Verdict: a well-built, ARIA-conscious progressive-enhancement layer over native
`<select>` elements, scoped correctly to `#workout[data-page="workout-plan"]`
(`:11-14`). No raw `fetch()`, no API calls at all — pure DOM/UI. The one real defect is a
built-but-never-invoked cleanup path that becomes a listener/DOM leak under the page's own
dynamic-row-mutation pattern.** `[NEW]` on the leak; otherwise clean.

- **`_cleanupHandler` (`:327-339`) is fully implemented — removes the `scroll`/`resize`/
  `click` window/document listeners, disconnects the `MutationObserver`, and removes the
  popover from `document.body` — but is never called anywhere.** Grepped the whole repo for
  `_cleanupHandler`: only the one definition. Meanwhile, `initializeWorkoutDropdowns()` is
  re-invoked by a `MutationObserver` on `#workout` (`:639-646`, `childList: true, subtree: true`)
  every time the workout-plan table's DOM changes (e.g. exercises added/removed by
  `workout-plan.js`), and `enhanceSelect()` guards against **re-enhancing** an
  already-wrapped `<select>` (`:22`, `select.closest('.wpdd')`) — but nothing guards against
  a `<select>` (and its `.wpdd` wrapper + body-appended `.wpdd-popover`) being **removed**
  from the DOM when a row is deleted. Every dropdown ever enhanced during a session keeps
  its `window.addEventListener('scroll', ..., true)`, `window.addEventListener('resize', ...)`,
  and `document.addEventListener('click', outsideClickHandler)` registered forever
  (`:322-324`), and its orphaned popover node stays parked under `document.body`
  (`:91`) even after the original `<select>`/row is gone. `dropdownRegistry` (`:8`, a
  module-level `Set`) also keeps growing and is iterated by `closeAllDropdowns()`
  (`:31-37`) on every dropdown open, touching detached DOM nodes for entries whose page
  content no longer exists. `[RISK]` — on the one page this module is scoped to
  (`workout_plan`), exercise rows are added/removed repeatedly in a single session
  (add/remove/replace exercise flows exist per `static/js/CLAUDE.md`'s file table), so this
  is a real, cumulative per-session memory/listener leak, not a theoretical one. Fix would
  be wiring `_cleanupHandler` into the same `MutationObserver` callback (`:639-641`) — e.g.
  detect removed `.wpdd` containers via `mutation.removedNodes` and call their stored
  `_cleanupHandler` — but that's a code change, not something to do in this scan.
  Not verified live in a browser this phase (no app/test runs per phase rules); confirmed
  by static reading of the observer/registry/cleanup code paths only.
- **Global dropdown registry correctly serializes "only one open at a time."**
  `closeAllDropdowns(exceptContainer)` (`:30-37`) is called from every `openDropdown()`
  (`:110-111`), which is the right, simple approach for a single-page, non-virtualized list
  of enhanced selects. `[NEW]` (positive, informational) — this pattern would need to move
  or be duplicated if `enhanceSelect` is ever reused outside `#workout[data-page="workout-plan"]`,
  since `dropdownRegistry` is a single module-level `Set` shared by every instantiation
  regardless of which container they belong to (harmless today since only one page uses
  this module).
- **Positioning logic (`positionPopover`, `:573-628`) is comprehensive** — separate mobile
  (bottom-sheet) and desktop (viewport-aware up/down flip with min/max height clamping)
  branches, always `position: fixed` to escape `overflow:hidden` ancestors, which is exactly
  why the popover has to live under `document.body` rather than inside the `.wpdd` container
  (`:91` vs `:92`). No defect found; this is consistent, deliberate design, not incidental
  complexity. `[NEW]` (informational, no defect).
- **`buildOptions`/`rebuildOptions` (`:395-493`, `:349-366`) correctly rebuild the popover
  and re-derive the `options` array in place** (`options.length = 0; options.push(...newOptions)`,
  `:357-358`) rather than reassigning the outer `const options`, which is necessary because
  closures throughout the function (keyboard handlers, `selectOption`, etc.) all capture the
  original `options` reference. Subtle but correct — no bug found, just confirming the
  in-place-mutation choice isn't accidental. `[NEW]` (informational).

## static/js/modules/routine-cascade.js (414 lines)

**Verdict: small, self-contained 3-step cascade (Environment → Program → Routine) that
composes a hidden `#routine` field for the existing plan-save flow. Deliberately
stateless (resets on load and on `pageshow`/bfcache-restore per `:54,84-97`) — this is a
documented, intentional UX choice, not a bug. No raw `fetch()`, no API calls.**
`[CONFIRMS-PLAN]` on absence from WP3.5's raw-fetch list (correctly has none).

- **Dead import**: `import { showToast } from './toast.js';` (`:9`) — grepped the entire
  file for `showToast(` and found **zero call sites**. This module never shows a toast;
  every user-facing signal is either a CSS class toggle (`clearCascadeValidation`,
  `:367-376`) or the breadcrumb text (`updateBreadcrumb`, `:314-341`). `[NEW]` — trivial,
  one-line dead import, safe to delete.
- **`ROUTINE_CONFIG` (`:12-33`) is a fourth hand-maintained taxonomy list**, structurally
  parallel to (but not identical to) `utils/plan_generator.py`'s own
  `{training_days: (program_name, [routine_names])}` table (`utils/plan_generator.py:29-33`
  and beyond). Spot-checked: `plan_generator.py`'s 1-day entry is `("Full Body", ["Workout A"])`
  (a single routine), while `routine-cascade.js`'s `"Full Body"` always offers three
  fixed sub-workouts (`["Workout A", "Workout B", "Workout C"]`, `:14,24`) with no 1-day
  variant at all — these are two different taxonomies serving different features (this
  file drives the *manual* routine-selection dropdown for saving/loading a plan; the
  generator drives the *auto-generate* flow), so this is not necessarily a bug, but it is
  a fourth place (after the three muscle-naming maps in `filter-view-mode.js`) where
  routine/program vocabulary is hand-duplicated across the JS/Python boundary with no
  shared source of truth. Not fully traced against `routes/workout_plan.py`/
  `templates/workout_plan.html`'s own "Days Split" references this phase (out of scope —
  those belong to a plan-generator/routes phase), flagging as a cross-cutting seed only.
  `[NEW]`.
- **`GYM` and `Home Workout` branches of `ROUTINE_CONFIG` (`:13-32`) are byte-for-byte
  identical** (same 8 programs, same routine-name arrays for all 8) — the whole
  `"Home Workout"` object (`:23-32`) is a full duplicate of `"GYM"` (`:13-22`) with no
  difference in structure or values anywhere. `updateCompositeRoutineValue` (`:254-270`)
  does the one bit of real environment-specific logic (mapping `"Home Workout"` →
  `"Home"` in the composite string, `:262`), which is the only reason the two keys can't
  simply be collapsed into one shared program/routine list keyed off environment-agnostic
  data. `[NEW]` — low-severity, but a clean 10-line simplification: extract one
  `PROGRAMS` map (program → routine names) and reference it from both `ROUTINE_CONFIG.GYM`
  and `ROUTINE_CONFIG["Home Workout"]`, or drop the per-environment nesting entirely if the
  two environments truly never diverge in available programs/routines.
- **Stateless-reset design confirmed intentional and consistent.** `resetCascadeSelector()`
  (`:381-414`) is called on `initializeRoutineCascade()` (`:60-86`, via
  `applyStatelessCascadeReset()`) and again on every `pageshow` event
  (`:91-97`, guarded by `hasPageShowResetListener` so the listener itself is only attached
  once). The `wpdd-rebuild` custom event dispatch (`:107`, one per cascade `<select>`) is the
  correct hook into `workout-dropdowns.js`'s `rebuildOptions()` (`workout-dropdowns.js:369`,
  `select.addEventListener('wpdd-rebuild', rebuildOptions)`) — confirming these two files
  *do* have one real, deliberate integration point, not just coincidental adjacency in the
  file list. `[NEW]` (positive, confirms cross-module wiring is correct, not accidental).
- **`triggerRoutineSelected()` (`:346-361`) only fires if `hiddenField.value` is truthy**
  (`:348`), meaning selecting a routine dispatches `routineSelected` for `workout-plan.js`
  to consume, but there's no equivalent "cleared" event when the user picks a *different*
  environment mid-way (which resets `routine` to `''` via `handleEnvironmentChange`/
  `handleProgramChange`, `:119-120,144-145`, but never calls `triggerRoutineSelected`, and
  correctly so since there's nothing meaningful to trigger with an empty value). Confirmed
  this is not a gap — `workout-plan.js`'s listener side wasn't re-read this phase (out of
  scope), so whether it independently needs a "routine was cleared" signal isn't verified;
  noting only that this file's own logic is internally consistent. `[NEW]` (informational).

---

## Cross-cutting seeds

1. **The task brief's "toast.js legacy-arg trap" was already fully documented in Phase 17
   for `app.js` (`showToast(message, 'error')` at `app.js:99,111,158,162` silently rendering
   green) — independently re-verified this phase.** None of this phase's four files
   reproduce that trap: `workout-log.js`'s 18 `showToast` calls all use the correct
   type-first form (one harmless single-arg legacy call at `:414`); `filter-view-mode.js`,
   `workout-dropdowns.js`, and `routine-cascade.js` either don't call `showToast` at all or
   (in `routine-cascade.js`'s case) import it and never call it. This phase also refines one
   Phase 17 claim: `updateProgressionStatus`/`checkProgressionStatus` are **not** part of
   the legitimate inline-`onclick` bridge pattern Phase 17 describes for the other 19
   `window.*` globals — they have zero callers anywhere (see `workout-log.js` section).
2. **Two independent "editable cell" ownership claims over the same page, only one live.**
   `workout-log.js`'s `initializeEditableCells()` (`:595-618`) and
   `initializeWorkoutLogFilters()`/`filterWorkoutLogs()` (`:620-690`) both target DOM
   selectors and an API endpoint (`/filter_workout_logs`) that don't exist in the real
   `templates/workout_log.html` — confirmed dead end-to-end (front-end hooks + a backend
   route that was never implemented or was removed). The real click-to-edit wiring lives in
   `ui-handlers.js`. This is a strong candidate for a small, low-risk WP: delete
   `workout-log.js:595-690` (96 lines, ~12% of the file) and its one call site.
3. **A concrete, high-confidence double-submission bug**: every scored-value edit
   (`scored_min_reps`/`scored_max_reps`/`scored_rir`/`scored_rpe`/`scored_weight`) is wired
   through *both* an inline `onchange="updateScoredValue(...)"` in the template *and*
   `ui-handlers.js`'s 500 ms-debounced `input`-event handler, which independently also calls
   `window.updateScoredValue`. This plausibly double-POSTs `/update_workout_log` (and
   double-recomputes learned calibration server-side, and double-toasts client-side) on a
   normal type-then-Enter or type-then-click-away edit. Worth a live-browser verification
   (network tab, count POSTs per edit) before any refactor touches either file — if
   confirmed, the fix is straightforward (drop the inline `onchange` attributes now that
   `ui-handlers.js` owns the debounced save, or vice versa) but is a behavior change outside
   this scan's no-app-runs mandate.
4. **A genuine progression-badge correctness bug from triplicated logic**:
   `handleDateChange` (`workout-log.js:801-807`) recomputes the Achieved/Pending badge with
   a naive `scored_weight > planned_weight` check, omitting the
   `isWeightProgression()`/`isAssistedBodyweightRow()` special-casing that the other two
   copies of the same logic (`updateScoredValue:388-395`, `checkProgressiveOverload:580-586`)
   correctly apply. For assisted-bodyweight exercises, editing only the progression date can
   flip the badge to the wrong state. Root cause is copy-paste of a ~10-line block three
   times instead of one shared helper — exactly the kind of duplication WP3.3's
   "characterize then extract pure logic" pattern (currently scoped only to
   `workout-plan.js`) would catch if applied here too.
5. **At least four independently hand-maintained taxonomy/allowlist pairs span the JS/Python
   boundary in this phase's files alone**: (a) `utils/constants.py::MUSCLE_GROUPS` (backend
   canonical, 20 entries) vs. (b) `filter-view-mode.js`'s `DB_TO_SIMPLE`/`DB_TO_ADVANCED`
   (contain keys — `'Upper Chest'`, `'Abs/Core'`, `'Glutes'`, etc. — absent from (a)), vs.
   (c) the filters-layer's own allowlist (a different phase, already flagged by the backend
   scan as one of "two hand-synced allowlists"), plus (d) `routine-cascade.js`'s
   `ROUTINE_CONFIG` vs. `utils/plan_generator.py`'s day-count → program/routine table (two
   different taxonomies for two different features, not necessarily buggy, but zero shared
   source of truth). None of these are broken *today* in an observable way from a JS-only
   read, but each is a place where a future muscle- or routine-taxonomy change (e.g.
   normalizing `'Upper Chest'` into `'Chest'`, or adding a 7th split type) must be
   remembered and hand-applied in 2-4 separate files with no compiler/test signal if one is
   missed.
6. **`workout-dropdowns.js`'s unused `_cleanupHandler` (built, never invoked) is a real
   per-session leak specifically because it's scoped to the one page
   (`workout_plan`) where rows are added/removed dynamically** — the `MutationObserver` that
   re-runs `initializeWorkoutDropdowns()` on every `#workout` DOM change (`:639-646`) has no
   counterpart that detects *removed* `.wpdd` containers and calls their stored cleanup.
   Every enhanced dropdown that's ever removed from the page (e.g. via exercise-row
   deletion) leaves its `window`/`document` listeners and body-appended popover behind for
   the rest of the session.
