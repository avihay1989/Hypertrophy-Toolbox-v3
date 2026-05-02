# workout-cool Integration — Execution Log

Tracks concrete work against `PLANNING.md`. Newest entry on top.

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
