# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: `feat/workout-cool-section-4-checkpoint-3` (origin/main at `7a77315` = §4 checkpoint 2). Five commits ahead: checkpoint 3 (`1ff57ff`), checkpoint 4 (`e3ebd43`), checkpoint 5 (`df27c8d`), docs stamp (`553d52a`), checkpoint 6 (`d00eae6`). **§4 is feature-complete; the branch is ready for PR.** No checkpoint work in flight.
- **Last committed milestone on `main`**: workout.cool §4 checkpoint 2 — free-exercise-db assets vendored under `static/vendor/free-exercise-db/` (LICENSE, NOTICE.md, VERSION pin, `exercises.json`, 873 image folders). Shipped via PR #19 (`7a77315`).
- **Last committed milestone on the branch**: workout.cool §4 checkpoint 6 (`d00eae6`) — PLANNING.md §4.4 Option A: new `static/js/modules/exercise-helpers.js` with `escapeHtml()` + `resolveExerciseMediaSrc()` (path-shape rules mirror `utils/media_path.py` verbatim); workout-plan row renderer routes every template-literal interpolation through `escapeHtml()` and prepends a 32×32 thumbnail when `media_path` is set; `templates/workout_log.html` server-renders the same thumbnail gated by the new `safe_media_path` Jinja filter (registered in `app.py` + `tests/conftest.py`) that revalidates §4.3 shape rules at render time. +4 self-contained Playwright tests (mock rows via `updateWorkoutPlanTable([row])` — no live-DB dependency) and +2 filter unit tests. Earlier on the branch: checkpoint 5 (`df27c8d`) added the `_trim_exercise_name_whitespace` PK-repair pass + surfaced `media_path` in `/get_workout_plan` and `/get_workout_logs` JSON; `553d52a` stamped the docs for shipped checkpoint 5; checkpoint 4 (`e3ebd43`) curated the mapping to 113 reviewed rows (1784 auto / 98 confirmed / 10 manual / 5 rejected) and bundled the fatigue Stage 4 parked-decision docs; checkpoint 3 (`1ff57ff`) shipped the mapper, the raw 1,897-row CSV, and the coverage report.
- **Last verified pytest**: full suite **1289 passed in 171.47s on 2026-05-14** (post-checkpoint-6).
- **Last verified E2E (Chromium)**: targeted plan+log **56 passed in 1.6m on 2026-05-14** (`e2e/workout-plan.spec.ts` + `e2e/workout-log.spec.ts`; was 52 baseline, +4 thumbnail/helper tests, all self-contained). Last full E2E baseline remains 414 passed / 1 failed on 2026-05-10; failure is pre-existing & out-of-scope: `nav-dropdown.spec.ts:117` dark-mode toggle off-viewport at 1440 width.

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow refit | complete through Tier 2 + T3.1 | Use [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) + this handover as active truth; treat `.claude/SHARED_PLAN.md` as local audit history only | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked by owner choice (Phase 1 + Stage 4 entry shipped; Option 1 confirmed 2026-05-13) | Treat as complete-for-now; proceed with non-fatigue work unless real logged weeks, owner labels, or explicit Phase 2 override arrive. No Phase 2 / `utils/fatigue.py` edits while parked. | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md), [docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md](fatigue_meter/STAGE4_PARKED_HANDOFF.md) |
| workout.cool integration | §3 + §5 shipped on `main`; §4 checkpoints 1+2 shipped on `main`; §4 **feature-complete** on branch — checkpoints 3+4+5+6 shipped (latest `d00eae6`) plus docs stamp `553d52a`; full pytest 1289 green, plan+log E2E 56 green | PR the five branch commits (`1ff57ff`, `e3ebd43`, `df27c8d`, `553d52a`, `d00eae6` — four checkpoint commits plus the docs stamp) against `main`. Visual baseline pass per §4.6 (desktop / tablet / mobile + light / dark + simple / advanced) folds into the next dedicated visual snapshot session. | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md), [docs/workout_cool_integration/EXECUTION_LOG.md](workout_cool_integration/EXECUTION_LOG.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- None outstanding for §4.

## Blockers
- None.

## Next Safe Step
Use [docs/ACTIVE_DEVELOPMENT.md](ACTIVE_DEVELOPMENT.md) as the execution source of truth. §4 is feature-complete on the branch (five commits ahead of `origin/main`). The next safe step is to PR the branch against `main`. After merge, the visual baseline pass per §4.6 (desktop / tablet / mobile + light / dark + simple / advanced) folds into the next dedicated visual snapshot session.
