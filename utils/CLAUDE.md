# utils/ — Orientation

## Purpose
All business logic and DB access. Routes call into here; nothing in here imports from `routes/`. Each module owns one concern.

## Key files (by concern)
| Concern | Files |
|---|---|
| **DB / persistence** | `database.py` (DatabaseHandler), `db_initializer.py` (schema), `config.py` (env), `auto_backup.py`, `program_backup.py` |
| **Calculation engines** | `effective_sets.py`, `weekly_summary.py`, `session_summary.py`, `progression_plan.py`, `volume_classifier.py`, `volume_taxonomy.py`, `volume_progress.py`, `volume_export.py`, `volume_ai.py`, `fatigue.py`, `fatigue_data.py` |
| **Filters & catalogs** | `filter_predicates.py`, `filter_cache.py`, `normalization.py`, `constants.py`, `movement_patterns.py` |
| **Domain helpers** | `workout_log.py`, `user_selection.py`, `exercise_manager.py`, `plan_generator.py`, `profile_estimator.py` |
| **Infra** | `logger.py`, `errors.py`, `request_id.py`, `maintenance.py`, `export_utils.py` |

## Conventions
- DB access via `with DatabaseHandler() as db:` only (`database.py:200`). No `sqlite3.connect()` calls.
- Logger via `get_logger()` (`logger.py:121`). Never `print()` or a custom logger.
- Normalize before persisting: `normalize_muscle()`, `normalize_equipment()`, etc. from `normalization.py`.
- `utils/__init__.py` is **not** an authoritative facade for new code — import the concrete module (`from utils.db_initializer import ...`).

## Gotchas
- **Effective sets are informational only** (`effective_sets.py:6-7`). Never auto-adjust or block user actions on them.
- **FLASK_DEBUG default mismatch**: `app.py:259` defaults `'0'`, `database.py:90` defaults `'1'`. Result: `python app.py` runs Flask non-debug but DB uses DELETE-journal/FULL-sync (safe).
- `session_summary.py` imports `STATUS_MAP` from `weekly_summary.py` — not duplicates; per-session vs cross-routine weekly aggregation.

## See also
- `.claude/rules/database.md` — schema table, DatabaseHandler pattern, adding a table
- `.claude/rules/debugging.md` — logging / request-id / typical failures
- root [CLAUDE.md](../CLAUDE.md) §2–§3 (architecture, conventions) and §5 (risks)
