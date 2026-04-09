# Program Backup / Program Library

## Overview

The Program Backup feature allows users to save snapshots of their current workout program and restore them later. This enables users to:

1. **Experiment safely** with new programs and quickly restore previous ones without rebuilding from scratch
2. **Recover quickly** after using erase/reset operations, thanks to automatic backups

## User Stories

- As a user, I want to save my current workout program so I can experiment with a new one without losing my work
- As a user, I want to see a list of my saved programs with their creation dates and exercise counts
- As a user, I want to restore a saved program to make it my active workout plan
- As a user, I want to delete old backups I no longer need
- As a user, when I erase my data, I want an automatic backup created so I can recover if needed

## Storage Approach

### Database Tables

Backups are stored in two dedicated SQLite tables that are separate from the active program tables:

#### `program_backups` (Header/Metadata)
```sql
CREATE TABLE program_backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- User-provided name
    note TEXT,                             -- Optional description
    backup_type TEXT NOT NULL DEFAULT 'manual',  -- 'manual' or 'auto'
    schema_version INTEGER NOT NULL DEFAULT 1,   -- For future migrations
    item_count INTEGER NOT NULL DEFAULT 0,       -- Number of exercises
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, created_at)
)
```

#### `program_backup_items` (Exercise Data)
```sql
CREATE TABLE program_backup_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_id INTEGER NOT NULL,            -- FK to program_backups
    routine TEXT NOT NULL,                 -- e.g., "Workout A"
    exercise TEXT NOT NULL,                -- Exercise name
    sets INTEGER NOT NULL,
    min_rep_range INTEGER NOT NULL,
    max_rep_range INTEGER NOT NULL,
    rir INTEGER,                           -- Reps in Reserve
    rpe REAL,                              -- Rate of Perceived Exertion
    weight REAL NOT NULL,
    exercise_order INTEGER,                -- Optional ordering (may be NULL)
    FOREIGN KEY (backup_id) REFERENCES program_backups(id) ON DELETE CASCADE
)
```

### Design Decisions

- **Separate Tables**: Backups are stored in dedicated tables, completely isolated from the active program (`user_selection`). This ensures backups survive erase/reset operations.
- **Schema Versioning**: The `schema_version` field enables future migrations if the backup format needs to change.
- **Optional Fields**: Fields like `exercise_order`, `rir`, and `rpe` are nullable to handle cases where the source data doesn't have these values.
- **Cascading Deletes**: Deleting a backup header automatically deletes its items via `ON DELETE CASCADE`.

## API Endpoints

### List Backups
```
GET /api/backups
```

**Response:**
```json
{
    "ok": true,
    "status": "success",
    "data": [
        {
            "id": 1,
            "name": "My PPL Program",
            "note": "Before trying 5x5",
            "backup_type": "manual",
            "schema_version": 1,
            "item_count": 12,
            "created_at": "2026-02-03T10:30:00"
        }
    ]
}
```

### Create Backup
```
POST /api/backups
Content-Type: application/json

{
    "name": "My PPL Program",
    "note": "Optional description"
}
```

**Response:**
```json
{
    "ok": true,
    "status": "success",
    "message": "Backup 'My PPL Program' created successfully with 12 exercises",
    "data": {
        "id": 1,
        "name": "My PPL Program",
        "note": "Optional description",
        "backup_type": "manual",
        "schema_version": 1,
        "item_count": 12,
        "created_at": "2026-02-03T10:30:00"
    }
}
```

### Get Backup Details
```
GET /api/backups/<backup_id>
```

**Response:**
```json
{
    "ok": true,
    "status": "success",
    "data": {
        "id": 1,
        "name": "My PPL Program",
        "note": "Optional description",
        "backup_type": "manual",
        "schema_version": 1,
        "item_count": 12,
        "created_at": "2026-02-03T10:30:00",
        "items": [
            {
                "routine": "Workout A",
                "exercise": "Bench Press",
                "sets": 3,
                "min_rep_range": 6,
                "max_rep_range": 8,
                "rir": 3,
                "rpe": 7.0,
                "weight": 80.0,
                "exercise_order": 1
            }
        ]
    }
}
```

### Restore Backup
```
POST /api/backups/<backup_id>/restore
```

**Response:**
```json
{
    "ok": true,
    "status": "success",
    "message": "Restored 12 exercises from 'My PPL Program'",
    "data": {
        "backup_id": 1,
        "backup_name": "My PPL Program",
        "restored_count": 12,
        "skipped": []
    }
}
```

**Response with skipped exercises:**
```json
{
    "ok": true,
    "status": "success",
    "message": "Restored 10 exercises from 'My PPL Program' (2 skipped due to missing exercises)",
    "data": {
        "backup_id": 1,
        "backup_name": "My PPL Program",
        "restored_count": 10,
        "skipped": ["Deleted Exercise", "Renamed Exercise"]
    }
}
```

### Delete Backup
```
DELETE /api/backups/<backup_id>
```

**Response:**
```json
{
    "ok": true,
    "status": "success",
    "message": "Backup deleted successfully"
}
```

## Restore Rules

### Replace Mode (Default)
When restoring a backup, the system:
1. Clears all current entries in `user_selection` and `workout_log`
2. Inserts all backed-up items that have valid exercises in the catalog

### Missing Exercise Handling
If an exercise in the backup no longer exists in the exercises catalog:
- The item is **skipped** (not inserted)
- The skipped exercise name is added to the `skipped` list in the response
- The restore continues with remaining valid items
- **No FK constraint errors** occur

### Optional Columns
- `exercise_order`: Used if present in both backup and target schema, ignored otherwise
- `rir`, `rpe`: Stored as NULL if not present in source data

### Versioning
The `schema_version` field (currently `1`) allows future migrations:
- Version 1: Current format
- Future versions may add fields; restore logic handles missing fields gracefully

## Erase/Reset Integration

### Auto-Backup Behavior
When the `/erase-data` endpoint is called:

1. **Before erasing**: If the active program has data (`user_selection` is not empty):
   - An automatic backup is created with name: `"Pre-Erase Auto-Backup (YYYY-MM-DD HH:MM:SS)"`
   - Backup type is set to `"auto"`

2. **During erase**: Program tables are dropped and reinitialized:
   - `user_selection`
   - `workout_log`
   - `progression_goals`
   - `muscle_volumes`
   - `volume_plans`

3. **Backup tables are NOT affected**:
   - `program_backups`
   - `program_backup_items`

4. **Response includes auto-backup info** (if created):
```json
{
    "ok": true,
    "status": "success",
    "message": "All data has been erased... Auto-backup 'Pre-Erase Auto-Backup (2026-02-03 10:30:00)' created with 12 exercises.",
    "data": {
        "id": 5,
        "name": "Pre-Erase Auto-Backup (2026-02-03 10:30:00)",
        "item_count": 12
    }
}
```

### UI Auto-Backup Banner
After an erase operation, if an auto-backup was created, the UI shows a dismissible banner:
- Displays backup name and exercise count
- "Restore Now" button to immediately restore the backup
- Banner can be dismissed if user doesn't want to restore

## Verification

### Automated Coverage Status

Primary automated coverage lives in `tests/test_program_backup.py`.

That suite covers:

1. Create backup flows and stored metadata
2. Restore-in-replace-mode behavior
3. Missing-exercise skip handling during restore
4. Backup deletion and cascade cleanup
5. Erase/reset integration and auto-backup behavior

This document keeps the automated status separate from manual QA. The checklist below is intentionally left as manual verification work until a human run confirms those scenarios.

### Running Automated Tests
```bash
# Run all backup tests
pytest tests/test_program_backup.py -v

# Run specific test class
pytest tests/test_program_backup.py::TestProgramBackup -v

# Run with coverage
pytest tests/test_program_backup.py --cov=utils.program_backup --cov=routes.program_backup -v
```

## Manual Verification Checklist

Status note: unchecked items below are not auto-promoted to done by test coverage alone.

### Basic Operations
- [ ] Create a backup with name and optional note
- [ ] List backups shows all saved programs
- [ ] View backup details shows exercise count
- [ ] Restore backup replaces current program
- [ ] Delete backup removes it from list

### Edge Cases
- [ ] Creating backup with empty program works (0 items)
- [ ] Restoring with missing exercises shows skipped list
- [ ] Backup name is required (validation error if empty)
- [ ] Duplicate backup names allowed (different timestamps)

### Erase Integration
- [ ] Erase with non-empty program creates auto-backup
- [ ] Erase with empty program doesn't create backup
- [ ] Auto-backup appears in program library with "auto" type
- [ ] Backups survive after erase operation
- [ ] "Restore Now" banner appears after erase (if auto-backup created)

### UI/UX
- [ ] "Save Program" button opens save modal
- [ ] "Program Library" button opens library modal
- [ ] Restore confirmation dialog works
- [ ] Delete confirmation dialog works
- [ ] Toast notifications show success/error messages
- [ ] After restore, workout plan table refreshes

## Files Added/Modified

### New Files
- `utils/program_backup.py` - Core backup logic
- `routes/program_backup.py` - API endpoints
- `static/js/modules/program-backup.js` - Frontend JS module
- `tests/test_program_backup.py` - Test suite
- `docs/program_backups.md` - This documentation

### Modified Files
- `app.py` - Register blueprint, initialize tables, integrate auto-backup with erase
- `static/js/app.js` - Import and initialize program backup module
- `templates/workout_plan.html` - Add buttons and modals
- `tests/conftest.py` - Register blueprint and initialize tables for tests
