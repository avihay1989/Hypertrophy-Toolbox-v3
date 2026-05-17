# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: `feat/workout-cool-section-4-checkpoint-3`. **Upstream is `[gone]`** — the remote branch was deleted after squash-merge. `git diff origin/main..HEAD` is empty, so the branch carries no code unique to it: its seven historical commits (four checkpoints `1ff57ff`, `e3ebd43`, `df27c8d`, `d00eae6` plus three docs stamps `553d52a`, `966a338`, `8fd6ffe`) were collapsed into squash commit `8b348a5` on `origin/main`. Local `main` is one commit behind `origin/main` and has not been fast-forwarded yet.
- **§4 squash-merged to `origin/main` on 2026-05-15** as commit `8b348a5 feat(workout-cool §4): free-exercise-db exercise thumbnails` (PR #20). Squash bundles checkpoints 3–6: mapping proposal + curation (1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed), `media_path` route contracts, DB whitespace repair, thumbnail UI + `escapeHtml()` / `resolveExerciseMediaSrc()` helpers, and the `safe_media_path` Jinja filter. **§4 is shipped.**
- **Prior milestone on `main`**: §4 checkpoint 2 (`7a77315`, PR #19) — free-exercise-db assets vendored under `static/vendor/free-exercise-db/`.
- **Last verified pytest** (pre-merge, on the branch at `8fd6ffe`): full suite **1289 passed in 171.47s on 2026-05-14**. Re-verify after syncing local `main` to `8b348a5` and resolving the dirty `requirements.txt` pins.
- **Last verified E2E (Chromium)** (pre-merge): targeted plan+log **56 passed in 1.6m on 2026-05-14** (`e2e/workout-plan.spec.ts` + `e2e/workout-log.spec.ts`). Last full E2E baseline remains 414 passed / 1 failed on 2026-05-10; failure is `nav-dropdown.spec.ts:117` dark-mode toggle off-viewport at 1440 width — there is a **dirty local fix** in the working tree (uses `evaluate(() => toggle.click())` to bypass the off-viewport bounding box) that has not been committed yet.
- **Dirty working tree** (uncommitted, owner-decision required before sync): `.claude/settings.json` (local agent permissions), `.mcp.json` (deletion of project MCP config), `data/database.db` (runtime, never commit as source of truth), `e2e/nav-dropdown.spec.ts` (real test-stability fix — candidate for commit), `package.json` + `package-lock.json` (Playwright 1.58.1→1.60.0, sass 1.69→1.94, typescript 5.3→5.9, node engine 16→18 — candidate for commit), `requirements.txt` (Flask 3.1.1→3.1.3, pandas 2.2.3→3.0.3 pins — candidate for commit).

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow refit | complete through Tier 2 + T3.1 | Use [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) + this handover as active truth; treat `.claude/SHARED_PLAN.md` as local audit history only | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked by owner choice (Phase 1 + Stage 4 entry shipped; Option 1 confirmed 2026-05-13) | Treat as complete-for-now; proceed with non-fatigue work unless real logged weeks, owner labels, or explicit Phase 2 override arrive. No Phase 2 / `utils/fatigue.py` edits while parked. | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md), [docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md](fatigue_meter/STAGE4_PARKED_HANDOFF.md) |
| workout.cool integration | §3 + §4 + §5 all shipped on `origin/main`. §4 squash-merged 2026-05-15 as `8b348a5` (PR #20). Local `main` one commit behind `origin/main`; branch upstream `[gone]`. | (1) Classify and dispose of dirty working-tree files (see Current State); (2) fast-forward local `main` to `origin/main`; (3) run the deferred visual baseline pass per PLANNING §4.6 (desktop / tablet / mobile × light / dark × simple / advanced); (4) run `scripts/apply_free_exercise_db_mapping.py` against the canonical DB to populate `exercises.media_path` for the 108 confirmed/manual rows. | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md), [docs/workout_cool_integration/EXECUTION_LOG.md](workout_cool_integration/EXECUTION_LOG.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- **Dirty working-tree disposition.** Three categories awaiting owner call:
  - **Candidate for a follow-up commit**: `e2e/nav-dropdown.spec.ts` (fixes the off-viewport dark-mode toggle red tracked in PLANNING §2.7 + Issue #8 via `evaluate(() => toggle.click())`), `package.json` + `package-lock.json` (Playwright/sass/TS/node-engine bumps), `requirements.txt` (Flask/pandas/etc. version pins).
  - **Local-personal config**: `.claude/settings.json` (agent permissions list overhauled, MCP servers disabled). Owner decides whether to keep local-only or commit.
  - **Project config decision**: `.mcp.json` deletion (was project-level context7 + puppeteer MCP). Owner decides whether to commit the deletion.
  - **Do not commit**: `data/database.db` (runtime, per CLAUDE.md agent-must-not list).

## Blockers
- None for §4 ship (already merged). Post-merge sync is gated on the dirty-file disposition above.

## Next Safe Step
Use [docs/ACTIVE_DEVELOPMENT.md](ACTIVE_DEVELOPMENT.md) as the execution source of truth. §4 is **shipped on `origin/main` as `8b348a5`**. The next safe sequence: (1) resolve the dirty working-tree files per the Open Decisions table; (2) fast-forward local `main` to `origin/main` once the working tree is clean (or stashed); (3) run the deferred visual baseline pass per §4.6; (4) run `scripts/apply_free_exercise_db_mapping.py` against the canonical DB to populate `exercises.media_path` for the 108 confirmed/manual rows. Fatigue meter remains parked per `docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md` — no Phase 2 work, no `utils/fatigue.py` edits.
