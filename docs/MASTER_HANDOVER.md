# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: `main`
- **Last committed milestone**: `1a889d8` — docs(ai-workflow): apply CODEX cross-review to Tier 2.2 council (#18)
- **Last verified pytest**: 1160 passed in 159.70s on 2026-05-10
- **Last verified E2E (Chromium)**: 414 passed / 1 failed on 2026-05-10. Failure is pre-existing & out-of-scope: `nav-dropdown.spec.ts:117` dark-mode toggle off-viewport at 1440 width. The previous `program-backup.spec.ts:79` DB-state-pollution flake passed in this full run.

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow refit | complete through Tier 2; T3.1 docs complete in current change | Use [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) + this handover as active truth; treat `.claude/SHARED_PLAN.md` as audit history only | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked (Phase 1 + Stage 4 entry shipped) | Hold; no Phase 2 / `utils/fatigue.py` edits without real data or explicit go-ahead | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md) |
| workout.cool integration | §3 shipped on `main`; §5 and §4 are pending in the active plan | Start §5 YouTube modal first per risk-ordered sequence, then §4 free-exercise-db media. Historical §4/§5 commits exist off-main and can be used as reference only. | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- Whether to archive or leave `.claude/SHARED_PLAN.md` as local audit history. It is no longer the active workflow source of truth.
- Before starting workout.cool §5, decide whether to cherry-pick/adapt the historical off-main §5 commits or reimplement from the active plan.

## Blockers
- None.

## Next Safe Step
Commit the T3.1 workflow docs closeout, then start workout.cool §5 (YouTube modal) from [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md) §5. Use historical off-main §5 commits as reference only after reviewing their diff against current `main`.
