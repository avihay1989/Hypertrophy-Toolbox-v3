# Plan Review — CI/CD Phase 3: cheap static gates (MEASURE-ONLY / NON-BLOCKING)

*Council-plan for Phase 3 of [`docs/CI_CD_IMPROVEMENT_PLAN.md`](../CI_CD_IMPROVEMENT_PLAN.md). Phases 0 (#40), 2.1 (#41), 1 (#42) shipped on `main`. Owner constraint for this PR: **expose the backlog, block nothing.***

---

## Plan v1

**Goal**: Make the static-typing and lint backlog **visible** in CI — add pyright, `tsc --noEmit`, and hardened flake8 diagnostics as **non-blocking** jobs/steps, capture current failure counts + categories, and define the path to flip each gate to blocking in a follow-up PR. Nothing in this PR can fail a build or block a merge.

**Measured backlog (2026-06-05, this checkout)** — the deliverable this PR surfaces:
| Gate | Count | Categories |
|---|---|---|
| **pyright** (`pyrightconfig.json`, py3.12, whole repo) | **138 errors** | app + utils + tests type issues (e.g. `reportAssignmentType` in `utils/volume_progress.py:237`) |
| **tsc --noEmit** (`tsconfig.json`, e2e + playwright.config.ts only) | **31 errors** | 24× TS7006 (implicit-any params), 3× TS2307 (cannot-find-module, e.g. `/static/js/modules/*` imports in specs), 2× TS18046 (unknown), 1× TS2556 (spread), 1× TS2339 (property) |
| **flake8 hardened** (`F401,F811,F841,E711,E712`) | **122** | 65× F841 (unused locals — mostly `except … as e` unused), 56× F401 (unused imports, esp. `render_template`), 1× E712 |

**Scope**
- **In**:
  - New `typecheck` CI job: `pyright` + `tsc --noEmit`, **both non-blocking** (`continue-on-error: true`), printing error counts to the log.
  - Harden the existing `lint` job: keep the current blocking `E9,F63,F7,F82` selection, **add a separate non-blocking** flake8 step reporting `F401,F811,F841,E711,E712` with `--statistics` (does not fail the job).
  - (Optional, most-droppable) `pytest --cov` summary in the `test` job, soft, no threshold, report-only.
  - Capture the counts/categories above in this planning doc + the PR description, with a "path to blocking" note per gate.
  - Reconcile **only what's needed to make pyright run in CI**: create `.venv` + `pip install -r requirements.txt` so `pyrightconfig.json`'s `venv` resolves; run the typecheck job on **Python 3.12** to match the committed config (the 3.11-runtime-vs-3.12-analysis reconciliation is a *follow-up* concern, noted not fixed).
- **Out**:
  - Making any of pyright / tsc / flake8 **blocking** (that is the follow-up PR).
  - Fixing the 138 / 31 / 122 backlog (except *tiny, clearly-mechanical* fixes — e.g. if a handful of F401 are trivially safe to delete and obviously dead; otherwise leave them).
  - Expanding tsc to cover app JS under `static/js/modules/*` (no types exist; separate decision).
  - Branch protection (Phase 5), any `cron`/`schedule`, any production-code/app-behavior change, any calculation/schema/API change.

**Artifacts**
| Path | Change | Notes |
|---|---|---|
| `.github/workflows/ci.yml` | modify | Add `typecheck` job (pyright + tsc, non-blocking); add non-blocking flake8 diagnostics step to `lint`; (optional) `--cov` in `test` |
| `docs/ci_cd_phase3/PLANNING.md` | new | This doc + measured backlog + path-to-blocking |
| `pyrightconfig.json` | likely unchanged | Keep py3.12 + `.venv`; CI job creates `.venv` to satisfy it. Touch only if pyright cannot run otherwise |
| `tsconfig.json` | unchanged | tsc scope stays e2e + config; app-JS coverage is out of scope |
| `requirements*.txt` / dev deps | maybe | Only if `--cov` (pytest-cov) is kept; pyright via `npx pyright`, flake8 already installed in the lint job |

**Effort**: S–M · **Owner**: Claude · **Depends on**: nothing (independent of Phase 1)

**Sequence**
1. Re-measure counts cleanly (done above) and record in this doc.
2. Add the `typecheck` job: setup-python 3.12 → `python -m venv .venv` → `.venv` pip install requirements → `npx pyright` (`continue-on-error`); setup-node → `npm ci` → `npx tsc --noEmit` (`continue-on-error`). Each step ends by printing its count.
3. Add a non-blocking flake8 diagnostics step to the `lint` job (after the existing blocking selection) with `--select=F401,F811,F841,E711,E712 --statistics`, `continue-on-error: true`.
4. (Optional) Add `pytest --cov=. --cov-report=term-missing:skip-covered` soft summary to the `test` job; drop if it complicates the run.
5. Apply only tiny/mechanical backlog fixes if any are obviously safe; otherwise none.
6. Open PR; confirm the new job/steps run, are visibly non-blocking (workflow green even with errors logged), and the counts appear. Document the per-gate "path to blocking" in the PR body.
7. Do **not** enable branch protection. Do **not** add cron.

**Expected gates** (filled in by `test-strategist`)
- pytest: unchanged — full `tests/` still green (no Python logic touched).
- e2e: unchanged.
- other: `ci.yml` YAML valid; the new steps must be provably non-blocking (job conclusion success even when pyright/tsc/flake8 report errors).

**Open questions for the council**
1. Is running pyright at **py3.12** in CI (to match `pyrightconfig.json`) acceptable while the app runs on 3.11 elsewhere, given this is measure-only? Or should the typecheck job pin 3.11 and override the config's `pythonVersion`?
2. `pytest --cov` (3.3): keep it in this PR or drop as scope-creep? It adds a `pytest-cov` dependency and ~runtime.
3. Should the non-blocking flake8 diagnostics be a separate **step in the existing `lint` job** or its own job? (Plan v1 picks a step to avoid a second pip-install.)
4. Is creating a real `.venv` in the typecheck job the right way to satisfy `pyrightconfig.json`, vs. editing the config to point at the system interpreter? (Plan v1 prefers not editing the committed config.)
5. Any risk that `continue-on-error: true` masks a *real* future failure (e.g. the job infra breaking) and reads as "passing"? Should the step echo an explicit "NON-BLOCKING — N errors" banner so it's not mistaken for clean?

---

## Reviewer findings

### architecture-reviewer (agent a536530d7ea4ed921) — verdict: Needs revision (non-blocking only)
- Re-ground against the **live 8-job `ci.yml`** (lint at :38-63, test at :247-278; `e2e-functional`/`e2e-backup`/artifacts already present). Parent-plan §1.1/§3 describe a stale 6-job pipeline — ignore as pre-Phase-0/1 history.
- `pyrightconfig.json` also pins `pythonPlatform: "Windows"`; running on ubuntu shifts the count. Don't edit the config (shared, affects the win32 owner's local pyright). Note as a measurement caveat.
- `npx pyright` is unpinned (not in `package.json`); the 138 count can drift run-to-run. Pin `npx pyright@<version>` and record it next to the count. (`tsc` is fine — pinned via `typescript@5.9.3` + `npm ci`.)
- The 3 TS2307 are spec-side dynamic imports of untyped app JS (`/static/js/modules/*`) — an honest gap, correctly listed as Out. Phrase precisely.
- `continue-on-error: true` is the right mechanism but can read as green/mask infra failure — adopt the post-tool "NON-BLOCKING — N errors" banner (Open Q5). Don't use `|| true`.
- Drop `--cov` or, if kept, declare the `pytest-cov` requirements edit and never wrap the existing blocking pytest call. Flake8 diagnostics as an **added** step in `lint` (leave the `E9,F63,F7,F82` line byte-for-byte unchanged).

### test-strategist (agent a85413d9cdb1bf2aa) — verdict: Needs revision
- **B1 (blocking): DROP `pytest --cov`.** No `pytest-cov` in `requirements.txt` → `--cov` errors with "unrecognized arguments" → reds the one strong gate (`test` job has no `continue-on-error`). Coverage deserves its own PR (pin dep + `.coveragerc`). Verdict: DROP.
- **B2 (blocking): counts in a green job's log rot.** Write each gate's count to `$GITHUB_STEP_SUMMARY` (renders on the Checks tab) and upload raw outputs (`pyright --outputjson`, tsc output, `flake8 --statistics`) as an `if: always()` artifact (same pattern as the pytest JUnit upload). This is what makes the baseline diffable by the follow-up.
- **B3 (blocking): "path to blocking" is under-specified.** State explicit per-gate flip criteria: tsc → backlog==0; pyright/flake8 → baseline-allowlist / grow the blocking selection rule-by-rule as each reaches zero. Match the `e2e/CLAUDE.md` measure-first→flip precedent.
- **B4 (blocking): silent-drift hole.** Between this PR and the flip, new errors slip in unseen. Cheapest close: promote **tsc to blocking now** (31, mostly mechanical) — flagged for owner decision. If owner says block-nothing, the baseline artifact (B2) is mandatory.
- **B5 (blocking, signal quality): F841 is mostly noise** (`except … as e` logging idiom; 80 such sites, several load-bearing). Drop F841 from the headline set or report it separately labeled "expected idiom." Lead with F401/F811/E711/E712.
- Nits: pin tool versions for reproducibility; confirm flake8-as-step (Q3) and `.venv`-not-config (Q4) — both correct as planned.

### product-risk-reviewer (agent a0c6dd4a69e10c665) — verdict: Needs revision (one blocking item in-lane)
- **Finding 1 (blocking): the "tiny/mechanical fixes" carve-out is a behavior-change vector.** Proven: `utils/plan_generator.py:1397-1399` puts `str(e)` into a user-visible `persist_error` API field; line 1031 reads `e` in a log — a blanket "strip unused `except as e`" breaks both. F401 is load-bearing for `__all__` re-exports (`utils/__init__.py`) and blueprint side-effect imports (`app.py:13-25`). Fix: scope this PR to **zero backlog fixes** (diff = `ci.yml` + planning doc only), or an explicit allow/deny list. Recommends zero.
- Finding 2: correct the stale `ci.yml` baseline (converges with arch).
- Finding 3: PASS — no telemetry/cloud/cron; `.venv`/coverage artifacts are ephemeral runner state, not user data. Nit: pin pyright (supply-chain reproducibility).
- Finding 4: py3.12-analysis vs 3.11-runtime can inflate/mask the count — label the recorded count as "3.12-analysis, not 3.11-runtime authoritative," or override to 3.11.
- Findings 5–6: PASS — no calculation/effective-sets/terminology drift; no quiet resume of the parked fatigue Stage-4 workstream.

---

## Response matrix

| Finding | Reviewer | Disposition | Action in v2 |
|---|---|---|---|
| Drop `pytest --cov` — errors without `pytest-cov`, reds the one strong gate | test-strategist + arch | **accept** (blocking) | Remove step 4 / Open Q2 entirely. Coverage = separate future PR. |
| Counts in a green log rot — surface durably | test-strategist | **accept** (blocking) | Write counts to `$GITHUB_STEP_SUMMARY` + upload raw pyright/tsc/flake8 outputs as an `if: always()` artifact. |
| "Path to blocking" under-specified | test-strategist | **accept** (blocking) | Add explicit per-gate flip criteria to the doc + PR: tsc→0; pyright/flake8→baseline-allowlist / grow blocking selection rule-by-rule. |
| Silent-drift hole; promote tsc to blocking now | test-strategist | **reject for this PR** (owner constraint: block nothing) | Keep tsc measure-only. Mitigate drift via the baseline artifact (B2). Document "clear tsc's 31 → make tsc blocking" as the recommended **first follow-up**. |
| F841 is mostly noise | test-strategist + product-risk | **accept** | Headline diagnostics = F401, F811, E711, E712. Report F841 in a separate line labeled "expected `except as e` idiom — not a flip candidate." |
| "tiny/mechanical fixes" can change behavior (proven `str(e)` in API field) | product-risk | **accept** (blocking) | Scope this PR to **zero backlog fixes**. Diff = `ci.yml` + `docs/ci_cd_phase3/PLANNING.md` only. Document the F401/F841 allow/deny guardrail for the follow-up. |
| Re-ground against live 8-job `ci.yml` | all three | **accept** | v2 anchors on actual `ci.yml` (lint :38-63, test :247-278). New `typecheck` job + flake8 step are additive; touch no existing job/line. |
| Pin `npx pyright` version | all three | **accept** | Use `npx pyright@1.1.410` (the measured version); record it next to the counts. |
| `continue-on-error` can read as green / mask infra failure | arch | **accept** | Keep `continue-on-error: true`; add a post-tool `echo "NON-BLOCKING — <tool>: N errors"` banner computed from the tool's own output. |
| `pythonPlatform: Windows` + py3.12-vs-3.11 shift the count | arch + product-risk | **accept** | Don't edit `pyrightconfig.json`. Label the recorded count "pyright 1.1.410, py3.12 + Windows-platform config — approximate, not 3.11-runtime-authoritative." |
| flake8 as step in `lint` (Q3); `.venv` not config edit (Q4) | arch + test-strategist | **accept** (confirm) | flake8 diagnostics = new `continue-on-error` step in `lint`. typecheck job creates `.venv` + installs requirements so `pyrightconfig.json`'s `venv` resolves. |

---

## Plan v2

**Goal**: Unchanged — make the pyright / tsc / hardened-flake8 backlog **visible and diffable** in CI as non-blocking signal, with an explicit per-gate path to blocking. **Zero backlog fixes, zero blocking, zero new pytest dependency** in this PR.

**Key changes from v1:** drop `pytest --cov`; surface counts via `$GITHUB_STEP_SUMMARY` + an artifact (not just logs); add explicit per-gate flip criteria; lead diagnostics with F401/F811/E711/E712 and label F841 as expected idiom; **scope to zero code fixes** (diff = `ci.yml` + this doc); pin pyright; add the non-blocking banner; re-ground on the live 8-job `ci.yml`.

**Measured backlog (pyright 1.1.410, py3.12 + Windows-platform config, this checkout — approximate, not 3.11-runtime-authoritative):**
| Gate | Count | Lead categories | Flip-to-blocking criterion (follow-up) |
|---|---|---|---|
| tsc --noEmit (e2e + playwright.config.ts) | 31 | 24 TS7006 implicit-any, 3 TS2307 (untyped app-JS dynamic imports — out of scope), 2 TS18046, 1 TS2556, 1 TS2339 | **backlog == 0**, then drop `continue-on-error` (recommended FIRST follow-up — smallest, mostly mechanical) |
| flake8 hardened | F401 56, F811 0, E711 0, E712 1 (**meaningful**); F841 65 (expected `except as e` idiom — reported separately, not a flip candidate) | unused imports / redefinition / `==None`/`==True` | **grow the existing blocking `E9,F63,F7,F82` selection rule-by-rule** as each added rule reaches 0 (start with F811/E711/E712 which are already ~0; F401 after a guardrailed cleanup PR) |
| pyright (whole repo) | 138 | app+utils+tests type issues | **baseline-allowlist**: snapshot `pyright --outputjson`; follow-up blocks only *new* errors vs baseline |

**Scope**
- **In**: new non-blocking `typecheck` job (pyright@1.1.410 + `tsc --noEmit`, both `continue-on-error`, each with a count banner + `$GITHUB_STEP_SUMMARY` line); a non-blocking flake8 diagnostics step appended to the `lint` job (`F401,F811,F841,E711,E712 --statistics`); upload raw tool outputs as an `if: always()` artifact; the flip criteria above documented in this doc + the PR body.
- **Out**: `pytest --cov`; any backlog code fix; making any gate blocking; editing `pyrightconfig.json`/`tsconfig.json`; expanding tsc to app JS; branch protection; cron; any production-code/calculation/schema/API change.

**Artifacts**
| Path | Change | Notes |
|---|---|---|
| `.github/workflows/ci.yml` | modify | Add `typecheck` job; append non-blocking flake8 step to `lint` (leave `E9,F63,F7,F82` line unchanged); upload static-analysis outputs artifact |
| `docs/ci_cd_phase3/PLANNING.md` | new | This doc — measured backlog + per-gate flip criteria + F401/F841 guardrail for the follow-up |

**Sequence**
1. Add `typecheck` job: setup-python 3.12 → `python -m venv .venv` → `.venv` pip install requirements → `npx pyright@1.1.410 --outputjson > pyright.json` (`continue-on-error`), then a step parsing the count → banner + `$GITHUB_STEP_SUMMARY`; setup-node → `npm ci` → `npx tsc --noEmit | tee tsc.txt` (`continue-on-error`) → banner + summary.
2. Append flake8 diagnostics step to `lint` (`continue-on-error`): `flake8 . --select=F401,F811,F841,E711,E712 --statistics | tee flake8.txt`; banner + summary; the F841 line explicitly labeled expected-idiom.
3. Upload `pyright.json` + `tsc.txt` + `flake8.txt` as artifact `static-analysis-baseline` (`if: always()`).
4. No code fixes. Confirm pytest/e2e jobs are byte-for-byte unchanged.
5. Open PR; verify the workflow is green with the three counts visible on the Checks tab + artifact present; put the backlog table + flip criteria in the PR body.
6. No branch protection. No cron.

**Expected gates**
- pytest: unchanged (verify the `test` job diff is empty). e2e: unchanged.
- other: `ci.yml` YAML valid; the new job/step provably non-blocking (workflow conclusion success with errors logged); counts appear in `$GITHUB_STEP_SUMMARY` + artifact.

---

## Sign-off

- [x] Every finding has a disposition.
- [x] User approved Plan v2 (2026-06-05: "Approve v2 as written" — measure-only, zero fixes, tsc stays non-blocking).
- [x] Ready to implement.

---

## Follow-up — flake8 flip (2026-06-10, A8)

Executed the first rung of the flake8 "path to blocking": `F811,E711,E712` (the meaningful rules already sitting at ~0) added to the blocking `--select=E9,F63,F7,F82` line in the `lint` job, plus the one mechanical E712 fix (`tests/test_plan_generator.py:594` `== True` → `is True`). The blocking step's `--exclude` was aligned with the measure-only `EXCL`. **F401 is now the only remaining flip candidate** in the measure-only diagnostics — its flip still needs a guardrailed cleanup PR first (`utils/__init__.py` re-exports + `app.py` side-effects are load-bearing). pyright/tsc criteria unchanged.
