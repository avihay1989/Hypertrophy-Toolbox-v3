# workout-cool Integration — Execution Log

Tracks concrete work against `PLANNING.md`. Newest entry on top.

## 2026-05-14 — §4 checkpoint 6 (thumbnail UI + escapeHtml rollout)

**Scope**: PLANNING.md §4.4 Option A. Adds a shared `escapeHtml()` /
`resolveExerciseMediaSrc()` helper module, renders free-exercise-db
thumbnails in the workout-plan + workout-log Exercise cells, routes the
workout-plan row template-literal interpolations through `escapeHtml()`
so the new `alt`/`src` work isn't the only safe spot in an otherwise
unsafe row, and revalidates `media_path` at render time on the
server-rendered log page via a new `safe_media_path` Jinja filter.

### What landed

| File | Status | What landed |
|---|---|---|
| `static/js/modules/exercise-helpers.js` | new | Shared `escapeHtml(value)` + `isValidMediaPathShape(value)` + `resolveExerciseMediaSrc(mediaPath)`. Path-shape rules mirror `utils/media_path.py::is_valid_media_path_shape` verbatim (non-empty, no leading slash, no `\`, no `:`, no `..`/`.`/empty segments, jpg/jpeg/png/gif/webp extension allowlist). URL builder runs each path segment through `encodeURIComponent` and re-joins with `/`. |
| `static/js/modules/workout-plan.js` | modified | Imports the helpers. Row renderer at the §4.4 site (~line 1543) now `escapeHtml()`-wraps every interpolated value (exercise name, routine, muscle raw-value attrs, utility/movement/grips/stabilizers/synergists, sets/reps/RIR/RPE/weight, superset-group, aria-label). Pre-existing routine helpers `formatRoutineForDisplay` and `formatRoutineForTab` also escape their parsed parts. New thumbnail `<img>` prepended into the Exercise cell when `resolveExerciseMediaSrc(exercise.media_path)` returns a URL (else nothing rendered, matching pre-checkpoint behaviour). |
| `app.py` | modified | Registers a `safe_media_path` Jinja filter that returns the path iff `utils.media_path.is_valid_media_path_shape` accepts it, else `None`. Defense-in-depth: the apply script validates on write, but rows can be edited out-of-band and PLANNING §4.4 mandates revalidation at render time. |
| `tests/conftest.py` | modified | Registers the same `safe_media_path` filter on the test-only Flask app (which is built from scratch in the fixture rather than imported from `app.py`). |
| `templates/workout_log.html` | modified | Server-rendered thumbnail `<img class="exercise-thumbnail" …>` prepended into the Exercise-cell content block when `log.media_path | safe_media_path` returns a non-None value. Jinja auto-escaping handles the `alt`; `url_for('static', filename='vendor/free-exercise-db/exercises/' + safe_path)` builds the URL only after the filter accepts the path. |
| `static/css/components.css` | modified | `.exercise-cell .exercise-thumbnail` — 32×32, 1:1 aspect-ratio, rounded corners, `object-fit: cover`, neutral background. Dark-mode override adjusts the placeholder background. |
| `static/css/pages-workout-plan.css` | modified | Advanced view-mode override: thumbnail `align-self: flex-start` to coexist with the wrapped exercise-name + swap/play buttons. |
| `e2e/workout-plan.spec.ts` | modified | +4 tests in new `§4 free-exercise-db thumbnails` describe block, all **self-contained** (no live-DB dependency): they call `updateWorkoutPlanTable([mockRow])` via dynamic `import('/static/js/modules/workout-plan.js')` to render synthetic rows directly. Coverage: (a) `media_path: 'Band_Good_Morning/0.jpg'` → renders `<img.exercise-thumbnail>` with safe `src`, `alt`, `loading=lazy`, `width=height=32`; (b) `media_path: null` → no `<img>`, no console errors; (c) `exercise: "Coach's <Test> Press"` → `.exercise-name` textContent matches the literal angle brackets and zero injected `<Test>` elements (proves `escapeHtml` works end-to-end); (d) `page.evaluate()` drives `escapeHtml()` + `resolveExerciseMediaSrc()` across the full accept/reject matrix from §4.6 — synthetic `Coach's <Test> Press`, ampersand, null, valid jpg, upper-case `.PNG`, empty, abs path, `..`, backslash, `:`, `.exe`, no-extension, and `weird name/0.jpg` URL-encoding. |
| `tests/test_free_exercise_db_mapping.py` | modified | +2 unit tests in new `TestSafeMediaPathJinjaFilter` class covering accept (`Squat_Barbell/0.jpg`) and reject (None, empty, abs path, `..`, double slash, backslash, `:`, `.exe`, no-extension, int) for the `safe_media_path` filter. |

### Why E2E is mock-driven, not DB-driven

The earlier draft seeded the test by adding `Band Good Morning` through
the cascade UI and asserting the rendered thumbnail. That depends on
the live `data/database.db` carrying a populated `media_path` for the
row, which is true only after running `scripts/apply_free_exercise_db_mapping.py`
against the local DB — and `data/database.db` is intentionally not
committed, so a clean CI checkout would render no thumbnail and the
test would fail.

The revised tests render synthetic rows by calling
`updateWorkoutPlanTable([mockExercise])` directly via dynamic
`import('/static/js/modules/workout-plan.js')`. This exercises the same
template-literal renderer the production code uses, but the input is
controlled by the test rather than the DB. The route contract is
covered by `tests/test_free_exercise_db_mapping.py::TestRouteContracts`
(checkpoint 5).

### Why a server-side path-shape filter

PLANNING §4.4 explicitly mandates "Re-validates `mediaPath` against the
§4.3 path-shape rules before constructing a URL (defense in depth —
DB rows can still be edited out-of-band)" for the client-side helper.
The same logic applies to the server-rendered log template: even with
the apply-script invariant in place, anyone editing the SQLite file by
hand could bypass shape validation and inject `../../../etc/passwd` or
similar into the URL. The `safe_media_path` Jinja filter mirrors
`utils.media_path.is_valid_media_path_shape` and returns `None` for
any value that fails, causing the template to skip the `<img>` and
behave like the NULL case.

### Apply pass (informational; not part of the committed slice)

`scripts/apply_free_exercise_db_mapping.py` was run against the live
DB during checkpoint-6 development to confirm the route contract
populated the `media_path` field end-to-end:

```
OK: applied 108 row(s) to exercises.media_path (1789 ignored as auto/rejected).
```

`data/database.db` is **not** committed (excluded as a local/runtime
file per the standing rule). To apply mappings on any environment:

```bash
.venv/Scripts/python.exe scripts/apply_free_exercise_db_mapping.py
```

It's idempotent and all-or-nothing — safe to re-run.

### Verification

- `.venv/Scripts/python.exe -m pytest tests/ -q` → **1289 passed in 171.47s** on 2026-05-14 (was 1287; +2 `safe_media_path` filter tests).
- `npx playwright test e2e/workout-plan.spec.ts e2e/workout-log.spec.ts --project=chromium --reporter=line` → **56 passed in 1.6m** (was 52 baseline; +4 thumbnail/helper tests, all self-contained).

### Out of scope

- No further hardening of `transformMuscleDisplay()` / `renderExecutionStyleBadge()` — they operate on normalised enum-like DB columns. If future audit determines they need escaping too, that's a separate, narrowly scoped commit.
- No visual-regression baseline updates. PLANNING §4.6 calls for desktop / tablet / mobile, light / dark, simple / advanced snapshots; deferred to a dedicated visual-baseline pass.
- No backup-center / program-backup `escapeHtml()` consolidation — those modules already have local copies that work; converging them with the new shared helper is a tidy-up for later.

### Next sessions

1. PR the four-commit branch (checkpoints 3 → 6) once you're happy.
2. Visual-baseline pass per §4.6 (desktop / tablet / mobile + light / dark + simple / advanced) — fold into the next visual snapshot session.
3. Future curation passes can lift more rows from `auto` → `confirmed`/`manual` (the structural-equivalence rule under-confirms; manual-spot-check rule still applies).

## 2026-05-14 — §4 checkpoint 5 (DB whitespace trim + route SELECT updates) — shipped at `df27c8d`

**Scope**: PLANNING.md §4.5 — surface `media_path` in the page/JSON
contracts. Resolves the open trailing-whitespace catalogue row blocker by
adding a guarded startup trim repair (path (a) from checkpoint 4's
followups). No UI/template work; no `escapeHtml()` rollout — those remain
for checkpoint 6.

### What landed

| File | Status | What landed |
|---|---|---|
| `utils/db_initializer.py` | modified | New `_trim_exercise_name_whitespace` pass added to the startup sequence between `_normalize_muscle_group_values` and `_repair_known_exercise_metadata`. Trims `exercises.exercise_name` PK values that drift on whitespace and updates the FK and FK-less text references in `exercise_isolated_muscles`, `user_selection`, and `workout_log` in lockstep under `PRAGMA defer_foreign_keys = ON`. Skips trims that would collide with an existing case-insensitive name. Idempotent on a clean DB. |
| `routes/workout_plan.py` | modified | `/get_workout_plan` JSON now returns `e.media_path` alongside `e.youtube_video_id`. |
| `routes/workout_log.py` | modified | `/get_workout_logs` JSON now returns `e.media_path` alongside `e.youtube_video_id`. |
| `utils/workout_log.py` | modified | `get_workout_logs()` SQL adds `e.media_path` so the page render and export inherit the field without further wiring. |
| `tests/test_priority0_filters.py` | modified | +4 trim tests (`test_trim_repair_strips_trailing_space_from_exercise_name`, `test_trim_repair_cascades_to_fk_references`, `test_trim_repair_is_idempotent`, `test_trim_repair_skips_when_trimmed_collides`). Cascade test calls `_trim_exercise_name_whitespace` directly because TESTING=1 drops `user_selection` / `workout_log` inside `initialize_database`. |
| `tests/test_free_exercise_db_mapping.py` | modified | +4 route-contract tests in new `TestRouteContracts` class, mirroring the §5 `youtube_video_id` shape: `/get_workout_plan` and `/get_workout_logs` return `media_path: null` by default and propagate the curated value when set. |
| `data/free_exercise_db_mapping.csv` | modified | Removed the trailing whitespace from `Dumbbell Shoulder Internal Rotation` (CSV line 909) so the CSV's canonical form matches the trimmed DB row. |

### Trim repair design

The `exercises.exercise_name` PK schema lacks `ON UPDATE CASCADE`, so a
plain `UPDATE exercises SET exercise_name = TRIM(...)` would fail FK
checks for any row in `exercise_isolated_muscles` or `user_selection`
referencing the dirty name. The repair therefore wraps the parent +
child updates in a single transaction with `PRAGMA defer_foreign_keys =
ON` (FKs deferred until commit). On commit, all rows are consistent, so
FK enforcement passes. `workout_log.exercise` is updated in lockstep
even though it has no formal FK, to keep cross-table text references in
sync.

The function is defensive:

- Identifies dirty rows via `WHERE exercise_name != TRIM(exercise_name)`.
- Skips rows whose trimmed form would collide with an existing
  case-insensitive row (logs a warning instead of corrupting the
  catalogue).
- Idempotent — once trimmed, re-running the pass finds zero dirty rows.
- Each `execute_query` call uses `commit=False` so the surrounding
  transaction holds until the explicit `db.connection.commit()`.

### Live DB unblock

Before the trim landed, the unscoped `apply_free_exercise_db_mapping.py
--dry-run` failed on line 909:
```
FAILED: 1 row(s) reference unknown exercises:
  - line 909: exercise_name 'Dumbbell Shoulder Internal Rotation' not found in exercises table
```
After running `initialize_database(force=True)` against the live DB:
```
[INFO] Trimmed whitespace from 1 exercise_name row
```
The unscoped dry-run is now clean:
```
OK (dry-run): 108 row(s) would be applied (1789 ignored as auto/rejected).
```

### Verification

- `.venv/Scripts/python.exe -m pytest tests/test_priority0_filters.py -q`
  → **23 passed in 4.03s** (was 19; +4 trim tests).
- `.venv/Scripts/python.exe -m pytest tests/test_free_exercise_db_mapping.py -q`
  → **83 passed in 4.60s** (was 79; +4 route-contract tests).
- `.venv/Scripts/python.exe -m pytest tests/test_priority0_filters.py tests/test_workout_plan_routes.py tests/test_workout_log_routes.py tests/test_youtube_video_id.py -q`
  → **126 passed in 47.31s** (adjacent regression batch; no regressions).
- `.venv/Scripts/python.exe -m pytest tests/ -q`
  → **1287 passed in 158.99s** (full suite gate green).
- `.venv/Scripts/python.exe scripts/apply_free_exercise_db_mapping.py --dry-run`
  → **OK: 108 row(s) would be applied (1789 ignored as auto/rejected).**

### Out of scope for this checkpoint

- No template-side rendering of `<img>` thumbnails (checkpoint 6).
- No `resolveExerciseMediaSrc()` helper or `escapeHtml()` rollout in
  `static/js/modules/workout-plan.js` (checkpoint 6).
- `get_exercise_details` (modal endpoint) not extended — it doesn't
  currently expose `youtube_video_id` either, so the parallel keeps
  scope tight; can be added with the modal redesign if needed.

### Next sessions

1. Open checkpoint 6: thumbnail rendering in `templates/workout_plan.html`
   and `templates/workout_log.html`, plus the `escapeHtml()` rollout per
   §4.4 Option A.
2. Once thumbnails ship, run an apply pass (`scripts/apply_free_exercise_db_mapping.py`)
   so the curated 108 rows pick up populated `media_path` values, then
   re-verify the page renders without console errors.

## 2026-05-14 — §4 checkpoint 4 (mapping curation, in-branch) — follow-up pass

**Scope (follow-up)**: extend the curation beyond the structural-rule
floor with a small manual pass targeted at starter-plan + common-strength
exercises that the structural rule under-confirms, mark a handful of
obvious wrong-matches as `rejected`, and unblock the §4 pytest gate by
retiring a stale checkpoint-1-era assertion. No DB writes; no route or
template changes.

### What landed (follow-up)

| File | Status | What landed |
|---|---|---|
| `data/free_exercise_db_mapping.csv` | modified | 10 additional rows flipped `auto` → `manual` (clear naming-variance / implicit-modifier matches with verified upstream + on-disk asset) and 5 rows flipped `auto` → `rejected` (clear false-positive high-score suggestions). Final distribution: 1784 auto, 98 confirmed, 10 manual, 5 rejected. Total reviewed: **113** (≥50 §4.7 tertiary acceptance bar). |
| `tests/test_free_exercise_db_mapping.py` | modified | `TestMappingCsv.test_csv_passes_validator` retired its stale `assert rows == []` line. That assertion was authored under checkpoint 1's header-only CSV and was not refreshed when checkpoint 3 (`1ff57ff`) committed the 1,897-row populated CSV; the test has been red on the branch ever since. The retained `assert errors == []` still enforces the CSV-validator contract end-to-end on the populated CSV, which is now the meaningful invariant. |

### Manual confirmations (10 rows → `manual`)

Each row was hand-verified against the upstream `exercises.json` name and
the on-disk asset at `static/vendor/free-exercise-db/exercises/<fed_id>/0.jpg`:

| Local exercise | Upstream `fed_id` | Reason |
|---|---|---|
| `Cable Standing Shoulder Press` | `Cable_Shoulder_Press` | starter plan; "standing" implicit |
| `Cable Rope Hammer Curl` | `Cable_Hammer_Curls_-_Rope_Attachment` | starter plan; rope attachment matches |
| `Machine Seated Calf Raises` | `Seated_Calf_Raise` | starter plan; "machine" implicit |
| `Pull Ups` | `Pullups` | common strength; compound vs spaced |
| `Situp` | `Sit-Up` | common strength; compound vs hyphenated |
| `Barbell Squat` | `Barbell_Full_Squat` | common strength; "full" = standard ROM |
| `Barbell Squat - Quadriceps focused` | `Barbell_Full_Squat` | same plus local cue suffix |
| `Cable Pallof Press Rotation` | `Pallof_Press_With_Rotation` | common strength; word order |
| `Band Skullcrusher` | `Band_Skull_Crusher` | naming variance only |
| `Dumbbell Seated One Arm Triceps Extension` | `Dumbbell_One-Arm_Triceps_Extension` | "seated" implicit for this movement |

### Manual rejections (5 rows → `rejected`)

These were score-100 auto suggestions the mapper proposed at the top of
the §4.3 step-2 review queue; each is a clear false positive. Marking
them `rejected` signals to future curation passes that they have been
reviewed and have no good upstream match:

| Local exercise | Mapper's suggestion | Why rejected |
|---|---|---|
| `Barbell Decline Bench Press` | `Barbell_Incline_Bench_Press` | decline ≠ incline |
| `Barbell Split Squat` | `Barbell_Side_Split_Squat` | split ≠ side split (different exercise) |
| `Smith Machine Bench Press` | `Machine_Bench_Press` | smith machine ≠ generic machine |
| `Smith Machine Incline Bench Press` | `Smith_Machine_Bench_Press` | loses incline modifier |
| `Smith Deadlift` | `Axle_Deadlift` | smith machine ≠ axle bar |

### Verification (follow-up)

- `.venv/Scripts/python.exe scripts/curate_free_exercise_db_mapping.py --dry-run`
  → idempotent: 0 additional auto rows flipped; recognises the 15 newly
  reviewed rows as "other status" (script preserves `manual` / `rejected`).
- `.venv/Scripts/python.exe -m pytest tests/test_free_exercise_db_mapping.py -q`
  → **79 passed in 2.52s** (back to green after the stale assertion was
  retired).
- Scoped apply dry-run (filter CSV to `confirmed` + `manual` rows, run
  `scripts/apply_free_exercise_db_mapping.py --dry-run`):
  ```
  Scoped CSV: 108 confirmed/manual rows
  OK (dry-run): 108 row(s) would be applied (0 ignored as auto/rejected).
  ```
- Unscoped `scripts/apply_free_exercise_db_mapping.py --dry-run` still
  fails on the **pre-existing trailing-whitespace catalogue row**
  documented at the top of the original entry — `'Dumbbell Shoulder
  Internal Rotation '` at line 909 of the CSV (review_status `auto`, so
  not applied; the all-or-nothing validator aborts on the row anyway).
  Fix path (a)/(b)/(c) decision still deferred to checkpoint 5.

### Coverage delta

- Catalogue-wide: 108 of 1,897 rows now apply (5.7%), up from 98 (5.2%).
- Starter-plan defaults (17 exercises per `checkpoint3_coverage.md`):
  6 of 17 covered after this pass (3 previously confirmed by the
  structural rule + 3 added via manual `Cable Standing Shoulder
  Press` / `Cable Rope Hammer Curl` / `Machine Seated Calf Raises`).
  The remaining 11 starter-plan slots are either ambiguous (auto rows
  the script left in `auto`) or have no upstream match (`Hollow Hold`,
  `Cable Pushdown with back support`, etc.).
- §4.7 thresholds: tertiary (≥50 reviewed) cleared with margin (113).
  Primary (NULL `media_path` rows render exactly like today) is gated on
  checkpoint 5/6 template work and is not exercised by this checkpoint.

### Why this is the right stopping point

Beyond the obvious naming-variance and implicit-modifier cases listed
above, remaining `auto` rows trip the autonomous-policy bar in
`docs/ACTIVE_DEVELOPMENT.md` Next Task: "Leave ambiguous rows as `auto`
or `rejected`; do not ask the owner for routine judgement calls." For
example, `Cable Low Single Arm Lateral Raise` → `Cable_Seated_Lateral_Raise`
(score 68) drops both "Low" and "Single Arm" and gains "Seated" —
arguably correct enough to render a thumbnail, but not unambiguous
enough for an unattended flip. Those judgements belong to a future
human review pass and are explicitly outside the scope of this
checkpoint.

## 2026-05-14 — §4 checkpoint 4 (mapping curation, in-branch)

**Scope**: §4.3 step 2 (human review of CSV proposals). Branch
`feat/workout-cool-section-4-checkpoint-3`, on top of `1ff57ff`. No DB
writes. No route/template changes. No new tests yet (the existing
`tests/test_free_exercise_db_mapping.py` already covers the validator
and apply-script contract; the curation script is a reproducible
artifact, not a production code path).

### What landed

| File | Status | What landed |
|---|---|---|
| `scripts/curate_free_exercise_db_mapping.py` | new | Reproducible curation pass. Reads `data/free_exercise_db_mapping.csv`, flips `auto` → `confirmed` for rows whose local + upstream names produce equal token sets after lenient normalization (lowercase, punctuation noise removal, alias collapse for `band/bands` etc., stopword removal, plural-strip, and a small `" - <muscle> focused"` cue-suffix strip on the local side). Score floor and asset existence are also enforced. Idempotent: re-running on a curated CSV flips zero additional rows. |
| `data/free_exercise_db_mapping.csv` | modified | 98 of 1,897 rows flipped from `review_status=auto` to `confirmed` by the curation script. All 98 pass `scripts/apply_free_exercise_db_mapping.py` validation (DB-name lookup + on-disk asset existence). |

### Curation rule (encoded in the script, not in human edits)

A row is flipped to `confirmed` iff **all** of the following hold:

1. Current `review_status == auto`.
2. `score >= 60` (mapper's combined name + equipment + muscle score).
3. `suggested_image_path` is non-blank and the upstream `fed_id`
   resolves to a name in `static/vendor/free-exercise-db/exercises.json`.
4. After the local cue-suffix strip and lenient token normalization
   (alias collapse, plural-strip, stopword removal), the local name
   and the **full** upstream name (including any `" - <variant>"`
   suffix) produce identical token sets.
5. The on-disk asset at `static/vendor/free-exercise-db/exercises/<path>`
   exists.

Rule (4) is the gate that rejects false positives the mapper's score
threshold misses on its own — e.g., `Barbell Decline Bench Press` →
`Barbell_Incline_Bench_Press` (score 100) is left as `auto` because
`{decline}` and `{incline}` differ. Hand-spot-checked all 98 flipped
rows; zero visible mismatches.

### Coverage hit

The starter-plan default-args subset is **non-deterministic** (the
generator draws from candidate sets), so its precise overlap with the
98 confirmed rows shifts between runs. Catalog-wide coverage from this
pass: 98 / 1,897 = 5.2%. That clears the §4.7 tertiary acceptance bar
(≥50 reviewed mappings) and is the explicit `auto`-→-`confirmed` floor
called out in `docs/MASTER_HANDOVER.md` Next Safe Step. Remaining `auto`
rows include both genuine high-score matches that the structural rule
under-confirms (cases where the upstream variant adds equipment text
that's already implicit in the local name) and genuine no-match rows
where no upstream exercise exists. Future curation passes can lift
these row-by-row.

### Apply-script dry-run

`scripts/apply_free_exercise_db_mapping.py --dry-run` returns 1 because
of a **pre-existing, unrelated DB defect** surfaced by validation:

```
FAILED: 1 row(s) reference unknown exercises:
  - line 909: exercise_name 'Dumbbell Shoulder Internal Rotation' not found in exercises table
```

The catalogue row literally exists as `'Dumbbell Shoulder Internal
Rotation '` (with a trailing space) in `data/database.db`. The
checkpoint-3 mapper preserved that whitespace in the generated CSV; the
apply script strips whitespace on read; the resulting trimmed name
fails the `WHERE exercise_name = ? COLLATE NOCASE` lookup against the
trailing-space row. This is the only such row in the catalogue.

**This is not a curation defect.** The affected row's
`review_status` is `auto`, not `confirmed`, so it would not actually be
applied. Apply-script all-or-nothing validation runs across every row,
including non-apply ones, which is why it aborts.

Scoping validation to only the 98 `confirmed` rows passes cleanly:

```
SCOPED-TO-CONFIRMED dry-run result:
  OK: all 98 confirmed/manual rows pass validation.
```

### Followups (not blocking checkpoint 4)

1. Resolve the trailing-whitespace catalogue row before checkpoint 5
   (route SELECT updates / thumbnail UI). Three viable paths:
   (a) extend the startup metadata repair in `utils/db_initializer.py`
       (the same pattern shipped in `6246854`) to `UPDATE exercises SET
       exercise_name = TRIM(exercise_name) WHERE exercise_name !=
       TRIM(exercise_name)`, then regenerate the CSV from the cleaned
       DB;
   (b) patch `scripts/map_free_exercise_db.py` `load_local()` to TRIM
       on read and regenerate the CSV;
   (c) patch `scripts/apply_free_exercise_db_mapping.py`
       `validate_against_db()` to use `WHERE TRIM(exercise_name) = ?
       COLLATE NOCASE` and accept that the live DB carries dirty rows.

   Path (a) is the architectural fix (PK should not carry significant
   whitespace) and matches the existing repair pattern. Decision
   deferred to checkpoint-5 owner.

2. The mapper script's `usage_subset` query returns near-zero results
   today because `workout_log` is empty (see fatigue-meter Stage 4
   notes) and `user_selection` has minimal entries. The "common
   strength (usage + starter)" subset in `checkpoint3_coverage.md` is
   therefore mostly starter-plan-only and is small. This is fine for
   checkpoint 4 (the structural rule covered ~5× the §4.7 floor on
   the strength subset directly), but the §4.7 secondary acceptance
   bar (≥70% of a ~150–250-row "common strength" subset) is gated on
   real `user_selection` / `workout_log` data accumulating.

### Verification

- `python scripts/curate_free_exercise_db_mapping.py --dry-run` →
  98 rows would flip; idempotent re-run on the curated CSV flips 0.
- `python scripts/apply_free_exercise_db_mapping.py --dry-run` → fails
  on the unrelated trailing-space row at line 909; scoped validation
  on the 98 confirmed rows passes cleanly.
- No new pytest cases run (curation produces an artifact, not a
  production code path); existing `tests/test_free_exercise_db_mapping.py`
  79-test suite remains green on the branch's pre-curation tree.

### Next sessions

1. Fix the trailing-whitespace catalogue row per one of (a)/(b)/(c)
   above so the unscoped apply dry-run is also clean.
2. Open checkpoint 5: route SELECT updates (`routes/workout_plan.py`,
   `routes/workout_log.py`, `utils/workout_log.py`) to include
   `media_path` in the page/JSON contract.
3. Open checkpoint 6: thumbnail rendering in templates + `escapeHtml()`
   rollout per §4.4 Option A.

## 2026-05-11 — §4 checkpoint 1 shipped on `main` (schema + validator + apply script)

**Scope**: §4.3-§4.6 data/import layer only. No vendor assets, no UI wiring.
Adapted from historical off-main commit `76bcd48` (checkpoint 1 of six), ported
against current `main` after diffing the schema patch context for the
intervening §5 `youtube_video_id` addition (the only collision was the trailing
comma on `youtube_video_id TEXT` inside `CREATE TABLE`, and an analogous
guarded `ALTER` next to the existing one).

### Polish after Codex review

Codex flagged three follow-ups against the first draft of the port; all
addressed before commit:

1. **Apply script is now truly transactional.** `apply_rows()` issues each
   `UPDATE` with `commit=False` so per-statement commits are suppressed;
   `DatabaseHandler.__exit__` performs one commit on success or one rollback
   on exception. A new test injects a synthetic `sqlite3.OperationalError`
   on the second `UPDATE EXERCISES` call and asserts every prior row's
   `media_path` rolled back to `NULL`.
2. **Shape validator tightened.** `is_valid_media_path_shape` now rejects
   `:` anywhere (blocks `C:/temp/0.jpg` and `C:temp/0.jpg`) and rejects
   single-dot path segments (blocks `./dir/0.jpg` and `dir/./0.jpg`, which
   would otherwise normalise away on `Path.resolve()` and silently work).
   Five new parametrised reject cases cover these inputs.
3. **Docs flipped to past tense** in the same commit so the planning state
   matches the committed tree.

### Files added / modified

| File | Status | What landed |
|---|---|---|
| `utils/db_initializer.py` | modified | Adds nullable `media_path TEXT` to `CREATE TABLE IF NOT EXISTS exercises` AND a guarded `ALTER TABLE exercises ADD COLUMN media_path TEXT` for legacy DBs. Fresh and migrated DBs converge on the same shape. |
| `utils/media_path.py` | new | Pure-function shape validator (`is_valid_media_path_shape`, `explain_media_path_shape_failure`) and filesystem resolver (`media_path_resolves`). Mirrors §4.3 rules: non-empty, no leading slash/backslash, no `..`, no empty segments, jpg/jpeg/png/gif/webp extension allowlist, file must live under `static/vendor/free-exercise-db/exercises/`. |
| `scripts/apply_free_exercise_db_mapping.py` | new | All-or-nothing apply: parses CSV, validates header + per-row shape + uniqueness + review_status, checks every `exercise_name` against the catalogue (case-insensitive), checks every confirmed/manual asset against the vendor base, then writes `media_path` for `confirmed`/`manual` rows only. `--dry-run` and `--vendor-base` flags. Idempotent. |
| `data/free_exercise_db_mapping.csv` | new (header-only) | Canonical column scaffold: `exercise_name,suggested_fed_id,suggested_image_path,score,review_status`. No rows yet. |
| `tests/test_free_exercise_db_mapping.py` | new | 73 cases covering validator accept/reject, schema additivity (fresh / legacy `ALTER` / re-init no-op), CSV shape, apply-script atomicity (unknown exercise, missing asset, invalid path all abort with no DB write), happy path, idempotency, CLI smoke. |

### Verification

Run on 2026-05-11 against this slice (post-polish):

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-pytest.ps1 tests/test_free_exercise_db_mapping.py` — 79 passed in 3.80s (73 original + 5 new validator-reject cases + 1 mid-loop rollback test).
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-pytest.ps1 tests/test_youtube_video_id.py tests/test_priority0_filters.py tests/test_workout_plan_routes.py tests/test_workout_log_routes.py` — 122 passed in 20.09s (adjacent route/contract + §5 schema neighbour; no regressions).

### Out of scope for this checkpoint

- No vendored `static/vendor/free-exercise-db/` assets (the historical `d4bb636`
  commit lands ~21 MB of images plus `exercises.json`; deferred to its own
  checkpoint so the schema slice can be reviewed in isolation).
- No `routes/workout_plan.py` / `routes/workout_log.py` SELECT changes.
- No `templates/workout_plan.html` / `templates/workout_log.html` thumbnail
  rendering.
- No `escapeHtml()` rollout in `static/js/modules/workout-plan.js`.
- No `tests/test_workout_plan_routes.py` or `tests/test_workout_log_routes.py`
  contract extension for the new field.

### Next sessions

1. Vendor `static/vendor/free-exercise-db/{LICENSE,NOTICE.md,VERSION,exercises.json,exercises/}`. Cross-reference historical commit `d4bb636` for the file list; do not blindly cherry-pick — re-derive the pin and re-fetch from the upstream commit.
2. Generate `data/free_exercise_db_mapping.csv` proposals via a `scripts/map_free_exercise_db.py` mapper (per PLANNING.md §4.3) and human-review them.
3. Apply via the script. Add backend route-contract tests once a non-empty mapping is in place.
4. Thumbnail rendering + `escapeHtml()` rollout per §4.4 (depends on a populated mapping or a fixture row).

## 2026-05-11 — §5 shipped on `main` (YouTube reference video modal)

**Scope**: §5.1-§5.8 (Pattern A modal + nullable schema field, apply script,
and `/workout_plan` and `/workout_log` wiring). This was adapted from historical
off-main §5 commits and landed on current `main` after the AI workflow refit.
Curated CSV ships header-only, so every uncurated row uses the search fallback.

### Commits on `main`

| Commit | What landed |
|---|---|
| `bc88ee8` | Schema + apply script + route contracts. Adds nullable `youtube_video_id TEXT` to `exercises`, guarded migration for existing DBs, `/get_workout_plan` and `/get_workout_logs` JSON fields, server-rendered workout-log metadata, header-only curated CSV, and validation tests. |
| `0842778` | Shared modal and `/workout_plan` wiring. Adds `exercise-video-modal.js`, `templates/partials/exercise_video_modal.html`, one base-template include, shared button/modal CSS, and plan-page Playwright coverage. |
| `1e5a1c0` | `/workout_log` wiring. Adds server-rendered play buttons, log-page JS binding, and workout-log Playwright coverage. |

### Conflict resolution note

The historical modal commit conflicted in `static/css/components.css`. The
resolution kept the current `main` CSS and added only the §5 video modal/button
styles; an unrelated body-composition CSS block from the old branch was not
ported.

### Compliance posture (§5.6)

- Embed via `https://www.youtube.com/embed/<id>` only. No download, cache, or
  rehosting of video data or thumbnails.
- "Watch on YouTube" link is present in the embed surface with `target="_blank"`
  and `rel="noopener noreferrer"`.
- NULL or malformed IDs fall back to a YouTube search URL for the exercise name.

### Verification

Run on 2026-05-11 against current `main`:

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-pytest.ps1 tests/test_youtube_video_id.py` — 40 passed in 4.64s.
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/workout-plan.spec.ts e2e/workout-log.spec.ts` — 52 passed in 1.6m.

### Outstanding / next sessions

- §4 (free-exercise-db media + path validation + thumbnail rendering) is next.
- §3.6 (Profile coverage body map) remains deferred.

## 2026-04-29 — §3 kickoff (workout-plan body map only)

**Scope**: §3.1–§3.5 + §3.7. Profile coverage body map (§3.6) deferred per
defaults agreed at start. No DB/schema changes (presentation-only).

### Upstream pin

- Source repo: `https://github.com/Snouzy/workout-cool` (MIT, Mathias Bradiceanu, 2023).
- Pinned commit SHA: **`77f25a922b51be7d96bd051c5d2096959f0d61a8`** (resolved
  from `main` via the GitHub commits API on 2026-04-29).
- Sources fetched verbatim from `raw.githubusercontent.com` at that SHA into
  `tmp/workout-cool-77f25a/` (gitignored). Files retrieved:
  - `LICENSE` (MIT)
  - `src/features/workout-builder/ui/muscle-selection.tsx` (1220 lines —
    parent SVG container, body silhouette outlines, head/glute accent paths)
  - `src/features/workout-builder/ui/muscles/{abdominals,back,biceps,calves,
    chest,forearms,glutes,hamstrings,obliques,quadriceps,shoulders,traps,
    triceps}-group.tsx` (13 files, 3011 lines combined)
  - Total upstream source: 4231 lines (matches PLANNING.md §3.2 estimate).

### Layout findings (verified against raw TSX, not WebFetch summaries)

Upstream renders **a single 535×462 SVG containing two bodies side-by-side**:

- **LEFT half** (X &lt; ~268): anterior (front) body. Confirmed: every
  `<path>` in `chest-group.tsx` has X coords in 70–160. Every path in
  `abdominals-group.tsx` is also low-X.
- **RIGHT half** (X &gt;= ~268): posterior (back) body. Confirmed: every
  `<path>` in `back-group.tsx` has X coords above 360.

Several muscle groups span both halves:

- `SHOULDERS` — anterior paths (X≈50–180) become `front-shoulders`;
  posterior paths (X≈340–470) become `rear-shoulders`. (PLANNING §3.3.)
- `FOREARMS`, `CALVES` — paths in both halves; both kept and share the
  same canonical key on each side (matches `MUSCLES_BY_SIDE` listing
  `forearms` and `calves` on both `front` and `back` in
  `muscle-selector.js`).
- `TRICEPS` — upstream draws triceps **only** on the posterior body
  (every path in `triceps-group.tsx` has X ≥ 341). `MUSCLES_BY_SIDE.front`
  still lists `triceps` because react-body-highlighter draws a small
  lateral-arm region on the anterior, so the front tab continues to
  expose `triceps` via the legend; the workout-cool simple variant
  simply has no clickable SVG path for it. Recorded in the deviation
  note below.
- `TRAPS` — paths in both halves upstream, but `MUSCLES_BY_SIDE` only lists
  `traps` on the back side. Anterior `TRAPS` paths will be **dropped** at
  build time so the front view matches the existing app model.
- `BICEPS` — only kept on anterior. `OBLIQUES`, `QUADRICEPS`,
  `ABDOMINALS` — anterior only. `BACK`, `GLUTES`, `HAMSTRINGS` —
  posterior only.

These rules are encoded in `scripts/build_workout_cool_svgs.py` as a single
`(enum, side) → [canonical-keys]` table.

### Body silhouette paths (in `muscle-selection.tsx`)

Outline / accent paths are not muscle groups but are needed for the body
shape:

| Line range | Starting `M` | Half | Notes |
|---|---|---|---|
| 44–421 | `M 440.43,458.85` | posterior | main posterior silhouette |
| 423–461 | `M 389.54,40.30` | posterior | head detail (fill `#757575`) |
| 463–483 | `M 386.48,416.75` | posterior | foot/glute crease detail |
| 485–505 | `M 461.30,429.86` | posterior | mirror of above on opposite side |
| 507–561 | `M 529.77,230.19` | posterior | side accent (right edge) |
| 563–617 | `M 325.88,218.03` | posterior | upper back accent |
| 619–942 | `M 163.05,461.45` | anterior | main anterior silhouette |
| 956+ | various | both | post-render overlays (head, neck, knee, ankle accents) |

The build script copies all of these into the appropriate SVG's
`<g class="body-outline">` group, so the silhouette renders identically to
upstream.

### Files added so far

- `static/vendor/workout-cool/LICENSE` — verbatim upstream MIT.
- `static/vendor/workout-cool/NOTICE.md` — attribution + change log.
- `static/vendor/workout-cool/VERSION` — pinned SHA + import date.
- `.gitignore` — added `/tmp/` to keep the upstream source download out of
  version control. The build script can re-fetch it deterministically.

### Deviation from PLANNING.md §3.3: triceps not drawn on anterior

Discovered during SVG build: upstream's `triceps-group.tsx` only contains
paths in the high-X cluster (X ≥ 341). Workout-cool does **not** draw
triceps on the anterior body. This is anatomically reasonable (most
triceps mass is hidden from the front by biceps and the lateral arm
silhouette) and matches what we'd see in any standard front-facing
illustration.

Consequence: the existing `MUSCLES_BY_SIDE.front` array
([muscle-selector.js:262-266](../../static/js/modules/muscle-selector.js#L262-L266))
includes `'triceps'` (the react-body-highlighter SVG renders a small
lateral-arm triceps polygon on the anterior side). Workout-cool's SVG
won't have that polygon, so `triceps` becomes legend-clickable but not
SVG-clickable on the anterior tab.

**Resolution**: extend the §3.3 *Unmapped-by-art allowlist* to include
`triceps` on the anterior side. The original allowlist already covers
`adductors`, `hip-abductors`, and `neck`, all of which workout-cool
likewise doesn't draw. Effective allowlist for the workout-cool variant:

| Canonical key | Anterior | Posterior |
|---|---|---|
| `adductors` | unmapped | n/a |
| `hip-abductors` | n/a | unmapped |
| `neck` | unmapped | unmapped |
| `triceps` | unmapped (new) | mapped |

The §3.7 mapping test (`tests/test_muscle_selector_mapping.py`) will
encode this expanded allowlist. PLANNING.md §3.3 should be amended on
its next revision; this log records the deviation in the meantime.

### Build artifacts (committed)

- `static/vendor/workout-cool/body_anterior.svg` — viewBox `0 0 268 462`,
  39 muscle-region paths across 8 canonical keys (chest, abdominals,
  obliques, biceps, forearms, front-shoulders, quads, calves).
- `static/vendor/workout-cool/body_posterior.svg` — viewBox
  `268 0 267 462` (non-zero min-x crops the left half), 39 muscle-region
  paths across 8 distinct values (calves, forearms, glutes,
  `lats,upper-back,lowerback`, rear-shoulders, traps, triceps,
  hamstrings). Note that `lats,upper-back,lowerback` is one
  multi-key region per §3.3.

### §3 done — what landed

| Area | Files |
|---|---|
| Vendor scaffolding | `static/vendor/workout-cool/{LICENSE,NOTICE.md,VERSION}` |
| TSX→SVG build | `scripts/build_workout_cool_svgs.py` (deterministic, fetches at pinned SHA from `raw.githubusercontent.com`; offline mode via `--src-dir`) |
| Generated art | `static/vendor/workout-cool/body_{anterior,posterior}.svg` (39 muscle-region paths each, 8 distinct canonical keys per side, plus the multi-key BACK region) |
| JS refactor | `static/js/modules/muscle-selector.js` — `SVG_PATHS[mode][side]`, `getSvgPathForMode()`, `getCanonicalKeys()`, `flattenToAdvancedChildren()`, `regionVisualState()`, `toggleRegion()`; `switchViewMode()` reloads the SVG variant; `mapVendorSlugsToCanonical()` skips pre-canonicalized regions |
| CSS | `pages-workout-plan.css` — verified `.muscle-region.partial` rules already present (pre-existing, no edit needed); workout-cool SVGs intentionally ship a minimal inline `<style>` (just `.body-outline path { pointer-events: none; }`) so the page CSS palette controls every state, including dark mode |
| Tests (pytest) | `tests/test_muscle_selector_mapping.py` — 16 new tests in `TestWorkoutCoolSvgCoverage` (7) and `TestRegionVisualState` (9). Full suite: 1175 passed (was 1159) in ~3m 20s |
| Tests (E2E) | `e2e/workout-plan.spec.ts` — 3 new tests in "Muscle selector body-map variants". Targeted run: 3/3 passed in ~10s |
| Docs | `docs/muscle_selector.md` — view-mode SVG variants + multi-key click semantics. `docs/muscle_selector_vendor.md` — workout-cool attribution + refresh procedure + unmapped-by-art table |

### Untouched per scope

- `static/js/modules/bodymap-svg.js` — Profile coverage map's loader.
  Confirmed `muscle-selector.js` does not import it, so no shared-loader
  pressure forced an edit. Profile coverage continues to use
  react-body-highlighter unchanged.
- DB schema, route contracts, and template render paths — §3 is
  presentation-only and stays that way.

### Outstanding / next sessions

- §5 (YouTube modal — one nullable column, both `/workout_plan` and
  `/workout_log`) — next per the §6 risk-ordered sequence.
- §4 (free-exercise-db media + `escapeHtml()` rollout) — third.
- §3.6 (Profile coverage body map) — deferred indefinitely; future
  separate plan.
- PLANNING.md §3.3 should be amended on its next revision to add
  `triceps` to the anterior unmapped-by-art allowlist (see deviation
  recorded above).
