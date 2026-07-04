# Phase 12 — JS: workout-plan cluster (line-by-line audit)

Scope: full reads of `static/js/modules/workout-plan.js` (2411 lines),
`static/js/modules/exercises.js` (269 lines), `static/js/modules/exercise-helpers.js`
(48 lines). Cross-referenced against `static/js/CLAUDE.md`, `.claude/rules/frontend.md`,
and `docs/REFACTOR_PLAN.md` WP3.3/WP3.4/WP3.5. Also read `static/js/app.js` (299 lines,
not in the assigned file list but is the wiring layer that imports all three target
files and exposes their exports as `window.*` globals — needed to determine what's
actually live vs. dead and to verify the toast-misuse hypothesis) and `toast.js` /
`fetch-wrapper.js` for the toast-signature and fetch-wrapper contracts referenced in the
task brief. Line numbers are exact against the worktree at time of reading.

---

## exercise-helpers.js (48 lines) — genuinely pure, small, well-scoped

- `exercise-helpers.js:20-28` — `escapeHtml(value)` — pure, no DOM, no globals. Correctly
  used 26 times inside `workout-plan.js` for every value interpolated into a row
  template literal (verified by grep count).
- `exercise-helpers.js:30-48` — `isValidMediaPathShape` (private) + `resolveExerciseMediaSrc`
  (exported) — pure path-shape validation mirroring `utils/media_path.py::is_valid_media_path_shape`
  per the file's own docstring (§4.3). Only consumer is `workout-plan.js:1796`
  (`resolveExerciseMediaSrc(exercise.media_path)`). No duplication found — this one is a
  correctly-shared, single-source-of-truth helper. [CONFIRMS-PLAN — this file is already
  the "logic-*.js" pattern WP3.3 wants to replicate for the rest of `workout-plan.js`]
- **Duplication elsewhere, not in this file**: `escapeHtml` is independently
  re-implemented in `static/js/modules/program-backup.js`, `backup-center.js`, and
  `body-composition.js` (grepped `function escapeHtml`) instead of importing the
  canonical one from `exercise-helpers.js`. Out of this phase's file scope but directly
  answers the task's "duplicated logic with exercise-helpers.js" prompt: the duplication
  runs *outward* (other modules re-invent it) rather than *inward* (workout-plan.js
  doesn't duplicate it — it imports it correctly). [NEW] [seed: rename/relocate
  `exercise-helpers.js` as a shared `html-safety.js` or similar if Phase 3 wants those
  three other modules to consume it too]

---

## exercises.js (269 lines) — half dead code, half live, both halves duplicate workout-plan.js

- `exercises.js:1-3` — imports `showToast`, `fetchWorkoutPlan` (from `workout-plan.js`),
  `notifyVolumeAffectingPlanChange`. This is the one confirmed cross-import from
  `workout-plan.js` (besides `app.js` itself) — any WP3.4 split must keep `fetchWorkoutPlan`
  importable at the same path/name for this file to keep working.
- `exercises.js:13-79` — `validateExerciseValues` — **pure**, no DOM/fetch, straightforward
  boundary-check function (sets ≤20, reps ≤100, weight ≤2000, RIR ≤10, RPE 1-10). Good
  Vitest characterization candidate in isolation.
- `exercises.js:81-148` — `addExercise()` (exported) — reads 8 form fields via
  `getElementById`, calls `validateExerciseValues`, then `sendExerciseData`.
- `exercises.js:150-185` — `sendExerciseData` — **raw `fetch('/add_exercise', ...)`**
  (line 154), manual `response.json()` / `response.ok` handling, calls `showToast(...)`
  (legacy 1-2 arg form) and `resetFormFields()`.
- `exercises.js:190-227` — `removeExercise(exerciseId)` (exported) — **raw
  `fetch('/remove_exercise', ...)`** (line 206), a `deletingExercises` Set used as a
  reentrancy guard.
- `exercises.js:229-238` — private `resetFormFields()` — sets 5 DOM fields to hardcoded
  defaults (`sets=1`, `rir=0`, `weight=100`, `min_rep=3`, `max_rep_range=5`).
- `exercises.js:240-269` — `clearWorkoutPlan()` (exported) — **raw
  `fetch('/clear_workout_plan', ...)`** (line 251), closes a Bootstrap modal, calls
  `fetchWorkoutPlan()` + `notifyVolumeAffectingPlanChange`.

**[CONFIRMS-PLAN] exactly 3 raw `fetch()` calls in this file** (`/add_exercise`,
`/remove_exercise`, `/clear_workout_plan`) — WP3.5's count is exactly right.

**[NEW] [RISK] `addExercise()` (and everything it exclusively calls — `validateExerciseValues`,
`sendExerciseData`, this file's `resetFormFields`) is dead in production.** Traced the
call graph:
- `app.js:5` imports `addExercise` from `exercises.js`; `app.js:43` does
  `window.addExercise = addExercise;` — so the *name* is referenced (a rule-8 grep for
  `\baddExercise\b` would find this import/assignment and call it "live").
- But grepping `templates/**/*.html` and `static/js/**/*.js` for the actual call
  `addExercise(` (not just the identifier) returns **zero matches** — no
  `onclick="addExercise()"` anywhere, and the `#add_exercise_btn` button
  (`templates/workout_plan.html:247`) has no inline `onclick` at all. The real Add
  Exercise click handler is wired programmatically in `workout-plan.js:1651-1654`
  (`addExerciseBtn.addEventListener('click', handleAddExercise)`) — a completely
  separate function.
- Net effect: `exercises.js`'s `addExercise`/`sendExerciseData`/`resetFormFields`/
  `validateExerciseValues` are **unreachable from the UI** — the only way to invoke them
  is typing `window.addExercise()` in devtools. Meanwhile `workout-plan.js` has its own,
  actually-wired, parallel implementation: `handleAddExercise` (1483-1547) →
  `sendExerciseData` (1567-1595, uses `api.post`) → `resetFormFields` (1597-1600) — **same
  function names, same responsibility, two independent bodies, only one of which runs.**
  This directly matters for WP3.3/WP3.4: a naive "move pure logic out of workout-plan.js"
  pass could easily also want to touch `exercises.js`'s near-identical, differently-named
  functions and conflate the two, or leave the dead copy behind as apparent "coverage."
  This is exactly the kind of dead-code case that survives rule 8's grep heuristic
  (import/assignment reference exists) but is functionally orphaned — worth a rule-8
  refinement note or a dedicated Phase-0 follow-up: **grep the call site, not just the
  identifier, before deciding something WP3.4-adjacent is "still used."**
- `removeExercise` (exercises.js:190) and `clearWorkoutPlan` (exercises.js:240) ARE live:
  `removeExercise` is invoked via the inline `onclick="removeExercise(${exercise.id})"`
  generated by `workout-plan.js:1849` in every table row, and `clearWorkoutPlan` via
  `onclick="clearWorkoutPlan()"` at `templates/workout_plan.html:849`. Both need
  `window.*` global exposure (inline `onclick=` requires it) — `app.js:44-45` does this
  correctly. These two are correctly the "3 raw fetches" the plan wants migrated, but only
  2 of the 3 (`remove_exercise`, `clear_workout_plan`) are reachable in normal use; the
  third (`add_exercise`) is dead weight riding along.

- Toast-call audit for this file (all 10 `showToast(...)` calls): every call uses either
  the modern `(type, message)` form is **not** used here at all — this file only ever
  uses the **legacy** `(message)` / `(message, true)` two-positional form (lines 101, 107,
  122, 168, 174, 193, 215, 223, 259, 267). None of them pass a non-boolean value in the
  `isError` slot, so **the toast-misuse trap described in the task brief (string as 2nd
  positional arg silently renders success-green) does not occur in `exercises.js` or
  `workout-plan.js`.** It does occur in `app.js` (see Cross-cutting seed 1 below), which
  is adjacent but outside this phase's three target files.

---

## workout-plan.js (2411 lines) — the real seam analysis

### Module load / top-level side effects
- `workout-plan.js:1-8` — imports, then `initializeExerciseImagePreview();` runs
  **at module-import time**, not inside an exported init function. Any consumer that
  imports this module (including a future Vitest test that just wants
  `parseRoutine` or `escapeHtml`-adjacent pure helpers) will trigger this DOM side
  effect on import. **[RISK for WP3.3]** — WP3.3's plan is "write Vitest
  characterization tests against current behavior FIRST" against the *current* module;
  importing `workout-plan.js` in a Vitest/jsdom environment to characterize e.g.
  `parseRoutine` will also execute `initializeExerciseImagePreview()` (from
  `exercise-image-preview.js`, not read this phase) and pull in the full import chain
  (`fetch-wrapper.js`, `toast.js`, `workout-plan-events.js`, `exercise-video-modal.js`,
  `exercise-helpers.js`, `exercise-image-preview.js`). None of those are declared or
  fenced by any factory/init-guard — WP3.3 should either mock `initializeExerciseImagePreview`
  or hoist the pure functions to their own file *first* to get frictionless test isolation
  (the "write tests against current file, then move" ordering in WP3.3 may need to invert
  to "move first, then test the new pure file" for functions that live above line 8).

### Module-level mutable state (no shared-state module — a real gap in WP3.4)
`workout-plan.js:130-166` declares 8 pieces of shared mutable state at module scope:
`currentRoutineTabFilter`, `allExercisesCache`, `isExerciseSubmissionPending`,
`selectedExerciseIds` (Set), `supersetColorMap` (Map), `executionStyleOptions`,
`weightUserDirty` (declared later at :718), `latestTracePayload` (declared later at :875).
**[CONTRADICTS-PLAN]** WP3.4 proposes four leaf files — `table.js`, `estimates.js`,
`supersets.js`, `media.js` — plus `index.js` for wiring, but does not name a shared-state
module. In the current file, at least three of those four leaves need to read/write the
*same* state:
- `allExercisesCache` / `currentRoutineTabFilter` are read+written by table-rendering code
  (`fetchWorkoutPlan`, `updateRoutineTabs`, `handleRoutineTabClick`, `applyRoutineTabFilter`)
  AND by the swap-exercise flow (`updateCachedExercise`, :2215-2225) which isn't really
  "table.js" or "supersets.js" territory either (see next finding).
- `selectedExerciseIds` / `supersetColorMap` are populated inside
  `updateWorkoutPlanTable` (the row-render loop, :1741-1789 — clearly "table.js") but
  consumed/mutated by `handleSupersetCheckboxChange` / `updateSupersetActionButtons` /
  `handleLinkSuperset` / `handleUnlinkSuperset` (clearly "supersets.js"). Splitting by
  feature file, as WP3.4 proposes, means these two Set/Map objects must either become
  exported/imported module state (fragile — two files mutating one shared object across
  an import boundary) or get promoted into a small `state.js` (or live in `index.js` and
  get passed down). **This should be an explicit decision point added to WP3.4, not
  discovered mid-execution.**
- `latestTracePayload` (estimate-trace state, :875) is read by `estimates.js`-bound
  functions (`applyLearnedSuggestionToInputs`, `resetWorkoutControlsToSuggestion`,
  `buildLearnedActions`, `ignoreRelatedTransferForCurrentExercise`) — self-contained to
  the estimates cluster, no cross-file leakage. This one *does* fit WP3.4 cleanly.

### Cluster 1 — Muscle-display transforms (lines 17-87): mostly pure, one global read
- `transformMuscleDisplay` (17-40) and `getRelevantIsolatedMuscles` (46-87) — no DOM
  writes, but both read `window.FilterViewMode` (a global set up by a different module,
  `filter-view-mode.js`, not read this phase). **Not fully pure** — pure-function
  characterization tests (WP3.3) will need to stub `window.FilterViewMode` rather than
  treating these as zero-dependency functions. Good extraction candidates for a
  `logic-muscle-display.js`, but WP3.3/3.4 should note the global-read dependency
  up front so the Vitest scaffold stubs it consistently. [CONFIRMS-PLAN, with caveat]

### Cluster 2 — Swap-button markup builders (89-109): genuinely pure
- `getSwapButtonMarkup()` / `getSwapButtonLoadingMarkup()` — zero-argument pure string
  templates, no DOM, no globals. Trivial, safe WP3.3 extraction. [CONFIRMS-PLAN]

### Dead code: `handleApiResponse` (111-128)
- Explicitly marked `@deprecated Use api wrapper from fetch-wrapper.js instead`. Grepped
  the whole `static/js/` tree: zero call sites anywhere (only its own definition).
  **Confirmed dead** — candidate for Phase-0-style deletion, not currently on any WP0.x
  list because Phase 0 in `docs/REFACTOR_PLAN.md` didn't audit `static/js/`. [NEW]

### Cluster 3 — Execution style picker (168-391, ~220 lines): entirely unaccounted for by WP3.4
`getExecutionStyleOptions` (cached API fetch), `renderExecutionStyleBadge` (pure-ish
string builder, no DOM read but does read exercise fields), `showExecutionStylePicker`
(DOM-heavy: builds a floating positioned picker widget, wires radio-change/save/cancel/
close handlers, positions itself against viewport bounds). **[CONTRADICTS-PLAN / NEW]**
WP3.4's target shape is `table.js` / `estimates.js` / `supersets.js` / `media.js` /
`index.js` — none of those is a natural home for a ~220-line AMRAP/EMOM execution-style
picker feature. It's invoked from a click handler attached inside the table-row template
(`execution-style-cell` click → `showExecutionStylePicker`, wired at :1892-1898 inside
`updateWorkoutPlanTable`), so it could be shoehorned into `table.js`, but it's a
self-contained feature (its own floating-panel DOM, its own API endpoint
`/api/execution_style_options` + `/api/execution_style`) that would be cleaner as its own
`execution-style.js` leaf. This entire cluster is a scope gap in WP3.4 as written.

**[RISK] Event-listener leak in `showExecutionStylePicker` (383-390):** the "close on
outside click" handler is added to `document` via `setTimeout(..., 100)` and only
self-removes when it actually fires (i.e., the user clicks outside the picker):
```
picker.querySelector('.btn-close-picker').addEventListener('click', () => picker.remove());
picker.querySelector('.btn-cancel-exec').addEventListener('click', () => picker.remove());
picker.querySelector('.btn-save-exec').addEventListener('click', async () => { ... picker.remove(); ... });
setTimeout(() => {
    document.addEventListener('click', function closeOnOutside(e) { ... document.removeEventListener('click', closeOnOutside); });
}, 100);
```
If the user closes the picker via the Close button, Cancel button, or Save button (three
of the four ways to close it), `picker.remove()` runs but the `closeOnOutside` listener
registered on `document` is **never removed** — only the fourth path (click-outside)
unregisters it. Each time a user opens the execution-style picker and dismisses it via
Close/Cancel/Save, a new stale `closeOnOutside` closure (holding a reference to the
now-detached `picker` node) accumulates permanently on `document`. Over a session with
repeated use this is an unbounded listener leak plus wasted `picker.contains(e.target)`
checks on every future document click. **Not currently flagged by any WP; worth a
one-line fix (call a shared `cleanup()` from all four exit paths) whenever this cluster
is touched.** [NEW] [RISK]

### Cluster 4 — Routine string parsing/formatting (394-453): pure, good WP3.3 fit
`parseRoutine`, `formatRoutineForDisplay`, `formatRoutineForTab`, `compareRoutines` — all
pure (string split/compare), zero DOM/globals. Textbook WP3.3 extraction candidates
(`logic-routine-format.js`). [CONFIRMS-PLAN]

### Cluster 5 — Table fetch/render/tabs (456-607, 1704-1908, 1672-1702, 1310-1328)
`fetchWorkoutPlan` (exported, API+DOM), `updateRoutineTabs`/`handleRoutineTabClick`/
`applyRoutineTabFilter` (mixed — `applyRoutineTabFilter` at 602-607 is pure and trivially
extractable, the rest is DOM), `updateWorkoutPlanTable` (1714-1908, the big row-builder),
`handleViewModeChange`/`updateMuscleDisplaysInTable` (1672-1702), `updateWorkoutPlanUI`
(1310-1328, computes totals then writes DOM — the `reduce()` total-sets calculation
at :1312 is a two-line pure extractable). This is the clear `table.js` core and mostly
matches WP3.4. **One structural problem:**

**[CONTRADICTS-PLAN / RISK] `updateWorkoutPlanTable` interleaves table rendering with
superset business logic — table.js and supersets.js are not cleanly separable as WP3.4
assumes.** Lines 1741-1789 (inside the row-render loop) compute the superset color-index
assignment (`supersetColorMap`), group adjacency detection (`superset-first`/
`superset-last` CSS classes based on whether paired rows are physically adjacent in the
sorted array), and the superset badge HTML — all embedded directly in the per-row
template-building code, not delegated to a `supersets.js`-owned function. Likewise,
`initializeDragAndDrop` (2341-2411) contains explicit superset-partner-adjacency logic
(finding a dragged row's superset partner and moving it to stay adjacent, :2365-2385) —
drag-and-drop is a table concern but this chunk is pure superset semantics. A literal
"table.js has rendering, supersets.js has pairing" split will either (a) leave superset
coloring/adjacency logic duplicated or awkwardly imported back into table.js, or (b)
require table.js to import supersets.js for at least three functions
(color-index-for-group, is-adjacent-pair, find-partner-row) that don't exist yet as
standalone functions — they're inlined. WP3.4 should call out "extract 3 named superset
helpers used by both table.js and supersets.js" as an explicit sub-step, not assume the
split falls out of the file boundary for free.

### Cluster 6 — Estimates / Workout Controls / fatigue-context / nudge (707-1195, 798-1180)
This is the largest coherent cluster and best matches WP3.4's "`estimates.js` (Workout
Controls + fatigue-context section + nudge)" description:
`setWorkoutControlValue`, `weightUserDirty`/`markWeightUserDirty`/
`initializeWeightDirtyTracking`, `applyEstimateToWorkoutControls`, `updateLearnedBadge`,
`updateFatigueContextChip` (707-815); `applyLearnedSuggestionToInputs`,
`resetLearnedForCurrentExercise`, `ignoreRelatedTransferForCurrentExercise` (817-869);
`updateEstimateTraceUI`, `renderEstimateTrace`, `buildFatigueContextSection`,
`resolveControlStep`/`resolveControlMin`/`nudgeWorkoutControl`,
`resetWorkoutControlsToSuggestion`, `buildFatigueNudgeGroup`/`buildFatigueNudgeControls`,
`buildLearnedActions`, `collapseEstimateTrace`, `bindEstimateTraceToggle` (871-1180);
`applyUserProfileEstimateForSelectedExercise` (1182-1195). [CONFIRMS-PLAN — file boundary
matches]

**[RISK / nuance for WP3.3]** The task brief frames this section as a target for "pure
logic extraction," but on a line-by-line read, almost none of `buildFatigueContextSection`
/ `buildFatigueNudgeControls` / `buildFatigueNudgeGroup` / `buildLearnedActions` /
`renderEstimateTrace` is pure data logic — they are DOM-node factories
(`document.createElement`, `.addEventListener`, `.appendChild`) that return live DOM
nodes, not data. The only genuinely pure sub-piece buried in this cluster is the numeric
step computed inside `nudgeWorkoutControl` (:1031-1042 — `base + (direction === 'down' ?
-step : step)`, clamped to `min`, rounded to 2dp) — worth pulling out as a 4-line pure
`computeNudgedValue(current, step, min, direction)` helper, but that's a much smaller win
than WP3.3's framing implies. Most of this cluster's "logic" is inseparable from DOM
construction; WP3.3's Vitest characterization tests here will mostly be
snapshot/structure assertions on DOM output (jsdom), not pure-function unit tests. This
doesn't invalidate WP3.3, but the phase's effort estimate should account for DOM-node
factories being harder to characterize than string/number pure functions.
- 2D-A section (`buildFatigueContextSection`, :982-1013) correctly renders the locked
  advisory line `fatigue.advisory || 'This does not change your suggestion.'` (:1002) —
  matches the protected-zone copy in `docs/REFACTOR_PLAN.md` rule 2. Any WP3.3/3.4 move
  of this function must preserve this exact fallback string verbatim (it's not test-only —
  it's a live user-facing default when `fatigue.advisory` is absent).
- 2D-C nudge steppers (`buildFatigueNudgeControls`/`buildFatigueNudgeGroup`, :1084-1111,
  1055-1079) are correctly scoped to weight+sets only (reps deferred per comment at
  :1082-1083) and are client-side-only (no API call) — matches the documented Phase
  2D-C/2D-D gating; nothing here reaches into the blocked 2D-D surface.

### Cluster 7 — Exercise-selection / routine-selection wiring (1197-1308)
`handleExerciseSelection`, `handleRoutineSelection` (exported), `updateExerciseDropdown` —
DOM+API, dynamic `import('./filters.js')` at :1234 and :1255 (lazy-loaded to avoid a
circular/eager dependency on `filters.js`). Fits `index.js` or a small `routine-select.js`;
not explicitly named by WP3.4 but small enough to fold into `index.js` wiring.

### Cluster 8 — Form validation for Routine/Exercise required fields (1330-1481)
`setFieldValidationState`, `highlightIncompleteCascadeDropdowns`,
`clearCascadeDropdownValidation`, `clearRequiredFieldValidation`,
`validateRequiredSelections` — DOM-heavy validation-highlighting cluster, entirely
separate from muscle-display/table/estimates/supersets/media. **[NEW]** Not named by
WP3.4's four leaves; it's tightly coupled to the Add Exercise form (used only by
`handleAddExercise`), so it likely belongs bundled with Cluster 9 below rather than
`table.js`.

### Cluster 9 — Add Exercise submission flow (1483-1600, 1602-1637): the file's OWN duplicate of exercises.js
`handleAddExercise` (exported), `setAddExerciseButtonLoading`, `sendExerciseData`
(different body from exercises.js's same-named function — uses `api.post` +
`isHandledApiError`/`logApiError`), `resetFormFields` (different body from exercises.js's
version — calls `applyUserProfileEstimateForSelectedExercise()` instead of hardcoding
field values), `initializeDefaultValues` (sets defaults + wires a `change`-event
clamp-to-min/max on 6 inputs). **[NEW]** This is the live, wired Add-Exercise path (see
exercises.js section above for the dead twin). Like Cluster 8, WP3.4's four named leaves
(`table.js`/`estimates.js`/`supersets.js`/`media.js`) have no obvious home for "the Add
Exercise form submission + validation" — it isn't table rendering, isn't an estimate, isn't
a superset, isn't media. Recommend WP3.4 add a fifth leaf (e.g. `add-exercise-form.js`)
covering Clusters 8+9, or explicitly fold them into `index.js` since `initializeWorkoutPlanHandlers`
(Cluster 10) already wires all of this together.

### Cluster 10 — Init entry point (1639-1670): the natural `index.js`
`initializeWorkoutPlanHandlers` (exported, called once from `app.js:217`) — wires
`initializeDefaultValues`, `initializeWeightDirtyTracking`, `bindEstimateTraceToggle`,
the add-exercise button listener, `handleExerciseSelection`, `handleRoutineSelection`,
`initializeRoutineTabs`, a `filterViewModeChanged` document listener, and the initial
`fetchWorkoutPlan()` call. This is exactly WP3.4's `index.js` — confirmed clean fit.
[CONFIRMS-PLAN]

### Cluster 11 — Superset actions (1911-2081): clean supersets.js fit (state caveat above)
`handleSupersetCheckboxChange`, `updateSupersetActionButtons`, `initializeSupersetActions`,
`handleLinkSuperset`, `handleUnlinkSuperset` — all DOM+API, self-contained aside from the
shared `selectedExerciseIds`/`supersetColorMap` state noted above. [CONFIRMS-PLAN, with
the shared-state caveat]

### Cluster 12 — Swap/replace exercise (2083-2226): another WP3.4 scope gap
`handleSwapExercise` (API+DOM, the biggest single handler after `updateWorkoutPlanTable`),
`updateRowMetadata`, `updateCachedExercise`. **[NEW]** Not table rendering (though it
mutates an existing table row rather than rebuilding it), not an estimate, not a
superset, not media. WP3.4's four-leaf split has no named destination for this ~140-line
cluster; by elimination it would land in `table.js` (it's the closest fit — row mutation),
but that's not stated anywhere in the plan and should be.

### Cluster 13 — Inline cell editing (2228-2338): table.js
`makeTableCellEditable`, `updateExerciseField` — DOM event wiring for click-to-edit
numeric cells, clean `table.js` fit. Uses a `mousedown` document listener added/removed
per edit session (:2312-2313, :2306, :2319, :2323) — correctly paired add/remove on every
exit path (Enter/Escape/click-outside all call `document.removeEventListener` before
`finishEditing`), **unlike** the execution-style-picker leak above. Good pattern, worth
using as the template if the picker leak gets fixed.

### Cluster 14 — Drag-and-drop reorder (2341-2411): table.js, with embedded superset logic (see Cluster 5 note)
`initializeDragAndDrop` — `Sortable.create` wiring, `onStart`/`onEnd` handlers. Contains
the superset-partner-adjacency-on-drag logic flagged above.

### Media/YouTube glue
`buildPlayButton` is imported from `./exercise-video-modal.js` (not one of this phase's
three files) and invoked once per row inside `updateWorkoutPlanTable` (:1860-1864). This
is the entirety of "media.js" glue that lives inside `workout-plan.js` today — WP3.4's
`media.js` leaf would need to absorb this ~6-line call site plus decide whether
`exercise-video-modal.js` itself moves under `workout-plan/` or stays a sibling import.
Small, low-risk, but worth naming explicitly since `media.js` per the plan's own
description ("YouTube modal + image preview glue") sounds like it means the *modal
implementation*, when in fact the modal implementation already lives in a separate file
and `workout-plan.js` only holds the call site.

---

## Cross-cutting seeds

1. **[NEW] [RISK — confirmed live bug, outside this phase's 3 files but directly answers
   the task's toast-misuse question]** `static/js/app.js` has the exact toast-misuse
   pattern the task asked about, in the `window.generateStarterPlan` handler
   (`app.js:65-168`, wired to the workout-plan page's "Generate Starter Plan" modal):
   `showToast(errorMsg, 'error')` (app.js:158) and `showToast('Error generating plan.
   Please try again.', 'error')` (app.js:162). Tracing through `toast.js`'s signature
   detection (`toast.js:11-31`): `type` is the message string (not in
   `{success,error,warning,info}`) → legacy-signature branch triggers → `legacyIsError =
   typeof message === 'boolean' ? message : false` — but `message` here is the *string*
   `'error'`, not a boolean, so `legacyIsError` evaluates `false` → the toast renders
   **green/success** with the error text inside it, exactly inverted from intent. Same
   bug at `app.js:99` and `app.js:111` (`showToast(msg, 'warning')` → renders green, not
   yellow). `app.js:146` (`showToast(..., 'success')`) happens to render correctly by
   accident (legacy default is already 'success'). **Recommend filing this as a real bug
   fix** (change to `showToast('error', errorMsg)` / `showToast('warning', msg)`) —
   separate from any refactor WP, this is user-visible today. Also confirms `app.js` has
   its own 1 raw `fetch('/generate_starter_plan', ...)` call (app.js:117), matching
   WP3.5's "app.js (1)" tally exactly.

2. **Two full parallel "Add Exercise" implementations exist simultaneously** (exercises.js
   dead / workout-plan.js live, detailed above). This is the single most important finding
   for WP3.3/WP3.4 sequencing: whoever executes the split should decide explicitly whether
   to delete the dead `exercises.js` trio first (a cheap, low-risk Phase-0-style follow-up,
   not currently on any WP0.x list since Phase 0 didn't audit `static/js/`) or carry it
   forward — carrying it forward means the WP3.4 diff will "move" dead code into the new
   `workout-plan/` folder structure and make it look alive again by association.

3. **No shared-state module named in WP3.4** despite `selectedExerciseIds`,
   `supersetColorMap`, `allExercisesCache`, `currentRoutineTabFilter` being genuinely
   cross-cutting between the proposed `table.js` and `supersets.js` leaves. Recommend
   WP3.4 add an explicit `state.js` (or equivalent) as a fifth file, or document exactly
   which leaf "owns" each piece of state and how the others read it (export getters, not
   raw mutable bindings, to avoid import-order fragility).

4. **Execution-style picker (~220 lines) and swap/replace-exercise (~140 lines) and the
   Add-Exercise form+validation (~300 lines across Clusters 8+9) are three multi-hundred-
   line clusters with no named destination in WP3.4's four-leaf split** (`table.js`,
   `estimates.js`, `supersets.js`, `media.js`). Combined these three clusters are roughly
   660 of the file's 2411 lines (~27%) — not a rounding error. WP3.4 should either name
   additional leaves (`execution-style.js`, `add-exercise-form.js`) or explicitly assign
   these clusters to existing leaves by elimination (most naturally: swap/replace →
   `table.js`; execution-style → new leaf or `table.js`; add-exercise form → `index.js` or
   new leaf) rather than leaving it to be discovered mid-execution.

5. **Confirmed real event-listener leak** in `showExecutionStylePicker`'s outside-click
   handler (workout-plan.js:383-390) — three of four close paths never unregister the
   `document` click listener. Independent of the refactor plan, worth a one-line fix
   whenever this cluster is next touched (cite as a Phase-3 filler or immediate hotfix,
   executor's call).

6. **`handleApiResponse` (workout-plan.js:111-128) is confirmed dead** (deprecated,
   zero call sites) — small, safe addition to a future dead-code sweep; Phase 0 in
   `docs/REFACTOR_PLAN.md` never looked at `static/js/`, so nothing currently catches this.

7. **The toast-signature legacy-compat branch in `toast.js` is a footgun by design, not
   just at these two call sites.** Any future call written as `showToast(someMessage,
   someNonBooleanNonNumber)` — e.g. a string, object, or `undefined` where a boolean was
   intended — silently defaults to `'success'` (green) rather than erroring or warning in
   the console. Given `app.js` already got this wrong twice, and `workout-plan.js`/
   `exercises.js` (this phase's files) do NOT have this bug only because every call
   happens to correctly use either the modern 2-positional-string form or the legacy
   `(message, true)` boolean form, this is a fragile invariant to maintain by convention
   alone. Worth flagging to whoever eventually revisits `toast.js` (not in this phase's
   scope) that the legacy branch could `console.warn` when `message` is present but not a
   boolean/number/object, to catch exactly this class of caller mistake instead of
   silently mis-coloring the toast.
