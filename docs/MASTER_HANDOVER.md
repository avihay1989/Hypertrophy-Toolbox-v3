# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: `feat/workout-cool-section-4-checkpoint-3`. **Upstream is `[gone]`** — the remote branch was deleted after squash-merge. The seven historical workout.cool §4 commits (four checkpoints `1ff57ff`, `e3ebd43`, `df27c8d`, `d00eae6` plus three docs stamps `553d52a`, `966a338`, `8fd6ffe`) were collapsed into squash commit `8b348a5` on `origin/main` and now produce an empty net diff against it. Two local follow-up commits sit on top:
  - `3919d82 docs: update handoff for workout.cool §4 squash merge` — refreshed `docs/MASTER_HANDOVER.md` + `docs/ACTIVE_DEVELOPMENT.md` for the post-merge state.
  - `e135ff5 test: stabilize nav dropdown e2e and refresh dependency pins` — `e2e/nav-dropdown.spec.ts` off-viewport fix + Playwright/sass/TS/node-engine + Flask/pandas pins.
  Net `git diff origin/main..HEAD` is exactly those two commits' files; there is **no unmerged workout.cool feature code**. Local `main` is one commit behind `origin/main` and has not been fast-forwarded yet.
- **§4 squash-merged to `origin/main` on 2026-05-15** as commit `8b348a5 feat(workout-cool §4): free-exercise-db exercise thumbnails` (PR #20). Squash bundles checkpoints 3–6: mapping proposal + curation (1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed), `media_path` route contracts, DB whitespace repair, thumbnail UI + `escapeHtml()` / `resolveExerciseMediaSrc()` helpers, and the `safe_media_path` Jinja filter. **§4 is shipped.**
- **Prior milestone on `main`**: §4 checkpoint 2 (`7a77315`, PR #19) — free-exercise-db assets vendored under `static/vendor/free-exercise-db/`.
- **Last verified pytest** (pre-merge, on the branch at `8fd6ffe`): full suite **1289 passed in 171.47s on 2026-05-14**. Re-verify after syncing local `main` to `8b348a5` (the requirements pins are now committed in `e135ff5`).
- **Last verified E2E (Chromium)** (pre-merge): targeted plan+log **56 passed in 1.6m on 2026-05-14** (`e2e/workout-plan.spec.ts` + `e2e/workout-log.spec.ts`). Last full E2E baseline remains 414 passed / 1 failed on 2026-05-10; failure was `nav-dropdown.spec.ts:117` dark-mode toggle off-viewport at 1440 width — the `evaluate(() => toggle.click())` stabilization is now **committed in `e135ff5`** and no longer dirty.
- **Dirty working tree** (uncommitted, owner-decision required before sync) — narrowed to three entries:
  - `.claude/settings.json` (local agent permissions overhaul + MCP servers disabled) — local-personal config.
  - `.mcp.json` (deletion of project-level context7 + puppeteer MCP) — project config decision.
  - `data/database.db` (runtime; agents-must-not list in CLAUDE.md) — do not commit.

  The previously-dirty `e2e/nav-dropdown.spec.ts`, `package.json`, `package-lock.json`, and `requirements.txt` are now committed in `e135ff5` and are no longer in the dirty set.

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow refit | complete through Tier 2 + T3.1 | Use [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) + this handover as active truth; treat `.claude/SHARED_PLAN.md` as local audit history only | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked by owner choice (Phase 1 + Stage 4 entry shipped; Option 1 confirmed 2026-05-13) | Treat as complete-for-now; proceed with non-fatigue work unless real logged weeks, owner labels, or explicit Phase 2 override arrive. No Phase 2 / `utils/fatigue.py` edits while parked. | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md), [docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md](fatigue_meter/STAGE4_PARKED_HANDOFF.md) |
| workout.cool integration | §3 + §4 + §5 all shipped on `origin/main`. §4 squash-merged 2026-05-15 as `8b348a5` (PR #20). Branch carries no unmerged feature code; two local follow-up commits sit on top (`3919d82` docs, `e135ff5` nav e2e + dependency pins). Local `main` one commit behind `origin/main`; branch upstream `[gone]`. | (1) Owner decision on the remaining three dirty files (`.claude/settings.json`, deleted `.mcp.json`, `data/database.db`) — stash / revert / commit as appropriate; (2) fast-forward local `main` to `origin/main` once the working tree is clean (or stashed); (3) cherry-pick `3919d82` and `e135ff5` onto the new local `main` if those follow-ups should land there; (4) run the deferred visual baseline pass per PLANNING §4.6 (desktop / tablet / mobile × light / dark × simple / advanced); (5) run `scripts/apply_free_exercise_db_mapping.py` against the canonical DB to populate `exercises.media_path` for the 108 confirmed/manual rows. | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md), [docs/workout_cool_integration/EXECUTION_LOG.md](workout_cool_integration/EXECUTION_LOG.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- **Dirty working-tree disposition.** The nav e2e + dependency pin follow-up was committed in `e135ff5`, so the dirty set is narrowed to three files awaiting owner call:
  - **Local-personal config**: `.claude/settings.json` (agent permissions list overhauled, MCP servers disabled). Owner decides whether to keep local-only (revert or move to `.claude/settings.local.json`) or commit.
  - **Project config decision**: `.mcp.json` deletion (was project-level context7 + puppeteer MCP). Owner decides whether to commit the deletion.
  - **Do not commit**: `data/database.db` (runtime, per CLAUDE.md agent-must-not list).
- **Local follow-up commits relative to `origin/main`.** `3919d82` (handoff docs refresh) and `e135ff5` (nav e2e + dependency pins) live only on this branch. After local `main` fast-forwards to `8b348a5`, owner decides whether to cherry-pick either or both onto local `main` (or open a small follow-up PR) or drop them.

## Blockers
- None for §4 ship (already merged). Post-merge sync is gated on the dirty-file disposition above.

## Next Safe Step
Use [docs/ACTIVE_DEVELOPMENT.md](ACTIVE_DEVELOPMENT.md) as the execution source of truth. §4 is **shipped on `origin/main` as `8b348a5`**. The next safe sequence: (1) owner decision on the three remaining dirty files (`.claude/settings.json`, `.mcp.json` deletion, `data/database.db`) — stash, revert, or commit as appropriate; (2) fast-forward local `main` to `origin/main` once the working tree is clean (or stashed); (3) cherry-pick `3919d82` and/or `e135ff5` onto the new local `main` if those follow-ups should land there; (4) run the deferred visual baseline pass per §4.6; (5) run `scripts/apply_free_exercise_db_mapping.py` against the canonical DB to populate `exercises.media_path` for the 108 confirmed/manual rows. Fatigue meter remains parked per `docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md` — no Phase 2 work, no `utils/fatigue.py` edits.
