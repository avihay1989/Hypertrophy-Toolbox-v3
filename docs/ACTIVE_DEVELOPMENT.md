# Active Development

This file is the execution source of truth for autonomous development sessions. Use it when it conflicts with older narrative planning text.

## Current Objective

Finish workout.cool §4 exercise thumbnails through mapping curation, mapping apply, route contracts, thumbnail UI, escaping, and validation.

## Current Branch

`feat/workout-cool-section-4-checkpoint-3`

Known history:

- `origin/main` at `7a77315`: workout.cool §4 checkpoint 2, free-exercise-db assets vendored.
- Branch at `1ff57ff`: workout.cool §4 checkpoint 3, mapping proposals and coverage report generated.
- Branch at `e3ebd43`: workout.cool §4 checkpoint 4, curated CSV (113 reviewed rows) + fatigue parked-decision docs.

## Already Done

- §4 checkpoint 1: `media_path` schema, path validator, and `scripts/apply_free_exercise_db_mapping.py`.
- §4 checkpoint 2: `static/vendor/free-exercise-db/` assets, `LICENSE`, `NOTICE.md`, `VERSION`, `exercises.json`, and 873 `0.jpg` images.
- §4 checkpoint 3: `scripts/map_free_exercise_db.py`, `data/free_exercise_db_mapping.csv`, and `docs/workout_cool_integration/checkpoint3_coverage.md`.
- §4 checkpoint 4 (shipped at `e3ebd43`): `scripts/curate_free_exercise_db_mapping.py` (structural-equivalence rule) + curated `data/free_exercise_db_mapping.csv` (1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed) + stale-assertion fix + bundled fatigue Stage 4 parked-decision docs.
- §4 checkpoint 5 (in-branch, uncommitted): `_trim_exercise_name_whitespace` repair pass in `utils/db_initializer.py` (path (a)), `media_path` surfaced in `/get_workout_plan` + `/get_workout_logs` JSON and in `utils/workout_log.py::get_workout_logs` (workout-log page render), `data/free_exercise_db_mapping.csv` line-909 trailing-space cleanup, 4 trim tests in `tests/test_priority0_filters.py`, 4 route-contract tests in `tests/test_free_exercise_db_mapping.py::TestRouteContracts`. Unscoped `apply_free_exercise_db_mapping.py --dry-run` now reports `OK: 108 row(s) would be applied (1789 ignored as auto/rejected)`. Full pytest: 1287 passed in 158.99s.
- Fatigue meter Phase 1 / Stage 4 entry is parked by owner choice (Option 1 confirmed 2026-05-13). Do not work on fatigue unless explicit reopen criteria are met.

## Next Task

Commit the in-branch checkpoint-5 slice, then open checkpoint 6.

### Step 1 — commit checkpoint 5

Stage only these files:

- `utils/db_initializer.py` (new `_trim_exercise_name_whitespace` pass + call-site)
- `routes/workout_plan.py` (`/get_workout_plan` adds `e.media_path`)
- `routes/workout_log.py` (`/get_workout_logs` adds `e.media_path`)
- `utils/workout_log.py` (`get_workout_logs()` SQL adds `e.media_path`)
- `tests/test_priority0_filters.py` (+4 trim regression tests)
- `tests/test_free_exercise_db_mapping.py` (+4 route-contract tests in `TestRouteContracts`)
- `data/free_exercise_db_mapping.csv` (line 909 trailing-space cleanup)
- `docs/MASTER_HANDOVER.md`, `docs/workout_cool_integration/EXECUTION_LOG.md`, `docs/ACTIVE_DEVELOPMENT.md`

Do **not** stage unrelated dirty files: `data/database.db` (mutated locally by `initialize_database(force=True)` during verification), `.mcp.json`, `.claude/settings.json`, `package.json`, `package-lock.json`, `requirements.txt`, `e2e/nav-dropdown.spec.ts`.

### Step 2 — open checkpoint 6 (thumbnail rendering + escapeHtml rollout)

Per PLANNING.md §4.4 Option A — server-rendered thumbnail tags on plan/log pages, plus the `escapeHtml()` rollout in `static/js/modules/workout-plan.js`.

1. Add a `resolveExerciseMediaSrc()` helper (or equivalent) that returns the `static/vendor/free-exercise-db/exercises/<media_path>` URL when `media_path` is non-null, and falls back gracefully otherwise.
2. Render the thumbnail in `templates/workout_plan.html` and `templates/workout_log.html` adjacent to the exercise name (size + placement per §4.4 mocks).
3. Roll out `escapeHtml()` for any user-rendered strings in the affected JS paths.
4. Apply the curated mappings to the live DB via `scripts/apply_free_exercise_db_mapping.py` so the 108 confirmed/manual rows pick up `media_path` values.
5. Add Playwright coverage (visual or attribute-level) for at least one row with a populated thumbnail and one with null.

## Agent Authority

Agents may, without asking the owner:

- Update docs that are stale relative to committed branch state.
- Curate high-confidence CSV rows.
- Mark obvious mismatches as `rejected`.
- Add focused tests for the current checkpoint.
- Run targeted pytest / Playwright checks.
- Continue from one listed task to the next after tests pass.

Agents must not:

- Redo checkpoint 2 vendoring.
- Regenerate checkpoint 3 mapping proposals unless the mapper itself changes.
- Mutate committed `data/database.db` as source of truth.
- Start fatigue-meter work.
- Start Phase 2 fatigue planning.
- Edit `utils/fatigue.py`.
- Touch unrelated dirty files unless the active task requires it.

## Stop Conditions

Ask the owner only if:

- A destructive DB reset, branch reset, or file deletion is required.
- License / attribution status is unclear.
- A product behavior change would exceed the approved plan.
- Tests reveal a broad unrelated regression.
- The mapping policy cannot be resolved by the rules above.
- The owner explicitly redirects the work.

Transport failures, idle stream stalls, or stale chat titles are not repo blockers. Start a fresh agent session and point it at this file.

## Required Checkpoint Closeout

Before calling a checkpoint done:

- Update `docs/MASTER_HANDOVER.md`.
- Update `docs/workout_cool_integration/EXECUTION_LOG.md`.
- Record tests run and results.
- Leave the diff commit-ready, with generated DB/runtime files excluded unless explicitly intended.
