# CI/CD Improvement Plan

> **Status:** Reviewed draft; ready for phased implementation after the Phase 1
> E2E shard-safety prerequisite is handled
> **Author:** Claude Code session, 2026-06-05
> **Branch context:** authored while on `chore/e2e-db-isolation`
> **Scope:** Expand the GitHub Actions pipeline from a narrow smoke gate into a
> trustworthy production gate, given that **`main` IS production** for this
> local-first app.

---

## 0. Framing: what "production" means here

This is a **local-first, single-user Flask app** (`localhost:5000`, no auth, no
cloud, no remote DB — see CLAUDE.md §1 non-goals). There is no deployed server.
The owner's definition, confirmed:

> **production = push to `main`.**

This single fact drives the entire design:

- There is **no meaningful "post-merge gate."** Anything that runs *after* merge
  to `main` runs *after* code has already shipped. Therefore **every check that
  protects production must be a required PR check** enforced by branch
  protection.
- Manual deep-gate runs on `main` or a PR branch are **not** prevention unless
  they are run before merge. They are for checks too slow or too
  environment-sensitive to block every PR. Do **not** schedule cron jobs for
  this repo; the owner wants deep checks triggered during development, not by
  time-based automation.
- The Codex/earlier suggestion of a "CD / package / publish / rollback" phase
  does **not** apply as written — there is no artifact to publish. The "release
  event" is the merge itself. If distribution ever becomes a real need
  (tagged zip, installer), that is a *separate future decision*, noted in
  §6 "Worth considering" but explicitly **out of scope** here.

---

## 1. Current state

### 1.1 What exists (`.github/workflows/ci.yml`)
Six parallel jobs:

| Job | What it does | Strength |
|---|---|---|
| `security-audit` | `pip-audit` (one CVE ignored, no upstream fix) | Real, blocking |
| `lint` | flake8 — **fails only on syntax/undefined-name** (`E9,F63,F7,F82`); everything else `--exit-zero` | Weak (advisory) |
| `frontend-build` | `npm ci` + `npm run build:css` | Real, blocking |
| `e2e-smoke` | **only `smoke-navigation.spec.ts`** (1 of 27 specs) | Token product gate |
| `test` | full **pytest** (`tests/ -v`) | **Strong — the one real gate** |
| `dependency-check` | `pip list --outdated`, `safety check` | Non-blocking (informational) |

### 1.2 What's GOOD (keep, don't disturb)
- **pytest is a genuinely strong gate** — ~1447 tests, real backend/business-logic
  coverage (CLAUDE.md §5).
- **DB isolation for E2E is being solved right now** — `playwright.config.ts`
  seeds a throwaway `artifacts/e2e/database.e2e.db` so the suite never touches
  live data. This is the prerequisite that makes broad E2E in CI possible.
- Jobs are **parallel** and **pip/npm cached** — fast feedback structure is
  already sound.
- Security + dependency scanning already wired (pip-audit, safety).

### 1.3 What's MISSING (the real gaps)
- **Product/UI coverage in CI is ~1/27 of the E2E suite.** CI can go green while
  workout-plan, workout-log, backup/restore, progression, summaries,
  accessibility, validation, supersets are all broken.
- **Backup→restore tests exist, but need stronger integrity assertions** —
  `tests/test_program_backup.py` already covers restore behavior. The missing
  piece is a row-for-row integrity check for the intended backup scope:
  `user_selection` program rows only.
- **No type checking** — `pyrightconfig.json` and `tsconfig.json` exist but
  neither `pyright` nor `tsc --noEmit` runs.
- **flake8 is effectively advisory** — only syntax errors fail.
- **No coverage reporting** — we know tests pass, not what they cover.
- **No failure artifacts** — Playwright writes HTML report + traces +
  screenshots to `artifacts/playwright/`, but CI never uploads them. A red gives
  a log line, not a trace.
- **No fresh-clone / missing-DB cold-start smoke.**
- **No old-DB migration compatibility test** (startup ALTERs / `add_*_table`
  helpers upgrade an existing DB silently — untested against a real old DB).
- **No JS unit/lint gate** (many JS modules, zero frontend unit tests).
- **No branch protection** making any of this *required* before merge.

### 1.4 The honest verdict
The pipeline is **lopsided, not useless.** It catches backend regressions well
and product regressions almost not at all. It is fast (~1.5–2 min) *because* it
barely exercises the product — not because it is efficient. A fast green that
doesn't mean anything is worse than a slower green that does.

---

## 2. Constraints that shape the plan (read before implementing)

1. **`main` = production → heavy checks must be required PR checks**, not
   post-merge. (See §0.)
2. **Visual regression cannot be naively turned on in CI.** Snapshots in
   `e2e/__screenshots__/` were generated on **Windows/Chromium**; CI runs
   **ubuntu-latest**. Cross-OS font hinting / sub-pixel rendering differs, so
   visual specs will diff ~100% on Linux. Local baselines already carry
   documented sub-pixel reds (CLAUDE.md §5). Visual-in-CI requires a *separate
   set of Linux-generated baselines* (or a pinned Docker render). This is real
   work, deferred to the manual deep gate (Phase 4).
3. **The full E2E suite has a documented red baseline** (13 fail + 17 did-not-run
   on the last full run, CLAUDE.md §5) — partly visual, partly viewport-width,
   partly the visual-DB preflight. The functional subset must be chosen to
   **exclude** these known-flaky/environment families so the new gate is green
   and trustworthy from day one.
4. **E2E DB isolation must land first.** CI cannot run E2E reliably until
   `chore/e2e-db-isolation` is merged (the seeded throwaway DB).
5. **Serial E2E is slow** (`fullyParallel: false`, full suite ~12.5 min).
   Broadening E2E without sharding would make the PR gate painfully slow →
   sharding is part of the plan, not an afterthought.

---

## 3. Target pipeline shape (two tiers)

```
PR opened / updated  ──►  TIER 1: REQUIRED PR CHECKS (branch-protected)
                          ├─ pytest (full)                              [exists]
                          ├─ backup/restore user_selection integrity     [new]
                          ├─ functional E2E (sharded, non-visual)        [new]
                          ├─ pyright + tsc --noEmit                      [new]
                          ├─ flake8 (curated, failing) + SCSS build      [harden]
                          ├─ pip-audit                                  [exists]
                          └─ upload traces/reports on failure            [new]
                                   │
                                   ▼  (all green) → merge → PRODUCTION

Manual deep gate ─────►   TIER 2: DEVELOPMENT-TRIGGERED CHECKS
(`workflow_dispatch`)     ├─ full E2E incl. accessibility                [new]
                          ├─ visual regression (Linux baselines)         [new+setup]
                          ├─ fresh-clone / missing-DB cold start          [new]
                          ├─ old-DB migration compatibility               [new]
                          └─ dependency health (outdated / safety)        [move here]
```

Expected PR-gate wall-clock: **~8–12 min** (from ~2 min). This is the
deliberate, correct cost of `main` being trustworthy.

---

## 4. Phases, steps, and what each step does

### Phase 0 — Land the prerequisite
**Goal:** make E2E runnable in CI at all.

- **Step 0.1 — Merge `chore/e2e-db-isolation` to `main`.**
  Verify the seeded throwaway DB path works headless in CI (the config already
  seeds via the web-server command to avoid the globalSetup race —
  `playwright.config.ts:15-20`). Confirm a CI run of even the existing smoke job
  still passes against the seeded DB on ubuntu.
  *Improves:* unblocks every later phase. *Risk:* low — work is already done,
  just needs the green CI confirmation + merge.

---

### Phase 1 — Broaden the product gate (highest value)
**Goal:** stop CI from going green while the product is broken.

- **Step 1.1 — Define the "functional E2E" set with a per-spec table.**
  Curate the list of specs that are deterministic and environment-stable. The
  initial target is broad required-PR coverage for functional/product specs,
  with visual, known-red, and environment-sensitive checks in the manual deep
  gate. Document the final inclusion/exclusion rationale in `e2e/CLAUDE.md`.

  | Spec | Target | Reason / current note |
  |---|---|---|
  | `accessibility.spec.ts` | manual-deep initially | Valuable, but keep out of required PR until run cost and CI stability are measured. Promote later if stable. |
  | `api-integration.spec.ts` | required-pr | Broad API contract/product integration coverage. |
  | `body-composition.spec.ts` | required-pr | Recent product surface; should not be unaccounted. |
  | `browser-navigation-state.spec.ts` | required-pr | Browser state, back/refresh/deep-link behavior. |
  | `dark-mode.spec.ts` | required-pr | Theme behavior; non-visual functional assertions. |
  | `empty-states.spec.ts` | required-pr | Important first-run and no-data behavior. |
  | `error-handling.spec.ts` | required-pr | User-visible failure behavior and double-click paths. |
  | `exercise-interactions.spec.ts` | required-pr | Per-row actions in core plan workflow. |
  | `fatigue-stage4-smokes.spec.ts` | required-pr candidate | Recent feature smoke; verify CI stability before branch protection. |
  | `fatigue.spec.ts` | required-pr | Recent analytics/product feature coverage. |
  | `learned-calibration.spec.ts` | required-pr | Recent profile/calibration feature coverage. |
  | `nav-dropdown.spec.ts` | required-pr | Fixed 2026-06-11; guards navbar dropdowns and real dark-mode-toggle actionability. |
  | `program-backup.spec.ts` | required-pr after shard-safety | High-value data-loss-adjacent flow; known historical sequential DB flake means it must wait for reset/order-safe grouping. |
  | `progression.spec.ts` | required-pr | Core progress workflow. |
  | `replace-exercise-errors.spec.ts` | required-pr | Edge/error states for replace flow. |
  | `smoke-navigation.spec.ts` | required-pr | Baseline navigation smoke. |
  | `summary-pages.spec.ts` | required-pr | Core analyze workflow. |
  | `superset-edge-cases.spec.ts` | required-pr | Complex plan interaction state. |
  | `ui-hardening.spec.ts` | required-pr candidate | Broad UI resilience; verify CI stability before branch protection. |
  | `user-profile.spec.ts` | required-pr | Core profile/workout controls workflow. |
  | `validation-boundary.spec.ts` | required-pr | Input validation and bounds. |
  | `visual-baseline-thumbnails.spec.ts` | manual-deep | Cross-OS visual baseline setup required. |
  | `visual.spec.ts` | manual-deep | Cross-OS visual baseline setup required. |
  | `volume-progress.spec.ts` | required-pr candidate | Valuable product workflow; verify CI stability before branch protection. |
  | `volume-splitter.spec.ts` | required-pr | Core distribute workflow. |
  | `workout-log.spec.ts` | required-pr | Core log workflow. |
  | `workout-plan.spec.ts` | required-pr | Core plan workflow. |

  *Improves:* replaces the vague `~22/27` claim with an auditable contract for
  all 27 specs.

- **Step 1.2 — Add a `e2e-functional` job with sharding.**
  Replace/augment `e2e-smoke` with a matrix-sharded job
  (`--shard=${i}/${n}`, n=2–3) so serial-but-parallel-across-runners keeps
  wall-clock ~5–8 min. Each shard installs Chromium, builds CSS, seeds its own
  throwaway DB. Keep `retries: 2` (already set for CI in config).
  *Improves:* broad coverage without a 12-min single-runner stall.

- **Step 1.2a — Prove DB reset or order-safe shard groups before enforcement.**
  `playwright.config.ts` seeds once when the web server starts. Inside one shard,
  specs still mutate the same DB sequentially, and `program-backup.spec.ts` has
  a documented historical sequential-DB flake. Before `e2e-functional` becomes
  branch-protected, either reseed/reset between specs or define explicit
  order-safe shard groups with a documented green baseline.

- **Step 1.3 — Upload failure artifacts.**
  On job failure, `actions/upload-artifact` the Playwright HTML report
  (`artifacts/playwright/report`), traces, screenshots, and videos
  (config already emits these on first-retry). Artifact names must include the
  job name and shard index, e.g. `playwright-functional-shard-1-of-3`, so
  parallel reports are easy to identify. Also upload pytest JUnit XML
  (`pytest --junitxml=...`) with a stable artifact name.
  *Improves:* a red CI becomes debuggable (trace viewer) instead of a log line.

---

### Phase 2 — Strengthen the highest-value existing test area
**Goal:** protect against the local-first nightmare: data loss.

- **Step 2.1 — Add row-for-row `user_selection` integrity assertions.**
  `tests/test_program_backup.py` already covers backup/restore behavior. Extend
  it with a deterministic row-for-row integrity test for the intended backup
  scope: program/routine rows in `user_selection`. Seed a known program with
  multiple routines, ordering, RIR/RPE/weight, rep ranges, and supersets; create
  a backup via the same path as `POST /api/backups`; mutate/erase the active
  program; restore; assert restored `user_selection` rows match the pre-mutation
  snapshot exactly for the columns backup owns.

  This app's documented backup scope is "snapshot/restore entire programs" in
  the local-first sense: routines and planned exercise selections. It is
  intentionally **not** full app-state backup. Do not assert that `workout_log`,
  profile, reference lifts, or calibration rows survive restore. Current restore
  behavior intentionally deletes `workout_log` when replacing the active
  program.

  Cover at least: full program restore, restore over a non-empty DB, and restore
  of a backup taken before a schema-affecting startup ALTER.
  *Improves:* the single most consequential untested path. *Why pytest not E2E:*
  faster, deterministic, and exercises the actual `utils/program_backup.py`
  logic without browser flake.

- **Step 2.2 — Add it to the Tier-1 gate.** It's part of the pytest job
  automatically once written; just confirm it runs in CI.

---

### Phase 3 — Cheap static gates
**Goal:** catch type/contract errors and real lint issues for near-zero runtime.

> **Status (2026-06-06):** Phase 3 measure-only landed (PR #43). The **tsc
> fast-follow is complete**: the `tsc --noEmit` backlog was cleared from 31 → **0**
> and the gate is now **BLOCKING** in `.github/workflows/ci.yml` (job
> "Type Check (tsc blocking + pyright measure-only)"). **pyright (138) and flake8
> remain measure-only**; their flip paths are unchanged (pyright →
> baseline-allowlist; flake8 → grow the blocking selection rule-by-rule). The 31
> tsc fixes were type-only (param annotations, casts, an `e2e/app-modules.d.ts`
> ambient declaration for `/static/js/modules/*` dynamic imports) — no runtime
> behavior change.

- **Step 3.1 — Add a `typecheck` job: `pyright` + `tsc --noEmit`.**
  Configs already exist (`pyrightconfig.json`, `tsconfig.json`). Start in a
  **non-blocking** mode for one or two PRs to measure the existing error
  backlog, then flip to blocking once clean (or once a baseline is agreed).
  **tsc is now blocking (done, see Status above); pyright stays non-blocking.**
  Important scope/setup notes:
  - `tsc --noEmit` currently checks `e2e/**/*.ts` and `playwright.config.ts`,
    not app JS under `static/js/modules/*`.
  - CI currently uses Python 3.11 while `pyrightconfig.json` targets Python
    3.12. Reconcile that before making pyright blocking.
  - `pyrightconfig.json` points at `.venv`, but CI does not currently create a
    repo-local venv. Either add a venv setup step for the typecheck job or
    adjust the pyright config/job so imports resolve correctly in CI.
  *Improves:* catches type drift, bad imports, API-shape mistakes before runtime.

- **Step 3.2 — Harden flake8.**
  Curate a rule set that *fails* (not just `E9,F63,F7,F82`) — e.g. unused
  imports/vars (F401/F841), undefined names already covered. Keep
  `--max-line-length=127` advisory if desired, but make correctness rules
  blocking. Measure backlog first; fix or `# noqa` the existing hits.
  *Improves:* real lint signal instead of a no-op job.

- **Step 3.3 — (Optional) coverage reporting.**
  Add `pytest --cov` with a report artifact and a *soft* coverage comment.
  No hard threshold initially — visibility first, ratchet later.
  *Improves:* shows which critical modules are under-covered.

---

### Phase 4 — Manual deep gate (`workflow_dispatch`, not scheduled)
**Goal:** catch slow/env-sensitive regressions during development without
running time-based jobs in the owner's work environment.

> **Status (2026-06-06): Phase 4 SHIPPED, including 4.2 Linux visual baselines.**
> `.github/workflows/deep-gate.yml` added (`workflow_dispatch` only — no cron),
> with jobs: **full-e2e** (every non-visual spec, accessibility included),
> **visual-linux** (4.2 — opt-in manual Linux/Chromium visual regression with
> committed `e2e/__screenshots__/linux/` baselines and `generate` / `compare`
> modes), **cold-start** (4.3 — boots app.py with no `data/database.db`,
> asserts `GET /` → 200), **old-db-migration** (4.4 — generates a pre-migration
> DB via `tests/fixtures/make_old_schema_db.py`, boots, asserts `/` + `/workout_plan`
> → 200, migrated columns/tables, and preservation of the seeded row; the fixture
> generator requires an explicit throwaway `--output` path), and
> **dependency-health** (4.5 — moved off the required PR path; it was never a
> required check, so branch protection is unaffected). Phase 4.2 shipped through
> PR #48–#51: `{platform}` snapshot split, canonical populated visual seed,
> `PW_VISUAL_SEED`, manual visual job pinned to `ubuntu-24.04`, 66 committed
> Linux PNGs, two green compare runs, and a proven deliberate drift red. No
> `ci.yml`, required-check, or branch-protection change.

- **Step 4.1 — Add a manually triggered workflow.**
  Add `workflow_dispatch` only. Do **not** add `schedule` / `cron`. The workflow
  can be run against `main` or a PR branch when the owner wants a deeper pass
  during development or pre-merge review. It runs full E2E incl.
  `accessibility.spec.ts`, plus the items below.

- **Step 4.2 — Visual regression with Linux baselines.**
  Generate a *Linux/Chromium* baseline set (run `--update-snapshots` once in the
  CI image, commit them under a Linux-specific snapshot path, or use a pinned
  Docker image so local + CI render identically). Only then enable
  `visual.spec.ts` + `visual-baseline-thumbnails.spec.ts` (the latter needs the
  `e2e/scripts/prepare_visual_db.py` preflight). **This step has real setup cost
  — do not bundle into Tier 1.**
  *Improves:* catches unintended UI drift; *cost:* baseline maintenance.

- **Step 4.3 — Fresh-clone / missing-DB cold-start smoke.**
  Spin the app with **no** `data/database.db` present; assert
  `initialize_database()` + the `add_*_table` helpers + `initialize_exercise_order`
  bring it up cleanly and `GET /` returns 200.
  *Improves:* protects the first-run experience for anyone who pulls `main`.

- **Step 4.4 — Old-DB migration compatibility.**
  Commit a historical `database.db` fixture (pre-`exercise_order`, pre-profile
  tables). Assert startup upgrades it without error and core routes work.
  *Improves:* guards the silent startup ALTER path (CLAUDE.md §5
  "exercise_order column").

- **Step 4.5 — Move `dependency-check` here.** Outdated/safety scans are
  informational; they don't belong on the critical PR path.

---

### Phase 5 — Enforcement
**Goal:** make the gate actually gate.

> **Status (2026-06-06): DONE** — council-reviewed (`docs/ci_cd_phase5/PLANNING.md`)
> and applied to the live repo. `main` is now branch-protected. Applied config
> (exact JSON + recovery commands recorded in the Phase 5 planning doc):
> - **8 required status checks**: `Run Tests`, `E2E Functional (Chromium)`,
>   `E2E Backup (Chromium, isolated)`, `E2E Smoke (Chromium)`,
>   `Type Check (tsc blocking + pyright measure-only)`, `Code Linting`,
>   `Frontend Build (npm ci + SCSS)`, `Security Audit`. `Dependency Health Check`
>   is **not** required (informational / continue-on-error end-to-end).
> - **strict = OFF** (solo repo; avoids re-running the flake-prone E2E set on
>   every unrelated merge and fighting auto-merge).
> - **required approving reviews = 0** (solo owner can't self-approve).
> - **enforce_admins = false** (documented admin-override escape hatch).
> - require PR before merge (no direct pushes to `main`); force-push + deletion
>   blocked.
> - **Invariant:** renaming any required job's `name:` in `ci.yml` requires
>   re-PUTting protection in the same PR (exact-string match). Known upcoming
>   break: the pyright→blocking flip will rename `Type Check (...)`.

- **Step 5.1 — Enable branch protection on `main`.** *(applied; see Status.)*
  Original target: require pytest, e2e-functional, typecheck, flake8,
  frontend-build, pip-audit, backup-restore (via pytest). **Deviations from the
  v1 sketch, per council + owner:** strict is OFF (not "up-to-date required"),
  and enforce_admins is false (escape hatch).
  *Improves:* turns the whole plan from "exists" into "enforced."
  *Note:* aligns with the documented PR workflow (auto-merge on green CI).

---

## 5. What this improves (summary)

| Gap today | After this plan |
|---|---|
| 1/27 product specs in CI | Audited functional spec set required on every PR |
| Backup/restore integrity under-specified | Row-for-row `user_selection` integrity required |
| No type checking | pyright + tsc blocking |
| Advisory lint | Correctness lint blocking |
| Red CI = log line | Red CI = trace + report + video artifacts |
| Cold start untested | Fresh-clone + old-DB migration smokes in manual deep gate |
| No UI drift detection | Visual regression in manual deep gate after Linux baselines |
| Nothing enforced | Branch protection makes `main` trustworthy |
| Fast-but-meaningless green | ~8–12 min green that actually means "safe to ship" |

---

## 6. Worth considering (not scheduled — owner decision)

- **Distribution / real CD.** If `main` ever needs to ship as an artifact
  (zip, installer, tagged GitHub Release), add a release workflow on tag push:
  build → smoke the artifact → attach to release → changelog/version check.
  Out of scope while "production = push to main."
- **Cross-browser (Firefox/WebKit).** Currently commented out in
  `playwright.config.ts:82-90`. Likely low ROI for a single-user localhost app;
  reconsider only if non-Chromium use is real.
- **Mobile/tablet viewport coverage** — same reasoning; add to the manual deep
  gate if needed.
- **JS unit tests** (Vitest/Jest) for the `static/js/modules/*` logic — worth it
  if JS complexity grows; currently zero coverage there.
- **Coverage thresholds** — ratchet up once Step 3.3 gives a baseline.
- **Required-vs-flaky audit of the existing 13+17 red baseline** — decide,
  per failing test, fix-or-quarantine, so "known reds" don't mask new reds.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| PR gate too slow → friction | Shard E2E (Step 1.2); keep visual/accessibility out of Tier 1 |
| New E2E job flaky on CI | Curate stable subset (Step 1.1); prove DB reset or order-safe shard groups before branch protection |
| Type/lint backlog blocks all PRs | Introduce non-blocking first, measure, then flip (Steps 3.1, 3.2) |
| Visual baselines unmaintainable | Linux baseline set + manual-deep only; never Tier 1 |
| Branch protection locks out hotfixes | Keep an admin override path documented |

---

## 8. Recommended execution order

1. **Phase 0** (merge DB isolation) — unblocks everything.
2. **Phase 2.1** (backup/restore integrity test) — highest-value test, independent of CI.
3. **Phase 1** (functional E2E + sharding + artifacts) — closes the biggest gap.
4. **Phase 3** (type/lint static gates) — cheap wins.
5. **Phase 5** (branch protection) — enforce Tiers once green and stable.
6. **Phase 4** (manual deep gate + visual Linux baselines) — last, highest setup cost.

> Suggested process: run `/council-plan` on Phases 1, 3, 5 (they touch the
> test-gate contract) before implementing, then `/verify-suite` after each phase.

---

## 9. Codex review findings (2026-06-05)

> **Reviewer:** Codex
> **Review stance:** The plan is directionally strong, but should be tightened
> before implementation or branch-protection enforcement.
> **Opus adjudication:** All findings accepted. Finding 1 downgraded from High
> to Medium because it is precision/contract clarity rather than an immediate
> correctness risk. Finding 2 and Finding 3 remain High.

### 9.1 Findings

1. **Medium — E2E coverage math and spec selection were inconsistent.**
   Original Phase 1 claimed `~22/27` meaningful product flows, but the include
   list named only 15 specs and excluded 4. Several important specs were
   unaccounted for: `user-profile`, `volume-splitter`, `body-composition`,
   `learned-calibration`, `ui-hardening`, `volume-progress`, `fatigue`, and
   `fatigue-stage4-smokes`. Resolution: Phase 1 now has a per-spec decision
   table for all 27 specs with `required-pr`, `manual-deep`, or excluded status.

2. **High — The backup/restore proposal conflicts with current behavior and
   existing tests.** The plan says there is no backup/restore round-trip test,
   but `tests/test_program_backup.py` already covers restore replacement,
   rollback, missing exercises, API restore, delete/prune behavior, and commit
   behavior. The real gap is stronger row-for-row integrity coverage. Also,
   Step 2.1 proposes seeding `workout_log` and profile as if restore should
   preserve them, but `utils/program_backup.py` currently snapshots only
   `user_selection` and restore intentionally deletes `workout_log`. Rewrite
   this phase as "strengthen existing backup/restore integrity tests." Opus
   confirmed the open product-scope question is already answered by CLAUDE.md:
   backup means snapshot/restore entire planned programs, not logs/profile/full
   app state.

3. **High — Sharding may not be safe without DB reset boundaries.** Each shard
   gets its own runner and throwaway DB, but tests within a shard still mutate
   a shared DB sequentially. The repo documents historical sequential
   DB-pollution flakes, including `program-backup.spec.ts`. Resolution: Phase 1
   now has an explicit DB reset or order-safe shard-group prerequisite before
   `e2e-functional` becomes required.

4. **Medium — Typecheck scope is narrower than the plan implies.** `tsc
   --noEmit` currently covers `e2e/**/*.ts` and `playwright.config.ts`, not the
   app's `static/js/modules/*.js` files. This is still useful, but it should be
   described as Playwright/config TypeScript checking, not app-JS checking.
   Also align the Python version story before requiring `pyright`: CI uses
   Python 3.11 while `pyrightconfig.json` currently targets Python 3.12. Opus
   added one practical setup note: pyright currently points at `.venv`, which CI
   does not create, so the typecheck job needs venv setup or config adjustment.

5. **Medium — Failure artifacts need shard-safe names.** Artifact upload is the
   right move, but parallel E2E shards should upload with names that include
   shard index and job name so reports/traces are easy to identify and do not
   collide in downloads.

### 9.2 Open questions

- **Closed:** Program backup is intentionally `user_selection` program state,
  not full app state. Do not expand backup semantics as part of CI hardening.
- **Still open:** Should accessibility remain manual-deep only? If it is stable
  after DB isolation, it may deserve required PR coverage for UI-heavy changes.

### 9.3 Recommended edits before implementation

- Replace the Phase 1 include/exclude prose with a complete per-spec decision
  table. **Done in this draft.**
- Reword Phase 2 from "missing backup/restore test" to "strengthen existing
  backup/restore integrity coverage." **Done in this draft.**
- Add an explicit DB-reset/shard-safety prerequisite before enabling
  branch-protected E2E shards. **Done in this draft.**
- Clarify that TypeScript checking does not currently cover app JS modules and
  note pyright venv setup. **Done in this draft.**
- Add artifact naming conventions for E2E shards. **Done in this draft.**
- Replace scheduled/nightly language with owner-triggered `workflow_dispatch`
  manual deep gates. **Done in this draft.**

---

*End of draft — awaiting Opus review.*
