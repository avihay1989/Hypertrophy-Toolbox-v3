# CLAUDE.md Audit - Live Architecture Debt

Last validated: 2026-04-24

This file tracks only unresolved, repo-verified architecture debt. Historical rollout plans and completed migration trackers were removed from the active docs surface during the April 24 docs cleanup.

## 1. Database Access Standardization

No unresolved route/business-helper bypasses of `DatabaseHandler` were found in the current `app.py`, `routes/`, or normal `utils/` workflow code.

Intentional low-level SQLite owners remain:

- `utils/database.py` owns `get_db_connection()` and the `DatabaseHandler` context manager.
- `utils/db_initializer.py` owns database/table creation.
- `utils/auto_backup.py` uses SQLite's online backup API to copy the live DB to `data/auto_backup/`.
- `utils/maintenance.py` imports `sqlite3` only for error handling while using `DatabaseHandler`.

`utils/user_selection.py`, `utils/volume_export.py`, and `routes/volume_splitter.py` now use `DatabaseHandler`.

## 2. Response Contract Exceptions

Most live JSON routes use `success_response()` / `error_response()`. The remaining intentional exceptions are:

- `routes/weekly_summary.py` `GET /api/pattern_coverage` still returns legacy top-level `success` / `error` JSON.
- `routes/workout_plan.py` replace-exercise fallback branches return 200 error payloads for UI-handled states such as `no_candidates`, `selection_failed`, and `duplicate`.

These are user-facing contracts and should only change with paired frontend updates and tests.

## 3. No Longer Tracked Here

The following historical items were resolved and are no longer active debt:

- Spring-cleanup Phase 4/5 execution plans
- Seed DB regeneration and later `SEED_DB_PATH` retirement
- Legacy CSS consolidation and deletion after the Calm Glass redesign
- Backup Center hardening implementation plan and review handoffs
- `utils/database_indexes.py` retirement
- `utils/volume_export.py` DatabaseHandler migration
