# Active Development

This file is the execution source of truth for autonomous development sessions. Use it when it conflicts with older narrative planning text.

## Current Objective

workout.cool §4 (free-exercise-db thumbnails) is **fully shipped on `origin/main`**. PR #20 (squash `8b348a5`) landed the feature; PR #23 (`bfd9087`) landed the post-merge handoff refresh + nav-dropdown e2e stabilization + dependency pin bumps; PR #22 (`631b5f8`) landed the §4.6 visual-baseline spec + seed. No outstanding workout.cool work remains.

As of 2026-05-20, **no workstream is in-flight on `origin/main`**. All previously queued options are closed; the fatigue badge presentation polish (PR #28 `63c745d`) shipped on the same day as a small UI fix and did not reopen Stage 4:

- **Redesign post-P8 triage** — closed (10 of 11 shipped, #1 deferred by owner choice; verified 2026-05-19, PR #25).
- **phase5_3i_plan** — closed (accepted-as-shipped 2026-05-19; planning doc shipped `c0da18e` and deleted `635fa3e`, 5A–5H validation never ran but `12c90ac` refactors have held 5+ weeks under the 1160-test baseline; PR #25).
- **Fatigue meter** — Phase 1 done; Stage 4 still parked. PR #26 (2026-05-20) shipped a docs-only owner-approved synthetic-override / coherence pass section; PR #28 (2026-05-20) shipped a presentation-only badge restyle (template + SCSS + refreshed visual snapshots). Neither touched `utils/fatigue.py`, thresholds, scenario script, or real-data calibration.

Pick a new workstream from owner direction.

## Current Branch

`main`, in sync with `origin/main` at `63c745d`. Working tree dirty only on `data/database.db` (runtime; owner-approved kept dirty per `CLAUDE.md` agents-must-not list).

Recent history on `origin/main` (newest first):

- `63c745d` (2026-05-20) — **PR #28** `fix(fatigue-badge): compact, intentional widget on summary pages`. Presentation-only — 16 files changed, 184 insertions(+), 88 deletions(-). Restructures `templates/_fatigue_badge.html` (drops the `.card`/`.card-body` scaffold, switches to a `<section>` grid; promotes score + band to a readout row with eyebrow + info icon above; period label moves to the right column on desktop and stacks below on mobile). Rewrites `scss/_fatigue.scss` for a translucent surface harmonized with `.summary-frame` glass styling (score 2.1rem/700 tabular-nums; band rendered as a pill chip; empty-state pill is dashed-outline; tighter padding drops desktop badge height ~162px → ~86px). Rebuilds `static/css/bootstrap.custom.min.css` + source map. Refreshes 12 visual snapshots for weekly/session × {desktop,tablet,mobile} × {light,dark}. **No `utils/fatigue.py`, no thresholds, no APIs, no calibration, no scenario-script changes.** Existing Playwright selectors (`.fatigue-badge`, `.fatigue-badge__info-btn`, `.fatigue-badge__band`) preserved. Verification recorded in PR: pytest fatigue+summary 150 passed; `e2e/fatigue-stage4-smokes.spec.ts` 5 passed; `e2e/summary-pages.spec.ts` 20 passed; `e2e/visual.spec.ts` 42 passed (after intentional re-baseline).
- `330b2a9` (2026-05-20) — **PR #27** `docs: refresh handoff after fatigue synthetic override`. Docs-only — refreshed `ACTIVE_DEVELOPMENT.md` + `MASTER_HANDOVER.md` to reflect PR #25 + PR #26 on `origin/main` (current-SHA bump, recent-merges list, CI rows, fatigue-meter workstream-row update, 2026-05-20 override note in the "DO NOT REOPEN" block). No code, script, test, template, route, or runtime files touched.
- `2b34b50` (2026-05-20) — **PR #26** `docs(fatigue): record synthetic calibration override`. Docs-only — 1 file changed, 101 insertions(+), 0 deletions(-) in `docs/fatigue_meter/calibration-notes.md`. Reframes the existing 2026-05-11 generated calibration report as an owner-approved synthetic-override / coherence pass; flags `hard_4d` mismatch (intended `heavy`, computed `moderate` at 161.9 weekly); records hypothesis A (threshold drift) and B (scenario miscal, preferred) as proposals only. No `utils/fatigue.py`, no scenario script, no DB writes. CI 6/6 green.
- `1eebe54` (2026-05-19) — **PR #25** `docs: close stale handoff workstreams`. Docs-only — closes the redesign post-P8 triage and phase5_3i_plan rows after verifying both were already complete on `origin/main`. CI 6/6 green.
- `631b5f8` (2026-05-18) — **PR #22** `test(workout-cool §4.6): add visual-baseline thumbnail spec + seed`. Adds `e2e/visual-baseline-thumbnails.spec.ts` (18 tests) and `scripts/seed_visual_baseline.py`. `.gitignore` now ignores `e2e/artifacts/`. Screenshots are inspection artifacts only — no `toHaveScreenshot()` pixel baselines committed.
- `bfd9087` (2026-05-18) — **PR #23** `chore: post-section-4 handoff refresh + nav e2e + dependency pins`. Replaces closed PR #21. Rebased onto `origin/main` to drop the seven pre-squash §4 commits that had made the original branch `CONFLICTING`. Carries the nav-dropdown off-viewport fix and the Playwright/sass/TS/Node/Flask/pandas/click bumps.
- `8b348a5` (2026-05-15) — **PR #20** `feat(workout-cool §4): free-exercise-db exercise thumbnails`. Squash bundles checkpoints 3–6.
- `7a77315` (2026-05-14) — **PR #19** `feat(workout-cool §4): vendor free-exercise-db assets (checkpoint 2)`.

## Already Done

- §4 checkpoint 1: `media_path` schema, path validator, and `scripts/apply_free_exercise_db_mapping.py`.
- §4 checkpoint 2: `static/vendor/free-exercise-db/` assets, `LICENSE`, `NOTICE.md`, `VERSION`, `exercises.json`, 873 `0.jpg` images.
- §4 checkpoint 3: `scripts/map_free_exercise_db.py`, `data/free_exercise_db_mapping.csv` (raw 1,897 rows), `docs/workout_cool_integration/checkpoint3_coverage.md`.
- §4 checkpoint 4: `scripts/curate_free_exercise_db_mapping.py` (structural-equivalence rule) + curated `data/free_exercise_db_mapping.csv` (1784 auto / 98 confirmed / 10 manual / 5 rejected = 113 reviewed).
- §4 checkpoint 5: `_trim_exercise_name_whitespace` repair pass in `utils/db_initializer.py`; `media_path` surfaced in `/get_workout_plan` + `/get_workout_logs` JSON and in `utils/workout_log.py::get_workout_logs`; +4 trim tests + +4 route-contract tests.
- §4 checkpoint 6: `static/js/modules/exercise-helpers.js` with `escapeHtml()` + `resolveExerciseMediaSrc()`; workout-plan row renderer thumbnails; workout-log template `safe_media_path` Jinja filter; thumbnail CSS; +4 self-contained Playwright tests + +2 filter unit tests.
- §4 squash-merge (`8b348a5`) on 2026-05-15.
- Post-§4 follow-up (`bfd9087`) on 2026-05-18: nav e2e off-viewport fix + dependency pin refresh.
- §4.6 visual-baseline (`631b5f8`) on 2026-05-18: 18-test spec + seed.
- Apply-mapping: `exercises.media_path` populated for 108 rows (98 confirmed + 10 manual) in the main-checkout DB and the visual-baseline worktree DB.
- Fatigue meter Phase 1 / Stage 4 entry parked by owner choice (Option 1 confirmed 2026-05-13).
- Fatigue meter bounded synthetic-override / coherence pass (2026-05-20) — docs-only via PR #26 (`2b34b50`). Reuses 2026-05-11 generated report; `hard_4d` mismatch flagged; two hypotheses recorded as proposals only; no thresholds or scripts touched; Stage 4 still parked.
- Fatigue badge presentation polish (2026-05-20) — PR #28 (`63c745d`). Template + SCSS + built CSS + 12 refreshed visual snapshots. No `utils/fatigue.py`, no thresholds, no APIs, no calibration, no scenario-script changes; Stage 4 still parked.

## Next Task

No active workstream is currently in-flight on `origin/main`. As of 2026-05-20, no queued workstream remains — pick a new one from owner direction.

### Closed workstreams (do not reopen as "next task")

- **Redesign post-P8 triage** — closed 2026-05-19 after verification against `origin/main`. 10 of 11 issues shipped (#2 `9052337`, #3+#4 `0a41725`, #5 `7880618`, #6 `38b1f59`, #7+#8 `9b0c71b`, #9 `a95b067`, #10 `f6e39d6`, #11 `f7d9f12`); #1 (nav Backup link) deferred by owner choice. `debug/redesign_post_p8_issues_SESSION_STATE.md` is historical only.
- **phase5_3i_plan** — closed 2026-05-19 as accepted-as-shipped. Planning doc `docs/phase5_3i_plan.md` was authored 2026-04-15 (`c0da18e`) and deleted 2026-04-24 (`635fa3e`) with the rest of the spring-cleanup planning suite. The 5A–5H retroactive confidence-recovery validation gates never ran, but the underlying `12c90ac` refactors (3i-a..3i-h decompositions) have held under the test baseline for 5+ weeks (1160 passed; baseline rose from 934 at session-state writing) with no regression traced back to them. `debug/phase5_3i_plan_SESSION_STATE.md` is historical only. Re-open only if a concrete regression appears in one of the decomposed functions.

### Optional — workout.cool §4 follow-ups

None are blocking. Available if the owner wants final polish:

- Owner eyes-on review of the 18 visual-baseline screenshots at `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4/e2e/artifacts/visual-baseline/`. The spec asserts behavioural invariants (thumbnail count ≥ 1, src prefix, theme attr) but doesn't pixel-compare.
- Clean up the `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4` worktree. The remote branch is gone; local branch `test/visual-baseline-thumbnails` is unmerged-locally because the worktree holds it. Worktree still carries untracked `.venv` + `node_modules`. **Do not delete without owner approval.**
- Lock in `toHaveScreenshot()` pixel baselines once layout has settled (currently the spec captures PNGs for inspection only).

### Worktree disposition (open, awaiting owner decision)

- **`D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4`** — branch `test/visual-baseline-thumbnails` at `99910a4`. Holds untracked `.venv` + `node_modules` + the §4.6 inspection screenshots. Remote branch was deleted at PR #22 merge. Keep for faster re-runs vs remove to free disk. Owner has not decided. **Do not delete without explicit approval.**
- **`D:/development/Hypertrophy-Toolbox-v3-redesign-calm-glass`** — branch `redesign/calm-glass-2026` at `ba519df`, clean but behind `main`. No active workstream tied to it on the current handoff trail. Owner has not decided whether to revive, archive, or remove. **Do not delete without explicit approval.**

### Fatigue meter — DO NOT REOPEN

Fatigue is parked per `docs/fatigue_meter/STAGE4_PARKED_HANDOFF.md` (owner Option 1, 2026-05-13). No Phase 2 work, no `/fatigue` page, no API endpoints, no `utils/fatigue.py` edits, no `scripts/fatigue_calibration_report.py` scenario tuning. Reopen only if `workout_log` accumulates ≥4 labeled real weeks, or the owner explicitly overrides the parked state.

**2026-05-20 bounded override note.** The owner explicitly authorized **one** docs-only synthetic-override / coherence pass (PR #26 `2b34b50`). It produced no code, threshold, or script changes — only documentation in [calibration-notes.md](fatigue_meter/calibration-notes.md). That single override did not lift the parked state; the agent guidance above still applies. Hypothesis B (`scripts/fatigue_calibration_report.py::SCENARIOS["hard_4d"]` retune) is the preferred future follow-up if synthetic calibration is deepened later, but is NOT to be picked up without explicit owner go-ahead.

**2026-05-20 badge restyle note.** PR #28 (`63c745d`) shipped a **presentation-only** badge polish — `templates/_fatigue_badge.html` + `scss/_fatigue.scss` + built CSS + 12 refreshed visual snapshots. **No `utils/fatigue.py`, no thresholds, no APIs, no scenario script, no calibration.** Existing fatigue-stage4 Playwright selectors are preserved. Stage 4 remains parked; the parked-state guidance is unchanged.

## Agent Authority

Agents may, without asking the owner:

- Update docs that are stale relative to committed `origin/main` state.
- Run targeted pytest / Playwright checks.
- Continue from one listed task to the next after tests pass.

Agents must not:

- Reset, force-push, or otherwise discard working-tree state without owner approval.
- Commit `data/database.db` (runtime; agents-must-not list in CLAUDE.md).
- Delete or move the `Hypertrophy-Toolbox-v3-visual-baseline-s4` or `Hypertrophy-Toolbox-v3-redesign-calm-glass` worktrees without owner approval.
- Start fatigue-meter work.
- Start Phase 2 fatigue planning.
- Edit `utils/fatigue.py`.
- Tune `scripts/fatigue_calibration_report.py` SCENARIOS.
- Touch unrelated dirty files unless the active task requires it.

## Stop Conditions

Ask the owner only if:

- A destructive DB reset, branch reset, or file deletion is required.
- License / attribution status is unclear.
- A product behavior change would exceed the approved plan.
- Tests reveal a broad unrelated regression.
- The owner explicitly redirects the work.

Transport failures, idle stream stalls, or stale chat titles are not repo blockers. Start a fresh agent session and point it at this file.

## Required Checkpoint Closeout

Before calling a checkpoint done:

- Update `docs/MASTER_HANDOVER.md`.
- Update `docs/workout_cool_integration/EXECUTION_LOG.md` for workout.cool work; or the equivalent workstream log for other workstreams.
- Record tests run and results.
- Leave the diff commit-ready, with generated DB/runtime files excluded unless explicitly intended.
