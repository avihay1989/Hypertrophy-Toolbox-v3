# e2e/ — Orientation

## Purpose
Playwright Chromium specs covering UI flows end-to-end. `playwright.config.ts` auto-starts Flask via `.venv/Scripts/python.exe app.py` on port 5000; serial execution (`fullyParallel: false`).

## Key files
| File | Coverage |
|---|---|
| `fixtures.ts` | Shared `test` fixture (console-error collector), `ROUTES`, `API_ENDPOINTS`, `SELECTORS`, `waitForPageReady()`, `expectToast()` |
| `fixtures/database.visual.seed.db` | Seed DB used by visual specs (committed; whitelisted in `.gitignore`) |
| `smoke-navigation.spec.ts` | Page loads + nav cycle (no fixtures) |
| `dark-mode.spec.ts`, `nav-dropdown.spec.ts` | Theme + navbar |
| `workout-plan.spec.ts`, `workout-log.spec.ts` | Plan/log CRUD |
| `summary-pages.spec.ts`, `progression.spec.ts`, `volume-splitter.spec.ts` | Analyze + progress + distribute |
| `program-backup.spec.ts`, `user-profile.spec.ts` | Backup modal, profile questionnaire |
| `exercise-interactions.spec.ts`, `superset-edge-cases.spec.ts`, `replace-exercise-errors.spec.ts` | Per-row actions |
| `validation-boundary.spec.ts`, `error-handling.spec.ts`, `empty-states.spec.ts`, `accessibility.spec.ts` | Edge & a11y |
| `api-integration.spec.ts` | All API endpoints |
| `visual.spec.ts`, `volume-progress.spec.ts`, `fatigue-stage4-smokes.spec.ts` | Visual snapshots + recent feature smokes |

Full per-spec test count map: `.claude/rules/testing.md`.

## Conventions
- Reuse the `test` fixture from `fixtures.ts` — it fails specs that emit console errors.
- Reference routes via `ROUTES.X`, selectors via `SELECTORS.X` — keeps locators centralized.
- `npx playwright test --project=chromium --reporter=line` — Chromium only; Firefox/WebKit are not configured.
- `PW_REUSE_SERVER=1` reuses an already-running Flask process.

## Database isolation (web-server command)
- The suite runs against an **isolated throwaway DB**, never the developer's live `data/database.db`. `playwright.config.ts` points `webServer.env.DB_FILE` at `artifacts/e2e/database.e2e.db` and the `webServer.command` seeds it *before* launching the app: `prepare_e2e_db.py --output <db> && python app.py`.
- Seeding lives in the web-server command (not `globalSetup`) on purpose: Playwright starts `webServer` **before** `globalSetup`, so seeding in `globalSetup` races `app.py`'s first DB open (fails in CI on a fresh checkout).
- `e2e/scripts/prepare_e2e_db.py` snapshots the committed seed (`fixtures/database.visual.seed.db`), applies migrations, ensures the learned-calibration tables exist, then **wipes all user-state** (profile, reference lifts, plan, logs, calibration, backups) — full exercise catalog preserved. Every run starts from an identical clean slate; tests must not depend on ambient saved data.
- With `PW_REUSE_SERVER=1` and a server already running, the command (and reseed) is skipped — the reused server owns its own DB.
- `nav-dropdown.spec.ts` uses a real Playwright click for `#darkModeToggle`; keep it that way so desktop navbar actionability stays guarded. `workout-plan.spec.ts` still dispatches `#muscleModeToggle` because that broader workflow has its own historical layout note.

## CI inclusion contract (`e2e-functional-shard` matrix + `e2e-functional` gate / `e2e-backup` jobs)
The GitHub Actions gate runs a curated, deterministic subset on **ubuntu/Chromium** (not every spec). Auditable contract for all specs:

| Spec | CI placement | Reason |
|---|---|---|
| `accessibility`, `api-integration`, `body-composition`, `browser-navigation-state`, `dark-mode`, `empty-states`, `error-handling`, `exercise-interactions`, `fatigue`, `fatigue-stage4-smokes`, `learned-calibration`, `nav-dropdown`, `progression`, `replace-exercise-errors`, `smoke-navigation`, `summary-pages`, `superset-edge-cases`, `ui-hardening`, `user-profile`, `validation-boundary`, `volume-progress`, `volume-splitter`, `workout-log`, `workout-plan` | `e2e-functional-shard` matrix job (`--shard=i/2`) | Deterministic functional/product coverage |
| `smoke-navigation` | also `e2e-smoke` job | Fast standalone "is the app up" signal |
| `program-backup` | `e2e-backup` job (isolated) | Live backup/restore mutations — own server + fresh seed avoids intra-run sequential-DB pollution without any between-spec reset |
| `accessibility`, `fatigue-stage4-smokes`, `volume-progress` | **promoted to `e2e-functional` (A10, 2026-06-11)** | Were measure-first (a11y run-cost; geometry/sub-pixel asserts). Promoted after a 5×-repeat ubuntu stability probe (225/225 green, zero flakes) + the 2026-06-05 deep-gate full-e2e green. Their asserts are coarse thresholds (tap-target ≥32/≥44, viewport-bound ±1px, overflow boolean), not pixel-exact snapshots. Watch the first ~10 PR runs for any geometry flake; revert that one spec line if one appears. |
| `nav-dropdown` | **promoted to `e2e-functional` (2026-06-11)** | Fixed the 1440px dark-mode-toggle actionability red with compact desktop navbar utility chrome; spec now uses a real Playwright click. |
| `visual`, `visual-baseline-thumbnails` | manual deep gate only (`visual-linux` job) | Cross-OS rendering: compared against Linux baselines, never a required PR check. See "Visual spec contract" below. |

- The functional/backup specs assert **current shipped behavior**. A future intentional behavior change (e.g. a fatigue Stage-4 threshold tweak) must update the spec deliberately — it should not be treated as "CI caught a regression."
- **Sharded n=2 (leftovers A11).** The functional set runs as a 2-way matrix (`e2e-functional-shard`, `--shard=${{ matrix.shard }}/2`, `fail-fast: false`). Each matrix leg is its own runner with its own setup/server/freshly-seeded throwaway DB (seeded by the `webServer` command per server start), so cross-shard is clean by construction and within-shard serial order-safety (`fullyParallel: false` / `workers: 1`) is unchanged — `playwright.config.ts` is **not** modified for sharding. The **single branch-protection required check** stays the `e2e-functional` **fan-in gate** job, whose name `E2E Functional (Chromium)` must stay byte-for-byte (renaming it orphans the required check and blocks every PR). The per-shard contexts `E2E Functional Shard 1/2` / `E2E Functional Shard 2/2` are **not** required checks — do not add them to branch protection. The gate is `if: always()` + `needs: e2e-functional-shard` and is green iff `needs.e2e-functional-shard.result == 'success'` (i.e. both shards passed). Pre-A11 the single `E2E Functional (Chromium)` job ran ~13 min; the n=2 split runs the shards in parallel for roughly half the wall-clock at 2× runner cost.
- **Artifact-upload privacy**: trace/screenshot/video/HTML-report uploads are safe *because* the suite runs only against the committed, user-state-wiped seed (`prepare_e2e_db.py`) — no real user data. CI must **never** upload the developer's live `data/database.db` or `data/auto_backup/`.

## Visual spec contract (`visual.spec.ts`, `visual-baseline-thumbnails.spec.ts`)
- **Manual deep gate only.** Visual specs never run on the PR path and are **never** a required status check. They run via the `visual-linux` job in `.github/workflows/deep-gate.yml`, opt-in behind the `run_visual` input (`workflow_dispatch`-only). An `if:`-gated, non-required job cannot block merge.
- **Platform-split baselines** (`snapshotPathTemplate` carries a `{platform}` directory segment):
  - **Linux** baselines live under `e2e/__screenshots__/linux/` — used by CI (`visual-linux` job runs on pinned `ubuntu-24.04`). Generated by the job's `generate` mode (`--update-snapshots`), uploaded as the `visual-baselines-linux` artifact, and committed by the owner after review — CI never pushes.
  - **Windows** baselines live under `e2e/__screenshots__/win32/` — the owner's local visual workflow (`process.platform === 'win32'`).
  - The two sets never collide and are maintained independently. An intentional UI change re-baselines both.
- **`PW_VISUAL_SEED=1`** selects the plan-bearing visual seed (`prepare_visual_db.py`) over the user-state-wiped functional seed (`prepare_e2e_db.py`) in the `playwright.config.ts` webServer command, so the throwaway DB is seeded with the canonical visual data (plan rows + `media_path` thumbnails) **before Flask opens it** — no per-spec runtime DB rewrite. The `visual-linux` job sets it; local visual runs set it too. Default (unset) keeps the functional suite on `prepare_e2e_db.py`.
- **Runner image is pinned** (`ubuntu-24.04`, not `ubuntu-latest`): the generate and compare runs must share one image so the Chromium/freetype/font renderer matches by construction. A deliberate runner bump requires a re-baseline (`generate`); a silent `ubuntu-latest` promotion must not move pixels.

## Gotchas
- **Known historical flake**: `program-backup.spec.ts` (`Backup Center Page` describe block) — sequential DB-pollution flake observed in earlier full runs; passes in isolation. This is why CI runs it in the isolated `e2e-backup` job (see CI inclusion contract above), not alongside other DB-mutating specs.
- Visual snapshot regressions need an intentional re-baseline. Don't blanket-`--update-snapshots`.
- Chromium is the only configured project (`playwright.config.ts`).

## See also
- `.claude/rules/testing.md` — spec inventory + baselines
- `/run-e2e` skill (full or single spec) and `/verify-suite` skill (full gate)
- [docs/E2E_TESTING.md](../docs/E2E_TESTING.md)
