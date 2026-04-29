# workout-cool — Attribution

Body anatomy SVG art (`body_anterior.svg`, `body_posterior.svg`) is derived
from the open-source project [workout-cool](https://github.com/Snouzy/workout-cool)
by Mathias Bradiceanu, used under the MIT License (see `LICENSE`).

The original art lives as React/TSX components under
`src/features/workout-builder/ui/muscles/*.tsx` and the parent container
`src/features/workout-builder/ui/muscle-selection.tsx`. Our SVG files are
mechanically derived from those sources via `scripts/build_workout_cool_svgs.py`
at the upstream commit pinned in `VERSION`.

## What we changed

- React-isms (`className={...}`, `data-elem={Enum.X}`, `onClick`) replaced
  with plain SVG attributes:
  - `class="muscle-region"`
  - `data-canonical-muscles="<key1>[,<key2>,...]"` carrying our own
    canonical muscle keys (pre-canonicalized at build time so the runtime
    JS doesn't need an upstream-slug-to-canonical translation table for
    these SVGs).
- The single upstream 535×462 SVG (with anterior + posterior bodies
  side-by-side) is split into two files:
  - `body_anterior.svg` — left half (X &lt; ~268), viewBox `0 0 268 462`.
  - `body_posterior.svg` — right half (X &gt;= 268), viewBox
    `268 0 267 462` (path coordinates kept verbatim; the viewBox crops the
    left half).
- Decorative `className="fill-transparent"` paths in the upstream source
  are dropped (they render nothing).
- Static accent paths (e.g. inter-pec shading, head detail) are preserved
  inside a `.body-outline` `<g>`.

## How to refresh

1. Bump `VERSION` to the new upstream commit SHA + import date.
2. Re-run `python scripts/build_workout_cool_svgs.py`. The script fetches
   sources at the pinned SHA from `raw.githubusercontent.com` and emits
   byte-deterministic SVGs given the same source.
3. Inspect the resulting diff and run `tests/test_muscle_selector_mapping.py`
   to confirm canonical-muscle coverage hasn't regressed.

## License

The MIT License terms in `LICENSE` cover the upstream source. This
attribution `NOTICE.md` and the build script are part of our repo and
follow our project license.
