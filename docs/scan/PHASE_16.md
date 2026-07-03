# Phase 16 — JS: progression / body-comp / tables / summary

Line-by-line read of `static/js/modules/progression-plan.js` (573),
`static/js/table-responsiveness.js` (514), `static/js/modules/body-composition.js`
(490), `static/js/modules/filters.js` (348), `static/js/modules/summary.js` (133),
`static/js/modules/charts.js` (59), plus `static/js/CLAUDE.md` and
`.claude/rules/frontend.md` for context. Cross-checked against
`docs/REFACTOR_PLAN.md` v2 (WP3.5 raw-fetch migration, WP3.2 inline-template
extraction), `utils/body_fat.py` (JS-mirror docstring contract), and
`e2e/body-composition.spec.ts` (parity test coverage). Also read
`static/js/app.js`, `static/js/modules/ui-handlers.js`, `static/js/modules/toast.js`,
`templates/weekly_summary.html`, `templates/session_summary.html`,
`templates/base.html`, and `templates/workout_plan.html` to trace call sites,
since several of this phase's files are not directly wired from templates and
their liveness can only be established by following the import chain.

---

## static/js/modules/progression-plan.js (573 lines)

**One live, well-integrated export (`initializeProgressionPlan`) plus ~50 lines
of fully dead legacy code at the bottom of the file.**

- `initializeProgressionPlan()` (`:23-521`) is the only export and the only
  function reachable from `app.js` (`initializeProgressionPage()` calls it
  directly, no gating). It owns: the goal-setting Bootstrap modal (focus trap,
  focus restore, ESC handling, flatpickr date picker `:88-98`), the
  exercise-select → suggestions fetch (`handleExerciseChange`, `:295-340`),
  suggestion-card rendering (`displaySuggestions`, `:342-387`), the Phase 2D-B
  fatigue-context advisory block (`renderProgressionFatigueContext`,
  `:395-427`), goal save/delete/complete handlers (`:250-520`), and a second,
  independent focus-trap listener for a *second* modal (`deleteGoalModal`,
  `:452-470`). All of this genuinely belongs together (one page, one modal
  workflow) — unlike the grab-bag pattern flagged for `ui-handlers.js` in
  Phase 17, this file's breadth is justified by being page-scoped.
- **Fatigue-context wiring (`:322-427`) matches the plan's framing exactly.**
  `handleExerciseChange` treats `response.fatigue_context` as an **additive
  sibling to `data`** on the response envelope (`:325-327`, explicit comment
  citing "Phase 2D-B"), not part of the suggestions array. It is rendered by
  `renderProgressionFatigueContext(fatigue)` into `#suggestionsFatigueContext`
  as its own DOM section (`.progression-fatigue`), **always below** the
  suggestion cards, with a hardcoded fallback advisory string `'This does not
  change your suggestion.'` (`:423`) matching the CLAUDE.md-documented locked
  2D-A copy. The host element is explicitly hidden (`host.hidden = true`) when
  `fatigue_context` is absent (`:399-402`) — correctly treating the toggle-off
  / unknown-muscle case as "no chip at all," not an empty chip. This is also
  called on the **error path** (`:337`, passing `null`) so a failed fetch
  clears any stale advisory from a previous successful exercise selection —
  a correctness detail worth noting since it's easy to miss in a refactor.
  **[CONFIRMS-PLAN]**
- **[NEW] — `createSuggestionCard()` (`:523-539`) and `openGoalModal()`
  (`:541-573`) are fully dead, and `openGoalModal` is also broken.** Neither
  function is `export`ed, neither has any caller anywhere in this file or the
  rest of the repo (verified via repo-wide grep — the only hits for
  `createSuggestionCard`/`openGoalModal`/`getCurrentValue` are inside this
  file itself). `createSuggestionCard` builds a suggestion-card HTML string
  with an inline `onclick="openGoalModal(this)"` attribute (`:532`) — but
  `openGoalModal` is a module-scoped ES-module function, never assigned to
  `window`, so even if this string were ever injected into the DOM the
  `onclick` would throw `ReferenceError: openGoalModal is not defined`.
  `openGoalModal` itself ends by calling `getCurrentValue(goalType)` (`:572`)
  — **`getCurrentValue` does not exist anywhere in the codebase** (repo-wide
  grep confirms zero definitions). This pair is leftover from an earlier,
  pre-2D-B implementation of the same goal-modal workflow that the live
  `document.addEventListener('click', ...)` delegation at `:120-247` and
  `displaySuggestions` at `:342-387` have since superseded. Clean rule-8
  deletion candidate (`docs/REFACTOR_PLAN.md` global rule 8) — not currently
  on the plan's WP0.1/WP0.2 lists, which are Python-only; worth a follow-up
  JS dead-code WP.
- **[NEW] — 17 unguarded `console.log` calls** (`:100-383`, e.g. `:100, 108,
  113-115, 122, 140-141, 162, 168, 175, 183, 280, 296-298, 306, 313, 316, 343,
  382`), all firing unconditionally in production on every exercise selection,
  goal save, etc. Every sibling file read this phase gates its debug logging
  behind a module-level flag (`FILTERS_DEBUG` in `filters.js`,
  `TABLE_RESPONSIVENESS_DEBUG` in `table-responsiveness.js`, `APP_DEBUG` in
  `app.js` per Phase 17) — this file has no such flag and logs raw, including
  full suggestion payloads (`:175, 313, 316`). Not a bug, but an inconsistency
  worth folding into any future pass over this file (e.g. a Phase 3 JS-split
  WP) since it's a 5-minute fix once someone is already touching the file.
- **`showToast` legacy-arg usage here is actually correct**, unlike the
  confirmed-buggy `app.js` call sites documented in Phase 17's cross-cutting
  seed #1. The three legacy-signature calls (`:291, 488, 517`, all
  `showToast('...' + error.message, true)`) pass a genuine boolean `true` as
  the second argument, which `toast.js`'s legacy-detection branch (`toast.js:17`)
  correctly maps to `legacyIsError = true` → type `'error'`. The three
  object-style calls (`:285, 480, 504`) correctly pass `'success'` as the first
  arg. **No misuse in this file** — worth noting since the task brief flagged
  toast legacy-arg misuse as a watch item; it exists elsewhere (`app.js`, per
  Phase 17) but not here. **[CONTRADICTS-PLAN-WATCHLIST]** (in the sense that
  this specific file is clean).
- Goal-type mapping dictionary (`:129-138`) hardcodes the mapping from
  specialized suggestion types (`double_progression_weight`,
  `reduce_weight`, `maintain_progress`, etc.) down to the four base storage
  types (`weight`/`reps`/`sets`/`technique`). This mapping is duplicated
  conceptually by whatever generates those specialized `suggestion.type`
  values server-side (`utils/progression_plan.py`, not read this phase) —
  a second dual-source-of-truth pattern (smaller stakes than the body-fat
  formulas, but the same shape of risk: if the server adds a new suggestion
  type, this client-side map silently falls through to
  `goalTypeMapping[rawGoalType] || rawGoalType` and stores whatever the raw
  string was). **[RISK]**, low severity — no evidence of current drift, just
  a maintenance trap.
- Weight-increment logic (`:192-196`, `<20kg → +2.5kg, else +5kg`) is
  duplicated in the fallback branch only (used when `current`/`target` values
  aren't pre-filled by the suggestion card's `data-*` attributes); the
  comment at `:193` explicitly says "Use same increment logic as suggestion
  cards" — meaning the authoritative version lives server-side and this is a
  third small mirror. Not verified against `utils/progression_plan.py` this
  phase (out of scope), flagging for cross-reference only.

---

## static/js/table-responsiveness.js (514 lines)

**Non-module, global IIFE script — deliberately outside `modules/` because it
is loaded unconditionally in `base.html`, not per-page like the ES-module
feature files.**

- Loaded at `templates/base.html:301`:
  `<script src="{{ url_for('static', filename='js/table-responsiveness.js') }}?v={{ range(1, 1000000) | random }}"></script>`
  — a plain classic script (no `type="module"`), self-invoking IIFE
  (`:28-514`) that exposes a single `window.TableResponsiveness` object
  (`:506-512`). This is why it lives at `static/js/table-responsiveness.js`
  rather than `static/js/modules/`: per `static/js/CLAUDE.md`'s own
  file-role table, the flat (non-`modules/`) files are exactly the
  cross-cutting, non-module, base.html-loaded scripts (`darkMode.js`,
  `accessibility.js`, and this file) — feature-scoped ES modules live in
  `modules/` and are imported per-page. **[CONFIRMS-PLAN]** in the sense
  that the placement is intentional and documented, not an oversight.
- **[NEW] — cache-busting inconsistency.** This file's `<script>` tag carries
  a `?v={{ range(1, 1000000) | random }}` query string that changes on
  *every server render* (`base.html:301`), permanently defeating browser
  caching for a 514-line file loaded on every single page. The same pattern
  is applied to `app.js` (`base.html:298`), `filter-view-mode.js`
  (`base.html:303`), and `exercise-video-modal.js` (`base.html:305`) — but
  **not** to `darkMode.js` or `accessibility.js` (`base.html:299-300`), which
  sit immediately adjacent with no cache-busting at all. No functional bug,
  but an inconsistent policy worth a single decision (either all shared
  scripts get cache-busting, or none do, or it's tied to a real
  content-hash) rather than four files opting in ad hoc.
- **Auto-init is entirely attribute-driven** (`autoInit()`, `:471-493`):
  scans for `[data-table-responsive]` and, for each match, calls
  `initColumnChooser(table, pageKey)` unconditionally and
  `fitRowsToViewport` conditionally on a `data-table-on-page-size` attribute
  naming a `window[...]` callback. **[NEW] — repo-wide grep for
  `data-table-responsive` finds exactly one consumer**:
  `templates/workout_plan.html:330` (`data-table-responsive="workout_plan"`).
  No other template uses this attribute, so despite being loaded globally on
  every page, the column-chooser feature is currently exercised by exactly
  one table.
- **[NEW] — `fitRowsToViewport` (`:408-462`) is fully dead code in
  production.** It is exported on the public API (`:508`), documented with a
  full JSDoc block and a usage example in the file's own header comment
  (`:25`), and wired into `autoInit()` (`:483-491`) behind a
  `data-table-on-page-size` attribute — but repo-wide grep finds **zero**
  templates setting that attribute, and zero other JS files calling
  `fitRowsToViewport` or `TableResponsiveness.fitRowsToViewport` directly.
  The ResizeObserver, debounce, ~40 lines of height-arithmetic (`:426-449`),
  and cleanup-function return are all unreachable. Confirmed
  rule-8-deletable pending a final grep at execution time (dynamic
  `window[onPageSize]` lookups can hide callers from static grep in theory,
  but the gating attribute itself has zero occurrences, which is sufficient
  to prove the branch never fires).
- **[NEW] — `applyColumnVisibility()` (`:354-389`) and `toggleColumn()`
  (`:344-346`) are dead, superseded by the CSS-class approach.** The
  column-visibility feature was rearchitected to toggle `.tbl--view-simple`
  / `.tbl--view-advanced` classes on the `<table>` element so dynamically
  added rows inherit visibility via CSS (`applyViewMode`, `:330-341`, whose
  own comment says exactly this). `toggleColumn` is explicitly marked as a
  kept-for-compatibility no-op (`:343`, "Legacy call ignored - use view mode
  toggle instead") — but grep finds **zero callers of `toggleColumn`
  anywhere**, so even the compatibility shim has no one to be compatible
  with. `applyColumnVisibility` (per-column `nth-child` show/hide,
  `:354-389`) has zero call sites in this file or elsewhere — it predates
  the CSS-class refactor and was never deleted. Both are candidates for the
  same JS dead-code follow-up as `fitRowsToViewport`.
- **Workout-plan/global-filter-mode coupling** (`:155-166, 249-262,
  311-321`): when `pageKey === 'workout_plan'` and
  `window.FilterViewMode` exists, this file defers Simple/Advanced state
  entirely to `window.FilterViewMode.getViewMode()`/`setViewMode()` and a
  custom `filterViewModeChanged` event, bypassing its own `localStorage`
  persistence (`getPrefs`/`setPrefs`, `:41-68`) for that one page. Every
  other page that might one day adopt `data-table-responsive` would use the
  plain `localStorage`-backed path. This is a real, intentional branch (not
  dead), but it means the "Simple/Advanced" concept has two independent
  sources of truth depending on which page you're on — worth flagging for
  anyone extending this to a second table.

---

## static/js/modules/body-composition.js (490 lines)

**The JS half of a documented dual-source-of-truth: `utils/body_fat.py`'s
docstring (`:1-11`) requires the four pure functions here to mirror the
Python module "verbatim," and they do — but the Playwright parity test only
exercises one of the four, one gender, one age bracket.**

- Module docstring (`:1-9`) states the contract in-repo: `computeNavy`,
  `computeBmi`, `aceCategory`, `jacksonPollockIdeal` "mirror `utils/body_fat.py`
  byte-for-byte" and "any change here MUST be reflected in `utils/body_fat.py`
  (and vice versa)." Cross-referencing `utils/body_fat.py:77-203` line by
  line against this file:
  - `computeNavy` (`:61-89`) ↔ `compute_navy` (`body_fat.py:77-115`): same
    validation ranges (`CIRCUMFERENCE_MIN/MAX_CM`, `HEIGHT_MIN/MAX_CM`, all
    re-declared as JS constants `:14-20` matching the Python module-level
    constants exactly), same male formula
    (`495/(1.0324 - 0.19077*log10(delta) + 0.15456*log10(height)) - 450`,
    JS `:78` vs Python `:102-104`), same female formula (`:88` vs `:112-114`).
    Verified identical coefficients.
  - `computeBmi` (`:91-111`) ↔ `compute_bmi` (`body_fat.py:118-151`): same
    adult/minor branch at `ADULT_AGE_THRESHOLD = 18`, same four linear
    formulas (`1.20*bmi + 0.23*age - {16.2|5.4}` adult,
    `1.51*bmi - 0.70*age {-2.2|+1.4}` minor) — coefficients match exactly
    between `:105-109` (JS) and `:141-150` (Python).
  - `aceCategory` (`:113-130`) ↔ `ace_category` (`body_fat.py:154-172`): same
    band tables (`ACE_BANDS_MALE`/`ACE_BANDS_FEMALE`, JS `:33-46` vs Python
    `:45-58`, identical breakpoints), same inclusive-lower/exclusive-upper
    open-ended-Obese semantics.
  - `jacksonPollockIdeal` (`:132-156`) ↔ `jackson_pollock_ideal`
    (`body_fat.py:175-203`): same table (`JACKSON_POLLOCK_TABLE`, JS
    `:22-31` vs Python `:31-40`, values match row-for-row), same clamp/
    interpolate logic.
  - All four read as a faithful, currently-in-sync mirror. **[CONFIRMS-PLAN]**
    — the docstring's claim holds as of this reading.
- **[RISK] — parity test coverage is much narrower than the mirror's actual
  surface area.** `e2e/body-composition.spec.ts` has exactly one test that
  numerically cross-checks JS vs Python (`'JS preview matches Python
  persisted Navy BFP within rounding'`, `:100-126`), and it only covers:
  - `computeNavy`, **male** branch only (seeded profile is `gender: 'M'`,
    `:14`) — the female branch (`hip_cm` required, different coefficients,
    `body-composition.js:80-88`) has **no** JS/Python parity assertion
    anywhere in the E2E suite.
  - **`computeBmi` has zero parity assertions.** The `'BMI fallback shows
    when tape fields are blank'` test (`:93-98`) only asserts the displayed
    BFP is not the placeholder dash (`not.toHaveText('—')`) — it never reads
    the persisted Python-side value and compares. A drift in the BMI
    formula's coefficients (adult or minor) would not be caught by any
    current E2E test.
  - **`aceCategory` has zero test coverage** of any kind — no test asserts
    the rendered band label (`[data-bc-band-label]`) matches what
    `ace_category()` would return server-side for the same inputs.
  - **`jacksonPollockIdeal` has zero test coverage** — `[data-bc-jp-ideal]`
    /`[data-bc-jp-current]` are rendered (`:347-349`) but never asserted
    against in any spec.
  - **Age bracket**: the seeded profile is `age: 34` (`:15`) — the minor
    (`age_years < 18`) branch of both `compute_bmi` and the age-clamping
    edges of `jackson_pollock_ideal` (`<20` / `>55`) are untested for
    parity.
  - Net: of the four documented "must match Python" functions, **one is
    tested (partially — one gender, one age bracket, ±0.05% tolerance)** and
    three have **no parity test at all**. Given the module docstring frames
    this as a manually-synced contract with no automated single-source
    generation, this is the highest-value gap this phase found: a future
    edit to `compute_bmi`, `ace_category`, or `jackson_pollock_ideal` in
    either file, made without touching the other, would ship silently and
    only be caught by an alert user noticing the live preview disagrees with
    a saved snapshot.
- Range-validation constants (`:14-20`) and the `checkRange`/`_check_range`
  helper pattern (`:52-59` JS vs `body_fat.py:70-74` Python) are duplicated
  by necessity (client can't import server validation) — this is the same
  class of drift risk as the formulas themselves but is at least
  mechanically simple (five numeric bounds) and less likely to silently
  drift than the formula bodies.
- DOM-wiring half of the file (`:158-490`, `bindForm`, `renderResults`,
  `renderTrend`, `prependHistoryRow`) is unremarkable — standard fetch/
  render/error-toast pattern via `api.get`/`api.post`/`api.delete` from
  `fetch-wrapper.js` (imports at `:11`), **zero raw `fetch()` calls in this
  file** (contradicts the generic "watch for raw fetch" brief for this
  specific file — it is already fully on the wrapper). Error toasts
  correctly use the new-style `showToast('error', msg)` / `showToast('success',
  msg)` object-argument form throughout (`:396, 404, 416, 425, 443`) — no
  legacy-arg misuse here.
- `escapeHtml` (`:471-478`) is applied to snapshot `captured_at` when
  building history rows via `innerHTML` (`:455, 463`) but the numeric fields
  (`bfp_navy`, `bfp_bmi`, `lean_mass_kg`, `fat_mass_kg`, `:456-459`) are
  interpolated raw — safe today only because they're server-computed floats,
  not user text; worth noting as a pattern to watch if this function is ever
  reused for user-editable fields (`notes` is stored but never rendered back
  into this table, so it's not currently an XSS vector).

---

## static/js/modules/filters.js (348 lines)

**Exactly one raw `fetch()` call, confirming `docs/REFACTOR_PLAN.md` WP3.5's
count for this file.**

- **[CONFIRMS-PLAN]** — `clearFilters()` (`:161-253`) contains the file's
  only raw `fetch()` call: `fetch("/get_all_exercises")` at `:222`, with
  manual `response.ok` checking (`:223`) and manual `.json()` parsing
  (`:224`) instead of `api.get(...)` from `fetch-wrapper.js` (which this
  same file already imports and uses elsewhere, `:2, 58, 69`). This exactly
  matches WP3.5's inventory: "filters.js … (1 each)". No other `fetch(`
  occurrences exist in this file (verified via full-file grep) — the plan's
  count is accurate, not just plausible.
- **`showToast` calls here all use the legacy 1–2-arg form and are all
  correct** (`:77, 80, 248, 252`): `showToast(message)` for two success
  cases (`:77, 252` — single-arg, legacy path defaults to `'success'` since
  `typeof undefined !== 'boolean'` → `legacyIsError = false`, which is the
  intended behavior for a success message) and `showToast(message, true)`
  for two error cases (`:80, 248` — `true` correctly maps to `'error'`). No
  misuse in this file, same conclusion as `progression-plan.js` above.
- `filterExercises()` (`:38-82`) has a duplicated "reload everything" path:
  when no filters are selected it calls `api.get("/get_all_exercises", ...)`
  (`:58`, the wrapper) — but `clearFilters()` (a different function, called
  from a different button) re-implements the same "reload all exercises"
  logic independently using the raw `fetch()` flagged above (`:220-249`),
  including its own separate error handling and its own dropdown-rebuild
  logic (`:225-243`) that partially duplicates
  `updateExerciseDropdown()` (`:255-298`, which `filterExercises` calls via
  `updateExerciseDropdown(exercises, preserveSelection)` at `:61, 72`, but
  which `clearFilters` does **not** call — it hand-rolls its own dropdown
  rebuild instead). **[NEW]** — this means "clear filters" and "select an
  empty filter set" are two different code paths for what is conceptually
  the same operation (show all exercises), one going through the shared
  `updateExerciseDropdown` helper (with its `filter-applied` glow effect,
  `:289-297`) and one not. Migrating the raw `fetch()` in WP3.5 is a good
  opportunity to also unify these two paths onto the same helper — flagging
  for whoever picks up that WP.
- `updateFilteredView()` (`:311-320`) and `initializeAdvancedFilters()`
  (`:300-309`) implement a `data-category`/`.advanced-filter` row-filtering
  scheme distinct from the `filter-dropdown`/`#filters-form` scheme used by
  the rest of the file. Grepped for `.advanced-filter` and `data-category`
  usage in templates — not found in `templates/workout_plan.html` (the only
  template that loads `filters.js`'s exported `initializeFilters`,
  `initializeAdvancedFilters`, `initializeSearchFilter`,
  `initializeFilterKeyboardEvents` via `app.js:4, 213-214`). **[RISK] —
  likely orphaned feature**, same shape as Phase 17's confirmed-orphaned
  `initializeSuggestionCards()` in `ui-handlers.js`: the function is called
  (`app.js:213`, `initializeAdvancedFilters()`), so it's not fully dead in
  the "unreachable" sense, but it attaches listeners to a `.advanced-filter`
  selector that doesn't appear to exist in the current DOM, meaning it's a
  no-op in production. Not exhaustively verified against every template
  (out of this phase's file list), but worth a follow-up grep before any
  rule-8 deletion claim.
- `initializeSearchFilter()` (`:322-335`) similarly targets `#search-filter`
  — not grepped against templates this phase (out of scope), flagging as an
  open question rather than a confirmed finding.

---

## static/js/modules/summary.js (133 lines)

**Called unconditionally by `app.js` on both summary pages, but effectively
a guarded no-op in production because both pages define their own updater
functions inline.**

- `fetchWeeklySummary`/`fetchSessionSummary` (`:11-49`) both open with the
  same guard: `if (pageHasOwnUpdater()) { return; }` (`:13-15, 33-35`), where
  `pageHasOwnUpdater()` (`:6-9`) checks
  `typeof window.updateWeeklySummary === 'function' || typeof
  window.updateSessionSummary === 'function'`. Both are called
  unconditionally from `app.js`'s `initializeWeeklySummary()`/
  `initializeSessionSummary()` (`app.js:187-207`) on every load of
  `/weekly_summary` and `/session_summary`.
- **[NEW] — the guard is always true in production, making these two
  exported functions permanent no-ops on the only two pages that call
  them.** `templates/weekly_summary.html:448` and
  `templates/session_summary.html:335` (not read in full this phase, but
  grepped and spot-checked) each declare a **top-level, non-module**
  `async function updateWeeklySummary()` / `async function
  updateSessionSummary()` inside a plain inline `<script>` tag — a
  top-level function declaration in a classic (non-module) script is a
  property of `window` by default, so `window.updateWeeklySummary` and
  `window.updateSessionSummary` are both always defined by the time
  `app.js`'s `DOMContentLoaded` handler runs (inline scripts execute in
  document order, before the deferred `type="module"` `app.js` — module
  scripts are deferred by spec). This means `summary.js`'s
  `fetchWeeklySummary`/`fetchSessionSummary` **return immediately every
  time**, and all of `updateSummaryUI`/`updateSummaryTable`/
  `updateCategoryTable`/`updateIsolatedMusclesTable`/`getVolumeClass`/
  `getVolumeLabel` (`:51-133`) are unreachable in current production
  templates. This is the JS-side twin of WP3.2's premise: the ~395 inline
  JS lines in `weekly_summary.html` (and the analogous block in
  `session_summary.html`) are not a *duplicate* implementation living
  alongside this module — they are the **only live implementation**, and
  this module is the vestigial one. **[CONFIRMS-PLAN]** for WP3.2's framing
  ("extract inline template scripts") but adds a sharper detail: extraction
  should *replace* `summary.js`'s dead functions rather than merge with
  them, since they compute the same UI from a structurally different data
  shape assumption (see next point).
- The inline `updateWeeklySummary()` in the template (confirmed by reading
  `weekly_summary.html:448-576`) uses a **raw `fetch()`** (`:468`,
  `fetch(\`/weekly_summary?contribution_mode=${contributionMode}\`, {...})`)
  with manual header-setting, `isApiFailure`/`getApiErrorMessage`/
  `unwrapApiPayload` helpers (not defined in this phase's files — likely
  template-local or a separate shared script), and renders
  `effective_sets`/`raw_sets` side-by-side per the CLAUDE.md-documented
  Effective/Raw display contract. This raw fetch is **outside** the
  `filters.js`/`volume-splitter.js`/etc. file list WP3.5 enumerates (WP3.5
  only lists JS module files, not inline template scripts) — **[RISK]**:
  if WP3.2 (inline-script extraction) and WP3.5 (raw-fetch migration) are
  sequenced independently, this raw fetch could be extracted into a new
  `weekly-summary-page.js` module in WP3.2 and then missed by WP3.5's
  file-list-driven migration (since the new file wouldn't be on the
  original list). Worth a one-line addition to WP3.2's gate: "the extracted
  module should use `apiFetch`/`api` from the start, not carry the raw
  fetch forward."
- `summary.js`'s own data-shape assumptions (`updateSummaryUI`, `:51-62`)
  read `data.session_summary || data.weekly_summary || []` and expect flat
  fields `item.total_sets`/`item.total_reps`/`item.total_volume` with no
  `effective_sets`/`raw_sets` split — an older shape than what the live
  inline implementation renders (Effective vs Raw side-by-side,
  `weekly_summary.html:493-506`). This confirms `summary.js` predates the
  Effective/Raw UI work and was never updated or deleted afterward — further
  evidence it's dead weight, not a currently-maintained parallel path.
- `getVolumeClass`/`getVolumeLabel` (`:121-133`, thresholds 10/20/30 sets)
  are a third copy of volume-classification-label logic; `weekly_summary.html`
  has its own `getVolumeDetails()` (referenced at `:496`, not read this
  phase) and `charts.js`/`ui-handlers.js` don't duplicate it. Not chasing
  further since it's out of this phase's file list, but flagging that any
  WP3.2 cleanup should check whether the template's `getVolumeDetails`
  and this module's `getVolumeClass`/`getVolumeLabel` agree on thresholds
  before deleting one in favor of the other.

---

## static/js/modules/charts.js (59 lines)

**Fully dead in production — reachable by the call graph, but the DOM
attribute and global it depends on never exist.**

- Two exports, `createVolumeChart` (`:3-30`) and `createProgressChart`
  (`:32-59`), both thin wrappers around `new Chart(container, {...})` (Chart.js
  library API) with a try/catch that shows an error toast on failure.
- Import chain: `ui-handlers.js` imports both (`ui-handlers.js:1`) and calls
  them from `initializeCharts()` (`ui-handlers.js:392-410`), which dispatches
  based on a `container.dataset.chart` value (`'volume'`/`'progress'`) read
  from `[data-chart]` elements. `app.js` calls `initializeCharts()`
  unconditionally in both `initializeWeeklySummary()` and
  `initializeSessionSummary()` (`app.js:189, 200`) — so the call graph *is*
  live and reachable, unlike `summary.js`'s guarded no-op above.
- **[NEW] — but the DOM query and the library both come up empty.**
  Repo-wide grep for `data-chart` across `templates/` returns **zero
  matches** — no template anywhere creates an element with `data-chart`, so
  `initializeCharts()`'s `document.querySelectorAll('[data-chart]')`
  (`ui-handlers.js:393`) always returns an empty NodeList, and the
  `forEach` body that would call `createVolumeChart`/`createProgressChart`
  never executes. Separately, repo-wide grep for `chart.js`/`Chart.min.js`/
  any CDN reference to the Chart.js library across `templates/` also
  returns **zero matches** — the global `Chart` constructor these two
  functions call (`:5, 34`) is never loaded anywhere in the app. Even in the
  hypothetical case where a template someday adds a `[data-chart]` element,
  `new Chart(...)` would throw `ReferenceError: Chart is not defined`
  (caught by the try/catch, surfaced as an error toast, not a crash — but
  still non-functional).
- Net: this is a fully self-consistent, syntactically fine, **completely
  unreachable-in-practice** 59-line module — not because of a broken import
  (it's imported and called correctly) but because the two things it depends
  on (a `data-chart` markup convention and the Chart.js library) were never
  actually adopted anywhere in the templates. This reads as scaffolding for
  a chart feature that was planned or partially built and then abandoned in
  favor of the hand-rolled SVG trend line in `body-composition.js`
  (`renderTrend`, `body-composition.js:227-258`) and whatever the weekly/
  session summary pages use instead (server-rendered tables + Bootstrap
  tooltips, no charting library, confirmed via the `weekly_summary.html`
  excerpt read this phase). **[NEW]** — strong rule-8 deletion candidate for
  both `charts.js` in full and the `initializeCharts()`/`data-chart` branch
  of `ui-handlers.js`, pending the standard re-verification grep at
  execution time (dynamic `dataset.chart` values can't hide additional
  producers from a `data-chart` attribute grep, since the attribute name
  itself is static).

---

## Cross-cutting seeds

1. **The "informational advisory, always additive, never blocking" pattern
   from `docs/effective_sets.py`'s non-goal ("never auto-adjust or block
   user actions") is faithfully carried into the JS layer for fatigue
   context.** `progression-plan.js`'s `renderProgressionFatigueContext`
   treats `fatigue_context` as a pure rendering concern, fully decoupled
   from suggestion-card generation (`displaySuggestions` never branches on
   `fatigue`), and explicitly clears itself on error. Anyone touching this
   file for Phase 3 JS-split work should keep this separation (e.g. don't
   let `estimates.js`-style extraction accidentally merge fatigue-context
   rendering into the suggestion-card builder).

2. **Three of this phase's six files contain code that is reachable-by-import
   but never actually reached-at-runtime**, each for a different reason:
   `summary.js` (guarded no-op — `pageHasOwnUpdater()` is always true in
   production), `charts.js` (empty DOM query — no `[data-chart]` markup
   exists), and roughly a third of `table-responsiveness.js`
   (`fitRowsToViewport`, `applyColumnVisibility`, `toggleColumn` — gated
   behind attributes/call-sites that don't exist). This is a distinct
   category from `progression-plan.js`'s `createSuggestionCard`/
   `openGoalModal` (which are *not* reachable by import — no caller at
   all). A future dead-code sweep should treat "imported and called, but
   the thing it queries for never exists in the DOM" as its own rule-8
   sub-case, since a naive `grep -rn functionName` will report false-live
   hits for `createVolumeChart`/`fetchWeeklySummary`/`fitRowsToViewport` —
   the grep finds their call sites in `ui-handlers.js`/`app.js`, but those
   call sites are themselves inside dead branches or defeated by a runtime
   guard. `docs/REFACTOR_PLAN.md`'s rule 8 (dead-code grep) as currently
   worded would not catch any of these three cases — worth a note added to
   rule 8 alongside the existing decorator-registration carve-out.

3. **Body-composition JS/Python parity testing is the single highest-value
   gap found this phase.** `utils/body_fat.py`'s docstring makes the
   dual-source-of-truth contract explicit and names all four functions that
   must be kept in sync; `e2e/body-composition.spec.ts` numerically verifies
   exactly one of them (`compute_navy`, male-only, one input pair, ±0.05%
   tolerance). `compute_bmi`, `ace_category`, and `jackson_pollock_ideal`
   have zero JS/Python parity assertions — a silent one-sided edit to any of
   the three would ship undetected by any existing gate (pytest tests
   `utils/body_fat.py` in isolation; Playwright only smoke-tests that the
   JS side renders *something* non-placeholder for the BMI-fallback and
   never touches ACE/Jackson-Pollock at all). Recommend this as a
   standalone follow-up (not a REFACTOR_PLAN WP, since it's new test
   coverage rather than a refactor): add parity assertions for the female
   Navy branch, the BMI method (both age brackets), `ace_category` band
   boundaries, and `jackson_pollock_ideal` clamp/interpolation — ideally as
   Vitest characterization tests once WP3.1's scaffold lands (this module's
   four pure functions are an ideal first Vitest target: no DOM, pure math,
   already isolated at the top of the file), cross-checked against
   `utils/body_fat.py`'s existing pytest suite for the same input vectors.

4. **`docs/REFACTOR_PLAN.md` WP3.5's fetch-count claim for `filters.js` is
   verified exactly correct: 1 raw `fetch()`, at `filters.js:222` inside
   `clearFilters()`.** No hidden second call, no false positive. Small
   bonus finding for whoever executes WP3.5: migrating that one call is
   also a chance to unify `clearFilters()`'s hand-rolled dropdown-rebuild
   logic (`filters.js:225-243`) with the shared `updateExerciseDropdown()`
   helper (`filters.js:255-298`) that the sibling `filterExercises()`
   function already uses for the same "show all exercises" scenario — not
   required by WP3.5's stated scope, but low-cost to fold in while the
   function is already open for the fetch-wrapper edit.

5. **Toast legacy-arg misuse is real but file-specific, not endemic to this
   phase's slice.** Of this phase's six files, `filters.js` and
   `progression-plan.js` both use the legacy 1–2-arg `showToast` signature
   extensively (7 call sites total) and every single one resolves correctly
   (`true`/absent second arg maps to the intended error/success color).
   `body-composition.js` uses the new object-style signature exclusively
   and correctly. **None of this phase's files reproduce the
   `app.js`-confirmed bug** (Phase 17 cross-cutting seed #1: passing a
   string as the second arg, e.g. `showToast(msg, 'warning')`, which the
   legacy branch coerces to `false` → green success toast regardless of
   intent). Worth stating explicitly so a future grep-driven toast-signature
   fix doesn't waste time re-checking these six files — the bug's blast
   radius (as currently known) is `app.js` only, four call sites, already
   documented in Phase 17.

6. **JS-side dead code is broader than `docs/REFACTOR_PLAN.md`'s current
   Phase 0 scope, which is Python-only (WP0.1/WP0.2 target
   `utils/errors.py`, `utils/logger.py`, `movement_patterns.py`,
   `profile_estimator.py` constants).** This phase alone found five
   independent JS dead-code candidates across three files
   (`progression-plan.js`'s `createSuggestionCard`/`openGoalModal` pair;
   `table-responsiveness.js`'s `fitRowsToViewport`,
   `applyColumnVisibility`, and the already-self-declared-legacy
   `toggleColumn`), plus the effectively-fully-dead `charts.js` module and
   its `ui-handlers.js` `initializeCharts()`/`data-chart` branch (Phase 17
   independently flagged `ui-handlers.js`'s `initializeSuggestionCards()`
   as a sixth). None of these are on the plan's Phase 0 list. Recommend a
   dedicated "Phase 0.6 — JS dead code sweep" WP (same rule-8 discipline,
   but using the runtime-guard-aware grep approach from seed #2 above)
   before or during Phase 3's JS-split work, since deleting this dead
   weight first would shrink the diffs WP3.3/WP3.4 need to move around.
