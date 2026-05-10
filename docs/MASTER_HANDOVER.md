# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: `main`
- **Last commit**: `4d2febe` — docs(fatigue): record synthetic calibration stress test
- **Last verified pytest**: 1160 passed in 159.70s on 2026-05-10
- **Last verified E2E (Chromium)**: 414 passed / 1 failed on 2026-05-10. Failure is pre-existing & out-of-scope: `nav-dropdown.spec.ts:117` dark-mode toggle off-viewport at 1440 width. The previous `program-backup.spec.ts:79` DB-state-pollution flake passed in this full run.

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow Tier 1 | shipped 2026-05-10 | Awaiting user review before starting Tier 2 | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked (Phase 1 + Stage 4 entry shipped) | Hold; no Phase 2 / `utils/fatigue.py` edits without real data or explicit go-ahead | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md) |
| workout.cool integration | §3 + §5 shipped (2026-04-29 / 2026-04-30) | §4 free-exercise-db media | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- Tier 2 of the Avi Lewis workflow (worktree isolation + plan-review council) is approved in concept but not approved to start until Tier 1 ships and is reviewed.

## Blockers
- None.

## Next Safe Step
Tier 1 is complete and uncommitted. Review the new artifacts (handover spine, six folder maps, quality/unslop gate) and commit when satisfied. Do not start Tier 2 (worktree isolation + plan-review council) until that review and an explicit go-ahead.
