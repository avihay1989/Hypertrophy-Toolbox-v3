# E2E Testing

Last updated: 2026-04-08

This document tracks the current Playwright setup and the spec inventory that exists in the repo today. It is intentionally conservative: the inventory below is a file listing, not a claim that every suite was rerun clean in this environment during this docs refresh.

## How To Run

### Prerequisites

1. Install Node dependencies:
   ```bash
   npm install
   npx playwright install
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Commands

| Command | Description |
|---------|-------------|
| `npm run test:e2e` | Run the full Playwright suite headless |
| `npm run test:e2e:headed` | Run the suite with a visible browser |
| `npm run test:e2e:ui` | Open the Playwright UI runner |
| `npm run test:e2e:debug` | Run with Playwright Inspector |
| `npx playwright test e2e/summary-pages.spec.ts --project=chromium` | Run one spec file |

## Current Runner Configuration

Validated from `package.json` and `playwright.config.ts` on 2026-04-08:

- Test directory: `e2e/`
- Active browser project: `chromium`
- Base URL: `http://127.0.0.1:5000`
- HTML report output: `playwright-report/`
- Auto-start server: `app.py` via `.venv\Scripts\python.exe` when present, otherwise `python`
- Default retry policy: retries on CI only
- Default timeout: `30s`

## Current Playwright Spec Inventory

There are currently **17** Playwright spec files in `e2e/`:

| Spec file | Primary coverage |
|-----------|------------------|
| `accessibility.spec.ts` | Keyboard nav, ARIA, focus behavior, touch targets |
| `api-integration.spec.ts` | Direct endpoint and response-shape checks |
| `browser-navigation-state.spec.ts` | Stateless routine-cascade behavior |
| `dark-mode.spec.ts` | Theme toggle and persistence |
| `empty-states.spec.ts` | Empty plan/log/export flows |
| `error-handling.spec.ts` | Server/network failure handling |
| `exercise-interactions.spec.ts` | Delete, replace, superset, inline interactions |
| `program-backup.spec.ts` | Backup library flows |
| `progression.spec.ts` | Progression page flows and goal interactions |
| `replace-exercise-errors.spec.ts` | Replace-exercise failure toasts |
| `smoke-navigation.spec.ts` | Core page loads and navigation smoke checks |
| `summary-pages.spec.ts` | Weekly/session summary rendering and controls |
| `superset-edge-cases.spec.ts` | Superset link/unlink/delete/replace edge cases |
| `validation-boundary.spec.ts` | Invalid form and boundary-value behavior |
| `volume-splitter.spec.ts` | Volume splitter inputs, modes, and results |
| `workout-log.spec.ts` | Workout log table, editing, filters, import/clear flows |
| `workout-plan.spec.ts` | Workout plan CRUD and routine-building flows |

## Supporting E2E Files

These are also present and support the browser suite:

- `e2e/fixtures.ts` - shared selectors and helpers
- `e2e/scripts/` - helper scripts used by specific test flows
- `e2e/puppeteer_mcp_summary_regression.py` - summary regression helper
- `e2e/run_puppeteer_summary_regression.ps1` - PowerShell runner for the Puppeteer/MCP summary regression path

## Coverage Notes

- The suite covers page-level browser flows, targeted regression paths, and a broad API smoke layer.
- The dedicated error and state-regression specs added in February 2026 remain part of the live inventory.
- `api-integration.spec.ts` is intentionally tolerant in some assertions because route standardization is still incomplete across the app.

## Maintenance Rules

1. Treat spec counts as inventory, not as a permanent promise.
2. When adding or removing spec files, update this document from the current `e2e/*.spec.ts` listing.
3. Do not claim a full-suite pass here unless the full suite was rerun in the same environment.
