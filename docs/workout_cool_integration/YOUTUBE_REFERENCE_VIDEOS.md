# YouTube Reference Videos

## Current State

The reference-video feature has shipped as application infrastructure, and the
curated batch landed in two passes: `cf21191` (2026-05-22, 36 rows) and
`ff244aa` (2026-05-23, +20 rows → 56 rows total). Curation is considered
**closed by diminishing returns** — see "Curation Closed" below.

What is complete:

- `exercises.youtube_video_id` exists as a nullable text column.
- `/get_workout_plan` and `/get_workout_logs` expose `youtube_video_id`.
- `/workout_plan` and `/workout_log` both render the play button.
- `static/js/modules/exercise-video-modal.js` opens either an embedded YouTube
  iframe for valid IDs or a YouTube search fallback for missing/invalid IDs.
- `scripts/apply_youtube_curated.py` validates and applies curated IDs
  all-or-nothing.
- `tests/test_youtube_video_id.py` covers schema, validation, importer, and
  route-contract behavior.
- `data/youtube_curated_top_n.csv` ships with **56 curated rows + header** as
  of `ff244aa` (cumulative across `cf21191` + `ff244aa`). The matching
  exercise rows open the embedded iframe; all other rows use the YouTube
  search fallback (designed hybrid behavior).

## Curation Closed (2026-05-23, diminishing returns)

Triage of the remaining ~1,841 uncurated catalogue rows against actual usage
in `user_selection` + `workout_log` found that **all but one** have 0–1
combined uses; the lone exception is `Barbell Close Grip Bench Press` (2
uses). The 56 curated rows already cover every common/core lift with
meaningful usage signal; the remaining catalogue is dominated by stretches,
recovery drills, band variants, and obscure variations that the search
fallback already handles correctly.

Closing rationale:

- The 56-row set covers every exercise with >1 actual use except one edge
  case; no further data-driven signal remains.
- Expanding by guessing or fabricating YouTube IDs would degrade UX vs. the
  search fallback, which always produces a working `<exercise name> exercise
  form` query.
- The hybrid behavior in [PLANNING.md §5.4](PLANNING.md#54-where-the-video-ids-come-from)
  was always the design intent — curate top-N, search-fallback the long tail.

If the owner ever wants to add more rows later, the flow is unchanged:

1. Append rows to `data/youtube_curated_top_n.csv` (exercise_name,
   youtube_video_id). YouTube ID must be 11 chars, owner-vetted.
2. Run `.venv\Scripts\python.exe scripts\apply_youtube_curated.py --dry-run`
   then re-run without `--dry-run`. The importer is idempotent and
   all-or-nothing.
3. Verify with
   `.venv\Scripts\python.exe -m pytest tests/test_youtube_video_id.py -q`.

## User-Facing Behavior

Each exercise row has one play button.

- Valid 11-character YouTube ID: opens the modal with
  `https://www.youtube.com/embed/<id>` and a "Watch on YouTube" external link.
- NULL, blank, or malformed ID: opens the same modal in search mode, with a CTA
  to YouTube search for `<exercise name> exercise form`.

This is the planned hybrid behavior from
[PLANNING.md §5.4](PLANNING.md#54-where-the-video-ids-come-from): manually curate
top exercises, use search fallback for the long tail.

## UX Follow-Up Options

The current UI always shows the play button. For uncurated rows, it opens the
search fallback. If that feels misleading, consider one of these follow-ups:

- Keep the current single button, but change the tooltip/title for uncurated rows
  to make the search behavior explicit.
- Use a distinct search icon for uncurated rows and a play icon only for curated
  rows.
- Hide the video button unless a curated ID exists, and add a separate explicit
  search action elsewhere.

Any UX change should preserve the `/workout_plan` and `/workout_log` symmetry
documented in [PLANNING.md §5.5](PLANNING.md#55-frontend--workout_log-is-in-scope).

## Related Docs

- [PLANNING.md §5](PLANNING.md#5-youtube-reference-decision-pattern-a--single-button-modal) -
  original design and accepted hybrid approach.
- [EXECUTION_LOG.md §5 shipped](EXECUTION_LOG.md#2026-05-11--5-shipped-on-main-youtube-reference-video-modal) -
  what landed on `main`.
- [../../CHANGELOG.md](../CHANGELOG.md) - release note for the schema/UI ship.
