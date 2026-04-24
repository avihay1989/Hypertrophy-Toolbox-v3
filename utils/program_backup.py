"""
Program Backup / Program Library functionality.

Provides snapshot and restore capabilities for the active workout program.
Backups are stored persistently in the database and survive standard erase/reset operations.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()

# TODO: schema_version is written but not yet consumed. First consumer should
# read it in restore_backup to trigger field migration. Until then it is purely
# informational.
BACKUP_SCHEMA_VERSION = 1


def initialize_backup_tables(db: Optional[DatabaseHandler] = None) -> None:
    """Create the backup tables if they don't exist.
    
    Creates two tables:
    - program_backups: Header/metadata for each backup
    - program_backup_items: Individual items (user_selection rows) for each backup
    """
    should_close = False
    if db is None:
        db = DatabaseHandler()
        should_close = True
    
    try:
        # Create backup header table
        db.execute_query("""
            CREATE TABLE IF NOT EXISTS program_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                note TEXT,
                backup_type TEXT NOT NULL DEFAULT 'manual',
                schema_version INTEGER NOT NULL DEFAULT 1,
                item_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, created_at)
            )
        """)
        
        # Create backup items table with FK to header
        db.execute_query("""
            CREATE TABLE IF NOT EXISTS program_backup_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_id INTEGER NOT NULL,
                routine TEXT NOT NULL,
                exercise TEXT NOT NULL,
                sets INTEGER NOT NULL,
                min_rep_range INTEGER NOT NULL,
                max_rep_range INTEGER NOT NULL,
                rir INTEGER,
                rpe REAL,
                weight REAL NOT NULL,
                exercise_order INTEGER,
                superset_group TEXT DEFAULT NULL,
                FOREIGN KEY (backup_id) REFERENCES program_backups(id) ON DELETE CASCADE
            )
        """)
        
        # Add superset_group column if it doesn't exist (migration for existing backup tables)
        cols = db.fetch_all("PRAGMA table_info(program_backup_items)")
        col_names = {row['name'] for row in cols}
        if 'superset_group' not in col_names:
            db.execute_query("ALTER TABLE program_backup_items ADD COLUMN superset_group TEXT DEFAULT NULL")
            logger.debug("Added superset_group column to program_backup_items table")
        
        # Create indexes for efficient lookups
        db.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_backup_items_backup_id 
            ON program_backup_items(backup_id)
        """)
        
        db.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_backups_type 
            ON program_backups(backup_type)
        """)
        
        db.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_backups_created_at 
            ON program_backups(created_at DESC)
        """)
        
        logger.debug("Backup tables initialized successfully")
    except sqlite3.Error:
        logger.exception("Failed to initialize backup tables")
        raise
    finally:
        if should_close:
            db.close()


def _check_column_exists(db: DatabaseHandler, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    try:
        columns = db.fetch_all(f"PRAGMA table_info({table})")
        return any(col['name'] == column for col in columns)
    except sqlite3.Error:
        return False


def create_backup(
    name: str,
    note: Optional[str] = None,
    backup_type: str = "manual",
    db: Optional[DatabaseHandler] = None
) -> Dict[str, Any]:
    """
    Create a backup (snapshot) of the current active program.
    
    Args:
        name: Required name for the backup
        note: Optional note/description
        backup_type: 'manual' (user-initiated) or 'auto' (system-initiated)
        db: Optional shared database handler for callers managing a transaction
    
    Returns:
        Dict with backup metadata including id, name, item_count, etc.
    
    Raises:
        ValueError: If name is empty
        sqlite3.Error: On database errors
    """
    if not name or not name.strip():
        raise ValueError("Backup name is required")

    name = name.strip()
    if len(name) > 100:
        raise ValueError("Backup name must be 100 characters or fewer")

    if note is not None:
        note = note.strip()
        if len(note) > 500:
            raise ValueError("Backup note must be 500 characters or fewer")
        note = note or None
    
    should_close = False
    if db is None:
        db = DatabaseHandler()
        db.__enter__()
        should_close = True

    commit_writes = should_close

    try:
        # Check if user_selection table exists
        table_check = db.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_selection'"
        )
        if not table_check:
            logger.warning("user_selection table does not exist, creating empty backup")
            items = []
        else:
            # Check if exercise_order and superset_group columns exist
            has_order = _check_column_exists(db, 'user_selection', 'exercise_order')
            has_superset = _check_column_exists(db, 'user_selection', 'superset_group')
            
            # Build SELECT columns based on available columns
            base_cols = "routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight"
            extra_cols = []
            if has_order:
                extra_cols.append("exercise_order")
            if has_superset:
                extra_cols.append("superset_group")
            
            select_cols = base_cols + (", " + ", ".join(extra_cols) if extra_cols else "")
            order_clause = "ORDER BY exercise_order, routine, exercise" if has_order else "ORDER BY routine, exercise"
            
            # Fetch all items from active program
            items = db.fetch_all(f"""
                SELECT {select_cols}
                FROM user_selection
                {order_clause}
            """)
        
        item_count = len(items)
        
        # Create backup header
        db.execute_query("""
            INSERT INTO program_backups (name, note, backup_type, schema_version, item_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, note, backup_type, BACKUP_SCHEMA_VERSION, item_count, datetime.now()), commit=commit_writes)
        
        # Get the newly created backup ID
        result = db.fetch_one("SELECT last_insert_rowid() as id")
        if not result:
            raise RuntimeError("Failed to retrieve backup ID after insert")
        backup_id = result['id']
        
        # Insert all items
        if items:
            for item in items:
                db.execute_query("""
                    INSERT INTO program_backup_items 
                    (backup_id, routine, exercise, sets, min_rep_range, max_rep_range, 
                     rir, rpe, weight, exercise_order, superset_group)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    backup_id,
                    item.get('routine'),
                    item.get('exercise'),
                    item.get('sets'),
                    item.get('min_rep_range'),
                    item.get('max_rep_range'),
                    item.get('rir'),
                    item.get('rpe'),
                    item.get('weight'),
                    item.get('exercise_order'),  # Will be None if column doesn't exist
                    item.get('superset_group')   # Will be None if column doesn't exist
                ), commit=commit_writes)
        
        logger.info(
            "Backup created successfully",
            extra={
                'backup_id': backup_id,
                'backup_name': name,
                'backup_type': backup_type,
                'item_count': item_count
            }
        )
        
        return {
            'id': backup_id,
            'name': name,
            'note': note,
            'backup_type': backup_type,
            'schema_version': BACKUP_SCHEMA_VERSION,
            'item_count': item_count,
            'created_at': datetime.now().isoformat()
        }
    except BaseException as exc:
        if should_close:
            db.__exit__(type(exc), exc, exc.__traceback__)
            should_close = False
        raise
    finally:
        if should_close:
            db.__exit__(None, None, None)


def update_backup_metadata(
    backup_id: int,
    name: Optional[str] = None,
    note: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Update the editable metadata for a backup.

    Args:
        backup_id: The ID of the backup to update
        name: Optional new backup name
        note: Optional new backup note

    Returns:
        Updated backup metadata, or None if the backup does not exist

    Raises:
        ValueError: If neither field is provided or validation fails
        sqlite3.Error: On database errors
    """
    if name is None and note is None:
        raise ValueError("At least one of 'name' or 'note' must be provided")

    with DatabaseHandler() as db:
        existing = db.fetch_one(
            """
            SELECT id, name, note, backup_type, schema_version, item_count, created_at
            FROM program_backups
            WHERE id = ?
            """,
            (backup_id,),
        )

        if not existing:
            return None

        updates = []
        params = []

        if name is not None:
            normalized_name = name.strip()
            if not normalized_name:
                raise ValueError("Backup name is required")
            if len(normalized_name) > 100:
                raise ValueError("Backup name must be 100 characters or fewer")
            updates.append("name = ?")
            params.append(normalized_name)

        if note is not None:
            normalized_note = note.strip()
            if len(normalized_note) > 500:
                raise ValueError("Backup note must be 500 characters or fewer")
            updates.append("note = ?")
            params.append(normalized_note or None)

        db.execute_query(
            f"UPDATE program_backups SET {', '.join(updates)} WHERE id = ?",
            tuple(params + [backup_id]),
        )

        row = db.fetch_one(
            """
            SELECT id, name, note, backup_type, schema_version, item_count, created_at
            FROM program_backups
            WHERE id = ?
            """,
            (backup_id,),
        )

        return dict(row) if row else None


def list_backups() -> List[Dict[str, Any]]:
    """
    List all saved program backups.
    
    Returns:
        List of backup metadata dicts, ordered by created_at DESC
    """
    with DatabaseHandler() as db:
        backups = db.fetch_all("""
            SELECT id, name, note, backup_type, schema_version, item_count, created_at
            FROM program_backups
            ORDER BY created_at DESC
        """)
        
        return [dict(b) for b in backups]


def get_backup_details(backup_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific backup, including its items.
    
    Args:
        backup_id: The ID of the backup to retrieve
    
    Returns:
        Dict with backup metadata and items, or None if not found
    """
    with DatabaseHandler() as db:
        # Get backup header
        backup = db.fetch_one("""
            SELECT id, name, note, backup_type, schema_version, item_count, created_at
            FROM program_backups
            WHERE id = ?
        """, (backup_id,))
        
        if not backup:
            return None
        
        # Get backup items
        items = db.fetch_all("""
            SELECT routine, exercise, sets, min_rep_range, max_rep_range, 
                   rir, rpe, weight, exercise_order, superset_group
            FROM program_backup_items
            WHERE backup_id = ?
            ORDER BY exercise_order, routine, exercise
        """, (backup_id,))
        
        result = dict(backup)
        result['items'] = [dict(item) for item in items]
        
        return result


def restore_backup(backup_id: int) -> Dict[str, Any]:
    """
    Restore a backup to the active program (replace mode).
    
    This will:
    1. Clear all current user_selection entries
    2. Insert all backup items (skipping any with missing exercises)
    
    Args:
        backup_id: The ID of the backup to restore
    
    Returns:
        Dict with restore results including:
        - restored_count: Number of items successfully restored
        - skipped: List of exercises that were skipped (missing from catalog)
        - backup_name: Name of the restored backup
    
    Raises:
        ValueError: If backup_id is invalid
    """
    with DatabaseHandler() as db:
        # Verify backup exists
        backup = db.fetch_one("""
            SELECT id, name, item_count
            FROM program_backups
            WHERE id = ?
        """, (backup_id,))
        
        if not backup:
            raise ValueError(f"Backup with id {backup_id} not found")
        
        backup_name = backup['name']
        
        # Get backup items
        items = db.fetch_all("""
            SELECT routine, exercise, sets, min_rep_range, max_rep_range, 
                   rir, rpe, weight, exercise_order, superset_group
            FROM program_backup_items
            WHERE backup_id = ?
        """, (backup_id,))
        
        # Get list of valid exercises from catalog
        valid_exercises = db.fetch_all("""
            SELECT exercise_name FROM exercises
        """)
        valid_exercise_names = {row['exercise_name'] for row in valid_exercises}
        
        # Check if exercise_order and superset_group columns exist in user_selection
        has_order = _check_column_exists(db, 'user_selection', 'exercise_order')
        has_superset = _check_column_exists(db, 'user_selection', 'superset_group')
        
        try:
            db.execute_query("BEGIN IMMEDIATE", commit=False)

            # Clear current active program (user_selection)
            # FK CASCADE from user_selection also clears workout_log; explicit DELETE documents intent.
            db.execute_query("DELETE FROM workout_log", commit=False)
            db.execute_query("DELETE FROM user_selection", commit=False)

            restored_count = 0
            skipped = []

            for item in items:
                exercise_name = item.get('exercise')

                # Check if exercise exists in catalog (FK constraint)
                if exercise_name not in valid_exercise_names:
                    skipped.append(exercise_name)
                    logger.warning(
                        f"Skipping exercise during restore: '{exercise_name}' not in catalog"
                    )
                    continue

                # Insert item
                # Build INSERT based on available columns
                if has_order and has_superset:
                    db.execute_query(
                        """
                        INSERT INTO user_selection
                        (routine, exercise, sets, min_rep_range, max_rep_range,
                         rir, rpe, weight, exercise_order, superset_group)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.get('routine'),
                            exercise_name,
                            item.get('sets'),
                            item.get('min_rep_range'),
                            item.get('max_rep_range'),
                            item.get('rir'),
                            item.get('rpe'),
                            item.get('weight'),
                            item.get('exercise_order'),
                            item.get('superset_group')
                        ),
                        commit=False,
                    )
                elif has_order:
                    db.execute_query(
                        """
                        INSERT INTO user_selection
                        (routine, exercise, sets, min_rep_range, max_rep_range,
                         rir, rpe, weight, exercise_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.get('routine'),
                            exercise_name,
                            item.get('sets'),
                            item.get('min_rep_range'),
                            item.get('max_rep_range'),
                            item.get('rir'),
                            item.get('rpe'),
                            item.get('weight'),
                            item.get('exercise_order')
                        ),
                        commit=False,
                    )
                elif has_superset:
                    db.execute_query(
                        """
                        INSERT INTO user_selection
                        (routine, exercise, sets, min_rep_range, max_rep_range,
                         rir, rpe, weight, superset_group)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.get('routine'),
                            exercise_name,
                            item.get('sets'),
                            item.get('min_rep_range'),
                            item.get('max_rep_range'),
                            item.get('rir'),
                            item.get('rpe'),
                            item.get('weight'),
                            item.get('superset_group')
                        ),
                        commit=False,
                    )
                else:
                    db.execute_query(
                        """
                        INSERT INTO user_selection
                        (routine, exercise, sets, min_rep_range, max_rep_range,
                         rir, rpe, weight)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.get('routine'),
                            exercise_name,
                            item.get('sets'),
                            item.get('min_rep_range'),
                            item.get('max_rep_range'),
                            item.get('rir'),
                            item.get('rpe'),
                            item.get('weight')
                        ),
                        commit=False,
                    )
                restored_count += 1
            db.connection.commit()
        except sqlite3.Error:
            db.connection.rollback()
            raise

        # Normalize skipped entries while preserving order
        skipped_unique = list(dict.fromkeys(skipped))
        
        logger.info(
            "Backup restored successfully",
            extra={
                'backup_id': backup_id,
                'backup_name': backup_name,
                'restored_count': restored_count,
                'skipped_count': len(skipped_unique)
            }
        )
        
        return {
            'backup_id': backup_id,
            'backup_name': backup_name,
            'restored_count': restored_count,
            'skipped': skipped_unique
        }


def delete_backup(backup_id: int) -> bool:
    """
    Delete a backup and all its items.
    
    Args:
        backup_id: The ID of the backup to delete
    
    Returns:
        True if deletion was successful, False if backup not found
    """
    with DatabaseHandler() as db:
        # Check if backup exists
        backup = db.fetch_one("""
            SELECT id, name FROM program_backups WHERE id = ?
        """, (backup_id,))
        
        if not backup:
            logger.warning(f"Attempted to delete non-existent backup: {backup_id}")
            return False
        
        backup_name = backup['name']
        
        # Delete backup items first (cascading delete should handle this, but be explicit)
        db.execute_query("""
            DELETE FROM program_backup_items WHERE backup_id = ?
        """, (backup_id,))
        
        # Delete backup header
        db.execute_query("""
            DELETE FROM program_backups WHERE id = ?
        """, (backup_id,))
        
        logger.info(
            "Backup deleted successfully",
            extra={
                'backup_id': backup_id,
                'backup_name': backup_name
            }
        )
        
        return True


def create_auto_backup_before_erase() -> Optional[Dict[str, Any]]:
    """
    Create an automatic backup before erase/reset operations.
    
    Only creates a backup if the active program has data.
    
    Returns:
        Backup metadata dict if backup was created, None if active program was empty
    """
    with DatabaseHandler() as db:
        # Check if user_selection table exists and has data
        table_check = db.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_selection'"
        )
        
        if not table_check:
            logger.debug("No user_selection table found, skipping auto-backup")
            return None
        
        count_result = db.fetch_one("SELECT COUNT(*) as count FROM user_selection")
        if not count_result or count_result['count'] == 0:
            logger.debug("Active program is empty, skipping auto-backup")
            return None
    
    # Create timestamped auto-backup
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    backup_name = f"Pre-Erase Auto-Backup ({timestamp})"

    with DatabaseHandler() as db:
        db.execute_query("BEGIN IMMEDIATE", commit=False)
        try:
            backup = create_backup(
                name=backup_name,
                note="Automatically created before erase/reset operation",
                backup_type="auto",
                db=db,
            )
            prune_auto_backups(keep_count=10, db=db)
            db.connection.commit()
            return backup
        except sqlite3.Error:
            db.connection.rollback()
            raise


def prune_auto_backups(keep_count: int = 10, db: Optional[DatabaseHandler] = None) -> int:
    """Delete auto-backups beyond the latest keep_count. Manual backups are never touched.

    Returns the number of rows deleted.
    """
    should_close = False
    if db is None:
        db = DatabaseHandler()
        db.__enter__()
        should_close = True

    try:
        rowcount = db.execute_query(
            """
            DELETE FROM program_backups
             WHERE backup_type = 'auto'
               AND id NOT IN (
                     SELECT id FROM program_backups
                      WHERE backup_type = 'auto'
                      ORDER BY created_at DESC
                      LIMIT ?
                   )
            """,
            (keep_count,),
            commit=should_close,
        )
        logger.info("Pruned auto-backups", extra={'kept': keep_count, 'deleted': rowcount})
        return rowcount
    except BaseException as exc:
        if should_close:
            db.__exit__(type(exc), exc, exc.__traceback__)
            should_close = False
        raise
    finally:
        if should_close:
            db.__exit__(None, None, None)


def get_latest_auto_backup() -> Optional[Dict[str, Any]]:
    """
    Get the most recent auto-backup.
    
    Returns:
        Backup metadata dict or None if no auto-backups exist
    """
    with DatabaseHandler() as db:
        backup = db.fetch_one("""
            SELECT id, name, note, backup_type, schema_version, item_count, created_at
            FROM program_backups
            WHERE backup_type = 'auto'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        return dict(backup) if backup else None


def get_active_program_count() -> int:
    """
    Get the number of items in the current active program.
    
    Returns:
        Number of items in user_selection, or 0 if table doesn't exist
    """
    with DatabaseHandler() as db:
        table_check = db.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_selection'"
        )
        
        if not table_check:
            return 0
        
        result = db.fetch_one("SELECT COUNT(*) as count FROM user_selection")
        return result['count'] if result else 0
