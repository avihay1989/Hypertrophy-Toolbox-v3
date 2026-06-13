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

Each exercise row has one reference-video button whose icon and action depend on
whether the exercise has a curated id:

- **Valid 11-character YouTube ID** (play glyph): opens the in-app modal with
  `https://www.youtube.com/embed/<id>` and a "Watch on YouTube" external link.
- **NULL, blank, or malformed ID** (magnifier glyph): opens a YouTube search in a
  new tab (`https://www.youtube.com/results?search_query=<exercise name>%20exercise%20form`)
  — **no modal**. The user lands on a real results list and picks a video. This
  replaced the earlier "No reference video has been curated yet" modal panel
  (removed 2026-06-14) because a direct results list is more useful than an
  intermediate message.

This is the planned hybrid behavior from
[PLANNING.md §5.4](PLANNING.md#54-where-the-video-ids-come-from): manually curate
top exercises, use search fallback for the long tail.

## UX Follow-Up — Option 2 Shipped (2026-06-13)

The button now signals its behavior by icon and accessible name instead of
always reading as "play":

- **Curated rows** (valid 11-char id): play glyph (`fa-play`), title
  "Watch reference video", aria-label "Play reference video for `<name>`".
- **Uncurated rows** (NULL/blank/malformed id): magnifier glyph (`fa-search`),
  title "Search YouTube for reference video", aria-label "Search YouTube for a
  `<name>` reference video". Clicking opens a YouTube search tab directly (see
  User-Facing Behavior above) — it no longer routes through the modal.

Both render sites were updated symmetrically — the plan page's JS button builder
(`static/js/modules/exercise-video-modal.js` `buildPlayButton`) and the
server-rendered log row (`templates/workout_log.html`) — preserving the
`/workout_plan` ↔ `/workout_log` symmetry from
[PLANNING.md §5.5](PLANNING.md#55-frontend--workout_log-is-in-scope). The modal's
search-mode panel and its `.exercise-video-search-wrap` CSS were deleted as dead
code once the uncurated path stopped using the modal. Coverage:
`tests/test_youtube_video_id.py` (icon + aria-label per state) plus the
`workout-plan.spec.ts` / `workout-log.spec.ts` accessible-button + search-tab
specs.

The remaining unbuilt options (reword tooltip only; or hide the button unless a
curated id exists + separate search action) are not planned — Option 2 plus the
direct-search-tab behavior resolves the "misleading play button" concern without
removing the long-tail search affordance.

## Related Docs

- [PLANNING.md §5](PLANNING.md#5-youtube-reference-decision-pattern-a--single-button-modal) -
  original design and accepted hybrid approach.
- [EXECUTION_LOG.md §5 shipped](EXECUTION_LOG.md#2026-05-11--5-shipped-on-main-youtube-reference-video-modal) -
  what landed on `main`.
- [../../CHANGELOG.md](../CHANGELOG.md) - release note for the schema/UI ship.
