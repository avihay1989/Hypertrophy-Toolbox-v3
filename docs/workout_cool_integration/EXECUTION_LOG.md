# workout-cool Integration — Execution Log

Tracks concrete work against `PLANNING.md`. Newest entry on top.

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
