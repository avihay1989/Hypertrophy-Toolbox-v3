# Leftovers by Priority

> **Purpose:** Prioritized punch list of unfinished / parked / deferred items discovered in `docs/` and in the local working tree. Sections A (current open backlog) and the closed-item audit trail below.
>
> **Live truth caveat:** `docs/MASTER_HANDOVER.md` + `docs/ACTIVE_DEVELOPMENT.md` (refreshed 2026-06-09) are the canonical current state. This file is the prioritized *to-do* view derived from them plus a full subsystem-doc + archive scan.
>
> **Review history:**
> - **v1–v10 (2026-05-23 → 2026-05-24):** initial backlog framing → in-flight triage → six-scope landing → KI-001/KI-009/§4.6/§5/worktree closures → Phase 2 Stage 4 reframe. (Detail preserved in the closed sections below.)
> - **v11 (2026-06-10, Opus full re-scan):** File was ~3 weeks + one major workstream stale (last real update 2026-05-24). Re-scanned all `docs/` subsystem folders + `docs/archive/`. Added **Section A — Current Open Backlog (Prioritized Plan)** reflecting everything that landed since v10: the entire **Learned Calibration Phase 2 track** (2A–2D-C shipped PRs #53–#58; **2D-D BLOCKED** 2026-06-09), the **CI/CD Improvement Plan** (all phases shipped PRs #40–#51 + optional fast-follows), the **Stage 4 observer tooling + tests** (PR #59 `672491c`), and the deferred **Fatigue Phase 3 / Profile v2** backlogs. Verified live facts: `workout_log` = **0 rows**; Stage-4 observer test PR **merged** (not pending); `main` tip `284dca4`. Old "row #15" reframed into Section A. Closed sections 0/1/2/4/5/6 retained unchanged as audit trail.
> - **v12 (2026-06-10, Codex review for Opus):** Re-reviewed v11 against live git, DB status, active docs, subsystem docs, and `docs/archive/`. Confirmed the P0/P2/P3 ordering is broadly right, but added a **P1 doc-truth cleanup block**: canonical handover files lag PR #59/#60, E2E inventory is stale (repo has 28 spec files), plan-volume archive needs shipped/historical banners across the whole subfolder, and a few active cross-references still say already-shipped Body Composition / Known Issues work is open. Also closed the proposed anterior-triceps PLANNING edit as already done.
> - **v13 (2026-06-10, Codex A4-A6 cleanup):** Closed the remaining P1 doc-truth housekeeping: plan-volume archive banners added to all three files, `E2E_TESTING.md` refreshed from 25 → 28 spec files, and stale Body Composition / Known Issues cross-reference sentences patched. `HEAD`/`origin/main` verified at `6acc537`; only P0 data-gated work, P2 optional CI fast-follows, and P3 owner-gated product remain.
> - **v14 (2026-06-10, Codex A7 cleanup):** Reproduced the `accessibility.spec.ts:283` focus-return flake locally (1/10 repeat failure), traced it to closing `#generatePlanModal` before Bootstrap's show transition finished, and patched the spec to wait for `shown.bs.modal` / `hidden.bs.modal` before asserting focus returns to `#generate-plan-btn`. Verified targeted repeat 10/10 and full `e2e/accessibility.spec.ts` 24/24. `HEAD`/`origin/main` before this local change: `89062d1`.

---

## Section A — Current Open Backlog (Prioritized Plan, 2026-06-10)

Ordered by what to handle first. Most of the project is shipped; the genuinely open work is small and front-loaded on **data collection**, then **cheap housekeeping**, then **optional polish**, then **owner-gated future product**.

### P0 — Gated on real usage data (you are the blocker, not code)

Both items below wait on the same thing: a populated `workout_log`. **Verified 2026-06-10: `workout_log` = 0 rows.** Nothing here is actionable by an agent until you actually log training sessions over multiple weeks.

| # | Item | Status | Gate / next action | Effort |
|---|---|---|---|---|
| A1 | **Fatigue Meter Phase 2 — Stage 4 calibration window** | OPEN since 2026-05-24; nominal earliest-close 2026-06-07 **passed without closing** because no data exists. | **Action: log real workouts.** The observer (`scripts/fatigue_stage4_observer.py`, daily scheduled task) is installed + idle and appends nothing while `workout_log` is empty. Then collect per-muscle band disagreements as `(muscle, period, engine band, felt label, direction)`. **Close rule: ≥2 same-direction real-use disagreements = signal; 1 = noise.** No threshold tuning before that bar. | owner data + review |
| A2 | **Learned Calibration Phase 2D-D — suggestion modification** | **BLOCKED 2026-06-09. Do not start.** First advisory→prescriptive step (2D-A/B/C all keep the number unchanged). | Unblock needs ALL of: non-empty multi-week `workout_log`; ≥2 same-direction real-use disagreements (the A1 evidence); explicit owner approval to cross advisory→prescriptive; decisions on touched output(s) / magnitude / double-counting (G4). Detail: [`user_profile/LEARNED_CALIBRATION_PLAN.md`](user_profile/LEARNED_CALIBRATION_PLAN.md) §"Phase 2D-D Gate Review — BLOCKED". | gated |

**Guardrails for both (no edits without ≥2 real-use disagreements + fresh owner go-ahead):** do not edit `utils/fatigue.py::MUSCLE_VOLUME_LANDMARKS` / `SESSION_FATIGUE_BANDS` / `WEEKLY_FATIGUE_BANDS`; do not edit `tests/test_fatigue.py` boundary tests; do not tune `scripts/fatigue_calibration_report.py::SCENARIOS`.

### P1 — Cheap housekeeping (safe to do now, no owner gate)

| # | Item | Status | Action | Effort |
|---|---|---|---|---|
| A3 | **Canonical handover docs lag current git truth** | ✅ **DONE 2026-06-10.** [`MASTER_HANDOVER.md`](MASTER_HANDOVER.md) + [`ACTIVE_DEVELOPMENT.md`](ACTIVE_DEVELOPMENT.md) current-state/branch blocks refreshed: PR #59 (`672491c`) marked shipped (was "pending"), PR #60 (`284dca4`) recorded, and the stale `5bf4880` tip references corrected. Historical commit chains left intact. Current `main`/`origin/main` tip after PR #61: `6acc537`. | Done. | — |
| A4 | **Stale archived plan-volume docs read as live work** | ✅ **DONE 2026-06-10.** Added "SHIPPED / historical reference only" banners to [`PLAN_VOLUME_INTEGRATION.md`](archive/plan-volume-integration/PLAN_VOLUME_INTEGRATION.md), [`PLAN_VOLUME_INTEGRATION_PLANNING.md`](archive/plan-volume-integration/PLAN_VOLUME_INTEGRATION_PLANNING.md), and [`PLAN_VOLUME_INTEGRATION_EXECUTION.md`](archive/plan-volume-integration/PLAN_VOLUME_INTEGRATION_EXECUTION.md). The historical implementation/gate text remains preserved below the banners. | Done. | — |
| A5 | **E2E inventory doc stale** | ✅ **DONE 2026-06-10.** [`E2E_TESTING.md`](E2E_TESTING.md) now says 28 Playwright specs, lists `fatigue-context.spec.ts`, `fatigue.spec.ts`, and `learned-calibration.spec.ts`, and keeps the no-full-suite-pass caveat. | Done. | — |
| A6 | **Stale cross-references in active trackers** | ✅ **DONE 2026-06-10.** [`user_profile/development_issues.md`](user_profile/development_issues.md) now points Issue #21 to the resolved Body Composition work and shipped Profile hooks; [`UI_SCENARIOS_GAP_ANALYSIS.md`](UI_SCENARIOS_GAP_ANALYSIS.md) now says the Known Issues map exists in §0. Historical review bodies are preserved. | Done. | — |

### P2 — Optional CI/CD fast-follows (all phases already shipped; pick when convenient)

All CI/CD phases (0/1/2.1/3/4/4.2/5) shipped via PRs #40–#51. These are documented opt-in hardening steps from [`CI_CD_IMPROVEMENT_PLAN.md`](archive/ci_cd/CI_CD_IMPROVEMENT_PLAN.md) + `archive/ci_cd/phase*/PLANNING.md`. None block anything. A7–A11 are now closed; **A12 misc is the only remaining P2 item** (no measure-only flake8 flip candidates left).

| # | Item | Notes |
|---|---|---|
| A7 | **Investigate `accessibility.spec.ts:283` focus-return flake** | ✅ **DONE 2026-06-10.** Reproduced locally, then fixed test timing in [`e2e/accessibility.spec.ts`](../e2e/accessibility.spec.ts) by waiting for Bootstrap modal lifecycle events before close/focus assertions. Verification: `npx playwright test e2e/accessibility.spec.ts -g "focus returns after modal closes" --project=chromium --repeat-each=10` = 10 passed; `npx playwright test e2e/accessibility.spec.ts --project=chromium` = 24 passed. |
| A8 | **Flip flake8 rules to blocking** | ✅ **DONE — fully closed 2026-06-11.** First pass (2026-06-10): added `F811,E711,E712` to the blocking `--select` in `.github/workflows/ci.yml` (they sat at ~0) + aligned `--exclude`; fixed `tests/test_plan_generator.py:594` E712. Final flip (2026-06-11, PR #74 `18de45e`): drove the last candidate **F401 from 56 → 0** (removed unused imports across ~30 test files + `app.py`/`routes/body_composition.py`/`routes/user_profile.py`/`utils/fatigue_data.py`/two scripts; deleted stray `replace.py`), added `F401` to the blocking `--select`, and dropped it from the measure-only diagnostics. The "load-bearing re-exports" worry proved moot — `utils/__init__.py` uses `__all__` (zero F401) and `app.py`'s hits were unused `flask` symbols, not side-effect imports. Verified `flake8 --select=F401` = 0 + pytest 1595 passed + CI green. **No measure-only flake8 flip candidates remain** (`F841` `except … as e` idiom stays measured-only by design). |
| A9 | **Flip pyright to blocking** | ✅ **DONE 2026-06-10.** Baseline-allowlist landed: committed snapshot [`docs/ci_cd_phase3/pyright-baseline.json`](ci_cd_phase3/pyright-baseline.json) (190 diagnostics / 58 distinct keys under the committed `pyrightconfig.json` — py3.12 + Windows; the old ~138 figure predates the learned-calibration/fatigue growth) + reusable [`scripts/pyright_baseline_diff.py`](../scripts/pyright_baseline_diff.py). The `typecheck` job keeps the measure-only pyright count/artifact, then runs a **blocking** baseline-diff that fails only on NET-NEW diagnostics (keyed by file+rule+message+severity, repo-relative POSIX path, multiset counts — reproduces cross-OS). Existing backlog never reds the build. Tests: `tests/test_pyright_baseline_diff.py` (13 cases incl. duplicate-count + resolved-baseline). Regenerate via `--write-baseline`. pyright config reconciliation (py3.11-vs-3.12) stays A12. |
| A10 | **Promote excluded specs to required-PR after a stability run** | ✅ **DONE 2026-06-11.** Promoted all three measure-first specs (`accessibility`, `fatigue-stage4-smokes`, `volume-progress`) into the required `e2e-functional` job by adding them to its Chromium spec list in `.github/workflows/ci.yml` — **no job/check-context rename, no branch-protection change**. Evidence: a throwaway `--repeat-each=5` ubuntu probe (`probe/a10-e2e-promotion-stability`, since deleted) → **225/225 green, zero flakes**, plus the 2026-06-05 deep-gate full-e2e green and a local Windows pass. CI inclusion contract in [`e2e/CLAUDE.md`](../e2e/CLAUDE.md) updated. **Watch:** monitor the first ~10 real PR runs for any geometry flake (`volume-progress` ±1px / `fatigue-stage4-smokes` overflow asserts); if one appears, revert that single spec line. Follow-up on 2026-06-11 fixed `nav-dropdown` issue #8 and promoted it too; visual specs stay excluded. |
| A11 | **Shard `e2e-functional` to n=2** | ✅ **DONE 2026-06-11.** Split the single `e2e-functional` job into a 2-way matrix `e2e-functional-shard` (`name: E2E Functional Shard ${{ matrix.shard }}/2`, `fail-fast: false`, `matrix.shard: [1, 2]`) running the **identical** explicit spec list with `--shard=${{ matrix.shard }}/2`, plus an `e2e-functional` **fan-in gate** that keeps the required check context `E2E Functional (Chromium)` byte-for-byte (`needs: e2e-functional-shard`, `if: always()`, green iff both shards pass). Each shard has its own setup/server/seeded throwaway DB; per-shard artifacts upload as `playwright-functional-shard-<i>-of-2`. **No `playwright.config.ts` change** (`fullyParallel: false` stays); **no branch-protection change** (the new `Shard 1/2`/`Shard 2/2` contexts are non-required). Green + red paths validated on the PR's own CI; realized shard runtimes + wall-clock savings recorded in the PR. CI contract in [`e2e/CLAUDE.md`](../e2e/CLAUDE.md) + [`ci_cd_phase1/PLANNING.md`](archive/ci_cd/phase1/PLANNING.md) updated. Pre-A11 single-job baseline: ~13 min. |
| A12 | **Lower-value / out-of-scope** | **Pyright py3.11-vs-3.12 reconcile ✅ DONE 2026-06-11** (PR #76 `e2778c0`): aligned `pyrightconfig.json` `pythonVersion` 3.12 → 3.11 to match the CI runtime + regenerated the baseline; **old-vs-new diagnostic delta = 0** (190 diags / 58 keys, symmetric diff 0, `reportMissingImports` 0), job name unchanged, no branch-protection change, CI green. **Remaining (optional, none blocking):** expand tsc to app JS (`static/js/modules/*` — 29 files / ~14.6k untyped LOC, large); add JS unit tests (Vitest/Jest — greenfield, needs owner direction); audit the manual-deep E2E baseline (visual/thumbnails/remaining geometry reds that never gate a required PR). Only if complexity grows. |

### P3 — Deferred-by-design future product (needs owner direction; do NOT start unprompted)

These are intentional future-phase scope, not oversights. Listed so this file is the single index; source-of-truth gates live in the linked docs.

**Fatigue Meter Phase 3** ([`fatigue_meter/PHASE2_PLANNING.md §10`](fatigue_meter/PHASE2_PLANNING.md), [`BRAINSTORM.md`](fatigue_meter/BRAINSTORM.md)):
- **Most concrete:** owner-vetted **MEV/MAV/MRV for the 6 unranked muscles** (Front-Shoulder, Rear-Shoulder, Lower Back, Hip-Adductors, Middle-Traps, Neck) — they render `—` until supplied. Do not invent thresholds.
- Per-muscle SFR cards · systemic + joint fatigue channels (B+C) · decay model · %1RM path (blocked on populated reference lifts, 0/1897) · technique modifier (opt-in) · `user_fatigue_thresholds` calibration table (first schema change) · partial-week "X/N expected" display · `/api/fatigue/*` endpoints.
- **📌 Fatigue body heatmap — COMMITTED (owner-requested 2026-06-13), NOT deferred.** Exception to this section's "do NOT start" rule — the owner has greenlit it. Pure visualization on `/fatigue` reusing the MuscleMap figure + `bodymap-svg.js` coloring + the `fatigue-*` band palette; **no math / threshold / schema / `/api` change**, calibration-freeze-safe. Gated only on the open decisions in [`HEATMAP_PLANNING.md §8`](fatigue_meter/HEATMAP_PLANNING.md); then `/council-plan` → implement (§6 there). Tracked in [`PHASE2_PLANNING.md §3`](fatigue_meter/PHASE2_PLANNING.md).

**User Profile v2** ([`user_profile/DESIGN.md §10`](user_profile/DESIGN.md), [`RELATED_EXERCISE_TRANSFER_DESIGN.md`](user_profile/RELATED_EXERCISE_TRANSFER_DESIGN.md)):
- Per-exercise override ratios · auto-update reference lifts from logged data · bodyweight add-on for weighted pull-ups/dips · "estimate based on N/14 lifts" confidence indicator · 6 open related-transfer ratio-seeding design questions (Phase 2A shipped with zero seeded ratios).

**Other deferred:** KI-008 multi-tab editing conflict detection ([`UI_SCENARIOS_GAP_ANALYSIS.md §0`](UI_SCENARIOS_GAP_ANALYSIS.md)) — out of scope under single-user/single-tab model, no demand signal.

### What is NOT open (closed since v10 — folded in here so this file is current)

- **Learned Calibration MVP + 2A + 2B + 2C + 2D-A + 2D-B + 2D-C** — all shipped (PRs #37/#53/#54/#55/#56/#57/#58). Only 2D-D remains (A2, blocked).
- **CI/CD Improvement Plan** — all phases shipped (PRs #40–#51). Optional fast-follows A7–A11 closed (A11 = `e2e-functional` sharding PR #71; A8 F401 flip fully closed PR #74 `18de45e`); A12's pyright py3.11 reconcile done (PR #76 `e2778c0`). Only optional A12 leftovers remain (app-JS tsc, JS unit tests, known-red E2E audit) — none blocking.
- **Stage 4 observer tooling + tests** — `scripts/fatigue_stage4_observer.py` + `_status.py` + health-check/installer PowerShell scripts; **test PR #59 (`672491c`) merged** (handover said "pending" — it is in fact on `main`).
- **`movement_pattern` catalog cleanup** — shipped `df9b6f9` (454 NULLs → 0).
- **Archive folder** — all historical; nothing open. `PUPPETEER_TEST_FINDINGS.md` is obsolete (puppeteer dropped, PR #60); the plan-volume-integration trio is shipped and now carries shipped/historical banners.
- **Anterior `triceps` workout.cool planning note** — already reflected in [`workout_cool_integration/PLANNING.md §3.3`](workout_cool_integration/PLANNING.md) and execution log; no longer a P1 item.

---

## Section B — Closed-Item Audit Trail (v1–v10, preserved unchanged)

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
| 3  | [`archive/body_composition/development_issues.md`](archive/body_composition/development_issues.md) | Issue #21 still showed `Open`. | Flipped to Resolved; all acceptance boxes ticked; pointed at PR #31, PR #32, and `de3e4d0` for the Profile hooks. |
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
| 11 | **KI-001 — Filter cache invalidation** | Resolved by deleting the module. Triage discovered `utils/filter_cache.py` was dormant code: zero `from utils.filter_cache` imports in `routes/`, `utils/`, or `app.py`; `get_cached_unique_values()` only called by `warm_cache()` which itself was never wired into startup; the then-live `routes/filters.py::get_unique_values` route hit `DatabaseHandler` directly (that unused route was later removed in WPB.6). Catalogue mutations (`save_exercise`, `remove_exercise_by_name`) had no HTTP path. Removing the module eliminated the "1 hour staleness" theoretical risk AND the latent SQLi exposure on the un-validated `f"SELECT DISTINCT {column} FROM {table}"` at line 85. `tests/test_filter_cache.py` (~440 LOC, 30+ tests) removed along with it. |

---

## 3. Remaining Backlog — superseded by Section A (2026-06-10)

> The single open row that lived here (row #15 — Fatigue Phase 2 Stage 4 calibration window) is now tracked as **A1** in Section A, with the live `workout_log = 0` fact and the passed 2026-06-07 nominal date recorded. Rows #4, #5, #8, #9, #12, #13, #14 were closed in v5–v9 (see Sections 0/4/5/6). The Phase-3 follow-ups previously parked here are now enumerated under **P3** in Section A.

---

## 4. CLOSED — Row #13 §4.6 Pixel Baselines (resolved 2026-05-23 by `toHaveScreenshot()` lock-in)

| # | Item | Resolution |
|---|---|---|
| 13 | **§4.6 pixel baselines** | Resolved. [`e2e/visual-baseline-thumbnails.spec.ts`](../e2e/visual-baseline-thumbnails.spec.ts) was promoted from inspection-only PNGs to committed `toHaveScreenshot()` baselines under [`e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots/`](../e2e/__screenshots__/visual-baseline-thumbnails.spec.ts-snapshots/). 18 PNGs cover the full §4.6 matrix at `maxDiffPixelRatio: 0.01`. Verified via the canonical isolated-DB harness → **18 passed in 14.3s**. See [`docs/workout_cool_integration/EXECUTION_LOG.md`](workout_cool_integration/EXECUTION_LOG.md) (top entry) for the full command sequence. |

---

## 5. CLOSED — Row #12 §5 YouTube Curation (resolved 2026-05-23 by diminishing returns)

| # | Item | Resolution |
|---|---|---|
| 12 | **workout.cool §5 curation** | Closed. Owner-approved `ff244aa` added 20 owner-vetted rows on top of `cf21191`'s starter 36, bringing [`data/youtube_curated_top_n.csv`](../data/youtube_curated_top_n.csv) to **56 curated rows + header**. Usage triage of the remaining ~1,841 uncurated catalogue rows confirmed all but one have 0–1 combined uses (lone exception `Barbell Close Grip Bench Press` at 2 uses); the 56-row set already covers every common/core lift with meaningful usage signal. Further expansion would require fabricating unvalidated YouTube IDs, which is worse UX than the search fallback. See [`docs/workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md`](workout_cool_integration/YOUTUBE_REFERENCE_VIDEOS.md) "Curation Closed" for the reopen flow. |

---

## 6. CLOSED — Row #14 Worktree Disposition (resolved 2026-05-23 by inspection + branch cleanup)

| # | Item | Resolution |
|---|---|---|
| 14 | **Worktree disposition** | Closed. Both worktree paths (`Hypertrophy-Toolbox-v3-visual-baseline-s4`, `Hypertrophy-Toolbox-v3-redesign-calm-glass`) already absent from disk; neither registered in `git worktree list`. The row's "still checked out locally" claim was stale. Two dangling branch refs verified redundant and deleted with owner approval: `test/visual-baseline-thumbnails @ 99910a4` (shipped via PR #22 squash `631b5f8` + later `b5b8c7a`) and `origin/redesign/calm-glass-2026 @ ba519df` (strict ancestor of `origin/main`). |

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
| Section A P0 (A1/A2)       | [`fatigue_meter/PHASE2_PLANNING.md`](fatigue_meter/PHASE2_PLANNING.md) Stage 4 + §10, [`user_profile/LEARNED_CALIBRATION_PLAN.md`](user_profile/LEARNED_CALIBRATION_PLAN.md) §"Phase 2D-D Gate Review", [`MASTER_HANDOVER.md`](MASTER_HANDOVER.md) |
| Section A P1 (A3–A6)       | `git log` (`6acc537` / `284dca4` / `672491c` / `f136f60` / `99f64ad`), [`MASTER_HANDOVER.md`](MASTER_HANDOVER.md), [`ACTIVE_DEVELOPMENT.md`](ACTIVE_DEVELOPMENT.md), [`E2E_TESTING.md`](E2E_TESTING.md), archived plan-volume docs, Body Composition/Profile/UI trackers |
| Section A P2 (A7–A12)      | [`CI_CD_IMPROVEMENT_PLAN.md`](archive/ci_cd/CI_CD_IMPROVEMENT_PLAN.md), `archive/ci_cd/phase{1,3,4_2,5}/PLANNING.md`, `.github/workflows/ci.yml`, [`e2e/accessibility.spec.ts`](../e2e/accessibility.spec.ts) |
| Section A P3               | [`fatigue_meter/PHASE2_PLANNING.md §10`](fatigue_meter/PHASE2_PLANNING.md), [`user_profile/DESIGN.md §10`](user_profile/DESIGN.md), [`user_profile/RELATED_EXERCISE_TRANSFER_DESIGN.md`](user_profile/RELATED_EXERCISE_TRANSFER_DESIGN.md), [`UI_SCENARIOS_GAP_ANALYSIS.md`](UI_SCENARIOS_GAP_ANALYSIS.md) |
| Section 0 (dirty tree)     | `git diff --stat HEAD`, `git status --short` (2026-05-23 revisions)                                          |
| Sections 1–6 (closed)      | per-row links above; preserved from v1–v10                                                                   |
| Section 7                  | grep `TODO|FIXME` across `utils/`, `routes/`, `static/js/`                                                    |

---

*Last updated: 2026-06-11 (v17 — Opus did the A12 pyright py3.11-vs-3.12 reconcile: aligned `pyrightconfig.json` to 3.11 to match the CI runtime + regenerated the baseline, PR #76 `e2778c0`; old-vs-new diagnostic delta = 0 (190 diags / 58 keys, symmetric diff 0, `reportMissingImports` 0), job name unchanged, no branch-protection change. v16 closed A8 F401 flip (PR #74 `18de45e`); v15 closed A11 sharding (PR #71 `17b9d7f`).) Closed sections 0/1/2/4/5/6 retained as audit trail. Live facts verified: `workout_log` = 0 rows; `main`/`origin/main` tip `e2778c0` (PR #76 merged). Remaining A12 leftovers (app-JS tsc, JS unit tests, known-red E2E audit) are optional and non-blocking.*
