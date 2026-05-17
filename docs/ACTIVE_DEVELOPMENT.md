# Active Development

This file is the execution source of truth for autonomous development sessions. Use it when it conflicts with older narrative planning text.

## Current Objective

workout.cool §4 (free-exercise-db thumbnails) is **fully shipped on `origin/main`**. PR #20 (squash `8b348a5`) landed the feature; PR #23 (`bfd9087`) landed the post-merge handoff refresh + nav-dropdown e2e stabilization + dependency pin bumps; PR #22 (`631b5f8`) landed the §4.6 visual-baseline spec + seed. No outstanding workout.cool work remains.

The default next workstream is the **redesign post-P8 triage** (#7 + #8 next, per `debug/redesign_post_p8_issues_SESSION_STATE.md`) unless the owner redirects.

## Current Branch

`main`, in sync with `origin/main` at `631b5f8`. Working tree dirty only on `data/database.db` (runtime; owner-approved kept dirty per `CLAUDE.md` agents-must-not list).

Recent history on `origin/main` (newest first):

- `631b5f8` (2026-05-18) — **PR #22** `test(workout-cool §4.6): add visual-baseline thumbnail spec + seed`. Adds `e2e/visual-baseline-thumbnails.spec.ts` (18 tests) and `scripts/seed_visual_baseline.py`. `.gitignore` now ignores `e2e/artifacts/`. Screenshots are inspection artifacts only — no `toHaveScreenshot()` pixel baselines committed.
- `bfd9087` (2026-05-18) — **PR #23** `chore: post-section-4 handoff refresh + nav e2e + dependency pins`. Replaces closed PR #21. Rebased onto `origin/main` to drop the seven pre-squash §4 commits that had made the original branch `CONFLICTING`. Carries the nav-dropdown off-viewport fix and the Playwright/sass/TS/Node/Flask/pandas/click bumps.
- `8b348a5` (2026-05-15) — **PR #20** `feat(workout-cool §4): free-exercise-db exercise thumbnails`. Squash bundles checkpoints 3–6.
- `7a77315` (2026-05-14) — **PR #19** `feat(workout-cool §4): vendor free-exercise-db assets (checkpoint 2)`.

## Already Done

- §4 checkpoint 1: `media_path` schema, path validator, and `scripts/apply_free_exercise_db_mapping.py`.
- §4 checkpoint 2: `static/vendor/free-exercise-db/` assets, `LICENSE`, `NOTICE.md`, `VERSION`, `exercises.json`, 873 `0.jpg` images.
- §4 checkpoint 3: `scripts/map_free_exercise_db.py`, `data/free_exercise_db_mapping.csv` (raw 1,897 rows), `docs/workout_cool_integration/checkpoint3_coverage.md`.
- §4 checkpoint 4: `scripts/curate_free_exercise_db_mapping.py` (structural-equivalence rule) + curated `data/free_exercise_db_mapping.csv` (1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed).
- §4 checkpoint 5: `_trim_exercise_name_whitespace` repair pass in `utils/db_initializer.py`; `media_path` surfaced in `/get_workout_plan` + `/get_workout_logs` JSON and in `utils/workout_log.py::get_workout_logs`; +4 trim tests + +4 route-contract tests.
- §4 checkpoint 6: `static/js/modules/exercise-helpers.js` with `escapeHtml()` + `resolveExerciseMediaSrc()`; workout-plan row renderer thumbnails; workout-log template `safe_media_path` Jinja filter; thumbnail CSS; +4 self-contained Playwright tests + +2 filter unit tests.
- §4 squash-merge (`8b348a5`) on 2026-05-15.
- Post-§4 follow-up (`bfd9087`) on 2026-05-18: nav e2e off-viewport fix + dependency pin refresh.
- §4.6 visual-baseline (`631b5f8`) on 2026-05-18: 18-test spec + seed.
- Apply-mapping: `exercises.media_path` populated for 108 rows (98 confirmed + 10 manual) in the main-checkout DB and the visual-baseline worktree DB.
- Fatigue meter Phase 1 / Stage 4 entry parked by owner choice (Option 1 confirmed 2026-05-13).

## Next Task

No active workstream is currently in-flight on `origin/main`. The natural next picks, in order of priority:

### Option A — Redesign post-P8 triage (#7 + #8)

Per the workstream table in `docs/MASTER_HANDOVER.md`. Owner state: 5 issues remaining; #6 done; #7 + #8 are next. See `debug/redesign_post_p8_issues_SESSION_STATE.md` for the full queue and where each issue stands.

### Option B — phase5_3i_plan resume

Paused mid-draft. Resume from `debug/phase5_3i_plan_SESSION_STATE.md` if the owner prefers planning work over execution.

### Optional — workout.cool §4 follow-ups

None are blocking. Available if the owner wants final polish:

- Owner eyes-on review of the 18 visual-baseline screenshots at `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4/e2e/artifacts/visual-baseline/`. The spec asserts behavioural invariants (thumbnail count ≥ 1, src prefix, theme attr) but doesn't pixel-compare.
- Clean up the `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4` worktree. The remote branch is gone; local branch `test/visual-baseline-thumbnails` is unmerged-locally because the worktree holds it.
- Lock in `toHaveScreenshot()` pixel baselines once layout has settled (currently the spec captures PNGs for inspection only).

### Fatigue meter — DO NOT REOPEN

Fatigue is parked per `docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md` (owner Option 1, 2026-05-13). No Phase 2 work, no `/fatigue` page, no API endpoints, no `utils/fatigue.py` edits. Reopen only if `workout_log` accumulates ≥4 labeled real weeks, or the owner explicitly overrides the parked state.

## Agent Authority

Agents may, without asking the owner:

- Update docs that are stale relative to committed `origin/main` state.
- Run targeted pytest / Playwright checks.
- Continue from one listed task to the next after tests pass.

Agents must not:

- Reset, force-push, or otherwise discard working-tree state without owner approval.
- Commit `data/database.db` (runtime; agents-must-not list in CLAUDE.md).
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
- The owner explicitly redirects the work.

Transport failures, idle stream stalls, or stale chat titles are not repo blockers. Start a fresh agent session and point it at this file.

## Required Checkpoint Closeout

Before calling a checkpoint done:

- Update `docs/MASTER_HANDOVER.md`.
- Update `docs/workout_cool_integration/EXECUTION_LOG.md` for workout.cool work; or the equivalent workstream log for other workstreams.
- Record tests run and results.
- Leave the diff commit-ready, with generated DB/runtime files excluded unless explicitly intended.
