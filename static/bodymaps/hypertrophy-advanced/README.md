# Hypertrophy Toolbox Advanced Body Map

`body_anterior.svg` / `body_posterior.svg` power the **Advanced** view of the
workout-plan muscle selector. They are generated — do not edit by hand.

## Source & license

The anatomy art is derived from [MuscleMap](https://github.com/melihcolpan/MuscleMap)
by Melih Colpan, used under the **MIT License**. MuscleMap ships its male body
geometry as SVG path strings embedded in Swift; we vendor those files (plus
LICENSE + VERSION) under [`static/vendor/musclemap/`](../../vendor/musclemap/)
and mechanically re-emit them as inline-clickable SVGs.

## How to regenerate

```bash
python scripts/build_musclemap_svgs.py
```

The script reads `static/vendor/musclemap/Male{Front,Back}Paths.swift`, maps
each MuscleMap muscle slug to one advanced canonical key (see
`SLUG_SIDE_TO_KEY` in the script — mirror of `SIMPLE_TO_ADVANCED_MAP` in
`static/js/modules/muscle-selector.js`), and writes the two SVGs here. Output
is byte-deterministic for a given vendored source.

## Contract

- Interactive regions: `<path class="muscle-region" data-canonical-muscles="<key>">`.
  Each is a single MuscleMap muscle that selects exactly itself; the runtime
  styles them via `.muscle-region` rules in `static/css/pages-workout-plan.css`
  (incl. dark mode + advanced-id stroke-width overrides for the 727-wide viewBox).
- Cosmetic parts (head / hair / hands / feet / knees / ankles) live in a
  non-interactive `<g class="body-outline">`.
- Coordinate space is verbatim MuscleMap: anterior `viewBox="0 95 727 1280"`,
  posterior `viewBox="718 95 727 1280"`.
- `tests/test_muscle_selector_mapping.py::TestFirstPartyAdvancedSvgCoverage`
  asserts the per-side key set.

`upper-back` (rhomboids) and `hip-abductors` have no distinct MuscleMap region
and are legend-only in the selector. These SVGs are the single body map used by
both the plan-modal muscle selector and the Profile coverage map.
