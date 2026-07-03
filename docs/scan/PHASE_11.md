# Phase 11 — Templates (line-by-line audit)

Scope: all 16 files under `templates/` (root + `templates/partials/`), read in full.
Cross-referenced against `templates/CLAUDE.md`, `.claude/rules/frontend.md`, and
`docs/REFACTOR_PLAN.md` (WP3.2, Phase 4 CSS). Line numbers below are exact against the
files as they stand in this worktree (branch `scan/codebase-grounding`) at the time of
reading.

---

## templates/base.html (311 lines)

- `base.html:2` — `<html ... data-scale="{{ ui_scale_level }}" style="zoom: {{ ui_zoom_value }};">`.
  Inline `style=` on the root element driven by a template variable (presumably a context
  processor — not chased down in this phase, out of template scope). `zoom` is a
  non-standard CSS property (Chromium/WebKit only historically; Firefox added support only
  in v126+). This is the one legitimate, intentional exception to the frontend rule "Do not
  add inline theme styling" — it's a UI-scale value, not a dark/light theme value, but it's
  worth flagging as a template-level inline style that isn't obviously covered by the
  "dark-mode gotcha" carve-out. [NEW]
- `base.html:18-28` — the 8 global CSS bundles load in this order: `base.css`,
  `layout.css`, `components.css`, `navbar.css`, `a11y.css`, then `{% block page_css %}`,
  then `tokens.css`, `motion.css`, `theme-dark.css`. **`tokens.css` and `motion.css` load
  AFTER every route bundle**, and `theme-dark.css` loads dead last. This means route
  bundles (`pages-*.css`) cannot rely on cascade order to be overridden by tokens/motion,
  and any token defined in `tokens.css` that a route bundle also sets will lose to the
  route bundle in specificity ties (tokens.css comes later in source order but page CSS may
  have higher specificity selectors). Relevant to Phase 4 (WP4.1 tokenization / WP4.2-final
  shared-bundle retirement) — the plan should account for this load order, not assume
  tokens are already "first" or "last" cleanly. [NEW] [RISK: Phase 4 planning gap]
- `base.html:36-216` — navbar is fully hand-built (no partial/include), duplicated nowhere
  else — single source of truth, good.
- `base.html:219-226` — `<div id="main-content" class="container-fluid mt-4">` wraps
  `{% block content %}`. **This is a `<div>`, not a `<main>` landmark.** See "Cross-cutting
  seeds" below — this is the root cause of an accessibility-landmark inconsistency across
  child templates.
- `base.html:258-259` — `{% include "partials/exercise_video_modal.html" %}` (no `with
  context` — the partial doesn't need any parent variables, correct).
- `base.html:271-297` — inline `<script>` (non-module), **27 lines**: registers
  `DOMContentLoaded` (hides `#error-message-container`) + two `window.addEventListener`
  global error/rejection loggers. Small, but it is inline JS the WP3.2 audit note
  ("`base.html` inline blocks: audit, extract if non-trivial") should explicitly resolve —
  27 lines is small enough to reasonably call "trivial" and leave in place, but it's the
  kind of thing that should be a one-line decision recorded in the WP3.2 PR, not silently
  skipped. [CONFIRMS-PLAN — audit needed; recommend "leave in place, trivial"]
- `base.html:298,301,303,305` — four `<script>`/`<script type="module">` tags append
  `?v={{ range(1, 1000000) | random }}` as a cache-buster: `app.js`,
  `table-responsiveness.js`, `filter-view-mode.js`, `exercise-video-modal.js`. **Lines
  299-300 (`darkMode.js`, `accessibility.js`) do NOT get the cache-buster** — inconsistent
  treatment across the same script block, and more importantly: a `random()` value on
  *every server render* means these four files can never be validated against browser
  cache (the URL changes on every page load, forcing a full re-download every navigation).
  This isn't a correctness bug but is a real, unnecessary performance cost baked into the
  shared layout — every page navigation re-fetches 4 JS files that would otherwise be
  cacheable. [NEW] [RISK: perf, not in refactor plan scope but worth a follow-up ticket]
- No `|safe` filters in this file. No route bundles loaded here (correct — base.html only
  loads the 8 global bundles, route bundles are `{% block page_css %}` in children,
  matching `.claude/rules/frontend.md`).

## templates/error.html (51 lines)

- `error.html:3` — `{% block title %}{{ error_title }} - Hypertrophy Toolbox{% endblock %}`
- `error.html:12` — `<h1 class="error-status-code">{{ error_code }}</h1>`
- `error.html:15` — `<h2 class="error-title">{{ error_title }}</h2>`
- `error.html:18` — `<p class="error-message">{{ error_message }}</p>`
- `error.html:31-48` — optional `error_detail_code` / `request_id` block.
- **Confirmed exactly**: the template reads `error_title`, `error_code`, `error_message`,
  `error_detail_code`, `request_id` — five distinct context vars, **none of which is
  `message`**.
- Grepped every `render_template("error.html", ...)` call site in `routes/` (7 total):
  `routes/weekly_summary.py:129`, `routes/user_profile.py:469`,
  `routes/session_summary.py:146`, `routes/progression_plan.py:133`,
  `routes/program_backup.py:44`, `routes/body_composition.py:192` all pass **`message=`**
  (wrong kwarg name — Jinja's default `Undefined` silently renders `error_message` as
  empty string, so users see a blank `<p>`, blank `<h1>` status code, and a title that
  reads just `" - Hypertrophy Toolbox"`). Only `routes/fatigue.py:28` passes the correct
  `error_message=`. **Confirms the Phase-10 finding exactly: 6 of 7 call sites are broken;
  the 7th (fatigue.py) is correct.** None of the 7 call sites pass `error_title` or
  `error_code` either, so those two fields are *always* blank across all 7 paths,
  including the one "correct" fatigue.py call. [CONFIRMS-PLAN] [RISK: confirmed live bug]
- **New finding beyond Phase 10**: `error.html` is reached ONLY via these 7 manual
  `render_template()` calls inside route `except` blocks. The actual Flask
  `@app.errorhandler` registrations in `utils/errors.py` (400/404/422/500/generic
  `Exception` — the ones CLAUDE.md/WP0.1 confirmed are live decorator-registered closures)
  **do not use `error.html` at all**. They call a local `_html_error(status_code, title,
  message)` helper (`utils/errors.py:141-153`) that hand-builds a raw, unescaped HTML
  string (`f"<h1>{title}</h1>" ... f"<p>{message}</p>"`) and returns it directly via
  `make_response`. So the styled `error.html` (with its "Return to Home" / "Go Back"
  buttons, `error-page-container` CSS) is invisible on the app's actual global error paths
  (any unhandled 500, any 404, any bad request) — it only renders for the 7 specific
  try/except blocks that explicitly call it, and even then with blank title/code due to the
  kwarg bug above. Net effect: **no user-facing path currently renders `error.html`
  correctly with all fields populated.** [NEW] [RISK: two parallel, inconsistent
  error-rendering systems — `_html_error()` raw strings vs. `error.html` Jinja template —
  worth a Phase-0/Phase-1 follow-up WP to unify, out of scope for WP3.2 but adjacent]
- `_html_error()` interpolates `title`/`message` into an f-string without HTML-escaping
  (`utils/errors.py:141-153`). Currently safe because every call site passes a hardcoded
  literal string (verified — no user input reaches `title`/`message` there), but it's a
  latent injection pattern if a future edit ever threads request data into those params.
  [NEW] [RISK: low likelihood, notable pattern]

## templates/welcome.html (416 lines)

- `welcome.html:377-414` — inline `<script>`, **38 lines**: wires the "Erase All Data"
  modal, and does a **raw `fetch('/erase-data', ...)`** (`welcome.html:389`) — not
  `apiFetch`/`api` from `fetch-wrapper.js`. This is a raw-fetch call that WP3.5 ("Unify raw
  `fetch()` → `apiFetch`") does not enumerate — its list is `volume-splitter.js` (7),
  `exercises.js` (3), `exports.js` (2), `filters.js`, `muscle-selector.js`,
  `bodymap-svg.js`, `app.js` (1 each). This one lives inline in `welcome.html`, not in a
  `static/js/modules/*.js` file, so a grep over `static/js/` for WP3.5 scoping would miss
  it entirely. [NEW] [RISK: WP3.5 scope gap — this raw fetch will survive that WP unless
  someone greps templates too, or WP3.2's welcome.html extraction happens first and moves
  it into a real module]
- Same 38-line script also manually wires two Bootstrap `Toast` instances
  (`successToast`/`errorToast`) that duplicate the shared toast pattern documented in
  `.claude/rules/frontend.md` ("use `import { showToast } from './toast.js'`"). Welcome.html
  does not import `toast.js`; it re-implements toast display inline. [NEW] duplication.
- No page-specific JS module — `welcome.html` never has a `{% block page_js %}`, its
  entire interactivity is the one inline block. WP3.2's phrasing ("audit, extract if
  non-trivial") should resolve this: 38 lines, one modal + 2 raw-fetch/toast patterns, is
  non-trivial enough to extract and worth doing so specifically to route the fetch through
  `apiFetch` and the toasts through `toast.js` at the same time (kills two WP3.5-adjacent
  birds).

## templates/workout_plan.html (856 lines)

- `workout_plan.html:6` — loads `pages-workout-plan.css` (the CSS bundle flagged
  elsewhere in the repo as 8,226 lines / the single biggest bundle — Phase 4 target).
- `workout_plan.html:561-771` — inline `<script>` (non-module), **exactly 211 lines**.
  Contains `updateMuscleFilterDropdowns()`, the muscle-selector wiring, and the
  "Generate Starter Plan" modal preview logic (`updatePlanPreview`,
  `updateEquipmentForEnvironment`, volume-scale color coding).
  **This matches the REFACTOR_PLAN.md WP3.2 estimate of "~211" precisely.** [CONFIRMS-PLAN]
- `workout_plan.html:773-831` — a **second**, separate inline `<script type="module">`
  block, **59 lines**: wires `.collapse-toggle` click handlers for all
  `.collapsible-frame` sections on this page (Filters / Workout Controls / Exercise
  Selection). **WP3.2's "~211" figure for this file does not include this second block.**
  Total actual inline JS in `workout_plan.html` is **270 lines (211 + 59)**, not 211.
  [CONTRADICTS-PLAN — undercounts by 59 lines / ~28%]
- **New duplication finding**: the `.collapse-toggle` / `.collapsible-frame` toggle
  behavior implemented inline at `workout_plan.html:773-831` is **the third independent
  implementation of the same behavior** in this codebase — `static/js/modules/workout-log.js`
  and `static/js/modules/user-profile.js` both also implement `.collapse-toggle` wiring
  (grepped; both files match `collapse-toggle`/`collapsible-frame`), and neither shares
  code with the other or with this inline block. All three targets (`workout_plan.html`,
  `workout-log.js`, `user-profile.js`) render the same `frame-header-2025` /
  `collapsible-frame` markup pattern (also used by `body_composition.html`, which appears
  to have no collapse buttons and is therefore unaffected). This is a strong candidate for
  a shared `static/js/modules/collapsible-frame.js` extracted once, consumed by all three —
  not currently called out anywhere in `docs/REFACTOR_PLAN.md`. [NEW] [seed for WP3.2 or a
  new WP]
- `workout_plan.html:231,238,247,494-495,536,849` etc. — many `onclick="functionName()"`
  handlers calling globals (`exportToWorkoutLog`, `exportToExcel`, `generateStarterPlan`,
  `clearWorkoutPlan`, inline `document.querySelectorAll(...)` for the equipment
  all/none buttons at `workout_plan.html:494-495`). These globals are presumably defined in
  `static/js/modules/workout-plan.js` and attached to `window` — old-style
  `onclick=` + ES6-module-globals mixing, consistent with the WP3.3/WP3.4 plan to
  eventually decompose `workout-plan.js`, but worth noting the coupling is currently very
  tight: the template's markup directly names JS function symbols by string, so any
  WP3.3/3.4 rename must grep `templates/workout_plan.html` too, not just `static/js/`.
  [NEW] [risk note for WP3.3/WP3.4 scoping]
- `workout_plan.html:2` region (`Generate Starter Plan Modal`) hardcodes preview copy
  (`~7 exercises`, `18 sets`, rep ranges) both in the static Jinja markup
  (`workout_plan.html:507-510`) and duplicated as JS string literals inside
  `updatePlanPreview()` (`workout_plan.html:740-767`) — the initial static markup and the
  JS-computed version must be kept manually in sync (e.g. `baseSets = Math.round(18 *
  volumeScale)` mirrors the static "18 sets" default). Minor duplication, flag only.
- No `|safe` filters; no direct DB-sourced text rendered without escaping.
- Uses `<main id="workout" data-page="workout-plan" role="main">` (`:10`) — has the
  `<main>` landmark (see cross-cutting note).

## templates/user_profile.html (648 lines)

- `user_profile.html:394` — `<span class="frame-title">{{ card_label | safe }}</span>` —
  the **only `|safe` filter found across all 16 templates**. `card_label` is not
  user/DB-controlled data — it comes from a hardcoded Jinja tuple literal defined in the
  same template at `user_profile.html:388-389`
  (`('anterior', 'Reference Lifts &mdash; Anterior', reference_lift_groups_anterior)`), used
  only so the `&mdash;` HTML entity renders instead of being escaped to `&amp;mdash;`. Not
  an XSS risk today (the value never touches request/DB input), but it's the one `|safe`
  usage in the entire template layer and should be noted for any future refactor that
  moves `card_label` to a translatable/configurable source. [CONFIRMS-PLAN: watch for raw
  `|safe` — this is the single hit, and it's benign]
- `user_profile.html:280` — `<script type="application/json" data-bodymap-state>{{ coverage
  | tojson }}</script>` — correct, safe pattern for passing server data to JS (uses
  `|tojson`, not string interpolation into a `<script>` body).
- `user_profile.html:646-648` — clean `{% block page_js %}` with a single ES6 module
  (`user-profile.js`), no inline script in the whole file otherwise. Good — this is the
  template WP3.2 should hold up as the target pattern for `workout_plan.html`/
  `weekly_summary.html` extraction.
- Extensive accessibility work: donut SVG `role="img"` + `aria-label`
  (`user_profile.html:82`), screen-reader linear summary `<dl>` mirroring the visual bodymap
  (`user_profile.html:265-279`, explicitly commented as "AT users read this list instead of
  interacting with the SVG"), `aria-live="polite"` on all three autosave-status regions.
  This is the most accessibility-considered template in the set.
- `user_profile.html:340-341` — comment: "Numbers below mirror TIER_RATIOS and
  REP_RANGE_PRESETS in utils/profile_estimator.py. Update both places if those constants
  change." — a hardcoded-copy-must-match-source-of-truth risk baked into the template
  (the tier ratios `×1.00/×0.70/×0.40` and rep-range percentages `×0.85/×0.77/×0.65` at
  `user_profile.html:360-370` are literal copy, not rendered from the Python constants).
  Directly relevant to WP2.1 (splitting `profile_estimator.py`) — that WP's "pure moves; no
  signature or logic edits" scope won't touch this, but if `TIER_RATIOS`/
  `REP_RANGE_PRESETS` values ever change in a *later* WP, this template's copy silently
  goes stale with no test or lint to catch it. [NEW] [RISK: doc/copy drift, not this WP's
  problem but worth recording]

## templates/weekly_summary.html (621 lines)

- `weekly_summary.html:2` — `{% from "partials/_volume_controls.html" import
  method_selector %}`; `weekly_summary.html:23` — `{{ method_selector('updateWeeklySummary')
  }}` renders the **only client-facing mode toggle on this page: `#contribution-mode`**
  (`partials/_volume_controls.html:5`, options `total` (selected) / `direct`).
  **There is no `CountingMode` UI toggle anywhere in this template.** Effective Sets and
  Raw Sets are always both rendered as separate table columns
  (`weekly_summary.html:100-101`), never gated behind a client toggle. The
  `updateWeeklySummary()` fetch (`weekly_summary.html:468`) sends only
  `?contribution_mode=${contributionMode}` — **no `counting_mode` query param is ever
  sent to the server.** [CONTRADICTS-PLAN] — REFACTOR_PLAN.md's WP3.2 "Mode-semantics pin"
  states "the weekly-summary inline JS wires the CountingMode / ContributionMode toggles" —
  only one toggle (`ContributionMode`) exists client-side; `CountingMode` is exclusively a
  backend/Python concept (grepped: only present in `utils/weekly_summary.py`,
  `utils/session_summary.py`, `utils/effective_sets.py`, `utils/fatigue*.py`, and tests —
  never in `templates/` or `static/js/`). The WP3.2 executor should not go looking for a
  `CountingMode` `<select>` to preserve — it doesn't exist. The **real** thing to preserve
  is: both Effective and Raw columns always render together (there's no toggle hiding
  either), and `contribution-mode` defaults to `total` (confirmed at
  `partials/_volume_controls.html:6`, `option value="total" selected`).
- `weekly_summary.html:19` — `{% include "_fatigue_badge.html" with context %}` — correct
  `with context` usage (the partial needs `fatigue_score`/`fatigue_band`/
  `fatigue_period_label` from the parent's render context).
- `weekly_summary.html:226-620` — inline `<script>`, **exactly 395 lines**. **Matches the
  REFACTOR_PLAN.md WP3.2 estimate of "~395" precisely.** [CONFIRMS-PLAN]
  Contains: `getVolumeDetails()`, `formatPatternName()`, the 4-function API-response-shape
  helper set (`isWrappedApiResponse`, `isApiFailure`, `unwrapApiPayload`,
  `getApiErrorMessage`), `updatePatternCoverage()` (builds a large HTML string via
  `container.innerHTML =` with `${}` template-literal interpolation of server data —
  `warning.message`/`warning.description`/pattern names/routine names, all currently
  backend-sourced/enum-controlled so not exploitable today, but built without any
  escaping — see cross-cutting XSS-surface note), `updateWeeklySummary()`, and two
  tooltip-text helper functions duplicated verbatim from `session_summary.html` (see next
  file's entry — this is the single largest duplication in the template layer).
- `weekly_summary.html:548-551` — re-initializes **every** `[data-bs-toggle="tooltip"]`
  element in the whole document (not scoped to this page's tables) on every
  `updateWeeklySummary()` call — including the fatigue badge's info-button tooltip
  (`_fatigue_badge.html:21-27`) and the static "Routines" column header tooltip
  (`weekly_summary.html:102-104`). Since `updateWeeklySummary()` re-runs on every
  contribution-mode change and on `filterViewModeChanged`, Bootstrap `Tooltip` instances
  accumulate on the same static elements repeatedly (Bootstrap doesn't dedupe
  `new bootstrap.Tooltip(el)` calls on an already-initialized element by itself). Minor
  perf/hygiene issue, not a correctness bug. [NEW] [RISK: low]

## templates/session_summary.html (495 lines)

- `session_summary.html:2,23` — same `method_selector('updateSessionSummary')` pattern,
  same single `#contribution-mode` toggle, same "no CountingMode toggle" situation as
  weekly_summary.html.
- `session_summary.html:213-494` — inline `<script>`, **exactly 282 lines.**
  REFACTOR_PLAN.md's WP3.2 only says "`session_summary.html` ... inline blocks: audit,
  extract if non-trivial" with no line estimate — but 282 lines (72% the size of
  weekly_summary's 395) is clearly non-trivial and should be sized the same as
  weekly_summary.html's extraction, not treated as an afterthought "audit" pass.
  [CONTRADICTS-PLAN — the "audit, extract if non-trivial" framing undersells the actual
  size/effort relative to weekly_summary.html]
- **Major duplication, byte-for-byte**: `get_category_tooltip()`
  (`session_summary.html:215-222` vs `weekly_summary.html:594-601`),
  `get_subcategory_tooltip()` (`session_summary.html:224-240` vs
  `weekly_summary.html:603-618`), `isWrappedApiResponse()` / `isApiFailure()` /
  `unwrapApiPayload()` / `getApiErrorMessage()` (`session_summary.html:242-282` vs
  `weekly_summary.html:277-317`), and `getVolumeDetails()`
  (`session_summary.html:285-314` vs `weekly_summary.html:227-257`) are **identical
  (or near-identical) function bodies copy-pasted between the two templates.** This is
  ~140 of the 282 lines in `session_summary.html` (and ~140 of 395 in
  `weekly_summary.html`) that are pure duplication. REFACTOR_PLAN.md WP3.2 treats these as
  two independent extraction targets (`weekly-summary-page.js` for one,
  "merge into existing plan modules" implied only for `workout_plan.html`) — it does not
  call out that both summary pages should share one helper module (e.g.
  `summary-page-shared.js` housing the tooltip + API-shape helpers), which would cut the
  combined inline-JS-to-extract line count by roughly a third. [NEW] [seed: WP3.2 should
  factor a shared module, not two independent one-to-one file moves]
- `session_summary.html:316-332` — `getSessionWarningBadge()` is session-summary-specific
  (no weekly_summary equivalent — the borderline/excessive-set warning system is a
  session-only feature), correctly not duplicated.
- Same broad tooltip re-init pattern at `session_summary.html:450-453` as
  weekly_summary.html.

## templates/workout_log.html (292 lines)

- No `{% block page_js %}` and no inline `<script>` at all in this file. All interactivity
  (`importFromWorkoutPlan`, `deleteWorkoutLog`, `updateScoredValue`, date-field handling,
  `window.confirmClearWorkoutLog`) is wired via `onclick=`/`onchange=` attributes calling
  globals that live in `static/js/modules/workout-log.js`, imported centrally by
  `static/js/app.js` (`app.js:3-22`, confirmed via grep) rather than per-page. This is a
  different — and cleaner, from a "no inline JS" standpoint — architecture than
  `workout_plan.html`/`weekly_summary.html`/`session_summary.html`/`welcome.html`, but it
  means `app.js` is a central all-page-JS barrel that always imports every page's module
  regardless of which page is being viewed (confirmed by the same grep:
  `progression-plan.js`, `program-backup.js`, `backup-center.js` are all imported at
  `app.js` top level too). `backup.html`, `progression_plan.html`, and `volume_splitter.html`
  follow this same no-`page_js`-block pattern for the same reason. This is a real,
  consistent architecture (not a bug) but is worth naming for whoever executes WP3.3/WP3.4:
  **`app.js` unconditionally bundles all page modules**; the per-page dispatch must happen
  inside each module (e.g. checking `document.querySelector('[data-page="..."]')`), not at
  the template layer. [NEW] [architecture note, useful context for Phase 3 JS work]
- `workout_log.html:98` — `{% set safe_path = log.media_path | safe_media_path %}` — the
  one custom Jinja filter usage found in the audited templates; comment correctly notes
  it's defense-in-depth revalidation (§4.3), not the primary validation gate.
- `workout_log.html:92` — `data-assisted-bodyweight="{{ 'true' if
  is_assisted_bodyweight_exercise(log.exercise) else 'false' }}"` — a Python function
  called directly from template context per-row (registered presumably as a Jinja global,
  not chased further — out of scope for this phase, but worth noting business logic is
  reachable from template rendering, not just `utils/`).
- No `<main>` landmark — top-level content is `<div class="container-fluid px-1
  workout-log-page">` (`:10`). See cross-cutting note.

## templates/backup.html (227 lines)

- No inline `<script>`, no `{% block page_js %}` — same central-`app.js`-import pattern as
  workout_log.html (`backup-center.js`/`program-backup.js` imported at `app.js:30-31`).
- Uses `<main class="backup-center-page" ... role="main">` (`:10`) — has the landmark.
- Clean, well-structured; no `|safe`, no duplicated markup found against other templates.

## templates/body_composition.html (220 lines)

- `body_composition.html:218-220` — clean `{% block page_js %}` with one ES6 module,
  same good pattern as `user_profile.html`. No inline script.
- `body_composition.html:10-15` — `<main ... data-bc-app="true" data-profile-gender="..."
  data-profile-age="..." data-profile-height-cm="..." data-profile-weight-kg="...">` —
  profile fields passed to JS via `data-*` attributes on the root element rather than a
  `<script type="application/json">` blob (contrast with `user_profile.html:280`'s
  `|tojson` pattern for the bodymap state). Two different conventions for "hand server
  data to JS" exist side by side in this template set — not wrong, just inconsistent.
  [NEW] minor.
- Has the `<main role="main">` landmark.

## templates/progression_plan.html (177 lines)

- No inline `<script>` except a single external `<script
  src="https://cdn.jsdelivr.net/npm/flatpickr">` at `:176` (third-party CDN dependency,
  loaded unpinned-by-SRI, same pattern as the Bootstrap/FontAwesome CDN links in
  `base.html`). No `{% block page_js %}` — same central-`app.js` pattern
  (`progression-plan.js` imported at `app.js:25`).
- `progression_plan.html:21-23` — `<div class="debug-info text-muted small mb-3">
  Available exercises: {{ exercises|length }}</div>` — a class named `debug-info` shipped
  in production markup, permanently visible to end users (not hidden behind a debug flag).
  Likely leftover from development. [NEW] minor cleanliness note, not a security issue
  (just an exercise count) but the class name signals it wasn't meant to ship as-is.
- No `<main>` landmark — top-level is `<div class="progression-plan-container">`.

## templates/volume_splitter.html (175 lines)

- No inline `<script>` except two external CDN `<script>` tags at `:173-174`
  (`@popperjs/core@2`, `tippy.js@6`) — **Tippy.js is loaded here but Bootstrap tooltips
  (`data-bs-toggle="tooltip"`) are the pattern used everywhere else** (weekly/session
  summary, fatigue badge). This is the only template pulling in a second, different
  tooltip library. Not chased into `static/js/` to confirm actual usage, but worth flagging
  as a possible redundant dependency if Tippy isn't actually used by
  `volume-splitter.js`/`plan_volume_panel.js`. [NEW] [seed: verify Tippy.js is still used
  before Phase 4/CSS or any dependency-audit WP]
- `volume_splitter.html:25-29` — five `data-*` attributes on `#volume-splitter-app` each
  carrying a `|tojson`-serialized payload (`data-basic-muscles`, `data-advanced-muscles`,
  `data-basic-ranges`, `data-advanced-ranges`) plus `data-default-mode` — a third variant
  of the "hand server data to JS" pattern (attribute-embedded JSON, vs. body_composition's
  plain-value data attributes, vs. user_profile's `<script type="application/json">`
  block). Three different conventions for the same problem across the 16 templates. [NEW]
- No `<main>` landmark — top-level content starts directly with a `<div
  class="page-header ...">` then `<div id="volume-splitter-app">`.

## templates/fatigue.html (102 lines)

- `fatigue.html:14-37` — the period selector `<form method="get" ... onchange="this.form.
  submit()">` with a `<noscript>` fallback submit button (`:32-36`) — the only
  progressive-enhancement/no-JS fallback found anywhere in the 16 templates. Good practice,
  worth calling out positively; no other page in the set has a `<noscript>` path.
- `fatigue.html:91` — `{% include '_fatigue_muscle_bar.html' with context %}` inside a
  `{% for row in muscle_rows %}` loop — correct `with context` usage (partial needs `row`
  from the loop variable, which `with context` does expose since it's in scope at include
  time).
- No inline `<script>`, no `{% block page_js %}` at all — this page has **zero
  page-specific JavaScript**. The period `<select>` triggers a full page reload via GET
  form submission; there is no fatigue-specific `.js` module. Confirmed clean, simplest
  template in the set from a JS-surface standpoint.
- Uses `<section class="container fatigue-page py-4" ...>` as its top-level wrapper, not
  `<main>`. See cross-cutting note.

## templates/_fatigue_badge.html (56 lines) / templates/_fatigue_muscle_bar.html (56 lines)

- Both partials have thorough top-of-file comment blocks documenting their expected input
  shape and the calling contract (`{% include ... with context %}`) — the best-documented
  files in the template set.
- `_fatigue_badge.html:16-18` — `role="status"` + descriptive `aria-label` on the whole
  `<section>`; `_fatigue_badge.html:21-30` — the info button uses
  `data-bs-toggle="tooltip" data-bs-html="true"` with a long explanatory `title=` — note
  `data-bs-html="true"` means the tooltip content is rendered as HTML, but the `title=`
  attribute itself is a static, hardcoded template string (`:27`), not interpolated from
  any variable — safe, just worth confirming for anyone editing that copy in the future
  that it will render as HTML, not escaped text.
- `_fatigue_muscle_bar.html:44` — `style="width: {{ [width, 150] | min }}%"` — an inline
  `style=` attribute with a Jinja-computed numeric value (a meter-fill percentage). This is
  a legitimate, unavoidable use of inline style for a dynamically-sized bar (can't be done
  via a CSS class since the value is continuous), same category as the `donut-fill`
  `stroke-dasharray` inline style in `user_profile.html:84` and the several `--cs-pct`/
  `--cu-pct`/`--mark-pct`/`--band-progress`/`--band-total` CSS custom-property inline
  styles in `user_profile.html:92,162-165`. **Pattern across the codebase**: dynamic
  numeric visualizations (meters, donuts, bars) correctly use inline `style=` for the
  *value* while keeping the *appearance* in CSS via custom properties — this is the right
  pattern, not a violation of the "no inline theme styling" gotcha (that gotcha is about
  theme/color, not data-driven geometry). Noted so Phase 4 (CSS cleanup) doesn't
  mistakenly try to eliminate these.
- Both partials are used only by `fatigue.html` (muscle bar) and by `weekly_summary.html`
  + `session_summary.html` (`_fatigue_badge.html`, confirmed via the two `{% include
  "_fatigue_badge.html" with context %}` call sites found). No dead partials.

## templates/partials/exercise_video_modal.html (52 lines)

- Single-instance shared modal, included once from `base.html:259`, used by
  `workout_log.html` (via the `.log-play-video-btn` buttons at `workout_log.html:109-117`)
  and presumably `workout_plan.html`'s exercise table (not chased into the table's JS
  rendering, out of scope — table rows are built client-side by `workout-plan.js`, not
  server-rendered, so no matching markup is expected in `workout_plan.html` itself).
- `:26-35` — comment correctly documents the "embed mode only" behavior (curated ids only;
  uncurated rows skip the modal and open a YouTube tab directly) — consistent with the
  MEMORY.md note that PR #88 widened this fallback. No stale/contradicted comments found
  here.
- Clean, no `|safe`, no inline script — purely a template partial, all behavior lives in
  `static/js/modules/exercise-video-modal.js`.

## templates/partials/_volume_controls.html (not in the 16-file list but load-bearing)

- Read for context since both `weekly_summary.html` and `session_summary.html` import from
  it. Confirmed: `method_selector(update_function_name)` macro renders exactly one
  `<select id="contribution-mode">` with `total` (selected) / `direct` options
  (`:5-8`), plus a static help-text block. This is the entire "ContributionMode toggle"
  referenced by REFACTOR_PLAN.md WP3.2 — there is no companion `CountingMode` control in
  this macro or anywhere else in the templates. Confirms the finding under
  `weekly_summary.html` above.

---

## Cross-cutting seeds

1. **`<main>` landmark is inconsistent across templates, not just missing in one place.**
   `base.html:219` wraps `{% block content %}` in a plain `<div id="main-content">`, not a
   `<main>` element. Five templates add their own nested `<main>` inside that div
   (`workout_plan.html:10`, `user_profile.html:10`, `welcome.html:10`, `backup.html:10`,
   `body_composition.html:10`); the other seven page templates
   (`weekly_summary.html`, `session_summary.html`, `workout_log.html`,
   `progression_plan.html`, `volume_splitter.html`, `fatigue.html`, `error.html`) have no
   `<main>` landmark anywhere in their render — a screen-reader "jump to main content" or
   landmark-navigation pass gets nothing on those seven pages. Fix is cheap (either make
   `base.html`'s wrapper a real `<main>`, or add `<main>` to the remaining seven) but is
   currently inconsistent enough to be a real a11y gap, not a style nit. Not currently
   scoped by any WP in `docs/REFACTOR_PLAN.md`.

2. **Three different "hand server data to JS" conventions coexist**: `<script
   type="application/json" data-X>{{ ... | tojson }}</script>` (`user_profile.html:280`),
   plain-value `data-*` attributes (`body_composition.html:10-15`), and `data-*` attributes
   holding `|tojson`-serialized JSON strings (`volume_splitter.html:25-29`). None is wrong,
   but a JS-layer refactor (WP3.x) inheriting all three patterns should probably standardize
   on one, likely the `<script type="application/json">` form since it avoids HTML-attribute
   escaping edge cases that JSON-in-an-attribute has to route through `|tojson`'s
   attribute-safe escaping.

3. **The `.collapse-toggle`/`.collapsible-frame` open/close behavior is implemented three
   separate times**: inline in `workout_plan.html:773-831`, and independently inside
   `static/js/modules/workout-log.js` and `static/js/modules/user-profile.js`. All three
   target the same markup contract (`frame-header-2025` + `.collapse-toggle` button +
   `aria-expanded` + `.collapsed` class toggle). This is the single clearest "extract a
   shared module" opportunity found in this phase and isn't mentioned in
   `docs/REFACTOR_PLAN.md` — worth folding into WP3.2 (when `workout_plan.html`'s inline JS
   is extracted) or a small standalone follow-up WP.

4. **`weekly_summary.html` and `session_summary.html` duplicate ~140 lines of identical
   JS** (tooltip-copy helpers + API-response-shape helpers + `getVolumeDetails`).
   REFACTOR_PLAN.md WP3.2 treats `weekly_summary.html`'s extraction as a dedicated new
   module and only says "audit" for `session_summary.html` — the higher-value move is a
   shared helper module consumed by both extracted page modules, which also resolves the
   session_summary line-count undercount noted above (282 actual vs. implied "small enough
   to just audit").

5. **The REFACTOR_PLAN.md WP3.2 "Mode-semantics pin" language about a `CountingMode`
   toggle does not match the templates.** There is no `CountingMode` UI control anywhere in
   `templates/`; it's a backend-only concept. The only client-side toggle on the summary
   pages is `#contribution-mode` (`partials/_volume_controls.html`, default `total`). The
   WP3.2 executor's actual invariant to preserve is: (a) `contribution-mode` defaults to
   `total`/selected, (b) Effective Sets and Raw Sets always render as two separate,
   simultaneous table columns (never toggled/hidden), and (c) the fetch calls never send a
   `counting_mode` param today and must not start doing so as a side effect of extraction.

6. **`error.html`'s kwarg bug is real and confirmed** (6 of 7 `render_template("error.html",
   ...)` call sites pass `message=` instead of `error_message=`, and none of the 7 ever
   pass `error_title`/`error_code`) — **and** the template is structurally bypassed by the
   app's actual registered `@app.errorhandler`s, which use a separate raw-HTML
   `_html_error()` helper in `utils/errors.py` instead. Two parallel, inconsistent
   error-rendering code paths exist. This is adjacent to but larger than what WP0.1/WP0.2
   scoped (those only covered whether `_html_error`'s callers were dead code — they're not,
   they're live, but they don't use the Jinja template at all). Worth a dedicated
   Phase-0/Phase-1 follow-up WP: fix the 6 kwargs, decide whether `_html_error()` should be
   replaced with `render_template("error.html", ...)` for consistency, and add a smoke test
   asserting `error.html` renders with non-empty title/code/message for at least one path.

7. **Cache-busting via `range(1, 1000000) | random` on 4 of 6 `<script>` tags in
   `base.html`** (`app.js`, `table-responsiveness.js`, `filter-view-mode.js`,
   `exercise-video-modal.js` get it; `darkMode.js`, `accessibility.js` don't) forces a full
   re-download of those 4 files on every single page navigation, for every user, forever —
   not a correctness issue but a real, easily-fixed performance cost outside this
   refactor's stated scope; worth a note in `docs/MASTER_HANDOVER.md` as a cheap win
   (replace with a build-time content hash or drop the cache-buster entirely once CSS/JS
   ship through a real build step).
