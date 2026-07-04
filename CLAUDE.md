# CLAUDE.md

Operational guidance for Claude Code. Keep this file under 200 lines. Subsystem-specific detail lives in `.claude/rules/*.md` and loads only when the matching files enter context. **For long-running work, read [`docs/MASTER_HANDOVER.md`](docs/MASTER_HANDOVER.md) first** (canonical current state); folder orientation lives in `<dir>/CLAUDE.md` files.

---

## 1. Product Intent

### What this is
A local-first Flask web app for designing, logging, and analyzing hypertrophy (muscle-building) resistance-training programs. Single user, no auth, runs on `localhost:5000`.

### Core workflows
1. **Plan** (`/workout_plan`) — build routines: choose exercises via filters, set reps/sets/weight/RIR. Or auto-generate via starter plan generator.
2. **Log** (`/workout_log`) — record actual performance (scored reps, weight, RIR) against plan.
3. **Analyze** (`/weekly_summary`, `/session_summary`) — volume per muscle with Effective Sets and Raw Sets shown side-by-side; direct/total contribution mode.
4. **Progress** (`/progression`) — double-progression suggestions (increase weight vs reps).
5. **Distribute** (`/volume_splitter`) — optimize weekly set allocation across muscles.
6. **Profile** (`/user_profile`) — save reference lifts and rep preferences for Workout Controls estimates.
7. **Backup** (via `/api/backups`) — snapshot/restore entire programs.

### Key terminology
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

### Refactor invariant
Any change to core workflow behavior (plan/log/analyze/progress/distribute/backup) requires migration notes in the PR description and updated test coverage. Do not silently alter calculation logic, DB schema, or API response shapes.

### Non-goals
- No user accounts or authentication — single-user local only.
- No cloud sync or remote database.
- Effective sets are **informational only** — never auto-adjust or block user actions (`utils/effective_sets.py:6-7`).

---

## 2. Architecture

### Startup sequence (`app.py`)
```
initialize_database()           ← utils/db_initializer.py — tables + normalization (no seed)
add_progression_goals_table()   ← utils/database.py
add_volume_tracking_tables()    ← utils/database.py
add_user_profile_tables()       ← utils/database.py
add_body_composition_snapshots_table() ← utils/database.py
add_strength_calibration_tables()      ← utils/database.py
add_fatigue_context_settings_table()   ← utils/database.py
initialize_exercise_order()     ← routes/workout_plan.py — ALTERs user_selection
init_backup_tables()            ← routes/program_backup.py → utils/program_backup.py
create_startup_backup()         ← utils/auto_backup.py — snapshots live DB to data/auto_backup/
```
Then registers 13 blueprints (`app.py:84-98`), plus one direct route: `POST /erase-data` (`app.py:158`).

### Module boundaries
```
app.py                 ← startup + middleware only; no business logic
  routes/*.py          ← HTTP: validate input → call utils → return response
    utils/*.py         ← all business logic + DB queries
      utils/database.py → DatabaseHandler → data/database.db (SQLite)
```

- Routes import from utils; utils never import from routes.
- Prefer concrete module imports such as `utils.db_initializer`; `utils/__init__.py` is no longer the authoritative facade for new code.
- All DB access via `DatabaseHandler` context manager (class at `utils/database.py:185`; `__enter__` / `__exit__` at `utils/database.py:414`).
- All JSON responses via `success_response()` / `error_response()` (`utils/errors.py:22,67`).
- All logging via `get_logger()` (`utils/logger.py:121`).

### Blueprints (`app.py:60-71`)
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
| `user_profile_bp` | `routes/user_profile.py` | `GET /user_profile`, `GET /api/user_profile/estimate` |
| `body_composition_bp` | `routes/body_composition.py` | `GET /body_composition`, `POST /api/body_composition/snapshots` |
| `volume_splitter_bp` | `routes/volume_splitter.py` | `GET /volume_splitter` |
| `program_backup_bp` | `routes/program_backup.py` | `GET/POST /api/backups`, `POST /api/backups/<id>/restore` |
| `fatigue_bp` | `routes/fatigue.py` | `GET /fatigue` |

### Deeper references
- Routes / API endpoints / filters / security → `.claude/rules/routes.md` (loads when editing `routes/**`).
- DB schema / DatabaseHandler / adding tables → `.claude/rules/database.md` (loads when editing `utils/database*.py` or `utils/db_initializer.py`).
- Templates / JS modules / SCSS → `.claude/rules/frontend.md` (loads when editing `templates/**`, `static/**`, `scss/**`).
- Pytest + Playwright + E2E map → `.claude/rules/testing.md` (loads when editing `tests/**` or `e2e/**`).
- Logging / request tracing / typical failures → `.claude/rules/debugging.md` (loads when editing `utils/logger.py` or `utils/request_id.py`).

---

## 3. Conventions

### Logger pattern (every module)
```python
from utils.logger import get_logger
logger = get_logger()
```
Returns the `'hypertrophy_toolbox'` named logger (`utils/logger.py:37`). Logs to `logs/app.log` (rotating 10MB × 5) and console (INFO+).

### DatabaseHandler pattern
```python
from utils.database import DatabaseHandler
with DatabaseHandler() as db:
    rows = db.fetch_all("SELECT ... WHERE col = ?", (value,))
    row  = db.fetch_one("SELECT ... WHERE id = ?", (id,))
    db.execute_query("INSERT INTO t (c) VALUES (?)", (val,))
```

### Constants and normalization
`utils/constants.py` has canonical enums. Always normalize before persisting: `normalize_muscle()`, `normalize_equipment()`, etc. from `utils/normalization.py`.

### Env vars (`utils/config.py`)
| Variable | Default | Effect |
|---|---|---|
| `DB_FILE` | `data/database.db` | SQLite path. Tests patch `utils.config.DB_FILE` directly. |
| `FLASK_DEBUG` | `'0'` in `app.py:259`; `'1'` in `database.py:90` | Controls Flask debug AND journal mode |
| `FLASK_USE_RELOADER` | `'0'` | Auto-reload (off by default — avoids WAL corruption) |
| `TESTING` | unset | Set to `'1'` by `tests/conftest.py` |
| `MAX_EXPORT_ROWS` | `1000000` | Export cap |

### Run commands
```bash
# Dev server
.venv/Scripts/python.exe app.py

# Tests — use the /run-tests skill, or:
.venv/Scripts/python.exe -m pytest tests/ -q

# E2E — use the /run-e2e skill, or:
npx playwright test --project=chromium --reporter=line

# Full gate — use the /verify-suite skill
# CSS — use the /build-css skill, or: npm run build:css
```

---

## 4. Cross-cutting Playbooks

### A. Add a new feature
- [ ] Create `utils/myfeature.py` with business logic.
- [ ] Add `from utils.logger import get_logger` + `logger = get_logger()` at module top.
- [ ] Create `routes/myfeature.py` with blueprint (routes rule has the template).
- [ ] Register the blueprint in `app.py` AND `tests/conftest.py` (both — missing either is a 404 in tests).
- [ ] If a new table is needed, follow the database rule.
- [ ] Create `templates/myfeature.html` extending `{% extends "base.html" %}`.
- [ ] Create `static/js/modules/myfeature.js`; use `apiFetch` or `api` from `fetch-wrapper.js`.
- [ ] Add nav link in `templates/base.html` navbar.
- [ ] Write tests in `tests/test_myfeature.py`.

### B. Refactor safely
1. **Before**: run full test suite, record baseline.
   ```bash
   .venv/Scripts/python.exe -m pytest tests/ -q > baseline.txt 2>&1
   ```
2. **Scope**: Grep for function/class name across `routes/`, `utils/`, `templates/`, `tests/`.
3. **Change**: one module at a time, keeping old interface as a thin wrapper if callers span multiple files.
4. **Verify**: re-run affected test file(s) after each file.
5. **Gate**: full pytest + relevant E2E specs must pass before done. Use the `/verify-suite` skill.
6. **Rollback**: if tests fail and the fix isn't obvious, `git stash push` or `git stash push -- <file>` immediately.

---

## 5. Current State & Risks

### Verified test counts (2026-07-05 — Plan v3 Phase -1 entry on `main`)
- **Integrated `main` @ `c0d5c38`**: isolated-worktree pytest **1613 passed**;
  latest merged PR CI functional shards **202 + 202 passed**; dedicated fatigue-context
  **6 passed** and erase-flow **2 passed**; full inventory **501 tests / 30 specs**.
- Track A shipped in PRs #91–#98. Track B has shipped WPB.1 (#103), WPB.5 (#101),
  WPB.7 (#102), WPB.8 (#104), and WPB.9 step 1 (#100); WPB.2–WPB.4, WPB.6, and
  WPB.9 promotion remain pending/prerequisite-gated.

Historical baselines live in `docs/MASTER_HANDOVER.md`. Re-verify after significant changes.

### Known response-contract exceptions (2026-05-21)
None. The pattern-coverage and replace-exercise fallback paths were migrated to `success_response()` / `error_response()` (2026-05-21). The replace-exercise "no result" cases (`NO_CANDIDATES`, `DUPLICATE`, `SELECTION_FAILED`) keep HTTP 200 by passing `status_code=200` to `error_response()` — they're user-facing "couldn't be processed" outcomes that pytest + the JS swap handler treat as 200 + `ok:false`.

### exercise_order column
Added at startup by `initialize_exercise_order()` (`routes/workout_plan.py:634`) via `ALTER TABLE`. `get_workout_plan` (line 247) defensively checks `column_exists()` for pre-migration DBs.

### session_summary vs weekly_summary — not duplicates
- `utils/session_summary.py:21` — `calculate_session_summary(routine, time_window, ...)`: groups by routine, optional date filter, per-session averages from `workout_log` join.
- `utils/weekly_summary.py:35` — `calculate_weekly_summary(method, ...)`: aggregates across all routines weekly, no date filter, tracks frequency.

`session_summary.py` imports only `EFFECTIVE_STATUS_MAP` from `weekly_summary.py`
(`utils/session_summary.py:9`); the calculations remain independent.

### Historical audit trail
Full file-by-file audit log and violation details: `docs/CLAUDE_MD_AUDIT.md`. Resolved items list (Cleanup Waves 1 and 2, `utils/database_indexes.py` retirement 2026-04-18, `volume_export.py` DatabaseHandler migration) lives there.
