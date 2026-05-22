# Leftovers by Priority

> **Purpose:** Prioritized punch list of unfinished / parked / deferred items discovered in `docs/` and in the local working tree.
>
> **Review history:**
> - **v1 (2026-05-23, Opus):** initial clean-state backlog framing.
> - **v2 (Codex review):** flagged that the local tree is not clean — newer commits + large dirty working set overlap several backlog rows.
> - **v3 (Opus second-pass scan):** identified 6 distinct workstreams mixed in the dirty tree, including 2 unannounced navbar UX features; expanded the P0 docs-hygiene bucket.
> - **v4 (Codex re-review):** Opus + Codex agree. File rewritten to lead with in-flight work triage, then expanded P0 docs, then remaining backlog.
> - **v5 (2026-05-23, post-execution):** Owner accepted all six scopes; each landed as its own commit (`de3e4d0`, `18ad223`, `ef475cc`, `89561df`, `40d7dd2`, `0ae5b39`). Section 1 docs hygiene executed in a single doc-only commit on top of the six feature commits. Section 0 is fully resolved.
>
> **Current branch:** `main`, **9 commits ahead of `origin/main @ 94482d7`** as of v5. Working tree clean except for `data/database.db` (owner-approved runtime dirt). Awaiting `git push`.

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

## 2. Standalone P1 — Filter Cache Invalidation (after P0 docs)

| # | Item | Detail | Effort | Risk |
|---|---|---|---|---|
| 11 | **KI-001 — Filter cache invalidation** ([`utils/filter_cache.py:13`](../utils/filter_cache.py#L13)) | `invalidate_cache()` exists but is never called. Catalogue mutation paths `utils/exercise_manager.py::save_exercise()` (line 115) and `remove_exercise_by_name()` (line 165) do not call it. Wire it in. | **1–2 hr** | Low — single-user app, mutations are rare |

This is the cleanest standalone P1 in the repo right now. Independent of the dirty-tree triage and the docs refresh.

---

## 3. Remaining Backlog (still valid; only KI-001 is pending after Sections 0–1)

| #  | Pri       | Item                                                                                                                                                                       | Notes / status                                                                       | Effort     |
|----|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|------------|
| 12 | **P2**    | **workout.cool §5 curation — optional expansion beyond 36 rows**                                                                                                            | First batch shipped 2026-05-22 (`cf21191`, 36 rows). Long-tail rows still use search fallback. Content work only; no infrastructure changes needed. | +4–8 hr if expanding |
| 13 | **P3**    | **§4.6 pixel baselines** — lock in `toHaveScreenshot()` on the 18 visual-baseline thumbnails                                                                                | Layout has settled; turns inspection-only spec into a real regression guard.          | **2–3 hr** |
| 14 | **P4**    | **Worktree disposition** — `D:/development/Hypertrophy-Toolbox-v3-visual-baseline-s4` (`test/visual-baseline-thumbnails @ 99910a4`) + `D:/development/Hypertrophy-Toolbox-v3-redesign-calm-glass` (`ba519df`) | Disk hygiene only. Owner decision; do not delete without explicit approval.           | 15 min after decision |
| 15 | **Don't** | **Fatigue meter Phase 2** — decay, technique modifier, `/fatigue` page, multi-channel SFR, API endpoints                                                                    | Explicitly parked; Stage 4 closed 2026-05-20 with no threshold changes. Do not edit `utils/fatigue.py`, `tests/test_fatigue.py`, or `scripts/fatigue_calibration_report.py::SCENARIOS` without fresh owner override. | — |

### Rows #4, #5, #8, #9 — closed

All four were Section 0 in-flight scopes; they landed as commits `40d7dd2` (#4, scope E), `de3e4d0` (#5, scope A), `0ae5b39` (#8, scope F), and `18ad223` (#9, scope B) on 2026-05-23.

---

## 4. Low-Priority Code TODOs (for completeness; don't let these distract)

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
| Section 2 (#11)            | [`UI_SCENARIOS_GAP_ANALYSIS.md §0`](UI_SCENARIOS_GAP_ANALYSIS.md) (KI-001), `utils/filter_cache.py`, `utils/exercise_manager.py` |
| Section 3 #12              | [`workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md`](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md), `data/youtube_curated_top_n.csv` |
| Section 3 #13              | [`workout_cool_integration/PLANNING.md §4.6`](workout_cool_integration/PLANNING.md)                            |
| Section 3 #14              | [`MASTER_HANDOVER.md`](MASTER_HANDOVER.md) Open Decisions, [`ACTIVE_DEVELOPMENT.md:156-159`](ACTIVE_DEVELOPMENT.md#L156-L159) |
| Section 3 #15              | [`fatigue_meter/PLANNING.md`](fatigue_meter/PLANNING.md), [`fatigue_meter/STAGE4_PARKED_HANDOFF.md`](fatigue_meter/STAGE4_PARKED_HANDOFF.md) (superseded), [`fatigue_meter/calibration-notes.md`](fatigue_meter/calibration-notes.md) |
| Section 4                  | grep `TODO|FIXME` across `utils/`, `routes/`, `static/js/`                                                    |

---

## Effort Caveats

- Estimates assume a solo developer with this codebase already loaded.
- Figures cover code + tests + targeted Playwright, but **do not** include the full `/verify-suite` runtime (~3 min pytest + ~7 min full Chromium E2E sweep).
- Section 0 dirty-tree triage time depends entirely on owner direction. Best case (accept all 6 scopes as-is): ~1–2 hr to split commits + targeted tests. Worst case (revert + redo): hours-to-days per scope.
- Section 1 P0 docs effort assumes the dirty tree is already triaged. Several items become much cheaper if the underlying scopes landed cleanly.

---

*Last updated: 2026-05-23 (v5 — post-execution). Sections 0 + 1 closed (six feature commits + one docs-only commit on local `main`). Awaiting `git push` and the standalone KI-001 work in Section 2.*
