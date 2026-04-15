# Code Cleanup & Refactoring Plan

**Project:** Hypertrophy Toolbox v3
**Date:** 2026-04-10
**Scope:** Dead code removal, duplication consolidation, low-risk cleanup, and explicitly deferred semantic changes
**Safety Philosophy:** Every change follows the cycle: capture checkpoint → baseline tests → targeted edit → re-run tests → rollback on failure

** codex 5.4*** The safety loop is right, but I would avoid `git stash push` as the default rollback path in a potentially dirty worktree. For this repo, a safer rule is "capture a patch or commit a checkpoint before risky phases" so unrelated local work does not get buried during cleanup.

### Baseline Test Counts (current snapshot, must be re-recorded)
| Suite | Command | Expected |
|-------|---------|----------|
| pytest | `.venv/Scripts/python.exe -m pytest tests/ -q` | **938 passed, 1 skipped** (validated 2026-04-15 after Phase 5 test hardening) |
| Playwright summary surfaces | `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line` | **20 passed** (validated 2026-04-15 after summary UX follow-up close) |
| Full Playwright | `npx playwright test --project=chromium --reporter=line` | **315 passed** (latest recorded full run from Phase 4 close-out) |

> **Important:** These counts drift as tests are added/removed. Treat them as a snapshot, not an invariant. Always re-record in this environment before starting. For rollback, prefer a saved patch or checkpoint commit over `git stash push` in a dirty worktree.

** codex 5.4*** I would treat the `Expected` column as a snapshot, not an invariant. Test totals and pass counts drift quickly, so this section should emphasize "record current numbers in this environment" rather than using hardcoded pass counts as success criteria.

---

## Phase 0: Prerequisite Confidence Gate

> **Goal:** Reach ~95% execution confidence before any destructive cleanup starts.
>
> **Phase 0 exit criterion:** Treat this phase as complete only when the checklist evidence supports an estimated ~95% confidence to begin the low-risk cleanup path without functional, UI, flow, or performance regressions.

### 0.1 Checkpoint & Baseline Capture

- [x] Save a rollback checkpoint before risky edits:
  - [x] `git status --short | Tee-Object -FilePath cleanup_preflight_status.txt`
  - [x] `git diff --binary | Out-File -Encoding ascii cleanup_preflight.patch`
- [x] Re-record full pytest baseline:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q | Tee-Object -FilePath baseline_pytest.txt`
- [x] Re-record summary-surface browser baseline:
  - [x] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line | Tee-Object -FilePath baseline_summary_pages.txt`
- [x] If the upcoming phase touches templates, shared JS, or route contracts, re-record full Playwright first:
  - [x] `npx playwright test --project=chromium --reporter=line | Tee-Object -FilePath baseline_e2e_full.txt`

**Execution note (2026-04-10):** Rollback artifacts were written to `cleanup_preflight_status.txt` and `cleanup_preflight.patch`. Baselines revalidated at `981 passed, 1 skipped`, `21 passed`, and `315 passed` (Chromium full Playwright).

### 0.2 Package-Surface Decision (Required before deleting exported utils)

- [x] Audit package-style imports and references:
  - [x] `rg -n "from utils import|import utils\.|from utils\.(data_handler|business_logic|helpers|filters|database_init|muscle_group)" app.py routes tests e2e docs CLAUDE.md`
- [x] Record whether `utils/__init__.py` is treated as:
  - [ ] internal convenience only
  - [x] supported package surface
- [x] If this decision is not explicit, **do not** delete `utils/data_handler.py` or `utils/business_logic.py`.

**Decision (2026-04-10):** Phase 0 initially treated `utils/__init__.py` as a supported package surface because `app.py` imported from `utils`, `CLAUDE.md` documented package-level imports as acceptable, and `DataHandler` / `BusinessLogic` / package-level `get_workout_logs()` still appeared in docs or tests. A later explicit API retirement decision authorized `3b Wave 2`: `app.py` moved to `utils.db_initializer`, active docs were updated, the legacy exports were removed from `utils/__init__.py`, and the paired legacy modules/tests were retired with full pytest green at `930 passed, 1 skipped`.

### 0.3 Summary-Page Frontend Coupling Audit

- [x] Document the current ownership of summary-page updates before touching summary templates or JS:
  - [x] `static/js/app.js`
  - [x] `static/js/modules/summary.js`
  - [x] `templates/session_summary.html`
  - [x] `templates/weekly_summary.html`
  - [x] `e2e/summary-pages.spec.ts`
- [x] Confirm which updater path is authoritative for each page during this cleanup cycle.
- [x] Confirm whether the fallback module in `static/js/modules/summary.js` still depends on the presence of inline page updaters and/or `#counting-mode`.
- [x] Do not start template dedup or summary-page JS dedup until this ownership note is complete.

**Ownership note (2026-04-10):** The authoritative updater path for both summary pages is still the inline template functions: `updateWeeklySummary()` in `templates/weekly_summary.html` and `updateSessionSummary()` in `templates/session_summary.html`. `static/js/app.js` still calls `fetchWeeklySummary()` / `fetchSessionSummary()` on page init, but `static/js/modules/summary.js` immediately short-circuits when it sees an inline updater or `#counting-mode`. That means any template refactor must preserve the inline updater contract or replace the fallback guard in the same change. The weekly page also owns live `GET /api/pattern_coverage` rendering, which is asserted by `e2e/summary-pages.spec.ts`.

**Post-4M UX update (2026-04-11):** `#counting-mode` is no longer a summary-page UI contract. Weekly/Plan Summary and Session Summary now show both Effective Sets and Raw Sets directly in the table, so the Set Counting Mode selector and derived Active Sets column were removed to avoid presenting two competing counting models. `static/js/modules/summary.js` now short-circuits on the inline updater functions only.

### 0.4 Semantic-Change Test Gap Review

- [x] Before changing the `exercise_order` recalculation loop in `routes/exports.py`, confirm dedicated tests exist for:
  - [ ] successful recalculation
  - [ ] failure / rollback semantics
- [x] If those tests do not exist, create them first or defer that optimization to the last phase.

**Decision (2026-04-10):** Dedicated tests for the `exercise_order` recalculation branch are not present in `tests/test_exports.py` or E2E coverage. `3j` remains deferred and is not part of the Phase 0 go decision.

### 0.5 Frontend Orphan Audit

- [x] Audit likely orphan or legacy frontend files before backend cleanup starts:
  - [x] `static/js/modules/sessionsummary.js`
  - [x] `static/js/updateSummary.js`
- [x] Record whether each file is:
  - [ ] live
  - [ ] dormant but intentionally kept
  - [x] safe delete candidate

**Audit result (2026-04-10):**
- `static/js/modules/sessionsummary.js` has no repo references, still contains an embedded `<script>` wrapper, and uses an older `?method=` flow. Treat as a safe-delete candidate.
- `static/js/updateSummary.js` has no repo references and appears to be a tiny orphan helper. Treat as a safe-delete candidate.

### 0.6 Go / No-Go Gate

- [x] Proceed to Phase 1 only when:
  - [x] the baseline is green
  - [x] the package-surface decision is recorded
  - [x] the summary-page ownership audit is recorded
  - [x] the semantic-change test gap is closed or explicitly deferred
  - [x] rollback artifacts exist on disk
- [x] Treat a passing Phase 0 as authorization to start only the clearly low-risk path first:
  - [x] `3a`
  - [x] `3b Wave 1`
  - [x] `3c`
- [x] `3d`
- [x] `3e`
- [x] `3g`
- [x] Hold `3f` behind a separate frontend / visual go-no-go after `3e`, because it edits active summary templates.
- [x] Require a second explicit go / no-go decision before:
  - [x] `3b Wave 2` package-surface contraction
  - [x] `3j` export write-path semantic optimization

**Phase 0 outcome (2026-04-10):** initial `GO` for `3a`, `3b Wave 1`, `3c`, `3d`, `3e`, and `3g`; initial `HOLD` for `3f` pending a deliberate template-risk decision; `NO-GO` for `3b Wave 2` and `3j` until their prerequisite decisions/tests exist. The separate `3f` go decision and the later explicit API retirement decision for `3b Wave 2` were both granted, and `3f`, `3g`, and `3b Wave 2` are now complete.

---

## Status Dashboard (2026-04-10)

> **Tracking rule:** Update this dashboard after every completed phase so confidence, status, and go/no-go decisions stay visible at a glance.
>
> **Fresh agent? Start here:** if you need to know "what's next," skip to the **[Post-Phase-4 Handoff](#post-phase-4-handoff-2026-04-11)** section below. Do not interpret the checkboxes in `[Phase 3i]` / `[Phase 3j]` / `Execution Checklist` as an active to-do list — those sections are historical and superseded by the Stage Tracker plus `docs/phase5_3i_plan.md`.

### Overall Status

| Scope | Confidence now | Status | Notes |
|---|---:|---|---|
| `Phase 0` gate itself | `99%` | Completed | Baselines, rollback, package-surface, frontend ownership, and export-gap review were all executed. |
| Completed work: `3a` + `3b Wave 1` + `3b Wave 2` + `3c` + `3d` + `3e` + `3f` + `3g` | `99%` | Completed | Landed cleanly and validated. |
| Remaining approved low-risk path | `N/A` | Completed | The approved low-risk tranche is complete through `3g`; `3i` and `3j` were later retired by `docs/phase5_3i_plan.md`. |
| `3f` after the explicit frontend / visual go decision | `95-96%` | Completed | Selector-contract guardrails were strengthened first, the extraction stayed markup-only, and summary/full Chromium Playwright plus desktop/mobile visual checks passed. |
| `3b Wave 2` after the explicit package-surface retirement decision | `95-96%` | Completed | `app.py` moved to a concrete module import, `utils/__init__.py` dropped the retired legacy exports, `utils/business_logic.py` and `utils/data_handler.py` plus their dedicated tests were deleted, and full pytest stayed green. |
| `3j` after Phase 5 recovery | `95%+` | Completed | `debug/5I_test_hardening.md` added the missing tests and `debug/5J_recalculate_exercise_order.md` validated the intended atomic batch semantics. |
| Whole remaining program including all open phases | `N/A` | Split | `3i` and `3j` no longer block this cleanup plan; other open items, if any, remain tracked separately by their own artifacts. |

### Stage Tracker

| Stage | Confidence now | Status | Comment |
|---|---:|---|---|
| `Phase 0` | `99%` | Completed | Evidence-based go / no-go completed. |
| `3a` Remove unused imports | `99%` | Completed | Route import cleanup is complete and `pylint` `W0611` is clean. |
| `3b Wave 1` High-confidence deletions | `98-99%` | Completed | Dead internal modules removed safely. |
| `3c` Delete orphaned templates | `99%` | Completed | Six orphaned templates removed; smoke navigation and full pytest stayed green. |
| `3d` Extract parse functions | `99%` | Completed | Shared helpers landed, route compatibility wrappers were preserved, and targeted plus full pytest stayed green. |
| `3e` Summary-page coupling gate | `99%` | Completed | Inline summary-template updaters were re-confirmed as authoritative, the guarded fallback contract stayed intact, and summary Playwright re-passed. |
| `3f` Method-selector macro | `95-96%` | Completed | Stronger selector-contract tests landed first; the shared macro extraction preserved the inline updater contract and passed browser plus visual checks. |
| `3g` Backend-only classifier cleanup | `99%` | Completed | Landed as a backend-only helper refactor in `utils/volume_classifier.py`; public API stayed intact and the targeted pytest gate passed. |
| `3b Wave 2` Package-surface contraction | `95-96%` | Completed | Explicit API retirement decision granted; legacy package exports, modules, and paired tests were removed together, and full pytest stayed green. |
| `3j` Export write-path optimization | `95%+` | Completed | Retroactively validated by `docs/phase5_3i_plan.md` sub-phase 5J. See `debug/5J_recalculate_exercise_order.md`. |
| `3i` Large function decomposition | `95%+` | Completed | Retroactively validated by `docs/phase5_3i_plan.md` sub-phases 5A-5H. See `debug/5A_*.md`..`debug/5H_*.md` for per-function audits. |
| `Phase 4` Validation & regression | `N/A` | Completed | Closed via `phase4_option_c_plan.md`: audits ran, 4J orphan removal landed, 4M smoke failures were triaged, Progression was fixed forward in `ec748ba`, and the current full pytest baseline is `938 passed, 1 skipped` after Phase 5 test hardening. |

### Current Evidence Snapshot

| Check | Result |
|---|---|
| Seed DB restore browser verification | `pass` (`force=4`, `equipment=19`, `grips=10`, `stabilizers=24`, `synergists=26`, `exercise=1898`) |
| Full pytest during health checkpoint (`4C`) | `932 passed, 1 skipped` (`phase4c_pytest.txt`) |
| Summary-page Playwright during health checkpoint (`4D`) | `21 passed` (`phase4d_summary.txt`) |
| Full Chromium Playwright during health checkpoint (`4E`) | `315 passed` (`phase4e_full_e2e.txt`) |
| Hardening regression test (`4N`) | `2 passed` (`tests/test_seed_db_paths.py`) |
| Full pytest after seed-path hardening (`4N`) | `934 passed, 1 skipped` (`phase4n_seed_path_pytest.txt`) |
| Full pytest after Progression fixed-forward bugfix (`ec748ba`) | `936 passed, 1 skipped` |
| 4M manual smoke triage | Progression fixed forward in `ec748ba`; Weekly/Session summary counter UX resolved by `b058d19`, `73bc1eb`, and `571a365`; reverified 2026-04-15 with focused pytest and summary Playwright |
| Workout-plan Playwright after seed-path hardening (`4N`) | `17 passed` (`phase4n_seed_path_workout_plan_e2e.txt`) |
| Smoke-navigation Playwright after `3c` | `10 passed` |
| Full pytest after `3d` | `963 passed, 1 skipped` |
| Targeted pytest for `3d` shared-helper extraction | `163 passed` |
| Summary-page Playwright after `3e` | `21 passed` |
| Summary-page Playwright after `3f` | `21 passed` |
| Full Chromium Playwright after `3f` | `315 passed` |
| Desktop/mobile visual spot-check after `3f` | `4 screenshots reviewed` |
| Targeted pytest after `3g` backend-only classifier cleanup | `104 passed` |
| Full pytest after `3b Wave 2` package-surface retirement | `930 passed, 1 skipped` |
| Full pytest after `3c` | `959 passed, 1 skipped` |
| Full pytest after `3b Wave 1` | `959 passed, 1 skipped` |
| `tests/test_exports.py` after final `routes/exports.py` import cleanup | `35 passed` |
| `pylint --disable=all --enable=W0611` on touched routes | `10.00/10` |
| Full Chromium Playwright from Phase 0 | `315 passed` |
| Summary-page Playwright from Phase 0 | `21 passed` |

> **Note:** The current full-suite pytest snapshot is `938 passed, 1 skipped` after Phase 5 test hardening. Earlier `930`, `932`, `934`, and `936` snapshots were point-in-time results recorded after intermediate cleanup/hardening steps; the higher current count reflects later regression coverage, including the 4M Progression fixed-forward tests and the Phase 5 export-order characterization tests.

---

## Post-Phase-4 Handoff (2026-04-11)

> **Fresh agent entry point.** If you are landing on this file and need to know "what's next after Phase 4," **read this section first** — do not skim the rest of the plan looking for unchecked boxes. Several items in the body of this document are deferred for confidence reasons that are not obvious from the checklist state.
>
> **Why this section exists:** it was drafted after an Opus session ran out of tokens mid-conversation while walking the user through post-Phase-4 options. The full decision tree is in [phase4_option_c_plan.md §18](phase4_option_c_plan.md#18-post-4o-decision-tree--what-happens-after-phase-4-closes). This section is the short version and the entry point.

### Is Phase 4 closed?

| Signal | If present → | If absent → |
|---|---|---|
| `debug/4O_commit.txt` exists and references a `docs(4O): close spring-cleanup Phase 4` commit | Phase 4 is **closed**. Skip to "What's next" below. | Phase 4 is **not closed**. Go to `phase4_option_c_plan.md` and execute the next action starting from §17 "Fresh Session Kickoff Prompt". |
| `git tag -l phase4-rollback-point` returns a tag | Phase 4 is mid-execution. Resume via `phase4_option_c_plan.md`. | Tag has been cleaned up per 4O-5 → Phase 4 is fully closed. |
| Stage Tracker row for `Phase 4` in this file shows `Completed` | Phase 4 is closed. | Phase 4 is still in progress. |

### What's next (if Phase 4 is closed)

Execute in this order, stopping at the first item the user approves. **Do not start any of these without explicit user confirmation** — the user decides, not you.

1. **Merge `spring-cleanup` → `main`.** This is the baseline exit from Phase 4/5. Long-lived cleanup branches lose value over time.
2. **(Optional) db_seed_fix_plan.md Phase F** — `SEED_DB_PATH` retirement. Architectural cleanup, no user-visible payoff. Only if the user specifically asks.
3. **(Optional) `create_performance_indexes()` startup decision.** Still tracked as an open architectural question in CLAUDE.md Appendix C/current-risk notes.

**4M status update (2026-04-15):** no 4M summary bugs remain open. Progression was fixed forward in `ec748ba`; Weekly/Session summary counter UX was resolved by surfacing both Effective Sets and Raw Sets directly, removing the confusing Raw/Effective selector, and keeping only the Total/Direct contribution selector. Verified with `pytest tests/test_weekly_summary.py tests/test_session_summary.py tests/test_weekly_summary_routes.py tests/test_session_summary_routes.py -q` (`95 passed`) and `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line` (`20 passed`).

### What's NOT next — retired items that must not auto-resume

The following items previously appeared in this document as "deferred," "no-go," or with `[x]` checkbox marks. **Do not execute them directly.** They were deferred at 50-60% / 55-60% until `docs/phase5_3i_plan.md` split and validated them with per-sub-phase artifacts:

| Item | Confidence | Historical note | Current authority |
|---|---:|---|---|
| `3i` Large function decomposition | **95%+** | Was deferred at **50-60%** because it bundled multiple unrelated high-blast-radius refactors. The `[x]` marks under `[Phase 3i]` were a known plan self-inconsistency. | Retroactively validated by `docs/phase5_3i_plan.md` sub-phases 5A-5H. See `debug/5A_*.md`..`debug/5H_*.md`. |
| `3j` Export write-path optimization | **95%+** | Was deferred at **55-60%** because it would alter write semantics without dedicated tests proving intended behavior. | Retroactively validated by `docs/phase5_3i_plan.md` sub-phase 5J after 5I test hardening. See `debug/5I_test_hardening.md` and `debug/5J_recalculate_exercise_order.md`. |

**Both items are now retired from this document's executable checklist.** Running them directly from this document's `[Phase 3i]` / `[Phase 3j]` checklists would re-run historical work. See `docs/phase5_3i_plan.md` for the executed audit trail.

### Anti-patterns (do not do any of these without explicit user instruction)

- Execute `3i-a..3i-h` just because the historical `[Phase 3i]` checklist had `[x]` marks. Those marks are superseded by `docs/phase5_3i_plan.md` and the `debug/5A_*.md`..`debug/5H_*.md` exit artifacts.
- Interpret this file as a to-do list with unchecked boxes that must be drained. The checklist state is a historical artifact; the Stage Tracker + this Post-Phase-4 Handoff section are the authoritative "what to do next" source.
- Roll back a 3a–3h cleanup commit to "fix" a 4M bug without first running the regression-check block in [phase4_option_c_plan.md §10 4M-3](phase4_option_c_plan.md#4m-3--record-failures-as-triage-entries-if-any). Pre-existing bugs (most 4M findings are) must be fixed forward.
- Delete the `debug/` directory — it is the Phase 4 audit trail.

### Reporting format when you land here as a fresh agent

Your first reply to the user should be:

```
Read docs/code_cleanup_plan.md Post-Phase-4 Handoff section.

Phase 4 status: <closed per debug/4O_commit.txt at <hash>> OR <in progress, next action = 4X-Y>

If closed, remaining open items:
  1. Merge spring-cleanup → main (ready)
  2. 4M bugs: closed as of 2026-04-15
  3. 3i/3j retired by docs/phase5_3i_plan.md (do not auto-resume)
  4. db_seed Phase F deferred
  5. create_performance_indexes() open question from CLAUDE.md Appendix C

Which would you like to start with?
```

Do not start work without an explicit "go."

---

## Confidence Recovery Plan (<95% Phases)

> **Goal:** Convert every sub-`95%` phase into either:
> 1. an execution-ready phase with explicit prerequisites and validation, or
> 2. a deliberately deferred / re-scoped phase that no longer blocks the safe cleanup path.

### Recovery Matrix

| Phase | Current Confidence | Why It Is Below 95% | What Must Happen To Reach ~95% |
|---|---:|---|---|
| `3f` Extract descoped method-selector macro | `95-96%` | No longer below `95%`: the contract-preserving extraction is complete and validated | None in the current cycle |
| `3b Wave 2` Package-surface contraction | `95-96%` | No longer below `95%`: the explicit API retirement decision was granted and validated | None in the current cycle |
| `3j` Export write-path optimization | `95%+` | No longer below `95%`: `debug/5I_test_hardening.md` added the missing characterization coverage and `debug/5J_recalculate_exercise_order.md` validated the intended semantics | None in the current cycle |
| `3i` Bloated-function decomposition | `95%+` | No longer below `95%`: `docs/phase5_3i_plan.md` split the bundled work into one-function validation sub-phases 5A-5H | None in the current cycle |

### Recovery Plan for `3f` — Jinja Method-Selector Macro

**Execution status:** completed on `2026-04-10` at `95%+`

- [x] Complete `3e` first and convert its ownership note into a hard contract for this phase:
  - [x] Preserve `id="counting-mode"` on both summary pages
  - [x] Preserve `id="contribution-mode"` on both summary pages
  - [x] Preserve `onchange="updateWeeklySummary()"` in `templates/weekly_summary.html`
  - [x] Preserve `onchange="updateSessionSummary()"` in `templates/session_summary.html`
  - [x] Preserve the `.method-selector` wrapper and current label / option text
  - [x] Leave both volume-legend blocks page-specific; do not widen the extraction beyond the selector block
- [x] Add browser guardrails before the template refactor:
  - [x] Extend `e2e/summary-pages.spec.ts` to assert both pages still render the selector labels and options exactly as expected after extraction
  - [x] Assert both pages still expose `#counting-mode` and `#contribution-mode`, because `static/js/modules/summary.js` uses those as part of its fallback short-circuit
  - [x] Assert changing each selector still triggers the expected fetch-backed update flow on both pages
  - [x] Keep the existing `GET /api/pattern_coverage` assertions green on the weekly page
- [x] Constrain the implementation so the change stays markup-only:
  - [x] Create a partial that accepts only `update_function_name`
  - [x] Do not rename `updateWeeklySummary()` or `updateSessionSummary()`
  - [x] Do not touch `static/js/app.js`
  - [x] Do not touch `static/js/modules/summary.js`
  - [x] Do not change any page-specific legend text, warning copy, or formula copy in this phase
- [x] Add a validation gate that must pass before the phase is considered `95%` safe:
  - [x] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`
  - [x] `npx playwright test --project=chromium --reporter=line`
  - [x] Desktop visual spot-check of both summary pages
  - [x] Mobile-width visual spot-check of both summary pages

**Execution note (2026-04-10):** The stronger Playwright guardrails were added before the template extraction, then the shared `method_selector` macro was introduced in `templates/partials/_volume_controls.html` and wired into both summary templates without widening the change beyond the selector block. The inline updater contract remained intact, the summary suite re-passed at `21 passed`, the full Chromium suite re-passed at `315 passed`, and desktop/mobile screenshots of both summary pages were reviewed.

### Recovery Plan for `3b Wave 2` — Package-Surface Contraction

**Execution status:** completed on `2026-04-10` at `95%+` after an explicit API retirement decision.

- [x] Record the explicit retirement decision for package-surface legacy names:
  - [x] `DataHandler`
  - [x] `BusinessLogic`
  - [x] package-level `get_workout_logs()`
- [x] Stop treating `utils/__init__.py` as the authoritative import surface for this work:
  - [x] `app.py` now imports `initialize_database` from `utils.db_initializer`
  - [x] `CLAUDE.md` now directs new code toward concrete module imports
- [x] Remove the retired package exports and paired legacy modules/tests in one change set:
  - [x] Drop `DataHandler` and `BusinessLogic` from `utils/__init__.py`
  - [x] Remove the package-level `get_workout_logs()` compatibility export
  - [x] Delete `utils/business_logic.py` and `tests/test_business_logic.py`
  - [x] Delete `utils/data_handler.py` and `tests/test_data_handler.py`
- [x] Write a release / migration note for the package-surface removal
- [x] Validation gate:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `930 passed, 1 skipped`

**Execution note (2026-04-10):** The explicit API retirement decision was granted after a repo-wide zero-caller audit for `DataHandler`, `BusinessLogic`, and package-level `get_workout_logs()`. `app.py` moved off the package import surface, `utils/__init__.py` dropped the retired exports, active docs were updated to stop treating package-level re-exports as authoritative, the legacy modules and their dedicated tests were deleted together, and the full pytest suite stayed green at `930 passed, 1 skipped`.

### Recovery Plan for `3j` — Export Write-Path Optimization

**Status:** Superseded by `docs/phase5_3i_plan.md` — see that file §5I and §5J for the executed test-hardening and batch-update validation sub-phases.

**Result:** `3j` reached `95%+` after `debug/5I_test_hardening.md` added the missing characterization coverage and `debug/5J_recalculate_exercise_order.md` validated the intended atomic batch semantics.

### Recovery Plan for `3i` — Bloated-Function Decomposition

**Status:** Superseded by `docs/phase5_3i_plan.md` — see that file §5 for the executed one-function sub-phases.

**Result:** `3i` reached `95%+` after `debug/5A_*.md` through `debug/5H_*.md` validated the individual decomposition targets one at a time.

### Recommended Order For Confidence Recovery Work

- [x] First: finish the remaining already-approved path (`3g`)
- [x] Second: revisit `3f` with the tightened browser / visual guardrails above
- [x] Third: explicitly retire the `3b Wave 2` package surface after a zero-caller audit, paired test deletion, and migration note
- [x] Fourth: `docs/phase5_3i_plan.md` added/hardened export-path tests before validating `3j`
- [x] Fifth: `docs/phase5_3i_plan.md` replaced the bundled `3i` phase with one-function validation sub-phases

---

## Phase 1: Discovery & Analysis

### 1.1 Tools & Methods

| Tool | Purpose | Command |
|------|---------|---------|
| **vulture** | Detect unused Python code (functions, variables, imports) | `vulture routes/ utils/ --min-confidence 80` |
| **pylint** | Detect unused imports specifically | `pylint --disable=all --enable=W0611 routes/ utils/` |
| **rg** | Trace callers of suspect modules/functions | `rg -n "from utils\.business_logic|import utils\.business_logic|BusinessLogic" routes utils tests app.py` |
| **IDE Find Usages** | Confirm zero callers before deletion (VSCode: right-click → Find All References) | Manual |
| **Template cross-ref** | Find orphaned templates | `rg -n "render_template|include|extends" routes templates` + `Get-ChildItem templates -File` |
| **JS import audit** | Find orphaned JS modules | `rg -n "import .* from|<script" static templates` + `Get-ChildItem static/js -Recurse -File *.js` |

** codex 5.4*** This runbook mixes Windows-only paths like `.venv/Scripts/...` with Unix tooling like `grep`, `find`, `wc`, `ls`, and `xargs`. Since the repo is being worked from PowerShell, I would rewrite these commands to `rg` plus PowerShell equivalents so the plan is executable as written.

### 1.2 Directory Scan Checklist

- [ ] **`routes/`** — Scan all 10 route files for: unused imports, dead functions, raw `print()` calls, inconsistent error response formats
- [ ] **`utils/`** — Scan all utility files for: unused classes/functions, raw `get_db_connection()` usage, raw `print()` calls, stale re-exports
- [ ] **`templates/`** — Cross-reference all 15 templates against `render_template()` calls and `{% include %}` / `{% extends %}` directives
- [ ] **`static/js/modules/` and `static/js/*.js`** — Cross-reference all JS modules against `import` statements in `app.js` and `<script>` tags in templates
- [ ] **`tests/`** — Identify test files that only test dead modules (scheduled for removal alongside module deletion)
- [ ] **`utils/__init__.py`** — Audit every item in `__all__` for actual downstream usage in `routes/` or `tests/`

** codex 5.4*** I would widen this checklist to include top-level `static/js/*.js`, not only `static/js/modules/`. `static/js/modules/sessionsummary.js` looks like a legacy artifact and even contains literal `<script>` tags, while `static/js/updateSummary.js` is also a likely orphan candidate.

---

## Phase 2: Categorization of Issues

### 2.1 Master Issue Table

| # | Issue Type | Impact | Affected Files | Fix Strategy |
|---|-----------|--------|----------------|--------------|
| 1 | ~~**Legacy module / package-surface candidate**~~ | ~~Medium~~ **Resolved** | ~~`utils/business_logic.py`, `tests/test_business_logic.py`~~ — deleted in `3b Wave 2` on 2026-04-10 | Explicit API retirement decision granted; no further action needed |
| 2 | ~~**Legacy module / package-surface candidate**~~ | ~~Medium~~ **Resolved** | ~~`utils/data_handler.py`, `tests/test_data_handler.py`~~ — deleted in `3b Wave 2` on 2026-04-10 | Explicit API retirement decision granted; no further action needed |
| 3 | ~~**Dead module** (superseded)~~ | ~~Medium~~ **Resolved** | ~~`utils/database_init.py`~~ — deleted in `3b Wave 1` on 2026-04-10 | No further action needed |
| 4 | ~~**Dead module** (deprecated wrapper)~~ | ~~Medium~~ **Resolved** | ~~`utils/filters.py`~~ — deleted in `3b Wave 1` on 2026-04-10 | No further action needed |
| 5 | ~~**Dead module** (legacy, only self-tested)~~ | ~~Medium~~ **Resolved** | ~~`utils/muscle_group.py`, `tests/test_muscle_group.py`~~ — deleted in `3b Wave 1` on 2026-04-10 | No further action needed |
| 6 | ~~**Dead module** (redundant re-export shim + broken import)~~ | ~~High~~ **Resolved** | ~~`utils/helpers.py`~~ — deleted in `3b Wave 1` on 2026-04-10 | No further action needed |
| 7 | ~~**Stale re-exports** in package init~~ | ~~Low~~ **Resolved** | ~~`utils/__init__.py` legacy package exports~~ — retired in `3b Wave 2` on 2026-04-10 | `DataHandler`, `BusinessLogic`, and package-level `get_workout_logs()` were removed after the explicit API retirement decision |
| 8 | ~~**Unused imports** in routes~~ | ~~Low~~ **Resolved** | ~~`routes/exports.py:1,5-6,9,19`~~ — plus `Response` / `jsonify` removed on 2026-04-10 after `pylint` install | No further action needed |
| 9 | ~~**Unused import** in routes~~ | ~~Low~~ **Resolved** | ~~`routes/weekly_summary.py:8`~~ — removed in `3a` on 2026-04-10 | No further action needed |
| 10 | ~~**Orphaned templates** (not rendered by any route)~~ | ~~Low~~ **Resolved** | ~~`templates/dropdowns.html`, `templates/filters.html`, `templates/table.html`, `templates/exercise_details.html`, `templates/debug_modal.html`, `templates/workout_tracker.html`~~ — deleted in `3c` on 2026-04-10 | No further action needed |
| 11 | ~~**Duplicated parse functions** (character-identical)~~ | ~~Medium~~ **Resolved** | ~~`routes/session_summary.py:19-30`, `routes/weekly_summary.py:21-32`~~ — centralized in `utils/effective_sets.py` with compatibility wrappers preserved in `3d` on 2026-04-10 | No further action needed in the current cycle |
| 12 | **Duplicated template HTML** (~23 lines after descoping) | Medium | `templates/session_summary.html`, `templates/weekly_summary.html` | Extract `method_selector` only, and only after the summary-page frontend ownership gate is documented |
| 13 | **Volume classifier** — backend duplication only | Low | `utils/volume_classifier.py:10-35` | Backend-only consolidation first; leave template and JS threshold copies untouched this cycle |
| 14 | **N+1 UPDATE loop / semantic change** | High | `routes/exports.py:359-373` | Add dedicated success + rollback tests first; move to the last phase; treat as intentional semantic change |
| 15 | ~~**Raw `get_db_connection()` bypassing DatabaseHandler**~~ | ~~Medium~~ **Resolved** | ~~`utils/volume_export.py:8`, `routes/volume_splitter.py:154,199,234`, `utils/user_selection.py:34`~~ — migrated in DOCS_AUDIT_PLAN Tier 3. **Only** `utils/database_indexes.py:51` remains: intentional raw access with manual `_DB_LOCK` for PRAGMA operations (documented, not a violation). | No further action needed |
| 16 | ~~**`print()` instead of `get_logger()`**~~ | ~~Medium~~ **Historical / Resolved** | See archived audit execution notes | No further action needed in the current codebase |
| 17 | **Bloated functions** (>130 lines) | Medium | `routes/exports.py:export_to_excel` (338 lines), `routes/workout_plan.py:replace_exercise` (230 lines), `utils/session_summary.py:calculate_session_summary` (256 lines), `utils/export_utils.py:create_excel_workbook` (227 lines), `utils/progression_plan.py:generate_progression_suggestions` (224 lines) | Extract sub-functions through re-scoped `3i` one-function sub-phases |
| 18 | **Duplicated SQL JOIN** (user_selection + exercises) | Medium | `utils/session_summary.py:55-71`, `utils/weekly_summary.py:62-76`, `utils/user_selection.py:31` | Revisit only if the remaining live call sites are worth consolidating after the legacy module deletions |
| 19 | **Summary-page dual updater ownership** | High | `static/js/app.js`, `static/js/modules/summary.js`, `templates/session_summary.html`, `templates/weekly_summary.html` | Add prerequisite ownership audit; do not refactor summary templates or JS until one active updater path is documented |

** codex 5.4*** That distinction mattered: `#1` and `#2` were only executed after the explicit API retirement decision, paired test deletion, doc updates, and a green full-suite pytest run on 2026-04-10.

### 2.2 Code Smell Definitions

| Smell | Description | Detection Method |
|-------|-------------|-----------------|
| **Dead Import** | `import X` or `from X import Y` where `Y` is never referenced in the file | `pylint --enable=W0611` or `vulture` |
| **Dead Module** | Entire `.py` file with zero callers in production code (`routes/`, `app.py`) | `rg -n "from utils\.module_name|import utils\.module_name" routes app.py` returns empty |
| **Orphaned Asset** | Template/JS/CSS file not referenced by any route, `include`, or `import` | Cross-reference `render_template` calls, `{% include %}` directives, and JS `import` statements |
| **Code Duplication** | Identical or near-identical logic in 2+ locations | Manual review; `jscpd` for automated clone detection |
| **N+1 Query** | DB query executed inside a loop, where a single batch query would suffice | Search for `for.*:` followed by `db.execute_query` or `db.fetch_one` within loop body |
| **Bloated Function** | Function exceeding ~80 lines, typically handling multiple concerns | Manual/editor line count on function bodies; functions >130 lines are priority targets |
| **Inconsistent Abstraction** | Using raw `sqlite3.connect()` or `get_db_connection()` instead of `DatabaseHandler` | `rg -n "get_db_connection|sqlite3\.connect" routes utils` |
| **Print-as-Logging** | Using `print()` instead of the project's `get_logger()` pattern | `rg -n "print\(" routes utils -g "*.py"` |

---

## Phase 3: Execution Strategy

> **Golden Rule:** After every discrete change (one file edit or one file deletion), run the relevant test file. After completing each sub-phase, run the full pytest suite. Never batch multiple untested changes.

** codex 5.4*** I like the bias toward small validated steps. One tweak: for deletion phases, define the verification query first, save its output, then delete, then rerun tests. That gives you stronger evidence than "grep came back empty once" when you later review why a file was removed.

### 3a. Remove Unused Imports

**Estimated impact:** ~10 lines removed across 2 files

- [x] **`routes/exports.py`** — Remove 5 unused imports
- [x] **`routes/weekly_summary.py`** — Remove dead `BusinessLogic` import
- [x] Confirm import cleanup by validation:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_weekly_summary.py -q`
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - [x] `.\.venv\Scripts\python.exe -m pylint --disable=all --enable=W0611 routes/exports.py routes/weekly_summary.py`
  - [x] Import audit: `rg -n "make_response|sanitize_filename|create_content_disposition_header|should_use_streaming|^import logging$|BusinessLogic|\\bResponse\\b|\\bjsonify\\b" routes/exports.py routes/weekly_summary.py` returns no import matches

**Execution note (2026-04-10):** `pylint` was installed into the project `.venv` during the cleanup session. It surfaced two additional unused imports in `routes/exports.py` (`Response`, `jsonify`), which were removed immediately and revalidated.

#### Before / After: `routes/exports.py`

```python
# BEFORE (lines 1-19)
from flask import Blueprint, Response, jsonify, request, make_response
from utils.export_utils import (
    create_excel_workbook,
    sanitize_filename,
    create_content_disposition_header,
    generate_timestamped_filename,
    stream_excel_response,
    should_use_streaming,
    MAX_EXPORT_ROWS
)
from utils.weekly_summary import (
    calculate_exercise_categories,
    calculate_isolated_muscles_stats,
    calculate_weekly_summary
)
from utils.errors import error_response, success_response
from utils.logger import get_logger
import logging

# AFTER
from flask import Blueprint, request
from utils.export_utils import (
    create_excel_workbook,
    generate_timestamped_filename,
    stream_excel_response,
    MAX_EXPORT_ROWS
)
from utils.weekly_summary import (
    calculate_exercise_categories,
    calculate_isolated_muscles_stats,
    calculate_weekly_summary
)
from utils.errors import error_response, success_response
from utils.logger import get_logger
```

#### Before / After: `routes/weekly_summary.py`

```python
# BEFORE (line 8)
from utils.business_logic import BusinessLogic

# AFTER
# (line deleted entirely)
```

**Validation:** `python -m pytest tests/test_exports.py tests/test_weekly_summary.py -q`

---

### 3b. Delete Dead Modules

**Estimated impact:** split into a safe Wave 1 and a guarded Wave 2 package-surface contraction.

#### Wave 1 — high-confidence internal deletions

- [x] **Step 1:** Confirm Phase 0 package-surface decision still allows Wave 1 deletions to be treated as internal-only cleanup.
- [x] **Step 2:** Remove dead import in `routes/weekly_summary.py:8`
  - [x] Confirm this was completed in Phase 3a before deleting any legacy module files.
- [x] **Step 3:** Delete `utils/helpers.py`
  - Rationale: strict subset of `utils/__init__.py`; also imports nonexistent `get_weekly_summary`
  - Verify first: `rg -n "from utils\.helpers|import utils\.helpers" app.py routes utils tests e2e`
- [x] **Step 4:** Delete `utils/filters.py`
  - Rationale: deprecated wrapper around `filter_predicates.py`
  - Verify first: `rg -n "from utils\.filters|import utils\.filters|ExerciseFilter" app.py routes utils tests e2e`
- [x] **Step 5:** Delete `utils/database_init.py`
  - Rationale: superseded by `utils/db_initializer.py`
  - Verify first: `rg -n "from utils\.database_init|import utils\.database_init|database_init" app.py routes utils tests e2e`
- [x] **Step 6:** Treat `utils/muscle_group.py` as Wave 1.5 only if it remains test-only after re-grep
  - Verify first: `rg -n "MuscleGroupHandler|from utils\.muscle_group|import utils\.muscle_group" app.py routes utils tests e2e`
  - [x] If deleted, delete `tests/test_muscle_group.py` in the same change
  - [ ] If not clearly safe, defer instead of forcing deletion
- [x] **Step 7:** Update docs and architecture notes that mention any Wave 1 deletions in the same branch (`CLAUDE.md`, plan docs, legacy inventories)
- [x] **Step 8:** Validate Wave 1 with full pytest:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

**Execution note (2026-04-10):** Wave 1 deleted `utils/helpers.py`, `utils/filters.py`, `utils/database_init.py`, `utils/muscle_group.py`, and `tests/test_muscle_group.py`. The post-Wave full-suite snapshot is now `959 passed, 1 skipped`; the drop from the Phase 0 baseline is expected because one dedicated legacy-module test file was intentionally removed.

#### Wave 2 — guarded package-surface contraction

- [x] **Step 9:** Record an explicit decision for `utils/__init__.py` package exports:
  - [x] `DataHandler` retired
  - [x] `BusinessLogic` retired
  - [x] package-level `get_workout_logs()` retired
- [x] **Step 10:** Edit `utils/__init__.py` after the explicit retirement decision:
  - [x] Remove `from .data_handler import DataHandler`
  - [x] Remove `from .business_logic import BusinessLogic`
  - [x] Remove `"DataHandler"` and `"BusinessLogic"` from `__all__`
  - [x] Remove the package-level `get_workout_logs()` compatibility export
- [x] **Step 11:** Delete `utils/business_logic.py` only after all of the following are true
  - [x] `routes/weekly_summary.py` dead import removed
  - [x] Repo-wide grep showed no supported runtime callers
  - [x] `tests/test_business_logic.py` was deleted in the same change
- [x] **Step 12:** Delete `utils/data_handler.py` only after all of the following are true
  - [x] package-surface retirement decision was recorded
  - [x] Repo-wide grep showed no supported runtime callers
  - [x] `tests/test_data_handler.py` was deleted in the same change
- [x] **Step 13:** Re-run full pytest after Wave 2 deletion work:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `930 passed, 1 skipped`

**Execution note (2026-04-10):** Wave 2 executed only after an explicit package-surface retirement decision. `app.py` moved to a direct `utils.db_initializer` import, `utils/__init__.py` dropped the retired legacy exports, the paired legacy modules/tests were deleted together, a migration note was added, and the full pytest suite stayed green at `930 passed, 1 skipped`.

---

### 3c. Delete Orphaned Templates

**Estimated impact:** 6 files deleted

- [x] Verify each template has no `render_template`, `{% include %}`, or `{% extends %}` references:
  ```powershell
  rg -n "dropdowns\.html|filters\.html|table\.html|exercise_details\.html|debug_modal\.html|workout_tracker\.html" routes templates static tests e2e
  ```
- [x] Delete `templates/dropdowns.html`
- [x] Delete `templates/filters.html`
- [x] Delete `templates/table.html`
- [x] Delete `templates/exercise_details.html`
- [x] Delete `templates/debug_modal.html`
- [x] Delete `templates/workout_tracker.html`
- [x] Run E2E smoke navigation tests: `npx playwright test e2e/smoke-navigation.spec.ts --project=chromium --reporter=line`
- [x] Re-run full pytest after sub-phase completion:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

**Execution note (2026-04-10):** All six candidate templates were confirmed orphaned by repo-wide `rg` audit before deletion. Post-delete validation passed with `10` green smoke-navigation browser tests and `959 passed, 1 skipped` in full pytest.

---

### 3d. Extract Duplicated Parse Functions (DRY)

**Estimated impact:** modest deduplication, but tests currently import the route-local helpers directly.

- [x] Add `parse_counting_mode()` and `parse_contribution_mode()` to `utils/effective_sets.py`
- [x] Update both route files to use the shared implementation
- [x] **Preferred safe path:** keep `_parse_counting_mode()` and `_parse_contribution_mode()` in both routes as thin compatibility wrappers for one cleanup cycle
  - [x] Existing route tests import these helpers directly and stayed green without test rewrites
- [x] Add or refresh direct tests for the new shared helpers in `tests/test_effective_sets.py`
- [x] Only if wrappers are intentionally removed later, update `tests/test_session_summary_routes.py` and `tests/test_weekly_summary_routes.py` in the same change set

#### Before (identical in both files):

```python
# routes/session_summary.py:19-30 AND routes/weekly_summary.py:21-32
def _parse_counting_mode(value: str) -> CountingMode:
    """Parse counting mode from request parameter."""
    if value and value.lower() == 'raw':
        return CountingMode.RAW
    return CountingMode.EFFECTIVE

def _parse_contribution_mode(value: str) -> ContributionMode:
    """Parse contribution mode from request parameter."""
    if value and value.lower() == 'direct':
        return ContributionMode.DIRECT_ONLY
    return ContributionMode.TOTAL
```

#### After:

```python
# utils/effective_sets.py (append to existing file)
def parse_counting_mode(value: str) -> CountingMode:
    """Parse counting mode from request query parameter."""
    if value and value.lower() == 'raw':
        return CountingMode.RAW
    return CountingMode.EFFECTIVE

def parse_contribution_mode(value: str) -> ContributionMode:
    """Parse contribution mode from request query parameter."""
    if value and value.lower() == 'direct':
        return ContributionMode.DIRECT_ONLY
    return ContributionMode.TOTAL
```

```python
# routes/session_summary.py — updated import
from utils.effective_sets import (
    CountingMode,
    ContributionMode,
    parse_counting_mode as shared_parse_counting_mode,
    parse_contribution_mode as shared_parse_contribution_mode,
)

def _parse_counting_mode(value: str) -> CountingMode:
    return shared_parse_counting_mode(value)

def _parse_contribution_mode(value: str) -> ContributionMode:
    return shared_parse_contribution_mode(value)

# routes/weekly_summary.py — same import
from utils.effective_sets import (
    CountingMode,
    ContributionMode,
    parse_counting_mode as shared_parse_counting_mode,
    parse_contribution_mode as shared_parse_contribution_mode,
)
```

**Validation:**
- `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary.py tests/test_weekly_summary.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_effective_sets.py -q` → `163 passed`
- `.\.venv\Scripts\python.exe -m pytest tests/ -q` → `963 passed, 1 skipped`

**Execution note (2026-04-10):** Shared query-parameter parsers now live in `utils/effective_sets.py`, while both route modules keep thin `_parse_*` wrappers so existing route tests and any direct route-level imports remain stable for one cleanup cycle. Four direct parser tests were added to `tests/test_effective_sets.py`, which raised the current full-suite snapshot from `959` to `963 passed, 1 skipped`.

---

### 3e. Summary-Page Frontend Coupling Gate

**Estimated impact:** no code change required by default; this is a safety gate before touching summary templates or summary JS.

- [x] Record which updater path is authoritative for each summary page during this cleanup cycle:
  - [x] `static/js/app.js` page initializers still call `fetchWeeklySummary()` / `fetchSessionSummary()` on page init
  - [x] `static/js/modules/summary.js` remains a fallback updater path and returns early when it detects an inline updater or `#counting-mode`
  - [x] `templates/session_summary.html` inline `updateSessionSummary()` remains the authoritative session-page updater
  - [x] `templates/weekly_summary.html` inline `updateWeeklySummary()` remains the authoritative weekly-page updater
- [x] Confirm whether `static/js/modules/summary.js` still depends on the presence of the inline updater and/or `#counting-mode` to short-circuit safely
- [x] Confirm that `GET /api/pattern_coverage` stays on its current deferred contract from `DOCS_AUDIT_PLAN.md`
- [x] Do not start 3f until this ownership note is complete and committed to the plan / review notes
- [x] Validate current behavior before any template refactor:
  - [x] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`

**Execution note (2026-04-10):** `static/js/app.js` still initializes both summary pages, but the authoritative render/update path remains the inline template functions `updateSessionSummary()` and `updateWeeklySummary()`. `static/js/modules/summary.js` still uses `pageHasOwnUpdater()` plus the presence of `#counting-mode` to short-circuit safely, so any `3f` selector extraction must preserve those hooks or replace the fallback guard in the same change. The weekly page still owns live `GET /api/pattern_coverage` rendering on the intentionally deferred `success` + `data` contract documented in `docs/archive/DOCS_AUDIT_PLAN.md`, and the summary-page Chromium Playwright suite re-passed at `21 passed`.

**Post-4M UX update (2026-04-11):** The `#counting-mode` hook was intentionally retired after review found the UI confusing: the table already displays both Effective Sets and Raw Sets. The fallback guard in `static/js/modules/summary.js` was updated to detect the inline updater functions instead of relying on that selector.

---

### 3f. Extract Jinja2 Method Selector Macro (Descoped)

**Estimated impact:** ~23 duplicated lines → single shared macro (descoped from original ~78 estimate)

> **Review finding (2026-04-08):** Line-by-line comparison revealed the volume-legend sections are **NOT identical** between templates. Three specific differences exist:
> 1. Session line 69 shows session warning thresholds (`<=10 OK | 10-11 Borderline | >11 Excessive`); Weekly line 71 shows the effective sets formula instead.
> 2. Session has an extra `<p>` tag with the formula before the `<details>` expand section; Weekly omits it.
> 3. The `<details>` block in Session starts with the formula then Effort Factor; Weekly starts directly with Effort Factor.
>
> **Decision:** Descope to `method_selector` macro only. The volume-legend stays page-specific until a content-block design is validated.

- [x] Start only after Phase 3e is complete
- [x] Strengthen `e2e/summary-pages.spec.ts` to lock the selector contract before extraction
- [x] Create `templates/partials/_volume_controls.html` with `method_selector` macro
- [x] Update `templates/session_summary.html` to use the macro for the method selector only
- [x] Update `templates/weekly_summary.html` to use the macro for the method selector only
- [x] Leave volume-legend sections as page-specific (NOT extracted)
- [x] Do not rename or remove inline updater functions unless the Phase 3e ownership note explicitly allows it

#### After: New file `templates/partials/_volume_controls.html`

```html
{% macro method_selector(update_function_name) %}
<div class="method-selector">
    <div class="mb-3">
        <label for="contribution-mode" class="form-label">Muscle Contribution Mode</label>
        <select id="contribution-mode" class="form-select"
                onchange="{{ update_function_name }}()">
            <option value="total" selected>Total (Primary + Secondary + Tertiary)</option>
            <option value="direct">Direct Only (Primary Muscle Only)</option>
        </select>
        <small class="form-text text-muted">
            <strong>Total:</strong> Counts volume from all muscles worked (Primary 100%, Secondary 50%, Tertiary 25%).<br>
            <strong>Direct Only:</strong> Only counts sets where the muscle is the primary target.
        </small>
    </div>
</div>
{% endmacro %}
```

#### Usage in both templates:

```html
{% from "partials/_volume_controls.html" import method_selector %}
<!-- In session_summary.html: -->
{{ method_selector("updateSessionSummary") }}
<!-- volume-legend stays inline (page-specific content) -->

<!-- In weekly_summary.html: -->
{{ method_selector("updateWeeklySummary") }}
<!-- volume-legend stays inline (page-specific content) -->
```

**Validation:** `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line` + filtered API/browser checks if fetch behavior changes + visual spot-check of both pages

** codex 5.4*** The shared controls and legend shell are good macro candidates, but the pages are not fully identical. `weekly_summary.html` has plan-specific explanatory text and extra pattern-coverage content, so I would scope the extraction narrowly and consider whether the larger duplication worth tackling next is actually the inline JS, not the Jinja markup.

---

### 3g. Consolidate Volume Classifier Threshold Functions (Backend-only)

**Estimated impact:** ~10 lines reduced in backend helper code only. This phase intentionally does **not** deduplicate template or JS threshold logic.

- [x] Confirm this phase is backend-only
  - [x] Did **not** touch `templates/session_summary.html`
  - [x] Did **not** touch `templates/weekly_summary.html`
  - [x] Did **not** touch `static/js/modules/summary.js`
  - [x] Did **not** touch `static/js/modules/sessionsummary.js` or `static/js/updateSummary.js`
- [x] Refactor `utils/volume_classifier.py`
- [x] Preserve public API (`get_volume_class`, `get_volume_label`) — no callers needed to change

#### Before (`utils/volume_classifier.py:10-35`):

```python
def get_volume_class(total_sets):
    if total_sets < 10:
        return "low-volume"
    elif total_sets < 20:
        return "medium-volume"
    elif total_sets < 30:
        return "high-volume"
    else:
        return "ultra-volume"

def get_volume_label(total_sets):
    if total_sets < 10:
        return "Low Volume"
    elif total_sets < 20:
        return "Medium Volume"
    elif total_sets < 30:
        return "High Volume"
    else:
        return "Excessive Volume"
```

#### After:

```python
_VOLUME_TIERS = [
    # (threshold, css_class, label)  — evaluated top-down, first match wins
    (30, "ultra-volume",  "Excessive Volume"),
    (20, "high-volume",   "High Volume"),
    (10, "medium-volume", "Medium Volume"),
    (0,  "low-volume",    "Low Volume"),
]

def _classify(total_sets):
    """Return (css_class, label) for a raw set count."""
    for threshold, css_class, label in _VOLUME_TIERS:
        if total_sets >= threshold:
            return css_class, label
    return _VOLUME_TIERS[-1][1], _VOLUME_TIERS[-1][2]

def get_volume_class(total_sets):
    """Return the CSS class for volume classification (raw sets based)."""
    return _classify(total_sets)[0]

def get_volume_label(total_sets):
    """Return the text label for volume classification."""
    return _classify(total_sets)[1]
```

**Validation (2026-04-10):** `.\.venv\Scripts\python.exe -m pytest tests/test_volume_classifier.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py -q` -> `104 passed`

** codex 5.4*** This refactor is safe, but it is also relatively low ROI compared with the stronger cleanup wins above. If scope widens, I would prioritize dead JS detection and logger/DB normalization ahead of this cosmetic consolidation.

---

### 3h. Migrate Raw DB Access & Replace `print()` with Logger

> **These tasks are already captured in the archived audit record [`docs/archive/DOCS_AUDIT_PLAN.md`](archive/DOCS_AUDIT_PLAN.md).**
> To avoid duplication, this plan defers to that document for execution steps.

| Task | Covered By | Scope |
|------|-----------|-------|
| Migrate `get_db_connection()` → `DatabaseHandler` in 4 files | `archive/DOCS_AUDIT_PLAN.md` — **Tier 3** (6 steps with Codex review comments, `lastrowid` nuances, FK pre-checks) | `utils/user_selection.py`, `utils/volume_export.py`, `routes/volume_splitter.py` (3 endpoints), `utils/database_indexes.py` |
| Replace `print()` → `get_logger()` in ~20 files | `archive/DOCS_AUDIT_PLAN.md` — **Tier 2** (file-by-file table, migration template, safety rationale) | ~52 `print()` calls across `routes/` and `utils/` |

- [x] Execute `archive/DOCS_AUDIT_PLAN.md` Tier 2 (logging)
- [x] Execute `archive/DOCS_AUDIT_PLAN.md` Tier 3 (DB migration)
- [x] Validate both: `python -m pytest tests/ -q` (full suite) — current validated snapshot: `981 passed, 1 skipped`

** codex 5.4*** Since this plan still touches `routes/weekly_summary.py`, `routes/session_summary.py`, and later `routes/exports.py` in `3j`, I would opportunistically remove the local `print()` calls in those same edits instead of guaranteeing a second pass later. That keeps touched files moving toward the project standard in one trip.

---

### 3i. Bloated Function Decomposition (Retired - see phase5_3i_plan.md)

> **Retired 2026-04-13 by `docs/phase5_3i_plan.md` §5A-§5H.** The decompositions
> listed here shipped inside commit `12c90ac` bundled with phases `3a-3h`;
> the confidence-recovery audit required by this plan's Confidence Recovery Plan
> ran in `docs/phase5_3i_plan.md` and produced the exit artifacts
> `debug/5A_*.md` through `debug/5H_*.md`.
>
> The original §3i sub-phase bodies (`3i-a`..`3i-h`) are preserved in git
> history at commit `571a365` for reference. Do not re-execute from this
> document.

---

### 3j. Fix N+1 UPDATE Loop (Retired - see phase5_3i_plan.md)

> **Retired 2026-04-13 by `docs/phase5_3i_plan.md` §5I-§5J.** The export
> write-path optimization shipped inside commit `12c90ac` and intentionally
> changed failure semantics from partial-success per-row updates to an atomic
> batch update.
>
> `debug/5I_test_hardening.md` hardened the missing characterization coverage,
> and `debug/5J_recalculate_exercise_order.md` validated the documented
> `executemany()` batch semantics at `95%+` confidence.
>
> The original §3j checklist is preserved in git history at commit `571a365`
> for reference. Do not re-execute from this document.

---

## Known Bugs Triage (2026-04-10)

> **Source:** user-reported during the spring-cleanup review, before Phase 4 began. Captured during `4B` with fresh diagnostic evidence. None of the bugs here are caused by spring-cleanup — the root cause predates cleanup by ~2.5 months — but they will block a useful `4M` manual smoke test, so they must be resolved (or explicitly deferred with a reason) during `4N`.

### Bug 1 — Workout plan filter dropdowns are partially empty

- **Reported:** 2026-04-10 via quick-glance observation in the running app.
- **Repro:**
  1. Start app (`.\.venv\Scripts\python.exe app.py`).
  2. Open `/workout_plan`.
  3. Open the filter dropdowns rendered from `fetch_unique_values(...)` at [routes/workout_plan.py:101-122](routes/workout_plan.py#L101-L122).
  4. Observe that `Force`, `Equipment`, `Grips`, `Stabilizers`, `Synergists` are all empty; `Secondary Muscle Group`, `Tertiary Muscle Group`, `Advanced Isolated Muscles` are sparse.
- **Hypothesis (confirmed by SQL diagnostic on 2026-04-10):** the live `data/database.db` only has **16 rows** in `exercises`, and the following columns are **100% NULL or empty** across all 16 rows: `grips`, `stabilizers`, `synergists`, `force`, `equipment`. `tertiary_muscle_group` is populated on 6/16 rows; `secondary_muscle_group` on 10/16. The dropdowns are not broken — they are correctly rendering the distinct non-empty values of the underlying columns, which happen to be empty.
- **Root cause:** the canonical seed file at the path the code expects (`data/Database_backup/database.db`) does not exist on disk. A usable backup **does** exist at a different path (`data/backup/database.db`, 1883 rows, well-populated columns), but the seeder at [utils/db_initializer.py:16](utils/db_initializer.py#L16) and [utils/db_initializer.py:348-350](utils/db_initializer.py#L348-L350) looks only at `data/Database_backup/database.db`, detects the missing file, logs a warning, and silently skips. `.gitignore:29` excludes `*.db` so neither path has ever been tracked in git; commit `79c4161` on 2026-01-19 removed the historical `.db.backup_*` snapshots from `data/Database_backup/` but `database.db` itself was already untracked.
- **Affected files:**
  - `data/Database_backup/database.db` (missing — expected location)
  - `data/backup/database.db` (present — actual backup, 1883 rows)
  - [utils/db_initializer.py:331-413](utils/db_initializer.py#L331-L413) (seed path; correct behavior given the missing file at the expected path)
  - [routes/workout_plan.py:18-99](routes/workout_plan.py#L18-L99) (`fetch_unique_values` — not at fault)
- **Status:** `Fixed — restored from data/backup/database.db on 2026-04-10; browser-verified on /workout_plan`. **Not a spring-cleanup regression.** Resolved by the executed `Seed DB Restore Plan` below.

### Bug 2 — Exercise dropdown on `/workout_plan` is missing most exercises

- **Reported:** 2026-04-10, same observation path as Bug 1.
- **Repro:**
  1. Start app and open `/workout_plan`.
  2. Open the exercise dropdown (populated by `get_exercises()` in [utils/exercise_manager.py:16-18](utils/exercise_manager.py#L16-L18)).
  3. Observe that only a small number of exercises are listed.
- **Hypothesis (confirmed by SQL diagnostic on 2026-04-10):** only 16 rows exist in `exercises`. The render path `get_exercises()` → `FilterPredicates.filter_exercises(None)` → [utils/filter_predicates.py:107-130](utils/filter_predicates.py#L107-L130) issues `SELECT exercise_name FROM exercises WHERE 1=1 ORDER BY exercise_name ASC` with no LIMIT. The code correctly returns every row that exists; there are just 16 rows.
- **Root cause:** same missing seed file as Bug 1.
- **Affected files:** same as Bug 1.
- **Status:** `Fixed — restored from data/backup/database.db on 2026-04-10; browser-verified on /workout_plan`. **Not a spring-cleanup regression.** Resolved by the executed `Seed DB Restore Plan` below.

### Hardening — seed path mismatch can silently recur

- **Reported:** 2026-04-10 during `Seed DB Restore Plan` execution.
- **Repro:**
  1. Leave `data/backup/database.db` present but leave `data/Database_backup/database.db` missing.
  2. Start the app or call `initialize_database()`.
  3. Observe that the seeder checks only the `Database_backup` path, logs a warning, and skips the restore path entirely.
- **Hypothesis:** the configured `SEED_DB_PATH` no longer matches the real backup location in this working tree, so the app can silently fall back to an underpopulated live DB even when a usable seed file exists elsewhere.
- **Affected files:**
  - [utils/db_initializer.py:16](utils/db_initializer.py#L16)
  - [utils/db_initializer.py:348-350](utils/db_initializer.py#L348-L350)
  - `data/backup/database.db`
  - `data/Database_backup/database.db`
- **Status:** `Fixed — 4N hardening landed on 2026-04-10.` **Selected path:** Option A (code-side) — `SEED_DB_PATH` now points at `data/backup/database.db`, and the copied compatibility file at `data/Database_backup/database.db` was removed after validation.

### Hardening Completion Checklist

- [x] Update `SEED_DB_PATH` in [utils/db_initializer.py](utils/db_initializer.py) to `data/backup/database.db`.
- [x] Update the matching recovery path in [utils/database.py](utils/database.py) to `data/backup/database.db`.
- [x] Add regression coverage in [tests/test_seed_db_paths.py](tests/test_seed_db_paths.py):
  - [x] canonical path assertion
  - [x] empty temp DB seeds successfully from the canonical backup path
- [x] Remove the temporary compatibility copy at `data/Database_backup/database.db`.
- [x] Validate the fix:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_seed_db_paths.py -q` -> `2 passed`
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `934 passed, 1 skipped`
  - [x] `npx playwright test e2e/workout-plan.spec.ts --project=chromium --reporter=line` -> `17 passed`

### Diagnostic evidence captured 2026-04-10

```text
live_exercises_count: 16
  grips_filled: 0            grips_distinct_nonnull: 0
  stabilizers_filled: 0      stabilizers_distinct_nonnull: 0
  synergists_filled: 0       synergists_distinct_nonnull: 0
  tertiary_filled: 6         tertiary_distinct_nonnull: 5
  secondary_filled: 10
  force_filled: 0            force_distinct_nonnull: 0
  equipment_filled: 0        equipment_distinct_nonnull: 0
seed_exercises_count (data/Database_backup/database.db): FILE MISSING
backup_exercises_count (data/backup/database.db):        1883
  grips_filled: 559 / 1883        (≈30%)
  stabilizers_filled: 284 / 1883  (≈15%)
  synergists_filled: 305 / 1883   (≈16%)
  tertiary_filled: 693 / 1883     (≈37%)
  secondary_filled: 1084 / 1883   (≈58%)
  force_filled: 1805 / 1883       (≈96%)
  equipment_filled: 1883 / 1883   (100%)
```

Generated via ad-hoc SQL run against both DBs in the current working tree. Re-run at any time with:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('data/database.db').cursor(); c.execute('SELECT COUNT(*) FROM exercises'); print(c.fetchone()[0])"
.\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('data/backup/database.db').cursor(); c.execute('SELECT COUNT(*) FROM exercises'); print(c.fetchone()[0])"
```

### Operational note — manual smoke testing during cleanup

`4M` could not produce meaningful results against a 16-row DB because most filter paths, summary aggregations, and progression suggestions would not exercise realistic code. **The `Seed DB Restore Plan` below was executed successfully on 2026-04-10**, which unblocks realistic `4M` coverage from the data side.

---

## Seed DB Restore Plan (pre-Phase-4 prerequisite)

> **Why this section sits before Phase 4:** `Known Bugs Triage` above shows both user-reported bugs trace to a single data issue: the seeder at [utils/db_initializer.py:16](utils/db_initializer.py#L16) looks at `data/Database_backup/database.db`, but the usable 1883-row backup is at `data/backup/database.db`. Phase 4 sub-phase `4M` (manual workflow smoke test) cannot produce meaningful results against a 16-row DB, so this restore must complete successfully before `4M` runs.
>
> **Safety properties:** every step is non-destructive. Copying the backup file adds a file without modifying any existing file. The seed function uses `INSERT OR IGNORE` keyed on the `exercise_name` PRIMARY KEY, so the 16 rows already in `data/database.db` are preserved — the seed only adds new rows. File copy is reversible (`del` / `Remove-Item`), and if the seed produces an unexpected result the pre-seed state can be restored from `phase4_preseed.backup.db` created in step 2.

### Execution order

### Completion Checklist

- [x] **Step 1 completed** — confirmed no Flask process was holding the DB lock.
- [x] **Step 2 completed** — created rollback snapshot at `data/database.phase4_preseed.backup.db`.
- [x] **Step 3 completed** — copied `data/backup/database.db` to `data/Database_backup/database.db` and verified matching hashes.
- [x] **Step 4 completed** — ran `initialize_database()` successfully; live DB seeded to `1897` exercises.
- [x] **Step 5 completed** — verified live DB counts and non-empty metadata columns (`grips=558`, `stabilizers=283`, `synergists=304`, `force=1803`, `equipment=1881`, `iso_muscles_rows=1598`).
- [x] **Step 6 completed** — browser-verified `/workout_plan`; previously empty dropdowns are populated and the exercise selector shows `1898` options.
- [x] **Step 7 completed** — recorded `Restore Results`, marked Bug 1 and Bug 2 fixed, and opened the `Hardening: seed path mismatch` follow-up with Option A selected.

#### Step 1 — Confirm no Flask process is holding the DB lock
- **Goal:** avoid `database is locked` errors during the seed step.
- **Command:**
  ```powershell
  Get-Process python, pythonw, flask -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, StartTime, Path
  ```
- **Expected:** no process whose `Path` points at the project `.venv\Scripts\python.exe` and whose command line includes `app.py`.
- **If a process is found:** stop it cleanly (Ctrl+C in its window, or `Stop-Process -Id <pid>`). Do not kill the whole `python` process tree blindly.
- **Exit condition:** no Flask process running against the project DB.

#### Step 2 — Snapshot the current live DB as a rollback point
- **Goal:** create a named rollback artifact so the pre-seed state can be restored byte-for-byte if the seed produces unexpected results.
- **Command:**
  ```powershell
  Copy-Item data/database.db data/database.phase4_preseed.backup.db
  ```
- **Expected:** a new file `data/database.phase4_preseed.backup.db` with the same size as `data/database.db` at snapshot time.
- **Exit condition:** snapshot file exists and is the same size as the source.
- **Do not:** move the file (use Copy-Item, not Move-Item). Do not overwrite an existing snapshot from a prior attempt.

#### Step 3 — Copy the backup file into the path the code expects
- **Goal:** place the 1883-row backup where the seeder actually looks for it, without touching the seeder code.
- **Preconditions:** steps 1 and 2 complete.
- **Commands:**
  ```powershell
  New-Item -ItemType Directory -Path data/Database_backup -Force
  Copy-Item data/backup/database.db data/Database_backup/database.db
  ```
- **Expected:** `data/Database_backup/database.db` exists, byte-identical to `data/backup/database.db`.
- **Validation:**
  ```powershell
  (Get-FileHash data/backup/database.db).Hash -eq (Get-FileHash data/Database_backup/database.db).Hash
  ```
  Must print `True`.
- **Exit condition:** hash check returns `True`.
- **Do not:** delete the original at `data/backup/database.db`. Keep both copies until the seed is verified end-to-end.

#### Step 4 — Run the seed function directly (no full Flask startup)
- **Goal:** invoke `initialize_database()` out-of-process so the seed runs without booting the rest of the Flask app. This is the same function the app runs at startup; it is idempotent.
- **Preconditions:** step 3 complete.
- **Command:**
  ```powershell
  .\.venv\Scripts\python.exe -c "from utils.db_initializer import initialize_database; initialize_database()"
  ```
- **Expected console output:** a log line similar to `Seeding exercises catalogue from backup (existing rows: 16)` followed by `Exercises catalogue now holds <N> rows (<M> isolated muscle mappings)`. `<N>` should be close to 1883 (16 existing rows merged with 1883 seed rows via `INSERT OR IGNORE`; the overlap is expected to be small or zero).
- **Exit condition:** function returns without exception and the log shows a non-zero seed copy count.
- **If it fails:** do not retry blindly. Read the exception, consult [utils/db_initializer.py:331-413](utils/db_initializer.py#L331-L413), and resolve the root cause. If unsure, restore from `data/database.phase4_preseed.backup.db` and stop.

#### Step 5 — Verify the live DB is populated
- **Goal:** confirm both the row count and the previously-empty columns are now non-empty.
- **Preconditions:** step 4 complete.
- **Command:**
  ```powershell
  .\.venv\Scripts\python.exe -c "
  import sqlite3
  c = sqlite3.connect('data/database.db').cursor()
  c.execute('SELECT COUNT(*) FROM exercises')
  print('exercises_count:', c.fetchone()[0])
  c.execute('''SELECT
    SUM(CASE WHEN grips IS NOT NULL AND TRIM(grips) <> '' THEN 1 ELSE 0 END),
    SUM(CASE WHEN stabilizers IS NOT NULL AND TRIM(stabilizers) <> '' THEN 1 ELSE 0 END),
    SUM(CASE WHEN synergists IS NOT NULL AND TRIM(synergists) <> '' THEN 1 ELSE 0 END),
    SUM(CASE WHEN force IS NOT NULL AND TRIM(force) <> '' THEN 1 ELSE 0 END),
    SUM(CASE WHEN equipment IS NOT NULL AND TRIM(equipment) <> '' THEN 1 ELSE 0 END)
  FROM exercises''')
  print('grips, stabilizers, synergists, force, equipment filled:', c.fetchone())
  c.execute('SELECT COUNT(*) FROM exercise_isolated_muscles')
  print('exercise_isolated_muscles rows:', c.fetchone()[0])
  "
  ```
- **Expected:**
  - `exercises_count` ≈ 1883 (or 1883 + any pre-existing exercises that were not in the backup).
  - Every filled column count greater than zero. `force` ≈ 1805, `equipment` ≈ 1883.
  - `exercise_isolated_muscles` rows greater than zero (the seeder auto-rebuilds this table from `advanced_isolated_muscles` when underpopulated — see [utils/db_initializer.py:408-410](utils/db_initializer.py#L408-L410)).
- **Exit condition:** all three expectations hold. Record the actual numbers in this section under `Restore Results`.

#### Step 6 — Browser verification of the previously-broken dropdowns
- **Goal:** close the loop on the original user-reported bugs.
- **Preconditions:** step 5 complete.
- **Action:**
  1. Start the app: `.\.venv\Scripts\python.exe app.py`
  2. Open `http://localhost:5000/workout_plan` in a browser.
  3. Open each filter dropdown that `Known Bugs Triage > Bug 1` listed as empty: `Force`, `Equipment`, `Grips`, `Stabilizers`, `Synergists`.
  4. Confirm every one of them is now populated with real values.
  5. Open the exercise dropdown and confirm it lists many more than 16 exercises.
- **Exit condition:** both bugs visually confirmed fixed. Mark `Known Bugs Triage > Bug 1` and `Bug 2` as `Fixed — restored from data/backup/database.db on 2026-04-10`.
- **If the dropdowns are still empty:** there is a second, independent bug on the render path that the data fix did not uncover. Reopen the bug with new repro evidence and escalate.

#### Step 7 — Record results and schedule the path-mismatch hardening
- **Goal:** leave an honest audit trail and prevent silent recurrence.
- **Action:**
  - Fill in a `Restore Results` block below (row counts from step 5, browser confirmation from step 6, timestamp).
  - Open a new triage entry under `Known Bugs Triage` titled `Hardening: seed path mismatch` describing the two long-term fix options:
    - **Option A (code-side):** update `SEED_DB_PATH` in [utils/db_initializer.py:16](utils/db_initializer.py#L16) to point at `data/backup/database.db`, deleting the copy at `data/Database_backup/database.db`. Aligns code with reality.
    - **Option B (filesystem-side):** keep `data/Database_backup/database.db` as the canonical location, document it in `CLAUDE.md`, and add a startup error (not just a warning) when the file is missing AND `exercises` is below `MIN_EXERCISE_ROWS`. Prevents silent recurrence.
  - Choose one option and schedule it as a `4N` fix commit.
- **Exit condition:** triage entry exists; hardening path is chosen.

### Restore Results *(executed 2026-04-10)*

```text
executed_at:           2026-04-10T17:36:50+03:00
exercises_count_after: 1897
grips_filled:          558
stabilizers_filled:    283
synergists_filled:     304
force_filled:          1803
equipment_filled:      1881
iso_muscles_rows:      1598
step_6_browser_check:  pass
step_6_dropdowns:      force=4, equipment=19, grips=10, stabilizers=24, synergists=26, exercise=1898
hardening_option:      A (implemented)
```

---

## Phase 4: Validation & Regression

### 4.1 Pre-Cleanup Baseline

Run before starting any changes:

- [ ] Record pytest results: `.\.venv\Scripts\python.exe -m pytest tests/ -q | Tee-Object -FilePath baseline_pytest.txt`
- [ ] Record summary-page browser gate: `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line | Tee-Object -FilePath baseline_summary_pages.txt`
- [ ] If the upcoming phase touches templates, shared JS, or route contracts, record full Playwright too: `npx playwright test --project=chromium --reporter=line | Tee-Object -FilePath baseline_e2e_full.txt`
- [ ] Record file counts:
  ```powershell
  (rg --files utils -g "*.py" | Measure-Object).Count
  (rg --files routes -g "*.py" | Measure-Object).Count
  (Get-ChildItem templates -File | Measure-Object).Count
  (rg --files static/js/modules -g "*.js" | Measure-Object).Count
  (rg --files static/js -g "*.js" | Measure-Object).Count
  ```
- [ ] Record total Python line count:
  ```powershell
  $pyFiles = rg --files -g "*.py" -g "!.venv/**" -g "!node_modules/**"
  ($pyFiles | ForEach-Object { (Get-Content $_ | Measure-Object -Line).Lines } | Measure-Object -Sum).Sum
  ```

** codex 5.4*** This subsection has been normalized to PowerShell-friendly commands so the baseline checklist can be executed exactly as written on this repo's current Windows workflow.

### 4.2 Per-Change Validation Protocol

| Change Type | Test Command | Scope |
|-------------|-------------|-------|
| Wave 1 module deletion | `.\.venv\Scripts\python.exe -m pytest tests/ -q` + `rg` import audit | Full suite + import safety |
| Wave 2 package-surface deletion | `.\.venv\Scripts\python.exe -m pytest tests/ -q` + package/doc audit | Full suite + API-surface safety |
| Route helper extraction | `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_effective_sets.py -q` | Targeted route + helper contract |
| Backend helper edit used by templates | relevant util tests + relevant route tests | Targeted |
| Template / summary-page markup edit | `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line` + visual check | Browser + manual |
| Shared summary JS or route-contract edit | targeted summary browser spec + filtered API integration + full Playwright if shared modules change | Browser + contract |
| Semantic DB write-path change | `.\.venv\Scripts\python.exe -m pytest tests/test_exports.py tests/test_ui_flows.py -q` + full pytest | Targeted + suite |

### 4.3 Test File → Module Coverage Map

| Test File | Covers Module | Action After Module Deletion |
|-----------|--------------|------------------------------|
| ~~`tests/test_business_logic.py`~~ | ~~`utils/business_logic.py`~~ | Deleted in `3b Wave 2` |
| ~~`tests/test_data_handler.py`~~ | ~~`utils/data_handler.py`~~ | Deleted in `3b Wave 2` |
| `tests/test_session_summary.py` | `utils/session_summary.py` | Must still pass after parse function extraction |
| `tests/test_weekly_summary.py` | `utils/weekly_summary.py` | Must still pass after parse function extraction |
| `tests/test_session_summary_routes.py` | `routes/session_summary.py` | Must still pass if compatibility wrappers are kept or updated in the same change |
| `tests/test_weekly_summary_routes.py` | `routes/weekly_summary.py` | Must still pass if compatibility wrappers are kept or updated in the same change |
| `tests/test_volume_classifier.py` | `utils/volume_classifier.py` | Must still pass after threshold consolidation |
| `tests/test_exports.py` | `routes/exports.py` | Must be expanded before the deferred batch-update phase |
| `tests/test_ui_flows.py` | export and page flows | Must still pass after export/write-path changes |
| `tests/test_workout_log_routes.py` | `routes/workout_log.py` | Must still pass |
| `tests/test_workout_plan_routes.py` | `routes/workout_plan.py` | Must still pass after any route changes |
| `tests/test_effective_sets.py` | `utils/effective_sets.py` | Must still pass after adding parse functions |

### 4.4 Post-Cleanup Verification Checklist

- [x] **Full pytest:** `.\.venv\Scripts\python.exe -m pytest tests/ -q` — actual result: `932 passed, 1 skipped` (`phase4c_pytest.txt`)
- [x] **Summary surfaces browser gate:** `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line` — actual result: `21 passed` (`phase4d_summary.txt`)
- [x] **Full E2E:** `npx playwright test --project=chromium --reporter=line` — actual result: `315 passed` (`phase4e_full_e2e.txt`)
- [ ] **Dead code scan:** `vulture routes/ utils/ --min-confidence 80` — expect zero or near-zero findings
- [ ] **Unused import scan:** `pylint --disable=all --enable=W0611 routes/ utils/` — expect zero findings
- [ ] **Print audit:** `rg -n "print\(" routes utils -g "*.py"` — expect zero hits (covered by `archive/DOCS_AUDIT_PLAN.md` Tier 2)
- [x] **Raw DB access audit:** `rg -n "get_db_connection|sqlite3\.connect" routes utils` — only intentional hits remain in `utils/database_indexes.py` for the locked `optimize_database()` maintenance path plus the helper implementation in `utils/database.py`
- [ ] **Frontend orphan audit:** `rg -n "sessionsummary|updateSummary" static templates`
- [ ] **Package-surface audit:** `rg -n "from utils import .*DataHandler|from utils import .*BusinessLogic|from utils\.helpers|from utils\.filters" app.py routes tests e2e`
- [ ] **File count comparison:** Compare against baseline counts from 4.1
- [ ] **Line count comparison:** Compare total Python LOC against baseline

** codex 5.4*** I would add one more post-cleanup audit here for dead or duplicate frontend code, because the discovery phase already points toward that scope and the current checklist stops short of confirming it. At minimum, re-check `static/js/modules/sessionsummary.js`, `static/js/updateSummary.js`, and any JS left behind after deleting `templates/dropdowns.html`.

### 4.6 Granular Phase 4 Sub-Phases (2026-04-10)

> **Why this section exists:** the original `4.4` checklist and the `Post-Cleanup Final Gate` at the bottom of this doc list too many actions in one flat list to execute safely within a single conversation. This section breaks Phase 4 into **15 self-contained sub-phases**. Each one is designed to be runnable in a fresh conversation with zero prior-conversation memory: it lists goal, preconditions, exact command(s), expected result, what to record, and the exit condition.
>
> **Execution order:** run top-to-bottom. `4A` and `4B` are prerequisites for every subsequent sub-phase. `4M` is where user-visible bugs (already captured in `Known Bugs Triage`) are most likely to surface. `4N` is the only sub-phase allowed to change production code; every other sub-phase is read-only or limited to deleting already-orphaned assets.
>
> **Execution note (2026-04-10):** an explicit user decision overrode that nominal order for one narrow reason: the known `/workout_plan` bugs were fixed before entering Phase 4 proper. To honor that, the `Seed DB Restore Plan` plus the immediate health checkpoint (`4C`-`4E`) were executed ahead of `4A`/`4B`. `4A` and `4B` still remain valuable commit-hygiene / evidence-capture tasks, but they are no longer blockers to interpreting the current validation snapshot.

#### 4A — Commit working tree as phase checkpoints
- **Goal:** turn the current uncommitted blob on `spring-cleanup` into one commit per completed cleanup sub-phase so rollback and `git bisect` work.
- **Why first:** every following sub-phase needs a clean baseline to diff against. Right now everything since commit `47736b9` (pre-cleanup snapshot) is in the working tree as one implicit batch, which violates the plan's own golden rule that every cleanup step must be individually reversible.
- **Preconditions:** none.
- **Action:**
  - Review `git status` and `git diff --stat` against `47736b9`.
  - Stage and commit in logical groups matching the completed phases in this order: `3a`, `3b Wave 1`, `3c`, `3d`, `3e`, `3f`, `3g`, `3h`, `3i-a`, `3i-b`, `3i-c`, `3i-d`, `3i-e`, `3i-f`, `3i-g`, `3i-h`, `3b Wave 2`.
  - Use `git add -p` or `git add <specific files>` — never `git add -A`.
  - Each commit message should reference the sub-phase (e.g., `chore(3a): remove unused imports in routes/exports.py and routes/weekly_summary.py`).
- **Exit condition:** `git status` is clean (only the expected `baseline_*.txt`, `cleanup_preflight*.txt`, and other untracked artifacts remain untracked) and `git log --oneline 47736b9..HEAD` shows one commit per phase.
- **Do not:** force-push, amend published commits, or touch `main`.

#### 4B — Bug triage capture *(record-only; see `Known Bugs Triage` section)*
- **Goal:** capture every known user-visible bug with repro steps, hypothesized cause, and affected files *before* any re-test or any fix. This is the evidence side of the "tests green vs. app broken" contradiction.
- **Preconditions:** `4A` complete (so bug entries can reference a stable commit).
- **Action:** confirm the `Known Bugs Triage (2026-04-10)` section below is complete and accurate against the live app. Add any new bugs you notice to that section. Do **not** fix anything yet.
- **Exit condition:** every bug has a `Repro`, `Hypothesis`, `Affected files`, and `Status` entry.
- **Do not:** delete, rename, or "fix" any file referenced by a bug entry in this sub-phase.

#### 4C — Full pytest re-run against current HEAD
- **Goal:** confirm the plan's claim of `930 passed, 1 skipped` (post-`3b Wave 2`) and `932 passed, 1 skipped` (post-`3i-e`) still holds today against the committed tree.
- **Preconditions:** `4A` complete.
- [x] **Executed on 2026-04-10** — result: `932 passed, 1 skipped` written to `phase4c_pytest.txt`.
- **Command:**
  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests/ -q | Tee-Object -FilePath phase4c_pytest.txt
  ```
- **Expected:** pass count within 1–2 of the latest validated claim (`~930–932 passed, 1 skipped`). Any failure or unexpected drop is a regression.
- **Record:** final pass/fail/skip counts and the path to `phase4c_pytest.txt` in this plan's `Current Evidence Snapshot` table.
- **Exit condition:** pass count matches expectation (or every failure opened as a triage entry under `Known Bugs Triage` and deferred to `4N`).

#### 4D — Summary-surfaces Playwright gate
- **Goal:** confirm the summary pages still pass the contract-lock tests added during `3f`.
- **Preconditions:** `4A` and `4C` complete.
- [x] **Executed on 2026-04-10** — result: `21 passed` written to `phase4d_summary.txt`.
- **Command:**
  ```powershell
  npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line | Tee-Object -FilePath phase4d_summary.txt
  ```
- **Expected:** `21 passed`.
- **Exit condition:** `21 passed`, or each failure opened as a triage entry.

#### 4E — Full Playwright suite
- **Goal:** confirm all 17 spec files still pass after the full cleanup sequence.
- **Preconditions:** `4A`, `4C`, `4D` complete.
- [x] **Executed on 2026-04-10** — result: `315 passed` written to `phase4e_full_e2e.txt`.
- **Command:**
  ```powershell
  npx playwright test --project=chromium --reporter=line | Tee-Object -FilePath phase4e_full_e2e.txt
  ```
- **Expected:** `315 passed`.
- **Record:** runtime and pass count; flag any new flake.
- **Exit condition:** `315 passed`, or each failure opened as a triage entry.

#### 4F — Dead-code scan (vulture)
- **Goal:** find any dead code the manual cleanup missed.
- **Preconditions:** `4A` complete. `vulture` installed in `.venv` (`.\.venv\Scripts\python.exe -m pip install vulture` if missing).
- **Command:**
  ```powershell
  .\.venv\Scripts\python.exe -m vulture routes/ utils/ --min-confidence 80 | Tee-Object -FilePath phase4f_vulture.txt
  ```
- **Record:** every finding. Delete only items that are unambiguously dead (zero callers, not part of any documented public API, no test-only fixtures). Open anything uncertain as a triage entry and defer.
- **Exit condition:** findings recorded; any deletion followed by a `4C` re-run before the next sub-phase starts.

#### 4G — Unused-import scan (pylint W0611)
- **Goal:** catch any `import X` regressions in `routes/` or `utils/`.
- **Preconditions:** `4A` complete.
- **Command:**
  ```powershell
  .\.venv\Scripts\python.exe -m pylint --disable=all --enable=W0611 routes/ utils/
  ```
- **Expected:** zero findings.
- **Exit condition:** zero findings, or each one fixed and `4C` re-run.

#### 4H — `print()` audit
- **Goal:** confirm the logging migration from `archive/DOCS_AUDIT_PLAN.md` Tier 2 is still clean.
- **Preconditions:** `4A` complete.
- **Command:**
  ```powershell
  rg -n "print\(" routes utils -g "*.py"
  ```
- **Expected:** zero hits.
- **Exit condition:** zero, or every hit converted to `get_logger()` and `4C` re-run.

#### 4I — Raw DB access audit
- **Goal:** confirm the only raw DB access paths are the documented exceptions in `CLAUDE.md` Section 2.
- **Preconditions:** `4A` complete.
- **Command:**
  ```powershell
  rg -n "get_db_connection|sqlite3\.connect" routes utils
  ```
- **Expected:** only `utils/database.py` (helper definition) and `utils/database_indexes.py:51` (`optimize_database()` PRAGMA path with manual lock).
- **Exit condition:** expected hits only, or any new hit opened as a triage entry.

#### 4J — Frontend orphan audit & safe deletion
- **Goal:** finish removing the two dormant JS files that `Phase 0.5` flagged as safe-delete candidates.
- **Preconditions:** `4A`, `4C`, `4D`, `4E` all complete and green (so there is a known-good baseline to compare against after deletion).
- **Commands:**
  ```powershell
  rg -n "sessionsummary|updateSummary" static templates e2e
  ```
- **Action if zero references:** delete `static/js/modules/sessionsummary.js` and `static/js/updateSummary.js`. Commit the deletion as a single commit `chore(4J): remove orphaned JS modules`.
- **Post-delete validation:** re-run `4D` and `4E`.
- **Exit condition:** files deleted and `4D`+`4E` still green, or deletion deferred with a recorded reason.

#### 4K — Package-surface audit
- **Goal:** confirm no regression reintroduced a legacy package import.
- **Preconditions:** `4A` complete.
- **Command:**
  ```powershell
  rg -n "from utils import .*DataHandler|from utils import .*BusinessLogic|from utils\.helpers|from utils\.filters|from utils\.database_init|from utils\.muscle_group" app.py routes tests e2e
  ```
- **Expected:** zero hits.
- **Exit condition:** zero, or each regression removed and `4C` re-run.

#### 4L — File & line-count delta
- **Goal:** replace the placeholder estimates in `4.5 Expected Reduction Summary` with actuals.
- **Preconditions:** `4A`, `4C`–`4K` complete.
- **Commands:**
  ```powershell
  (rg --files utils -g "*.py" | Measure-Object).Count
  (rg --files routes -g "*.py" | Measure-Object).Count
  (Get-ChildItem templates -File | Measure-Object).Count
  (rg --files static/js/modules -g "*.js" | Measure-Object).Count
  (rg --files static/js -g "*.js" | Measure-Object).Count
  $pyFiles = rg --files -g "*.py" -g "!.venv/**" -g "!node_modules/**"
  ($pyFiles | ForEach-Object { (Get-Content $_ | Measure-Object -Line).Lines } | Measure-Object -Sum).Sum
  ```
- **Exit condition:** actual numbers written into the `After` column of `4.5 Expected Reduction Summary`.

#### 4M — Manual workflow smoke test *(highest bug-finding value)*
- **Goal:** walk through the six core workflows from `CLAUDE.md` Section 1.2 in the running app and record anything that misbehaves. This is the layer that catches user-visible bugs automated tests miss.
- **Preconditions:** `4A`–`4L` complete and green. `Known Bugs Triage` data issue (seed DB) resolved if it blocks realistic smoke coverage — see that section for the reseed step.
- **Action:**
  1. Start the app: `.\.venv\Scripts\python.exe app.py`
  2. For each workflow, execute one realistic flow and record `pass` / `fail` + notes:
     - [ ] **Plan** (`/workout_plan`): open page, apply a filter, add an exercise to a routine, reorder it.
     - [ ] **Log** (`/workout_log`): import from plan, edit scored reps/weight/RIR, save.
     - [ ] **Analyze — Weekly** (`/weekly_summary`): toggle counting mode, toggle contribution mode, confirm numbers change.
     - [ ] **Analyze — Session** (`/session_summary`): same toggles, plus a time-window filter.
     - [ ] **Progress** (`/progression`): pick an exercise, view suggestions.
     - [ ] **Distribute** (`/volume_splitter`): move a slider, recalculate.
     - [ ] **Backup** (`/api/backups` modal on workout plan page): create → list → restore → delete.
- **Record:** for every `fail`, add a `Known Bugs Triage` entry with repro, affected route/file, expected vs. actual.
- **Exit condition:** every workflow either green-checked or recorded as a triage entry.

#### 4N — Bug investigation & fixing
- **Goal:** fix every `Known Bugs Triage` entry captured in `4B` and `4M` that is in scope for this cleanup cycle.
- **Preconditions:** `4A`–`4M` complete; each bug has a documented repro.
- **Rules:**
  - One bug per commit.
  - Every fix requires either a new failing test that the fix turns green, or a documented reason why adding a test is not feasible.
  - After each fix, re-run `4C` (full pytest) and the narrowest relevant spec from `4D`/`4E`.
  - Bugs triaged as "out of scope for this cleanup cycle" must be recorded as such, not silently deferred.
- **Exit condition:** every `4B`/`4M` bug is either `fixed + tests green` or `deferred with explicit reason`.

#### 4O — Update `CLAUDE.md` and close the plan
- **Goal:** bring `CLAUDE.md` in sync with the post-cleanup reality.
- **Preconditions:** `4A`–`4N` complete.
- **Action:**
  - Update `CLAUDE.md` Section 8 `Verified Test Counts` with the results from `4C`, `4D`, `4E`.
  - Update the `last verified` date.
  - Update the `Deprecated / Legacy Modules` table to reflect `3b Wave 2` retirements.
  - Refresh `docs/CHANGELOG.md` with a single entry summarizing the spring-cleanup sequence.
  - Mark the `Status Dashboard` in this plan as fully complete for every executed phase.
  - Resolve the self-inconsistency in this plan between `Stage Tracker` (3i marked `Later`) and `[Phase 3i]` (sub-phases marked `[x]`).
- **Exit condition:** `CLAUDE.md` accurately describes the post-cleanup tree, `git status` clean, plan dashboard closed.

> **Note:** the legacy `Post-Cleanup Final Gate` checklist at the bottom of this document is superseded by `4A`–`4O` above. It is kept for historical reference only; do not execute it line by line.

---

### 4.5 Expected Reduction Summary

| Metric | Before | After (actual) | Reduction |
|--------|---------------|--------------|-----------|
| Python files in `utils/` | 34 | 27 | -7 files |
| Python files in `routes/` | 10 | 10 | 0 files |
| Template files | 15 | 9 | -6 files |
| JS files in `static/js/modules/` | 24 | 21 | -3 files |
| Dead imports | ~7 | 0 | -7 |
| Duplicated parse functions | 2 route copies | 1 shared helper + optional temporary wrappers | Safer incremental reduction |
| N+1 query loops | 1 | 0 unresolved | Initially deferred to `3j`; later validated by `docs/phase5_3i_plan.md` §5J |
| Raw `get_db_connection()` calls | ~8 | 1 intentional maintenance exception | Unsafe app write paths migrated; `utils/database_indexes.py` holds `_DB_LOCK` explicitly |
| `print()` calls in prod code | already 0 | 0 | Already completed in archived audit |
| Total Python LOC | ~27,000 | 25,546 | ~1,454 fewer |

---

## Execution Priority

| Priority | Sub-phase | Risk | Effort |
|----------|-----------|------|--------|
| 0 (required first) | **Phase 0** Confidence gate | Very low | **COMPLETED** (2026-04-10) |
| 1 | **3a** Remove unused imports | Very low | **COMPLETED** (2026-04-10) |
| 2 | **3b Wave 1** High-confidence deletions | Low | **COMPLETED** (2026-04-10) |
| 3 | **3c** Delete orphaned templates | Very low | **COMPLETED** (2026-04-10) |
| 4 | **3d** Compatibility-first parse extraction | Low | **COMPLETED** (2026-04-10) |
| 5 | **3e** Summary-page frontend coupling gate | Very low | **COMPLETED** (2026-04-10) |
| 6 | **3f** Extract descoped method-selector macro | Medium (visual regression) | **COMPLETED** (2026-04-10) |
| 7 | **3g** Backend-only volume classifier cleanup | Low | **COMPLETED** (2026-04-10) |
| 8 | **3b Wave 2** Package-surface contraction | Medium | **COMPLETED** (2026-04-10) |
| ~~9~~ | ~~**3h** DB migration + logging cleanup~~ | ~~Medium~~ | **COMPLETED** (see `archive/DOCS_AUDIT_PLAN.md` Tiers 2-3) |
| 10 (last / optional) | **3j** N+1 update loop semantic optimization | Medium-High (write path) | 20-40 min |
| 11 | **3i** Decompose bloated functions | Medium (wide scope) | 2+ hours |

---

## Architectural Review Findings (2026-04-10)

### Review Confidence Scores

| Phase | Confidence | Risk | Notes |
|---|---|---|---|
| **3a** Remove unused imports | **99%** | Very Low | Completed and validated; `pylint` also surfaced and cleared `Response` / `jsonify` in `routes/exports.py` |
| **3b Wave 1** High-confidence deletions | **98-99%** | Low | Completed and validated; deleted internal dead modules plus the legacy test-only `muscle_group` pair |
| **3b Wave 2** Package-surface contraction | **95-96%** | Medium | Completed after an explicit API retirement decision, paired test deletion, migration note, and a green full-suite pytest run at `930 passed, 1 skipped` |
| **3c** Delete orphaned templates | **99%** | Very Low | Completed and validated with smoke-navigation Playwright plus full pytest |
| **3d** Extract parse functions | **99%** | Low | Completed with route-level compatibility wrappers preserved; targeted plus full pytest stayed green |
| **3e** Summary-page frontend coupling gate | **99%** | Very Low | Completed in practice: inline updater ownership, guarded fallback behavior, and deferred `/api/pattern_coverage` contract were re-confirmed; summary Playwright re-passed at `21 passed` |
| **3f** Extract Jinja2 macro | **95-96%** | Medium (visual regression) | Completed as a strict `method_selector` extraction with stronger selector-contract tests, preserved inline updater hooks, green summary/full Chromium Playwright, and desktop/mobile visual review |
| **3g** Consolidate volume classifier | **99%** | Low | Completed as a backend-only table-driven helper extraction in `utils/volume_classifier.py`; public API stayed intact and the targeted pytest gate passed at `104 passed` |
| **3h** DB migration + logging | **99%** | N/A | Already completed and validated at `981 passed, 1 skipped` |
| **3i** Decompose bloated functions | **95%+** | Retired | Later validated by `docs/phase5_3i_plan.md` sub-phases 5A-5H |
| **3j** Fix N+1 loop | **95%+** | Retired | Later validated by `docs/phase5_3i_plan.md` sub-phase 5J after 5I test hardening |

### Key Corrections Applied
1. **Baseline evidence refreshed:** Phase 0 baseline snapshot was `981 passed, 1 skipped`, `21` passing summary-surface browser tests, and `315` passing Chromium Playwright tests. Post-`3b Wave 1`, `3c`, and `3d`, the current pytest snapshot is `963 passed, 1 skipped` because `tests/test_muscle_group.py` was intentionally removed with its dead module and four shared-helper tests were added in `3d`.
2. **Phase 3b split:** high-confidence internal deletions are separated from package-surface contraction work
3. **Phase 3d hardened:** route-level parse helper compatibility is now called out explicitly because route tests import those helpers directly
4. **Phase 3e added:** summary-page frontend ownership must be documented before template dedup proceeds
5. **Phase 3g narrowed:** backend-only for this cycle; template / JS threshold dedup is deferred
6. **Phase 3j initially deferred:** the export write-path optimization moved to the end and was blocked on dedicated tests until Phase 5 resolved it
7. **Phase 0 executed:** start authorization was evidence-based: initial `GO` for `3a`, `3b Wave 1`, `3c`, `3d`, `3e`, `3g`; initial `HOLD` for `3f`; initial `NO-GO` for `3b Wave 2` and `3j`
8. **Phase 3c executed:** orphaned templates were removed after a clean reference audit and validated with smoke-navigation Playwright plus full pytest
9. **Phase 3d executed:** shared query-parameter parsers were centralized in `utils/effective_sets.py`, route-level compatibility wrappers were preserved, and both targeted plus full pytest stayed green
10. **Phase 3f executed:** selector-contract assertions were strengthened first, the summary method selector was extracted into a shared partial without touching shared JS or page-specific legend copy, and summary/full Chromium Playwright plus desktop/mobile visual review stayed green
11. **Phase 3g executed:** raw-volume thresholds were centralized into `_VOLUME_TIERS` + `_classify()` in `utils/volume_classifier.py`, the public helper API stayed unchanged, and the scoped pytest gate passed at `104 passed`
12. **Phase 3b Wave 2 executed:** explicit package-surface retirement was approved, `app.py` moved to a direct module import, `utils/__init__.py` dropped the retired legacy exports, the paired legacy modules/tests were deleted, and the full pytest suite stayed green at `930 passed, 1 skipped`
13. **Phase 5 recovery executed:** `docs/phase5_3i_plan.md` retired the remaining `3i`/`3j` confidence gaps with per-function artifacts and a post-5I baseline of `938 passed, 1 skipped`

### Volume Classifier Boundary Verification

| Input | `get_volume_class` (current) | `_classify()[0]` (proposed) | Match |
|---|---|---|---|
| -1 | `"low-volume"` | `"low-volume"` (fallback) | Yes |
| 0 | `"low-volume"` | `>= 0` hit | Yes |
| 9.99 | `"low-volume"` | `>= 0` hit | Yes |
| 10 | `"medium-volume"` | `>= 10` hit | Yes |
| 19.99 | `"medium-volume"` | `>= 10` hit | Yes |
| 20 | `"high-volume"` | `>= 20` hit | Yes |
| 29.99 | `"high-volume"` | `>= 20` hit | Yes |
| 30 | `"ultra-volume"` | `>= 30` hit | Yes |
| 100 | `"ultra-volume"` | `>= 30` hit | Yes |

Note: Plan only refactors `get_volume_class()` and `get_volume_label()` (lines 10-35). The other 5 public functions (`get_effective_volume_label`, `get_volume_tooltip`, `get_session_warning_tooltip`, `get_category_tooltip`, `get_subcategory_tooltip`) are untouched.

---

## Execution Checklist

> **Pre-flight:** Record current baseline before starting any work.
> ```powershell
> .\.venv\Scripts\python.exe -m pytest tests/ -q | Tee-Object -FilePath baseline_pytest.txt
> npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line | Tee-Object -FilePath baseline_summary_pages.txt
> ```

---

### [Phase 0] Prerequisite Confidence Gate
- [x] **0-1.** Save rollback artifacts before risky edits:
  - [x] `git status --short | Tee-Object -FilePath cleanup_preflight_status.txt`
  - [x] `git diff --binary | Out-File -Encoding ascii cleanup_preflight.patch`
- [x] **0-2.** Re-run full pytest baseline:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q`
- [x] **0-3.** Re-run summary-surface browser baseline:
  - [x] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`
- [x] **0-4.** If template/shared-JS/contract work is planned in this cycle, re-run full Playwright now:
  - [x] `npx playwright test --project=chromium --reporter=line`
- [x] **0-5.** Audit package-surface imports and references:
  - [x] `rg -n "from utils import|import utils\.|from utils\.(data_handler|business_logic|helpers|filters|database_init|muscle_group)" app.py routes tests e2e docs CLAUDE.md`
- [x] **0-6.** Record whether `utils/__init__.py` is treated as supported API or internal-only convenience.
  - [x] Decision: Phase 0 treated it as supported package surface for the cycle; a later explicit API retirement decision authorized and completed `3b Wave 2`
- [x] **0-7.** Audit summary-page ownership:
  - [x] `static/js/app.js`
  - [x] `static/js/modules/summary.js`
  - [x] `templates/session_summary.html`
  - [x] `templates/weekly_summary.html`
  - [x] `e2e/summary-pages.spec.ts`
  - [x] Decision: inline template updaters are authoritative; `summary.js` is a guarded fallback
- [x] **0-8.** Audit likely orphan frontend files:
  - [x] `static/js/modules/sessionsummary.js`
  - [x] `static/js/updateSummary.js`
  - [x] Result: both are currently safe-delete candidates with no repo references
- [x] **0-9.** Confirm whether the export recalculation branch already has dedicated success and failure tests.
  - [x] Result at Phase 0 time: dedicated recalculation/rollback tests were not present, so `3j` stayed deferred until Phase 5
- [x] **0-10.** Record go / no-go:
  - [x] baseline green
  - [x] package-surface decision recorded
  - [x] summary-page ownership recorded
  - [x] semantic-change test gap resolved or deferred
  - [x] Go for `3a`, `3b Wave 1`, `3c`, `3d`, `3e`, `3g`
  - [x] Hold `3f` for separate frontend / visual decision
  - [x] No-go for `3b Wave 2` and `3j` until prerequisites are satisfied; both were resolved later by explicit follow-up decisions/plans

---

### [Phase 3a] Remove Unused Imports
- [x] **3a-1.** Edit `routes/exports.py` — remove 5 unused imports:
  - [x] Remove `make_response` from Flask import (line 1)
  - [x] Remove `sanitize_filename` (line 5)
  - [x] Remove `create_content_disposition_header` (line 6)
  - [x] Remove `should_use_streaming` (line 9)
  - [x] Remove `import logging` (line 19)
- [x] **3a-2.** Edit `routes/weekly_summary.py` — remove dead import:
  - [x] Remove `from utils.business_logic import BusinessLogic` (line 8)
- [x] **3a-3.** Validate: `.venv/Scripts/python.exe -m pytest tests/test_weekly_summary.py -q`
- [x] **3a-4.** Validate: `.venv/Scripts/python.exe -m pytest tests/ -q` — same pass count as baseline
- [x] **3a-5.** Run `pylint` / import audit after installing it into the current `.venv`:
  - [x] `.\.venv\Scripts\python.exe -m pylint --disable=all --enable=W0611 routes/exports.py routes/weekly_summary.py`
  - [x] `rg -n "make_response|sanitize_filename|create_content_disposition_header|should_use_streaming|^import logging$|BusinessLogic|\\bResponse\\b|\\bjsonify\\b" routes/exports.py routes/weekly_summary.py`

---

### [Phase 3b Wave 1] High-Confidence Internal Deletions
- [x] **3bW1-1.** Confirm the Phase 0 package-surface decision still allows Wave 1 deletions to be treated as internal-only.
- [x] **3bW1-2.** Confirm the dead `BusinessLogic` import in `routes/weekly_summary.py` is already removed.
- [x] **3bW1-3.** Delete `utils/helpers.py` only after:
  - [x] `rg -n "from utils\.helpers|import utils\.helpers" app.py routes utils tests e2e` returns no runtime callers
- [x] **3bW1-4.** Delete `utils/filters.py` only after:
  - [x] `rg -n "from utils\.filters|import utils\.filters|ExerciseFilter" app.py routes utils tests e2e` returns no runtime callers
- [x] **3bW1-5.** Delete `utils/database_init.py` only after:
  - [x] `rg -n "from utils\.database_init|import utils\.database_init|database_init" app.py routes utils tests e2e` returns no runtime callers
- [x] **3bW1-6.** Evaluate `utils/muscle_group.py` as optional Wave 1.5:
  - [x] `rg -n "MuscleGroupHandler|from utils\.muscle_group|import utils\.muscle_group" app.py routes utils tests e2e`
  - [x] If still test-only, delete `utils/muscle_group.py` and `tests/test_muscle_group.py` together
  - [ ] If not clearly safe, defer it
- [x] **3bW1-7.** Update docs / inventories for deleted modules in the same branch (`CLAUDE.md`, cleanup plan, legacy inventories)
- [x] **3bW1-8.** Validate with full pytest:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - [x] Current post-Wave snapshot: `959 passed, 1 skipped`

---

### [Phase 3b Wave 2] Package-Surface Contraction
- [x] **3bW2-1.** Record the explicit decision for `DataHandler`, `BusinessLogic`, and package-level `get_workout_logs()` in `utils/__init__.py`
- [x] **3bW2-2.** Edit `utils/__init__.py` after the explicit retirement decision:
  - [x] Remove `from .data_handler import DataHandler`
  - [x] Remove `from .business_logic import BusinessLogic`
  - [x] Remove `"DataHandler"` and `"BusinessLogic"` from `__all__`
  - [x] Remove the package-level `get_workout_logs()` compatibility export
- [x] **3bW2-3.** Delete `utils/business_logic.py` only after:
  - [x] `rg -n "BusinessLogic|from utils\.business_logic|import utils\.business_logic" app.py routes utils tests e2e` showed no supported runtime callers
  - [x] `tests/test_business_logic.py` was deleted in the same change
- [x] **3bW2-4.** Delete `utils/data_handler.py` only after:
  - [x] `rg -n "DataHandler|from utils\.data_handler|import utils\.data_handler|from utils import .*DataHandler" app.py routes utils tests e2e` showed no supported runtime callers
  - [x] `tests/test_data_handler.py` was deleted in the same change
- [x] **3bW2-5.** Re-run full pytest after the Wave 2 deletion work:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q` -> `930 passed, 1 skipped`

---

### [Phase 3c] Delete Orphaned Templates
- [x] **3c-1.** Pre-verify runtime references:
  - [x] `rg -n "dropdowns\.html|filters\.html|table\.html|exercise_details\.html|debug_modal\.html|workout_tracker\.html" routes templates static tests e2e`
- [x] **3c-2.** Delete `templates/dropdowns.html`
- [x] **3c-3.** Delete `templates/filters.html`
- [x] **3c-4.** Delete `templates/table.html`
- [x] **3c-5.** Delete `templates/exercise_details.html`
- [x] **3c-6.** Delete `templates/debug_modal.html`
- [x] **3c-7.** Delete `templates/workout_tracker.html`
- [x] **3c-8.** Validate: `npx playwright test e2e/smoke-navigation.spec.ts --project=chromium --reporter=line`
- [x] **3c-9.** Re-run full pytest after sub-phase completion:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q`

---

### [Phase 3d] Extract Duplicated Parse Functions
- [x] **3d-1.** Add shared `parse_counting_mode()` and `parse_contribution_mode()` to `utils/effective_sets.py`
- [x] **3d-2.** Update `routes/session_summary.py` to use the shared implementation
  - [x] Preferred safe path: keep `_parse_counting_mode()` and `_parse_contribution_mode()` as thin wrappers for one cycle
- [x] **3d-3.** Update `routes/weekly_summary.py` the same way
  - [x] Preferred safe path: keep `_parse_counting_mode()` and `_parse_contribution_mode()` as thin wrappers for one cycle
- [x] **3d-4.** Add or refresh direct tests in `tests/test_effective_sets.py`
- [x] **3d-5.** If wrappers are removed instead, update `tests/test_session_summary_routes.py` and `tests/test_weekly_summary_routes.py` in the same change
- [x] **3d-6.** Validate:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_session_summary.py tests/test_weekly_summary.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py tests/test_effective_sets.py -q`
- [x] **3d-7.** Re-run full pytest after sub-phase completion:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/ -q`
  - [x] Current post-`3d` snapshot: `963 passed, 1 skipped`

---

### [Phase 3e] Summary-Page Frontend Coupling Gate
- [x] **3e-1.** Record which updater path is authoritative for each summary page
  - [x] `static/js/app.js`
  - [x] `static/js/modules/summary.js`
  - [x] `templates/session_summary.html`
  - [x] `templates/weekly_summary.html`
- [x] **3e-2.** Confirm whether `static/js/modules/summary.js` still relies on inline updaters and/or `#counting-mode` for safe short-circuit behavior
- [x] **3e-3.** Confirm `GET /api/pattern_coverage` remains on its current deferred contract
- [x] **3e-4.** Validate current summary behavior before template refactor:
  - [x] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`
  - [x] Result: `21 passed`

---

### [Phase 3f] Extract Jinja2 Method Selector Macro (Descoped)
- [x] **3f-1.** Start only after Phase 3e is complete
- [x] **3f-2.** Strengthen `e2e/summary-pages.spec.ts` before extraction:
  - [x] Lock the selector labels, option text/value pairs, wrapper class, IDs, and inline `onchange` contract
  - [x] Assert selector-driven fetches still include the expected `counting_mode` / `contribution_mode` query params
- [x] **3f-3.** Create `templates/partials/_volume_controls.html` with `method_selector` macro
- [x] **3f-4.** Update `templates/session_summary.html`:
  - [x] Add `{% from "partials/_volume_controls.html" import method_selector %}`
  - [x] Replace the method-selector block only
  - [x] Leave the volume-legend block untouched
  - [x] Do not rename/remove inline `updateSessionSummary()` unless Phase 3e explicitly allows it
- [x] **3f-5.** Update `templates/weekly_summary.html`:
  - [x] Add the import line
  - [x] Replace the method-selector block only
  - [x] Leave the volume-legend block untouched
  - [x] Do not rename/remove inline `updateWeeklySummary()` unless Phase 3e explicitly allows it
- [x] **3f-6.** Validate:
  - [x] `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`
  - [x] Result: `21 passed`
  - [x] `npx playwright test --project=chromium --reporter=line`
  - [x] Result: `315 passed`
- [x] **3f-7.** Visual spot-check:
  - [x] `/session_summary`
  - [x] `/weekly_summary`
  - [x] Desktop and mobile screenshots reviewed from `logs/3f_visual_checks/`

---

### [Phase 3g] Consolidate Volume Classifier (Backend-only)
- [x] **3g-1.** Confirm this phase is backend-only:
  - [x] Do not touch `templates/session_summary.html`
  - [x] Do not touch `templates/weekly_summary.html`
  - [x] Do not touch `static/js/modules/summary.js`
  - [x] Do not touch `static/js/modules/sessionsummary.js`
  - [x] Do not touch `static/js/updateSummary.js`
- [x] **3g-2.** Edit `utils/volume_classifier.py` — replace `get_volume_class()` and `get_volume_label()` with table-driven `_VOLUME_TIERS` + `_classify()`:
  - [x] Add `_VOLUME_TIERS` list (descending thresholds: 30, 20, 10, 0)
  - [x] Add `_classify(total_sets)` helper returning `(css_class, label)`
  - [x] Rewrite `get_volume_class()` to delegate to `_classify()[0]`
  - [x] Rewrite `get_volume_label()` to delegate to `_classify()[1]`
  - [x] Do NOT touch `get_effective_volume_label`, `get_volume_tooltip`, `get_session_warning_tooltip`, `get_category_tooltip`, `get_subcategory_tooltip`
- [x] **3g-3.** Validate:
  - [x] `.\.venv\Scripts\python.exe -m pytest tests/test_volume_classifier.py tests/test_session_summary_routes.py tests/test_weekly_summary_routes.py -q` -> `104 passed`

---

### [Phase 3i] Decompose Bloated Functions (Retired - see phase5_3i_plan.md)
Retired - see `docs/phase5_3i_plan.md` §5A-§5H and `debug/5A_*.md`..`debug/5H_*.md`.

---

### [Phase 3j] Fix N+1 UPDATE Loop (Retired - see phase5_3i_plan.md)
Retired - see `docs/phase5_3i_plan.md` §5I-§5J, `debug/5I_test_hardening.md`, and `debug/5J_recalculate_exercise_order.md`.

---

### Post-Cleanup Final Gate *(superseded by 4.6 Granular Phase 4 Sub-Phases)*

> **This legacy flat checklist is superseded by [4.6 Granular Phase 4 Sub-Phases](#46-granular-phase-4-sub-phases-2026-04-10) above.** Do not execute it line by line. Run the `4A`–`4O` sub-phases instead. The mapping below exists only so historical check-marks are not lost.
>
> | Legacy line | Now lives in |
> |---|---|
> | Full pytest | `4C` |
> | Summary surfaces browser gate | `4D` |
> | Full E2E | `4E` |
> | Dead code scan (vulture) | `4F` |
> | Unused import scan (pylint) | `4G` |
> | Print audit | `4H` |
> | Raw DB access audit | `4I` |
> | Frontend orphan audit | `4J` |
> | Package-surface audit | `4K` |
> | File count + line count comparison | `4L` |
> | Manual workflow smoke | `4M` *(new)* |
> | Bug investigation / fixing | `4N` *(new)* |
> | Update `CLAUDE.md` | `4O` |
> | Checkpoint commits | `4A` *(new)* |
> | Known bugs capture | `4B` *(new, + `Known Bugs Triage` section)* |
