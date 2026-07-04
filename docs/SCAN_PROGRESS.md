# Codebase Grounding Scan — Progress Tracker

**Purpose:** A genuine line-by-line read of the *entire* codebase, resumable across many
runs, so that any refactor recommendation rests on a full reading — not the grep
heuristics `docs/REFACTOR_PLAN.md` was built from. **No recommendations until every box
below is checked.**

- **Worktree:** `D:/development/HT-scan`  ·  **Branch:** `scan/codebase-grounding`  ·  **Base:** `b5e837d`
- **Findings accumulate in:** [`SCAN_FINDINGS.md`](SCAN_FINDINGS.md) (one section per phase)
- **Depth:** line-by-line, everything (owner decision 2026-07-03)

## How to resume (read this first every run)
1. Find the first phase below whose box is unchecked → that's the current phase.
2. Within it, the `▶ RESUME AT` marker names the exact next file to read.
3. Read the files in that phase, appending notes to `SCAN_FINDINGS.md §<phase>`.
4. Check each file's box as you finish it; move the `▶ RESUME AT` marker.
5. When every file in a phase is checked, tick the phase header and commit
   (`git add -A && git commit -m "scan: phase N — <area>"`).
6. Only after **Phase 23** is complete do you write recommendations.

**Legend:** `[ ]` not read · `[x]` read + notes captured · `(N)` = line count

---

## ✅ SCAN COMPLETE (23/23) — recommendations in [SCAN_RECOMMENDATIONS.md](SCAN_RECOMMENDATIONS.md)

---

### [x] Phase 1 — Entry points & cross-cutting (~1,300 LOC + docs)
- [x] app.py (327)
- [x] app_launcher.py (101)
- [x] utils/config.py
- [x] utils/logger.py (127)
- [x] utils/request_id.py (46)
- [x] utils/errors.py (259)
- [x] utils/constants.py (275)
- [x] utils/normalization.py (237)
- [x] Orientation docs: CLAUDE.md, docs/MASTER_HANDOVER.md read. NOTE: subsystem rules deferred to
      matching phases (database.md→P2, routes.md→P8, frontend.md→P12, testing.md→P21, debugging.md→P22);
      per-dir CLAUDE.md read at the start of each phase.

### [x] Phase 2 — Data layer & schema (~2,290 LOC)
- [x] utils/database.py (762)
- [x] utils/db_initializer.py (655)
- [x] utils/exercise_manager.py (201)
- [x] utils/filter_predicates.py (193)
- [x] utils/exercise_media.py (212)
- [x] utils/media_path.py (137)
- [x] utils/maintenance.py (129)

### [x] Phase 3 — Volume & summary calculations (~2,900 LOC)
- [x] utils/effective_sets.py (575)
- [x] utils/weekly_summary.py (464)
- [x] utils/session_summary.py (299)
- [x] utils/volume_progress.py (507)
- [x] utils/movement_patterns.py (506)
- [x] utils/volume_taxonomy.py (327)
- [x] utils/volume_classifier.py (105)
- [x] utils/volume_ai.py (71)
- [x] utils/volume_export.py (55)

### [x] Phase 4 — Fatigue, progression, log (~2,370 LOC) — agent-read, merged
- [x] utils/fatigue.py (751)
- [x] utils/fatigue_data.py (395)
- [x] utils/fatigue_context.py (389)
- [x] utils/progression_plan.py (481)
- [x] utils/body_fat.py (203)
- [x] utils/workout_log.py (153)

### [x] Phase 5 — Estimator core (~2,420 LOC)
- [x] utils/profile_estimator.py (2418)

### [x] Phase 6 — Plan generation & calibration (~2,480 LOC)
- [x] utils/plan_generator.py (1441)
- [x] utils/strength_calibration.py (845)
- [x] utils/lift_matching.py (195)

### [x] Phase 7 — Backup, exports, misc utils (~1,350 LOC)
- [x] utils/program_backup.py (722)
- [x] utils/export_utils.py (458)
- [x] utils/auto_backup.py (87)
- [x] utils/__init__.py (80)

### [x] Phase 8 — Routes: workout_plan + filters (~2,260 LOC)
- [x] routes/workout_plan.py (1774)
- [x] routes/filters.py (489)

### [x] Phase 9 — Routes: profile / exports / progression (~1,940 LOC)
- [x] routes/user_profile.py (877)
- [x] routes/exports.py (673)
- [x] routes/progression_plan.py (393)

### [x] Phase 10 — Routes: remainder (~1,470 LOC)
- [x] routes/body_composition.py (335)
- [x] routes/volume_splitter.py (313)
- [x] routes/workout_log.py (250)
- [x] routes/program_backup.py (233)
- [x] routes/weekly_summary.py (159)
- [x] routes/session_summary.py (146)
- [x] routes/fatigue.py (29)
- [x] routes/main.py

### [x] Phase 11 — Templates (~4,770 LOC, incl. inline JS)
- [x] templates/workout_plan.html (856)
- [x] templates/user_profile.html (648)
- [x] templates/weekly_summary.html (621)
- [x] templates/session_summary.html (495)
- [x] templates/welcome.html (416)
- [x] templates/base.html (311)
- [x] templates/workout_log.html (292)
- [x] templates/backup.html (227)
- [x] templates/body_composition.html (220)
- [x] templates/progression_plan.html (177)
- [x] templates/volume_splitter.html (175)
- [x] templates/fatigue.html (102)
- [x] templates/_fatigue_muscle_bar.html (56)
- [x] templates/_fatigue_badge.html (56)
- [x] templates/partials/exercise_video_modal.html (52)
- [x] templates/error.html (51)

### [x] Phase 12 — JS: workout-plan cluster (~2,730 LOC)
- [x] static/js/modules/workout-plan.js (2411)
- [x] static/js/modules/exercises.js (269)
- [x] static/js/modules/exercise-helpers.js (48)

### [x] Phase 13 — JS: profile / muscle-map / media (~2,890 LOC)
- [x] static/js/modules/user-profile.js (1483)
- [x] static/js/modules/muscle-selector.js (817)
- [x] static/js/modules/bodymap-svg.js (278)
- [x] static/js/modules/exercise-video-modal.js (177)
- [x] static/js/modules/exercise-image-preview.js (131)

### [x] Phase 14 — JS: backup / volume-splitter (~2,480 LOC)
- [x] static/js/modules/backup-center.js (1005)
- [x] static/js/modules/volume-splitter.js (912)
- [x] static/js/modules/plan_volume_panel.js (248)
- [x] static/js/modules/program-backup.js (174)
- [x] static/js/modules/exports.js (143)

### [x] Phase 15 — JS: log / filters / dropdowns (~2,600 LOC)
- [x] static/js/modules/workout-log.js (818)
- [x] static/js/modules/filter-view-mode.js (725)
- [x] static/js/modules/workout-dropdowns.js (646)
- [x] static/js/modules/routine-cascade.js (414)

### [x] Phase 16 — JS: progression / body-comp / tables / summary (~2,120 LOC)
- [x] static/js/modules/progression-plan.js (573)
- [x] static/js/table-responsiveness.js (514)
- [x] static/js/modules/body-composition.js (490)
- [x] static/js/modules/filters.js (348)
- [x] static/js/modules/summary.js (133)
- [x] static/js/modules/charts.js (59)

### [x] Phase 17 — JS: app infra & shared (~2,010 LOC)
- [x] static/js/app.js (298)
- [x] static/js/modules/ui-handlers.js (443)
- [x] static/js/modules/navbar-enhancements.js (316)
- [x] static/js/modules/fetch-wrapper.js (263)
- [x] static/js/accessibility.js (264)
- [x] static/js/modules/workout-controls-animation.js (175)
- [x] static/js/modules/toast.js (111)
- [x] static/js/darkMode.js (81)
- [x] static/js/modules/navbar.js (58)

### [x] Phase 18 — CSS part 1: workout-plan + components (~12,740 LOC)
- [x] static/css/pages-workout-plan.css (8226)
- [x] static/css/components.css (4511)

### [x] Phase 19 — CSS part 2: log / profile / layout / summaries (~10,240 LOC)
- [x] static/css/pages-workout-log.css (3368)
- [x] static/css/pages-user-profile.css (1843)
- [x] static/css/layout.css (1841)
- [x] static/css/pages-weekly-summary.css (1601)
- [x] static/css/pages-session-summary.css (1587)

### [x] Phase 20 — CSS part 3: navbar / welcome / volume / remainder (~6,900 LOC)
- [x] static/css/navbar.css (1536)
- [x] static/css/pages-welcome.css (1084)
- [x] static/css/pages-volume-splitter.css (1059)
- [x] static/css/a11y.css (813)
- [x] static/css/theme-dark.css (621)
- [x] static/css/pages-backup.css (497)
- [x] static/css/tokens.css (433)
- [x] static/css/pages-progression.css (341)
- [x] static/css/pages-body-composition.css (324)
- [x] static/css/base.css (123)
- [x] static/css/motion.css (71)
- [x] scss/_fatigue.scss (528)
- [x] scss/pages/_workout_plan_volume_panel.scss (299)
- [x] scss/custom-bootstrap.scss (53)

### [x] Phase 21 — Tests: pytest suite (58 files)
- [x] Read all tests/*.py; map coverage per subsystem (fill coverage matrix in findings)

### [x] Phase 22 — E2E specs + build/CI config (28 specs + config)
- [x] Read all e2e/*.spec.ts; note flakes/known-reds
- [x] scripts/*.py (17), package.json, playwright.config, .github/workflows/*.yml, conftest.py

### [x] Phase 23 — Synthesis → recommendations
- [x] Cross-cutting themes from findings (SCAN_FINDINGS.md bottom section)
- [x] Validate / challenge each Phase in docs/REFACTOR_PLAN.md against what was actually read
- [x] Produce prioritized recommendation set → [SCAN_RECOMMENDATIONS.md](SCAN_RECOMMENDATIONS.md)

**SCAN COMPLETE — 23/23.** Deliverable: [SCAN_RECOMMENDATIONS.md](SCAN_RECOMMENDATIONS.md).

---

## Run log
| Date | Phases advanced | Notes |
|---|---|---|
| 2026-07-03 | setup | worktree + tracker created; scan not yet started |
| 2026-07-03 | Phase 1 ✓ | entry points + cross-cutting read; 11 findings incl. shadowed error handlers (contradicts WP0.1), schema-init duplication (confirms WP2.4). Resume at Phase 2. |
| 2026-07-03 | Wave 1 dispatched | Phases 2–10 (Python core) running as 9 parallel Sonnet agents, each writing docs/scan/PHASE_NN.md. Orchestrator merges into SCAN_FINDINGS.md + ticks boxes as each returns. Boxes stay unchecked until each phase's findings file is verified. |
| 2026-07-03 | Phases 2,3,5–10 ✓ | Wave 1 complete: all 9 Python-core agents merged. Python source 100% read. REFACTOR_PLAN.md copied into worktree (was untracked → invisible to agents). Wave 2 (11–22) dispatching. |
| 2026-07-03 | Phases 11,13,14,17 ✓ | Wave 2 hit session limit; 4 of 12 files survived complete + merged. Phases 12,15,16,18-22 re-dispatched after reset. |
| 2026-07-03 | Phase 19 ✓ | CSS part 2 merged: summary bundles 99.1% identical ×4 copies; tokens.css load-order inversion; workout-log.css debt champion; user-profile.css = target template. |
| 2026-07-03 | Phases 12,15,16,18,20,21,22 ✓ | Wave 2 redispatch complete — ALL READING DONE (22/22). Key: WP3.4 split gaps; double-submit + triplicated-badge-logic bugs in log JS; @layer trap; siloed token namespaces; inverted backup test coverage; non-hermetic pytest files; vacuous E2E assertions; visual-helper class hardcoding. Next: Phase 23 synthesis. |
| 2026-07-03 | Phase 23 ✓ | SYNTHESIS COMPLETE — SCAN_RECOMMENDATIONS.md written: 12-item bug-fix track, per-WP plan amendments, 3 new CSS prerequisite WPs, execution order. Scan closed 23/23. |
