# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: `main`
- **Last committed milestone**: workout.cool §4 checkpoint 1 — `media_path` schema + shape validator + apply script (no vendor assets, no UI).
- **Last verified pytest**: targeted §4 checkpoint-1 gate 79 passed in 3.80s on 2026-05-11 (`tests/test_free_exercise_db_mapping.py`). Adjacent regression: 122 passed in 20.09s (`tests/test_youtube_video_id.py` + `test_priority0_filters.py` + `test_workout_plan_routes.py` + `test_workout_log_routes.py`). Last full pytest baseline remains 1160 passed in 159.70s on 2026-05-10.
- **Last verified E2E (Chromium)**: no E2E run for this checkpoint (data/import layer only, no UI). Last verified E2E gate: §5 targeted 52 passed in 1.6m on 2026-05-11 (`e2e/workout-plan.spec.ts`, `e2e/workout-log.spec.ts`). Last full E2E baseline remains 414 passed / 1 failed on 2026-05-10; failure is pre-existing & out-of-scope: `nav-dropdown.spec.ts:117` dark-mode toggle off-viewport at 1440 width.

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow refit | complete through Tier 2 + T3.1 | Use [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) + this handover as active truth; treat `.claude/SHARED_PLAN.md` as local audit history only | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked (Phase 1 + Stage 4 entry shipped) | Hold; no Phase 2 / `utils/fatigue.py` edits without real data or explicit go-ahead | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md) |
| workout.cool integration | §3 + §5 + §4 checkpoint 1 (data/import layer) shipped on `main`; remaining §4 checkpoints pending | Vendor `static/vendor/free-exercise-db/` assets (LICENSE/NOTICE/VERSION/exercises.json/exercises/), then generate + review `data/free_exercise_db_mapping.csv` proposals, then route SELECT updates + thumbnail UI + `escapeHtml()` rollout. Historical commit `d4bb636` is a reference only; re-derive the pin. | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- None outstanding for §4 schema/import layer.

## Blockers
- None.

## Next Safe Step
Vendor the free-exercise-db assets per [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md) §4.2 / §4.5 (LICENSE, NOTICE.md, VERSION pin + commit SHA, `exercises.json`, image folder). Apply assets independently from any mapping CSV work; the `apply_free_exercise_db_mapping.py` script will validate paths against the vendor base directory once assets exist.
