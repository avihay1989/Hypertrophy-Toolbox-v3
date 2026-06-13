# Muscle Selector Vendor Integration

A single body-map figure is used across the app, sourced from the MIT-licensed
**MuscleMap** project and mechanically converted to plain inline SVGs with our
`.muscle-region` / `data-canonical-muscles` contract. Regions are
**pre-canonicalized** — every region carries `data-canonical-muscles="<key>"`
directly, so there is no runtime vendor-slug translation layer.

| Surface | Art | Vendor | Generator |
|---|---|---|---|
| Plan modal muscle selector | MuscleMap | `static/vendor/musclemap/` | `scripts/build_musclemap_svgs.py` |
| Profile coverage map | MuscleMap | `static/vendor/musclemap/` | (same generated SVGs) |

> History: an earlier `react-body-highlighter` advanced map and a `workout-cool`
> Simple-mode/Profile map were both retired in 2026-06 once everything moved to
> the single MuscleMap figure (and the Simple/Advanced toggle was removed). Their
> vendor dirs, build scripts, and the old `VENDOR_SLUG_TO_CANONICAL` translation
> layer went with them. The `workout_cool_integration/` docs retain the §3
> body-map history; the workout.cool **exercise media** features (§4/§5) are
> unrelated and still live.

See [muscle_selector.md](muscle_selector.md) for the runtime component overview.

## MuscleMap

- **Repository**: https://github.com/melihcolpan/MuscleMap
- **License**: MIT (Melih Colpan)
- **Pinned commit**: see [`static/vendor/musclemap/VERSION`](../static/vendor/musclemap/VERSION)

MuscleMap ships its male anatomy as SVG path strings embedded in Swift. We
vendor those path files (plus LICENSE/VERSION) and
[`scripts/build_musclemap_svgs.py`](../scripts/build_musclemap_svgs.py) emits
`static/bodymaps/hypertrophy-advanced/body_{anterior,posterior}.svg` (viewBox
`0 95 727 1280` / `718 95 727 1280`). Its clean human-shaped regions are
parent-level, so each simple group maps to one MuscleMap muscle key — see
`SLUG_SIDE_TO_KEY` in the build script (mirror of `SIMPLE_TO_ADVANCED_MAP`).
Full notes: [`static/bodymaps/hypertrophy-advanced/README.md`](../static/bodymaps/hypertrophy-advanced/README.md)
and [`static/vendor/musclemap/NOTICE.md`](../static/vendor/musclemap/NOTICE.md).

`upper-back` (rhomboids) and `hip-abductors` have no distinct MuscleMap region
and are legend-only in the selector. On the Profile coverage map the lat-wing
region maps to the **Upper Back** coverage chain (the only back-width chain).

## Mapping layers (`muscle-selector.js`)

```
data-canonical-muscles (SVG)  →  SIMPLE_TO_ADVANCED_MAP leaf keys  →  MUSCLE_TO_BACKEND
        (region)                       (selectedMuscles)              (priority_muscles API)
```

- `getCanonicalKeys()` reads `data-canonical-muscles` (comma-split).
- `flattenToAdvancedChildren()` expands simple keys to their advanced leaves;
  `selectedMuscles` only ever stores leaf keys.
- `getSelectedMusclesForBackend()` maps leaves through `MUSCLE_TO_BACKEND` for
  the `/generate_starter_plan` `priority_muscles` payload.

The Profile coverage map (`bodymap-svg.js`) annotates the same SVG regions with
backend coverage muscles via `CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES`.

## Adding / changing regions

Because the SVGs are generated, edit the **build script mapping**, not the SVGs
by hand:

1. Update `SLUG_SIDE_TO_KEY` in `scripts/build_musclemap_svgs.py` and re-run it.
2. Add the leaf key to `SIMPLE_TO_ADVANCED_MAP`, `MUSCLE_LABELS`, and
   `MUSCLE_TO_BACKEND` in `static/js/modules/muscle-selector.js`.
3. If the Profile coverage map should reflect it, add it to
   `CANONICAL_SIMPLE_TO_COVERAGE_MUSCLES` in `static/js/modules/bodymap-svg.js`.
4. Run `tests/test_muscle_selector_mapping.py`.

## Testing

`tests/test_muscle_selector_mapping.py` validates that the body-map SVGs carry
the expected per-side key set and that multi-key region state derivation matches
the JS `regionVisualState()`.
