# YouTube Reference Videos

## Current State

The reference-video feature has shipped as application infrastructure, and a
first curated batch landed 2026-05-22 (`cf21191`, 36 rows).

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
- `data/youtube_curated_top_n.csv` ships with **36 curated rows + header** as
  of `cf21191`. The matching exercise rows now open the embedded iframe; all
  other rows still use the YouTube search fallback.

What is not complete:

- Coverage is partial — only ~36 of the 1,897 catalogue exercises have curated
  IDs. Long-tail rows still fall through to the search fallback (this is the
  designed hybrid behavior, not a bug).
- Expanding curation beyond 36 rows is content work; no infrastructure changes
  are required.

## User-Facing Behavior

Each exercise row has one play button.

- Valid 11-character YouTube ID: opens the modal with
  `https://www.youtube.com/embed/<id>` and a "Watch on YouTube" external link.
- NULL, blank, or malformed ID: opens the same modal in search mode, with a CTA
  to YouTube search for `<exercise name> exercise form`.

This is the planned hybrid behavior from
[PLANNING.md §5.4](PLANNING.md#54-where-the-video-ids-come-from): manually curate
top exercises, use search fallback for the long tail.

## What Is Needed To Finish The Content

1. Choose a starter curation scope.
   A practical first batch is 30-50 common lifts and starter-plan exercises:
   squat variants, deadlift variants, bench/incline bench, overhead press, rows,
   pulldowns, pull-ups, dips, leg press, leg extension/curl, hip thrust, lateral
   raise, curls, triceps pressdowns/extensions, calf raises, and common core
   movements.

2. Populate `data/youtube_curated_top_n.csv`.
   Format:

   ```csv
   exercise_name,youtube_video_id
   Bench Press,dQw4w9WgXcQ
   ```

   `youtube_video_id` is the 11-character ID from a YouTube URL, not the full
   URL.

3. Validate and apply:

   ```powershell
   .venv\Scripts\python.exe scripts\apply_youtube_curated.py --dry-run
   .venv\Scripts\python.exe scripts\apply_youtube_curated.py
   ```

4. Verify:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-pytest.ps1 tests/test_youtube_video_id.py
   ```

   For UI confidence, also run the workout-plan and workout-log Playwright specs
   if the curation change is committed:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-playwright.ps1 e2e/workout-plan.spec.ts e2e/workout-log.spec.ts
   ```

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
