# MuscleMap — Attribution

Body anatomy geometry vendored here is from the open-source project
[MuscleMap](https://github.com/melihcolpan/MuscleMap) by Melih Colpan, used
under the MIT License (see `LICENSE`).

Upstream ships its body art as SVG path strings embedded in Swift source under
`Sources/MuscleMap/Data/`. We vendor only the male path data + supporting types:

- `MaleFrontPaths.swift`, `MaleBackPaths.swift` — the SVG `d` strings.
- `BodyPathData.swift` — the `BodyViewBox` (coordinate space) definitions.
- `LICENSE`, `VERSION` — upstream license + pinned commit.

`scripts/build_musclemap_svgs.py` parses these and emits
`static/bodymaps/hypertrophy-advanced/body_{anterior,posterior}.svg` with our
`.muscle-region` / `data-canonical-muscles` conventions for the workout-plan
Advanced muscle selector.

## How to refresh

1. Bump `VERSION` to the new upstream commit + import date and replace the
   vendored `.swift` files from that commit.
2. Re-run `python scripts/build_musclemap_svgs.py`.
3. Inspect the diff and run `tests/test_muscle_selector_mapping.py`.

## License

The MIT License terms in `LICENSE` cover the upstream source. This `NOTICE.md`
and the build script are part of our repo and follow our project license.
