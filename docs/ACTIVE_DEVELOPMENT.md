# Active Development

This file is the execution source of truth for autonomous development sessions. Use it when it conflicts with older narrative planning text.

## Current Objective

**As of 2026-05-29 (latest session): local `main` is in sync with `origin/main` (0 commits ahead) after pushing `df9b6f9` (movement_pattern cleanup, 2026-05-25), `f2cdc23` (Stage 4 calibration observer tooling, 2026-05-29), and this handover sync on top of the prior `origin/main` tip `39193f6`. Fatigue Meter Phase 2 Path 1 shipped 2026-05-23 via PR #35 (`d5b80bf`); Stage 3 verify-suite gate closed 2026-05-24 (`1a93f66`); Stage 4 calibration window OPEN 2026-05-24, earliest close 2026-06-07 — the observer is ready and read-only but stays blocked until real `workout_log` data exists (empty as of 2026-05-29).** Phase 2 Stage 0 lock landed via PR #33 (`24c6f46`) and Stage 1 close via PR #34 (`be22286`); planning extracted earlier in `f01ccb9`. The 2026-05-23 hygiene session, the six in-flight scope commits, the KI-001 / KI-009 / §4.6 baseline / §5 expansion follow-ups, and the YouTube curation closure all landed before Phase 2 work began. The lead-up: Body Composition Issue #21 fully shipped via PR #31 (squash `20b4b24`, 2026-05-20) and hardened in PR #32 (`94482d7`, 2026-05-21, `captured_at` ISO validation + JS↔Python parity test); response-contract exceptions migrated 2026-05-21 (`cbf745a`); §5 YouTube curation landed in two passes — `cf21191` (2026-05-22, 36 rows) + `ff244aa` (2026-05-23, +20 rows → **56 cumulative**, curation closed by diminishing returns). 2026-05-23 also landed the six in-flight scopes as separate commits (Profile #17/#18 hooks `de3e4d0`; workout-cool §3.6 Profile bodymap `18ad223`; navbar hover dropdowns `ef475cc`; navbar icon accents + motion `89561df`; Body Composition visual baselines `40d7dd2`; ui-hardening spec + Known Issues table `0ae5b39`), the docs-only hygiene commit, the KI-001 filter-cache deletion (`6d87284`), the KI-009 xlsxwriter exporter (`4bbe06b`) + docs (`f944366`), and the §4.6 visual-baseline `toHaveScreenshot()` lock-in (`b5b8c7a`). No active workstream remains in-flight.

workout.cool §4 (free-exercise-db thumbnails) is **fully shipped on `origin/main`**. PR #20 (squash `8b348a5`) landed the feature; PR #23 (`bfd9087`) landed the post-merge handoff refresh + nav-dropdown e2e stabilization + dependency pin bumps; PR #22 (`631b5f8`) landed the §4.6 visual-baseline spec + seed. workout.cool §5 reference-video infrastructure shipped 2026-05-11; the curated content shipped in two passes — `cf21191` (2026-05-22, 36 rows) + `ff244aa` (2026-05-23, +20 rows → **56 cumulative**). Curation is **closed by diminishing returns** (only 1 of the remaining ~1,841 uncurated rows has >1 actual uses; long-tail uses the search fallback by design). workout.cool §3.6 Profile coverage bodymap was previously "deferred indefinitely"; it shipped locally on 2026-05-23 (`18ad223`).

- **Redesign post-P8 triage** — closed (10 of 11 shipped, #1 deferred by owner choice; verified 2026-05-19, PR #25).
- **phase5_3i_plan** — closed (accepted-as-shipped 2026-05-19; planning doc shipped `c0da18e` and deleted `635fa3e`, 5A–5H validation never ran but `12c90ac` refactors have held 5+ weeks under the 1160-test baseline; PR #25).
- **Fatigue meter** — Phase 1 shipped; Phase 1 Stage 4 closed 2026-05-20 (owner-approved felt-label review, no threshold changes — `calibration-notes.md` authoritative). **Phase 2 Path 1 shipped 2026-05-23 via PR #35 (`d5b80bf`)** (per-muscle accumulator, period selector, dedicated `/fatigue` route, dual planned + logged bars, two SFR cards, nav link, badge → page link; 91 new pytest cases for total 1442; 8/8 `e2e/fatigue.spec.ts` green). Stage 0 lock PR #33 (`24c6f46`), Stage 1 close PR #34 (`be22286`). **Phase 2 Stage 3 verify-suite gate closed 2026-05-24 (`1a93f66`)** — 13 + 17 reds on full Chromium match the pre-existing baseline exactly with zero new Stage-2 reds. **Phase 2 Stage 4 calibration window OPEN 2026-05-24**, earliest close 2026-06-07 (≥2 weeks real use). Source of truth: [`docs/fatigue_meter/PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md).
  - 2026-05-20 history preserved: PR #26 (`2b34b50`) docs-only synthetic-override / coherence pass; PR #28 (`63c745d`) presentation-only badge restyle.

Pick a new workstream from owner direction.

## Owner-Approved Next Workstream Queue

Recorded 2026-05-20 so future agents do not need to re-evaluate the full docs
state before choosing what to do next.

1. **Body Composition (Issue #21) — DONE.** Shipped via PR #31 (`20b4b24`) +
   PR #32 (`94482d7`). Source of truth:
   [`docs/body_composition/development_issues.md`](body_composition/development_issues.md).
2. **Profile-page body-composition hooks (Issues #17/#18) — DONE.** Shipped
   2026-05-23 via local commit `de3e4d0`. Display-only BFP/ACE line + Lean
   Mass sub-line on the Profile insights card, read from the latest
   `body_composition_snapshots` row.
3. **workout.cool §5 YouTube curation — DONE (closed by diminishing returns
   2026-05-23).** `cf21191` (2026-05-22) populated 36 curated rows; `ff244aa`
   (2026-05-23) added 20 more for **56 cumulative**. Usage triage showed all
   remaining ~1,841 uncurated rows sit at 0–1 actual uses except one edge
   case, so the search fallback handles the long tail by design. Do not
   expand further without owner-vetted IDs. See
   [`docs/workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md`](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md)
   "Curation Closed".
4. **Fatigue Meter Phase 2 Stage 4 — TRACKING (window OPEN).** Phase 2 Path 1
   shipped 2026-05-23 (PR #35 `d5b80bf`); Stage 3 verify-suite gate closed
   2026-05-24 (`1a93f66`); Stage 4 calibration window open 2026-05-24, earliest
   close 2026-06-07 (≥2 weeks real use). **No per-muscle threshold tuning
   without ≥2 same-direction real-use disagreements** — synthetic-generator-only
   mismatches do not justify changes (Phase 1 `hard_4d` precedent). Do not edit
   `utils/fatigue.py::MUSCLE_VOLUME_LANDMARKS` / `SESSION_FATIGUE_BANDS` /
   `WEEKLY_FATIGUE_BANDS`, do not edit `tests/test_fatigue.py` boundary tests,
   do not tune `scripts/fatigue_calibration_report.py::SCENARIOS`. Source of
   truth: [`docs/fatigue_meter/PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md)
   Stage 4 + §10.
5. **Worktree disposition — DONE.** Closed 2026-05-23 via `21859a1`. Both old
   worktree paths (`Hypertrophy-Toolbox-v3-visual-baseline-s4`,
   `Hypertrophy-Toolbox-v3-redesign-calm-glass`) were already absent from
   `D:/development/` and neither was registered in `git worktree list`. Stale
   branch refs (`test/visual-baseline-thumbnails` local + remote;
   `origin/redesign/calm-glass-2026`) deleted with owner approval. Source of
   truth: [`docs/LEFTOVERS_BY_PRIORITY.md §6`](LEFTOVERS_BY_PRIORITY.md).

## Current Branch

`main`, in sync with `origin/main` (0 commits ahead) at the 2026-05-29 handover-sync commit. This sync pushed `df9b6f9` (movement_pattern cleanup, 2026-05-25), `f2cdc23` (Stage 4 observer tooling, 2026-05-29), and this handover sync on top of the prior `origin/main` tip `39193f6`. Working tree has only `data/database.db` runtime dirt (owner-approved kept dirty per `CLAUDE.md` agents-must-not list; do not commit). Feature branch `feat/body-composition-issue-21` was deleted locally and on the remote at the PR #31 merge; feature branches `feat/fatigue-meter-phase-2` and `feat/fatigue-meter-phase-2-stage-2` were merged via PR #34 and PR #35 respectively.

Recent local / `main` history (newest first):

- 2026-05-30 — **chore(fatigue): add stage 4 automation health-check + install/repair tooling**. Adds `scripts/check_fatigue_stage4_automation.ps1` (read-only health check that classifies the observer automation as [BROKEN] / [SKIPPED] / [IDLE] / [READY], explains task result codes incl. `0` and `0x800710E0`, and reports the live `workout_log` count), `scripts/install_fatigue_stage4_observer_task.ps1` (idempotent `schtasks /Create ... /F` installer, default daily 20:00), and `scripts/fatigue_stage4_status.py` (read-only `COUNT(*)` DB helper via `DatabaseHandler`). Closes the automation-observability gap (the owner can now tell at a glance whether the task is installed, last ran clean, was skipped by Windows, or is just idle on empty `workout_log`). Verified 2026-05-30: check -> **[IDLE]** (last result `0`, `workout_log` empty), installer re-registered the task idempotently, `schtasks /Run` succeeded (last code `0`, latest log refreshed). No fatigue thresholds / scenarios / boundary tests touched; no DB write. See [`PHASE2_PLANNING.md §10`](fatigue_meter/PHASE2_PLANNING.md).
- 2026-05-29 handover sync — **docs(fatigue): sync handover after Stage 4 observer tooling**. Refreshes the branch-position lines in [`docs/MASTER_HANDOVER.md`](MASTER_HANDOVER.md) + this file to reflect `df9b6f9` / `f2cdc23` pushed and `origin/main` advanced from `39193f6`; records the Stage 4 observer as ready + still blocked on empty `workout_log`.
- `f2cdc23` (2026-05-29) — **chore(fatigue): add stage 4 observer tooling**. Adds `scripts/fatigue_stage4_observer.py` (read-only; reuses `utils.fatigue_data.build_fatigue_page_context` so numbers match `GET /fatigue`; never edits thresholds / scenarios / boundary tests), `scripts/run_fatigue_stage4_observer.bat`, `.gitignore` entries, +1 line in [`PHASE2_PLANNING.md §10`](fatigue_meter/PHASE2_PLANNING.md). Ran once 2026-05-29: `workout_log` empty → nothing appended → Stage 4 stays blocked on real logged workouts.
- `df9b6f9` (2026-05-25) — **chore(fatigue): close Phase 2 §10 #5 movement_pattern cleanup**. 454 NULL/blank `movement_pattern` rows → 0 (76 inferred via `utils.movement_patterns.classify_exercise()`, 378 `"unassigned"` sentinel); new invariant `tests/test_catalog_invariants.py::test_catalog_movement_pattern_has_no_nulls`; pytest 1442 → 1443. Pre-flight backup local id 5, label `pre-movement-pattern-cleanup-2026-05-25`.
- `39193f6` (2026-05-24) — **docs(fatigue): refresh phase 2 stage 4 handoff**.
- `1a93f66` (2026-05-24) — **docs(fatigue): close phase 2 stage 3 gate**. Flips [`docs/fatigue_meter/PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md) status banner to Stage 3 CLOSED + Stage 4 OPEN; verify-suite gate on `main` @ `d5b80bf` recorded (pytest 1442 passed; Playwright Chromium full 449 passed / 13 failed / 17 did-not-run — reds match pre-existing baseline exactly, zero new Stage-2 reds).

Recently landed on `origin/main` (newest first):

- `d5b80bf` (2026-05-23) — **PR #35** `feat(fatigue): add stage 2 fatigue breakdown surface`. Phase 2 Path 1 squash: per-muscle accumulator (`utils/fatigue.py` planned + logged + 4-week window), `routes/fatigue.py` blueprint, `templates/fatigue.html` + `_fatigue_muscle_bar.html`, period selector, two SFR cards, nav link, badge → page link, SCSS, 91 new pytest cases (1351 → 1442), `e2e/fatigue.spec.ts` 8 passed. Pre-merge restore point: backup id 5, label `pre-fatigue-meter-phase-2-stage-2-merge-2026-05-23`.
- `be22286` (2026-05-23) — **PR #34** `chore(fatigue): close Phase 2 Stage 1 prerequisites`. Catalog cleanup pass — 633 `primary_muscle_group` NULLs eliminated (132 inferred from `exercise_name` via `utils.constants.MUSCLE_ALIAS ∪ MUSCLE_GROUPS`, 501 dormant rows assigned `"Unassigned"` sentinel); `tests/test_catalog_invariants.py::test_catalog_primary_muscle_group_has_no_nulls` added; pre-flight backup id 5 captured (label `pre-fatigue-meter-phase-2-2026-05-23`); pytest 1350 → 1351.
- `24c6f46` (2026-05-23) — **PR #33** `docs(fatigue): lock Phase 2 Path 1 scope via Stage 0 walk`. Stage 0 decisions D2.1–D2.10 + stretch decisions + catalog re-scope synced into [`docs/fatigue_meter/BRAINSTORM.md §13.1 Phase 2 Decision Log`](fatigue_meter/BRAINSTORM.md); [`docs/fatigue_meter/PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md) authored as canonical Phase 2 source.
- `f01ccb9` (2026-05-23) — **docs(fatigue): extract Phase 2 planning**. Splits Phase 2 planning out of `docs/fatigue_meter/PLANNING.md` Stage 5/6 + `docs/fatigue_meter/BRAINSTORM.md` Phase 2 matrix.
- `15ea316` (2026-05-23) — **docs: sync handoff after worktree cleanup** (LEFTOVERS row #14 follow-up).
- `21859a1` (2026-05-23) — **docs: close stale worktree disposition backlog** (LEFTOVERS row #14 closed; old worktree paths already absent from disk; stale branch refs `test/visual-baseline-thumbnails` local + remote and `origin/redesign/calm-glass-2026` deleted with owner approval).
- `1956089` (2026-05-23) — **docs(workout-cool): close YouTube curation backlog** (LEFTOVERS row #12 closed by diminishing returns at 56 rows; ahead-of-origin status text refreshed).
- `ff244aa` (2026-05-23) — **content(workout-cool): expand curated YouTube references** (+20 owner-vetted rows on top of `cf21191`; `data/youtube_curated_top_n.csv` now 56 rows + header; curation closed by diminishing returns — see [`docs/workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md`](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md) "Curation Closed").
- `b5b8c7a` (2026-05-23) — **test(workout-cool §4.6): lock visual-baseline thumbnails via `toHaveScreenshot()`** (18 committed PNG baselines at `maxDiffPixelRatio: 0.01`; closes LEFTOVERS row #13).
- `f944366` (2026-05-23) — **docs: record KI-009 resolution**.
- `4bbe06b` (2026-05-23) — **fix(workout-log): replace pandas with xlsxwriter direct writer** (KI-009 fix; drops pandas/numpy/python-dateutil from `requirements.txt`).
- `6d87284` (2026-05-23) — **chore: remove dormant filter cache (KI-001 resolved by deletion)**.
- 2026-05-23 docs hygiene commit — refresh after the six-scope landing.
- `0ae5b39` (2026-05-23) — **test+docs: lock down toast/form/modal contracts and add Known Issues table**. New `e2e/ui-hardening.spec.ts` (12 tests) + new `docs/UI_SCENARIOS_GAP_ANALYSIS.md §0` (KI-001..KI-008).
- `40d7dd2` (2026-05-23) — **test(visual): add Body Composition snapshot baselines**. Adds `/body_composition` to the visual.spec.ts sweep + 6 PNG baselines (desktop/tablet/mobile × light/dark); migration script applies `add_body_composition_snapshots_table()` so the page renders under the visual harness.
- `89561df` (2026-05-23) — **feat(navbar): accent colors + hover motion on Profile, Body Composition, and Backup icons**. CSS-only color accents + hover/focus motion + reduced-motion opt-out; swaps Profile icon to `fa-user-alt`.
- `ef475cc` (2026-05-23) — **feat(navbar): hover-to-open desktop dropdowns**. Gates on `(hover: hover) and (pointer: fine) and (min-width: 992px)`; touch + mobile remain click-to-open.
- `18ad223` (2026-05-23) — **feat(profile): mount workout-cool bodymap with worst-state aggregation (§3.6)**. Lifts the previously deferred §3.6 scope; multi-muscle BACK regions reflect the worst coverage state across the set.
- `de3e4d0` (2026-05-23) — **feat(profile): surface latest body composition snapshot (#17 + #18)**. Display-only BFP/ACE line + Lean Mass sub-line on the Profile insights card; reads latest snapshot, Navy-over-BMI fallback.
- `cf21191` (2026-05-22) — **Add curated YouTube references for core exercises** (36 rows; `data/youtube_curated_top_n.csv` populated and `scripts/apply_youtube_curated.py` applied).
- `cbf745a` (2026-05-21) — **fix(api): migrate remaining response-contract exceptions**. `/api/pattern_coverage` and the replace-exercise fallback branches now use `success_response()` / `error_response()`; "no result" cases pass `status_code=200` to keep the existing UI contract.
- `94482d7` (2026-05-21) — **chore(body-composition): validate captured_at, add JS↔Python parity test (#32)**. Tightens the snapshot create endpoint's ISO format validation and adds the Playwright JS↔Python numeric parity case.

Recent history on `origin/main` (newest first):

- `20b4b24` (2026-05-20) — **PR #31** `feat(body-composition): add page, API, and nav slot`. Squash bundles the two pre-squash Body Composition Issue #21 commits (backend formula + migration + tests; page + API + UI + Playwright). CI 6/6 green. Opus review verdict: ready to merge. Non-blocking follow-ups recorded for later: (1) add `captured_at` ISO format validation, (2) add JS↔Python numeric parity Playwright assertion, (3) minor docs test-count drift refresh.
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
- Body Composition Issue #21 (2026-05-20) — PR #31 (`20b4b24`). Both slices shipped as one squash commit: `utils/body_fat.py` (4 pure formulas with "MUST MATCH JS MIRROR" comment), `add_body_composition_snapshots_table()` migration in `utils/database.py`, `routes/body_composition.py` blueprint (4 endpoints), `templates/body_composition.html` page (calculator + ACE band + Jackson & Pollock + trend SVG + history), `static/js/modules/body-composition.js` (formula mirror + page wiring), `static/css/pages-body-composition.css` route bundle, navbar slot, `app.py` + `tests/conftest.py` blueprint registration, 67 route + formula + migration tests, 4 Playwright specs, smoke/nav-dropdown updates.

## Next Task

### Shipped 2026-05-20 via PR #31 — Body Composition Issue #21

Both slices landed as squash commit `20b4b24` on `origin/main`. Files included:

- **New** `routes/body_composition.py` — `body_composition_bp` blueprint with `GET /body_composition`, `POST /api/body_composition/snapshot`, `GET /api/body_composition/snapshots`, `DELETE /api/body_composition/snapshots/<id>`. All four routes use `success_response()` / `error_response()`, `DatabaseHandler`, and the shared logger pattern. Snapshot creation reads gender / age / height / bodyweight from the server-side `user_profile` row (the browser posts tape + notes only), then validates profile demographics and circumferences via the range constants exported from `utils.body_fat`. Tape data is all-or-nothing: provide all required tape values for the Navy method or leave blank to fall through to the BMI fallback.
- **New** `templates/body_composition.html` — `body-composition.html` page. Reads gender / age / height / bodyweight from the existing `user_profile` row (shown via `data-profile-*` attributes on the page wrapper), renders an "Profile incomplete" warning when demographics are missing, hosts the calculator form (tape inputs + collapsible "How to measure" guide), the live results panel (BFP / fat mass / lean mass / BMI / ACE segmented band with tick / Jackson & Pollock comparison line / citations footer), the trend SVG, and the snapshot history table with per-row delete.
- **New** `static/js/modules/body-composition.js` — pure-function mirror of the four Python formulas (`computeNavy`, `computeBmi`, `aceCategory`, `jacksonPollockIdeal`) with module-level "MUST MATCH PYTHON" comment, plus the page wiring: live results on every input event, ACE band tick positioning, trend polyline computation, snapshot save / delete via the `api` wrapper, toast notifications.
- **New** `static/css/pages-body-composition.css` — page bundle (calculator panel + results + ACE segmented band + trend SVG + history table; dark-theme overrides).
- **Edit** `templates/base.html` + `static/css/navbar.css` — moves `Profile` into the main left flow and adds the full-label `Body Composition` link between `Profile` and `Distribute` (`nav-volume-splitter`), with a ruler icon. `navbar.css` gives the longer label a wider fixed pill at desktop sizes so the text does not clip while the dark-mode toggle remains visible.
- **Edit** `static/js/modules/navbar.js` — adds `'/body_composition': 'nav-body-composition'` to the pathMap so the active-state highlight from Issue #12 fires.
- **Edit** `.claude/rules/frontend.md` — updates the route-bundle cap/list to include `pages-body-composition.css` and records the new nav flow with Profile + Body Composition before Distribute.
- **Edit** `app.py` + `tests/conftest.py` — register `body_composition_bp` (between `user_profile_bp` and `volume_splitter_bp` in both files).
- **New** `tests/test_body_composition_routes.py` — 18 route tests: page renders with + without profile, page lists existing snapshots, POST Navy male / female / male-rejects-hip / female-requires-hip / BMI-only / profile-demographics-source / missing-profile / out-of-range-height / partial-tape / log-domain-violation / captured-at passthrough, GET descending / empty, DELETE success / not-found.
- **New** `e2e/body-composition.spec.ts` — 4 Chromium specs: navbar routes to page, empty-state render, save-then-delete flow with live results assertion and trend update, BMI-fallback when tape blank.
- **Edit** `e2e/fixtures.ts`, `e2e/smoke-navigation.spec.ts`, `e2e/nav-dropdown.spec.ts` — adds body-composition route/selectors, smoke-cycles `/body_composition`, and asserts the top-level nav order `['Plan', 'Log', 'Analyze', 'Progress', 'Profile', 'Body Composition', 'Distribute', 'Backup']` plus a no-clipped-label check.
- **Edit** `docs/ACTIVE_DEVELOPMENT.md` + `docs/MASTER_HANDOVER.md` — this update.

First-slice files (now part of PR #31 squash, originally landed on the branch as `f4496f7`):

- **New** `utils/body_fat.py` — pure-function module with `compute_navy(...)`, `compute_bmi(...)`, `ace_category(bfp, gender)`, `jackson_pollock_ideal(age, gender)`. Carries the **"must match JS mirror"** module-level comment from the Issue #17 contract. Server-side validation (range checks + log-domain rejection) raises `ValueError`; route layer (not built here) will translate into structured 4xx responses.
- **New** `tests/test_body_fat.py` — 42 cases. Coverage: Navy male + female typical lifters, Navy log-domain rejection (both sexes), male-rejects-hip, female-requires-hip, out-of-range height, invalid gender; BMI adult male / adult female / boy <18 / girl <18 + age-18 boundary; ACE male + female boundary rows (parametrized 20 rows) + low-value clamp; Jackson & Pollock anchor rows + interpolation male/female + age clamp below 20 / above 55 + invalid gender.
- **Edit** `utils/database.py` — added `add_body_composition_snapshots_table()` migration. Creates the `body_composition_snapshots` table exactly per [`docs/body_composition/development_issues.md`](body_composition/development_issues.md) (14 columns; 6 NOT NULL: `captured_at`, `bodyweight_kg`, `height_cm`, `age_years`, `gender`, `bfp_bmi`) + `idx_body_composition_snapshots_captured_at` descending index. Idempotent (`CREATE TABLE/INDEX IF NOT EXISTS`). DatabaseHandler pattern only.
- **Edit** `app.py` — imports + calls `add_body_composition_snapshots_table()` in the startup sequence immediately after `add_user_profile_tables()`. Also registered in the `/erase-data` drop-list (between `user_profile` and `user_selection`) and in the post-drop re-init block.
- **Edit** `tests/conftest.py` — imports the new migration, calls it in `_initialize_test_database()` (between `add_user_profile_tables()` and `initialize_exercise_order()`), adds `body_composition_snapshots` to the inner `erase_data()` drop-list, and adds it to the `clean_db` fixture's per-test DELETE list.
- **New** `tests/test_db_migration.py` — 7 cases. Coverage: expected columns (incl. NOT NULL set), index existence + indexed column, idempotent re-run, accepts Navy-style insert, accepts BMI-only (tape-blank) insert, rejects missing NOT NULL, `/erase-data` recreates table + index.
- **New** `docs/body_composition/OPUS_START_PROMPT.md` — reusable prompt that scoped this workstream to the backend-first slice and preserved the fatigue / profile-hook / YouTube-curation guardrails.

**Verification (2026-05-20, second slice — pre-merge):**

- Original Opus targeted pytest: `.venv/Scripts/python.exe -m pytest tests/test_body_composition_routes.py tests/test_body_fat.py tests/test_db_migration.py -q` → **66 passed in 7.25s** (17 route tests on top of the 49 first-slice tests).
- Original Opus startup-touching subset: `.venv/Scripts/python.exe -m pytest tests/test_body_composition_routes.py tests/test_body_fat.py tests/test_db_migration.py tests/test_database_user_profile.py tests/test_harness_isolation.py tests/test_user_profile_routes.py tests/test_program_backup.py -q` → **132 passed in 21.06s**.
- Original Opus full pytest: `.venv/Scripts/python.exe -m pytest tests/ -q` → **1371 passed in 173.08s** (17 net new tests vs. 1354 first-slice baseline; no regressions).
- Opus post-Codex full pytest: `.venv/Scripts/python.exe -m pytest tests/ -q` → **1372 passed in 189.58s** (18 route tests after the profile-demographics contract test; no regressions).
- Original Opus Playwright targeted: `npx playwright test e2e/body-composition.spec.ts --project=chromium --reporter=line` → **4 passed in 5.4s**.
- Codex review pytest after fixes: `.venv/Scripts/python.exe -m pytest tests/test_body_composition_routes.py tests/test_body_fat.py tests/test_db_migration.py -q` → **67 passed in 4.76s**.
- Codex review Playwright, final: `npx playwright test e2e/body-composition.spec.ts e2e/smoke-navigation.spec.ts e2e/nav-dropdown.spec.ts --project=chromium --reporter=line` → **20 passed in 42.7s**.
- Codex review intermediate checks: same 20-spec sweep first exposed a strict-fixture failure after temporarily adding Profile to `nav-dropdown`'s backup-route list (`19 passed, 1 failed in 47.1s`; existing Profile bodymap SVG console error), then passed after narrowing that list back to the primary flow plus `/body_composition` (`20 passed in 42.8s`). `e2e/nav-dropdown.spec.ts` then failed twice while adding the no-clipped-label assertion (`5 passed, 1 failed in 19.7s` for clipped `Body Composition`; `5 passed, 1 failed in 19.0s` after an over-tight primary-pill adjustment), and finally passed after the targeted CSS width fix: `npx playwright test e2e/nav-dropdown.spec.ts --project=chromium --reporter=line` → **6 passed in 18.7s**.
- One unrelated flake from the original Opus pass remains noted: `e2e/accessibility.spec.ts:283 focus returns after modal closes` (modal close on `/workout_plan` — independent of body composition; passes in isolation).

**Explicitly NOT built in this slice (still deferred):**

- Profile-page display hooks (Issue #17 / #18 sub-lines: bodyweight-tile *Lean mass* + transparency-card *"Body fat: X % · {ACE band}"*) — owner-deferred follow-up after `/body_composition` ships and snapshots are routinely captured.
- Visual-baseline screenshots for `/body_composition` — out of scope for this slice; can be added later if owner wants pixel diffs.

Working tree post-merge: clean except for `data/database.db` (runtime, kept dirty by owner policy). `utils/fatigue.py`, `tests/test_fatigue.py`, and `scripts/fatigue_calibration_report.py` were **not touched**.

### Workstream queue (post Body Composition Issue #21)

No active workstream is currently in-flight on `origin/main`. Owner-approved queue (from the section above) still applies: Profile-page hooks (Issues #17 / #18) are the natural next step now that `/body_composition` ships and snapshots can accumulate, but owner has explicitly held them — do not start without a fresh go-ahead. YouTube curation is similarly held. Wait for owner direction.

### Closed workstreams (do not reopen as "next task")

- **Redesign post-P8 triage** — closed 2026-05-19 after verification against `origin/main`. 10 of 11 issues shipped (#2 `9052337`, #3+#4 `0a41725`, #5 `7880618`, #6 `38b1f59`, #7+#8 `9b0c71b`, #9 `a95b067`, #10 `f6e39d6`, #11 `f7d9f12`); #1 (nav Backup link) deferred by owner choice. `debug/redesign_post_p8_issues_SESSION_STATE.md` is historical only.
- **phase5_3i_plan** — closed 2026-05-19 as accepted-as-shipped. Planning doc `docs/phase5_3i_plan.md` was authored 2026-04-15 (`c0da18e`) and deleted 2026-04-24 (`635fa3e`) with the rest of the spring-cleanup planning suite. The 5A–5H retroactive confidence-recovery validation gates never ran, but the underlying `12c90ac` refactors (3i-a..3i-h decompositions) have held under the test baseline for 5+ weeks (1160 passed; baseline rose from 934 at session-state writing) with no regression traced back to them. `debug/phase5_3i_plan_SESSION_STATE.md` is historical only. Re-open only if a concrete regression appears in one of the decomposed functions.

### Closed — workout.cool §4 / §4.6 / §5 follow-ups

All previously-tracked follow-ups have shipped:

- §4.6 pixel baselines locked via `toHaveScreenshot()` in `b5b8c7a` (2026-05-23). 18 committed PNG baselines at `e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots/`.
- §5 YouTube curation closed by diminishing returns at 56 rows (`cf21191` + `ff244aa`, 2026-05-23). Reopen only if owner supplies new vetted IDs — see [YOUTUBE_REFERENCE_VIDEOS.md "Curation Closed"](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md).
- Worktree disposition closed by inspection + branch cleanup in `21859a1` (2026-05-23). See [LEFTOVERS_BY_PRIORITY.md §6](LEFTOVERS_BY_PRIORITY.md).

### Fatigue meter Phase 2 — Stage 4 calibration window OPEN (status updated 2026-05-24)

Phase 1 shipped; Phase 1 Stage 4 closed 2026-05-20 (no threshold changes). **Phase 2 Path 1 shipped 2026-05-23 via PR #35 (`d5b80bf`); Phase 2 Stage 3 verify-suite gate closed 2026-05-24 (`1a93f66`); Phase 2 Stage 4 calibration window OPEN 2026-05-24, earliest close 2026-06-07** (≥2 weeks real use). Source of truth: [`docs/fatigue_meter/PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md) Stage 4 + §10. `calibration-notes.md` remains the Phase 1 Stage 4 authority; STAGE4_PARKED_HANDOFF.md is superseded.

**Live calibration guardrails** (do not, without an explicit new owner override):

- Edit `utils/fatigue.py::MUSCLE_VOLUME_LANDMARKS` / `SESSION_FATIGUE_BANDS` / `WEEKLY_FATIGUE_BANDS` (per-muscle and global thresholds remain §24.B defaults + BRAINSTORM §5 verbatim for the 12 ranked muscles).
- Edit `tests/test_fatigue.py` boundary-classification tests.
- Tune `scripts/fatigue_calibration_report.py::SCENARIOS` (Hypothesis B retune of `hard_4d` is a documented-not-applied deferred follow-up).

**Calibration evidence to collect during the window** (per [`PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md) Stage 4 / §10):

- Per-muscle band disagreements recorded as `(muscle, period, engine band, felt label, direction)`. **Two same-direction disagreements = signal; one isolated disagreement = noise** (Phase 1 §4.2 rule).
- Real-use only: `workout_log` data drives the signal. Synthetic generator mismatches do not justify threshold changes (Phase 1 `hard_4d` precedent — scenario under-shoot, not threshold drift).
- `/fatigue` UX notes: MRV sort usefulness, period selector reach (this session / this week / last 4 weeks), `fatigue == 0 → "—"` SFR sentinel behavior, planned-vs-logged side-by-side usefulness vs clutter.
- Watch the six unranked labels (Front-Shoulder, Rear-Shoulder, Lower Back, Hip-Adductors, Middle-Traps, Neck) — `—` neutral state is intentional pending vetted MEV/MAV/MRV (Phase-3 follow-up).
- Watch the `Unassigned` bucket — should stay empty in `workout_log`-driven bars (501 sentinel rows verified dormant at Stage 1); if a logged set lands there, name the offending exercise as a catalog cleanup signal.
- Link reciprocity (badge → page, page → summary) and console errors.
- `movement_pattern` cleanup (454 NULLs → 0) shipped 2026-05-25 via local `df9b6f9` — see [PHASE2_PLANNING.md §10](fatigue_meter/PHASE2_PLANNING.md) Open follow-ups item #5 (76 inferred, 378 `"unassigned"` sentinel; pytest 1442 → 1443).

Threshold tuning requires both the ≥2 same-direction real-use disagreement bar AND a fresh owner go-ahead.

**Earlier history (preserved):**

- 2026-05-20 — Phase 1 Stage 4 close (owner labeled 5 anchors; 4/5 agreed; 1 isolated `hard_4d` synthetic disagreement → no threshold change).
- 2026-05-20 — PR #26 (`2b34b50`) docs-only synthetic-override / coherence pass; PR #28 (`63c745d`) presentation-only badge restyle.
- 2026-05-23 — Phase 2 Stage 0 lock PR #33 (`24c6f46`); Stage 1 close PR #34 (`be22286`); Stage 2 ship PR #35 (`d5b80bf`).

## Agent Authority

Agents may, without asking the owner:

- Update docs that are stale relative to committed `origin/main` state.
- Run targeted pytest / Playwright checks.
- Continue from one listed task to the next after tests pass.

Agents must not:

- Reset, force-push, or otherwise discard working-tree state without owner approval.
- Commit `data/database.db` (runtime; agents-must-not list in CLAUDE.md).
- Edit `utils/fatigue.py::MUSCLE_VOLUME_LANDMARKS` / `SESSION_FATIGUE_BANDS` / `WEEKLY_FATIGUE_BANDS` (per-muscle and global thresholds; gated by Phase 2 Stage 4 calibration — see DO NOT REOPEN block above).
- Edit `tests/test_fatigue.py` boundary-classification tests.
- Tune `scripts/fatigue_calibration_report.py::SCENARIOS`.
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
