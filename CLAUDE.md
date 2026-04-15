# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. Product Intent

### What This Is
A local-first Flask web app for designing, logging, and analyzing hypertrophy (muscle-building) resistance-training programs. Single user, no auth, runs on `localhost:5000`.

### Core Workflows
1. **Plan** (`/workout_plan`) — Build routines: choose exercises via filters, set reps/sets/weight/RIR. Or auto-generate via starter plan generator.
2. **Log** (`/workout_log`) — Record actual performance (scored reps, weight, RIR) against plan.
3. **Analyze** (`/weekly_summary`, `/session_summary`) — Volume per muscle with Effective Sets and Raw Sets shown side-by-side, plus direct/total contribution mode.
4. **Progress** (`/progression`) — Double-progression suggestions (increase weight vs reps).
5. **Distribute** (`/volume_splitter`) — Optimize weekly set allocation across muscles.
6. **Backup** (via `/api/backups`) — Snapshot/restore entire programs.

### Key Terminology
| Term | Meaning |
|---|---|
| RIR | Reps In Reserve — how many reps short of failure |
| RPE | Rate of Perceived Exertion — 1–10 effort scale |
| Effective sets | Raw sets × effort factor × rep-range factor × muscle contribution weight (`utils/effective_sets.py:44-68`) |
| CountingMode | `RAW` or `EFFECTIVE` — which set number to display (`utils/effective_sets.py:20-23`) |
| ContributionMode | `DIRECT_ONLY` (primary only) or `TOTAL` (weighted secondary/tertiary) (`utils/effective_sets.py:26-29`) |
| Routine | Named exercise group, e.g. `"GYM - Full Body - Workout A"` |
| Movement pattern | Biomechanical classification: squat, hinge, horizontal_push, etc. (`utils/movement_patterns.py`) |
| Superset | Two exercises linked for back-to-back performance — stored in `user_selection.superset_group` |

### Refactor Invariant
Any change to core workflow behavior (plan/log/analyze/progress/distribute/backup) requires migration notes in the PR description and updated test coverage. Do not silently alter calculation logic, DB schema, or API response shapes.

### Non-Goals
- No user accounts or authentication — single-user local only
- No cloud sync or remote database
- Effective sets are **informational only** — never auto-adjust or block user actions (`utils/effective_sets.py:6-7`)

---

## 2. Architecture

### Startup Sequence (`app.py`)
```
app.py lines 46-57:
  initialize_database()           ← utils/db_initializer.py — tables, seed, normalization
  add_progression_goals_table()   ← utils/database.py:476
  add_volume_tracking_tables()    ← utils/database.py:482
  initialize_exercise_order()     ← routes/workout_plan.py:614 — ALTERs user_selection
  init_backup_tables()            ← routes/program_backup.py → utils/program_backup.py:23
```
Then registers 10 blueprints (`app.py:60-71`).

### Module Boundaries
```
app.py                 ← startup + middleware only; no business logic
  routes/*.py          ← HTTP: validate input → call utils → return response
    utils/*.py         ← all business logic + DB queries
      utils/database.py → DatabaseHandler → data/database.db (SQLite)
```

**Target Standards:**
- Routes import from utils; utils never import from routes — **clean, no violations**
- Prefer concrete module imports such as `utils.db_initializer`; `utils/__init__.py` is no longer the authoritative facade for new code
- All DB access via `DatabaseHandler` context manager (`utils/database.py:200`)
- All JSON responses via `success_response()` / `error_response()` (`utils/errors.py:22,67`)
- All logging via `get_logger()` (`utils/logger.py:121`)

**Current Exceptions** (verified 2026-04-11):
| Rule | Violating File(s) | Detail |
|---|---|---|
| DatabaseHandler | `utils/database_indexes.py:60,65` | `optimize_database()` intentionally uses raw maintenance commands with explicit `_DB_LOCK` handling |
| success/error_response | `routes/weekly_summary.py:133,139` | Pattern coverage endpoint still returns legacy `success`/`error` JSON |
| success/error_response | `routes/workout_plan.py:1079,1093,1114,1125` | Replace-exercise fallback paths return legacy ad-hoc JSON with 200 error payloads |

### Blueprints Registered (`app.py:60-71`)
| Blueprint | File | Key routes |
|---|---|---|
| `main_bp` | `routes/main.py` | `GET /` |
| `workout_log_bp` | `routes/workout_log.py` | `GET /workout_log`, `POST /update_workout_log` |
| `weekly_summary_bp` | `routes/weekly_summary.py` | `GET /weekly_summary`, `GET /api/pattern_coverage` |
| `session_summary_bp` | `routes/session_summary.py` | `GET /session_summary` |
| `exports_bp` | `routes/exports.py` | `POST /export_workout_plan` |
| `filters_bp` | `routes/filters.py` | `POST /api/exercises`, `GET /api/available_filters` |
| `workout_plan_bp` | `routes/workout_plan.py` | `GET /workout_plan`, `POST /add_exercise`, `POST /generate_starter_plan` |
| `progression_plan_bp` | `routes/progression_plan.py` | `GET /progression` |
| `volume_splitter_bp` | `routes/volume_splitter.py` | `GET /volume_splitter` |
| `program_backup_bp` | `routes/program_backup.py` | `GET/POST /api/backups`, `POST /api/backups/<id>/restore` |

Additional route defined directly in `app.py:125`: `POST /erase-data` (drops and reinits all tables).

### Response Contract (`utils/errors.py`)
```python
# Success (line 33):  {"ok": True, "status": "success", "data": ..., "message": ..., "requestId": ...}
# Error (line 91):    {"ok": False, "status": "error", "message": ..., "error": {"code": ..., "message": ..., "requestId": ...}}
```
XHR detection (`utils/errors.py:47-64`): checks `X-Requested-With`, `Accept: application/json`, or `/api/` prefix.

### Database Schema (from `utils/db_initializer.py`)
| Table | PK | Key FK | Created in |
|---|---|---|---|
| `exercises` | `exercise_name TEXT` | — | `db_initializer.py:34` |
| `exercise_isolated_muscles` | `(exercise_name, muscle)` | → `exercises` CASCADE | `db_initializer.py:90` |
| `user_selection` | `id INTEGER` | `exercise` → `exercises` CASCADE | `db_initializer.py:166` |
| `workout_log` | `id INTEGER` | `workout_plan_id` → `user_selection` CASCADE | `db_initializer.py:237` |
| `progression_goals` | `id INTEGER` | — | `database.py:460` |
| `volume_plans` | `id INTEGER` | — | `database.py:484` |
| `muscle_volumes` | `id INTEGER` | `plan_id` → `volume_plans` CASCADE | `database.py:491` |
| `program_backups` | `id INTEGER` | — | `utils/program_backup.py:23` |
| `program_backup_items` | `id INTEGER` | `backup_id` → `program_backups` CASCADE | `utils/program_backup.py:23` |

### Seed Database
`data/backup/database.db` is the canonical exercise library. On first init, if `exercises` has < 100 rows (`MIN_EXERCISE_ROWS`, `db_initializer.py:17`), the seed is ATTACHed and copied (`db_initializer.py:331-395`). Skipped when `TESTING=1` env var is set (`db_initializer.py:333`).

### DB Connection Config (`utils/database.py:80-104`)
`_configure_connection()` sets PRAGMAs per connection:
- `foreign_keys = ON` (line 84)
- `busy_timeout = 30000` (line 86)
- Journal mode: `FLASK_DEBUG` env defaults to `'1'` → `DELETE` mode; set `FLASK_DEBUG=0` for `WAL` (line 90)
- Synchronous: debug → `FULL`; non-debug → `NORMAL` (lines 99-102)

**Note:** `database.py:90` defaults `FLASK_DEBUG` to `'1'`, but `app.py:259` defaults it to `'0'`. Result: `python app.py` runs Flask in non-debug mode, but DB uses DELETE journal + FULL sync (safe defaults).

### Thread Safety
DatabaseHandler writes are locked via `_DB_LOCK` (`threading.RLock`, `database.py:24`) — see `execute_query` (line 236) and `executemany` (line 311). Known exceptions exist (see Current Exceptions above).

---

## 3. Playbooks

### A. Add a New Feature
- [ ] Create `utils/myfeature.py` with business logic
- [ ] Add `from utils.logger import get_logger` + `logger = get_logger()` at module top
- [ ] Create `routes/myfeature.py` with blueprint (see Playbook C)
- [ ] Register blueprint in `app.py` AND `tests/conftest.py` (see Playbook C)
- [ ] If new table needed, follow Playbook D
- [ ] Create `templates/myfeature.html` extending `{% extends "base.html" %}`
- [ ] Create `static/js/modules/myfeature.js` — use `apiCall` from `fetch-wrapper.js`
- [ ] Add nav link in `templates/base.html` navbar
- [ ] Write tests in `tests/test_myfeature.py`

### B. Add an API Endpoint
```python
# In routes/myfeature.py
from flask import Blueprint, request
from utils.errors import success_response, error_response
from utils.logger import get_logger

myfeature_bp = Blueprint('myfeature', __name__)
logger = get_logger()

@myfeature_bp.route('/api/myfeature', methods=['POST'])
def my_endpoint():
    try:
        data = request.get_json() or {}
        field = data.get('field')
        if not field:
            return error_response("VALIDATION_ERROR", "field is required", 400)
        result = do_something(field)
        return success_response(data=result, message="Done")
    except Exception as e:
        logger.exception("Error in my_endpoint")
        return error_response("INTERNAL_ERROR", "Unexpected error", 500)
```

### C. Add a Blueprint
1. Create `routes/newbp.py` with `newbp_bp = Blueprint('newbp', __name__)`
2. In `app.py`: `from routes.newbp import newbp_bp` + `app.register_blueprint(newbp_bp)`
3. In `tests/conftest.py`: same import + `app.register_blueprint(newbp_bp)` in the `app` fixture (line ~59-69)

Missing step 3 = 404s in tests.

### D. Add a DB Table
1. Write creation function in `utils/database.py`:
```python
def add_myfeature_table() -> None:
    with DatabaseHandler() as db:
        db.execute_query("""CREATE TABLE IF NOT EXISTS myfeature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ...
        )""")
```
2. Call in `app.py` startup block (after line 52, alongside other `add_*` calls)
3. Call in `tests/conftest.py` → `app` fixture `with app.app_context():` block (line 107-112)
4. Call in `tests/conftest.py` → `erase_data()` inner function (line 92-97)
5. If FK to existing table: add child table name to drop-order list in `erase_data` and `clean_db` fixture

### E. Modify Filters Safely
Two injection-prevention layers:
1. **Column whitelist** — `ALLOWED_COLUMNS` dict in `routes/filters.py:115-139`. Call `validate_column_name()` (line 147) before any dynamic column name.
2. **Parameterized values** — `FilterPredicates.build_filter_query()` in `utils/filter_predicates.py:45` uses `?` params. `PARTIAL_MATCH_FIELDS` (line 34) use `LIKE ?` with `%value%`; others use exact match.

To add a filterable column:
- [ ] Add to `ALLOWED_COLUMNS` in `routes/filters.py`
- [ ] Add to `FilterPredicates.VALID_FILTER_FIELDS` in `utils/filter_predicates.py:17`
- [ ] If partial match: add to `PARTIAL_MATCH_FIELDS` (line 34)
- [ ] If muscle-type: add mapping in `SIMPLE_TO_DB_MUSCLE` / `SIMPLE_TO_ADVANCED_ISOLATED` (`routes/filters.py:17-69`)

### F. Add a JS Module + CSS
- Create `static/js/modules/myfeature.js` as ES6 module
- Import in template: `<script type="module" src="{{ url_for('static', filename='js/modules/myfeature.js') }}"></script>`
- Use `import { apiCall } from './fetch-wrapper.js'` for API calls
- Use `import { showToast } from './toast.js'` for notifications
- Add CSS file in `static/css/styles_myfeature.css`; link in `templates/base.html` `<head>`
- For SCSS changes: edit `scss/custom-bootstrap.scss`, run `npm run build:css`

### G. Refactor Safely
1. **Before touching code**: run full test suite, record baseline counts
   ```bash
   .venv/Scripts/python.exe -m pytest tests/ -q > baseline.txt 2>&1
   ```
2. **Scope the change**: identify all callers (`Grep` for function/class name across `routes/`, `utils/`, `templates/`, `tests/`)
3. **Make the change**: one module at a time, keeping old interface as a thin wrapper if callers span multiple files
4. **Verify after each file**: re-run affected test file(s)
5. **Full suite gate**: all pytest + relevant E2E specs must pass before considering it done
6. **Rollback**: if tests fail and the fix isn't obvious, `git stash push` or `git stash push -- <file>` immediately

---

## 4. Conventions

### Logger Pattern (every module)
```python
from utils.logger import get_logger
logger = get_logger()
```
Returns the `'hypertrophy_toolbox'` named logger (`utils/logger.py:37`). Logs to `logs/app.log` (rotating 10MB × 5, `logger.py:48-53`) and console (INFO+, `logger.py:61`).

**Known deviations:** none for `print()`-based logging in the current production code paths. The logging cleanup was completed earlier and the removed legacy modules from Cleanup Wave 1 no longer contribute stale exceptions here.

### DatabaseHandler Pattern
```python
from utils.database import DatabaseHandler
with DatabaseHandler() as db:
    rows = db.fetch_all("SELECT ... WHERE col = ?", (value,))    # list[dict]
    row = db.fetch_one("SELECT ... WHERE id = ?", (id,))         # dict | None
    db.execute_query("INSERT INTO t (c) VALUES (?)", (val,))     # write (locks)
```
Slow queries (>100ms) auto-logged as WARNING (`database.py:250`).

### Constants and Normalization
`utils/constants.py` has canonical enums: `FORCE`, `MECHANIC`, `UTILITY`, `DIFFICULTY`, `MUSCLE_GROUPS`, `EQUIPMENT_SYNONYMS`, `MUSCLE_ALIAS`.

Always normalize before persisting: `normalize_muscle()`, `normalize_equipment()`, etc. from `utils/normalization.py`.

### Config / Env Vars (`utils/config.py`)
| Variable | Default | Effect |
|---|---|---|
| `DB_FILE` | `data/database.db` | SQLite path. Tests patch `utils.config.DB_FILE` directly. |
| `FLASK_DEBUG` | `'0'` in `app.py:259`; `'1'` in `database.py:90` | Controls Flask debug AND journal mode |
| `FLASK_USE_RELOADER` | `'0'` | Auto-reload (off by default — avoids WAL corruption) |
| `TESTING` | unset | Set to `'1'` by `tests/conftest.py` for the shared pytest harness |
| `MAX_EXPORT_ROWS` | `1000000` | Export cap |

### Run Commands
```bash
# Dev server
.venv/Scripts/python.exe app.py                    # or: python app.py (if venv active)
FLASK_DEBUG=1 python app.py                         # debug mode
$env:FLASK_DEBUG='1'; python app.py                  # debug mode (PowerShell)

# Tests (930 pass, 1 skipped, ~114s)
.venv/Scripts/python.exe -m pytest tests/ -v
.venv/Scripts/python.exe -m pytest tests/test_effective_sets.py -q    # single file
.venv/Scripts/python.exe -m pytest tests/test_foo.py::test_bar -v    # single test

# E2E (315 pass, ~6.8m; auto-starts Flask via playwright.config.ts webServer)
npx playwright test                                  # full suite
npx playwright test e2e/smoke-navigation.spec.ts     # single spec
npx playwright test --headed                         # visible browser
npx playwright test --ui                             # interactive UI

# CSS build
npm run build:css       # one-off
npm run watch:css       # watch mode
```

---

## 5. Testing Guide

### Fixture Hierarchy (`tests/conftest.py`)
```
test_db_path (function)         — unique `tmp_path` SQLite file per test
  app (function)                — Flask app + fresh schema at that DB, all 10 blueprints + erase-data route
    client (function)           — test client bound to the same isolated DB
    db_handler (function)       — DatabaseHandler at the same DB; verifies FK=ON
      clean_db (function)       — DELETEs all rows, preserves tables
        exercise_factory        — INSERTs into exercises
        workout_plan_factory    — INSERTs into user_selection (needs exercise)
        workout_log_factory     — INSERTs into workout_log (needs plan)
```

### DB Patching Pattern — Critical
Tests swap DB by assigning `utils.config.DB_FILE` (not importing the value):
```python
import utils.config
utils.config.DB_FILE = test_db_path   # ← correct: modifies module attribute
```
`DatabaseHandler.__init__` reads `utils.config.DB_FILE` at call time (`database.py:209`). If you import `DB_FILE` as a bare name at module scope, the patch won't apply.

### Common Pitfalls
| Problem | Cause | Fix |
|---|---|---|
| `no such table` in test | Test bypassed the conftest initialization path | Use the shared `app` / `client` / `db_handler` fixtures or run the same initialization helpers |
| Route returns 404 in test | Blueprint not registered in the test app fixture | Register the needed blueprint in the local test app or use the shared conftest app fixture |
| FK constraint failed | Child row without parent | Use `exercise_factory` before `workout_plan_factory` |
| Test hits live DB | `utils.config.DB_FILE` not patched | Ensure fixture patches it; use `clean_db` fixture |
| `pytest` command not found | System Python, not venv | Use `.venv/Scripts/python.exe -m pytest` |

### E2E Setup
```bash
npm install                  # one-time
npx playwright install       # one-time (downloads browsers)
```
Config: `playwright.config.ts` — auto-starts Flask via `.venv/Scripts/python.exe app.py` on port 5000 (lines 5-8, 62-67). Chromium only. Serial execution (`fullyParallel: false`). `PW_REUSE_SERVER=1` reuses running server.

E2E fixtures: `e2e/fixtures.ts` — exports `test` (with console error collector), `ROUTES`, `API_ENDPOINTS`, `SELECTORS`, `waitForPageReady()`, `expectToast()`.

---

## 6. Security & Guardrails

### SQL Injection Prevention
- **Column whitelist**: `ALLOWED_COLUMNS` + `ALLOWED_TABLES` in `routes/filters.py:108-139`. `validate_column_name()` / `validate_table_name()` at lines 142-149.
- **Parameterized queries**: All `DatabaseHandler` methods use `?` placeholders.
- **DANGER**: `filter_cache.py:85` has `f"SELECT DISTINCT {column} FROM {table}"` — column/table are NOT parameterized here, but callers should pre-validate. `get_cached_unique_values()` is called with hardcoded column names only (line 103-109 `warm_cache`), but this is a latent risk if called with user input.

### Input Validation
Routes validate bounds before calling utils. Example pattern in `routes/workout_plan.py`: sets 1-20, reps 1-100, weight ≥ 0, RIR 0-10.

### Auth Boundaries
**No authentication exists.** Single-user local app. `POST /erase-data` (`app.py:125`) deletes everything with no confirmation. Do not expose to untrusted network.

**Recommendation:** Gate `/erase-data` behind an env var check (e.g. `ALLOW_ERASE=1`) or require a confirmation token in the request body to prevent accidental data loss.

### Filename Sanitization
`utils/export_utils.py` has `sanitize_filename()` to strip path traversal and dangerous characters from export filenames.

---

## 7. Debugging

### Request Tracing
1. Every request gets a UUID via `utils/request_id.py:19` → stored in `flask.g.request_id`
2. Returned in response header `X-Request-ID` (`request_id.py:44`) and JSON `requestId` field
3. Included in every log line via `RequestIdFilter` (`logger.py:10-20`)
4. Log format: `%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s [%(filename)s:%(lineno)d]`
5. Search logs:
   ```bash
   # bash / Git Bash
   grep "req_abc123" logs/app.log
   grep -i "ERROR" logs/app.log | tail -20

   # PowerShell
   Select-String "req_abc123" logs/app.log
   Select-String -Pattern "ERROR" logs/app.log | Select-Object -Last 20
   ```

### Slow Request Detection
- Queries >100ms: WARNING in `database.py:250`
- Requests >1000ms: WARNING in `logger.py:97`

### Typical Failures
| Symptom | Cause | Evidence |
|---|---|---|
| `database is locked` | Concurrent writes (e.g. reloader spawned 2 processes) | Check `_DB_LOCK` in `database.py:24`; disable reloader |
| Empty exercise list on fresh start | Seed DB missing at `data/backup/database.db` | `db_initializer.py:348` |
| `FK constraint failed` | Inserting log without valid `workout_plan_id` | `db_initializer.py:257` |
| 404 on new route in tests | Blueprint not in `conftest.py` | See Playbook C step 3 |
| Effective sets = raw sets | RIR/RPE null → neutral factor 1.0 | By design (`effective_sets.py:6-7`) |

---

## 8. Current State & Risks

### Verified Test Counts (last refreshed: 2026-04-15)
- **pytest**: 938 passed, 1 skipped (~118s) — command: `.venv/Scripts/python.exe -m pytest tests/ -q`
- **E2E Playwright**: 315 passed (~7.1m, Chromium project; last full-suite verification 2026-04-11) — command: `npx playwright test --project=chromium --reporter=line`
- **Summary-page Playwright**: 20 passed (~25s, Chromium project) — command: `npx playwright test e2e/summary-pages.spec.ts --project=chromium --reporter=line`

> Re-verify after significant changes: run both suites and update counts + date above.

### Filter Cache: TTL-Only Invalidation
`utils/filter_cache.py:13` — TTL of 3600s. `invalidate_cache()` (line 92) exists but is **never called from any route** — grep confirms only test and module-internal usage. Stale filter options may persist up to 1 hour after exercise data changes. This is a known gap, not a bug per se, but worth noting.

### Deprecated / Legacy Modules
No current deprecated / legacy modules are tracked here. Cleanup Waves 1 and 2 removed the confirmed dead legacy modules; `utils/volume_export.py` remains live and was migrated to `DatabaseHandler` in DOCS_AUDIT_PLAN Tier 3.

Cleanup Wave 1 removed `utils/helpers.py`, `utils/filters.py`, `utils/database_init.py`, and `utils/muscle_group.py` on 2026-04-10 after repo-wide reference audits and green suite validation. Cleanup Wave 2 retired `utils/business_logic.py`, `utils/data_handler.py`, `tests/test_business_logic.py`, `tests/test_data_handler.py`, and the package-level `get_workout_logs` compatibility export from `utils/__init__.py` on 2026-04-10 after a zero-caller audit and a green full-suite pytest run.

### exercise_order Column
Added at startup by `initialize_exercise_order()` (`routes/workout_plan.py:614`) via `ALTER TABLE`. Route handler `get_workout_plan` (line 231-234) defensively checks `column_exists()` before using it. In practice, the column always exists after init, but the defensive check is there for pre-migration databases.

### session_summary vs weekly_summary
These are **not duplicates** — they serve distinct purposes:
- `utils/session_summary.py:21` — `calculate_session_summary(routine, time_window, ...)`: groups by routine, optionally filters by date range, tracks per-session averages using `workout_log` join.
- `utils/weekly_summary.py:35` — `calculate_weekly_summary(method, ...)`: aggregates across all routines weekly, no date filtering, tracks frequency.

`session_summary.py` imports `STATUS_MAP`/`EFFECTIVE_STATUS_MAP` from `weekly_summary.py` (line 9), but calculations are independent.

---

## Appendix A: E2E Test Map (last verified: 2026-04-10)

All 17 Playwright spec files in `e2e/` (315 total tests from `npx playwright test --project=chromium --reporter=line`):

| Spec | Tests | User Flow | Key Routes | Fixtures Needed |
|---|---|---|---|---|
| `smoke-navigation.spec.ts` | 10 | Page loads, navbar links, full navigation cycle | `GET /`, all page routes | None (empty state) |
| `dark-mode.spec.ts` | 6 | Toggle dark mode, localStorage persistence, cross-page | `GET /`, `GET /workout_plan` | None |
| `workout-plan.spec.ts` | 17 | Routine cascade, add exercise, filters, export, plan generator | `GET /workout_plan`, `POST /add_exercise`, `/generate_starter_plan` | Needs exercises in DB |
| `workout-log.spec.ts` | 19 | Table structure, import from plan, edit scored fields, date filter, clear | `GET /workout_log`, `POST /update_workout_log` | Needs plan + log entries |
| `summary-pages.spec.ts` | 20 | Weekly + session summary structure, Effective/Raw columns, contribution mode selector, pattern coverage | `GET /weekly_summary`, `GET /session_summary`, `GET /api/pattern_coverage` | Needs exercises for pattern data |
| `progression.spec.ts` | 24 | Page structure, exercise selector, goals CRUD, methodology display, status indicators | `GET /progression` | Needs exercises + log data |
| `volume-splitter.spec.ts` | 26 | Page structure, slider controls, mode toggle, calculate, reset, export | `GET /volume_splitter` | None |
| `program-backup.spec.ts` | 18 | Modal open/close, create/list/restore/delete backups, API endpoints | `GET /workout_plan`, `GET/POST/DELETE /api/backups` | Needs plan data for backup |
| `exercise-interactions.spec.ts` | 21 | Delete, replace, superset link/unlink, inline edit, exercise details | `POST /remove_exercise`, `/replace_exercise`, `/api/superset/*` | Needs exercises in plan |
| `accessibility.spec.ts` | 24 | Keyboard nav, ARIA, focus management, skip links, color contrast | `GET /`, `GET /workout_plan` | None |
| `api-integration.spec.ts` | 56 | All API endpoints: plan CRUD, superset, generator, pattern coverage | All `POST/GET` API endpoints | Varies |
| `empty-states.spec.ts` | 16 | Empty plan export, empty log operations, empty filters, empty summaries | Various page routes | None (explicitly tests empty state) |
| `error-handling.spec.ts` | 12 | Server 500/503, malformed JSON, network failures, double-click prevention | `POST /add_exercise` (mocked errors) | None |
| `superset-edge-cases.spec.ts` | 12 | Link >2 or <2 exercises, delete in superset, unlink, replace in superset, persistence | `POST /api/superset/*` | Needs 2+ exercises in plan |
| `validation-boundary.spec.ts` | 23 | Negative values, rep range validation, zero values, RIR/RPE bounds, decimal handling, extreme values | `POST /add_exercise` | Needs exercise available |
| `browser-navigation-state.spec.ts` | 3 | Back button resets, page refresh resets, deep-link query ignored | `GET /workout_plan` | None |
| `replace-exercise-errors.spec.ts` | 3 | No alternative, all alternatives in routine, missing metadata | `POST /replace_exercise` | Specific exercise setup |

Support files:
- `e2e/fixtures.ts` — Shared test fixtures, route constants, selectors, helpers
- `e2e/puppeteer_mcp_summary_regression.py` — Python-based Puppeteer regression script (not Playwright)
- `e2e/run_puppeteer_summary_regression.ps1` — PowerShell runner for above
- `e2e/scripts/seed_summary_regression_db.py` — DB seeder for regression testing

Config: `playwright.config.ts` — Chromium only, serial, auto-starts Flask.

---

## Appendix B: Audit Provenance

Full file-by-file audit log and violation details moved to `docs/CLAUDE_MD_AUDIT.md` to keep this file focused on operational guidance. Last audit: 2026-03-01.

---

## Appendix C: Unknowns & Resolved

### Open

| Item | What's Unknown | How to Confirm |
|---|---|---|
| `create_performance_indexes()` not in startup | 14 indexes defined but never created in production — potential query performance gap | Decide whether to add call to `app.py` startup or keep as manual optimization |

### Resolved (2026-03-01)

| Item | Finding | Evidence |
|---|---|---|
| `utils/volume_export.py` bypasses `DatabaseHandler` | **Resolved in DOCS_AUDIT_PLAN Tier 3** | The live helper now uses `DatabaseHandler` with grouped `commit=False` inserts and context-manager commit/rollback semantics. Regression coverage verifies rollback on mid-write failure. |
| `filter_cache.py:85` SQL injection | **Latent risk only — no active user-input callers** | Only caller is `warm_cache()` (line 113) with hardcoded column/table names. No routes call `get_cached_unique_values()` directly. |
| `utils/business_logic.py` active callers | **Retired in Cleanup Wave 2** | Zero repo callers remained after the `routes/weekly_summary.py` dead import was removed, so the module and `tests/test_business_logic.py` were deleted on 2026-04-10. |
| `utils/data_handler.py` active callers | **Retired in Cleanup Wave 2** | Zero repo callers remained outside its dedicated test file, so the module and `tests/test_data_handler.py` were deleted on 2026-04-10. |
