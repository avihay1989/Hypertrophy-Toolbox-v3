# Fatigue Body Heatmap — Planning (draft v1)

**Status:** DRAFT — pending owner decisions (see §8). Not started.
**Goal:** On `/fatigue`, color a MuscleMap body figure by each muscle's fatigue
band so the user sees at a glance which muscles are loaded. Picks up the
deferred item in [`PLANNING.md`](PLANNING.md) §"Bodymap / per-muscle view
deferred to Phase 2 (D1 + Stage 5 preview)".

This is a **visualization** of data the fatigue meter already computes — it adds
no new fatigue math and changes no thresholds.

---

## 1. Why this is mostly assembly, not new infrastructure

Three pieces already exist and line up:

1. **The figure** — the single MuscleMap SVG (`static/bodymaps/hypertrophy-advanced/`)
   is already vendored, generated, and used by the plan selector + Profile map.
2. **"Color SVG regions by per-muscle state"** — `static/js/modules/bodymap-svg.js`
   already loads the figure (`loadBodymapSvg`), annotates each `.muscle-region`
   from `data-canonical-muscles`, and the Profile page applies a per-region
   `state-*` class. The heatmap is the same pattern with a different data
   source (fatigue band instead of coverage state).
3. **The colors** — fatigue bands `light / moderate / heavy / very_heavy`
   already have CSS classes/palette (`fatigue-*`) used by the SFR cards and bars.

So the new work is: a fatigue-muscle → region mapping, a small rendering module,
band-colored CSS, data plumbing, and tests.

## 2. Data source (server-rendered — no new API)

`/fatigue` is server-rendered and **intentionally has no `/api/fatigue/*`**
(D2.7 / Phase 1 D9). Respect that:

- `utils/fatigue_data.build_fatigue_page_context()` already produces
  `muscle_rows`, each row `{ "muscle", "band", planned/logged values, pct, ... }`.
- Embed that list as a JSON `<script type="application/json" id="fatigue-heatmap-data">`
  block in `fatigue.html`. The heatmap JS reads it — no fetch.
- The period selector already reloads the page server-side, so the embedded
  data (and thus the heatmap) updates with the period for free.

## 3. Fatigue muscle → MuscleMap region mapping (the crux)

The 12 ranked fatigue muscles (`utils/fatigue.py::MUSCLE_VOLUME_LANDMARKS`) map
cleanly to MuscleMap region keys (the `data-canonical-muscles` values):

| Fatigue muscle | MuscleMap region key | Side |
|---|---|---|
| Chest | `chest` | front |
| Latissimus-Dorsi | `lats` | back |
| Biceps | `biceps` | front |
| Triceps | `triceps` | front + back |
| Quadriceps | `quadriceps` | front |
| Hamstrings | `hamstring` | back |
| Glutes | `gluteal` | back |
| Calves | `calves` | front + back |
| Abdominals | `abs` | front |
| Traps | `trapezius` | back |
| Forearms | `forearms` | front + back |
| Middle-Shoulder | `front-deltoid` + `rear-deltoid` | front + back — **see §8.1** |

Unranked fatigue labels (no MEV/MAV/MRV → render `not_assessed`/gray): Front-Shoulder
→ `front-deltoid`, Rear-Shoulder → `rear-deltoid`, Lower Back → `lower-back`,
Hip-Adductors → `adductors`, Middle-Traps → `trapezius`, Neck → `neck`. The
MuscleMap `upper-back` region (rhomboids) has no fatigue muscle → `not_assessed`.

The mapping lives as one JS const (mirror of the Python muscle list); a
`test_*` sync check can assert every ranked muscle maps to a region that the
SVG actually draws — same guard style as `test_bodymap_canonical_in_sync`.

## 4. Color scale

Reuse the four existing fatigue bands so the heatmap matches the SFR cards/bars:
`light` → green, `moderate` → yellow, `heavy` → orange, `very_heavy` → red,
plus `not_assessed` → neutral gray. (A continuous %MRV gradient is a possible
later enhancement — see §8.3.) Dark-mode variants + the advanced-id stroke-width
overrides already exist in `pages-workout-plan.css` and can be mirrored into the
fatigue bundle.

## 5. UI

A new "Body heatmap" panel on `/fatigue`, above or beside the per-muscle bars:
- **Front / Back tabs** (reuse the muscle-selector tab pattern).
- **Planned / Logged toggle** (mirrors the existing dual bars).
- **Legend** (the four band colors) + **tooltips** (muscle name, band, %MRV).
- Degrades gracefully with no JS (the bars remain the primary view; `<noscript>`
  keeps the page usable, as today).

## 6. Phased implementation

1. **Mapping + data** — add the fatigue→region const (JS, optional Python
   mirror); embed `muscle_rows` JSON in `fatigue.html`.
2. **Rendering** — new `static/js/modules/fatigue-heatmap.js`: `loadBodymapSvg`,
   annotate regions with their fatigue muscle, apply band class; front/back +
   planned/logged toggles; tooltips.
3. **Styling** — fatigue band heatmap CSS (reuse palette) + dark mode; new panel
   layout in the fatigue route bundle.
4. **Tests** — pytest (mapping coverage + Python/JS sync); `e2e/fatigue.spec.ts`
   additions (panel renders, regions carry the right band class, toggles work,
   period reload re-colors). Update visual baselines if a snapshot is added.
5. **Docs + `/verify-suite`** — update `PLANNING.md` deferral line, this doc's
   status, and the fatigue docs; full gate before done.

## 7. Constraints & non-goals

- **No fatigue-math or threshold changes.** Pure visualization — does not touch
  `MUSCLE_VOLUME_LANDMARKS` / `SESSION_FATIGUE_BANDS` / `WEEKLY_FATIGUE_BANDS`,
  so it is compatible with the Stage-4 calibration-window freeze.
- **No `/api/fatigue/*`** (D2.7) — server-rendered embedded data only.
- Male figure only (matches the rest of the app). MuscleMap (MIT) — no new vendor.
- Informational only; nothing here blocks a session.

## 8. Open owner decisions (needed to finalize the plan)

1. **Middle-Shoulder** has no dedicated lateral-delt region in MuscleMap. Color
   **both** front+rear delt regions for it, color **front only**, or leave the
   delts driven only by the unranked Front/Rear-Shoulder labels?
2. **Metric & basis** — confirm color is driven by the per-muscle **band** with a
   **planned/logged toggle** (like the bars). Weekly basis, session basis, or both?
3. **Banded vs gradient** — 4 discrete band colors (matches the bars, less work)
   or a continuous %MRV gradient (richer, needs a new palette + legend)?
4. **Placement** — separate collapsible panel, or integrated next to the bar list?
5. **Unranked muscles** — show as gray "not assessed", or hide them entirely?
6. **Cosmetic styling** — match the MuscleMap demo (dark hair) or keep the
   current flat-gray head?

## 9. Suggested next step

Once §8 is answered, run `/council-plan` on this draft to harden it
(architecture / test-strategist / product-risk reviewers), then implement per §6.
