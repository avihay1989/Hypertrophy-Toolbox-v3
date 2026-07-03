# Phase 13 — JS: profile / muscle-map / media

Line-by-line read of `static/js/modules/user-profile.js` (1483), `muscle-selector.js`
(817), `bodymap-svg.js` (278), `exercise-video-modal.js` (177),
`exercise-image-preview.js` (131), plus `static/js/CLAUDE.md` and
`.claude/rules/frontend.md` for context. Cross-checked against `docs/REFACTOR_PLAN.md`
v2 WP3.5 (raw-fetch migration + heatmap sequencing note), the MuscleMap unification
(PR #87, `19937b1`), the YouTube modal fallback (PR #88), `docs/MASTER_HANDOVER.md`'s
"Fatigue meter" / "workout.cool integration" rows, and `utils/profile_estimator.py`
(`muscle_coverage_state`, `BODYMAP_MUSCLE_KEYS`, `COLD_START_RATIOS`,
`COHORT_BODYWEIGHT_KG`/`COHORT_HEIGHT_CM`/`COHORT_AGE_YEARS`).

---

## static/js/modules/muscle-selector.js (817 lines)

- **Not an ES module at all — plain classic script.** `templates/workout_plan.html:559`
  loads it as `<script src="...">` with **no `type="module"`**, unlike every other file
  in `modules/` (which all use `<script type="module">` per `static/js/CLAUDE.md:28`).
  The file itself contains zero `import`/`export` statements; it defines `class
  MuscleSelector` and, at the bottom (`muscle-selector.js:813-817`), assigns
  `window.MuscleSelector`, `window.MUSCLE_LABELS`, `window.MUSCLE_TO_BACKEND`,
  `window.SIMPLE_TO_ADVANCED_MAP`, `window.ADVANCED_TO_SIMPLE_MAP` to the global
  object. `workout_plan.html:561-651` then reads `window.MuscleSelector` from an
  inline (non-module) script. **[CONTRADICTS-PLAN] / [RISK]** — WP3.5 lists
  `muscle-selector.js`'s one raw `fetch()` as a same-shape swap-to-`apiFetch` item
  alongside `bodymap-svg.js`, `exercises.js`, etc. That undersells the work: `import {
  apiFetch } from './fetch-wrapper.js'` is not legal syntax in a classic script, so
  this item requires *first* converting the file to `type="module"` (verify the
  inline consumer in `workout_plan.html:561-651` still works — it should, since the
  window assignments are explicit and survive module scoping) before the fetch swap
  is even possible. This is a materially different, larger change than the other six
  items in the WP3.5 list and deserves its own line/checkbox, not lumped in.
- One raw `fetch()` confirmed: `muscle-selector.js:271` (`await fetch(svgPath)`
  inside `loadAndRenderSVG()`), matching the plan's count of 1. **[CONFIRMS-PLAN]**.
  Errors are caught (`catch` at line 290) and rendered as a Bootstrap alert in the
  SVG container — reasonable existing behavior an `apiFetch` swap must preserve
  (this fetch loads a static SVG asset, not a JSON API endpoint, so the `apiFetch`
  `{ok,status,data,error}` contract doesn't map 1:1 — same caveat as `bodymap-svg.js`
  below; likely stays a documented raw-fetch exception rather than an `apiFetch`
  migration, similar to the blob-download carve-out WP3.5 already grants
  `exports.js`).
- Per-instance SVG cache (`this.svgCache`, `muscle-selector.js:187-188,268-276`)
  keyed by path, populated on `switchBodySide()`. This is a **second, independent**
  cache of the exact same two SVG files (`SVG_PATHS` at `muscle-selector.js:151-154`
  is byte-identical to `BODYMAP_SVG_PATHS` in `bodymap-svg.js:6-9`) — the Profile
  page's `bodymap-svg.js` module cache (`svgCache` Map, module-scope) and this
  per-`MuscleSelector`-instance cache never share a fetch even though they load the
  same `/static/bodymaps/hypertrophy-advanced/body_{anterior,posterior}.svg` files.
  **[NEW]** — not a correctness bug (the two pages don't co-load today: workout_plan
  uses `muscle-selector.js`, user_profile uses `bodymap-svg.js`), but it is dead
  duplication in waiting: the committed fatigue-heatmap workstream
  (`docs/fatigue_meter/HEATMAP_PLANNING.md:20`) plans to import `bodymap-svg.js` on
  yet a third page (`/fatigue`), and `HEATMAP_PLANNING.md:84` says the heatmap will
  "reuse the muscle-selector tab pattern" (UI pattern only, not the module) — so the
  duplicate-cache shape will persist rather than converge. Worth a follow-up note if
  WP3.5 or the heatmap work ever touches SVG loading again: extract one shared
  `loadBodymapSvg`-style helper (already exists in `bodymap-svg.js`) and have
  `muscle-selector.js` import it instead of maintaining its own `fetch` + cache —
  blocked today only by `muscle-selector.js` not being a module (see above).
- `SIMPLE_TO_ADVANCED_MAP` / `MUSCLE_TO_BACKEND` (`muscle-selector.js:30-55,110-143`)
  are a **third** independent JS mirror of a canonical-muscle-key taxonomy, separate
  from `bodymap-svg.js`'s `CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES`
  (`bodymap-svg.js:200-220`) and `user-profile.js`'s `COLD_START_RATIOS`/
  `COVERAGE_MUSCLE_CHAIN` mirrors. All three encode the same underlying MuscleMap
  region taxonomy but map it to *different* targets (starter-plan priority-muscle
  backend names vs. Profile coverage-estimator muscle keys vs. cold-start ratios).
  None of the three references the others; there is no shared constants module.
  **[NEW] [RISK]** — see "Cross-cutting seeds" below.
- `getCanonicalKeys()`/`flattenToAdvancedChildren()`/`regionVisualState()`
  (`muscle-selector.js:305-359`) implement the multi-key-region → advanced-leaf
  flattening the header comment (`muscle-selector.js:22-29`) says is required
  because "`upper-back` and `hip-abductors` have no distinct MuscleMap geometry."
  `tests/test_muscle_selector_mapping.py::TestRegionVisualState` (lines 146-178,
  confirmed by read) explicitly Python-ports this same decision table to keep the
  JS-only runtime logic asserted in CI — good existing practice, and it still
  references stale "workout-cool" naming in its docstring (`test_muscle_selector_
  mapping.py:151`: *"the simple-mode (workout-cool) BACK region still ships..."*).
  **[NEW]** — cosmetic, doc/test-comment-only carryover from the retired hybrid
  (PR #87), not a functional bug; harmless to leave or fix opportunistically.
- No dead code from the old workout-cool/react-body-highlighter hybrid remains
  *inside this file* — `SVG_PATHS` already points only at the MuscleMap advanced
  SVGs (`/static/bodymaps/hypertrophy-advanced/...`); there is no simple-mode SVG
  path, no conditional branch for a second vendor, no leftover
  `react-body-highlighter` DOM class handling. **[CONFIRMS-PLAN]** that PR #87 fully
  retired the hybrid at the JS-module level (leftover references live only in
  comments/docs/tests — see "Cross-cutting seeds").

---

## static/js/modules/bodymap-svg.js (278 lines)

- Pure ES module (`export async function loadBodymapSvg`, `export const
  COVERAGE_MUSCLE_CHAIN`, `export const COVERAGE_LIFT_LABELS`, `export function
  annotateBodymapPolygons`), imported only by `user-profile.js:4-9`
  (`annotateBodymapPolygons`, `COVERAGE_LIFT_LABELS`, `COVERAGE_MUSCLE_CHAIN`,
  `loadBodymapSvg`). Correctly follows the module conventions
  `static/js/CLAUDE.md:28` documents (named exports, no defaults).
- One raw `fetch()` confirmed: `bodymap-svg.js:17` inside `loadBodymapSvg()`, matching
  the plan's count of 1. **[CONFIRMS-PLAN]**. Same static-asset caveat as
  `muscle-selector.js` above — this fetches an SVG file, not a JSON API response, so
  wrapping it in `apiFetch`'s `{ok,status,data,error}` shape doesn't fit cleanly
  unless `apiFetch` supports a raw/text response mode. Module-scope `svgCache`
  (`bodymap-svg.js:11`, a `Map`) persists for the page lifetime — reasonable single
  consumer today.
- `COVERAGE_MUSCLE_CHAIN` (`bodymap-svg.js:28-120`) and `COVERAGE_LIFT_LABELS`
  (`bodymap-svg.js:124-189`) are explicitly commented (`bodymap-svg.js:24-27,122-123`)
  as manual JS mirrors of `MUSCLE_TO_KEY_LIFT` / `KEY_LIFT_LABELS` in
  `utils/profile_estimator.py`, "KEEP IN SYNC" by convention only — no automated
  drift test found in this phase's file set (the Python-side comment at
  `profile_estimator.py:2305-2308` names a drift-detection test,
  `test_workout_cool_back_region_multi_key_mapping_matches_python_keys`, but that
  test's actual scope — confirmed by reading `tests/test_muscle_selector_mapping.py`
  — is the `muscle-selector.js` SIMPLE_TO_ADVANCED taxonomy, **not**
  `COVERAGE_MUSCLE_CHAIN`/`COVERAGE_LIFT_LABELS`). **[RISK]** — the two large lift-chain
  dictionaries in `bodymap-svg.js` have no cross-file automated parity check despite
  the "KEEP IN SYNC" comment promising one exists; a future edit to
  `MUSCLE_TO_KEY_LIFT` in Python would silently desync the JS coverage popovers.
  Flag for `docs/REFACTOR_PLAN.md` Phase 2 (WP2.1 profile_estimator split) or a
  dedicated small follow-up: add a parity test (JSON-export the Python dict, assert
  equality against the JS literal, or vice versa) — this phase found the gap but
  fixing it is out of scope here.
- Stale comment: `profile_estimator.py:2300` still says *"Each backend muscle key
  drives one or more polygons on the workout-cool SVG"* — the actual runtime is now
  MuscleMap (`bodymap-svg.js` header comment correctly says "MuscleMap anatomy art
  (melihcolpan/MuscleMap, MIT)"). **[NEW]** — Python-side leftover from the retired
  hybrid (PR #87 retired workout-cool for the *JS/SVG* layer but nobody swept the
  matching Python docstring). Low-risk doc fix.
- `CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES` (`bodymap-svg.js:200-220`) is the third
  independent muscle-taxonomy mirror noted under `muscle-selector.js` above — maps
  MuscleMap region keys to `profile_estimator.py` `BODYMAP_MUSCLE_KEYS` values (e.g.
  `'Front-Shoulder'`, `'Gluteus Maximus'`), a different vocabulary than
  `muscle-selector.js`'s `MUSCLE_TO_BACKEND` (e.g. `'Shoulders'`, `'Glutes'`) even
  though both ultimately describe overlapping body regions.
- `annotateBodymapPolygons()` (`bodymap-svg.js:248-277`) is idempotent by design
  (re-running just re-derives `dataset.bodymapMuscle`/`bodymapLabel`/`coverageState`)
  and correctly documents the `void side` parameter as reserved for a
  not-yet-needed side-specific branch (`bodymap-svg.js:249`) — no dead code, just an
  intentionally unused param with a clarifying comment.
- **Heatmap sequencing note verified against `docs/MASTER_HANDOVER.md:102` and
  `docs/fatigue_meter/HEATMAP_PLANNING.md:20,84`**: the committed heatmap work is a
  hard *module-import* dependency on `bodymap-svg.js` ("reuses the MuscleMap figure +
  `bodymap-svg.js`"), but its relationship to `muscle-selector.js` is only "reuse the
  muscle-selector **tab pattern**" — i.e. copy the front/back-tab markup/behavior,
  not `import` the module. **[CONTRADICTS-PLAN]** in a narrow but real way: WP3.5's
  finding #14 sequencing note ("the committed fatigue body-heatmap workstream reuses
  `bodymap-svg.js`/`muscle-selector.js`") treats both files as equally
  heatmap-coupled and therefore equally sequencing-sensitive. Only `bodymap-svg.js`
  is actually a shared-import risk (editing its `fetch()`/export surface while
  heatmap work is in flight could conflict); `muscle-selector.js` is a
  copy-the-pattern reference with no shared runtime code, so its raw-fetch migration
  is not blocked by the heatmap timeline the way the plan implies. Executors should
  re-read `docs/MASTER_HANDOVER.md` at execution time as the plan already instructs,
  but the risk is asymmetric between the two files, not equal.

---

## static/js/modules/user-profile.js (1483 lines)

**No raw `fetch()` anywhere** — every network call goes through `api.get`/`api.post`
from `fetch-wrapper.js` (`user-profile.js:1,264,1120,1208,1373,1393,1430,1440,1453,
1459`). **[CONFIRMS-PLAN]** (the plan doesn't list this file under WP3.5's raw-fetch
targets, consistent with what's actually in the file).

### Section map (natural split seams for the WP3.5 follow-up note)
The file is a single flat module with no internal class structure; it reads as six
clearly separable concerns stacked in file order, each already delimited by its own
`// ===...` banner comment or Issue/Phase tag:

| Lines | Concern | Notes |
|---|---|---|
| 1-9 | Imports | `api`, `showToast`, `initializeExerciseImagePreview`, 4 named imports from `bodymap-svg.js` |
| 13-230 | **Estimator-mirror constants + form-reading helpers** (`COLD_START_RATIOS`, `COLD_START_CANONICAL_COMPOUND`, `HIGH_IMPACT_LIFT_PRIORITY`, `ACCURACY_MAJOR_MUSCLE_GROUPS`, `classifyExperienceTier`, `experienceMultiplier`, `nextTierMultiplier`, `COHORT_*` constants, `classificationFromForm`, `liftRowsFromForm`, `isLiftFilled`, `epley1rm`, `coldStart1rm`, `computeAccuracyBand`, `bandPillLabel`, payload builders) | Explicitly commented (`user-profile.js:13-18,74-76`) as a JS port of `utils/profile_estimator.py` that "MUST be matched ... and vice versa" |
| 232-357 | **Generic autosave engine + collapse toggles** (`bindAutosaveForm`, `performSave`, `setAutosaveStatus`, `initializeCollapseToggles`) | Not Profile-specific in mechanism — `bindAutosaveForm` takes `formId`/`buildPayload`/`endpoint` as parameters; only the 3 call sites at `user-profile.js:1467-1474` are Profile-specific. Good extraction candidate to a shared `autosave-form.js` if another page ever needs debounced-autosave forms. |
| 359-708 | **Profile insights card** (`renderTiles`, `renderCohortSummary`, `renderCohortBars`, `renderProfileInsights`, `bindInsightsAutoUpdate`) | Issue #18 tiles/bars/donut rendering, ~350 lines |
| 710-1061 | **Bodymap coverage view** (Issue #19: `BODYMAP_STATE`, `computeMuscleCoverage`, `mountBodymapForSide`, `aggregateCoverageForRegion`, `applyCoverageStateToPolygons`, `popoverBodyForState`, `showPopover`/`hidePopover`, `attachPolygonInteractivity`, `initializeBodymap`, `renderBodymapCoverage`) | ~350 lines; the module-level mirror of `muscle_coverage_state` (see below) |
| 1063-1234 | **Two independent settings toggles**: Learned Calibration mode (1063-1154) and Phase 2D-A Fatigue Context settings (1156-1234) | Structurally near-identical optimistic-update-with-rollback pattern duplicated twice (see below) |
| 1236-1464 | **Phase 2B/2C Learned Calibration review/control surface** (`renderLearnedCalibrations`, `buildPromoteCell`, `renderIgnoredTransfers`, `refreshCalibrationReview`, `bindCalibrationReview`) | Table rendering + promote/unignore/clear/reset actions against `/api/user_profile/calibration/*` |
| 1466-1483 | `initializeUserProfile()` wiring + `DOMContentLoaded` | Entry point |

**[NEW]** — this gives WP3.5's "optional follow-up split" for `user-profile.js` five
concrete non-overlapping module candidates (estimator-mirror/form-helpers,
autosave-engine, insights-card, bodymap-coverage, calibration-settings+review), each
independently a few hundred lines, matching the file's own banner-comment
boundaries almost exactly — a WP3.3/3.4-style "characterize then extract" pass would
have very low ambiguity here since the seams are already comment-delimited.

### Calibration Settings vs. Fatigue Context toggle — duplicated pattern
`bindCalibrationSettings()` (`user-profile.js:1100-1154`) and
`bindFatigueContextSettings()` (`user-profile.js:1187-1234`) are near-identical in
shape: read current form state → optimistically sync a dependent control → `api.post`
→ on success merge server response + update status text + toast; on failure roll back
every field to the previous snapshot + re-sync + re-render status + error toast. Each
implements its own local `previousSettings`/`currentSettings` closure variables and
its own rollback block (compare `user-profile.js:1116-1153` to `1204-1233`). **[NEW]**
— a shared `bindOptimisticSettingsForm({ formId, endpoint, readForm, syncControls,
updateStatusText, ... })` helper would collapse ~90 lines into one generic function
+ two ~15-line config calls, which is exactly the kind of "extract-method, no logic
change" cleanup the refactor plan's Phase 3 JS work is aimed at (not currently listed
as its own WP — worth folding into the WP3.5 follow-up scope for `user-profile.js`
rather than a new WP, since it's the same file).

### muscle_coverage_state parity spot-check (Python ↔ JS)
Read `utils/profile_estimator.py:2327-2410` (`muscle_coverage_state`) side-by-side with
`user-profile.js:726-786` (`computeMuscleCoverage`): the state-derivation logic
(`not_assessed` / `measured` / `cross_muscle` / `cold_start_only` via
`first_filled_idx`) and the improvement-slug selection (first unfilled chain entry)
match exactly, including the `estimated_1rm` gating (`weight > 0 and reps > 0`, not
applied to `bodyweight_*` slugs) at `profile_estimator.py:2378` vs.
`user-profile.js:748`. **[CONFIRMS-PLAN]** — no drift found today; this is the same
"manual JS mirror of Python, no automated parity test" pattern flagged above for
`bodymap-svg.js`'s `COVERAGE_MUSCLE_CHAIN`, just for the state-machine instead of the
raw data tables. Combined, that's **3 independent hand-synced mirrors** in this
phase's two files (`COLD_START_RATIOS`+cohort constants, `COVERAGE_MUSCLE_CHAIN`+
`COVERAGE_LIFT_LABELS`, `computeMuscleCoverage`↔`muscle_coverage_state`), all pointed
at `utils/profile_estimator.py`, none covered by an automated cross-language parity
test found in this phase.
- **WP2.1 impact**: the plan's WP2.1 (split `profile_estimator.py` into a package,
  moving `muscle_coverage_state`/`cohort_ranges` into `cohort.py`) is a pure move with
  re-exports, so the JS comments' literal file references (`utils/profile_estimator.py`
  at `user-profile.js:14,75` and `bodymap-svg.js:25`) will still resolve correctly
  after the split (re-exports keep `from utils.profile_estimator import
  muscle_coverage_state` working) — but the comments name a *file*, and after WP2.1
  the real source of truth moves to `utils/profile_estimator/cohort.py`. **[RISK]** —
  low severity, but WP2.1 or a docs-sync follow-up should update these three JS
  comment pointers to the new submodule path so a future reader isn't sent to a
  296-line re-export shim looking for logic that moved.

### 2D-A independent Profile toggle — verified
`bindFatigueContextSettings()` (`user-profile.js:1187-1234`) posts to
`/api/user_profile/fatigue_context_settings` completely independently of
`bindCalibrationSettings()`'s `/api/user_profile/calibration_settings` — separate
forms (`profile-fatigue-context-form` vs. `profile-calibration-form`), separate
endpoints, separate status-text elements (`[data-fatigue-context-text]` vs.
`[data-calibration-text]`). **[CONFIRMS-PLAN]** — matches MEMORY.md's note that 2D-A
is an "independent Profile toggle," and the code comment at `user-profile.js:1156-
1161` explicitly states "No estimator math is touched here," consistent with the
protected-zone rule (advisory-only, additive `fatigue_context` block).

### Learned-calibration review-table + promote wiring — verified
`renderLearnedCalibrations()` / `buildPromoteCell()` (`user-profile.js:1266-1330`)
populate from `GET /api/user_profile/calibration/dashboard`
(`refreshCalibrationReview`, line 1373) and the promote button
(`user-profile.js:1407-1436`) posts to `/api/user_profile/calibration/promote` with a
`window.confirm()` gate whose copy differs based on whether an existing reference
lift is being overwritten (`promote.dataset.promoteHasExisting`). No calculation
logic lives here — purely read-and-post against precomputed `row.promotable`/
`row.promote_weight_kg`/`row.promote_reps` fields the dashboard endpoint already
computed server-side (comment at `user-profile.js:1299-1302` confirms this
design choice — "so the click handler can build the confirm copy without a
per-click round-trip"). **[CONFIRMS-PLAN]** — matches MEMORY.md's Phase 2C shipped
note; nothing found here to blocklist for the JS-split work.

### Global/module state in this file
- `BODYMAP_STATE` (`user-profile.js:714-717`, `{ side, svgMounted: {front,back} }`) and
  `bodymapInitialized` (line 1004) are module-scope singletons — correct for a
  single-page module with one bodymap instance; would need to become instance state
  if this module were ever reused twice on one page (not currently the case).
- No `window.*` globals are set by this file (unlike `muscle-selector.js`) — it's a
  clean ES module with only named imports/no exports (nothing else imports from
  `user-profile.js`, confirmed via grep — it's a leaf/page-entry module, same
  pattern as `workout-plan.js`).

---

## static/js/modules/exercise-video-modal.js (177 lines)

- Clean, small, single-purpose ES module (`export function openExerciseVideoModal`,
  `export function buildPlayButton`), also assigns `window.openExerciseVideoModal` /
  `window.buildExerciseVideoButton` (`exercise-video-modal.js:174-177`) — but unlike
  `muscle-selector.js`, this is a **documented, deliberate** dual-export: the header
  comment explains `workout-log.html` is server-rendered Jinja using inline
  `onclick` handlers in places, so the window globals are an intentional escape
  hatch alongside the real ES exports, not the file's only export mechanism.
  **[CONFIRMS-PLAN]** — no convention violation; this is the pattern
  `static/js/CLAUDE.md` doesn't explicitly bless but is a reasonable, narrow,
  self-documented exception.
- **PR #88 search-tab fallback verified**: `openExerciseVideoModal()`
  (`exercise-video-modal.js:91-123`) checks `isValidYoutubeId(videoId)` first
  (`YOUTUBE_ID_RE = /^[A-Za-z0-9_-]{11}$/`, line 23); if invalid/null/empty it calls
  `window.open(buildSearchUrl(exerciseName), '_blank', 'noopener,noreferrer')` and
  returns immediately — **no modal is opened for uncurated rows**, matching the
  commit title "uncurated rows open a YouTube search tab" exactly. `buildPlayButton()`
  (`exercise-video-modal.js:134-170`) independently derives the same `curated`
  boolean and swaps both the icon (`fa-play` vs `fa-search`) and the `aria-label`/
  `title` text so the affordance is visually distinct before the click even happens —
  no drift between the button's presented affordance and the click behavior (both
  derive from the same `isValidYoutubeId` check, just called twice on the same
  input — trivial, not a real duplication concern given the function is a 1-line
  regex test).
- Second fallback layer verified: if a curated id *is* valid but Bootstrap's `Modal`
  isn't loaded (`getBootstrapModal()` returns `null` at `exercise-video-modal.js:57-
  59`), `openExerciseVideoModal` opens the YouTube watch page directly
  (`exercise-video-modal.js:99-103`) rather than silently no-opping — comment at
  line 99-100 explicitly calls this out ("the click is never a no-op"). **[NEW]** —
  good defensive design, worth noting since it's a second distinct fallback path
  beyond the curated/uncurated split the plan and MEMORY.md focus on.
- No raw `fetch()`, no dead code, no leftover workout-cool/react-body-highlighter
  references. **[CONFIRMS-PLAN]**.

---

## static/js/modules/exercise-image-preview.js (131 lines)

- Clean, single-purpose ES module, one export (`initializeExerciseImagePreview`),
  called from two page-entry modules: `user-profile.js:11` and
  `workout-plan.js:8` (confirmed via grep). Idempotent per DOM root via a
  module-scope `initializedRoots` `WeakSet` (`exercise-image-preview.js:8,101-102`)
  — safe against double-init if a future page imports it twice.
- **"Fallback chain" clarification** — the phase brief flagged an "image preview
  fallback chain" to watch for; on inspection, **this file has no fallback chain of
  its own**. `showPreview()` (`exercise-image-preview.js:64-77`) only guards on
  `target?.src` truthiness and otherwise just displays whatever `src`
  (`target.currentSrc || target.src`) the `<img>` element already resolved to. The
  actual media-path fallback logic (deciding *which* image URL an exercise gets,
  including any curated → generic → placeholder chain) lives in
  `resolveExerciseMediaSrc()` in `static/js/modules/exercise-helpers.js` (called from
  `workout-plan.js:1796`, confirmed by read), which is **outside this phase's file
  list**. **[NEW]** — flagging so a future phase auditing `exercise-helpers.js` /
  `workout-plan.js` media logic doesn't assume this file already covers it; the two
  concerns (tooltip positioning vs. URL resolution) are cleanly separated across
  files today, which is good, but the brief's phrasing could mislead a reader into
  thinking the fallback chain lives here.
- `PREVIEW_SELECTOR = 'img.exercise-thumbnail, img.reference-lift-icon'`
  (`exercise-image-preview.js:1`) — the two consumer templates/JS files use
  different class names for what is conceptually the same widget
  (`exercise-thumbnail` from `workout-plan.js:1798`, `reference-lift-icon`
  presumably from a Profile-page template) but both are handled by one selector, so
  no duplication risk here, just worth noting the two naming conventions if a future
  pass audits template class-naming consistency.
- Global singleton tooltip element (`preview`, `previewImage`, `previewCaption` at
  module scope, `exercise-image-preview.js:4-8`) lazily created once via
  `ensurePreview()` and appended to `document.body` — correct singleton pattern for
  a page-level hover tooltip; no per-instance state leakage risk since only one
  tooltip can be visible at a time by design.
- No raw `fetch()`, no dead code, no leftover hybrid references. **[CONFIRMS-PLAN]**.

---

## Cross-cutting seeds

1. **Three independent, hand-maintained JS mirrors of Python muscle taxonomy/logic,
   zero automated parity tests found for two of them.** `muscle-selector.js`
   (`SIMPLE_TO_ADVANCED_MAP`/`MUSCLE_TO_BACKEND`, only reachable from
   `/generate_starter_plan`'s priority-muscle payload — no Python counterpart to
   even drift against, since that mapping is JS-only) is a separate concern from
   `bodymap-svg.js` (`COVERAGE_MUSCLE_CHAIN`/`COVERAGE_LIFT_LABELS`, mirrors
   `MUSCLE_TO_KEY_LIFT`/`KEY_LIFT_LABELS` in `profile_estimator.py`, "KEEP IN SYNC"
   comment but no automated test found) and `user-profile.js`
   (`computeMuscleCoverage` mirrors `muscle_coverage_state`, plus `COLD_START_RATIOS`
   + cohort constants mirror their Python namesakes — same no-automated-test gap).
   The one automated cross-language test that does exist
   (`tests/test_muscle_selector_mapping.py::TestRegionVisualState`) covers the
   `muscle-selector.js` region-flattening decision table, not the two
   `profile_estimator.py`-mirroring dictionaries in `bodymap-svg.js`/`user-profile.js`.
   Any future WP touching `profile_estimator.py`'s `MUSCLE_TO_KEY_LIFT`,
   `KEY_LIFT_LABELS`, `COLD_START_RATIOS`, or the `COHORT_*` constants should budget
   for manually re-checking these three JS blocks — grep alone won't catch semantic
   drift (the dicts don't share key names 1:1 across files).

2. **`muscle-selector.js` is the one file in `static/js/modules/` that isn't an ES
   module**, which quietly changes the cost of WP3.5's raw-fetch migration for it
   from "swap one call" to "convert the loading mechanism, then swap one call."
   Worth a one-line scope correction in the plan before that item is executed, and
   worth checking whether any *other* future JS-module-conventions pass
   (`static/js/CLAUDE.md` says "Modules are loaded with `<script type="module">`")
   should treat `muscle-selector.js` as its own small follow-up WP rather than a
   line item inside WP3.5.

3. **Heatmap-sequencing risk is asymmetric, not symmetric, between the two files
   WP3.5's finding #14 names together.** `bodymap-svg.js` is a real shared-import
   dependency for the committed `/fatigue` heatmap (`docs/fatigue_meter/
   HEATMAP_PLANNING.md:20`); `muscle-selector.js` is only a copy-the-tab-pattern
   reference (`HEATMAP_PLANNING.md:84`), not an import target. Sequencing
   `bodymap-svg.js`'s fetch-migration ahead of/behind the heatmap work matters;
   sequencing `muscle-selector.js`'s does not (subject to re-confirming against
   `docs/MASTER_HANDOVER.md` at execution time, as the plan already instructs).

4. **Leftover "workout-cool" naming survives only in comments/docstrings, not in
   runtime logic**, confirming PR #87 was a clean functional retirement but not a
   full documentation sweep: `utils/profile_estimator.py:2300` ("workout-cool SVG"),
   `tests/test_muscle_selector_mapping.py:151` ("simple-mode (workout-cool) BACK
   region"), `static/css/pages-workout-plan.css:7211` ("Uses vendor SVGs from
   react-body-highlighter (MIT License)") and `:7402` ("vs workout-cool's ~268"
   viewBox comparison — this one is arguably still useful historical context for
   the stroke-width scaling rule immediately below it, so not a clear-cut delete).
   None of these affect behavior; all are candidates for a docs/comment-hygiene
   pass whenever those specific files are next touched for another reason (not
   worth a standalone WP).

5. **`user-profile.js` (1483 lines) has five ready-made split seams** (estimator-
   mirror/form-helpers, generic autosave engine, insights card, bodymap-coverage
   view, calibration settings+review) already delimited by the file's own banner
   comments (see table above) — the WP3.5 "optional follow-up" for this file should
   be low-risk/low-ambiguity extraction work, and the calibration-settings vs.
   fatigue-context-settings duplicated optimistic-update pattern
   (`user-profile.js:1100-1154` vs. `1187-1234`) is a genuine same-file
   simplification opportunity worth folding into that same follow-up rather than
   opening a separate WP.
