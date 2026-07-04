---
paths:
  - "tests/**"
  - "e2e/**"
  - "tests/conftest.py"
  - "playwright.config.ts"
---

# Testing guide

## Baselines (re-verify after significant changes)
- **pytest**: 1613 passed on integrated `main` @ `c0d5c38` (2026-07-05) — `.venv/Scripts/python.exe -m pytest tests/ -q`
- **Playwright inventory**: 501 tests across 30 specs — `npx playwright test --list --project=chromium`
- **Required functional CI set**: 404 tests, split **202 + 202** across two Chromium shards
- **Summary-page Playwright**: 20 tests — `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`

## Fixture hierarchy (`tests/conftest.py`)
```
test_db_path (function)         — unique `tmp_path` SQLite file per test
  app (function)                — Flask app + fresh schema at that DB, all 13 blueprints + erase-data route
    client (function)           — test client bound to the same isolated DB
    db_handler (function)       — DatabaseHandler at the same DB; verifies FK=ON
      clean_db (function)       — DELETEs all rows, preserves tables
        exercise_factory        — INSERTs into exercises
        workout_plan_factory    — INSERTs into user_selection (needs exercise)
        workout_log_factory     — INSERTs into workout_log (needs plan)
```

## DB patching pattern — critical
Tests swap DB by **assigning** `utils.config.DB_FILE` (never importing the value):
```python
import utils.config
utils.config.DB_FILE = test_db_path   # ← correct: modifies module attribute
```
`DatabaseHandler.__init__` reads `utils.config.DB_FILE` at call time (`database.py:209`). If you import `DB_FILE` as a bare name at module scope, the patch won't apply.

## Common pitfalls
| Problem | Cause | Fix |
|---|---|---|
| `no such table` in test | Test bypassed conftest init path | Use the shared `app` / `client` / `db_handler` fixtures or run the same init helpers |
| Route returns 404 in test | Blueprint not registered in the test app fixture | Register the needed blueprint in the local test app or use the shared conftest app fixture |
| FK constraint failed | Child row without parent | Use `exercise_factory` before `workout_plan_factory` |
| Test hits live DB | `utils.config.DB_FILE` not patched | Ensure fixture patches it; use `clean_db` fixture |
| `pytest` command not found | System Python, not venv | Use `.venv/Scripts/python.exe -m pytest` |

## E2E setup
```bash
npm install                  # one-time
npx playwright install       # one-time (downloads browsers)
```
Config: `playwright.config.ts` — auto-starts Flask via `.venv/Scripts/python.exe app.py` on port 5000. Chromium only. Serial execution (`fullyParallel: false`). `PW_REUSE_SERVER=1` reuses a running server.

Fixtures: `e2e/fixtures.ts` exports `test` (console-error collector), `ROUTES`, `API_ENDPOINTS`, `SELECTORS`, `waitForPageReady()`, `expectToast()`.

## E2E test map (Chromium, 501 total across 30 specs)

| Spec | Tests | User flow | Fixtures needed |
|---|---|---|---|
| `smoke-navigation.spec.ts` | 10 | Page loads, navbar links, full navigation cycle | None |
| `dark-mode.spec.ts` | 6 | Toggle dark mode, localStorage persistence | None |
| `nav-dropdown.spec.ts` | 7 | Desktop/mobile navbar behavior and actionability | None |
| `workout-plan.spec.ts` | 35 | Routine cascade, plan CRUD, filters, generator, controls, media | Exercises in DB |
| `workout-log.spec.ts` | 23 | Import/edit/delete/date/mobile/media flows | Plan + log entries |
| `summary-pages.spec.ts` | 20 | Weekly + session structure, Effective/Raw columns, contribution mode, pattern coverage | Exercises |
| `progression.spec.ts` | 26 | Page, selector, goals CRUD, methodology, status indicators | Exercises + log |
| `volume-splitter.spec.ts` | 27 | Sliders, modes, calculate/reset/export/history | None |
| `volume-progress.spec.ts` | 16 | Active-plan volume drawer behavior and geometry | Exercises in DB |
| `program-backup.spec.ts` | 20 | Backup Center CRUD, restore, confirmations, API | Plan data |
| `erase-flow.spec.ts` | 2 | Erase confirmation and auto-backup banner | None |
| `exercise-interactions.spec.ts` | 21 | Delete, replace, superset, inline edit, details | Exercises in plan |
| `accessibility.spec.ts` | 24 | Keyboard, ARIA, focus, skip links, contrast | None |
| `api-integration.spec.ts` | 58 | API contracts across core workflows | Varies |
| `empty-states.spec.ts` | 16 | Empty plan/log/filters/summaries | None |
| `error-handling.spec.ts` | 12 | Server 500/503, malformed JSON, double-click | None (mocked) |
| `superset-edge-cases.spec.ts` | 12 | Link >2/<2, delete, unlink, replace, persistence | 2+ exercises |
| `validation-boundary.spec.ts` | 23 | Negative, rep range, zero, RIR/RPE bounds, decimals | Exercise available |
| `browser-navigation-state.spec.ts` | 3 | Back button, refresh, deep-link | None |
| `replace-exercise-errors.spec.ts` | 3 | No alternative, all in routine, missing metadata | Specific setup |
| `body-composition.spec.ts` | 5 | Snapshot CRUD, BMI fallback, JS/Python parity | None |
| `fatigue.spec.ts` | 8 | Fatigue page, periods, empty/mobile/dark states | None |
| `fatigue-context.spec.ts` | 6 | Profile setting and advisory Workout Controls | Mocked estimate API |
| `fatigue-stage4-smokes.spec.ts` | 5 | Badge mobile geometry and dark contrast | None |
| `learned-calibration.spec.ts` | 8 | Calibration settings, actions, golden path | Profile + log data |
| `listener-cleanup.spec.ts` | 3 | Detached picker/dropdown listener cleanup | Exercises in plan |
| `ui-hardening.spec.ts` | 12 | Toast, form-state, modal keyboard/focus contracts | Varies |
| `user-profile.spec.ts` | 24 | Profile, lifts, settings, body map, insights | None |
| `visual.spec.ts` | 48 | Eight-page viewport/theme screenshot matrix | Visual seed |
| `visual-baseline-thumbnails.spec.ts` | 18 | Plan/log thumbnail screenshot matrix | Visual seed |

Support files:
- `e2e/fixtures.ts` — shared fixtures, route constants, selectors, helpers
- `e2e/puppeteer_mcp_summary_regression.py` — Python-based Puppeteer regression (not Playwright)
- `e2e/run_puppeteer_summary_regression.ps1` — PowerShell runner for above
- `e2e/scripts/seed_summary_regression_db.py` — DB seeder for regression testing

## Adding a new blueprint — don't forget the test app
New blueprints must be registered in BOTH `app.py` AND `tests/conftest.py` (in the `app` fixture). Missing step = 404s in tests.
