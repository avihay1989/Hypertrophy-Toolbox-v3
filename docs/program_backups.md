# Program Backup / Backup Center

Last updated: 2026-04-24

## Overview

The Backup Center lets the local user save, inspect, edit, restore, and delete workout-program snapshots. It is the primary UI for program-level recovery and lives at `/backup`.

## Primary UI

- `Backup` in the main navbar opens `/backup`.
- Workout Plan `Save Program` opens `/backup?intent=save`.
- Workout Plan `Backup Center` opens `/backup?intent=browse`.
- The page shows current-program count, saved snapshot count, manual count, and auto-recovery count.
- The library supports search, type filtering, and sorting.
- Restore and delete confirmations are inline in the detail pane.
- Backup names and notes can be edited inline.

## Storage

Backups live in two SQLite tables separate from the active program:

| Table | Purpose |
|-------|---------|
| `program_backups` | Backup metadata: `id`, `name`, `note`, `backup_type`, `schema_version`, `item_count`, `created_at` |
| `program_backup_items` | Snapshot rows for routine, exercise, sets, rep range, RIR, RPE, weight, order, and `superset_group` |

Backups survive normal erase/reset flows because they are not stored in `user_selection`.

## API

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/backup` | Render the Backup Center page |
| `GET` | `/api/backups` | List backup metadata |
| `POST` | `/api/backups` | Create a manual backup |
| `GET` | `/api/backups/<backup_id>` | Fetch backup details and items |
| `PATCH` | `/api/backups/<backup_id>` | Rename a backup or edit its note |
| `POST` | `/api/backups/<backup_id>/restore` | Restore a backup in replace mode |
| `DELETE` | `/api/backups/<backup_id>` | Delete a backup |

Name and note limits are shared by the UI and backend:

- `name`: required, 100 characters max
- `note`: optional, 500 characters max
- duplicate backup names are allowed

## Restore Rules

Restore is replace-only:

1. The selected backup is loaded.
2. The active `workout_log` and `user_selection` rows are cleared in one transaction.
3. Backup items are inserted into `user_selection`.
4. Items whose exercise no longer exists in the catalog are skipped and returned in the restore result.

The UI displays partial-restore details inline. If `restored_count == 0`, the result is treated as a warning rather than a clean success.

Before a restore, the UI can create a "Pre-restore snapshot" of the current plan so the user has a recovery point.

## Auto-Recovery Behavior

There are two backup mechanisms:

- **Program auto-backup support**: `utils/program_backup.py` can create `program_backups` rows with `backup_type='auto'` and prune them to the latest 10. The Backup Center displays these separately when they exist. The current `/erase-data` full-reset route does not call this utility because it drops and recreates the backup tables.
- **Startup database snapshots**: `utils/auto_backup.py` copies the live SQLite file to `data/auto_backup/database_<timestamp>.db` when the app starts and immediately before `/erase-data`. These are disaster-recovery files outside the Backup Center UI and rotate to the latest 7 files.

## Key Files

- `templates/backup.html`
- `static/js/modules/backup-center.js`
- `static/js/modules/program-backup.js`
- `routes/program_backup.py`
- `utils/program_backup.py`
- `utils/auto_backup.py`
- `tests/test_program_backup.py`
- `e2e/program-backup.spec.ts`
