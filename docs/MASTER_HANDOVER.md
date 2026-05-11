# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: `main`
- **Last committed milestone**: `1e5a1c0` — feat(workout-cool §5): wire reference video modal into /workout_log
- **Last verified pytest**: targeted §5 gate 40 passed in 4.64s on 2026-05-11 (`tests/test_youtube_video_id.py`). Last full pytest baseline remains 1160 passed in 159.70s on 2026-05-10.
- **Last verified E2E (Chromium)**: targeted §5 gate 52 passed in 1.6m on 2026-05-11 (`e2e/workout-plan.spec.ts`, `e2e/workout-log.spec.ts`). Last full E2E baseline remains 414 passed / 1 failed on 2026-05-10; failure is pre-existing & out-of-scope: `nav-dropdown.spec.ts:117` dark-mode toggle off-viewport at 1440 width.

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow refit | complete through Tier 2 + T3.1 | Use [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) + this handover as active truth; treat `.claude/SHARED_PLAN.md` as local audit history only | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked (Phase 1 + Stage 4 entry shipped) | Hold; no Phase 2 / `utils/fatigue.py` edits without real data or explicit go-ahead | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md) |
| workout.cool integration | §3 + §5 shipped on `main`; §4 pending | Start §4 free-exercise-db media. Historical off-main §4 commits exist and can be used as reference only after review against current `main`. | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- Whether to mine the historical off-main §4 commits or reimplement §4 from the active plan. Review against current `main` before cherry-picking because those commits came from an older branch lineage.

## Blockers
- None.

## Next Safe Step
Start workout.cool §4 (free-exercise-db media) from [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md) §4. Begin by reviewing the historical off-main §4 commits against current `main`, then land schema/path-validation pieces before large media assets.
