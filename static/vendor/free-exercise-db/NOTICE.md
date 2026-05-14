# free-exercise-db — Attribution

Exercise reference imagery (`exercises/<name>/0.jpg`) and the bundled
catalogue metadata (`exercises.json`) are derived from the open-source
project [free-exercise-db](https://github.com/yuhonas/free-exercise-db)
by Jonathan Wong (and contributors). The upstream is released into the
public domain under the Unlicense (see `LICENSE`).

The pinned upstream commit and import date are recorded in `VERSION`.

## Deviations from upstream

This repository vendors a subset of the upstream payload:

1. **Only canonical `0.jpg` images are vendored.** Upstream ships two
   reference frames per exercise (`0.jpg` and `1.jpg`). For workout-cool
   §4 v1 we only need `images[0]` — the canonical reference image
   referenced by the apply script and frontend renderer. Skipping
   `1.jpg` halves the on-disk asset payload and avoids committing
   assets that no v1 code path reads. Alternate-angle `1.jpg` images
   can be re-imported later if a "show alternate view" UI affordance
   is ever added — see "How to refresh" below.

2. **Per-exercise `exercises/<name>.json` files are not vendored.** Their
   contents are duplicated by entries in the bundled `dist/exercises.json`
   (which we vendor as `exercises.json`). Skipping them avoids ~870
   redundant files.

3. **Source layout is flattened.** Upstream ships the catalogue at
   `dist/exercises.json` and images at `exercises/<name>/<n>.jpg`. We
   place the catalogue at `static/vendor/free-exercise-db/exercises.json`
   and images at `static/vendor/free-exercise-db/exercises/<name>/0.jpg`,
   which matches the relative paths the apply script writes into
   `exercises.media_path`.

## How to refresh

1. Bump `VERSION` to the new upstream commit SHA + import date.
2. Re-run the vendor process: shallow-clone upstream at the new SHA,
   copy `dist/exercises.json` → `static/vendor/free-exercise-db/exercises.json`,
   copy each `exercises/<name>/0.jpg` → matching path under
   `static/vendor/free-exercise-db/exercises/<name>/0.jpg`.
3. If a future feature needs alternate frames, also copy `1.jpg` and
   update `VERSION` + this `NOTICE.md` to reflect the new scope.
4. Re-run `tests/test_free_exercise_db_mapping.py` (and any later
   thumbnail tests) to confirm the apply script + path validator still
   accept the vendored shape.

## License

The Unlicense terms in `LICENSE` cover the upstream assets. This
attribution `NOTICE.md` and the `VERSION` file are part of our repo and
follow our project license.
