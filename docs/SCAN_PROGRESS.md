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

## ▶ RESUME AT: Phase 2 → utils/database.py

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

### [ ] Phase 2 — Data layer & schema (~2,290 LOC)
- [ ] utils/database.py (762)
- [ ] utils/db_initializer.py (655)
- [ ] utils/exercise_manager.py (201)
- [ ] utils/filter_predicates.py (193)
- [ ] utils/exercise_media.py (212)
- [ ] utils/media_path.py (137)
- [ ] utils/maintenance.py (129)

### [ ] Phase 3 — Volume & summary calculations (~2,900 LOC)
- [ ] utils/effective_sets.py (575)
- [ ] utils/weekly_summary.py (464)
- [ ] utils/session_summary.py (299)
- [ ] utils/volume_progress.py (507)
- [ ] utils/movement_patterns.py (506)
- [ ] utils/volume_taxonomy.py (327)
- [ ] utils/volume_classifier.py (105)
- [ ] utils/volume_ai.py (71)
- [ ] utils/volume_export.py (55)

### [x] Phase 4 — Fatigue, progression, log (~2,370 LOC) — agent-read, merged
- [x] utils/fatigue.py (751)
- [x] utils/fatigue_data.py (395)
- [x] utils/fatigue_context.py (389)
- [x] utils/progression_plan.py (481)
- [x] utils/body_fat.py (203)
- [x] utils/workout_log.py (153)

### [ ] Phase 5 — Estimator core (~2,420 LOC)
- [ ] utils/profile_estimator.py (2418)

### [ ] Phase 6 — Plan generation & calibration (~2,480 LOC)
- [ ] utils/plan_generator.py (1441)
- [ ] utils/strength_calibration.py (845)
- [ ] utils/lift_matching.py (195)

### [ ] Phase 7 — Backup, exports, misc utils (~1,350 LOC)
- [ ] utils/program_backup.py (722)
- [ ] utils/export_utils.py (458)
- [ ] utils/auto_backup.py (87)
- [ ] utils/__init__.py (80)

### [ ] Phase 8 — Routes: workout_plan + filters (~2,260 LOC)
- [ ] routes/workout_plan.py (1774)
- [ ] routes/filters.py (489)

### [ ] Phase 9 — Routes: profile / exports / progression (~1,940 LOC)
- [ ] routes/user_profile.py (877)
- [ ] routes/exports.py (673)
- [ ] routes/progression_plan.py (393)

### [ ] Phase 10 — Routes: remainder (~1,470 LOC)
- [ ] routes/body_composition.py (335)
- [ ] routes/volume_splitter.py (313)
- [ ] routes/workout_log.py (250)
- [ ] routes/program_backup.py (233)
- [ ] routes/weekly_summary.py (159)
- [ ] routes/session_summary.py (146)
- [ ] routes/fatigue.py (29)
- [ ] routes/main.py

### [ ] Phase 11 — Templates (~4,770 LOC, incl. inline JS)
- [ ] templates/workout_plan.html (856)
- [ ] templates/user_profile.html (648)
- [ ] templates/weekly_summary.html (621)
- [ ] templates/session_summary.html (495)
- [ ] templates/welcome.html (416)
- [ ] templates/base.html (311)
- [ ] templates/workout_log.html (292)
- [ ] templates/backup.html (227)
- [ ] templates/body_composition.html (220)
- [ ] templates/progression_plan.html (177)
- [ ] templates/volume_splitter.html (175)
- [ ] templates/fatigue.html (102)
- [ ] templates/_fatigue_muscle_bar.html (56)
- [ ] templates/_fatigue_badge.html (56)
- [ ] templates/partials/exercise_video_modal.html (52)
- [ ] templates/error.html (51)

### [ ] Phase 12 — JS: workout-plan cluster (~2,730 LOC)
- [ ] static/js/modules/workout-plan.js (2411)
- [ ] static/js/modules/exercises.js (269)
- [ ] static/js/modules/exercise-helpers.js (48)

### [ ] Phase 13 — JS: profile / muscle-map / media (~2,890 LOC)
- [ ] static/js/modules/user-profile.js (1483)
- [ ] static/js/modules/muscle-selector.js (817)
- [ ] static/js/modules/bodymap-svg.js (278)
- [ ] static/js/modules/exercise-video-modal.js (177)
- [ ] static/js/modules/exercise-image-preview.js (131)

### [ ] Phase 14 — JS: backup / volume-splitter (~2,480 LOC)
- [ ] static/js/modules/backup-center.js (1005)
- [ ] static/js/modules/volume-splitter.js (912)
- [ ] static/js/modules/plan_volume_panel.js (248)
- [ ] static/js/modules/program-backup.js (174)
- [ ] static/js/modules/exports.js (143)

### [ ] Phase 15 — JS: log / filters / dropdowns (~2,600 LOC)
- [ ] static/js/modules/workout-log.js (818)
- [ ] static/js/modules/filter-view-mode.js (725)
- [ ] static/js/modules/workout-dropdowns.js (646)
- [ ] static/js/modules/routine-cascade.js (414)

### [ ] Phase 16 — JS: progression / body-comp / tables / summary (~2,120 LOC)
- [ ] static/js/modules/progression-plan.js (573)
- [ ] static/js/table-responsiveness.js (514)
- [ ] static/js/modules/body-composition.js (490)
- [ ] static/js/modules/filters.js (348)
- [ ] static/js/modules/summary.js (133)
- [ ] static/js/modules/charts.js (59)

### [ ] Phase 17 — JS: app infra & shared (~2,010 LOC)
- [ ] static/js/app.js (298)
- [ ] static/js/modules/ui-handlers.js (443)
- [ ] static/js/modules/navbar-enhancements.js (316)
- [ ] static/js/modules/fetch-wrapper.js (263)
- [ ] static/js/accessibility.js (264)
- [ ] static/js/modules/workout-controls-animation.js (175)
- [ ] static/js/modules/toast.js (111)
- [ ] static/js/darkMode.js (81)
- [ ] static/js/modules/navbar.js (58)

### [ ] Phase 18 — CSS part 1: workout-plan + components (~12,740 LOC)
- [ ] static/css/pages-workout-plan.css (8226)
- [ ] static/css/components.css (4511)

### [ ] Phase 19 — CSS part 2: log / profile / layout / summaries (~10,240 LOC)
- [ ] static/css/pages-workout-log.css (3368)
- [ ] static/css/pages-user-profile.css (1843)
- [ ] static/css/layout.css (1841)
- [ ] static/css/pages-weekly-summary.css (1601)
- [ ] static/css/pages-session-summary.css (1587)

### [ ] Phase 20 — CSS part 3: navbar / welcome / volume / remainder (~6,900 LOC)
- [ ] static/css/navbar.css (1536)
- [ ] static/css/pages-welcome.css (1084)
- [ ] static/css/pages-volume-splitter.css (1059)
- [ ] static/css/a11y.css (813)
- [ ] static/css/theme-dark.css (621)
- [ ] static/css/pages-backup.css (497)
- [ ] static/css/tokens.css (433)
- [ ] static/css/pages-progression.css (341)
- [ ] static/css/pages-body-composition.css (324)
- [ ] static/css/base.css (123)
- [ ] static/css/motion.css (71)
- [ ] scss/_fatigue.scss (528)
- [ ] scss/pages/_workout_plan_volume_panel.scss (299)
- [ ] scss/custom-bootstrap.scss (53)

### [ ] Phase 21 — Tests: pytest suite (58 files)
- [ ] Read all tests/*.py; map coverage per subsystem (fill coverage matrix in findings)

### [ ] Phase 22 — E2E specs + build/CI config (28 specs + config)
- [ ] Read all e2e/*.spec.ts; note flakes/known-reds
- [ ] scripts/*.py (17), package.json, playwright.config, .github/workflows/*.yml, conftest.py

### [ ] Phase 23 — Synthesis → recommendations
- [ ] Cross-cutting themes from findings
- [ ] Validate / challenge each Phase in docs/REFACTOR_PLAN.md against what was actually read
- [ ] Produce prioritized recommendation set

---

## Run log
| Date | Phases advanced | Notes |
|---|---|---|
| 2026-07-03 | setup | worktree + tracker created; scan not yet started |
| 2026-07-03 | Phase 1 ✓ | entry points + cross-cutting read; 11 findings incl. shadowed error handlers (contradicts WP0.1), schema-init duplication (confirms WP2.4). Resume at Phase 2. |
| 2026-07-03 | Wave 1 dispatched | Phases 2–10 (Python core) running as 9 parallel Sonnet agents, each writing docs/scan/PHASE_NN.md. Orchestrator merges into SCAN_FINDINGS.md + ticks boxes as each returns. Boxes stay unchecked until each phase's findings file is verified. |
