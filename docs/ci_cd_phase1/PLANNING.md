# Plan Review — CI/CD Phase 1: Broaden the product gate

*Council-plan for Phase 1 of [`docs/CI_CD_IMPROVEMENT_PLAN.md`](../CI_CD_IMPROVEMENT_PLAN.md). Phase 0 (E2E DB isolation, PR #40) and Phase 2.1 (backup/restore integrity, PR #41) are already shipped on `main`.*

---

## Plan v1

**Goal**: Stop CI from going green while the product is broken — expand E2E coverage in CI from 1 spec (`smoke-navigation`) to the full functional/product spec set, sharded for wall-clock, with debuggable failure artifacts. (Branch protection making it *required* is Phase 5, out of scope here.)

**Scope**
- **In**:
  - (1.1) Finalize the per-spec functional-E2E inclusion contract (which of the 27 specs run in the new job) and document the rationale in `e2e/CLAUDE.md`.
  - (1.2) Add an `e2e-functional` GitHub Actions job using a matrix shard strategy (`--shard=i/n`), each shard self-contained (Python deps, Chromium, CSS build, its own seeded throwaway DB).
  - (1.2a) Establish DB-reset-or-order-safe-shard-groups so the new job is green and deterministic *before* Phase 5 makes it required. Handle the documented `program-backup.spec.ts` sequential-DB flake.
  - (1.3) Upload failure artifacts (Playwright HTML report, traces, screenshots, videos; pytest JUnit XML) with shard-safe names (`playwright-functional-shard-<i>-of-<n>`).
- **Out**:
  - Branch protection / required-check enforcement (Phase 5).
  - Visual specs (`visual.spec.ts`, `visual-baseline-thumbnails.spec.ts`) — cross-OS rendering, deferred to Phase 4 manual deep gate.
  - `accessibility.spec.ts` as required — plan §4 keeps it manual-deep "initially".
  - `nav-dropdown.spec.ts` — documented current red (off-viewport toggle).
  - pyright / tsc / flake8 hardening (Phase 3).
  - Any `schedule`/`cron` trigger (explicitly forbidden by plan §0).
  - Any production-code or app-behavior change.

**Artifacts**
| Path | Change | Notes |
|---|---|---|
| `.github/workflows/ci.yml` | modify | Add `e2e-functional` matrix job; keep `e2e-smoke` or fold it in; add artifact upload steps; add JUnit XML to `test` job |
| `e2e/CLAUDE.md` | modify | Document the per-spec inclusion/exclusion contract + shard-group rationale |
| `playwright.config.ts` | modify (maybe) | Add `junit`/`blob` reporter if needed for shard merge; possibly a `grep`/project for the functional set |
| `e2e/scripts/prepare_e2e_db.py` | modify (maybe, 1.2a) | If per-spec reset is chosen, expose a reset entry point or HTTP-triggerable wipe |
| `docs/ci_cd_phase1/PLANNING.md` | new | This doc |

**Effort**: M · **Owner**: Claude · **Depends on**: Phase 0 (done), Phase 2.1 (done)

**Sequence**
1. **1.1 — Inclusion contract.** Adopt the §4 per-spec table. Required-PR functional set (proposed): `api-integration`, `body-composition`, `browser-navigation-state`, `dark-mode`, `empty-states`, `error-handling`, `exercise-interactions`, `fatigue`, `learned-calibration`, `progression`, `replace-exercise-errors`, `smoke-navigation`, `summary-pages`, `superset-edge-cases`, `user-profile`, `validation-boundary`, `volume-splitter`, `workout-log`, `workout-plan`. **Candidates needing a stability run first** (included in the job but flagged, not yet relied on for Phase 5): `fatigue-stage4-smokes`, `ui-hardening`, `volume-progress`, `program-backup`. **Excluded**: `accessibility` (manual-deep), `nav-dropdown` (known red), `visual`, `visual-baseline-thumbnails` (cross-OS).
2. **1.2a first (de-risk before wiring the matrix).** Decide the shard-safety mechanism. Three options to evaluate:
   - (a) **Order-safe single-shard-group** — keep `fullyParallel: false`, run the functional set in one job (no matrix), rely on the existing once-per-run seed. Simplest; slowest (~8–10 min); doesn't solve in-run mutation flakes, only avoids cross-shard nondeterminism.
   - (b) **Per-spec reset** — add a mechanism to re-wipe user-state between spec files (e.g. a `globalSetup`-independent reset call, or a test-only reset route hit in `beforeAll`). Removes sequential-DB pollution entirely; most robust; most work.
   - (c) **Sharded by file with self-contained DB per shard** — `--shard=i/n`; each shard is its own runner/server/seed. Cross-shard is clean by construction; *within* a shard the sequential-mutation flake (`program-backup.spec.ts`) still exists, so pair (c) with grouping that keeps the backup/erase specs isolated or with (b).
   Proposed direction: **(c) + isolate the mutation-heavy specs** (put `program-backup` in its own shard or run it last), and only promote `program-backup` to relied-upon after a documented green baseline.
3. **1.2 — Matrix job.** Add `e2e-functional` with `strategy.matrix.shard: [1,2,3]` and `fail-fast: false`; run `npx playwright test <functional set> --project=chromium --shard=${{ matrix.shard }}/3 --reporter=line,junit`. Reuse the smoke job's setup steps (Python, Node, npm ci, build:css, playwright install --with-deps chromium). The webServer command already seeds per server start.
4. **1.3 — Artifacts.** `actions/upload-artifact@v4` `if: failure()` for `artifacts/playwright/report`, `test-results` (traces/screenshots/videos), named `playwright-functional-shard-${{ matrix.shard }}-of-3`. Add `--junitxml` to the pytest `test` job and upload as `pytest-junit`.
5. **1.1 doc close.** Write the final inclusion/exclusion table + shard grouping into `e2e/CLAUDE.md`.
6. Verify on the PR's own CI run (the new job runs on the PR), iterate on reds, confirm green + stable across at least 2 runs before declaring done. Do **not** enable branch protection (Phase 5).

**Expected gates** (filled in by `test-strategist`)
- pytest: unchanged (no Python logic change) — full `tests/` still green.
- e2e: the new functional set must pass on ubuntu Chromium; measure per-shard wall-clock.
- other: `/build-css` parity (job builds CSS); no visual snapshot changes.

**Open questions for the council**
1. Is sharding worth it vs. a single order-safe job, given total functional wall-clock may be ~8 min and matrix triples runner usage? (cost vs. latency)
2. For 1.2a, is a **test-only reset route** an acceptable addition to a no-auth local app, or does it violate a security/non-goal invariant? Alternative: per-shard `globalSetup` reseed without an app route.
3. Should `program-backup.spec.ts` be in the required set at all for Phase 1, or held as a candidate until the flake is provably fixed?
4. Does adding a `junit`/`blob` reporter to `playwright.config.ts` risk changing local-dev behavior or the visual baseline workflow?
5. Is folding `e2e-smoke` into `e2e-functional` safe, or should smoke stay as a fast separate signal?

---

## Reviewer findings

### architecture-reviewer (agent a9f1e26d03a939b06) — verdict: Needs revision
- **BLOCKING (plan-correctness):** Q2 reinvents the shipped `POST /erase-data` route (`app.py:162-224`), which already drops all user-state and re-runs the initializer chain. Adding a second reset route would be the real non-goal violation. Strike the "add a test-only reset route" alternative; if per-spec reset is needed, use existing `/erase-data` (confirm token) or the lighter `/clear_workout_plan` already used in `program-backup.spec.ts:45`. Note `/erase-data` runs `create_startup_backup()` — too heavy for `beforeEach`.
- **BLOCKING (would break the job):** `--reporter=line,junit` on the CLI *replaces* the config reporter array (`playwright.config.ts:43-46`), so the HTML report uploaded in 1.3 won't be produced; per-shard JUnit also collides on a fixed filename. Decide reporters in `playwright.config.ts` (CI branch), route JUnit/blob output to a per-shard env-var'd path.
- **non-blocking:** option (b) references a `globalSetup` that does not exist (seed runs in `webServer.command` precisely because globalSetup races). Drop that framing.
- **non-blocking:** `--shard=i/n` cannot order specs or pin a spec to a shard — "run program-backup last" needs a separate job/`--grep-invert`, not shard math.
- **non-blocking:** confirm each shard reseeds independently because `reuseExistingServer` is forced false under `CI` (`playwright.config.ts:9`); don't add `PW_REUSE_SERVER` to job env.
- **answered Q4:** reporters are independent of `snapshotPathTemplate`; CI-gate the junit/blob reporter → no local-dev or visual-baseline impact.
- **answered Q5:** keep `e2e-smoke` separate (fast independent signal) and include `smoke-navigation` in the functional set; pick explicitly.

### test-strategist (agent a10fa85ae96bb5418) — verdict: Needs revision; red-baseline accounting VERIFIED COMPLETE (19 required + 4 candidate + 4 excluded = 27)
- **BLOCKING B1:** `program-backup.spec.ts` must not be in the sharded job for Phase 1 — direction (c) does not fix *intra-shard* sequential pollution (seed runs once per server start; the spec does live backup saves while other specs mutate `user_selection`). Hold it out: run as a separate single-file job (own server/seed = free isolation) or defer. Answers open Q3 = "no, not in the required job for Phase 1." (Also: the `program-backup.spec.ts:79` citation is stale.)
- **BLOCKING B2:** `fatigue-stage4-smokes.spec.ts` asserts live geometry/tap-target/overflow at 375px — same cross-OS sub-pixel class the plan defers visual specs for; will flap on ubuntu. Exclude from Phase 1; its functional coverage already lives in `fatigue.spec.ts` + pytest.
- **non-blocking N1:** `volume-progress.spec.ts` is a viewport/geometry spec — downgrade to measure-first (covered by `volume-splitter.spec.ts`).
- **non-blocking N2:** `ui-hardening.spec.ts` is DOM-contract (toast/focus-trap/Escape), no pixel/geometry — the safest candidate to promote first.
- **non-blocking N3:** sharding n=3 is premature; ship Phase 1 as a single order-safe job (option a), get a documented green baseline, then shard to n=2 in a follow-up once per-spec timings are known. Phase 1's deliverable is a *green, trustworthy* gate, not minimal latency.
- **non-blocking N4/N5:** CI-gate junit/blob reporter; pytest `--junitxml` upload safe (use `if: always()` for trend data).
- **nits:** keep `e2e-smoke` standalone + in set; cite spec+describe block, not line 79.
- **Verification under-specified:** must run on ubuntu/Chromium; "stable across 2 runs" = 2 consecutive full runs with **zero retries consumed** on flaky families (`retries: 2` otherwise masks the B1 flake).

### product-risk-reviewer (agent aef36dd1b52484e75) — verdict: Needs revision (one blocking non-goal item)
- **BLOCKING Finding 1:** Step 1.2a option (b) "test-only reset route" adds a destructive production code path against the no-auth/local-first stance (CLAUDE.md §1 non-goals; `main` IS production). Drop the app-route reset; reset at the DB layer out-of-process by reusing the shipped, reviewed `wipe_user_state()` / `prepare()` in `prepare_e2e_db.py`. (Converges with arch BLOCKING #1.)
- **non-blocking Finding 2:** any reset path must reuse the single `USER_STATE_TABLES` source of truth and never touch the `exercises`/`exercise_isolated_muscles` catalog — no second table list, or specs depending on "catalog-full, user-state-empty" drift.
- **nit Finding 3:** artifact upload is privacy-safe *because* the suite is seed-only + user-state-wiped; document in `e2e/CLAUDE.md` that CI must never upload `data/database.db` or `data/auto_backup/`.
- **confirmed clean:** no telemetry/cloud/multi-user/cron; no calculation-semantics, terminology, or backup-contract drift; no user-facing copy change.
- **note:** the inclusion contract should state fatigue specs assert *current shipped* behavior, so a future Stage-4 threshold tweak isn't silently gated (parked-workstream guard).

---

## Response matrix

| Finding | Reviewer | Disposition | Action in v2 |
|---|---|---|---|
| Q2 reset reinvents shipped `/erase-data`; a new reset route is the real non-goal violation | architecture + product-risk | **accept** (blocking) | Remove all "new/test-only reset route" language. Phase 1 needs **no** between-spec reset — isolation comes from giving the one mutation-heavy spec its own job (own server+seed). No app-route change. |
| `--reporter=line,junit` CLI override suppresses the HTML report and collides per-shard | architecture | **accept** (blocking) | Move reporters into `playwright.config.ts` under a `process.env.CI` branch (`list`+`html`+`junit`/`blob`); route output to per-shard env-var'd paths. No CLI `--reporter` override. |
| `program-backup.spec.ts` not safe in a shared-DB job; (c) doesn't fix intra-shard pollution | test-strategist | **accept** (blocking) | Run `program-backup.spec.ts` as its **own** isolated `e2e-backup` job (separate runner → fresh seed). Out of the main functional invocation. |
| `fatigue-stage4-smokes.spec.ts` geometry will flap cross-OS | test-strategist | **accept** (blocking) | Exclude from Phase 1. Functional fatigue coverage stays via `fatigue.spec.ts`. |
| Sharding n=3 premature; ship single order-safe job first | test-strategist | **accept** | Phase 1 ships a **single order-safe `e2e-functional` job** (no matrix) + a separate `e2e-backup` job. Sharding to n=2 deferred to a fast-follow (documented in v2 "Deferred"). |
| `volume-progress.spec.ts` geometry — measure-first | test-strategist | **accept** | Exclude from Phase 1 job; note as measure-first candidate. |
| `ui-hardening.spec.ts` is the safe candidate to include | test-strategist | **accept** | Include `ui-hardening` in the functional set (DOM-contract, deterministic). |
| Keep `e2e-smoke` standalone AND include smoke in functional set | architecture + test-strategist | **accept** | Keep `e2e-smoke` job; `smoke-navigation` also runs in `e2e-functional`. |
| `--shard` can't order/pin specs | architecture | **accept** (moot for v2) | v2 has no matrix; isolation is by separate job, not shard math. Re-applies when sharding is revisited. |
| Reset must reuse `wipe_user_state` single table source; never touch catalog | product-risk | **accept** (moot for v2) | No reset path added in v2; recorded as a constraint for any future per-spec reset. |
| Artifact privacy: document seed-only safety; never upload live DB / auto_backup | product-risk | **accept** | Add the privacy note + "never upload `data/database.db`/`data/auto_backup/`" to `e2e/CLAUDE.md`. |
| pytest `--junitxml` upload `if: always()` | test-strategist | **accept** | Add `--junitxml`, upload `if: always()`. |
| Verification must be ubuntu/Chromium, 2 consecutive runs, zero retries consumed on the set | test-strategist | **accept** | Restate step 6 accordingly; treat any consumed retry on the functional set as a non-green signal to fix before done. |
| Inclusion contract should state fatigue specs assert *current shipped* behavior | product-risk | **accept** (nit) | Add that sentence to the `e2e/CLAUDE.md` contract. |
| `globalSetup`-independent reset references a non-existent file | architecture | **accept** | Drop the phrasing (moot — no reset added). |
| Stale `program-backup.spec.ts:79` citation | test-strategist | **accept** (nit) | Cite spec + describe block in docs, not a line number. |

---

## Plan v2

**Goal**: Unchanged — broaden CI E2E from 1 spec to the full functional/product set so CI stops going green while the product is broken, with debuggable failure artifacts. (Branch protection = Phase 5.)

**Key change from v1:** No sharding and **no reset mechanism** in Phase 1. The council showed (a) sharding is premature before per-spec timings exist and its only hard problem (intra-shard mutation pollution) is solved more simply by job isolation, and (b) every proposed between-spec reset either reinvents the shipped `/erase-data` route or violates the local-first non-goal. So Phase 1 = **two plain jobs sharing the existing seed-once-per-server model**, which is already proven by the current `e2e-smoke` job.

**Scope**
- **In**:
  - `e2e-functional` job — single runner, `fullyParallel:false`/`workers:1` (existing config), runs the deterministic functional set in one server/seed lifecycle.
  - `e2e-backup` job — single runner, runs only `program-backup.spec.ts` against its own fresh server/seed (free isolation for the one mutation-heavy spec).
  - Keep `e2e-smoke` as the fast standalone signal.
  - Reporters: add `junit` (+ keep `html`,`list`) in `playwright.config.ts` under a `process.env.CI` branch; route JUnit output to a job-named path.
  - Failure-artifact upload (`actions/upload-artifact@v4`) for the Playwright HTML report + `test-results` (traces/screenshots/videos), named per job. pytest `--junitxml` uploaded `if: always()`.
  - `e2e/CLAUDE.md`: the per-spec inclusion/exclusion contract, the job split + rationale, the "current shipped behavior" note, and the artifact-privacy guardrail.
- **Out**: sharding/matrix (deferred fast-follow), any reset route or `prepare_e2e_db.py` reset entry point, visual/accessibility/nav-dropdown/geometry specs, branch protection (Phase 5), Phase 3 static gates, any production-code/app-behavior change, cron/schedule.

**Functional set (e2e-functional job), 18 specs:**
`api-integration`, `body-composition`, `browser-navigation-state`, `dark-mode`, `empty-states`, `error-handling`, `exercise-interactions`, `fatigue`, `learned-calibration`, `progression`, `replace-exercise-errors`, `smoke-navigation`, `summary-pages`, `superset-edge-cases`, `ui-hardening`, `user-profile`, `validation-boundary`, `volume-splitter`, `workout-log`, `workout-plan`.
(That is 20 entries — `smoke-navigation` also has its own job; `ui-hardening` promoted from candidate.)

**Isolated job (e2e-backup):** `program-backup.spec.ts`.

**Excluded from Phase 1 CI (with reason):**
- `accessibility` — manual-deep (Phase 4), run-cost not yet measured.
- `nav-dropdown` — documented current red (off-viewport toggle).
- `visual`, `visual-baseline-thumbnails` — cross-OS rendering + visual-DB preflight (Phase 4).
- `fatigue-stage4-smokes`, `volume-progress` — geometry/sub-pixel assertions, measure-first before any inclusion.

**Artifacts**
| Path | Change | Notes |
|---|---|---|
| `.github/workflows/ci.yml` | modify | Add `e2e-functional` + `e2e-backup` jobs (reuse smoke setup steps); keep `e2e-smoke`; add `--junitxml` + uploads; per-job artifact names |
| `playwright.config.ts` | modify | Add `junit` reporter under `process.env.CI` branch; keep `list`+`html`; JUnit output path via env var |
| `e2e/CLAUDE.md` | modify | Inclusion/exclusion contract, job-split rationale, shipped-behavior note, artifact-privacy guardrail; fix stale flake citation |
| `docs/ci_cd_phase1/PLANNING.md` | new | This doc |

**Sequence**
1. Write the inclusion/exclusion contract + job split into `e2e/CLAUDE.md`.
2. Add the `process.env.CI`-gated `junit` reporter to `playwright.config.ts` (verify local `npx playwright test` still uses `list`+`html` only).
3. Add `e2e-functional` (explicit spec list or `--grep-invert` of the excluded/backup specs) and `e2e-backup` jobs to `ci.yml`, reusing the smoke job's setup; add artifact-upload steps (`if: failure()` for Playwright, `if: always()` for pytest JUnit).
4. Open PR; let the new jobs run on the PR's own CI. Iterate until **green on ubuntu/Chromium with zero retries consumed** on the functional + backup jobs across **2 consecutive runs**.
5. Do **not** enable branch protection (Phase 5). Update `docs/CI_CD_IMPROVEMENT_PLAN.md` Phase 1 status + CLAUDE.md §5 counts after green.

**Deferred to fast-follow (post-Phase-1, pre-Phase-5):** shard `e2e-functional` to n=2 once per-spec timings from step 4 show it's worth it; re-evaluate promoting `fatigue-stage4-smokes` / `volume-progress` / `accessibility` after a measured ubuntu stability run.

**Expected gates**
- pytest: unchanged — full `tests/` still green (no Python logic touched).
- e2e: `e2e-functional` + `e2e-backup` green on ubuntu/Chromium, zero retries consumed, 2 consecutive runs.
- other: `/build-css` parity (jobs build CSS); no visual snapshot changes; local-dev Playwright reporters unchanged.

---

## Sign-off

- [x] Every finding has a disposition.
- [x] User approved Plan v2 (2026-06-05: follow council — no sharding in Phase 1; accept council spec scope).
- [x] Ready to implement.
