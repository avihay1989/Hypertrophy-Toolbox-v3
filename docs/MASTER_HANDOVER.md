# Master Handover

*Committed canonical state. Curated manually after each milestone. New Claude instances read this first.*

## Current State
- **Branch**: local `main`, in sync with `origin/main` at `631b5f8`. Working tree dirty on `data/database.db` only (runtime; do not commit). No outstanding feature work on any branch.
- **Recent merges to `origin/main`** (newest first):
  - `631b5f8` — **PR #22** `test(workout-cool §4.6): add visual-baseline thumbnail spec + seed` (2026-05-18). Adds `e2e/visual-baseline-thumbnails.spec.ts` (18 tests: desktop / tablet / mobile × light / dark × simple / advanced for plan; desktop / tablet / mobile × light / dark for log) + `scripts/seed_visual_baseline.py` + `.gitignore` entry for `e2e/artifacts/`. Behavioural assertions only — screenshot PNGs are inspection artifacts, not committed pixel baselines.
  - `bfd9087` — **PR #23** `chore: post-section-4 handoff refresh + nav e2e + dependency pins` (2026-05-18). Replaces closed PR #21 (which was `CONFLICTING` because its branch carried the seven pre-squash §4 commits on top of the squash already on `main`). Rebased the three follow-ups onto `origin/main` and re-pushed. Carries: `e2e/nav-dropdown.spec.ts` off-viewport dark-mode-toggle fix via `evaluate(() => toggle.click())`; Playwright 1.58.1→1.60.0, sass 1.69→1.94, typescript 5.3→5.9, `@types/node` 20.10→20.19.32, node engine `>=16`→`>=18`; Flask 3.1.1→3.1.3, pandas 2.2.3→3.0.3, click 8.1.7→8.3.3 (XlsxWriter removed); handoff doc refresh.
  - `8b348a5` — **PR #20** `feat(workout-cool §4): free-exercise-db exercise thumbnails` (2026-05-15). Squash bundles checkpoints 3–6: mapping proposal + curation (1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed), `media_path` route contracts, DB whitespace repair, thumbnail UI + `escapeHtml()` / `resolveExerciseMediaSrc()` helpers, `safe_media_path` Jinja filter.
  - `7a77315` — **PR #19** `feat(workout-cool §4): vendor free-exercise-db assets (checkpoint 2)` (2026-05-14). `static/vendor/free-exercise-db/` assets, `LICENSE`, `NOTICE.md`, `VERSION`, `exercises.json`, 873 `0.jpg` images.
- **§4 is shipped and verified.** All four §4 deliverables (checkpoints 1–6 squash + visual baseline + dependency pins + nav e2e stabilization) are on `origin/main`.
- **Last verified CI on PR #23** (2026-05-18): 6/6 green — security-audit 23s, lint 26s, frontend-build 12s, dependency-check 28s, test 1m13s, e2e-smoke 1m29s. Confirms the Flask 3.1.3 / pandas 3.0.3 / click 8.3.3 / Playwright 1.60 / sass 1.94 / TS 5.9 / node 18 bumps are CI-clean.
- **Last verified CI on PR #22** (2026-05-18): 6/6 green — 1m53s total. Visual-baseline spec is not in the CI smoke job; reviewer runs it manually via `npx playwright test e2e/visual-baseline-thumbnails.spec.ts --project=chromium` (worktree run on 2026-05-18: 18 passed in 21.3s).
- **Local verifications on 2026-05-18**:
  - `tests/test_free_exercise_db_mapping.py` — 85 passed in 3.34s.
  - `e2e/visual-baseline-thumbnails.spec.ts` in the visual-baseline worktree — 18 passed in 21.3s, including a confirmed thumbnail asset (`/static/vendor/free-exercise-db/exercises/Lateral_Raise_-_With_Bands/0.jpg → 200`).
- **Apply-mapping status**: `exercises.media_path` populated for **108 rows** (98 confirmed + 10 manual) in the main-checkout DB and the visual-baseline worktree DB. The committed CSV (`data/free_exercise_db_mapping.csv`) is reproducible/idempotent; rerunning `scripts/apply_free_exercise_db_mapping.py` on a fresh DB will produce the same 108 rows.

## Active Workstreams
| Workstream | Status | Next safe step | Docs |
|---|---|---|---|
| Avi Lewis AI workflow refit | complete through Tier 2 + T3.1 | Use [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) + this handover as active truth; treat `.claude/SHARED_PLAN.md` as local audit history only | [docs/ai_workflow/INDEX.md](ai_workflow/INDEX.md) |
| Fatigue meter | parked by owner choice (Phase 1 + Stage 4 entry shipped; Option 1 confirmed 2026-05-13) | Treat as complete-for-now; proceed with non-fatigue work unless real logged weeks, owner labels, or explicit Phase 2 override arrive. No Phase 2 / `utils/fatigue.py` edits while parked. | [docs/fatigue_meter/PLANNING.md](fatigue_meter/PLANNING.md), [docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md](fatigue_meter/STAGE4_PARKED_HANDOFF.md) |
| workout.cool integration | §3 + §4 + §4.6 + §5 all shipped on `origin/main`. §4 squash-merge `8b348a5` (PR #20), post-§4 follow-up `bfd9087` (PR #23), visual baseline `631b5f8` (PR #22). | (1) Optional: owner eyes-on review of the 18 visual-baseline screenshots in `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4/e2e/artifacts/visual-baseline/`. (2) Optional: clean up the `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4` worktree (it served its purpose; still holds `.venv` + `node_modules` + screenshots, branch `test/visual-baseline-thumbnails` is merged on remote). (3) Optional: lock in pixel baselines later via `toHaveScreenshot()` once layout has settled — currently the spec only asserts behavioural invariants. | [docs/workout_cool_integration/PLANNING.md](workout_cool_integration/PLANNING.md), [docs/workout_cool_integration/EXECUTION_LOG.md](workout_cool_integration/EXECUTION_LOG.md) |
| Redesign post-P8 triage | #6 done; 5 issues remaining | #7 + #8 | local-only `debug/redesign_post_p8_issues_SESSION_STATE.md` |
| phase5_3i_plan | paused mid-draft | Resume from session-state file | local-only `debug/phase5_3i_plan_SESSION_STATE.md` |

## Open Decisions
- **None blocking.** Working tree dirty only on `data/database.db` (runtime, owner-approved kept dirty).
- **Visual-baseline worktree disposition.** [D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4](D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4) still has `test/visual-baseline-thumbnails` checked out locally and untracked `.venv` + `node_modules` + screenshots. The remote branch was deleted by `gh pr merge --delete-branch`. Decide whether to remove the worktree (frees disk, requires re-install for future re-runs) or keep it (faster re-runs, holds local venv/node_modules).

## Blockers
- None.

## Next Safe Step
Use [docs/ACTIVE_DEVELOPMENT.md](ACTIVE_DEVELOPMENT.md) as the execution source of truth. With workout.cool §4 fully shipped, the queue defaults to the redesign post-P8 triage (#7 + #8 next) unless the owner redirects. Fatigue meter remains parked per `docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md` — no Phase 2 work, no `utils/fatigue.py` edits.
