# CLAUDE.md Audit - Live Architecture Debt

Last validated: 2026-05-23

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

None. Every live JSON route uses `success_response()` / `error_response()`. The previously-listed exceptions (`/api/pattern_coverage` and the replace-exercise fallback branches in `routes/workout_plan.py`) were migrated 2026-05-21 in `cbf745a` (`fix(api): migrate remaining response-contract exceptions`). The replace-exercise "no result" cases (`no_candidates`, `duplicate`, `selection_failed`) keep HTTP 200 by passing `status_code=200` to `error_response()` — they're user-facing "couldn't be processed" outcomes that pytest and the JS swap handler treat as 200 + `ok:false`.

## 3. No Longer Tracked Here

The following historical items were resolved and are no longer active debt:

- Spring-cleanup Phase 4/5 execution plans
- Seed DB regeneration and later `SEED_DB_PATH` retirement
- Legacy CSS consolidation and deletion after the Calm Glass redesign
- Backup Center hardening implementation plan and review handoffs
- `utils/database_indexes.py` retirement
- `utils/volume_export.py` DatabaseHandler migration
