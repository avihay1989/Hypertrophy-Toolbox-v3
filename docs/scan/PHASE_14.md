# Phase 14 — JS: backup / volume-splitter / exports

Line-by-line read of `static/js/modules/backup-center.js` (1005),
`static/js/modules/volume-splitter.js` (912), `static/js/modules/plan_volume_panel.js`
(248), `static/js/modules/program-backup.js` (174), `static/js/modules/exports.js` (143),
plus `static/js/CLAUDE.md` and `.claude/rules/frontend.md` for context. Cross-checked
against `docs/REFACTOR_PLAN.md` v2, specifically WP3.5 ("Unify raw `fetch()` →
`apiFetch`") which names `volume-splitter.js` (7 raw fetches) and `exports.js` (2, blob
exceptions). Also traced call graphs via `app.js` and `templates/` to confirm what's live
vs. dead.

---

## static/js/modules/backup-center.js (1005 lines)

**Verdict: this is the Backup Center *page controller* — DOM rendering, list/filter/sort,
inline editing, and a two-step confirm flow for restore/delete. It consumes
`program-backup.js` for all network calls. No raw `fetch()` in this file — 100% via the
imported API functions, which themselves go through `api`/`apiFetch`.** `[CONFIRMS-PLAN]`
implicitly — this file was never named in WP3.5's raw-fetch inventory, and that's
correct; it has zero.

- `backup-center.js:1-19` — module-level mutable state: `backupCenterInitialized`,
  `backupsCache`, `selectedBackupId`, `selectedBackupDetails`, `pendingAction`,
  `detailRequestSequence`, `inlineEditField`, `emptyWarningShown`. Standard
  single-page-module pattern (matches `volume-splitter.js`'s own module-level state) — not
  flagging as a defect, just noting the pattern repeats across this phase's files with no
  shared "page module state" convention documented anywhere. `[NEW]` (low severity, doc
  gap only).
- `backup-center.js:601,617` (`loadBackupDetails`) — `detailRequestSequence` is a
  well-built out-of-order-response guard: every call to `loadBackupDetails` increments a
  sequence counter and any in-flight request whose captured `requestId` no longer matches
  the current sequence silently no-ops on resolve/reject. This correctly protects against
  rapid list-clicking racing two `fetchBackupDetails` calls. Worth flagging as a positive
  pattern other page modules in this codebase should copy (no equivalent guard exists in
  `volume-splitter.js`'s `loadPlan`/`calculateVolume`, though those aren't triggered by
  fast repeated clicks on different IDs the way backup selection is, so the risk profile
  differs). `[NEW]` (informational).
- `backup-center.js:59-64`, `escapeHtml` — every dynamic string interpolated into
  `innerHTML` in this file (`backup-record-name`, `backup-record-note`, item table cells
  in `renderBackupDetails`, inline editor values) is routed through `escapeHtml` first.
  This is the one file in this phase that consistently guards against injected HTML from
  backup names/notes/exercise names (all user-editable strings). Contrast with
  `volume-splitter.js` below, which does not escape comparable dynamic values. `[NEW]`
  (positive; useful reference implementation for a future audit finding elsewhere).
- `backup-center.js:760-818` (`handleConfirmAction`, restore branch) — `renderRestoreResult(result)`
  is called once immediately (line 782) and then called *again* at line 798, after
  `await refreshBackupCenter(...)`. This isn't dead duplication: `refreshBackupCenter` →
  `loadBackupDetails` → `renderBackupDetails` (line 532) unconditionally calls
  `clearRestoreResultPanel()` at its tail (line 588) as part of "reset detail panel to a
  clean state." So the restore-result banner painted at line 782 gets wiped by the
  subsequent detail reload, and the second call at line 798 repaints it. **This is a
  fragile order-of-operations coupling**: `renderBackupDetails` clearing
  `restore-result` as a side effect means every future caller that wants the restore
  banner to survive a detail refresh must remember to re-invoke `renderRestoreResult`
  *after* the refresh, with no compiler/lint signal if someone forgets. `[RISK]` — a
  future edit to `refreshBackupCenter`'s internals (e.g., adding another intermediate
  render) could silently drop the second `renderRestoreResult` call's effect, or a
  future caller of `refreshBackupCenter` elsewhere could reintroduce the same bug pattern
  without realizing the clear/repaint dependency exists.
- `backup-center.js:957-988` (`saveFirstBtn` "Save current plan first" handler) — on
  success this calls `refreshBackupCenter({ preserveSelection: true, preferredSelectionId })`
  but never re-invokes `showPendingAction('restore')`. `refreshBackupCenter` →
  `loadBackupDetails` → `renderBackupDetails` → `clearPendingAction()` (line 587), which
  sets `pendingAction = null` and hides the confirm panel (`confirmWrap.hidden = true`,
  line 157). **Net effect: after a user clicks "Save current plan first" mid-restore-confirm,
  the restore confirmation dialog silently disappears** instead of representing itself so
  the user can complete the restore they were mid-flow on. Not data-destructive (restore
  never fires without a fresh explicit click on "Restore" + "Confirm Restore" again), but
  it breaks the two-step safety flow's continuity — the user's "I want to restore backup X"
  intent is lost and must be re-declared from scratch. `[RISK]` — UX/flow correctness bug,
  not a data-safety bug (no backend call is skipped; the safety net over-fires, not
  under-fires).
- `backup-center.js:334-398` (`commitBackupEdit`) — solid optimistic-update pattern:
  snapshots `selectedBackupDetails` and the matching `backupsCache` entry before mutating,
  applies the optimistic value, calls the API, and on failure restores both snapshots and
  re-renders. Also correctly checks `stillSelected` (via `Number(selectedBackupId) ===
  Number(backupId)`) before touching `selectedBackupDetails`/re-rendering the detail panel,
  guarding against a user navigating to a different backup while the PATCH is in flight.
  `[NEW]` (positive pattern, no defect).
- `backup-center.js:23-26` (`getNavigationIntent`) / `applyNavigationIntent` (126-146) —
  reads `?intent=save|browse` from the URL to auto-scroll/focus a panel on load. Only
  entry point found for this is presumably a link from another page (e.g., a "Save backup"
  CTA elsewhere) — not verified further in this phase since it's outside the 5 target
  files; flagging as a cross-file dependency worth checking in a templates/nav phase if not
  already covered. `[NEW]` (low severity, informational).
- No dead exports: `initializeBackupCenter` is the only export and is imported/called
  once in `app.js:31,235`. Confirmed via grep — no other importer.

## static/js/modules/program-backup.js (174 lines)

**Verdict: this is the correct answer to "why two backup modules" — it's the *API +
shared-utility* layer, not a duplicate UI. `backup-center.js` imports six of its seven
exports (`fetchBackups`, `fetchBackupDetails`, `createBackup`, `restoreBackup`,
`deleteBackup`, `updateBackupMetadata`) for the full Backup Center page; `app.js` imports
the seventh (`showAutoBackupBanner`) directly for a *different* consumer.** `[CONFIRMS-PLAN]`
in spirit — this is intentional separation-of-concerns (API layer vs. page UI), not
duplication, and matches `static/js/CLAUDE.md`'s own file-role table ("Backups" row lists
both files together for a reason).

- `program-backup.js:12-102` — every exported CRUD function (`fetchBackups` …
  `deleteBackup`) is a thin `try { await api.X(...) } catch { console.error; throw }`
  wrapper around `api` from `fetch-wrapper.js`, always passing `showErrorToast: false`
  (the caller, `backup-center.js`, handles its own toasts). Clean, consistent, no raw
  `fetch()`. `[CONFIRMS-PLAN]`.
- `program-backup.js:104-162` (`showAutoBackupBanner`) — **dead code.** Exported here,
  imported and re-exposed as `window.showAutoBackupBanner` in `app.js:30,61`, but grepping
  the entire repo (`routes/`, `utils/`, `templates/`, `static/js/`, `tests/`, `e2e/`) for
  `showAutoBackupBanner` finds only its own definition + the `app.js` import/window-assign
  — **zero call sites**. The apparent intended trigger, the `/erase-data` confirm handler
  in `templates/welcome.html:387-412`, does its own inline `fetch('/erase-data', ...)` and
  on success just shows a Bootstrap toast + `window.location.reload()` — it never reads
  `data.auto_backup` or calls `window.showAutoBackupBanner(...)`. Also confirmed
  `routes/main.py` (which presumably owns `/erase-data`, not fully re-read this phase)
  wasn't grepped for `auto_backup` payload wiring in this pass, but the JS-side dead path
  is unambiguous regardless of what the backend returns. `[RISK]` / `[NEW]` — ~60 lines of
  a real, non-trivial feature (renders a whole dismissible restore banner with its own
  click handler and `restoreBackup` call) that appears to have been built and then either
  never wired up on the caller side, or had its caller removed later without cleanup. This
  is a stronger dead-code find than a simple unused constant — it's a fully-formed,
  behaviorally complete function with a live import chain that terminates in nothing.
  Recommend either wiring it into the erase-data flow (if `/erase-data` does return an
  `auto_backup` object server-side) or deleting it + the `app.js` import/window-assignment
  per the refactor plan's dead-code rule 8 (repo-wide grep confirms zero non-definition
  references).
- `program-backup.js:169-174` (`escapeHtml`) — near-identical duplicate of
  `backup-center.js:59-64`'s `escapeHtml` (both: guard falsy → return `''`; create a
  `div`; set `textContent`; return `innerHTML`). Two independent copies of the same
  6-line utility in two files that already import from each other's neighborhood (
  `backup-center.js` imports six functions from this file). `[NEW]` — trivial, easy
  extract-to-shared-utility candidate (e.g. add to `toast.js` or a new tiny
  `dom-utils.js`), low priority but a clean signal for the general "shared helpers"
  pass this refactor plan doesn't currently have a WP for.

## static/js/modules/volume-splitter.js (912 lines)

**Verdict: matches the plan's WP3.5 raw-fetch count exactly (7), but the deeper finding
is that this file also hand-rolls ~50 lines of API-response-envelope handling that
duplicates what `apiFetch`/`api` in `fetch-wrapper.js` already does — so WP3.5's framing
("migrate raw fetch calls to the fetch-wrapper.js contract") understates the work: it's
not a call-site swap, it's deleting a parallel implementation.** `[CONFIRMS-PLAN]` on the
count, `[NEW]`/`[RISK]` on the depth.

- **Raw `fetch()` inventory — exactly 7, confirmed by reading every call site:**
  1. `volume-splitter.js:164` — `calculateVolume()` → `POST /api/calculate_volume`
  2. `volume-splitter.js:231` — `loadPlan(planId)` → `GET /api/volume_plan/:id`
  3. `volume-splitter.js:287` — `executeDeletePlan(planId)` → `DELETE /api/volume_plan/:id`
  4. `volume-splitter.js:319` — `exportVolumePlan(activate)` → `POST /api/save_volume_plan`
  5. `volume-splitter.js:387` — `loadVolumeHistory()` → `GET /api/volume_history`
  6. `volume-splitter.js:468` — `exportToExcel()` → `POST /api/export_volume_excel`
     (**blob response** — legitimate raw-fetch exception per WP3.5's own carve-out for
     endpoints the wrapper doesn't support; `apiFetch` always attempts
     `response.json()`/`response.text()` per content-type, never `.blob()`)
  7. `volume-splitter.js:830` — `toggleActivePlan(planId, isActive)` →
     `POST /api/volume_plan/:id/activate|deactivate`
  Of these, only #6 is a justified blob exception; #1–5 and #7 are plain JSON
  request/response cycles with no reason not to use `apiFetch`. `[CONFIRMS-PLAN]`.
- `volume-splitter.js:16-19,23-67` — `JSON_REQUEST_HEADERS`, `isWrappedApiResponse`,
  `isApiFailure`, `unwrapApiPayload`, `getApiErrorMessage`, `parseJsonResponse`: this
  block re-implements, in miniature, the response-shape normalization that
  `fetch-wrapper.js`'s `apiFetch` already centralizes (`normalizeError`, the
  `{ok, status, data, error}` envelope unwrap, `showToast` on error). The local version
  differs in ways that matter: it does **not** show a loading indicator, does **not**
  auto-toast on failure (callers must remember to `.catch()` and toast individually — see
  next finding), and does **not** retry idempotent GETs the way `apiFetch` does for GET by
  default. `[NEW]` — this is the real WP3.5 payload: migrating the 6 non-blob fetches to
  `apiFetch` should let this entire ~50-line block (`JSON_REQUEST_HEADERS` through
  `parseJsonResponse`, plus `toNumericRange`'s fallback wiring at 69-90 which is unrelated
  and should stay) be deleted, not just have its call sites swapped.
- `volume-splitter.js:155-182` (`calculateVolume`) — **the `.catch()` only
  `console.error`s; it never calls `showToast`.** This function runs on: initial page
  load (line 139/547 via `setMode`), every debounced slider drag (`scheduleCalculate`,
  300 ms), every slider `change` event, and the manual "Calculate" button. If
  `/api/calculate_volume` fails (network blip, 500, validation error), **the user gets no
  visible feedback at all** — results silently go stale with whatever was last displayed,
  and nothing in the UI indicates a failure occurred. Contrast with every other network
  call in this same file (`loadPlan`, `executeDeletePlan`, `exportVolumePlan`,
  `loadVolumeHistory`, `exportToExcel`, `toggleActivePlan`) — all six of the others call
  `showToast('error', ...)` in their `.catch()`. `[RISK]` — this is the file's
  highest-traffic network call (fires on every slider tick) and the one silent failure
  path.
- `volume-splitter.js:307-356` (`exportVolumePlan`) / `457-490` (`exportToExcel`, this
  file's own local one) / `videoDays clamp` — `Math.max(parseInt(trainingSelect?.value, 10)
  || 3, 1)` is duplicated verbatim three times (lines 157, 309, 459). Minor, but a
  10-minute extract-helper candidate (`getTrainingDays()`), unrelated to WP3.5 but sitting
  right next to it. `[NEW]` (low severity).
- **Naming collision risk, not a runtime bug:** `volume-splitter.js:457` defines a
  module-private `function exportToExcel()` (exports the *volume plan* as an Excel file
  via `POST /api/export_volume_excel`) that is never exported from this module and never
  collides at runtime with `exports.js`'s exported `exportToExcel` (which exports the
  *workout plan* via `GET /export_to_excel` and is assigned to `window.exportToExcel` in
  `app.js:46`). The two are unrelated features that happen to share a name in different
  module scopes with genuinely different endpoints/payloads/blobs. `[NEW]` — flagging as a
  grep/refactor hazard: anyone searching the codebase for `exportToExcel` to understand
  "the Excel export" will find two unrelated implementations and must read call sites
  carefully to know which is which. A rename of the local one (e.g.
  `exportVolumePlanToExcel`) would remove the ambiguity at near-zero cost.
- `volume-splitter.js:199-219` (`displayResults`) and `358-384` (`displaySuggestions`) —
  both interpolate server-sourced strings directly into `innerHTML`
  (`` `<td>${muscle}</td>` ``, `` `<p class="mb-0">${suggestion.message}</p>` ``) with no
  escaping. `muscle` values originate from the `data-basic-muscles`/`data-advanced-muscles`
  JSON config baked into the template (a fixed enum, not user-entered text), and
  `suggestion.message` is server-generated advisory copy — so the practical XSS risk looks
  low today, but it's an inconsistency worth naming: `backup-center.js` in this same phase
  treats *comparable* server-returned strings (backup names/notes, which genuinely are
  user-entered) as requiring `escapeHtml`, while this file has no equivalent guard
  anywhere. `[RISK]` (low likelihood given current data sources, but no defense-in-depth
  if `suggestions` content generation ever starts incorporating user-editable text, e.g. a
  future "custom muscle" feature).
- `volume-splitter.js:753-766` (`handleCalculateResponse`) — applies server-computed
  `ranges` (via `applyServerRanges`) and `results`/`status` per muscle to the UI. Confirmed
  by reading `routes/volume_splitter.py:75-134` (`calculate_volume`) that the **status
  classification (`low`/`optimal`/`high`/`excessive`) and range defaults
  (`build_default_ranges`/`parse_requested_ranges`) are computed entirely server-side** and
  the client only paints whatever the server returns — the client does not reimplement
  the low/optimal/high/excessive threshold logic. `[CONTRADICTS-PLAN]` (narrowly) — the
  scan-context brief flagged "volume-splitter client-side math that mirrors backend logic
  (dual source of truth)" as a thing to watch for; on the JS side specifically, that
  concern does not materialize for the status/classification logic. The one place a
  client-side default does exist is `toNumericRange`'s hardcoded `{ min: 12, max: 20 }`
  fallback (line 70, reused at 563/588/677) used only until the first server response
  populates `modeRangeState` — a narrow, cosmetic pre-load default, not a competing
  classification scheme. `[NEW]`.

## static/js/modules/plan_volume_panel.js (248 lines)

**Verdict: clean, small, well-isolated module — the "Distribute" drawer widget embedded
on other pages (reads the active volume plan and shows a progress-bar-per-muscle summary
against the plan built in `volume-splitter.js`). No raw `fetch()`; uses `api.get` from
`fetch-wrapper.js` correctly (`api.get('/api/volume_progress', ...)`,
`plan_volume_panel.js:218`). `[CONFIRMS-PLAN]` implicitly — correctly not in WP3.5's
raw-fetch list.**

- **Naming inconsistency confirmed**: `plan_volume_panel.js` is the only snake_case
  filename among five kebab-case siblings in this phase (`backup-center.js`,
  `volume-splitter.js`, `program-backup.js`, `exports.js`) and, per `static/js/CLAUDE.md`'s
  own file table (`modules/volume-splitter.js`, `modules/plan_volume_panel.js` listed
  side-by-side under "Distribute"), the inconsistency is baked into the docs, not just the
  filesystem. `[CONFIRMS-PLAN]` — matches the brief's flagged concern exactly. Every other
  module file in `static/js/modules/` (per the CLAUDE.md table) uses kebab-case; this is
  the sole snake_case outlier repo-wide as far as this phase's file table shows.
- `plan_volume_panel.js:100-134` (`buildTargetedRow`) / `136-157` (`buildBonusRow`) — built
  with `document.createElement` + `.textContent` for all user/server-derived text (`
  row.muscle_group`, formatted set counts), only using `innerHTML` for a small fixed
  template fragment with an interpolated, whitelisted `status` string
  (`buildTargetedRow`'s `meta.innerHTML` at line 129, where `status` is one of a known
  small set of `progress_status` enum values). This is the safest string-handling of the
  three UI files in this phase — better than `volume-splitter.js`'s raw innerHTML
  interpolation, on par with `backup-center.js`'s `escapeHtml` discipline but via a
  different (arguably more idiomatic) technique. `[NEW]` (positive, informational).
- `plan_volume_panel.js:36-45` (`moveOverlayNodesToBody`) — relocates the drawer + backdrop
  DOM nodes to `document.body` on init (to escape stacking-context/overflow clipping from
  wherever the template physically places them). This is a common but slightly fragile
  pattern: it silently assumes the elements exist with fixed IDs (`vpDrawer`,
  `vpBackdrop`) wherever the panel's markup is injected (not traced further — the template
  partial that renders this markup wasn't in scope for this phase). No defect found, just
  noting the cross-file coupling for whoever eventually reads the templates. `[NEW]` (low
  severity, informational).
- `plan_volume_panel.js:3` — `STORAGE_KEY = 'vpDrawer.open'` in `localStorage`, alongside
  `backup-center.js:21`'s `SORT_PREF_KEY = 'backupCenter.sortPreference'` — both use ad hoc
  per-module localStorage keys with no shared namespacing convention or central registry
  of keys in use. Not a bug, but worth a note for a future
  "what's in localStorage across this app" audit. `[NEW]` (informational).
- `plan_volume_panel.js:244-247` — listens for a custom `workout-plan:volume-affecting-change`
  DOM event (debounced 150 ms) to refresh. This event is dispatched by
  `notifyVolumeAffectingPlanChange` from `workout-plan-events.js`, which is also called
  directly by `backup-center.js:795` (`handleConfirmAction`, after a successful restore)
  and `program-backup.js:151` (`showAutoBackupBanner`'s restore handler — dead code path,
  see above). This is the one piece of real cross-module coupling in this phase's file
  set, and it's done cleanly via a custom event rather than direct imports/globals.
  `[NEW]` (positive; confirms the "Refactor safely" playbook's event-based decoupling is
  actually followed here, not just aspirational).

## static/js/modules/exports.js (143 lines)

**Verdict: matches the plan's WP3.5 count exactly — 2 raw `fetch()` calls, both are
blob-download flows and both are legitimate exceptions per the wrapper's `.json()`-only
content handling.** `[CONFIRMS-PLAN]`.

- **Raw `fetch()` inventory — exactly 2:**
  1. `exports.js:42` (`exportToExcel`) → `GET /export_to_excel?view_mode=...`, reads
     `Content-Disposition` header for filename, then `.blob()`. Legitimate exception.
  2. `exports.js:116` (`exportSummary`) → `GET /export_{type}_summary`, then `.blob()`
     with a hardcoded `${type}_summary.xlsx` filename (does not read
     `Content-Disposition` at all, unlike #1 — inconsistent between the two blob-download
     functions in the same file, though low-impact since the filename is deterministic
     from a known `type` param anyway). `[NEW]` (very low severity, informational).
- `exports.js:24-90` (`exportToExcel`) contains **11 `console.log` statements**
  (lines 26, 36, 40, 49–52, 62, 67, 70) that appear to be leftover debugging
  instrumentation (`'=== Starting export to Excel ==='`, `'=== Response received ==='`,
  logging every response header) — none of the other blob-export function
  (`exportSummary`, right below it in the same file) or any other file in this phase logs
  at this verbosity. `[NEW]` — dead debug scaffolding left in shipped code; safe to
  delete, zero behavioral dependency (nothing reads these logs downstream).
- `exports.js:92-112` (`exportToWorkoutLog`) — the one function in this file that
  **already uses `api.post`** (not raw fetch) and the wrapper's `isHandledApiError`/
  `logApiError` helpers correctly to distinguish "handled" validation/no-data failures
  (shown as a `warning` toast) from genuine errors (shown as `error`). This is the most
  modern/idiomatic of the three functions in the file and shows the target end-state the
  other two blob functions can't fully reach (blobs aren't `.json()`), but at minimum the
  9-line duplicate blob-download-and-click boilerplate (create `<a>`, set `href`/`download`,
  append, click, revoke, remove) between `exportToExcel` (`exports.js:71-83`) and
  `exportSummary` (`exports.js:126-136`) — and a **third, near-identical copy** in
  `volume-splitter.js:476-484` (`exportToExcel`, the volume-plan one) — is a 3x-duplicated
  "trigger a file download from a blob" helper that never got extracted anywhere in this
  phase's files. `[NEW]` — good small-WP candidate: a `downloadBlob(blob, filename)`
  helper in a shared module (`fetch-wrapper.js` itself, or a new `download-helper.js`)
  would collapse three copies of identical DOM-manipulation boilerplate into one, and pairs
  naturally with WP3.5 since all three call sites are being touched for the fetch-wrapper
  migration anyway.
- `hasExercisesInPlan()` (`exports.js:8-22`) — a DOM-inspection heuristic (looks for `<tr>`
  rows in `#workout_plan_table_body` that aren't empty-state rows) duplicated as a guard in
  both `exportToExcel` (line 29) and `exportToWorkoutLog` (line 95), but not in
  `exportSummary` (which exports weekly/session summaries, not the plan table, so correctly
  doesn't need this guard — not a gap, just confirming the asymmetry is intentional).
  `[NEW]` (informational, no defect).

---

## Cross-cutting seeds

1. **WP3.5's raw-fetch counts for `volume-splitter.js` (7) and `exports.js` (2) are both
   exactly right**, but for `volume-splitter.js` the WP description ("migrate raw fetch
   calls to the fetch-wrapper.js contract") undersells the work: lines 16-90 are a ~50-line
   parallel reimplementation of `apiFetch`'s envelope-unwrap/error-normalize logic
   (`isWrappedApiResponse`/`isApiFailure`/`unwrapApiPayload`/`getApiErrorMessage`/
   `parseJsonResponse`) that should be deleted wholesale, not call-site-swapped. Recommend
   amending WP3.5's scope note for this file specifically.
2. **`program-backup.js`'s `showAutoBackupBanner` (lines 104-162) is dead code with a live
   import chain** — defined, imported into `app.js`, assigned to `window`, but zero actual
   call sites anywhere in routes/utils/templates/JS/tests/e2e. Its intended trigger
   (`/erase-data`'s success path in `templates/welcome.html:387-412`) doesn't call it or
   read an `auto_backup` field from the response. This is a stronger dead-code case than a
   typical unused constant (rule 8 in the plan) — it's a fully-built feature (~60 lines,
   its own restore-click handler, its own DOM banner) that got orphaned. Worth a dedicated
   Phase-0-style WP: either wire it into `/erase-data` (if the backend already returns
   `auto_backup`) or delete it + its `app.js` wiring.
3. **Silent failure in `volume-splitter.js`'s highest-frequency network call**:
   `calculateVolume()` (fires on every slider drag, debounced) has a `.catch()` that only
   `console.error`s — no `showToast`, unlike every one of the other 5 non-blob fetches in
   the same file. A flaky `/api/calculate_volume` response leaves the user staring at
   stale results with zero indication anything went wrong.
4. **Three independent copies of the same blob-download-and-click boilerplate**
   (`exports.js` ×2, `volume-splitter.js` ×1) plus **two independent copies of the same
   6-line `escapeHtml`** (`backup-center.js`, `program-backup.js`) — neither pair is large,
   but both are exact-logic duplicates sitting in files that already import from each
   other's neighborhood (`backup-center.js` imports 6 of `program-backup.js`'s 7 exports;
   `volume-splitter.js` and `exports.js` are both wired from `app.js` for "the Excel
   export" under a name collision — see #5). A tiny shared `dom-utils.js` (escapeHtml,
   downloadBlob) would remove both duplication pairs and is a natural rider on WP3.5's
   PR since WP3.5 already touches all three files with duplicate download logic.
5. **`backup-center.js` vs. `program-backup.js` is not a duplication problem** — it's
   correct layering (UI page-controller vs. API/shared-utility module), and
   `static/js/CLAUDE.md`'s file table already documents them as a pair under "Backups" for
   exactly this reason. The one real coupling risk found is internal to
   `backup-center.js` itself: `renderBackupDetails`'s side effect of unconditionally
   clearing the pending-action and restore-result panels (lines 587-588) is relied on by
   two different call sites in fragile, undocumented ways — once benignly (the normal
   detail-load path wants a clean slate) and once requiring a manual workaround
   (`handleConfirmAction`'s restore branch has to re-paint the restore result after
   `refreshBackupCenter` wipes it), and once as an apparent UX regression (the "save
   current plan first" button's success handler doesn't realize its `refreshBackupCenter`
   call will silently dismiss the restore confirmation the user was mid-flow on).
