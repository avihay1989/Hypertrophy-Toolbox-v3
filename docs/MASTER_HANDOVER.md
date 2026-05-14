# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: `feat/workout-cool-section-4-checkpoint-3` (origin/main at `7a77315` = §4 checkpoint 2). Checkpoint 4 shipped at `e3ebd43`; checkpoint 5 (DB trim repair + route contracts) work in progress, uncommitted.
- **Last committed milestone on `main`**: workout.cool §4 checkpoint 2 — free-exercise-db assets vendored under `static/vendor/free-exercise-db/` (LICENSE, NOTICE.md, VERSION pin, `exercises.json`, 873 image folders). Shipped via PR #19 (`7a77315`).
- **Last committed milestone on the branch**: workout.cool §4 checkpoint 4 — `scripts/curate_free_exercise_db_mapping.py` + curated `data/free_exercise_db_mapping.csv` (1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed), the stale-assertion fix in `tests/test_free_exercise_db_mapping.py`, the bundled fatigue Stage 4 parked-decision docs (`docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md` + matching `PLANNING.md` / `calibration-notes.md` updates), and refreshed `MASTER_HANDOVER.md` / `ACTIVE_DEVELOPMENT.md` (`e3ebd43`). Checkpoint 3 (`1ff57ff`) shipped the mapper, the raw 1,897-row CSV, and the coverage report.
- **In-branch (uncommitted) checkpoint 5 state (2026-05-14)**: `utils/db_initializer.py` gains a guarded `_trim_exercise_name_whitespace` pass between `_normalize_muscle_group_values` and `_repair_known_exercise_metadata` (path (a) from checkpoint 4's followups). It trims `exercises.exercise_name` PK values that drift on whitespace and updates `exercise_isolated_muscles.exercise_name`, `user_selection.exercise`, and `workout_log.exercise` in lockstep under `PRAGMA defer_foreign_keys = ON`. After running against the live DB, the previously-blocked unscoped `apply_free_exercise_db_mapping.py --dry-run` is clean: **OK: 108 row(s) would be applied (1789 ignored as auto/rejected).** `/get_workout_plan` and `/get_workout_logs` JSON now also return `media_path` alongside `youtube_video_id` (PLANNING.md §4.5); `utils/workout_log.py::get_workout_logs` parallels the change so the workout-log page render inherits the field. The CSV row at line 909 was trimmed to match the cleaned DB. Tests: 4 new trim cases in `tests/test_priority0_filters.py` + 4 new route-contract cases (`TestRouteContracts`) in `tests/test_free_exercise_db_mapping.py`.
- **Last verified pytest**: full suite **1287 passed in 158.99s on 2026-05-14** (post-checkpoint-5). Targeted §4 gate: 83 passed in 4.60s (was 79; +4 route-contract tests). `tests/test_priority0_filters.py` gate: 23 passed in 4.03s (was 19; +4 trim tests). Adjacent regression batch (priority0 + plan/log routes + youtube): 126 passed in 47.31s.
- **Last verified E2E (Chromium)**: no E2E run for the checkpoint-5 data/test slice (no UI changes; thumbnail render lands in checkpoint 6). Last verified E2E gate: §5 targeted 52 passed in 1.6m on 2026-05-11 (`e2e/workout-plan.spec.ts`, `e2e/workout-log.spec.ts`). Last full E2E baseline remains 414 passed / 1 failed on 2026-05-10; failure is pre-existing & out-of-scope: `nav-dropdown.spec.ts:117` dark-mode toggle off-viewport at 1440 width.

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow refit | complete through Tier 2 + T3.1 | Use [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) + this handover as active truth; treat `.claude/SHARED_PLAN.md` as local audit history only | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked by owner choice (Phase 1 + Stage 4 entry shipped; Option 1 confirmed 2026-05-13) | Treat as complete-for-now; proceed with non-fatigue work unless real logged weeks, owner labels, or explicit Phase 2 override arrive. No Phase 2 / `utils/fatigue.py` edits while parked. | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md), [docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md](fatigue_meter/STAGE4_PARKED_HANDOFF.md) |
| workout.cool integration | §3 + §5 shipped on `main`; §4 checkpoints 1+2 shipped on `main`; checkpoint 3 (mapping proposals) + checkpoint 4 (curated 113 reviewed rows) shipped on branch `feat/workout-cool-section-4-checkpoint-3`; checkpoint 5 (DB trim repair + `media_path` route contracts) **in-branch, uncommitted**; full pytest 1287 green | Commit the uncommitted checkpoint-5 slice (`utils/db_initializer.py`, `routes/workout_plan.py`, `routes/workout_log.py`, `utils/workout_log.py`, `tests/test_priority0_filters.py`, `tests/test_free_exercise_db_mapping.py`, `data/free_exercise_db_mapping.csv` line-909 cleanup, docs); then open checkpoint 6 (thumbnail UI + `escapeHtml()` rollout per §4.4 Option A). | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md), [docs/workout_cool_integration/EXECUTION_LOG.md](workout_cool_integration/EXECUTION_LOG.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- None outstanding for §4. Path (a) — DB-side TRIM repair in `utils/db_initializer.py` — was implemented in checkpoint 5.

## Blockers
- None for new work. Unscoped apply dry-run is now clean after the live-DB trim ran.

## Next Safe Step
Use [docs/ACTIVE_DEVELOPMENT.md](ACTIVE_DEVELOPMENT.md) as the execution source of truth. Commit the checkpoint-5 slice and open checkpoint 6 — thumbnail rendering in `templates/workout_plan.html` + `templates/workout_log.html` and the `escapeHtml()` rollout in `static/js/modules/workout-plan.js` per [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md) §4.4 Option A.
