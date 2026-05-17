# Active Development

This file is the execution source of truth for autonomous development sessions. Use it when it conflicts with older narrative planning text.

## Current Objective

§4 free-exercise-db thumbnails is **shipped on `origin/main`** as squash-merge `8b348a5` (PR #20, 2026-05-15). Remaining work is post-merge housekeeping: dispose of the three remaining dirty files, sync local `main`, decide whether to keep the two local follow-up commits, run the deferred visual baseline pass, then apply the curated mapping to the canonical DB.

## Current Branch

`feat/workout-cool-section-4-checkpoint-3`. **Upstream `[gone]`** — remote branch was deleted post-merge. There is **no unmerged workout.cool feature code**: the seven historical §4 commits have empty net diff vs `origin/main` (they were squashed into `8b348a5`). The branch now carries two local follow-up commits on top of that empty diff. Local `main` is one commit behind `origin/main` (missing `8b348a5`).

Known history:

- `origin/main` at `8b348a5` (2026-05-15): **workout.cool §4 squash-merge — PR #20**. Bundles checkpoints 3–6 (mapping proposal + curation, `media_path` route contracts, DB whitespace repair, thumbnail UI + helpers, `safe_media_path` Jinja filter).
- `origin/main` at `7a77315` (prior): workout.cool §4 checkpoint 2, free-exercise-db assets vendored (PR #19).
- Branch commits `1ff57ff`, `e3ebd43`, `df27c8d`, `553d52a`, `d00eae6`, `966a338`, `8fd6ffe` were the per-checkpoint development trail; all collapsed into `8b348a5` and no longer differ from `origin/main`.
- Local follow-ups on top of the squashed feature work:
  - `3919d82 docs: update handoff for workout.cool §4 squash merge` — first post-squash refresh of `docs/MASTER_HANDOVER.md` + `docs/ACTIVE_DEVELOPMENT.md`.
  - `e135ff5 test: stabilize nav dropdown e2e and refresh dependency pins` — `e2e/nav-dropdown.spec.ts` `evaluate(() => toggle.click())` fix for the off-viewport dark-mode toggle (PLANNING §2.7 / Issue #8) plus Playwright 1.58.1→1.60.0, sass 1.69→1.94, typescript 5.3→5.9, `@types/node` 20.10→20.19.32, node engine `>=16`→`>=18`, Flask 3.1.1→3.1.3, pandas 2.2.3→3.0.3, click 8.1.7→8.3.3 (XlsxWriter removed).

## Already Done

- §4 checkpoint 1: `media_path` schema, path validator, and `scripts/apply_free_exercise_db_mapping.py`.
- §4 checkpoint 2: `static/vendor/free-exercise-db/` assets, `LICENSE`, `NOTICE.md`, `VERSION`, `exercises.json`, and 873 `0.jpg` images.
- §4 checkpoint 3 (shipped at `1ff57ff`): `scripts/map_free_exercise_db.py`, `data/free_exercise_db_mapping.csv` (raw 1,897 rows), and `docs/workout_cool_integration/checkpoint3_coverage.md`.
- §4 checkpoint 4 (shipped at `e3ebd43`): `scripts/curate_free_exercise_db_mapping.py` (structural-equivalence rule) + curated `data/free_exercise_db_mapping.csv` (1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed) + stale-assertion fix + bundled fatigue Stage 4 parked-decision docs.
- §4 checkpoint 5 (shipped at `df27c8d`): `_trim_exercise_name_whitespace` repair pass in `utils/db_initializer.py` (path (a)); `media_path` surfaced in `/get_workout_plan` + `/get_workout_logs` JSON and in `utils/workout_log.py::get_workout_logs` (workout-log page render); +4 trim tests in `tests/test_priority0_filters.py`, +4 route-contract tests in `tests/test_free_exercise_db_mapping.py::TestRouteContracts`.
- §4 checkpoint 6 (shipped at `d00eae6`): new `static/js/modules/exercise-helpers.js` with `escapeHtml()` + `resolveExerciseMediaSrc()`; workout-plan row renderer routes interpolations through `escapeHtml()` and renders a 32×32 thumbnail when `media_path` is set; workout-log template server-renders the same thumbnail gated by the new `safe_media_path` Jinja filter (registered in `app.py` + `tests/conftest.py`) that revalidates §4.3 shape rules at render time per PLANNING §4.4 defense-in-depth; thumbnail CSS in `static/css/components.css` + advanced-view override in `static/css/pages-workout-plan.css`; +4 self-contained Playwright tests in `e2e/workout-plan.spec.ts` (mock rows via dynamic `import('/static/js/modules/workout-plan.js')` + `updateWorkoutPlanTable([row])` — no live-DB dependency); +2 filter unit tests in `tests/test_free_exercise_db_mapping.py::TestSafeMediaPathJinjaFilter`. Full pytest: 1289 passed in 171.47s. Plan+log E2E: 56 passed in 1.6m.
- Fatigue meter Phase 1 / Stage 4 entry is parked by owner choice (Option 1 confirmed 2026-05-13). Do not work on fatigue unless explicit reopen criteria are met.

## Next Task

§4 is **shipped on `origin/main`**. PR creation is not part of the remaining work. The next safe sequence is:

### Step 1 — Owner decision on the three remaining dirty files

The previously-listed `e2e/nav-dropdown.spec.ts`, `package.json`, `package-lock.json`, and `requirements.txt` are now committed in `e135ff5` and are no longer in the dirty set. Three entries remain:

- **Local-personal config**: `.claude/settings.json` (agent permission list overhauled, MCP servers disabled). Owner decides whether to keep this local-only (revert, or split out via `.claude/settings.local.json`) or commit it.
- **Project config decision**: `.mcp.json` deletion (was the project-level context7 + puppeteer MCP). Owner decides whether to commit the deletion.
- **Do not commit**: `data/database.db` (runtime; agents-must-not list in CLAUDE.md).

Resolve each via stash, revert, or commit before moving on. Agents must not reset, force-push, or otherwise discard these without owner approval.

### Step 2 — Sync local `main` to `origin/main`

Once the dirty set is resolved (committed, stashed, or reverted), fast-forward local `main` from `7a77315` to `8b348a5`. Do not force-push; do not reset hard while there are uncommitted local changes.

### Step 3 — Decide whether to keep the two local follow-up commits

After local `main` reaches `8b348a5`, owner decides whether `3919d82` (handoff docs refresh) and `e135ff5` (nav e2e + dependency pins) should land on local `main`. Options: cherry-pick one or both onto `main`, open a small follow-up PR carrying them, or drop them entirely. Neither is required for §4 shipped state.

### Step 4 — Visual baseline pass (deferred from §4.6)

PLANNING §4.6 calls for desktop / tablet / mobile × light / dark × simple / advanced snapshots, plus the workout-log embed of `safe_media_path`. Run as a dedicated visual snapshot session against the merged `main`.

### Step 5 — Apply the curated mappings on `main`

Run `scripts/apply_free_exercise_db_mapping.py` against whichever environment carries the canonical DB. The committed CSV is reproducible and idempotent; the apply step populates `exercises.media_path` for the 108 confirmed/manual rows. Verify with targeted tests around workout plan/log thumbnails (`e2e/workout-plan.spec.ts`, `e2e/workout-log.spec.ts`) and `tests/test_free_exercise_db_mapping.py`.

### Fatigue meter — DO NOT REOPEN

Fatigue is parked per `docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md` (owner Option 1, 2026-05-13). No Phase 2 work, no `/fatigue` page, no API endpoints, no `utils/fatigue.py` edits. Reopen only if `workout_log` accumulates ≥4 labeled real weeks, or the owner explicitly overrides the parked state.

## Agent Authority

Agents may, without asking the owner:

- Update docs that are stale relative to committed `origin/main` state.
- Run targeted pytest / Playwright checks.
- Continue from one listed task to the next after tests pass.

Agents must not:

- Reset, force-push, or otherwise discard the dirty working tree without owner approval.
- Fast-forward local `main` while the working tree carries uncommitted code changes (the merge would surface confusing conflicts or silently shadow the local fix).
- Mutate committed `data/database.db` as source of truth (the Step 4 apply-mapping run against the canonical DB is the only sanctioned write, and it must be against the chosen canonical environment).
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
- The mapping policy cannot be resolved by the rules above.
- The owner explicitly redirects the work.

Transport failures, idle stream stalls, or stale chat titles are not repo blockers. Start a fresh agent session and point it at this file.

## Required Checkpoint Closeout

Before calling a checkpoint done:

- Update `docs/MASTER_HANDOVER.md`.
- Update `docs/workout_cool_integration/EXECUTION_LOG.md`.
- Record tests run and results.
- Leave the diff commit-ready, with generated DB/runtime files excluded unless explicitly intended.
