# Active Development

This file is the execution source of truth for autonomous development sessions. Use it when it conflicts with older narrative planning text.

## Current Objective

**2026-06-11 — A12 pyright Python-version reconcile SHIPPED (PR #76, squash `e2778c0`; CI/config only).** Aligned pyright's analysis target to the CI runtime: `pyrightconfig.json` `pythonVersion` 3.12 → **3.11** (every other CI job — tests/lint/e2e/frontend/security — already runs 3.11, so the type gate had been validating against a Python version the tests never execute on). Also updated the `typecheck` job's `setup-python` 3.12 → 3.11 + the py3.12 notice/summary/comment text, the hardcoded regenerate-note in `scripts/pyright_baseline_diff.py`, and regenerated `docs/ci_cd_phase3/pyright-baseline.json` under 3.11. **The job `name:` was left byte-for-byte unchanged** (`Type Check (tsc blocking + pyright measure-only)`) — required branch-protection context preserved; no branch-protection change. **Measurement (old-vs-new delta = ZERO):** pyright reports **190 diagnostics / 58 distinct keys** under 3.11, identical to 3.12 — symmetric difference 0 (no net-new, no removals, no swaps); `reportMissingImports` = 0 (intrinsic, venv/platform-independent), so the regenerated baseline reproduced on CI's Linux runner (Type Check green, 0 net-new). Only content change to the baseline JSON is the `_meta.note` version string. **Verification:** local baseline gate PASS (0 net-new); `tests/test_pyright_baseline_diff.py` 13 passed; CI all 8 required checks green, `CLEAN`. Local `main` = `origin/main` tip **`e2778c0`** (0 commits ahead). `data/database.db` never staged. **Remaining A12 (optional/deferred, no owner gate forcing them): app-JS `tsc` expansion (`static/js/modules/*`, 29 files / ~14.6k untyped LOC — large), JS unit tests (Vitest/Jest — greenfield, needs owner direction), known-red E2E baseline audit (13+17 reds live only in the manual deep gate, never gate a PR). No CI backlog item is blocking.**

---

**2026-06-11 — A8 F401 flip SHIPPED (PR #74, squash `18de45e`; CI + cleanup) — leftovers A8 fully closed.** Completed the last flake8 measure-only→blocking flip. Drove `flake8 --select=F401` (unused imports) from **56 findings → 0** by removing genuinely-unused imports across ~30 test files plus `app.py`, `routes/body_composition.py`, `routes/user_profile.py`, `utils/fatigue_data.py`, and two `scripts/`; deleted the stray root-level `replace.py` throwaway (one-off template editor, no callers). Then added `F401` to the **blocking** `--select` in `.github/workflows/ci.yml`'s "Lint with flake8" step and removed it from the measure-only diagnostics (only `F841` `except … as e` idiom remains measured, non-flip). The A8 "load-bearing re-exports" caveat proved **moot**: `utils/__init__.py` guards re-exports with `__all__` (zero F401), and `app.py`'s two hits were plain unused `flask` symbols (`render_template`, `url_for`), not side-effect imports. **Verification:** `flake8 --select=F401` = 0; full blocking set `E9,F63,F7,F82,F811,E711,E712,F401` = 0; **pytest 1595 passed**; CI all checks green, `CLEAN`. Shipped as a narrow PR separate from the same-session docs sync (PR #73 `dbedeee`, A11 handover). Local `main` = `origin/main` tip **`18de45e`** (0 commits ahead). `data/database.db` never staged. **Remaining CI backlog: A12 misc (pyright py3.11-vs-3.12 reconcile now DONE — see A12 block above, PR #76 `e2778c0`; remaining optional: expand tsc to app JS, JS unit tests, audit the 13+17 known-red E2E baseline). No measure-only flake8 flip candidates remain.**

---

**2026-06-11 — A11 `e2e-functional` sharding SHIPPED (PR #71, squash `17b9d7f`; CI/docs only) — leftovers A11 closed.** Split the required functional E2E coverage into a 2-way `e2e-functional-shard` matrix plus a fan-in `e2e-functional` gate that keeps the branch-protection context **`E2E Functional (Chromium)`** byte-for-byte. Each shard runs the identical explicit functional spec list from A10 with only `--shard=${{ matrix.shard }}/2` appended, on its own runner/server/freshly-seeded throwaway DB. **No `playwright.config.ts` change** (`fullyParallel: false` stays); **no branch-protection change**; the new `E2E Functional Shard 1/2` / `Shard 2/2` contexts are non-required. Failure artifacts upload per shard as `playwright-functional-shard-<i>-of-2`. **CI proof:** PR #71 green path had Shard 1/2 = 205 passed, Shard 2/2 = 190 passed, fan-in green, `mergeStateStatus: CLEAN`; a throwaway red-path PR #72 broke one shard-1 assertion and proved Shard 2 still ran/passed while the fan-in failed. Realized critical path ≈ **8m28s** vs pre-A11 single job **12m58s** (~35% saved at 2x runner cost). Files already updated by the A11 branch: `.github/workflows/ci.yml`, `e2e/CLAUDE.md`, `docs/ci_cd_phase1/PLANNING.md`, `docs/LEFTOVERS_BY_PRIORITY.md`. Guardrails: no production/pyright/flake8/tsc/schema/API/calc/visual-baseline change; `data/database.db` not staged. Local `main` = `origin/main` tip **`17b9d7f`** (0 commits ahead, after prerequisite PR #70 `cf63ef9`). **Remaining CI backlog after A11: A12 misc; F401 was the last measure-only flip candidate — now flipped to blocking (see A8 block above, PR #74 `18de45e`).**

---

**2026-06-11 — A10 E2E spec promotion SHIPPED (PR #69, squash `45b6bec`; CI/docs only) — leftovers A10 closed.** Promoted `accessibility` + `fatigue-stage4-smokes` + `volume-progress` into the **required** `e2e-functional` Chromium job (added to its spec list in `.github/workflows/ci.yml`). **No job rename / no branch-protection change** — required context `E2E Functional (Chromium)` unchanged, just wider. **CI proof: widened job ran 395 tests, 395 passed (12.2m)** (+45 over prior 350). Promotion evidence: throwaway `--repeat-each=5` ubuntu probe → **225/225 green, zero flakes**, + 2026-06-05 deep-gate full-e2e green + local pass. Coarse-threshold asserts (tap-target ≥32/≥44, viewport ±1px, overflow boolean), not pixel snapshots. Files: `.github/workflows/ci.yml`, `e2e/CLAUDE.md` (CI inclusion contract), `docs/LEFTOVERS_BY_PRIORITY.md` (A10 done). Guardrails: `nav-dropdown` + visual specs stay excluded; no production/pyright-baseline/flake8/tsc/schema/API/calc/visual-baseline change; `data/database.db` not staged. **⚠️ Post-merge watch:** monitor the first ~10 real PR runs of `e2e-functional` for geometry flakes (`volume-progress` ±1px / `fatigue-stage4-smokes` overflow); revert that single spec line if one appears. Local `main` was `origin/main` tip **`45b6bec`** after A10; A11 shipped next (see current block above). **A7–A11 shipped; remaining P2: A12 misc; F401 still measure-only.**

---

**2026-06-10 — pyright baseline-allowlist gate SHIPPED (PR #66, squash `8d110fa`; CI/test/docs only) — leftovers A9 closed.** pyright is now **blocking on net-new errors only** (no existing error fixed). The `typecheck` job keeps its measure-only count + artifact, then runs a blocking baseline-diff. New files: `docs/ci_cd_phase3/pyright-baseline.json` (190 diagnostics / 58 distinct keys, committed `pyrightconfig.json` py3.12+Windows; old ~138 plan figure predates code growth), `scripts/pyright_baseline_diff.py` (repo-relative POSIX path normalization, key = `file+rule+message+severity`, multiset counts, fails only on exceeded counts, `--write-baseline` regenerates, stdlib-only), `tests/test_pyright_baseline_diff.py` (13 cases). Baseline **reproduced exactly on CI Linux** (intrinsic diagnostics, zero `reportMissingImports`). **Gotcha:** the typecheck job `name:` is a branch-protection required-check context — an initial rename orphaned it (green-but-BLOCKED); reverted + pinned with a comment, did not touch protection. Guardrails: no existing pyright error fixed; `pyrightconfig.json`/F401/flake8/tsc/production/schema/API/calc untouched; `data/database.db` not staged. **Verification:** diff unchanged PASS / temp-error FAIL(1); `pytest tests/test_pyright_baseline_diff.py` 13 passed; CI all 8 checks green, `CLEAN`. Local `main` = `origin/main` tip **`8d110fa`** (0 commits ahead). Intervening since `6b6b528`: PR #65 (`e26b895`, A8 handover sync). **A8+A9 done; remaining P2: A10 (promote excluded specs — under investigation), A11 (shard e2e), A12 (misc); F401 still measure-only.**

---

**2026-06-10 — flake8 blocking-rule flip SHIPPED (PR #64, squash `6b6b528`; CI/test/docs only) — leftovers A8 closed.** First rung of the Phase 3 flake8 "path to blocking": `F811,E711,E712` (all already at **0**) added to the blocking `--select=E9,F63,F7,F82` in the `lint` job; that step's `--exclude` aligned with the measure-only `EXCL`. The measure-only diagnostics now track **F401 as the sole remaining flip candidate** (its flip still needs a guardrailed cleanup PR — `utils/__init__.py` re-exports + `app.py` side-effects are load-bearing). One E712 fix: `tests/test_plan_generator.py:594` `== True` → `is True`. Files: `.github/workflows/ci.yml`, `tests/test_plan_generator.py`, `docs/LEFTOVERS_BY_PRIORITY.md` (A8 done), `docs/ci_cd_phase3/PLANNING.md` (follow-up note). No production/calculation/schema/API change; `data/database.db` never staged. **Verification:** `flake8 --select=F811,E711,E712` → **0**; `pytest tests/test_plan_generator.py` → **38 passed**; CI all 8 checks green. Local `main` = `origin/main` tip **`6b6b528`** (0 commits ahead). Intervening since the `284dca4` block below: PR #61 (`6acc537`), PR #62 (`89062d1`), PR #63 (`0d33563`) — docs/test hygiene.

---

**2026-06-10 — Stage 4 observer evidence-pipeline test-hardening SHIPPED (PR #59, squash `672491c`; tests-only, no source behavior change).** Added `tests/test_fatigue_stage4_observer.py` — **26 pytest cases** covering the two scripts that *collect* the Stage 4 calibration evidence gating Learned Calibration **Phase 2D-D** (`scripts/fatigue_stage4_observer.py` + `scripts/fatigue_stage4_status.py`), which previously had **zero** test coverage. Purpose: protect the evidence-collection path so a future 2D-D unblock decision can trust the observer's output. Covers `_direction` band math, `_pending_combos` dedup, `_append_csv` header-once/parent-dir, `analyze`'s **≥2 same-direction = signal / 1 = noise** bar, and the **2D-D gate invariant** — `observe` on an empty `workout_log` returns 0, appends nothing, and writes nothing to the DB; with a seeded log it appends only logged-side unfilled rows and a re-run yields no duplicates; plus `fatigue_stage4_status.main` JSON facts. All DB access via the isolated tmp-path test DB; live `data/database.db` untouched and not staged. **Guardrails:** no `utils/fatigue.py` thresholds/bands/landmarks edit, no estimator-priority/calibration-formula change, no 2D-D implementation (still BLOCKED — see [`docs/user_profile/LEARNED_CALIBRATION_PLAN.md`](user_profile/LEARNED_CALIBRATION_PLAN.md) §"Phase 2D-D Gate Review"). **Verification:** `tests/test_fatigue_stage4_observer.py` → **26 passed**; adjacent fatigue suites + new file → **201 passed**; **full `pytest tests/` → 1582 passed** (1556 documented baseline + 26 new). **Since merged:** PR #60 (`284dca4`, dropped the puppeteer MCP server, kept context7); local `main` = `origin/main` tip `284dca4` (0 commits ahead).

---

**As of 2026-06-10 (latest session): active branch is `main`, in sync with `origin/main` (0 commits ahead), tip `284dca4`.** Since the 2D-C ship, PR #59 (`672491c`, Stage 4 observer evidence-pipeline tests) and PR #60 (`284dca4`, drop-puppeteer-MCP) have merged on top of PR #58 (`5bf4880`). Phase 2D-C (Workout Controls manual fatigue-context nudge controls) **shipped to `origin/main`** via PR #58 (squash `5bf4880`, merged 2026-06-09); feature branch `feat/calibration-phase-2d-c-manual-nudge` merged and deleted. Phase 2D-B shipped via PR #57 (squash `9fb1337`, 2026-06-09); Phase 2D-A via PR #56 (squash `39fdd17`, 2026-06-08). The entire learned-calibration MVP + Phase 2A/2B/2C/2D-A/2D-B/2D-C track is now **shipped to `origin/main`**.

**Phase 2D-C — manual fatigue-context nudge controls (PR #58, squash `5bf4880`, merged 2026-06-09).** A neutral manual-adjustment affordance inside the existing Workout Controls fatigue-context section: ± steppers for **Weight** and **Sets** plus **"Reset to suggestion"**. It is a **neutral manual nudge** (each stepper moves the input by its own native step, clamped to `min`), **not** a fatigue-derived delta (that mapping is gated to 2D-D). **Weight + sets only; reps deferred.** **Client-side only** — sets input values directly (no `input` event → no user-dirty/re-estimate), no API/write path, no persistence to `user_selection`/`workout_log`/`user_profile_lifts`; **Reset restores the estimator suggestion exactly** (`latestTracePayload` weight + sets). **Reuses the shared 2D-A fatigue-context toggle** (no new setting; toggle-off hides it). **No schema/backend behavior change.** Code: `static/js/modules/workout-plan.js`, `static/css/pages-workout-plan.css` (hand-maintained route bundle — no SCSS rebuild), `e2e/fatigue-context.spec.ts` (+1 spec, +1 toggle-off assertion). Guardrails: no estimator suggestion-number change, no estimator-priority change, no fatigue-threshold/landmark/formula change (`utils/fatigue.py` untouched), no plan-row writes, no auto-apply; **2D-D out of scope and gated.** **Verification (2026-06-09):** full `pytest tests/` **1556 passed** (client-side-only — no pytest delta); Chromium E2E `fatigue-context` + `workout-plan` + `learned-calibration` + `progression` + `user-profile` **98 passed**; CI all 8 checks green before merge.

**Phase 2D-B — Progression fatigue context (PR #57, squash `9fb1337`, merged 2026-06-09).** Extends the 2D-A advisory layer to the **Progression page only** (`POST /get_exercise_suggestions`), reusing the 2D-A shared toggle/settings/copy verbatim (one `fatigue_context_settings` row, no per-surface toggle). The suggestions response keeps `data` as the list (contract unchanged) and attaches the same additive `fatigue_context` block as a top-level sibling — present only when the toggle is on and the muscle resolves; omitted otherwise; exception-guarded. New `build_fatigue_context_batch()` performs **one** `build_fatigue_page_context` build per request (no per-exercise scan, no new fatigue math); shared `_neutral_block`/`_block_from_page` keep per-exercise output identical to the single builder. A distinct "Fatigue context" chip + section renders below the suggestion cards. Code: `utils/fatigue_context.py`, `routes/progression_plan.py`, `templates/progression_plan.html`, `static/js/modules/progression-plan.js`, `static/css/pages-progression.css`, `tests/test_fatigue_context.py` (+5), `tests/test_progression_plan_routes.py` (+3), `e2e/progression.spec.ts` (+1, CI-covered). Guardrails: no suggestion-number change, no progression-decision change, no estimator-priority change, no fatigue-threshold/landmark/formula change, no plan-row writes, no auto-apply; `utils/fatigue.py` untouched; 2D-C/2D-D out of scope. **Verification (2026-06-08):** focused pytest **115 passed**; broader affected pytest **217 passed**; full `pytest tests/` **1556 passed**; Chromium E2E `progression.spec.ts` **26 passed**, `fatigue-context.spec.ts` + `user-profile.spec.ts` **29 passed**.

**Phase 2D-A — advisory fatigue context (PR #56, squash `39fdd17`, 2026-06-08).** Additive, post-estimate, default-off advisory layer: a read-only fatigue note for the muscle an exercise trains, rendered inside Workout Controls "show the math" behind an **independent** Profile toggle (separate from Learned Calibration). New `fatigue_context_settings` table; new `GET/POST /api/user_profile/fatigue_context_settings`; the estimate response gains an optional `fatigue_context` block attached **after** `estimate_for_exercise()` returns (omitted when disabled → byte-for-byte unchanged). Reuses the shipped `utils.fatigue_data.build_fatigue_page_context` (no new fatigue math); shows both planned + logged when they disagree; neutral advisory fallback for unranked/unknown/`Unassigned`; every variant says "This does not change your suggestion." Code: `utils/fatigue_context.py` (new), `utils/database.py`, `app.py`, `routes/user_profile.py`, `templates/user_profile.html` + `templates/workout_plan.html`, `static/js/modules/user-profile.js` + `static/js/modules/workout-plan.js`, `static/css/pages-workout-plan.css`, `tests/test_fatigue_context.py` (new), `e2e/fatigue-context.spec.ts` (new), `tests/conftest.py`. **Verification (2026-06-08):** pytest `test_fatigue_context` + `test_user_profile_routes` → 53 passed; `test_database_user_profile` + `test_db_migration` + `test_harness_isolation` + `test_fatigue` + `test_fatigue_routes` → 159 passed; Playwright `fatigue-context` + `learned-calibration` + `user-profile` (Chromium) → 37 passed; **full `pytest tests/` → 1548 passed**. CI: all 8 checks green before merge.

The learned-calibration MVP + Phase 2A/2B/2C track is **shipped to `origin/main`**. Recent learned-calibration history (newest first): `eb4dbf6` (docs handover close-out), `d3cb404` (**PR #55** Phase 2C promote learned rows → Profile references), `bad70c6` (**PR #54** Phase 2B review surface), `0f8b4b7` (**PR #53** Phase 2A related-exercise transfer plumbing).

The prior 2026-06-04 `feat/learned-calibration-backend` branch (commits `8a6d39a` / `76d7490` / `5587784`) and its UI/UX follow-up work landed on `main` and the branch is gone — that handoff is **superseded** by the merged Phase 2C state below.

**Learned-calibration state (all on `main`):**

- **MVP** (PR #37 `fd2e2f5`) — exact-exercise learned calibration backend, settings, estimator integration, Profile controls, Workout Controls source UI/actions, workout-log notifications. Estimator priority: `exact learned → exact log → related learned → Profile → cold-start → default`.
- **Phase 2A** (PR #53 `0f8b4b7`) — read-only, ratio-gated related-exercise transfer; ships with zero seeded ratios so no behavior change until learned + related modes + a ratio row all exist.
- **Phase 2B** (PR #54 `bad70c6`) — read/control review surface on `/user_profile` (learned-calibration list, ignored-transfer controls, bulk reset). No estimator math change.
- **Phase 2C** (PR #55 `d3cb404`) — per-row "Promote to reference lift" graduates an exact learned row into `user_profile_lifts` (measured top set, basis-converted). No schema change, no estimator-priority change, no silent overwrite (`REFERENCE_LIFT_EXISTS` guard + UI confirm). Full pytest **1524 passed**; CI all 8 checks green.

**Remaining learned-calibration work:** Phase 2D design review is complete (owner answers locked, `38d3b1c`); **Phase 2D-A shipped** (PR #56, squash `39fdd17`), **Phase 2D-B shipped** (PR #57, squash `9fb1337`), and **Phase 2D-C shipped** (PR #58, squash `5bf4880` — see the top block). **2D-D** (actual suggestion modification) was **gate-reviewed 2026-06-09 and is BLOCKED on insufficient Stage 4 real-use evidence — do not start.** It is the first advisory→prescriptive step, so it needs explicit owner approval **and** evidence. Evidence today (insufficient): `workout_log` **0 rows**; no `stage4_calibration_log.csv` observer output; **0 of ≥2** same-direction real-use disagreements; the one historical real anchor agreed with the engine and the synthetic mismatch does not count. Unblock: non-empty representative multi-week `workout_log` + ≥2 same-direction real-use disagreements + owner approval to cross advisory→prescriptive + decisions on touched output(s)/magnitude/double-counting (G4). Conditional narrowest future sketch (NOT actionable): sets-only, user-accepted, client-side, no auto-apply, no persistence. Split + gate detail: [`docs/user_profile/LEARNED_CALIBRATION_PLAN.md`](user_profile/LEARNED_CALIBRATION_PLAN.md) §"Phase 2D-D Gate Review — BLOCKED (2026-06-09)".

**Guardrails honored across the track:** no auto-apply, Profile reference lifts written only via the explicit 2C promote action, planned `user_selection` rows untouched, historical `workout_log` untouched, `utils/fatigue.py` untouched. Phase 2D-A adds advisory context only — no suggestion-number change, no estimator-priority change, no fatigue-threshold/landmark/formula changes. `data/database.db` is runtime-only and **must not be committed** (owner policy).

---

**Prior (2026-05-29) — `main` state: local `main` is in sync with `origin/main` (0 commits ahead) after pushing `df9b6f9` (movement_pattern cleanup, 2026-05-25), `f2cdc23` (Stage 4 calibration observer tooling, 2026-05-29), and this handover sync on top of the prior `origin/main` tip `39193f6`. Fatigue Meter Phase 2 Path 1 shipped 2026-05-23 via PR #35 (`d5b80bf`); Stage 3 verify-suite gate closed 2026-05-24 (`1a93f66`); Stage 4 calibration window OPEN 2026-05-24, earliest close 2026-06-07 — the observer is ready and read-only but stays blocked until real `workout_log` data exists (empty as of 2026-05-29).** Phase 2 Stage 0 lock landed via PR #33 (`24c6f46`) and Stage 1 close via PR #34 (`be22286`); planning extracted earlier in `f01ccb9`. The 2026-05-23 hygiene session, the six in-flight scope commits, the KI-001 / KI-009 / §4.6 baseline / §5 expansion follow-ups, and the YouTube curation closure all landed before Phase 2 work began. The lead-up: Body Composition Issue #21 fully shipped via PR #31 (squash `20b4b24`, 2026-05-20) and hardened in PR #32 (`94482d7`, 2026-05-21, `captured_at` ISO validation + JS↔Python parity test); response-contract exceptions migrated 2026-05-21 (`cbf745a`); §5 YouTube curation landed in two passes — `cf21191` (2026-05-22, 36 rows) + `ff244aa` (2026-05-23, +20 rows → **56 cumulative**, curation closed by diminishing returns). 2026-05-23 also landed the six in-flight scopes as separate commits (Profile #17/#18 hooks `de3e4d0`; workout-cool §3.6 Profile bodymap `18ad223`; navbar hover dropdowns `ef475cc`; navbar icon accents + motion `89561df`; Body Composition visual baselines `40d7dd2`; ui-hardening spec + Known Issues table `0ae5b39`), the docs-only hygiene commit, the KI-001 filter-cache deletion (`6d87284`), the KI-009 xlsxwriter exporter (`4bbe06b`) + docs (`f944366`), and the §4.6 visual-baseline `toHaveScreenshot()` lock-in (`b5b8c7a`). No active workstream remains in-flight.

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

`main`, **in sync with `origin/main` (0 commits ahead)**, tip `284dca4` (PR #60 `chore(mcp): drop puppeteer server, keep context7`, on top of `672491c` PR #59 Stage 4 observer evidence-pipeline tests, `8cb4c55` 2D-D gate-review-BLOCKED docs, `f442632` post-2D-C docs refresh, and `5bf4880` PR #58 Phase 2D-C manual fatigue-context nudge controls, squash merged 2026-06-09). The learned-calibration track merged on top of the prior 2026-05-29 handover-sync state: `0f8b4b7` (PR #53 Phase 2A), `bad70c6` (PR #54 Phase 2B), `d3cb404` (PR #55 Phase 2C), `eb4dbf6` (docs close-out), `39fdd17` (PR #56 Phase 2D-A), `acb67b0` (2D-A docs refresh), `9fb1337` (PR #57 Phase 2D-B), `f694333` (2D-B docs refresh), `5bf4880` (PR #58 Phase 2D-C). Feature branches `feat/calibration-phase-2d-c-manual-nudge` (PR #58) and `feat/calibration-phase-2d-b-progression-context` (PR #57) merged and deleted (local + remote). `data/database.db` runtime dirt is owner-approved and **never committed** (per `CLAUDE.md` agents-must-not list — it was never staged). Feature branches `feat/calibration-phase-2d-fatigue-context` (PR #56), `feat/calibration-phase-2c-promote-profile` (PR #55), `feat/calibration-phase-2b` (PR #54), and the Phase 2A branch were merged and deleted; earlier `feat/body-composition-issue-21` (PR #31), `feat/fatigue-meter-phase-2` (PR #34), and `feat/fatigue-meter-phase-2-stage-2` (PR #35) likewise merged and deleted.

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
