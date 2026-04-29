# workout.cool Integration — Planning

**Status:** §3 (Simple-mode body-map hybrid swap, workout-plan only) shipped 2026-04-29. §5 (YouTube reference video modal, both `/workout_plan` and `/workout_log`) shipped 2026-04-30. §4 free-exercise-db media still pending; §3.6 Profile coverage body map remains deferred. See [`EXECUTION_LOG.md`](EXECUTION_LOG.md) for the audit trail.
**Owner:** Yaakov Avihai Shai
**Source project:** [Snouzy/workout-cool](https://github.com/Snouzy/workout-cool) — MIT-licensed (Mathias Bradiceanu, 2023).
**Plan revision:** 2026-04-29 r4 — folds codex 5.5 third-review precision fixes. Key r4 changes: §3.4.1 pseudocode flattens simple keys through `SIMPLE_TO_ADVANCED_MAP` because `selectedMuscles` stores advanced child keys, not simple keys; function names corrected to `toggleMuscle()` and `updateAllRegionStates()` (the actual symbols at [muscle-selector.js:554,617](../../static/js/modules/muscle-selector.js#L554)); §3.5 `muscle-selector.js` bullet describes a local `SVG_PATHS` / `getSvgPathForMode()` change with absolute `/static/vendor/...` URLs and drops the `VENDOR_SLUG_TO_CANONICAL` mention (new SVGs ship pre-canonicalized `data-canonical-muscles`); §3.7 multi-key state-derivation test enumerates expanded advanced children (`lats, rhomboids, teres-major, teres-minor, erector-spinae`) and adds rhomboids-only / erector-spinae-only `partial` regression cases; column renamed `media_id` → `media_path` to reflect actual content (full relative path) with strict path-shape validation; §4.6 `escapeHtml()` unit test uses synthetic name `Coach's <Test> Press` so the input actually exercises quote and angle-bracket escaping (`Bulgarian Split Squat` has neither).

## 1. Goal

Adopt three UX elements observed on workout.cool, while preserving every existing feature of the Hypertrophy Toolbox:

1. **Body map SVG art** — replace the look of the muscle picker with workout.cool's anatomy art (hybrid scope; see §3).
2. **Exercise reference images** — give every exercise an icon, sourced from [free-exercise-db](https://github.com/yuhonas/free-exercise-db) (Unlicense / public domain).
3. **YouTube reference videos** — let users open a video for any exercise (external link + embedded iframe).

These three are independent and can ship in any order. No DB-schema/JSON-contract change is required by §3 (body map is presentation-only). §4 and §5 each add one nullable column.

### 1.1 Project invariants

- All DB/JSON changes in §4/§5 are **additive and nullable**. Old rows with NULL `media_path` / `youtube_video_id` must render exactly like today except for optional empty-state controls.
- This protects existing flows: plan generation, add/remove/update, export-to-log, replace exercise, superset, progression, backup restore, Profile estimator.
- **No direct mutation of the committed `data/database.db`** as a source of truth. Schema changes live in `utils/db_initializer.py`; mapping/import scripts produce reproducible artifacts. Local DB updates during verification are generated outputs, not the design record.
- All mapping CSVs and import scripts use **`exercise_name`** as the catalogue key. The `exercises` table has no numeric `id` ([utils/db_initializer.py:30-46](../../utils/db_initializer.py#L30-L46)) — `exercise_name TEXT PRIMARY KEY`. Joins use `COLLATE NOCASE`.

## 2. Non-goals

- No replacement of `/workout_plan`, `/user_profile`, or any existing flow's UX wholesale. We are decorating the existing screens, not rebuilding them.
- No changes to the canonical muscle keys, `MUSCLE_TO_BACKEND` mapping, or simple↔advanced mapping in [docs/muscle_selector.md](../muscle_selector.md).
- No video hosting, scraping, caching of YouTube content, or thumbnail re-hosting. We embed via the official iframe only.
- No 3-step "Equipment → Muscles → Exercises" wizard from workout.cool. The current generator UX stays.
- **No surrogate-id migration on `exercises`.** The schema stays keyed by `exercise_name`. Any migration to add a numeric id would be a separate, larger change touching every join and is out of scope for this integration.

## 3. Body Map — Hybrid Swap (Decision: Option 1)

### 3.1 Why hybrid

workout.cool's body SVG has only **13 simple-level muscle groups** (`ABDOMINALS, BACK, BICEPS, CALVES, CHEST, FOREARMS, GLUTES, HAMSTRINGS, OBLIQUES, QUADRICEPS, SHOULDERS, TRAPS, TRICEPS`).

- Their **simple** view is *less* granular than ours: they lump `lats + upper-back + lowerback` into one `BACK` and `front-shoulders + rear-shoulders` into one `SHOULDERS`.
- Their **advanced/scientific** view does **not exist** — there are no separately-clickable paths for upper vs mid-lower pec, three triceps heads, gastrocnemius vs soleus, gluteus medius vs maximus, etc.

To preserve our scientific picker, we keep both art sources side-by-side:

| View | SVG source | Notes |
|---|---|---|
| Simple | workout.cool art (new) | Visual upgrade; mapped onto our simple model (see §3.3) |
| Advanced | `react-body-highlighter` (current) | Untouched. All scientific keys preserved. |

The user toggles between Simple and Advanced exactly as today — only the art on the Simple tab changes.

**Scope for first pass: workout-plan generator only.** Profile coverage bodymap stays on `react-body-highlighter` until §3 proves the variant loader and visual baselines are stable. See §3.6.

### 3.2 Asset extraction

workout.cool's body map is **not a single SVG**. It is ~4,200 lines of TSX across 14 React components in `src/features/workout-builder/ui/muscles/*.tsx`, each a `<g>` of inline `<path d="…">` elements wired to `onClick={ExerciseAttributeValueEnum.X}`.

Conversion strategy:

1. Extract the raw `<path d="…">` blocks per component.
2. Group them into two new files: `body_anterior_workoutcool.svg` and `body_posterior_workoutcool.svg` (anterior- vs posterior-facing components, judged by viewBox coords).
3. Replace React-isms (`className`, `data-elem={Enum.X}`, `onClick`) with plain SVG attributes:
   - `class="muscle-region"`
   - `data-canonical-muscles="<key1>,<key2>,…"` — comma-separated list of our canonical **simple** keys for this region. Single-key regions (e.g. `CHEST` → `chest`) carry a list of one; multi-key regions (e.g. `BACK` → `lats,upper-back,lowerback`) carry the full list. Values are pre-canonicalized at extraction time, so `VENDOR_SLUG_TO_CANONICAL` does **not** need new entries.
   - Hover/click handlers attach in JS via existing `MuscleSelector` machinery — no per-path JS.
4. Preserve `viewBox`, copy outline `<path>`s into a `.body-outline` group, copy muscle `<path>`s into a `.muscle-regions` group — matching the structure documented in [docs/muscle_selector.md §SVG File Structure](../muscle_selector.md).

### 3.3 Vendor key → canonical key mapping (Simple view)

Reconciled against the current `MUSCLES_BY_SIDE` in [static/js/modules/muscle-selector.js:262-270](../../static/js/modules/muscle-selector.js#L262-L270). The mapping is intentionally lossy: workout.cool's coarser `BACK` and `SHOULDERS` regions select multiple of our simple keys at once.

| workout.cool key | Our canonical simple key(s) | `data-canonical-muscles` value |
|---|---|---|
| `CHEST` | `chest` | `chest` |
| `ABDOMINALS` | `abdominals` | `abdominals` |
| `OBLIQUES` | `obliques` | `obliques` |
| `BICEPS` | `biceps` | `biceps` |
| `TRICEPS` | `triceps` | `triceps` |
| `FOREARMS` | `forearms` | `forearms` |
| `SHOULDERS` (front) | `front-shoulders` | `front-shoulders` |
| `SHOULDERS` (back) | `rear-shoulders` | `rear-shoulders` |
| `TRAPS` | `traps` | `traps` |
| `BACK` | `lats` + `upper-back` + `lowerback` (multi-select) | `lats,upper-back,lowerback` |
| `QUADRICEPS` | `quads` | `quads` |
| `HAMSTRINGS` | `hamstrings` | `hamstrings` |
| `GLUTES` | `glutes` | `glutes` |
| `CALVES` | `calves` | `calves` |

**Unmapped-by-art allowlist** — simple keys that workout.cool's SVG cannot represent on a given side. These remain legend/checklist-selectable in Simple view but have no clickable SVG path on that side:

| Canonical key | Anterior | Posterior |
|---|---|---|
| `adductors` (inner thigh) | unmapped | n/a |
| `hip-abductors` (TFL / glute med) | n/a | unmapped |
| `neck` | unmapped | unmapped |
| `triceps` | **unmapped** | mapped |

`triceps` was added to the anterior allowlist after the §3 build verified that workout-cool's anterior body has no `triceps` paths (anatomically reasonable — most triceps mass is hidden from the front by biceps and the lateral arm silhouette). The legend remains clickable on the front tab via `MUSCLES_BY_SIDE.front`. Recorded in [`EXECUTION_LOG.md`](EXECUTION_LOG.md).

Anterior/posterior duplication (e.g. trapezius front vs back-deltoids back) is handled by giving anterior/posterior versions distinct paths but the same `data-canonical-muscles` value, exactly as our existing SVG does.

A test asserts every key in `MUSCLES_BY_SIDE` is either represented by at least one path in the new SVGs (anywhere in any region's `data-canonical-muscles` list) OR is listed in the allowlist above (see §3.7).

### 3.4 SVG reload across view modes

The current [static/js/modules/muscle-selector.js:796-809](../../static/js/modules/muscle-selector.js#L796-L809) `switchViewMode()` only re-renders the legend; it does **not** reload SVG assets. With two art sources, switching Simple↔Advanced must:

1. Unload the active SVG `<svg>` element.
2. Load the variant for the new mode (`workoutcool` for Simple, `react-body-highlighter` for Advanced).
3. Re-bind hover/click handlers via existing `MuscleSelector` machinery.
4. Preserve current selection state across the swap (selected muscle keys carry over; rendering re-derives from state).

This is the highest-risk part of §3 because it changes load-time behavior; it gets a dedicated browser regression test (§3.7).

### 3.4.1 Multi-key region state rules

**Critical implementation invariant:** [`MuscleSelector.selectedMuscles`](../../static/js/modules/muscle-selector.js#L286) stores **advanced child keys**, not simple keys. The current `toggleMuscle()` ([muscle-selector.js:554-580](../../static/js/modules/muscle-selector.js#L554-L580)) handles a single simple key by expanding it through `SIMPLE_TO_ADVANCED_MAP` ([muscle-selector.js:73-98](../../static/js/modules/muscle-selector.js#L73-L98)) and adding/removing all children. For a multi-key SVG region (e.g. `BACK`), the same expansion must happen across **all** simple keys in `data-canonical-muscles` before any `selectedMuscles.has` / `.add` / `.delete`.

For workout.cool `BACK` (`data-canonical-muscles="lats,upper-back,lowerback"`), the flattened advanced children set is:

```
['lats']                                                  ← from 'lats'
+ ['rhomboids', 'teres-major', 'teres-minor']             ← from 'upper-back'
+ ['erector-spinae']                                      ← from 'lowerback'
= ['lats', 'rhomboids', 'teres-major', 'teres-minor', 'erector-spinae']  (5 advanced keys)
```

Region state is derived from the union:

| Region condition (over flattened advanced children) | Visual state | Click effect | Hover effect |
|---|---|---|---|
| **All** advanced children present in `selectedMuscles` | `region.classList.add('selected')` (full fill) | Click toggles **all** advanced children off | Highlights every legend item whose key is in the flattened set |
| **Some** advanced children present (1 to N-1 of N) | `region.classList.add('partial')` (intermediate fill) | Click adds the missing children (promote to fully selected) | Same hover behavior as above; selected children are styled distinctly |
| **No** advanced children present | Default unselected | Click adds **all** advanced children to `selectedMuscles` | Same hover behavior |

Click handler pseudocode (mirrors the existing parent-key path inside `toggleMuscle()`):

```js
// e.currentTarget is the .muscle-region element
const region = e.currentTarget;
const simpleKeys = region.dataset.canonicalMuscles.split(',');

// CRITICAL: selectedMuscles stores advanced children, not simple keys.
// Flatten through SIMPLE_TO_ADVANCED_MAP before any has/add/delete.
const advancedKeys = simpleKeys.flatMap(k => SIMPLE_TO_ADVANCED_MAP[k] || [k]);

const allSelected = advancedKeys.every(k => this.selectedMuscles.has(k));
if (allSelected) {
  advancedKeys.forEach(k => this.selectedMuscles.delete(k));
} else {
  advancedKeys.forEach(k => this.selectedMuscles.add(k));
}
this.updateAllRegionStates();
```

State-derivation pseudocode (used by `updateAllRegionStates()` for each region):

```js
function regionVisualState(region, selectedMuscles) {
  const simpleKeys = region.dataset.canonicalMuscles.split(',');
  const advancedKeys = simpleKeys.flatMap(k => SIMPLE_TO_ADVANCED_MAP[k] || [k]);
  const hits = advancedKeys.filter(k => selectedMuscles.has(k)).length;
  if (hits === 0) return 'unselected';
  if (hits === advancedKeys.length) return 'selected';
  return 'partial';
}
```

The cascade matches the existing parent-key behavior at [muscle-selector.js:561-569](../../static/js/modules/muscle-selector.js#L561-L569). The `partial` state is essential: in Advanced mode the user can select individual children (e.g. only `rhomboids`), then return to Simple mode where `BACK` would otherwise look fully empty without `partial` styling.

***claude r4*** Codex flagged that the prior r3 pseudocode checked simple keys directly against `selectedMuscles`, which would never match because `selectedMuscles` only contains advanced children. The fix is the `flatMap` through `SIMPLE_TO_ADVANCED_MAP` before any membership test. Function names also corrected from invented `togglePicked()` / `refreshSelectionVisuals()` to the real symbols `toggleMuscle()` ([line 554](../../static/js/modules/muscle-selector.js#L554)) and `updateAllRegionStates()` ([line 617](../../static/js/modules/muscle-selector.js#L617)). The flattened-set example for `BACK` is shown explicitly so implementers can verify their logic against five advanced children, not three simple keys.

### 3.5 Files touched (workout-plan only)

**Add:**
- `static/vendor/workout-cool/body_anterior.svg`
- `static/vendor/workout-cool/body_posterior.svg`
- `static/vendor/workout-cool/LICENSE` (copy of workout-cool's MIT)
- `static/vendor/workout-cool/NOTICE.md` (attribution: "Body anatomy SVG art © Mathias Bradiceanu, used under MIT — github.com/Snouzy/workout-cool")
- `static/vendor/workout-cool/VERSION` (pinned upstream commit SHA + import date)
- `docs/workout_cool_integration/PLANNING.md` (this file)
- `docs/workout_cool_integration/EXECUTION_LOG.md` (created when work starts)

**Modify (preferred path — keep `bodymap-svg.js` untouched):**
- `static/js/modules/muscle-selector.js` — add a local `SVG_PATHS` table keyed by `mode` × `side` mapping to absolute `/static/vendor/...` URLs, e.g.:
  ```js
  const SVG_PATHS = {
    simple: {
      anterior: '/static/vendor/workout-cool/body_anterior.svg',
      posterior: '/static/vendor/workout-cool/body_posterior.svg',
    },
    advanced: {
      anterior: '/static/vendor/react-body-highlighter/body_anterior.svg',
      posterior: '/static/vendor/react-body-highlighter/body_posterior.svg',
    },
  };
  function getSvgPathForMode(mode, side) { return SVG_PATHS[mode][side]; }
  ```
  Update `switchViewMode()` to call `getSvgPathForMode()` and reload the SVG (per §3.4). Add multi-key region click/hover handling per §3.4.1 — every entry point that touches `selectedMuscles` must first expand `data-canonical-muscles` simple keys through `SIMPLE_TO_ADVANCED_MAP`. **No update to `VENDOR_SLUG_TO_CANONICAL` is needed** — the new SVGs ship pre-canonicalized `data-canonical-muscles` values per §3.2 step 3, so there are no upstream slugs to canonicalize at runtime. Update that map only if any region in the new SVGs still ships an upstream slug in `data-muscle`.
- `static/css/pages-workout-plan.css` — add styling for the new SVG (workout.cool uses Tailwind tokens we don't have; convert to our existing `--muscle-*` CSS custom properties). Add a `.muscle-region.partial` style for multi-key partial-selection state (§3.4.1).
- `docs/muscle_selector.md` — note the Simple-view art change, the new vendor file paths, and the `data-canonical-muscles` attribute convention.
- `docs/muscle_selector_vendor.md` — add a workout-cool section with attribution.

**Avoid touching unless §3.6 is also activated:**
- `static/js/modules/bodymap-svg.js` — currently consumed by Profile coverage ([user-profile.js:8-9,789](../../static/js/modules/user-profile.js#L8-L9) imports `loadBodymapSvg()`). Adding a `variant` parameter changes a shared API and risks regressing Profile coverage even though Profile is deferred. The `muscle-selector.js` script does not currently depend on `loadBodymapSvg()`, so it can fetch the workout.cool variant locally without touching this module. Only escalate to a shared loader (and add a Profile regression test) if the local approach proves insufficient.

**Out of scope for first pass (deferred to §3.6):**
- `static/js/modules/user-profile.js` — Profile coverage bodymap.
- `static/css/pages-user-profile.css` — Profile bodymap state styling.

***claude r4*** Codex flagged that r3's bullet implied a `VENDOR_SLUG_TO_CANONICAL` update was needed and was vague about whether `muscle-selector.js` shared `loadBodymapSvg()` with Profile. r4 commits to the local `SVG_PATHS` / `getSvgPathForMode()` design with a code stub so the implementer doesn't have to invent the shape, and explicitly removes the `VENDOR_SLUG_TO_CANONICAL` mention since the new SVGs are pre-canonicalized. The `bodymap-svg.js` "avoid touching" rule is reinforced with the supporting fact that `muscle-selector.js` does not currently import `loadBodymapSvg()` (so there is no shared-loader pressure here).

### 3.6 Profile coverage bodymap — deferred

The `/user_profile` page bodymap is a **coverage estimator**, not a Simple/Advanced selector. Its current implementation imports `BODYMAP_COVERAGE_MUSCLES` and `annotateBodymapPolygons()` ([static/js/modules/user-profile.js:1-5,797](../../static/js/modules/user-profile.js#L1-L5)) and renders state classes (`measured`, `cross-muscle`, `cold-start`, `not-assessed`) styled by `static/css/pages-user-profile.css`. There is no view-mode toggle.

For this integration:

- **Phase 1 (this plan)**: Profile bodymap stays on `react-body-highlighter`. No changes.
- **Phase 2 (future, separate plan)**: If Profile coverage should also adopt workout.cool art, write a dedicated mapping for the four coverage states, add tests for `state-measured` / `state-cross-muscle` / `state-cold-start` / `state-not-assessed` rendering, and verify click-to-lift popover behavior end-to-end. Do **not** reuse the workout-plan selector mapping there without proving these flows.

### 3.7 Test impact

- New `tests/test_muscle_selector_mapping.py` (or extend if it already exists) — assert workout.cool selector slug coverage:
  - Every workout.cool key in §3.3 resolves to at least one path with the corresponding `data-canonical-muscles` value in the new SVGs (parse SVG, extract attribute, assert coverage).
  - Every simple key in `MUSCLES_BY_SIDE` is either present in some region's `data-canonical-muscles` list OR present in the §3.3 unmapped-by-art allowlist.
  - Multi-key regions: the `BACK` region's `data-canonical-muscles` parses to exactly `['lats', 'upper-back', 'lowerback']`.
- New unit test for multi-key state derivation (`regionVisualState` per §3.4.1) — uses **expanded advanced children**, not simple-key counts, because `selectedMuscles` stores advanced keys. For `BACK` whose flattened set is `['lats', 'rhomboids', 'teres-major', 'teres-minor', 'erector-spinae']`:

  | Selected `selectedMuscles` content | Expected `regionVisualState('BACK')` |
  |---|---|
  | `{}` | `unselected` |
  | `{'rhomboids'}` | `partial` ← regression: only one child of `upper-back` |
  | `{'erector-spinae'}` | `partial` ← regression: only the `lowerback` child |
  | `{'lats'}` | `partial` |
  | `{'lats', 'rhomboids', 'teres-major', 'teres-minor'}` | `partial` (4 of 5) |
  | `{'lats', 'rhomboids', 'teres-major', 'teres-minor', 'erector-spinae'}` | `selected` |

  The `rhomboids`-only and `erector-spinae`-only cases specifically guard against an implementer forgetting the `SIMPLE_TO_ADVANCED_MAP` flattening — without it, those children would never count toward BACK's `partial` state.
- New unit test for the click handler: clicking `BACK` when no children are selected adds all five advanced children to `selectedMuscles`; clicking again removes all five.
- **Do not** modify [tests/test_profile_estimator.py:1222](../../tests/test_profile_estimator.py#L1222) `test_bodymap_canonical_in_sync`. That test guards Profile coverage `COVERAGE_MUSCLE_CHAIN` ↔ `BODYMAP_MUSCLE_KEYS` drift and is unrelated to selector SVG slugs. Selector coverage belongs in `tests/test_muscle_selector_mapping.py`.
- New browser regression for mode switching: select a Simple workout.cool region → switch to Advanced → assert the old SVG variant loads and child selections remain selected → switch back to Simple → assert workout.cool SVG reloads and selection state is preserved.
- New browser regression for multi-key BACK: select an individual `rhomboids` checkbox in Advanced → switch to Simple → assert `BACK` region renders with `.muscle-region.partial`; click `BACK` → assert all five children are now in `selectedMuscles` and the region renders `selected`.
- E2E `e2e/workout-plan.spec.ts` and any user-profile E2E that opens the muscle selector — re-run as regression. Existing assertions should still pass since muscle keys and selection behavior are unchanged. Visual snapshots, if any, will need an intentional refresh.
- Targeted verification commands:
  ```bash
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-pytest.ps1 tests/test_muscle_selector_mapping.py tests/test_user_profile_routes.py tests/test_profile_estimator.py
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/workout-plan.spec.ts e2e/visual.spec.ts
  ```
  After targeted runs pass and visual diffs are intentionally accepted, run the full gate. If `/verify-suite` skill is available in the harness, invoke it; otherwise run the equivalent commands directly:
  ```bash
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-pytest.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1
  ```

***claude r4*** Test wording rewritten to use the flattened advanced-children set (5 keys for `BACK`), not the 3 simple keys. The two regression rows (`{rhomboids}` → `partial` and `{erector-spinae}` → `partial`) are the precise cases codex called out as easy to break if the `SIMPLE_TO_ADVANCED_MAP` expansion is forgotten — making them explicit table rows means the test will fail loudly on that mistake. Also added the cross-mode browser regression so the partial-state cascade is exercised end-to-end.

## 4. Exercise Icons — free-exercise-db (Decision: bulk-vendor)

### 4.1 Source

[yuhonas/free-exercise-db](https://github.com/yuhonas/free-exercise-db) — Unlicense (public domain). ~800 exercises, JSON metadata + per-exercise GIF/PNG images. Total bundle ~21 MB.

### 4.2 Vendoring strategy

- Copy `dist/exercises.json` and `exercises/` image folder into `static/vendor/free-exercise-db/`.
- Pin to a specific commit; record the commit SHA in `static/vendor/free-exercise-db/VERSION`.
- No runtime fetching from GitHub.
- Smoke-test the bundled (PyInstaller) app path. `Hypertrophy-Toolbox.spec` already includes the `static` folder, so the assets package, but adding ~21 MB of vendor media is a deliberate size bump that needs verification.

### 4.3 Mapping to our exercise table

free-exercise-db's exercise IDs do not match ours, and our `exercises` table has no numeric id — the catalogue is keyed by `exercise_name TEXT PRIMARY KEY`. The mapping joins by `exercise_name COLLATE NOCASE`.

Catalogue size: **1,897** local exercises vs **~800** upstream entries. Full-catalogue coverage is mathematically capped well below 70%. See §4.7 for the redefined coverage target.

Each upstream entry exposes an `images: [...]` array (typically `["<id>/0.jpg", "<id>/1.jpg"]`). The first element is the canonical reference image; we do **not** assume a fixed `0.jpg` extension. Image path resolution reads `images[0]` from the upstream JSON.

The new column is named **`media_path`** (not `media_id`) because its value is the relative path under `static/vendor/free-exercise-db/exercises/` (e.g. `Squat_Barbell/0.jpg`), not an opaque identifier. The renderer concatenates this with the vendor base directory; no extension guessing.

**Path validation rules.** `media_path` is a security-sensitive value (it interpolates into a URL); the apply script enforces these before any DB write, and the frontend re-validates before rendering:

- Non-empty for any row where `review_status IN ('confirmed', 'manual')`.
- No leading `/` or `\` (must be a relative path).
- No `..` segments anywhere in the path.
- No backslashes anywhere (forward slashes only).
- Extension must match `^\.(jpg|jpeg|png|gif|webp)$` (case-insensitive).
- The resolved file must exist under `static/vendor/free-exercise-db/exercises/`.

Mapping pipeline:

1. Build a Python script `scripts/map_free_exercise_db.py` that:
   - Reads `static/vendor/free-exercise-db/exercises.json`.
   - Reads our `exercises` table.
   - For each of our exercises, computes a fuzzy match score against free-exercise-db entries using `(exercise_name, equipment, primary_muscle_group)` similarity.
   - Writes a 5-column CSV: `exercise_name, suggested_fed_id, suggested_image_path, score, review_status`. `review_status ∈ {auto, confirmed, rejected, manual}`. `suggested_image_path` is the verbatim `images[0]` value from upstream JSON (e.g. `"<id>/0.jpg"`); review can override it if a different frame is preferred.
2. Human review of CSV (manual edits for low-confidence rows; flip `review_status` accordingly; optionally override `suggested_image_path`).
3. Apply script `scripts/apply_free_exercise_db_mapping.py` reads the reviewed CSV and:
   - Adds nullable column `media_path TEXT` to `exercises` (DB migration via `utils/db_initializer.py`).
   - Validates that every reviewed row references an existing `exercises.exercise_name` (case-insensitive). Reports missing/renamed catalogue entries and **fails loudly without partially applying** if any are missing.
   - Validates every `suggested_image_path` against the path-shape rules above and confirms the resolved file exists.
   - Populates `media_path` only for rows where `review_status IN ('confirmed', 'manual')`.
4. Unmatched rows: `media_path = NULL` → frontend renders no thumbnail (matches current visual behavior; see §4.4).

***claude r4*** Codex flagged that `media_id` was a misleading name once the column stored a relative path. Renamed to `media_path` so the column name reflects content. Also added explicit path-shape validation (no leading slash, no `..`, no backslashes, extension allowlist) — these checks are independently useful even setting aside the rename, because `media_path` interpolates into a frontend URL and any value in it should be considered untrusted until proven safe. `youtube_video_id` keeps its name since it really is an opaque ID.

### 4.4 Frontend rendering

The current workout-plan rows do **not** render an `<img>`. [templates/workout_plan.html:353-355](../../templates/workout_plan.html#L353-L355) is an empty `<tbody>`; [static/js/modules/workout-plan.js:1554-1567](../../static/js/modules/workout-plan.js#L1554-L1567) renders the Exercise cell as `name + superset badge + Swap button`. Workout-log similarly server-renders `{{ log.exercise }}` ([templates/workout_log.html:95](../../templates/workout_log.html#L95)) with no image.

**Design**: thumbnail goes **inside the existing Exercise cell**, prepended to the name, as a fixed-size square. **Not a new column** — the table already has many narrow columns plus advanced/simple width overrides; a new column would break the responsive design.

- Add a frontend helper `resolveExerciseMediaSrc(mediaPath)` (in `static/js/modules/exercise-helpers.js` or co-located with the row renderer) that:
  - Re-validates `mediaPath` against the §4.3 path-shape rules before constructing a URL (defense in depth — DB rows can still be edited out-of-band).
  - Returns `static/vendor/free-exercise-db/exercises/{encodedPath}` when valid, encoding each path segment with `encodeURIComponent` and rejoining with `/`.
  - Returns `null` for NULL or invalid `mediaPath` (caller renders no `<img>` — keeping current visual behavior).
- Image attributes: `loading="lazy"`, fixed CSS `aspect-ratio: 1 / 1`, stable `width`/`height`, `alt="<exercise name> reference"` (escaped — see escaping requirement below).

**Escaping requirement (pre-existing gap surfaced by this work):** the current row renderer at [workout-plan.js:643,1542](../../static/js/modules/workout-plan.js#L643) uses `row.innerHTML = \`…\`` template literals that interpolate raw values such as `exercise.exercise`, `routine`, and metadata fields without HTML-escaping. Adding `media_path` and `youtube_video_id` (which are reviewed/allowlisted, but live in user-editable rows) makes the gap more visible, and the new `alt` attribute carries the exercise name straight from the DB. Two acceptable resolutions:

- **Option A (preferred):** introduce a small `escapeHtml(s)` helper (e.g. in `static/js/modules/dom-utils.js` if it exists, otherwise add it next to `resolveExerciseMediaSrc`) and route every interpolated value in the row template through it. Keeps the template-literal renderer.
- **Option B:** switch the Exercise-cell media + name + action cluster to DOM-node creation (`document.createElement` + `textContent`), keeping the rest of the row on `innerHTML`. Reduces blast radius but introduces two rendering styles in one function.

Either way, the new `alt`/`src` work must not be the only escape-safe spot in an otherwise unsafe row.

### 4.5 Files touched

**Add:**
- `static/vendor/free-exercise-db/exercises.json` (vendored from upstream).
- `static/vendor/free-exercise-db/exercises/<id>/0.jpg` etc. (vendored image set).
- `static/vendor/free-exercise-db/LICENSE` (Unlicense text).
- `static/vendor/free-exercise-db/VERSION` (pinned upstream commit SHA + import date).
- `scripts/map_free_exercise_db.py` — produces `data/free_exercise_db_mapping.csv` for human review.
- `scripts/apply_free_exercise_db_mapping.py` — applies reviewed CSV into `media_path` (idempotent, all-or-nothing).
- `data/free_exercise_db_mapping.csv` — the reviewed mapping (committed so the apply step is reproducible).
- `tests/test_free_exercise_db_mapping.py` — see §4.6.

**Modify:**
- `utils/db_initializer.py` — add `media_path TEXT` (nullable) to `CREATE TABLE IF NOT EXISTS exercises` AND a guarded migration for existing DBs using its local `PRAGMA table_info(exercises)` pattern. Do not import `column_exists()` from `routes/workout_plan.py` into lower-level DB code. Fresh DBs and migrated DBs must converge on the same shape.
- `routes/workout_plan.py` — `get_workout_plan()` ([routes/workout_plan.py:237-238](../../routes/workout_plan.py#L237)) is the actual source of workout-plan row JSON; its `SELECT` must include `media_path` (and §5's `youtube_video_id`). This is a route contract change.
- `routes/workout_log.py` — `get_workout_logs()` ([routes/workout_log.py:169](../../routes/workout_log.py#L169)) has its own query joining `user_selection` and currently does not surface catalogue metadata; extend its `SELECT` (or add a `LEFT JOIN exercises e ON e.exercise_name = ... COLLATE NOCASE`) to include `media_path` and `youtube_video_id` so the log API matches the page render.
- `utils/workout_log.py` — page-render path: add a `LEFT JOIN exercises e ON e.exercise_name = workout_log.exercise COLLATE NOCASE` so server-rendered log rows carry catalogue metadata to Jinja.
- `templates/workout_plan.html`, `templates/workout_log.html` — add the thumbnail inside the Exercise cell when `media_path` is present. For workout_log.html, server-rendered template; escape exercise name in `alt`.
- `static/js/modules/workout-plan.js` and any other module rendering exercise rows — add `resolveExerciseMediaSrc()`, route `alt`/name/routine/metadata through `escapeHtml()` (per §4.4 Option A).
- `static/css/pages-workout-plan.css`, `pages-workout-log.css` — sizing/aspect-ratio rules for the new image set, plus advanced-mode and dark-mode overrides.
- `Hypertrophy-Toolbox.spec` — confirm `static/vendor/free-exercise-db/` ships in the bundle (likely already covered by the existing `static` rule); smoke-test bundle size.
- `docs/CHANGELOG.md` — note the schema delta, image source, and bundle size change.
- `CLAUDE.md` §5 verified test counts — update after this lands.

**Removed from prior draft:** `utils/database.py` — there is no central frontend-feeding `SELECT` on `exercises` in that file; the workout-plan and workout-log JSON shapes are built by route-level SQL (see two route modify entries above). Add `utils/database.py` back only if a real touchpoint is found during implementation.

### 4.6 Test impact

- New `tests/test_free_exercise_db_mapping.py`:
  - Every non-NULL `media_path` in the DB satisfies the §4.3 path-shape rules (non-empty, no leading slash, no `..`, no backslashes, extension allowlist).
  - Every non-NULL `media_path` resolves to a real file under `static/vendor/free-exercise-db/exercises/`.
  - CSV rows are unique per `exercise_name` (case-insensitive).
  - Every CSV `exercise_name` references an existing `exercises.exercise_name`.
  - Every CSV `suggested_image_path` matches a file under `static/vendor/free-exercise-db/exercises/`.
- New unit tests for the path-shape validator (used by both the apply script and `resolveExerciseMediaSrc`):
  - Accepts: `Squat_Barbell/0.jpg`, `Some_Exercise/2.png`, `dir/sub/img.webp`.
  - Rejects: empty string, `/abs/path/0.jpg`, `\\abs\\path\\0.jpg`, `../../../etc/passwd`, `path/with/..//evil.jpg`, `dir\\img.jpg`, `dir/img.exe`, `dir/img` (no extension), `dir/img.JPGX`.
- New `tests/test_db_initializer_media_path.py` (or extend existing) — fresh-DB initialization adds the column; re-running on an existing DB is a no-op.
- Update `tests/conftest.py` if the seed exercise set needs a `media_path` value for any fixture exercise. Confirm `exercise_factory()` still works without specifying `media_path`.
- Backend contract: `tests/test_workout_plan_routes.py` (or equivalent) — `/get_workout_plan` returns rows when `media_path` is NULL; export-to-log still works for exercises with and without media.
- Backend contract: `tests/test_workout_log_routes.py` (or equivalent) — `/get_workout_logs` includes `media_path` in the JSON shape.
- New unit test for `escapeHtml()` (Option A) covering ampersand, less-than, greater-than, double-quote, single-quote. Use a synthetic name `Coach's <Test> Press` so the input definitely exercises every escape rule. (The catalogue does not contain a single exercise name with both an apostrophe and angle brackets — `Bulgarian Split Squat` for example has neither — so a synthetic input is necessary to assert the helper is correct.)
- E2E `e2e/workout-plan.spec.ts`:
  - An exercise row with mapped media renders an `<img>` whose `src` matches `/static/vendor/free-exercise-db/...`.
  - An exercise row with NULL `media_path` renders without an `<img>` and without console errors.
  - An exercise whose name contains HTML-special characters renders without raw markup leaking into the cell.
- Visual / accessibility regression: add baselines or snapshot comparisons for desktop / tablet / mobile, light / dark, simple / advanced table modes, and rows containing long exercise names plus thumbnail + superset badge + Swap button.
- Verification gate (run before marking done):
  ```bash
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-pytest.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1
  ```
  Or invoke the `/verify-suite` skill if available.

***claude r4*** Codex correctly noted that `Bulgarian Split Squat` doesn't have an apostrophe — using it for an `escapeHtml()` test would silently skip the quote-escape branch. Switched to the synthetic `Coach's <Test> Press` (apostrophe + angle brackets + space + alphanumerics) so every escape rule is exercised. Also added explicit accept/reject lists for the path-shape validator so the test surface matches the §4.3 rules row-for-row.

### 4.7 Coverage target

The 70% catalogue-wide floor in the prior draft is mathematically unreachable (1,897 local vs ~800 upstream). Redefined acceptance:

- **Primary**: zero regressions when coverage is low — NULL `media_path` rows render exactly like today (no `<img>`, no console errors).
- **Secondary**: ≥70% of a deliberately scoped "common strength exercises" subset, defined as: the top-N exercises by appearance in `user_selection` and `workout_log` history, plus all default starter-plan exercises, where N is chosen so the subset comprises ~150–250 exercises. The exact subset and N are decided when §4.3 step 1 produces its first coverage report.
- **Tertiary**: at least 50 reviewed mappings shipped in the initial release; the rest fall back to NULL.

### 4.8 Open questions

- **Animated GIFs vs static frames**: free-exercise-db ships GIFs. Page weight matters. Default to first-frame PNG, lazy-load animated on hover/click. (Implementation detail — defer until building.)
- **DB-side or filesystem-side resolution?** `media_path` in DB is canonical (full relative path; see §4.3). Frontend builds the URL by concatenating with the vendor base directory and re-validating shape. No need for a routes-level proxy.

## 5. YouTube Reference (Decision: Pattern A — single button, modal)

### 5.1 UX

Pattern A is preferred over Pattern B (two icons) to avoid table clutter. The workout-plan row already carries: superset checkbox, drag handle, Routine, Exercise, muscle columns, sets/reps/RIR/RPE/weight, execution-style, grips/stabilizers/synergists, Swap, Remove. Adding a second icon column is not viable on mobile.

- Add a single play-icon button **inside the existing Exercise cell action cluster**, next to the Swap button.
- Click → opens a Bootstrap modal with the YouTube iframe player.
- Modal includes a "Watch on YouTube ↗" link that opens the video externally in a new tab (`target="_blank"`, `rel="noopener noreferrer"`).
- If the iframe fails to load (uploader disabled embedding), modal degrades to just the external link.
- For exercises with NULL `youtube_video_id`, the same button opens a "Search YouTube" modal whose CTA is `https://www.youtube.com/results?search_query=<encoded exercise name>` (option-3 hybrid; see §5.4).

**Modal lifecycle:**

- Set the iframe `src` only when opening; remove/blank it on close so playback stops and no audio plays invisibly.
- `loading="lazy"`, `allowfullscreen`, descriptive `title="<exercise name> reference video"`.
- Keep Bootstrap defaults for focus trap / ESC / backdrop click.
- On close, return keyboard focus to the triggering button.
- Reopening for a different exercise swaps the URL cleanly (no leaked state).

### 5.2 Alternative (Pattern B — rejected)

Two icons per row: a YouTube logo (external link) and a play icon (modal embed). Rejected for mobile clutter; documented for completeness only.

### 5.3 Schema

- Add nullable column `youtube_video_id TEXT` to `exercises` (the 11-char video ID, not a full URL — keeps URL construction in the frontend so we can swap embed/external/short-link forms freely).
- DB migration via `utils/db_initializer.py` (same pattern as §4.5: add to `CREATE TABLE` AND guarded `ALTER` for existing DBs).
- Curated CSV references `exercise_name`, never a numeric id.

### 5.4 Where the video IDs come from

free-exercise-db does not include YouTube IDs. Three options:

1. **Manual curation**: admin populates `youtube_video_id` for the most common N exercises; rest stay NULL. Simplest, lowest legal exposure.
2. **Search-time fallback**: when video ID is NULL, render the play button as a "Search YouTube" link with the exercise name pre-filled. No stored IDs at all.
3. **Hybrid**: (1) for top N exercises, (2) fallback for the long tail.

**Decision: option 3 (hybrid)** — solves coverage without committing to populating all ~1,897 rows.

### 5.5 Frontend — `/workout_log` is in scope

The play-icon button appears on **both** `/workout_plan` and `/workout_log`. Reviewing past sessions is a primary use case where a quick form-check video is valuable; making the button plan-only would create asymmetric behavior across two pages that share the same exercise dataset.

- New component `static/js/modules/exercise-video-modal.js` — exports `openExerciseVideoModal(videoId, exerciseName)` and `openYouTubeSearch(exerciseName)`. Imported and wired by both the workout-plan row renderer and the workout-log table.
- New CSS in `pages-workout-plan.css` AND `pages-workout-log.css` (the modal/iframe styles can live in `components.css` if both pages need an identical button surface; otherwise duplicate the small play-button block to keep page-scoped styles independent).
- New template partial at `templates/partials/exercise_video_modal.html` (the existing partials directory; there is no `templates/_partials/`). The partial is included once in `base.html` so a single modal serves both pages.

### 5.6 Compliance

- Use only the official iframe embed code from `https://www.youtube.com/embed/<id>`.
- Do not download, cache, or re-host video data or thumbnails outside what `https://img.youtube.com/vi/<id>/...` provides.
- "Watch on YouTube" link present in every embed surface — meets YouTube ToS embed conditions.

### 5.7 Files touched

**Add:**
- `static/js/modules/exercise-video-modal.js`.
- `templates/partials/exercise_video_modal.html`.
- `data/youtube_curated_top_n.csv` — committed manual mapping `exercise_name, youtube_video_id` for the curated top-N (target ~50 most-used exercises).
- `scripts/apply_youtube_curated.py` — one-shot importer reading the CSV and writing `youtube_video_id` into `exercises` (idempotent, all-or-nothing). Validates: every `exercise_name` exists in `exercises` (case-insensitive); every `youtube_video_id` matches `^[A-Za-z0-9_-]{11}$`; no duplicate names; no blank IDs. Fails loudly on any violation.
- `tests/test_youtube_video_id.py` — see §5.8.

**Modify:**
- `utils/db_initializer.py` — add `youtube_video_id TEXT` (nullable) to `CREATE TABLE IF NOT EXISTS exercises` AND a guarded migration for existing DBs (same pattern as `media_path`).
- `routes/workout_plan.py` — `get_workout_plan()` is the actual source of workout-plan row JSON; its `SELECT` must include `youtube_video_id`. Route contract change.
- `routes/workout_log.py` — `get_workout_logs()` must also include `youtube_video_id` (per §5.5 in-scope decision).
- `utils/workout_log.py` — page-render path: `LEFT JOIN exercises` so server-rendered log rows carry `youtube_video_id`.
- `templates/workout_plan.html`, `templates/workout_log.html` — add the play-icon button inside the Exercise-cell action cluster per row. Include the `exercise_video_modal.html` partial (or include it once in `base.html`).
- `templates/base.html` — include the shared modal partial once if both pages need it (alternative to including per-page).
- `static/js/modules/workout-plan.js` and the workout-log JS module — wire the icon click(s) to `exercise-video-modal.js`. Route the button's `aria-label` and any inline text through `escapeHtml()` per the §4.4 escaping rule.
- `static/css/pages-workout-plan.css`, `pages-workout-log.css` — modal styling, iframe responsive aspect-ratio (16:9), play-icon button styling.
- `static/css/components.css` — only if the play-icon button becomes a generic component used elsewhere.
- `docs/CHANGELOG.md` — note the schema delta and ToS-compliance posture.
- `CLAUDE.md` §5 verified test counts — update after landing.

**Removed from prior draft:** `utils/database.py` and any reference to "exercise-row serializer" — same reasoning as §4.5; the JSON shape is built by route SQL.

### 5.8 Test impact

- New `tests/test_youtube_video_id.py`:
  - Every non-NULL `youtube_video_id` is exactly 11 chars and matches `^[A-Za-z0-9_-]{11}$`.
  - The `data/youtube_curated_top_n.csv` parses cleanly and references real `exercise_name` values.
  - `apply_youtube_curated.py` is idempotent: running twice produces no DB delta after the first run.
  - Apply script rejects duplicates / unknown names / invalid IDs / blank IDs without partially applying.
- Extend `tests/test_db_initializer_*` to assert the new column is added on fresh init and is a no-op on re-run.
- Backend contract test for `/get_workout_plan`: response JSON includes `youtube_video_id` (NULL when unset).
- Backend contract test for `/get_workout_logs`: response JSON includes `youtube_video_id` (NULL when unset).
- E2E `e2e/workout-plan.spec.ts` AND `e2e/workout-log.spec.ts` (per §5.5 in-scope):
  - Click the play icon on an exercise that has a `youtube_video_id` → modal opens, iframe `src` starts with `https://www.youtube.com/embed/`, modal contains a "Watch on YouTube" link with `target="_blank"` and `rel="noopener noreferrer"`.
  - Click the play icon on an exercise with NULL `youtube_video_id` → modal opens with a "Search YouTube" CTA whose href is `https://www.youtube.com/results?search_query=<encoded exercise name>`.
  - Closing the modal clears the iframe `src` (no invisible playback).
  - Reopening for a different exercise swaps to the new video / search URL.
  - Keyboard focus returns to the triggering button on close.
  - Icon-only buttons have accessible names (`aria-label="Play reference video for <exercise name>"`).
- No new backend route is added — modal logic is pure frontend — so no new pytest route test is required *beyond* the `/get_workout_plan` and `/get_workout_logs` contract assertions above.
- Verification gate (run before marking done):
  ```bash
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-pytest.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1
  ```
  Or invoke the `/verify-suite` skill if available.

## 6. Order of execution

Risk-ordered sequence (revised):

1. **§3 workout-plan bodymap only** (no DB change, presentation-only). Proves the variant loader, multi-key region behavior with `SIMPLE_TO_ADVANCED_MAP` flattening, and SVG-reload regression.
2. **§5 YouTube modal** (one nullable column, frontend-heavy, both `/workout_plan` and `/workout_log`). Confirms the additive-nullable migration pattern, `escapeHtml()` rollout, and the route contract change pattern with a small data set.
3. **§4 free-exercise-db media** (one nullable column, large data work, both `/workout_plan` and `/workout_log`). Largest mapping/review effort; benefits from the migration and escaping patterns proven in §5.
4. **§3.6 Profile coverage bodymap** (deferred; future plan). Only after §3 has stable visual baselines.

## 7. Open questions to resolve before starting

1. §3.2 conversion: do we accept ~4 hours of mechanical TSX→SVG conversion, or look for a Figma/Inkscape export the maintainer may have published elsewhere? (Default: do the conversion.)
2. §4.4 escaping: Option A (`escapeHtml()` helper applied at every interpolation) or Option B (DOM-node creation for the Exercise cell)? (Default: Option A.)
3. §4.7: confirm "common strength exercises" subset definition — top-N by usage history + starter-plan defaults; N to be set by §4.3 first coverage report.
4. §3.6: confirm Profile coverage bodymap is out of scope for this integration. (Default: yes.)

## 8. License & attribution checklist

- [ ] `static/vendor/workout-cool/LICENSE` includes verbatim MIT text.
- [ ] `static/vendor/workout-cool/NOTICE.md` credits Mathias Bradiceanu and links workout-cool repo.
- [ ] `static/vendor/workout-cool/VERSION` records pinned upstream commit SHA + import date.
- [ ] `static/vendor/free-exercise-db/LICENSE` includes Unlicense text.
- [ ] `static/vendor/free-exercise-db/VERSION` records pinned upstream commit SHA + import date.
- [ ] `docs/muscle_selector_vendor.md` updated to mention both vendor sources.
- [ ] Repo `README.md` (if it has a Credits section) updated to acknowledge both projects.

## 9. Pre-Implementation Guardrails

Run through this checklist before writing any production code:

- [ ] All mapping CSVs use `exercise_name` as the catalogue key. No `our_id` / `exercise_id` / numeric-id references remain (the `exercises` table has no numeric id).
- [ ] Workout-plan row design at desktop / tablet / mobile is preserved before adding media or video controls. Specifically: superset checkbox, drag handle, Swap, inline-edit cells, execution-style controls, Remove button, and advanced/simple table column behavior all still work.
- [ ] Profile coverage bodymap is confirmed out of scope (or has its own mapping/test plan in a follow-up document).
- [ ] NULL `media_path` and NULL `youtube_video_id` render without visual or JS errors — confirmed in unit + E2E tests.
- [ ] DB migrations live in `utils/db_initializer.py` only; routes never add columns at runtime.
- [ ] `CREATE TABLE IF NOT EXISTS exercises` and the `ALTER TABLE` migration paths converge for fresh and existing DBs.
- [ ] `escapeHtml()` (or DOM-node alternative) lands before any new media/video interpolation in the row template; new and pre-existing interpolation points are both covered.
- [ ] Path-shape validation for `media_path` enforced on both write (apply script) and read (`resolveExerciseMediaSrc`).
- [ ] Multi-key SVG region handlers expand `data-canonical-muscles` simple keys through `SIMPLE_TO_ADVANCED_MAP` before any `selectedMuscles.has` / `.add` / `.delete`. Verified by the §3.7 `rhomboids`-only and `erector-spinae`-only `partial` regression cases.
- [ ] Route contract changes (`get_workout_plan`, `get_workout_logs`) have backend tests asserting the new fields appear in JSON, NULL when unset.
- [ ] `bodymap-svg.js` is **not** modified unless §3.6 is also activated, in which case Profile regression tests are added in the same PR.
- [ ] Targeted pytest + Playwright specs pass before any visual snapshot is refreshed; snapshots are updated intentionally, never via blanket `--update-snapshots`.
- [ ] Upstream commit SHAs and import dates are recorded for both vendor projects before assets land.

## 10. Effort estimate (rough)

| Section | Estimate |
|---|---|
| §3 Body map hybrid swap (workout-plan only, multi-key regions w/ `SIMPLE_TO_ADVANCED_MAP` flattening) | 1–1.5 days (TSX→SVG conversion + CSS port + SVG-reload refactor + multi-key region handling) |
| §5 YouTube modal + schema + curation of top-N (plan + log) | 0.5–1 day |
| §4 free-exercise-db vendoring + mapping + image rendering + path validation + escapeHtml rollout | 1.5–2.5 days (script + manual review + thumbnail UI + path validator + escaping pass + visual baselines) |
| **Total** | **3–5 days** of focused work |

§3.6 Profile coverage bodymap (deferred) is not included in the estimate.
