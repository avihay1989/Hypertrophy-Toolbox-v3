# E2E Testing

Last updated: 2026-04-24

This document tracks the current Playwright setup and spec inventory. Treat counts as an inventory snapshot, not a promise that every suite was rerun during this docs refresh.

## How To Run

### Prerequisites

```bash
npm install
npx playwright install
pip install -r requirements.txt
```

### Commands

| Command | Description |
|---------|-------------|
| `npm run test:e2e` | Run the full Chromium suite through `scripts/run-playwright.ps1` |
| `npm run test:e2e:headed` | Run Playwright headed |
| `npm run test:e2e:ui` | Open the Playwright UI runner |
| `npm run test:e2e:debug` | Run with Playwright Inspector |
| `npx playwright test e2e/summary-pages.spec.ts --project=chromium` | Run one spec file directly |

## Current Runner Configuration

Validated from `package.json`, `playwright.config.ts`, and `scripts/run-playwright.ps1` on 2026-04-24:

- Test directory: `e2e/`
- Active browser project: `chromium`
- Base URL: `http://127.0.0.1:5000`
- Auto-start server: `app.py` via `.venv\Scripts\python.exe` when present, otherwise `python`
- Default worker count: `1` unless `PW_WORKERS` is set
- Reuse existing server: only when `PW_REUSE_SERVER=1` and not on CI
- HTML report output: `artifacts/playwright/report/`
- Test-results output: `artifacts/playwright/test-results/`
- Default retry policy: retries on CI only
- Default timeout: `30s`
- Default full-suite script: runs all non-visual specs first, then prepares a visual DB and runs `visual.spec.ts`

## Current Playwright Spec Inventory

There are currently **19** Playwright spec files in `e2e/`:

| Spec file | Primary coverage |
|-----------|------------------|
| `accessibility.spec.ts` | Keyboard nav, ARIA, focus behavior, touch targets |
| `api-integration.spec.ts` | Direct endpoint and response-shape checks |
| `browser-navigation-state.spec.ts` | Stateless routine-cascade behavior |
| `dark-mode.spec.ts` | Theme toggle and persistence |
| `empty-states.spec.ts` | Empty plan/log/export flows |
| `error-handling.spec.ts` | Server/network failure handling |
| `exercise-interactions.spec.ts` | Delete, replace, superset, inline interactions |
| `nav-dropdown.spec.ts` | Navbar dropdown and Backup Center route navigation |
| `program-backup.spec.ts` | Backup Center and program snapshot flows |
| `progression.spec.ts` | Progression page flows and goal interactions |
| `replace-exercise-errors.spec.ts` | Replace-exercise failure toasts |
| `smoke-navigation.spec.ts` | Core page loads and navigation smoke checks |
| `summary-pages.spec.ts` | Weekly/session summary rendering and controls |
| `superset-edge-cases.spec.ts` | Superset link/unlink/delete/replace edge cases |
| `validation-boundary.spec.ts` | Invalid form and boundary-value behavior |
| `visual.spec.ts` | Deterministic visual snapshots across routes, themes, and viewports |
| `volume-splitter.spec.ts` | Volume splitter inputs, modes, and results |
| `workout-log.spec.ts` | Workout log table, editing, filters, import/clear flows |
| `workout-plan.spec.ts` | Workout plan CRUD and routine-building flows |

## Supporting E2E Files

- `e2e/fixtures.ts` - shared selectors and helpers
- `e2e/strict-fixtures.ts` - stricter page-error gate for visual/redesign checks
- `e2e/visual-helpers.ts` - visual-test helpers
- `e2e/scripts/prepare_visual_db.py` - prepares the deterministic visual DB
- `e2e/fixtures/database.visual.seed.db` - committed visual-test seed database
- `e2e/puppeteer_mcp_summary_regression.py` - summary regression helper
- `e2e/run_puppeteer_summary_regression.ps1` - PowerShell runner for the Puppeteer/MCP summary regression path

## Coverage Notes

- The suite covers page-level browser flows, targeted regression paths, API smoke checks, Backup Center flows, navbar routing, and visual baselines.
- `api-integration.spec.ts` remains intentionally tolerant in some assertions while a few legacy response shapes are preserved.
- Visual snapshots live under `e2e/__screenshots__/visual.spec.ts-snapshots/`.

## Maintenance Rules

1. Update this document from the current `e2e/*.spec.ts` listing when adding or removing spec files.
2. Do not claim a full-suite pass here unless the full suite was rerun in the same environment.
3. Keep `scripts/run-playwright.ps1` and this document in sync when visual-suite orchestration changes.
