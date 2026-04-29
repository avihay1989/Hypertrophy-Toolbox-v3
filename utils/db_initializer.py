"""Database bootstrap helpers used at application start and in tests."""
from __future__ import annotations

import os
import sqlite3
import threading
from utils.database import DatabaseHandler
from utils.logger import get_logger
from utils.normalization import normalize_equipment, normalize_muscle

logger = get_logger()

# Guard against double initialization during Flask auto-reload
_INITIALIZATION_LOCK = threading.Lock()
_INITIALIZATION_COMPLETE = False


def _initialize_exercises_table(db: DatabaseHandler) -> None:
    existing = db.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='exercises'"
    )
    if existing:
        cols = db.fetch_all("PRAGMA table_info(exercises)")
        pk_column = next((row['name'] for row in cols if row.get('pk') == 1), None)
        if pk_column != 'exercise_name':
            db.execute_query("DROP TABLE IF EXISTS exercises")

    db.execute_query(
        """
        CREATE TABLE IF NOT EXISTS exercises (
            exercise_name TEXT PRIMARY KEY,
            primary_muscle_group TEXT,
            secondary_muscle_group TEXT,
            tertiary_muscle_group TEXT,
            advanced_isolated_muscles TEXT,
            utility TEXT,
            grips TEXT,
            stabilizers TEXT,
            synergists TEXT,
            force TEXT,
            equipment TEXT,
            mechanic TEXT,
            difficulty TEXT,
            movement_pattern TEXT,
            movement_subpattern TEXT,
            youtube_video_id TEXT,
            media_path TEXT
        )
        """
    )

    # Add movement pattern columns if they don't exist (for existing databases)
    cols = db.fetch_all("PRAGMA table_info(exercises)")
    col_names = {row['name'] for row in cols}
    if 'movement_pattern' not in col_names:
        db.execute_query("ALTER TABLE exercises ADD COLUMN movement_pattern TEXT")
    if 'movement_subpattern' not in col_names:
        db.execute_query("ALTER TABLE exercises ADD COLUMN movement_subpattern TEXT")
    if 'youtube_video_id' not in col_names:
        db.execute_query("ALTER TABLE exercises ADD COLUMN youtube_video_id TEXT")
    if 'media_path' not in col_names:
        db.execute_query("ALTER TABLE exercises ADD COLUMN media_path TEXT")
    db.execute_query(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_exercise_name_nocase
        ON exercises(exercise_name COLLATE NOCASE)
        """
    )


def _initialize_isolated_muscles_table(db: DatabaseHandler) -> None:
    existing = db.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='exercise_isolated_muscles'"
    )
    if existing:
        columns = {
            row['name'] for row in db.fetch_all("PRAGMA table_info(exercise_isolated_muscles)")
        }
        fk_info = db.fetch_all("PRAGMA foreign_key_list(exercise_isolated_muscles)")
        expected_columns = {'exercise_name', 'muscle'}
        fk_valid = bool(
            fk_info
            and fk_info[0].get('table') == 'exercises'
            and fk_info[0].get('from') == 'exercise_name'
            and fk_info[0].get('to') == 'exercise_name'
        )
        if columns != expected_columns or not fk_valid:
            db.execute_query("DROP TABLE IF EXISTS exercise_isolated_muscles")

    db.execute_query(
        """
        CREATE TABLE IF NOT EXISTS exercise_isolated_muscles (
            exercise_name TEXT NOT NULL,
            muscle TEXT NOT NULL,
            PRIMARY KEY (exercise_name, muscle),
            FOREIGN KEY (exercise_name) REFERENCES exercises(exercise_name) ON DELETE CASCADE
        )
        """
    )
    db.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_eim_muscle
        ON exercise_isolated_muscles(muscle)
        """
    )


def _rebuild_isolated_muscles_mapping(db: DatabaseHandler) -> None:
    """Rebuild exercise_isolated_muscles from the advanced_isolated_muscles column."""
    try:
        db.execute_query("DELETE FROM exercise_isolated_muscles")
        db.execute_query(
            """
            WITH RECURSIVE split(exercise_name, rest, part) AS (
              SELECT exercise_name,
                     REPLACE(COALESCE(advanced_isolated_muscles,''), ';', ',') || ',',
                     ''
              FROM exercises
              WHERE advanced_isolated_muscles IS NOT NULL
                AND TRIM(advanced_isolated_muscles) <> ''

              UNION ALL
              SELECT exercise_name,
                     substr(rest, instr(rest, ',') + 1),
                     TRIM(substr(rest, 1, instr(rest, ',') - 1))
              FROM split
              WHERE rest <> ''
            )
            INSERT OR IGNORE INTO exercise_isolated_muscles (exercise_name, muscle)
            SELECT exercise_name, 
                   LOWER(REPLACE(REPLACE(TRIM(part), ' ', '-'), '_', '-'))
            FROM split
            WHERE part <> ''
            """
        )
        row = db.fetch_one("SELECT COUNT(*) AS count FROM exercise_isolated_muscles")
        count = int(row["count"]) if row and row.get("count") is not None else 0
        logger.info("Rebuilt exercise_isolated_muscles with %s mappings", count)
    except sqlite3.Error:
        logger.exception("Failed to rebuild exercise_isolated_muscles mapping")


def _initialize_user_selection_table(db: DatabaseHandler) -> None:
    if os.getenv("TESTING") == "1":
        db.execute_query("DROP TABLE IF EXISTS user_selection")
    else:
        existing = db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_selection'"
        )
        if existing:
            fk_info = db.fetch_all("PRAGMA foreign_key_list(user_selection)")
            exercise_fk = next(
                (
                    row
                    for row in fk_info
                    if row.get('from') == 'exercise'
                    and row.get('table') == 'exercises'
                    and row.get('to') == 'exercise_name'
                ),
                None,
            )
            cascade_ok = exercise_fk and exercise_fk.get('on_delete', '').upper() == 'CASCADE'
            if not cascade_ok:
                db.execute_query("DROP TABLE IF EXISTS user_selection")

    db.execute_query(
        """
        CREATE TABLE IF NOT EXISTS user_selection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine TEXT NOT NULL,
            exercise TEXT NOT NULL,
            sets INTEGER NOT NULL,
            min_rep_range INTEGER NOT NULL,
            max_rep_range INTEGER NOT NULL,
            rir INTEGER,
            rpe REAL,
            weight REAL NOT NULL,
            superset_group TEXT DEFAULT NULL,
            FOREIGN KEY (exercise) REFERENCES exercises(exercise_name) ON DELETE CASCADE,
            UNIQUE (routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight)
        )
        """
    )
    
    # Add superset_group column if it doesn't exist (migration for existing databases)
    cols = db.fetch_all("PRAGMA table_info(user_selection)")
    col_names = {row['name'] for row in cols}
    if 'superset_group' not in col_names:
        db.execute_query("ALTER TABLE user_selection ADD COLUMN superset_group TEXT DEFAULT NULL")
        logger.info("Added superset_group column to user_selection table")
    
    # Phase 3: Add execution style columns for AMRAP/EMOM support
    if 'execution_style' not in col_names:
        db.execute_query("ALTER TABLE user_selection ADD COLUMN execution_style TEXT DEFAULT 'standard'")
        logger.info("Added execution_style column to user_selection table")
    if 'time_cap_seconds' not in col_names:
        db.execute_query("ALTER TABLE user_selection ADD COLUMN time_cap_seconds INTEGER DEFAULT NULL")
        logger.info("Added time_cap_seconds column to user_selection table")
    if 'emom_interval_seconds' not in col_names:
        db.execute_query("ALTER TABLE user_selection ADD COLUMN emom_interval_seconds INTEGER DEFAULT NULL")
        logger.info("Added emom_interval_seconds column to user_selection table")
    if 'emom_rounds' not in col_names:
        db.execute_query("ALTER TABLE user_selection ADD COLUMN emom_rounds INTEGER DEFAULT NULL")
        logger.info("Added emom_rounds column to user_selection table")
    
    db.execute_query(
        """
        CREATE INDEX IF NOT EXISTS idx_user_selection_exercise
        ON user_selection(exercise)
        """
    )


def _initialize_workout_log_table(db: DatabaseHandler) -> None:
    if os.getenv("TESTING") == "1":
        db.execute_query("DROP TABLE IF EXISTS workout_log")
    else:
        existing = db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workout_log'"
        )
        if existing:
            fk_info = db.fetch_all("PRAGMA foreign_key_list(workout_log)")
            plan_fk = next(
                (
                    row
                    for row in fk_info
                    if row.get('from') == 'workout_plan_id'
                    and row.get('table') == 'user_selection'
                    and row.get('to') == 'id'
                ),
                None,
            )
            cascade_ok = plan_fk and plan_fk.get('on_delete', '').upper() == 'CASCADE'
            if not cascade_ok:
                db.execute_query("DROP TABLE IF EXISTS workout_log")

    db.execute_query(
        """
        CREATE TABLE IF NOT EXISTS workout_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_plan_id INTEGER,
            routine TEXT NOT NULL,
            exercise TEXT NOT NULL,
            planned_sets INTEGER,
            planned_min_reps INTEGER,
            planned_max_reps INTEGER,
            planned_rir INTEGER,
            planned_rpe REAL,
            planned_weight REAL,
            scored_weight REAL,
            scored_min_reps INTEGER,
            scored_max_reps INTEGER,
            scored_rir INTEGER,
            scored_rpe REAL,
            last_progression_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workout_plan_id) REFERENCES user_selection(id) ON DELETE CASCADE
        )
        """
    )


def _backfill_workout_log_plan_ids(db: DatabaseHandler) -> None:
    """Backfill NULL workout_plan_id in workout_log by matching plan fields.

    Legacy rows were inserted without the FK.  We match on the full set of
    planned fields (routine, exercise, sets, rep range, weight, rir, rpe)
    to avoid linking a stale log to a modified plan row.  Ambiguous or
    unmatched rows are left as NULL and a warning is logged with the count.
    """
    try:
        null_count_row = db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM workout_log WHERE workout_plan_id IS NULL"
        )
        null_count = int(null_count_row["cnt"]) if null_count_row else 0
        if null_count == 0:
            return

        logger.info(f"Backfilling workout_plan_id for {null_count} workout_log rows")

        # Update where exactly one user_selection row matches on ALL planned fields.
        # Using COALESCE so that NULL = NULL comparisons don't silently fail.
        db.execute_query(
            """
            UPDATE workout_log
            SET workout_plan_id = (
                SELECT us.id
                FROM user_selection us
                WHERE us.routine       = workout_log.routine
                  AND us.exercise      = workout_log.exercise
                  AND us.sets          = workout_log.planned_sets
                  AND us.min_rep_range = workout_log.planned_min_reps
                  AND us.max_rep_range = workout_log.planned_max_reps
                  AND COALESCE(us.weight, -1) = COALESCE(workout_log.planned_weight, -1)
                  AND COALESCE(us.rir, -1)    = COALESCE(workout_log.planned_rir, -1)
                  AND COALESCE(us.rpe, -1)    = COALESCE(workout_log.planned_rpe, -1)
            )
            WHERE workout_plan_id IS NULL
              AND (
                SELECT COUNT(*)
                FROM user_selection us
                WHERE us.routine       = workout_log.routine
                  AND us.exercise      = workout_log.exercise
                  AND us.sets          = workout_log.planned_sets
                  AND us.min_rep_range = workout_log.planned_min_reps
                  AND us.max_rep_range = workout_log.planned_max_reps
                  AND COALESCE(us.weight, -1) = COALESCE(workout_log.planned_weight, -1)
                  AND COALESCE(us.rir, -1)    = COALESCE(workout_log.planned_rir, -1)
                  AND COALESCE(us.rpe, -1)    = COALESCE(workout_log.planned_rpe, -1)
              ) = 1
            """
        )

        still_null_row = db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM workout_log WHERE workout_plan_id IS NULL"
        )
        still_null = int(still_null_row["cnt"]) if still_null_row else 0
        matched = null_count - still_null
        logger.info(
            f"Backfill complete: {matched} rows matched, {still_null} rows unmatched"
        )
        if still_null > 0:
            logger.warning(
                f"{still_null} workout_log rows could not be matched to a plan row "
                "(ambiguous or deleted plan entries)"
            )
    except Exception:
        logger.exception("Error during workout_log FK backfill")


def _normalize_equipment_values(db: DatabaseHandler) -> None:
    """Ensure equipment values align with canonical normalization rules."""
    try:
        rows = db.fetch_all(
            "SELECT DISTINCT TRIM(equipment) AS equipment FROM exercises "
            "WHERE equipment IS NOT NULL AND TRIM(equipment) <> ''"
        )
    except sqlite3.Error:
        logger.exception("Failed to read distinct equipment values for normalization")
        return

    if not rows:
        return

    changes = 0
    for row in rows:
        original = row.get("equipment")
        if not original:
            continue
        normalised = normalize_equipment(original)
        if normalised is None or normalised == original:
            continue
        try:
            db.execute_query(
                "UPDATE exercises SET equipment = ? WHERE equipment = ?",
                (normalised, original),
            )
            changes += 1
        except sqlite3.Error:
            logger.exception("Failed to normalise equipment value '%s'", original)

    if changes:
        logger.info("Normalised %s equipment label%s", changes, "s" if changes != 1 else "")


def _normalize_muscle_group_values(db: DatabaseHandler) -> None:
    """Standardise muscle group columns to canonical casing and aliases."""
    muscle_columns = (
        "primary_muscle_group",
        "secondary_muscle_group",
        "tertiary_muscle_group",
    )

    for column in muscle_columns:
        try:
            rows = db.fetch_all(
                f"SELECT exercise_name, {column} FROM exercises "
                f"WHERE {column} IS NOT NULL AND TRIM({column}) <> ''"
            )
        except sqlite3.Error:
            logger.exception("Failed to read values for column '%s'", column)
            continue

        if not rows:
            continue

        updates = 0
        for row in rows:
            original = row.get(column)
            if not original:
                continue

            normalised = normalize_muscle(original)
            if normalised is None or normalised == original:
                continue

            try:
                db.execute_query(
                    f"UPDATE exercises SET {column} = ? WHERE exercise_name = ?",
                    (normalised, row.get("exercise_name")),
                )
                updates += 1
            except sqlite3.Error:
                logger.exception(
                    "Failed to normalise %s value '%s' -> '%s' for exercise '%s'",
                    column,
                    original,
                    normalised,
                    row.get("exercise_name"),
                )

        if updates:
            logger.info(
                "Normalised %s %s value%s",
                updates,
                column,
                "s" if updates != 1 else "",
            )


def initialize_database(force: bool = False) -> None:
    """Initialise all required tables and supporting indexes.
    
    Thread-safe: Uses locking to prevent concurrent initialization
    which can cause database corruption during Flask auto-reload.
    
    Args:
        force: If True, skip the initialization guard (useful for tests)
    """
    global _INITIALIZATION_COMPLETE
    
    # Quick check without lock (optimization)
    if _INITIALIZATION_COMPLETE and not force and os.getenv("TESTING") != "1":
        logger.debug("Database already initialized, skipping")
        return
    
    with _INITIALIZATION_LOCK:
        # Double-check after acquiring lock
        if _INITIALIZATION_COMPLETE and not force and os.getenv("TESTING") != "1":
            logger.debug("Database already initialized (verified under lock), skipping")
            return
        
        logger.info("Starting database initialization...")
        
        with DatabaseHandler() as db:
            _initialize_exercises_table(db)
            _initialize_isolated_muscles_table(db)
            _initialize_user_selection_table(db)
            _initialize_workout_log_table(db)
            _backfill_workout_log_plan_ids(db)
            _normalize_equipment_values(db)
            _normalize_muscle_group_values(db)
            _populate_movement_patterns(db)
        
        _INITIALIZATION_COMPLETE = True
        logger.info("Database initialization complete")


def _populate_movement_patterns(db: DatabaseHandler) -> None:
    """Populate movement_pattern and movement_subpattern for exercises that don't have them."""
    try:
        from utils.movement_patterns import classify_exercise
    except ImportError:
        logger.warning("movement_patterns module not available, skipping pattern population")
        return
    
    try:
        rows = db.fetch_all(
            """
            SELECT exercise_name, primary_muscle_group, mechanic 
            FROM exercises 
            WHERE movement_pattern IS NULL OR movement_pattern = ''
            """
        )
    except sqlite3.Error:
        logger.exception("Failed to query exercises for pattern population")
        return
    
    if not rows:
        logger.debug("All exercises already have movement patterns assigned")
        return
    
    updates = 0
    for row in rows:
        exercise_name = row.get("exercise_name")
        if not exercise_name:
            continue
        
        pattern, subpattern = classify_exercise(
            exercise_name,
            row.get("primary_muscle_group"),
            row.get("mechanic"),
        )
        
        if pattern:
            try:
                db.execute_query(
                    """
                    UPDATE exercises 
                    SET movement_pattern = ?, movement_subpattern = ?
                    WHERE exercise_name = ?
                    """,
                    (pattern.value, subpattern.value if subpattern else None, exercise_name),
                )
                updates += 1
            except sqlite3.Error:
                logger.exception(
                    "Failed to update movement pattern for exercise '%s'",
                    exercise_name,
                )
    
    if updates:
        logger.info(
            "Populated movement patterns for %s exercise%s",
            updates,
            "s" if updates != 1 else "",
        )
