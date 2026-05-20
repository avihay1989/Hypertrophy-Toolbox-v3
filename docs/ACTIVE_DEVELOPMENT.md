# Active Development

This file is the execution source of truth for autonomous development sessions. Use it when it conflicts with older narrative planning text.

## Current Objective

**Active workstream (2026-05-20, later session): Body Composition Issue #21 — conservative backend-first slice (uncommitted).** A pure-formula module, a new DB migration + registration, and focused tests are in the working tree on local `main`. UI / navbar / JS / chart / Playwright are intentionally **not** built yet — that is the deferred Issue #21 second slice. Source of truth: [`docs/body_composition/development_issues.md`](body_composition/development_issues.md). Detail block in *Next Task → Body Composition Issue #21*.

workout.cool §4 (free-exercise-db thumbnails) is **fully shipped on `origin/main`**. PR #20 (squash `8b348a5`) landed the feature; PR #23 (`bfd9087`) landed the post-merge handoff refresh + nav-dropdown e2e stabilization + dependency pin bumps; PR #22 (`631b5f8`) landed the §4.6 visual-baseline spec + seed. No outstanding workout.cool infrastructure work remains. One optional content follow-up remains for §5 reference videos: curated YouTube IDs have not been populated, so every exercise uses the search fallback until `data/youtube_curated_top_n.csv` is filled and `scripts/apply_youtube_curated.py` is run. See [docs/workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md).

As of 2026-05-20 (later in the day), the fatigue meter workstream has been **closed via an owner-approved Stage 4 calibration review** that walked PLANNING.md §4.1 → §4.3 to a no-change decision. This is a docs-only close — `utils/fatigue.py`, `tests/test_fatigue.py`, and `scripts/fatigue_calibration_report.py` were **not touched**. After this close, no workstream remains in-flight.

- **Redesign post-P8 triage** — closed (10 of 11 shipped, #1 deferred by owner choice; verified 2026-05-19, PR #25).
- **phase5_3i_plan** — closed (accepted-as-shipped 2026-05-19; planning doc shipped `c0da18e` and deleted `635fa3e`, 5A–5H validation never ran but `12c90ac` refactors have held 5+ weeks under the 1160-test baseline; PR #25).
- **Fatigue meter** — Phase 1 done; **Stage 4 closed 2026-05-20 by owner-approved felt-label calibration review with no threshold changes**. Owner labeled 5 anchors (1 real logged week W20 from the now-populated `workout_log` + 4 generator scenarios from `generated-calibration-report.md`); 4 of 5 felt labels agreed with the computed bands; the lone disagreement was on the `hard_4d` synthetic generator scenario only, so PLANNING.md §4.2's "≥2 disagreements" bar was not met. `utils/fatigue.py` thresholds remain the §24.B defaults. STAGE4_PARKED_HANDOFF.md is now superseded; the authoritative status lives in `calibration-notes.md` "2026-05-20 — owner-approved felt-label calibration review (Stage 4 close)". Phase 2 entry remains a separate owner decision.
  - Earlier in the same day: PR #26 (2026-05-20) shipped a docs-only owner-approved synthetic-override / coherence pass section; PR #28 (2026-05-20) shipped a presentation-only badge restyle (template + SCSS + refreshed visual snapshots). Both are preserved.

Pick a new workstream from owner direction.

## Owner-Approved Next Workstream Queue

Recorded 2026-05-20 so future agents do not need to re-evaluate the full docs
state before choosing what to do next.

1. **Start Body Composition (Issue #21)** — recommended next product
   workstream. It is the only open, fully-specced feature with no blockers:
   standalone `/body_composition` tab, tape inputs, U.S. Navy + BMI BFP,
   longitudinal snapshots, new blueprint/template/utils module/DB table/tests.
   Source of truth:
   [`docs/body_composition/development_issues.md`](body_composition/development_issues.md).
   Start with a conservative backend-first slice: formula module + tests,
   idempotent DB migration, route skeleton, then UI/JS/E2E.
2. **Keep Profile-page body-composition hooks deferred** until
   `/body_composition` ships and snapshots are routinely captured. This covers
   Issue #18's Lean Mass bodyweight-tile sub-line and Issue #17's
   `"Body fat: X % · {ACE band}"` line.
3. **Treat workout.cool §5 YouTube curation as optional content work.** The
   modal/search-fallback infrastructure is shipped; curated IDs are not
   populated. Do this only if the current fallback feels too unfinished.
4. **Do not reopen fatigue work.** Phase 1 is closed; Stage 4 is closed with no
   threshold changes. No Phase 2 planning or fatigue edits without fresh owner
   override.
5. **Leave worktree disposition as an owner/admin decision.** Do not delete or
   move `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4` or
   `D:/development/Hypertrophy-Toolbox-v3-redesign-calm-glass` without explicit
   owner approval.

## Current Branch

`main`, in sync with `origin/main` at `63c745d`. Working tree has the uncommitted Body Composition Issue #21 first-slice diff described below, plus `data/database.db` runtime dirt (owner-approved kept dirty per `CLAUDE.md` agents-must-not list; do not commit).

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

### In-flight (uncommitted) — Body Composition Issue #21, first slice

Backend-only slice landed in the working tree on local `main`, 2026-05-20. Files touched:

- **New** `utils/body_fat.py` — pure-function module with `compute_navy(...)`, `compute_bmi(...)`, `ace_category(bfp, gender)`, `jackson_pollock_ideal(age, gender)`. Carries the **"must match JS mirror"** module-level comment from the Issue #17 contract. Server-side validation (range checks + log-domain rejection) raises `ValueError`; route layer (not built here) will translate into structured 4xx responses.
- **New** `tests/test_body_fat.py` — 42 cases. Coverage: Navy male + female typical lifters, Navy log-domain rejection (both sexes), male-rejects-hip, female-requires-hip, out-of-range height, invalid gender; BMI adult male / adult female / boy <18 / girl <18 + age-18 boundary; ACE male + female boundary rows (parametrized 20 rows) + low-value clamp; Jackson & Pollock anchor rows + interpolation male/female + age clamp below 20 / above 55 + invalid gender.
- **Edit** `utils/database.py` — added `add_body_composition_snapshots_table()` migration. Creates the `body_composition_snapshots` table exactly per [`docs/body_composition/development_issues.md`](body_composition/development_issues.md) (14 columns; 6 NOT NULL: `captured_at`, `bodyweight_kg`, `height_cm`, `age_years`, `gender`, `bfp_bmi`) + `idx_body_composition_snapshots_captured_at` descending index. Idempotent (`CREATE TABLE/INDEX IF NOT EXISTS`). DatabaseHandler pattern only.
- **Edit** `app.py` — imports + calls `add_body_composition_snapshots_table()` in the startup sequence immediately after `add_user_profile_tables()`. Also registered in the `/erase-data` drop-list (between `user_profile` and `user_selection`) and in the post-drop re-init block.
- **Edit** `tests/conftest.py` — imports the new migration, calls it in `_initialize_test_database()` (between `add_user_profile_tables()` and `initialize_exercise_order()`), adds `body_composition_snapshots` to the inner `erase_data()` drop-list, and adds it to the `clean_db` fixture's per-test DELETE list.
- **New** `tests/test_db_migration.py` — 7 cases. Coverage: expected columns (incl. NOT NULL set), index existence + indexed column, idempotent re-run, accepts Navy-style insert, accepts BMI-only (tape-blank) insert, rejects missing NOT NULL, `/erase-data` recreates table + index.
- **New** `docs/body_composition/OPUS_START_PROMPT.md` — reusable prompt that scoped this workstream to the backend-first slice and preserved the fatigue / profile-hook / YouTube-curation guardrails.

**Verification (2026-05-20):**

- Targeted (initial slice run): `.venv/Scripts/python.exe -m pytest tests/test_body_fat.py tests/test_db_migration.py -q` → **49 passed in 1.60s**.
- Targeted (review-pass rerun, 2026-05-20 later): `.venv/Scripts/python.exe -m pytest tests/test_body_fat.py tests/test_db_migration.py -q` → **49 passed in 1.34s**. Review pass also fixed a docs-only off-by-one ("5 NOT NULL" → "6 NOT NULL") in this section; no code/test/migration changes, so the subset/full-pytest numbers below were not re-run.
- Startup-touching subset: `.venv/Scripts/python.exe -m pytest tests/test_body_fat.py tests/test_db_migration.py tests/test_database_user_profile.py tests/test_harness_isolation.py tests/test_user_profile_routes.py tests/test_program_backup.py -q` → **115 passed in 15.18s**.
- Full pytest: `.venv/Scripts/python.exe -m pytest tests/ -q` → **1354 passed in 160.93s** (no regressions vs. pre-slice baseline of 1305 currently-passing tests on local `main`; 49 new tests on top of that).
- Playwright not yet run (intentional — Issue #21 second slice is not built).

**Explicitly NOT built in this slice (deferred to Issue #21 second slice):**

- `routes/body_composition.py` blueprint and the four endpoints (`GET /body_composition`, `POST/GET/DELETE /api/body_composition/snapshot[s]`).
- `templates/body_composition.html` + nav link in `templates/base.html`.
- `static/js/modules/body-composition.js` JS mirror of the four formulas.
- `static/css/pages-body-composition.css`.
- `e2e/body-composition.spec.ts`.
- Profile-page display hooks (Issue #17 / #18 sub-lines) — already deferred to a follow-up.

Working tree is dirty only on the files listed above plus `data/database.db` (runtime, kept dirty by owner policy) and `docs/ACTIVE_DEVELOPMENT.md` / `docs/MASTER_HANDOVER.md` (this update). `utils/fatigue.py`, `tests/test_fatigue.py`, and `scripts/fatigue_calibration_report.py` were **not touched**.

### Workstream queue (post first-slice)

No other active workstream is currently in-flight on `origin/main`. Body Composition Issue #21 second slice (UI / blueprint / JS / chart / E2E) is the natural next step once the first slice ships.

### Closed workstreams (do not reopen as "next task")

- **Redesign post-P8 triage** — closed 2026-05-19 after verification against `origin/main`. 10 of 11 issues shipped (#2 `9052337`, #3+#4 `0a41725`, #5 `7880618`, #6 `38b1f59`, #7+#8 `9b0c71b`, #9 `a95b067`, #10 `f6e39d6`, #11 `f7d9f12`); #1 (nav Backup link) deferred by owner choice. `debug/redesign_post_p8_issues_SESSION_STATE.md` is historical only.
- **phase5_3i_plan** — closed 2026-05-19 as accepted-as-shipped. Planning doc `docs/phase5_3i_plan.md` was authored 2026-04-15 (`c0da18e`) and deleted 2026-04-24 (`635fa3e`) with the rest of the spring-cleanup planning suite. The 5A–5H retroactive confidence-recovery validation gates never ran, but the underlying `12c90ac` refactors (3i-a..3i-h decompositions) have held under the test baseline for 5+ weeks (1160 passed; baseline rose from 934 at session-state writing) with no regression traced back to them. `debug/phase5_3i_plan_SESSION_STATE.md` is historical only. Re-open only if a concrete regression appears in one of the decomposed functions.

### Optional — workout.cool §4 follow-ups

None are blocking. Available if the owner wants final polish:

- Owner eyes-on review of the 18 visual-baseline screenshots at `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4/e2e/artifacts/visual-baseline/`. The spec asserts behavioural invariants (thumbnail count ≥ 1, src prefix, theme attr) but doesn't pixel-compare.
- Clean up the `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4` worktree. The remote branch is gone; local branch `test/visual-baseline-thumbnails` is unmerged-locally because the worktree holds it. Worktree still carries untracked `.venv` + `node_modules`. **Do not delete without owner approval.**
- Lock in `toHaveScreenshot()` pixel baselines once layout has settled (currently the spec captures PNGs for inspection only).

### Optional — workout.cool §5 reference-video content

- Curate a starter batch of YouTube IDs in `data/youtube_curated_top_n.csv` and
  apply with `scripts/apply_youtube_curated.py`. Until this is done, the §5 modal
  is expected to show the search fallback for every exercise. Source of truth:
  [docs/workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md).
- Consider a small UX polish if the fallback feels misleading: clearer tooltip
  text for uncurated rows, a distinct search icon for uncurated rows, or hiding
  the play button unless a curated ID exists.

### Worktree disposition (open, awaiting owner decision)

- **`D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4`** — branch `test/visual-baseline-thumbnails` at `99910a4`. Holds untracked `.venv` + `node_modules` + the §4.6 inspection screenshots. Remote branch was deleted at PR #22 merge. Keep for faster re-runs vs remove to free disk. Owner has not decided. **Do not delete without explicit approval.**
- **`D:/development/Hypertrophy-Toolbox-v3-redesign-calm-glass`** — branch `redesign/calm-glass-2026` at `ba519df`, clean but behind `main`. No active workstream tied to it on the current handoff trail. Owner has not decided whether to revive, archive, or remove. **Do not delete without explicit approval.**

### Fatigue meter — DO NOT REOPEN (status updated 2026-05-20)

Phase 1 is the working state. **Stage 4 was closed by owner-approved felt-label calibration review on 2026-05-20 with no threshold changes.** STAGE4_PARKED_HANDOFF.md is superseded; `calibration-notes.md` is authoritative.

Do not, without an explicit new owner override:

- Edit `utils/fatigue.py` (thresholds remain §24.B defaults).
- Edit `tests/test_fatigue.py` boundary-classification tests.
- Tune `scripts/fatigue_calibration_report.py::SCENARIOS` (Hypothesis B retune of `hard_4d` is a documented-not-applied deferred follow-up).
- Start Phase 2 work, add a `/fatigue` page, or add new API endpoints.

Re-open Stage 4 review only if `workout_log` accumulates ≥4 representative real weeks with varied stress shapes and the owner requests a re-walk, or the owner explicitly overrides this status.

**Earlier 2026-05-20 history (preserved):**

- **Bounded synthetic-override / coherence pass** (PR #26 `2b34b50`) — docs-only addition to `calibration-notes.md`. No code or script changes.
- **Badge restyle** (PR #28 `63c745d`) — presentation-only `templates/_fatigue_badge.html` + `scss/_fatigue.scss` + built CSS + 12 refreshed visual snapshots. No fatigue math / threshold / API changes.
- **Stage 4 close** (this doc-only walk, later on 2026-05-20) — owner labeled 5 anchors (1 real W20 + 4 generated); 4/5 agreed; 1 isolated disagreement on `hard_4d` generated scenario was treated as scenario under-shoot per Hypothesis B, not as threshold drift. No `utils/fatigue.py` change.

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
