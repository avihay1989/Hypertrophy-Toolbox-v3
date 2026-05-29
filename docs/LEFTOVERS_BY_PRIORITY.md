# Leftovers by Priority

> **Purpose:** Prioritized punch list of unfinished / parked / deferred items discovered in `docs/` and in the local working tree.
>
> **Review history:**
> - **v1 (2026-05-23, Opus):** initial clean-state backlog framing.
> - **v2 (Codex review):** flagged that the local tree is not clean — newer commits + large dirty working set overlap several backlog rows.
> - **v3 (Opus second-pass scan):** identified 6 distinct workstreams mixed in the dirty tree, including 2 unannounced navbar UX features; expanded the P0 docs-hygiene bucket.
> - **v4 (Codex re-review):** Opus + Codex agree. File rewritten to lead with in-flight work triage, then expanded P0 docs, then remaining backlog.
> - **v5 (2026-05-23, post-execution):** Owner accepted all six scopes; each landed as its own commit (`de3e4d0`, `18ad223`, `ef475cc`, `89561df`, `40d7dd2`, `0ae5b39`). Section 1 docs hygiene executed in a single doc-only commit on top of the six feature commits. Pushed to `origin/main`.
> - **v6 (2026-05-23, KI-001 close):** Triage of Section 2 found the filter cache module was dormant code with zero production callers. Owner approved Path A (delete). `utils/filter_cache.py` + `tests/test_filter_cache.py` removed; agent + rule + CLAUDE.md references purged. Section 2 closed by deletion rather than by adding invalidation hooks.
> - **v7 (2026-05-23, §4.6 baselines + KI-009 close):** Two more rows closed. (a) Workout-log Excel export `ImportError: pandas` blocker (KI-009) resolved by replacing the pandas-based exporter with `xlsxwriter` direct writer; pandas/numpy/python-dateutil dropped from `requirements.txt`. (b) Row #13 §4.6 pixel baselines locked — `e2e/visual-baseline-thumbnails.spec.ts` promoted from inspection-only PNGs to committed `toHaveScreenshot()` baselines (18 PNGs at `maxDiffPixelRatio: 0.01`), 18 passed in 14.3s against the isolated visual DB harness. Section 3 row #13 closed, Section 4 added.
> - **v8 (2026-05-23, §5 curation closed):** Row #12 closed by diminishing returns. Owner-approved `ff244aa` (`content(workout-cool): expand curated YouTube references`) added 20 more rows on top of `cf21191`, bringing `data/youtube_curated_top_n.csv` to **56 curated rows + header**. Usage triage of the remaining ~1,841 uncurated catalogue exercises against `user_selection` + `workout_log` found only one (`Barbell Close Grip Bench Press`, 2 uses) above the 0–1-use floor — the 56-row set already covers every exercise with meaningful usage signal. Further expansion would require fabricating unvalidated YouTube IDs, which is worse UX than the search fallback. Section 5 added; Section 3 row #12 closed.
> - **v9 (2026-05-23, worktree disposition closed):** Row #14 closed by inspection. Both worktree paths (`Hypertrophy-Toolbox-v3-visual-baseline-s4`, `Hypertrophy-Toolbox-v3-redesign-calm-glass`) are absent from `D:/development/` and neither is registered in `git worktree list` — the row's "still checked out locally" claim was stale. Two dangling branch refs (`test/visual-baseline-thumbnails @ 99910a4` local + remote; `origin/redesign/calm-glass-2026 @ ba519df` remote) verified redundant — the first shipped via PR #22 squash (`631b5f8`) plus later refactor `b5b8c7a`, the second is a strict ancestor of `origin/main`. Owner-approved deletions ran: `git branch -D test/visual-baseline-thumbnails`, `git push origin --delete test/visual-baseline-thumbnails`, `git push origin --delete redesign/calm-glass-2026`. Section 6 added; Section 3 row #14 closed.
> - **v10 (2026-05-24, Phase 2 Stage 4 reframe):** Row #15 reframed from "parked Phase-2 planning" to Phase-2 Stage 4 calibration tracking. Phase 2 Path 1 shipped 2026-05-23 via PR #35 (`d5b80bf`); Stage 3 verify-suite gate closed 2026-05-24 (`1a93f66`). Stage 4 calibration window open 2026-05-24, earliest close 2026-06-07. Remaining "don't" guidance now targets the live calibration gate (per-muscle threshold tuning), not Phase 2 planning entry — that entry already happened. Phase-3 follow-ups (vetted MEV/MAV/MRV for the six unranked labels, per-muscle SFR card, `movement_pattern` cleanup) preserved as deferred per [`PHASE2_PLANNING.md §10`](fatigue_meter/PHASE2_PLANNING.md).

---

## 0. CLOSED — Six In-Flight Scopes All Landed (2026-05-23)

**All six scopes the owner accepted landed as separate commits on local `main`.**

The local working tree contained **six distinct workstreams** mixed together. Owner direction was "keep both A and B; keep both C and D as two separate commits; keep both E and F; run targeted tests before each commit." All six landed cleanly; targeted gates passed for each.

### Outcome — six commits landed

| # | Scope | Landed as | Targeted gate |
|---|---|---|---|
| A | **Profile BC hooks (Issues #17/#18)** | `de3e4d0` `feat(profile): surface latest body composition snapshot (#17 + #18)` | pytest 26 passed + Playwright 2 passed (A+B combined) |
| B | **Profile workout.cool bodymap §3.6** | `18ad223` `feat(profile): mount workout-cool bodymap with worst-state aggregation (§3.6)` | pytest 91 passed + same Playwright |
| C | **Navbar hover dropdowns** | `ef475cc` `feat(navbar): hover-to-open desktop dropdowns` | Playwright `e2e/nav-dropdown.spec.ts` 6 passed |
| D | **Navbar icon accents + motion** | `89561df` `feat(navbar): accent colors + hover motion on Profile, Body Composition, and Backup icons` | Playwright icon-test 1 passed |
| E | **Body Composition visual baselines** | `40d7dd2` `test(visual): add Body Composition snapshot baselines` | Playwright `visual.spec.ts -g body-composition` 6 passed |
| F | **UI hardening spec + Known Issues table** | `0ae5b39` `test+docs: lock down toast/form/modal contracts and add Known Issues table` | Playwright `e2e/ui-hardening.spec.ts` 12 passed |

### Bookkeeping corrections noted during execution

- `static/css/pages-user-profile.css` was originally bucketed under B in this doc, but the diff actually styles A's `.profile-insights-body-fat` + `.profile-insights-tile-subline`. It landed with A.
- `templates/base.html` (Profile nav icon swap `fa-user-circle` → `fa-user-alt`) was an orphan per the v4 doc; it belonged to D and landed with D.
- Per-block splits on `e2e/user-profile.spec.ts` (A vs B) and `e2e/nav-dropdown.spec.ts` (C vs D) used Edit-out / stage / Edit-back rather than `git add -p` since the harness has no interactive shell.

---

## 1. CLOSED — P0 Docs Hygiene (executed 2026-05-23 as a single doc-only commit on top of the six feature commits)

All ten items below shipped in one docs-only commit on top of A–F. Each links to the corrected file.

| #  | File / area | What was stale | Resolution |
|----|---|---|---|
| 1  | [`ACTIVE_DEVELOPMENT.md`](ACTIVE_DEVELOPMENT.md) + [`MASTER_HANDOVER.md`](MASTER_HANDOVER.md) | Described PR #31 follow-ups as non-blocking TODO; they shipped as PR #32 (`94482d7`). | Refreshed Current Objective + Workstream Queue + Active Workstreams table + Open Decisions + Next Safe Step to reflect PR #32 shipped + 6 new ahead-of-origin commits. |
| 2  | [`CLAUDE_MD_AUDIT.md §2`](CLAUDE_MD_AUDIT.md) | Listed `pattern_coverage` + replace-exercise as response-contract exceptions. | Rewritten to "None" with link to `cbf745a` migration. |
| 3  | [`body_composition/development_issues.md`](body_composition/development_issues.md) | Issue #21 still showed `Open`. | Flipped to Resolved; all acceptance boxes ticked; pointed at PR #31, PR #32, and `de3e4d0` for the Profile hooks. |
| 4  | [`E2E_TESTING.md`](E2E_TESTING.md) | Said 19 specs; actual is 25. | Bumped to 25; added rows for `body-composition`, `fatigue-stage4-smokes`, `ui-hardening`, `user-profile`, `visual-baseline-thumbnails`, `volume-progress`. |
| 5  | [`CSS_OWNERSHIP_MAP.md`](CSS_OWNERSHIP_MAP.md) | Said 16 CSS files; actual is 18. | Bumped to 18; added `pages-user-profile.css` and `pages-body-composition.css` to both tables. |
| 6  | [`workout_cool_integration/PLANNING.md`](workout_cool_integration/PLANNING.md) + [`YOUTUBE_REFERENCE_VIDEOS.md`](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md) | Described `data/youtube_curated_top_n.csv` as header-only. | Updated to 36 curated rows + header (commit `cf21191`); both docs reframe the work as "first batch shipped." |
| 7  | [`workout_cool_integration/EXECUTION_LOG.md`](workout_cool_integration/EXECUTION_LOG.md) | Said §3.6 was "deferred indefinitely; future separate plan." | Added two new top entries: 2026-05-23 §3.6 shipped (`18ad223`) and 2026-05-22 §5 curation (`cf21191`). |
| 8  | [`CHANGELOG.md`](CHANGELOG.md) | "Unreleased - May 11, 2026" was the most recent entry. | Added six new Unreleased sections: May 23 (Profile #17/#18 hooks + §3.6 + navbar + visual baselines + ui-hardening), May 22 (YouTube curation), May 21 (PR #32 + response-contract migration), May 20 (PR #31 + fatigue badge + Stage 4 close), May 18 (§4.6 + dependency pins), May 15 (§4 thumbnails). |
| 9  | [`ai_workflow/INDEX.md`](ai_workflow/INDEX.md) | Said fatigue meter "parked; Phase 1 + Stage 4 entry shipped." | Rewrote to "closed; Phase 1 + Stage 4 shipped"; added Body Composition Issue #21 row; updated workout.cool row to include §3.6 + YouTube curation. |
| 10 | [`docs/README.md`](README.md) | Last updated 2026-05-11; omitted `ACTIVE_DEVELOPMENT.md`, `MASTER_HANDOVER.md`, this file. | Added `MASTER_HANDOVER.md`, `ACTIVE_DEVELOPMENT.md`, `LEFTOVERS_BY_PRIORITY.md` to active docs; moved `VOLUME_TAXONOMY_AUDIT.md` to Archive (completed Phase 0 audit). |

---

## 2. CLOSED — KI-001 Filter Cache (resolved 2026-05-23 by deletion)

| # | Item | Resolution |
|---|---|---|
| 11 | **KI-001 — Filter cache invalidation** | Resolved by deleting the module. Triage discovered `utils/filter_cache.py` was dormant code: zero `from utils.filter_cache` imports in `routes/`, `utils/`, or `app.py`; `get_cached_unique_values()` only called by `warm_cache()` which itself was never wired into startup; the route that *would* consume it (`routes/filters.py::get_unique_values`) hit `DatabaseHandler` directly. Catalogue mutations (`save_exercise`, `remove_exercise_by_name`) had no HTTP path. Removing the module eliminated the "1 hour staleness" theoretical risk AND the latent SQLi exposure on the un-validated `f"SELECT DISTINCT {column} FROM {table}"` at line 85. `tests/test_filter_cache.py` (~440 LOC, 30+ tests) removed along with it. |

---

## 3. Remaining Backlog (after Sections 0, 1, 2, 4, 5, 6 closed)

| #  | Pri       | Item                                                                                                                                                                       | Notes / status                                                                       | Effort     |
|----|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|------------|
| 15 | **Tracking** | **Fatigue meter Phase 2 Stage 4 — calibration window OPEN**                                                                                                                | Phase 2 Path 1 shipped 2026-05-23 via PR #35 (`d5b80bf`); Stage 3 verify-suite gate closed 2026-05-24 (`1a93f66`). Stage 4 calibration window open 2026-05-24, **earliest close 2026-06-07** (≥2 weeks real use). Source of truth: [`fatigue_meter/PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md) Stage 4 + §10. **Live calibration guardrails:** no per-muscle threshold tuning without ≥2 same-direction real-use disagreements; synthetic-generator-only mismatches do not justify threshold changes (Phase 1 `hard_4d` precedent). Do not edit `utils/fatigue.py::MUSCLE_VOLUME_LANDMARKS` / `SESSION_FATIGUE_BANDS` / `WEEKLY_FATIGUE_BANDS`, do not edit `tests/test_fatigue.py` boundary-classification tests, do not tune `scripts/fatigue_calibration_report.py::SCENARIOS`. Phase-3 follow-ups (vetted MEV/MAV/MRV for the six unranked labels, per-muscle SFR card, `movement_pattern` cleanup) remain deferred per `PHASE2_PLANNING.md §10`. **Automation-observability gap CLOSED 2026-05-30** — `scripts/check_fatigue_stage4_automation.ps1` (read-only health check; [BROKEN]/[SKIPPED]/[IDLE]/[READY] verdict + task-result-code explanations incl. `0` / `0x800710E0`) + `scripts/install_fatigue_stage4_observer_task.ps1` (idempotent installer/repair) + `scripts/fatigue_stage4_status.py` (read-only `workout_log` count). Verified [IDLE] on empty `workout_log`. | — |

### Rows #4, #5, #8, #9, #12, #13, #14 — closed

Rows #4, #5, #8, #9 were Section 0 in-flight scopes; they landed as commits `40d7dd2` (#4, scope E), `de3e4d0` (#5, scope A), `0ae5b39` (#8, scope F), and `18ad223` (#9, scope B) on 2026-05-23. Row #12 (§5 curation) closed by diminishing returns 2026-05-23 — see Section 5 below. Row #13 (§4.6 pixel baselines) landed 2026-05-23 — see Section 4 below. Row #14 (worktree disposition) closed by inspection 2026-05-23 — see Section 6 below.

---

## 4. CLOSED — Row #13 §4.6 Pixel Baselines (resolved 2026-05-23 by `toHaveScreenshot()` lock-in)

| # | Item | Resolution |
|---|---|---|
| 13 | **§4.6 pixel baselines** | Resolved. [`e2e/visual-baseline-thumbnails.spec.ts`](../e2e/visual-baseline-thumbnails.spec.ts) was promoted from inspection-only PNGs (saved to `e2e/artifacts/visual-baseline/`) to committed `toHaveScreenshot()` baselines under [`e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots/`](../e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots/). 18 PNGs cover the full §4.6 matrix (`/workout_plan` desktop / tablet / mobile × light / dark × simple / advanced = 12 + `/workout_log` desktop / tablet / mobile × light / dark = 6) at `maxDiffPixelRatio: 0.01`. The spec is now a real regression guard. Owner reviewed the 18 generated PNGs before commit (per the spec's "first-run baseline commit is owner-eyes-on" gate). Verified via the canonical isolated-DB harness (`e2e/scripts/prepare_visual_db.py` → apply mapping → seed → `DB_FILE=… npx playwright test`) → **18 passed in 14.3s**. See [`docs/workout_cool_integration/EXECUTION_LOG.md`](workout_cool_integration/EXECUTION_LOG.md) (top entry) for the full command sequence. |

---

## 5. CLOSED — Row #12 §5 YouTube Curation (resolved 2026-05-23 by diminishing returns)

| # | Item | Resolution |
|---|---|---|
| 12 | **workout.cool §5 curation** | Closed. Owner-approved `ff244aa` (`content(workout-cool): expand curated YouTube references`) added 20 owner-vetted rows on top of `cf21191`'s starter 36, bringing [`data/youtube_curated_top_n.csv`](../data/youtube_curated_top_n.csv) to **56 curated rows + header**. Usage triage of the remaining ~1,841 uncurated catalogue rows against `user_selection` + `workout_log` confirmed all but one have 0–1 combined uses (lone exception `Barbell Close Grip Bench Press` at 2 uses); the 56-row set already covers every common/core lift with meaningful usage signal. Further expansion would require fabricating unvalidated YouTube IDs, which is worse UX than the search fallback. The designed hybrid behavior in [`PLANNING.md §5.4`](workout_cool_integration/PLANNING.md#54-where-the-video-ids-come-from) was always to curate top-N and search-fallback the long tail. Source of truth for content is the CSV + `scripts/apply_youtube_curated.py`; `data/database.db` is runtime-only and not committed. See [`docs/workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md`](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md) "Curation Closed" section for the closing rationale and the owner-driven reopen flow. |

---

## 6. CLOSED — Row #14 Worktree Disposition (resolved 2026-05-23 by inspection + branch cleanup)

| # | Item | Resolution |
|---|---|---|
| 14 | **Worktree disposition** | Closed. Inspection found both worktree paths (`D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4` and `D:/development/Hypertrophy-Toolbox-v3-redesign-calm-glass`) already absent from disk; neither was registered in `git worktree list`. The row's "still checked out locally" claim was stale. Two dangling branch refs were found and verified redundant: (a) `test/visual-baseline-thumbnails @ 99910a4` (local + remote) was shipped via PR #22 squash-merge `631b5f8` and later refactored on `main` as `b5b8c7a` (the `toHaveScreenshot()` lock-in); (b) `origin/redesign/calm-glass-2026 @ ba519df` was a strict ancestor of `origin/main` (verified via `git merge-base --is-ancestor`). Owner-approved deletions ran cleanly: `git branch -D test/visual-baseline-thumbnails` (was `99910a4`), `git push origin --delete test/visual-baseline-thumbnails`, `git push origin --delete redesign/calm-glass-2026`. Post-cleanup verification: `git branch --list test/visual-baseline-thumbnails` empty, `git ls-remote --heads origin test/visual-baseline-thumbnails redesign/calm-glass-2026` empty, working tree clean except for `data/database.db` runtime dirt. |

---

## 7. Low-Priority Code TODOs (for completeness; don't let these distract)

| Location                           | TODO                                                                                  | Disposition                                                  |
|------------------------------------|---------------------------------------------------------------------------------------|--------------------------------------------------------------|
| [`utils/program_backup.py:18`](../utils/program_backup.py#L18) | `schema_version` written but not yet consumed                                       | Forward-looking marker; no action needed                     |
| [`utils/constants.py:11`](../utils/constants.py#L11)           | Evaluate collapsing `Front-Shoulder` into anatomical naming once UI migrates          | Long-term taxonomy decision                                  |
| [`utils/constants.py:92-93`](../utils/constants.py#L92)        | Confirm whether `Mid/Upper Back` rollup should remain a dedicated grouping            | Long-term taxonomy decision                                  |

---

## Source References

| Section / item             | Source-of-truth doc                                                                                          |
|----------------------------|--------------------------------------------------------------------------------------------------------------|
| Section 0 (dirty tree)     | `git diff --stat HEAD`, `git status --short`, this revision                                                  |
| Section 1 #1, #2           | [`ACTIVE_DEVELOPMENT.md`](ACTIVE_DEVELOPMENT.md), [`MASTER_HANDOVER.md`](MASTER_HANDOVER.md), [`CLAUDE_MD_AUDIT.md`](CLAUDE_MD_AUDIT.md), `CLAUDE.md §5` |
| Section 1 #3               | [`body_composition/development_issues.md`](body_composition/development_issues.md)                            |
| Section 1 #4               | [`E2E_TESTING.md`](E2E_TESTING.md), `ls e2e/*.spec.ts`                                                        |
| Section 1 #5               | [`CSS_OWNERSHIP_MAP.md`](CSS_OWNERSHIP_MAP.md), `ls static/css/`                                              |
| Section 1 #6               | [`workout_cool_integration/PLANNING.md`](workout_cool_integration/PLANNING.md), [`workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md`](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md), `wc -l data/youtube_curated_top_n.csv` |
| Section 1 #7               | [`workout_cool_integration/EXECUTION_LOG.md`](workout_cool_integration/EXECUTION_LOG.md)                       |
| Section 1 #8               | [`CHANGELOG.md`](CHANGELOG.md), `git log --oneline -10`                                                        |
| Section 1 #9               | [`ai_workflow/INDEX.md`](ai_workflow/INDEX.md), [`fatigue_meter/calibration-notes.md`](fatigue_meter/calibration-notes.md) |
| Section 1 #10              | [`docs/README.md`](README.md), [`VOLUME_TAXONOMY_AUDIT.md`](VOLUME_TAXONOMY_AUDIT.md)                          |
| Section 2 (#11, closed)    | [`UI_SCENARIOS_GAP_ANALYSIS.md §0`](UI_SCENARIOS_GAP_ANALYSIS.md) (KI-001 — resolved by deletion); deleted files: `utils/filter_cache.py`, `tests/test_filter_cache.py` |
| Section 3 #15              | [`fatigue_meter/PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md) (authoritative for Phase 2), [`fatigue_meter/PLANNING.md`](fatigue_meter/PLANNING.md), [`fatigue_meter/BRAINSTORM.md`](fatigue_meter/BRAINSTORM.md), [`fatigue_meter/STAGE4_PARKED_HANDOFF.md`](fatigue_meter/STAGE4_PARKED_HANDOFF.md) (superseded), [`fatigue_meter/calibration-notes.md`](fatigue_meter/calibration-notes.md) |
| Section 4 (#13, closed)    | [`workout_cool_integration/PLANNING.md §4.6`](workout_cool_integration/PLANNING.md), [`workout_cool_integration/EXECUTION_LOG.md`](workout_cool_integration/EXECUTION_LOG.md) (top entry); committed files: [`e2e/visual-baseline-thumbnails.spec.ts`](../e2e/visual-baseline-thumbnails.spec.ts), [`e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots/`](../e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots/) (18 PNGs) |
| Section 5 (#12, closed)    | [`workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md`](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md) "Curation Closed", [`workout_cool_integration/PLANNING.md §5.4`](workout_cool_integration/PLANNING.md), [`workout_cool_integration/EXECUTION_LOG.md`](workout_cool_integration/EXECUTION_LOG.md); committed source of truth: [`data/youtube_curated_top_n.csv`](../data/youtube_curated_top_n.csv) (56 rows + header) + `scripts/apply_youtube_curated.py`; commits `cf21191` + `ff244aa` |
| Section 6 (#14, closed)    | `git worktree list` (no worktrees other than `Hypertrophy-Toolbox-v3-main`), `git ls-remote --heads origin` (no `test/visual-baseline-thumbnails` or `redesign/calm-glass-2026` remaining); related squash-merge commits: `631b5f8` (PR #22) + `b5b8c7a` (later `toHaveScreenshot()` refactor) |
| Section 7                  | grep `TODO|FIXME` across `utils/`, `routes/`, `static/js/`                                                    |

---

## Effort Caveats

- Estimates assume a solo developer with this codebase already loaded.
- Figures cover code + tests + targeted Playwright, but **do not** include the full `/verify-suite` runtime (~3 min pytest + ~7 min full Chromium E2E sweep).
- Section 0 dirty-tree triage time depends entirely on owner direction. Best case (accept all 6 scopes as-is): ~1–2 hr to split commits + targeted tests. Worst case (revert + redo): hours-to-days per scope.
- Section 1 P0 docs effort assumes the dirty tree is already triaged. Several items become much cheaper if the underlying scopes landed cleanly.

---

*Last updated: 2026-05-24 (v10 — Phase 2 Stage 4 reframe). Sections 0 + 1 + 2 + 4 + 5 + 6 all closed. Remaining tracking item is Section 3 row #15 (Fatigue Phase 2 Stage 4 calibration window — earliest close 2026-06-07).*
