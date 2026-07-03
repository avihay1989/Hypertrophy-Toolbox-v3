# Phase 17 — JS: app infra & shared

Line-by-line read of `static/js/app.js` (298), `static/js/modules/ui-handlers.js`
(443), `static/js/modules/navbar-enhancements.js` (316),
`static/js/modules/fetch-wrapper.js` (263), `static/js/accessibility.js` (264),
`static/js/modules/workout-controls-animation.js` (175),
`static/js/modules/toast.js` (111), `static/js/darkMode.js` (81),
`static/js/modules/navbar.js` (58), plus `static/js/CLAUDE.md` and
`.claude/rules/frontend.md` for context. Cross-checked against
`docs/REFACTOR_PLAN.md` v2, specifically WP3.5 (raw `fetch()` →
`apiFetch` migration) and Phase 3's general JS-split plan, which depends on
`fetch-wrapper.js`'s actual exported contract.

---

## static/js/modules/fetch-wrapper.js (263 lines)

**This is the file WP3.5 needs precisely documented. Read in full.**

- Two exports: `apiFetch(url, options)` (`:121-247`, default export at
  `:263`) and `api` (`:252-258`, a thin verb-convenience wrapper —
  `get/post/put/patch/delete`, all delegating to `apiFetch`). Also exports
  `isHandledApiError(error)` (`:87-89`) and `logApiError(context, error)`
  (`:95-98`) — two small helpers not mentioned in `static/js/CLAUDE.md`'s
  table, used elsewhere (`exports.js`, `workout-log.js`,
  `workout-plan.js` all import `isHandledApiError`). **[NEW]** — CLAUDE.md's
  one-line description ("Exports `apiFetch` (low-level) and `api`
  (convenience)") undersells the surface; two more named exports exist and
  are load-bearing for error-classification UX (deciding warning vs. error
  toast styling).
- **Request contract** (`:121-157`): default `method='GET'`; default headers
  always include `Content-Type: application/json`, `Accept: application/json`,
  `X-Requested-With: XMLHttpRequest` (`:137-142`), plus a generated
  `X-Request-ID` (`generateRequestId()`, `:44-46`, `req_<timestamp>_<random>`).
  Caller-supplied `headers` are shallow-merged on top (`:144`), so a caller
  *can* override `Content-Type` but not easily remove it. Body: if
  `typeof body === 'object'`, it's JSON.stringified (`:147`); anything else
  (string, `FormData`, etc.) passed through as-is — but `Content-Type:
  application/json` is still forced unless the caller explicitly overrides
  `headers['Content-Type']`, which would break a `FormData` upload's
  multipart boundary. **[RISK]** — no current caller does this (confirmed no
  `FormData` usage in this phase's grep), but it's a landmine for anyone
  adding a multipart upload through `apiFetch`.
- **No blob/binary response support** (`:170-180`): response parsing branches
  only on `content-type` — `application/json` → `response.json()`; anything
  else → `response.text()` wrapped as `{ ok: response.ok, data: text }`. There
  is no `response.blob()` / `arrayBuffer()` path anywhere in the file.
  **[CONFIRMS-PLAN]** — directly answers WP3.5's open question: *"Exports/downloads
  that stream blobs may keep raw fetch if the wrapper doesn't support
  blobs."* Confirmed: it does not. Any WP3.5 migration touching
  `exports.js`'s Excel-download raw `fetch()` calls must keep those as raw
  `fetch()` (or extend the wrapper with a `responseType: 'blob'` option
  first) — do not attempt a naive swap.
- **Response/error envelope** (`:171-237`): success path returns the parsed
  `data` object as-is (with `data.requestId` backfilled if missing,
  `:183-185`) — callers get the raw `{ok, status, data, error}` shape
  documented in `.claude/rules/frontend.md`'s "API response shape" section,
  not a further-unwrapped `.data`. On HTTP error (`!response.ok`,
  `:188-205`) or thrown JS error (network failure, JSON parse failure)
  (`:211-237`), the function **throws** a normalized `{code, message,
  requestId}` object (`normalizeError()`, `:51-81`) rather than returning it.
  Callers must `try/catch` `apiFetch`/`api.*` calls; there is no
  `.ok`-checking success/failure return contract at the call site — this
  matches what `workout-plan.js`, `volume-splitter.js`, etc. actually do
  (all wrap calls in try/catch, confirmed in earlier phases). **[NEW]** —
  worth stating explicitly for Phase 3 JS-split executors: `apiFetch` is
  throw-on-error, not a Result-object return; any refactor that changes call
  sites must preserve try/catch, not switch to `if (!result.ok)` checking.
- **Retry logic** (`:128`, `:166-239`): default `retries = method === 'GET' ?
  2 : 0`. Retry only fires when `method === 'GET' && attempt < retries`
  (`:213`) — non-GET requests never retry regardless of the `retries` option
  a caller might pass, since the retry gate is hardcoded to check
  `method === 'GET'` rather than trusting the caller's `retries` value.
  **[NEW]** — minor: a caller can't opt a POST into retries by passing
  `{retries: 2}`; the option is silently ignored for non-GET. No current
  caller does this (spot check: no `.js` file in the repo passes an explicit
  `retries` option to `apiFetch`/`api.*`), so this is latent, not exercised.
- **Global loading indicator** (`:13, 18-39, 159-163, 240-245`): a single
  module-level `activeRequests` counter drives a DOM-injected
  `#global-loading-indicator` spinner, shown/hidden via `.active` class
  toggling in a `finally` block — correctly decrements even when the request
  throws. `showLoading` defaults to `true`; callers can opt out per-call.
  Self-contained, no external dependency beyond `document.body`.
- **Error-toast auto-firing** (`:200-201`, `:232-235`): both the HTTP-error
  and thrown-error branches call `showToast('error', errorInfo.message,
  {requestId})` directly unless `showErrorToast: false` is passed. This means
  **every caller that doesn't explicitly suppress it gets an automatic error
  toast from the wrapper itself**, independent of whatever toast logic the
  caller's own `catch` block adds. **[RISK]** — double-toast potential:
  if a call site's `catch (error) { showToast('error', error.message) }`
  doesn't pass `showErrorToast: false`, the user could see two error toasts
  for one failure (one from the wrapper, one from the catch block). Not
  verified against every call site in this phase (that's Phase 3/JS-module
  territory), but flagging because WP3.5's migration of raw `fetch()` calls
  to `apiFetch` needs to check whether the destination call site already
  shows its own error toast — if so, it must pass `showErrorToast: false` to
  avoid a duplicate.
- `isHandledApiError()` / `HANDLED_UI_ERROR_CODES` (`:8, 87-89`): a fixed set
  `{VALIDATION_ERROR, NOT_FOUND, NO_DATA}` — errors with these codes are
  logged via `console.warn` instead of `console.error` by `logApiError()`
  (`:95-98`), and are treated as "expected" by consuming modules (confirmed:
  `exports.js`, `workout-log.js`, `workout-plan.js` use
  `isHandledApiError(error) ? 'warning' : 'error'` when choosing toast type).
  This is a small, deliberate UX classification layer, not dead code.
- `normalizeError()` (`:51-81`) has a comment-documented idempotency guard at
  `:52-55` ("already normalized... return as-is to prevent
  double-normalization") — evidence this function is called more than once
  on the same error object across the retry/catch chain (`:189` then
  potentially `:223` on the same thrown value), and someone already hit and
  fixed a double-normalization bug here. No further issue found; the guard
  works correctly (checks `error.code && error.message &&
  !(error instanceof Error)`).
- No dead code in this file. `api.put`/`api.patch`/`api.delete` are exported
  but grep shows only `api.get`/`api.post` actually used anywhere
  (spot-checked `workout-plan.js`, `volume-splitter.js`, `user-profile.js` in
  earlier phases) — **[NEW]**, low priority: unused convenience methods, not
  worth deleting (cheap to keep, plausible near-term use), but note for
  anyone doing a "is this API surface used" sweep.

---

## static/js/app.js (298 lines)

**Orchestrator + one raw fetch + a real toast-signature bug.**

- Import block (`:1-33`): pulls named exports from 20 different feature
  modules. This is the wiring hub, not business logic — matches
  `static/js/CLAUDE.md`'s description ("Top-level entry hooked from
  `base.html`").
- `window.*` assignment inventory (`:43-62`, plus `:65` for
  `generateStarterPlan`): **21 global assignments** — `addExercise`,
  `removeExercise`, `clearWorkoutPlan`, `exportToExcel`, `exportToWorkoutLog`,
  `exportSummary`, `deleteWorkoutLog`, `updateExerciseDetails`,
  `updateExerciseForm`, `updateProgressionDate`, `updateProgressionStatus`,
  `validateScoredValue`, `checkProgressionStatus`, `handleAddExercise`,
  `updateScoredValue`, `handleDateChange`, `importFromWorkoutPlan`,
  `confirmClearWorkoutLog`, `showAutoBackupBanner`, `fetchWorkoutPlan`,
  `generateStarterPlan`. All exist to satisfy inline `onclick="..."` handlers
  in templates (ES module scope isn't otherwise reachable from inline HTML
  attributes) — this is the standard, deliberate bridge pattern for a
  no-bundler ES-module setup, not accidental pollution. **[NEW]** — worth
  recording as the authoritative list for Phase 3 (WP3.2/3.3/3.4 template
  extraction work): any inline-script extraction must preserve every one of
  these 21 names on `window`, or find+update the corresponding
  `onclick`/inline-handler references in templates.
- **The one raw `fetch()` call** (`:117-134`, inside
  `window.generateStarterPlan`): confirmed exactly one raw `fetch()` in this
  file, matching WP3.5's count claim ("`app.js` (1 each)"). It POSTs to
  `/generate_starter_plan` with manually-built headers
  (`Content-Type: application/json` only — no `X-Requested-With`, no
  `X-Request-ID`) and manually parses `response.json()` (`:136`), checking
  `response.ok && result.data` (`:138`) rather than the `apiFetch`
  throw-on-error contract. **[CONFIRMS-PLAN]** — a direct, literal migration
  target for WP3.5; the response-shape check (`result.data` truthy) is
  compatible with `apiFetch`'s pass-through-on-success behavior, so this one
  should convert cleanly (no blob/multipart complication like the exports
  path).
- **Toast-type bug in the same function** (`:99, 111, 158, 162`): four calls
  use the *legacy* `showToast(message, isError)` two-arg form but pass a
  **string** (`'warning'`, `'success'`, `'error'`) as the second argument
  instead of a boolean:
  - `:99` — `showToast('Please select at least one equipment type.', 'warning')`
  - `:111` — `showToast('Maximum 2 priority muscles allowed...', 'warning')`
  - `:158` — `showToast(errorMsg, 'error')`
  - `:162` — `showToast('Error generating plan. Please try again.', 'error')`

  Tracing this through `toast.js`'s legacy-compat branch (`toast.js:14-31`):
  when `type` (the first positional arg) isn't one of the four valid type
  strings, the function treats the call as legacy `showToast(message,
  isError, duration)`. It computes
  `legacyIsError = typeof message === 'boolean' ? message : false` — and
  here `message` (the second arg) is the *string* `'warning'`/`'error'`, not
  a boolean, so `legacyIsError` is **always `false`**, and the resulting
  toast type becomes **`'success'`** (green) regardless of the intended
  warning/error styling (`toast.js:21`). **[RISK] — confirmed live bug.**
  `:99` and `:111` show a green "success" toast for what's meant to be a
  validation warning; `:158` and `:162` show a green "success" toast for an
  actual plan-generation *failure* message — i.e., a user sees a green toast
  bearing an error message after a failed API call. This is pre-existing
  behavior (not introduced by this scan), reachable via the "Generate
  Starter Plan" modal's equipment-checkbox validation and the catch/error
  branches of `window.generateStarterPlan`. Every other `showToast` call
  site surveyed in this phase's grep uses either the correct
  `showToast('type', message)` object-style call or the correct
  `showToast(message, true)` boolean legacy form — `app.js` is the only file
  using the broken string-as-second-arg pattern. Fix is a one-line-per-call
  change to `showToast('warning', ...)` / `showToast('error', ...)` (object
  style), no `toast.js` change needed. Not in current REFACTOR_PLAN scope
  (behavior-preserving-only rule would technically forbid fixing this as
  part of a refactor WP) — flagging for a bug-fix ticket, not a WP.
- Page-initializer registry (`:243-276`): a `pageInitializers` map keyed by
  `window.location.pathname`, dispatched once on `DOMContentLoaded`. Clean,
  small, no dead branches — every key (`/`, `/workout_plan`, `/workout_log`,
  `/weekly_summary`, `/session_summary`, `/progression`, `/volume_splitter`,
  `/backup`) has a real initializer function above it. Missing from this map:
  `/user_profile`, `/body_composition` — presumably those pages self-initialize
  via their own module's DOMContentLoaded listener (confirmed pattern exists
  in `navbar-enhancements.js` and `darkMode.js`; not verified against
  `user-profile.js` in this phase, would need Phase 3/user-profile phase to
  confirm). **[NEW]** — not a bug, just noting the registry is deliberately
  partial, not exhaustive.
- **Dead/vestigial `initializeModules()` function** (`:278-289`): defines a
  `switch` statement with a comment `// ... other cases ...` and exactly one
  real case (`/progression`, duplicating `initializeProgressionPage()` which
  is *also* already wired through `pageInitializers` at `:249`). This
  function is **never called anywhere** — confirmed by grep across
  `static/js/`: `initializeModules` has zero call sites, only its own
  definition. **[NEW] — dead code.** Candidate for Phase 0 deletion
  (`docs/REFACTOR_PLAN.md` WP0.1/WP0.2 territory) or a small follow-up;
  qualifies under rule 8 (repo-wide grep returns only the definition, not
  decorator-registered, not nested in a `register_*` function).
- Final `DOMContentLoaded` block (`:292-298`): defensively removes stray
  `#eraseDataBtn`/`.erase-data-btn` elements outside `.welcome-container`.
  Standalone, harmless, no findings.
- `APP_DEBUG` / `appDebugLog` (`:35-40`): a hardcoded-`false` debug flag
  gating a `console.log` wrapper, used by every `initializeXPage` function's
  entry/cleanup logging. Since `APP_DEBUG` is a `const false` with no env-var
  or URL-param toggle, none of these debug logs ever fire in any
  environment. **[NEW]** — not exactly dead code (the mechanism works if
  someone flips the constant), but effectively inert in production and in
  every test run; low-value flag, could be deleted along with all
  `appDebugLog(...)` call sites for a small win, or left as an actually-used
  manual-debugging toggle (developer intent unclear from the code alone).

---

## static/js/modules/ui-handlers.js (443 lines)

**A genuine grab-bag, confirming the plan's suspicion — five unrelated
concerns in one file, only loosely bound by "runs on every page."**

- `addCustomSpinnerButtons(input)` (`:9-94`, not exported): injects custom
  +/- buttons into number inputs, with **inline hardcoded styles**
  (`:29-35, 42`) rather than CSS classes — `border: 1px solid #ccc`,
  `background: #f8f9fa`, `color: #495057`, etc., baked directly into
  `style.cssText`. **[RISK]** — these hardcoded colors bypass the dark-mode
  token system entirely (`.claude/rules/frontend.md`'s "Dark mode... driven
  by custom-property swaps" convention, and the CSS Phase 4 tokenization
  effort). A spinner button injected via this function will not adapt to
  `data-theme="dark"` — it always renders light-mode colors. Worth a note
  for Phase 4 (CSS cleanup/tokenization) since this is a JS-injected style,
  not a stylesheet rule, so a CSS-only tokenization pass will miss it.
- `initializeUIHandlers()` (`:96-329`, the biggest export, 233 lines):
  internally combines (a) inline-edit-cell click/blur/keydown wiring for
  `.editable` table cells (workout-log-style edit-in-place), (b) date-input
  change wiring, (c) global click-outside-to-close handling, (d) routine
  dropdown click-state styling, (e) a call to
  `initializeSummaryMethodHandlers()` (weekly/session summary method
  dropdown), and (f) spinner-input debounced-save logic
  (`inputDebounceTimers`, 500ms debounce) tied to `window.updateScoredValue`
  (a global assigned in `app.js:57`). **[CONFIRMS-PLAN]** — this single
  function is doing workout-log editable-cell logic, summary-page dropdown
  logic, and generic spinner mechanics all at once, none of which relate to
  each other except "DOM setup on page load." A clean split would separate
  editable-cell logic (workout-log-specific) from the generic spinner/dropdown
  helpers.
- Five separate top-level `document.addEventListener('click', ...)` /
  `mouseup` listeners are registered across this one function
  (`:165, 195, 212`) plus more inside the `.editable-input` loop
  (`:262, 273`) — each doing its own closest()/classList work independently
  rather than a single delegated handler. Not a correctness bug (browsers
  handle many listeners fine), but it's the kind of accretion pattern that
  explains why the file grew grab-bag-like: features were added by appending
  another top-level listener rather than integrating into a shared
  dispatcher.
- `initializeFormHandlers()` (`:331-352`): two unrelated concerns — (1) an
  `add-exercise-btn` click listener whose body is **only a `console.log`**
  with a comment `"The actual addExercise function will be imported where
  needed"` (`:333-339`) — i.e., **this listener does nothing functionally**;
  the real add-exercise wiring happens elsewhere (`exercises.js`,
  `workout-plan.js`, confirmed via `window.addExercise`/`handleAddExercise`
  globals from `app.js`). **[NEW] — near-dead code**: the listener fires and
  logs on every "Add Exercise" click across every page that has this button,
  purely for a debug console line, doing no other work. Cheap to keep but
  arguably confusing (looks like exercise-adding logic lives here; it
  doesn't). (2) Bootstrap `.was-validated` form-validation wiring
  (`:342-351`) — unrelated, generic, fine.
- `initializeTooltips()` (`:354-359`) and `initializeDropdowns()`
  (`:361-367`): two near-identical 6-line Bootstrap-component initializers.
  Both simple, no findings, but reinforce the "small unrelated exports
  bundled together" pattern.
- `handleTableSort()` (`:369-390`): generic client-side table sorter keyed
  off `th[data-sort]` / `td[data-<column>]` attributes, string-locale-compare
  only (no numeric-aware sort) — **[NEW]**, minor: sorting a numeric column
  (e.g. weight, reps) with `localeCompare` will sort lexicographically
  ("10" before "2"), not numerically. Not verified whether any current
  `data-sort` table actually has numeric columns relying on correct numeric
  order (would need a template-level check outside this phase's scope) —
  flagging as a possible latent UX bug, not confirmed exploited.
- `initializeCharts()` (`:392-410`): **chart-bootstrapping logic sharing a
  file with editable-cell/spinner/tooltip/dropdown/sort code** — reads
  `data-chart`/`data-chart-data` attributes and dispatches to
  `createVolumeChart`/`createProgressChart` from `charts.js`. This is the
  fifth unrelated concern in the file and the one most clearly belonging in
  `charts.js` or its own module instead of `ui-handlers.js`.
  **[CONFIRMS-PLAN]**.
- `initializeSummaryMethodHandlers()` (`:412-426`, not exported, called only
  from inside `initializeUIHandlers()`): wires the `#summary-method` `<select>`
  to `fetchWeeklySummary`/`fetchSessionSummary` based on
  `window.location.pathname`. Page-specific logic nested inside a
  page-agnostic "common init" function — another instance of the
  cross-cutting/page-specific blur this file has throughout.
- `initializeSuggestionCards()` (`:428-438`) + its own standalone
  `document.addEventListener('DOMContentLoaded', ...)` call (`:441-443`,
  **separate from and in addition to** `app.js`'s own `DOMContentLoaded`
  listener that calls `initializeUIHandlers()` etc.): wires `.expand-toggle`
  clicks inside `.suggestion-card` elements to toggle an `.expanded` class
  and swap "Show More"/"Show Less" text. **[RISK] — likely dead/orphaned
  logic.** Grepped `.suggestion-card` / `.expand-toggle` across the repo:
  `.suggestion-card` markup exists in `volume-splitter.js:375` and
  `progression-plan.js:367,526` (both dynamically generate
  `<div class="card suggestion-card ...">` at runtime, i.e. **after**
  `DOMContentLoaded` has already fired), but neither of those markup sites —
  nor any CSS file, nor any template — contains an `.expand-toggle` element
  or class. `initializeSuggestionCards()` runs once at `DOMContentLoaded` and
  attaches listeners only to `.suggestion-card` elements that exist in the
  DOM *at that moment* (there are none on the two pages that create
  suggestion cards, since those cards are injected later via JS), and even
  if timing lined up, there is no `.expand-toggle` child for it to find in
  either producer. This function is a no-op today: it always queries zero
  matching elements. Candidate for Phase 0 dead-code review (needs the
  repo-wide-grep-and-confirm treatment per rule 8, but the pieces line up
  cleanly for "orphaned by a since-removed or since-changed feature").
- No `window.*` assignments in this file — all exports are ES-module named
  exports consumed by `app.js`'s import block, correctly following the "no
  global pollution from feature modules" pattern (the pollution is
  centralized in `app.js` by design).

---

## static/js/modules/navbar.js (58 lines) vs. static/js/modules/navbar-enhancements.js (316 lines)

**Clean split, not actually overlapping — the plan's "watch for overlap"
concern doesn't pan out.**

- `navbar.js` exports exactly two functions: `initializeNavHighlighting()`
  (`:1-37`, sets `.active` class on the current-page nav item via a
  `pathMap` lookup — 10 mapped routes) and `initializeNavbar()`
  (`:40-58`, a thin wrapper that calls `initializeNavHighlighting()` on
  `DOMContentLoaded`/immediately, then re-runs it on `popstate`, `load`, and
  `hashchange`). Pure "which nav link is active" concern only.
- `navbar-enhancements.js` covers three unrelated-to-highlighting concerns:
  scroll-triggered compact mode (`:19-56`), mobile-menu focus-trap + body
  scroll lock (`:58-214`), and desktop hover-dropdown mechanics
  (`:217-309`). Zero overlap in responsibility with `navbar.js` — confirmed
  by reading both fully; neither touches `.active` classes or `pathMap`, and
  `navbar.js` never touches scroll/focus/hover state.
- **Double self-initialization risk, but currently harmless**:
  `navbar-enhancements.js` has its own bottom-of-file self-invoking init
  (`:311-316`: `if (document.readyState === 'loading') { ... } else {
  initializeNavbarEnhancements(); }`), **and** `app.js:172` explicitly calls
  `initializeNavbarEnhancements()` again. If `app.js` is a `<script
  type="module">` (confirmed — `static/js/CLAUDE.md`: "Modules are loaded
  with `<script type="module">`"), module scripts are deferred by spec, so
  by the time `app.js`'s top-level code runs, `document.readyState` is
  already `'complete'`/`'interactive'`, meaning the file's own bottom-of-file
  guard takes the `else` branch and calls `initializeNavbarEnhancements()`
  immediately at **module load time** (i.e., when the browser parses/
  evaluates `navbar-enhancements.js`, which happens when `app.js`'s
  `import` for it is resolved — before `app.js`'s own body runs). Then
  `app.js:172` calls it again explicitly. **[RISK] — confirmed double-init.**
  `initializeNavbarEnhancements()` itself has a per-navbar re-entrancy guard
  for the hover-dropdown sub-feature only
  (`initializeDesktopHoverDropdowns`, `:218-219`:
  `if (navbar.dataset.hoverDropdownsInitialized === 'true') return;`), but
  **no equivalent guard on the outer function** — the scroll listener
  (`window.addEventListener('scroll', onScroll, {passive: true})`, `:53`)
  and resize listener (`:214`) get attached **twice** on every page load,
  meaning `handleScroll()` and `handleResize()` each run twice per
  scroll/resize event. Both are idempotent (just toggling a CSS class /
  checking `innerWidth`), so there's no visible bug today, but it's
  duplicated work on every scroll frame (mitigated by the `ticking` RAF
  throttle at `:42-51`, but that throttle is a per-listener-registration
  closure variable, not a global lock — since the function runs twice, there
  are literally two independent `ticking` closures, i.e. two separate RAF
  schedules per scroll frame instead of one). Confirmed no crash/visible
  defect, but this is real double-work that a Phase 3 JS-split executor
  should collapse (add a module-level or `navbar.dataset` init guard to
  `initializeNavbarEnhancements()` itself, matching the pattern already used
  for the hover-dropdown sub-piece).
- `window.navbarUnlockBodyScroll` (`:142`): one global assignment, used
  internally by the module's own `handleResize()` (`:208`) to call
  `unlockBodyScroll()` — this looks like it should just be a closure
  reference (both functions are already in the same closure scope inside
  `initializeNavbarEnhancements()`), not a global. **[NEW]** — the global
  appears unnecessary: `handleResize` could call `unlockBodyScroll()`
  directly since they're both declared in the same function body 60 lines
  apart. No other file in the repo references
  `window.navbarUnlockBodyScroll` (confirmed by earlier grep — only
  `navbar-enhancements.js` itself contains the string). Given the
  double-init issue above, this global also gets reassigned to a second,
  functionally-identical closure on the second `initializeNavbarEnhancements()`
  call — harmless since both closures do the same thing, but it's an
  unnecessary indirection either way.

---

## static/js/modules/navbar-enhancements.js — accessibility details

(Covered above jointly with navbar.js; additional accessibility-specific
notes:)

- Focus trap (`:84-107`) and `inert`/`aria-hidden` fallback
  (`:110-139`) are implemented with a manual feature-detect (`'inert' in
  mainContent`) and a `try/catch` fallback to `aria-hidden` — reasonable
  defensive coding for browser-support variance, not overengineered (single
  `if`/`catch`, no speculative extra branches).
- `desktopHoverQuery` media-query-driven dropdown behavior (`:223-308`)
  correctly re-checks `isDesktopHover()` on every interaction rather than
  caching the media-query result once, so resizing across the 992px/hover
  breakpoint mid-session works — verified via the `change` listener at
  `:303-307` that resets state when the query result flips.

---

## static/js/accessibility.js (264 lines)

**Tightly coupled to `a11y.css` class/attribute contract — confirmed, not
just plausible.**

- IIFE, not an ES module (`(function() { 'use strict'; ... })()`, `:6-264`)
  — the only non-module file in this phase's set besides `darkMode.js`.
  Loaded via a plain `<script src="...">` tag in `base.html:300` (confirmed
  by grep), not `type="module"`, consistent with it needing to run and
  attach `window.AccessibilityController` / `window.accessibilityController`
  (`:259, 262`) before other page scripts might reference the global (no
  confirmed external reader of these globals in this phase's grep, but the
  IIFE + explicit global-export pattern signals intent for external access,
  e.g. from inline template scripts not covered by this phase).
  **[NEW]** — worth noting for WP3.2 (inline-script extraction): if any
  inline template script reads `window.accessibilityController`, that
  dependency must survive the extraction; not verified in this phase (would
  need a grep across `templates/**/*.html` for `accessibilityController`,
  out of scope here).
- Dual persistence: `localStorage` (`STORAGE_KEY = 'ui-scale-level'`,
  `:9, 53-62`) for client-side reads, **and** a mirrored cookie
  (`syncCookie()`, `:40-48`; `saveScale()`, `:67-71`) so the **server** can
  read the scale on SSR (comment at `:38`: "server reads cookie for SSR").
  This is a real cross-cutting concern between this JS file and Flask
  template rendering — not verified in this phase whether `templates/`
  actually reads a `ui-scale-level` cookie server-side (would need a
  routes/templates phase to confirm), but the code's own comments assert it
  does. **[NEW]** — flag for whoever eventually audits `templates/base.html`
  or `app.py` for cookie-reading logic; this JS file's behavior only makes
  sense in light of a server-side consumer.
- `applyScale()` (`:78-99`): sets `data-scale` attribute on `<html>` (read
  by `a11y.css`'s `html[data-scale="N"]` rules, confirmed by the earlier
  grep hit-list — 8 scale levels, `:24-73` in `a11y.css`) and separately
  handles Firefox specially (`:86-95`) by skipping the CSS `zoom` property
  entirely (comment: "Firefox doesn't [support zoom]... buggy zoom
  behavior") and only setting a `--ui-scale` custom property instead — which
  per the same comment/code has **no actual effect in Firefox** beyond
  setting an inert CSS variable ("Just update the CSS variable for potential
  future use"). **[NEW]** — confirms accessibility scaling is **non-functional
  on Firefox by design**, a real gap (Firefox users get `data-scale`
  attribute + inert CSS var but no visual zoom), not a bug introduced by
  this file — it's an explicit, commented trade-off. Not flagged as
  [RISK] since it's a known, documented limitation rather than a silent
  failure, but material for anyone doing accessibility-coverage work.
- Keyboard shortcuts (`:233-256`, Ctrl/Cmd +/-/0) are global `keydown`
  listeners with no scoping to a focused control and no check for whether
  the user is typing in an input/textarea — pressing Ctrl+Plus while typing
  in *any* text field on the page (e.g., an exercise search box) would still
  trigger `increaseScale()` rather than the browser's native
  zoom-page behavior, since `e.preventDefault()` fires unconditionally
  (`:241, 246, 251`) whenever the modifier + key combo matches, regardless
  of `e.target`. **[RISK]** — likely intentional (the whole point is to
  override native browser zoom with the app's own scale system), but it
  means there's no way for a user to trigger native browser zoom via
  keyboard on this page at all, and no escape hatch (e.g. holding an
  additional modifier) — a minor UX tradeoff, not a functional bug.
- `updateControlsUI()` (`:200-228`) and `setupControls()` (`:142-195`)
  correctly guard every DOM lookup with `if (el)` before use — no crashes if
  a page doesn't render the accessibility dropdown/buttons (confirmed
  defensive, appropriate given this script loads globally on every page per
  `base.html`, but not every page necessarily renders the full accessibility
  UI).
- No dead code identified in this file — every method is called from either
  `init()`, `setupControls()`, or a keyboard/click listener that is itself
  wired in `setupControls()`.

---

## static/js/modules/workout-controls-animation.js (175 lines)

- Single export, `initializeWorkoutControlsAnimation()` (`:165-176`), gated
  on `document.querySelector('[data-section="controls"]')` — a clean,
  page-scoped no-op guard (matches the "Workout Plan" page's Workout
  Controls panel; confirmed called from `app.js:219` inside
  `initializeWorkoutPlan()` only, so it never runs on other pages even
  though the module itself has no route-based gating beyond the DOM check).
- `WORKOUT_CONTROL_IDS` (`:11-18`, six literal input IDs: `weight`, `sets`,
  `rir`, `rpe`, `min_rep`, `max_rep_range`) — a hardcoded ID list rather than
  a class-based or data-attribute-based selector. **[NEW]** — mild
  brittleness: if `workout-plan.js`/its template ever renames one of these
  input IDs, this file silently stops animating that field (no error, no
  warning, `initializeInputAnimation` just returns early at `:104` if
  `!input`). Low risk since these are core, stable form-field IDs, but worth
  noting as a coupling point for whoever eventually touches the Workout
  Controls markup (WP3.3/3.4 territory).
- Four different event types (`input`, `mouseup`, `wheel`, `keydown`, plus
  `change` as a fifth fallback) are all wired per-input (`:110-158`) purely
  to catch every possible way a number input's value can change (typing,
  spinner click, scroll-wheel, arrow keys, blur-after-change) and re-trigger
  the same `triggerValueChangedAnimation()`. This is thorough but also
  somewhat redundant — e.g., a spinner click fires both `mouseup` and
  `change`, so `triggerValueChangedAnimation` (which is idempotent — it
  removes-then-re-adds the CSS class, `:25-41`) gets called twice for one
  logical value change. Harmless (the class-remove/re-add + `setTimeout`
  reset pattern tolerates redundant calls cleanly), just not minimal.
- No `window.*` pollution, no dead code, no toast/API interaction (pure
  DOM/CSS-class animation, no network calls) — the cleanest, most
  single-purpose file in this phase.

---

## static/js/modules/toast.js (111 lines)

**The shared notification primitive every other module in the app depends
on — confirmed via the grep in this phase's investigation (60+ call sites
across 15+ files).**

- Single export, `showToast(type, message, options)` (`:11-110`). Supports
  **two call signatures** simultaneously: the documented new form
  `showToast('success'|'error'|'warning'|'info', message, {duration,
  requestId, action})`, and a legacy back-compat form
  `showToast(message, isErrorBoolean, durationNumber)` detected by checking
  whether the first argument is one of the four valid type strings
  (`:12-31`). This dual-signature design is deliberate (comment at `:14`:
  "Backward compatibility: detect legacy signature") and is why so many call
  sites across the codebase still use the old two-arg boolean form
  (`showToast('message', true)`) alongside newer object-style calls — both
  work correctly **as long as the second argument is actually a boolean**.
  **[CONFIRMS-PLAN root cause]** — this dual-signature design is exactly
  what makes `app.js`'s `showToast(msg, 'warning')` bug (documented above,
  `app.js:99,111,158,162`) possible: the legacy-detection branch has no
  validation that a non-boolean second argument is a programmer mistake; it
  silently coerces anything non-boolean to `false` (`:17`), so a string like
  `'warning'` or `'error'` passed where a boolean is expected fails silently
  into the `'success'` default rather than throwing or warning. A stricter
  legacy-branch guard (e.g., `typeof message !== 'boolean' && message !==
  undefined` triggering a `console.warn`) would have caught this class of
  bug at the source instead of at whichever call site misuses it.
- Action-button support (`:65-85`): an optional inline button inside the
  toast body, wired to `bootstrap.Toast.getInstance(toastElement)?.hide()`
  before running the caller's `onClick`, itself wrapped in try/catch
  (`:78-81`) so a broken action handler can't leave the toast stuck or throw
  unhandled. Used by at least `progression-plan.js` (not read this phase,
  referenced via the `action` param shape in the JSDoc) — clean, defensive
  implementation.
- Depends on two fixed DOM IDs existing in `base.html`: `#toast-body`
  (`:35`) and `#liveToast` (`:41`) — both guarded with early-return +
  `console.error` if missing (`:36-39, 42-45`), so a template regression
  (removing the toast markup) fails loud in the console rather than
  throwing, though it does mean an error toast call effectively becomes a
  silent (from the user's perspective) console-only failure if the markup is
  ever missing.
- Depends on the global `bootstrap` object (`:74, 103, 108` — Bootstrap's
  `Toast` class) being available — same pattern as `ui-handlers.js`'s
  `initializeTooltips()`/`initializeDropdowns()`, consistent with Bootstrap
  being loaded as a separate non-module global script (confirmed pattern
  across this and Phase-13-adjacent files, not re-verified here).
- No dead code; every branch (legacy-detect, numeric-duration-shorthand at
  `:28-31`, action button, background-class mapping `:91-98`, existing-toast
  disposal `:101-106`) is exercised by real call sites surveyed in this
  phase's grep.

---

## static/js/darkMode.js (81 lines)

**Confirmed as the single source of truth for `data-theme` stamping.**

- Not an ES module (plain `function DarkMode() {...}` + prototype methods,
  `:1-79`), self-instantiated via `document.addEventListener('DOMContentLoaded',
  () => new DarkMode())` (`:82`) — loaded as a plain script, matching
  `static/js/CLAUDE.md`'s description ("Theme toggle + `localStorage`
  persistence").
- Early-returns entirely if `#darkModeToggle` doesn't exist (`:3`) — so this
  script is a safe no-op on any page missing the toggle button (though
  `base.html:208` confirms the toggle is in the shared navbar, present on
  every page).
- Theme resolution priority (`:6-8`): explicit `localStorage.getItem('darkMode')`
  wins if set; otherwise falls back to `window.matchMedia('(prefers-color-scheme:
  dark)').matches` (system preference). This exactly matches the CLAUDE.md
  memory note's framing of `data-theme` stamping ("the viewer's theme toggle
  stamps `data-theme` on the root element") from the Artifact-tool
  instructions elsewhere in this environment — confirms the same convention
  is used app-wide, not just in generated artifacts.
- `applyTheme(isDark, animate)` (`:56-79`) sets `data-theme="dark"|"light"`
  directly on `document.documentElement` (`:64-66`) — this is the exact
  attribute `a11y.css` (`[data-theme="light"] .scale-indicator`, etc.,
  confirmed in the earlier grep) and presumably `theme-dark.css`
  (referenced in `.claude/rules/frontend.md`, not read this phase) key off
  of. The `animate` flag (`:59-60, 69-78`) adds/removes a `theme-animating`
  class around the swap using a double-`requestAnimationFrame` to let one
  paint happen with transitions disabled before re-enabling them — a
  reasonable technique to avoid a flash of transitioning colors on toggle,
  correctly *not* applied on initial page load (`applyTheme(this.isDarkMode,
  false)` at `:10` — no animation flash on first paint).
- System-preference live-sync (`:22-35`): if the user has never made an
  explicit choice (`stored === null`), a `matchMedia` `change` listener
  keeps the theme in sync with OS-level dark/light switches even after page
  load, with an `addListener` fallback for older browsers (`:32-33`) —
  small, correct, no findings.
- No `window.*` global export — `DarkMode` the constructor is never exposed
  globally, unlike `AccessibilityController`. **[NEW]** — inconsistent with
  `accessibility.js`'s explicit `window.AccessibilityController` /
  `window.accessibilityController` export pattern; no evidence anything
  needs `DarkMode` externally today (no grep hits for `window.DarkMode` or
  an instance reference anywhere), so this is a documentation-of-inconsistency
  note, not a bug.

---

## Cross-cutting seeds

1. **`app.js`'s `showToast(message, 'warning'|'error'|'success')` calls are
   a confirmed, reachable, pre-existing bug** — four call sites
   (`app.js:99,111,158,162`) misuse `toast.js`'s legacy two-arg signature by
   passing a string instead of a boolean as the second argument, causing
   every one of them to render as a green "success" toast regardless of
   intent (two are meant to be warnings, two are meant to be errors on
   actual API failure). Root cause lives in `toast.js`'s legacy-detection
   branch (`toast.js:17`, silently coerces non-boolean to `false`). Fix is
   trivial (`showToast('warning', ...)` / `showToast('error', ...)`
   object-style) but is a **behavior change**, so it doesn't fit
   `docs/REFACTOR_PLAN.md`'s "behavior-preserving only" global rule 1 as a
   refactor WP — recommend filing it as a standalone bug-fix ticket, not
   folding it into WP3.5 (which touches the same file for the raw-fetch
   migration and could pick this up as a drive-by fix if the owner
   approves an exception).

2. **`fetch-wrapper.js` has zero blob/binary response support** — confirmed
   by full read of the response-parsing branch (`fetch-wrapper.js:170-180`,
   JSON-or-text only). This directly resolves WP3.5's open question:
   Excel-export / streaming-download raw `fetch()` calls (in `exports.js`
   per the plan's own file list) **cannot** be migrated to `apiFetch` as-is
   and must either stay raw or wait for a wrapper extension
   (`responseType: 'blob'` option) as a prerequisite sub-task.

3. **Double-initialization of `navbar-enhancements.js`** — the module
   self-invokes at the bottom of its own file (`:311-316`) *and* is
   explicitly called again from `app.js:172`. Because `app.js` is a deferred
   `type="module"` script, `document.readyState` is already past `'loading'`
   by the time the file's own guard runs, so the self-invoke fires
   immediately at import time, then `app.js` calls it a second time. The
   outer function has no re-entrancy guard (only its internal
   `initializeDesktopHoverDropdowns` sub-call does, via
   `navbar.dataset.hoverDropdownsInitialized`), so the scroll and resize
   listeners are attached twice per page load — duplicated (but idempotent
   and RAF-throttled per-registration) work on every scroll/resize event.
   Worth a one-line fix (add a `navbar.dataset.enhancementsInitialized`
   guard mirroring the existing hover-dropdown pattern) whenever this file
   is next touched — not urgent, no user-visible defect found.

4. **`window.*` pollution is centralized and, on inspection, well-justified
   — except for two smaller stragglers.** `app.js` intentionally exports 21
   functions to `window` to satisfy inline `onclick=` template handlers
   (the standard bridge for no-bundler ES modules); `accessibility.js`
   exports its controller class + singleton instance (justified — non-module
   script, potentially read by inline scripts elsewhere); but
   `navbar-enhancements.js`'s `window.navbarUnlockBodyScroll` (`:142`)
   appears to be an unnecessary global — both the setter and its one reader
   are declared in the same closure (`initializeNavbarEnhancements`'s body)
   and could reference each other directly. Low-priority cleanup candidate.

5. **Two confirmed dead/near-dead code items for the Phase 0 dead-code
   sweep**: `app.js`'s `initializeModules()` function (`:278-289`) has zero
   call sites anywhere in the repo (its one real case duplicates logic
   already wired through the `pageInitializers` map) — qualifies under
   REFACTOR_PLAN rule 8 for deletion. `ui-handlers.js`'s
   `initializeSuggestionCards()` (`:428-443`) targets a `.suggestion-card
   .expand-toggle` DOM shape that no longer exists anywhere in the
   templates or the two JS files (`volume-splitter.js`, `progression-plan.js`)
   that dynamically create `.suggestion-card` elements — both a timing
   mismatch (cards are injected after `DOMContentLoaded`) and a markup
   mismatch (`.expand-toggle` doesn't exist in either producer). Needs the
   formal rule-8 grep-and-confirm pass before deletion, but the evidence
   from this phase's reading points strongly at "orphaned by a since-changed
   suggestion-card design."

6. **`static/js/CLAUDE.md`'s file-role table is slightly incomplete for
   `fetch-wrapper.js`**: it lists only `apiFetch` and `api` as exports, but
   `isHandledApiError` and `logApiError` are also exported and are actively
   imported by at least three other modules (`exports.js`, `workout-log.js`,
   `workout-plan.js`, confirmed via grep in this phase) to decide
   warning-vs-error toast styling. Worth a doc update alongside any Phase 3
   work that touches this file, so future readers don't have to
   re-discover the full export surface by reading the source.
