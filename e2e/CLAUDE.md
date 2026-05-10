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

## Gotchas
- **Known current red (out-of-scope)**: `nav-dropdown.spec.ts:117` — dark-mode toggle off-viewport at 1440 width. Do not "fix" this without an explicit task.
- **Known historical flake**: `program-backup.spec.ts:79` — sequential DB-pollution flake observed in earlier full runs; it passed in the 2026-05-10 full run and passes in isolation.
- Visual snapshot regressions need an intentional re-baseline. Don't blanket-`--update-snapshots`.
- Chromium is the only configured project (`playwright.config.ts`).

## See also
- `.claude/rules/testing.md` — spec inventory + baselines
- `/run-e2e` skill (full or single spec) and `/verify-suite` skill (full gate)
- [docs/E2E_TESTING.md](../docs/E2E_TESTING.md)
