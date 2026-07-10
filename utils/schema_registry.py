"""Canonical database schema initialization and owned-table registry."""
from __future__ import annotations

from utils.database import (
    DatabaseHandler,
    add_body_composition_snapshots_table,
    add_fatigue_context_settings_table,
    add_progression_goals_table,
    add_strength_calibration_tables,
    add_user_profile_tables,
    add_volume_tracking_tables,
)
from utils.db_initializer import initialize_database
from utils.logger import get_logger
from utils.program_backup import initialize_backup_tables


logger = get_logger()


OWNED_TABLES_DROP_ORDER = (
    'program_backup_items',  # Drop child table first (FK constraint)
    'program_backups',        # Then parent backup table
    'ignored_calibration_transfers',
    'exercise_transfer_ratios',
    'learned_strength_calibrations',
    'user_calibration_settings',
    'fatigue_context_settings',
    'user_profile_preferences',
    'user_profile_lifts',
    'user_profile',
    'body_composition_snapshots',
    'user_selection',
    'progression_goals',
    'muscle_volumes',
    'volume_plans',
    'workout_log',
)


def column_exists(db, table_name, column_name):
    """Check if a column exists in a table using PRAGMA."""
    query = f"PRAGMA table_info({table_name})"
    columns = db.fetch_all(query)
    return any(col['name'] == column_name for col in columns)


def table_exists(db, table_name):
    """Check if a table exists in the database."""
    result = db.fetch_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return result is not None


def initialize_exercise_order():
    """Initialize or update the order column in user_selection table."""
    try:
        with DatabaseHandler() as db:
            # First check if the table exists
            if not table_exists(db, 'user_selection'):
                logger.debug("user_selection table does not exist yet, skipping exercise order initialization")
                return True

            # Check if column exists using PRAGMA
            if column_exists(db, 'user_selection', 'exercise_order'):
                logger.debug("Exercise order column already exists")
                # Check for any NULL exercise_order values and initialize them
                null_count = db.fetch_one(
                    "SELECT COUNT(*) as count FROM user_selection WHERE exercise_order IS NULL"
                )
                if null_count and null_count.get('count', 0) > 0:
                    logger.info(f"Found {null_count['count']} rows with NULL exercise_order, initializing...")
                    # Get max existing order
                    max_order = db.fetch_one(
                        "SELECT COALESCE(MAX(exercise_order), 0) as max_order FROM user_selection"
                    )
                    current_order = (max_order.get('max_order', 0) or 0) if max_order else 0

                    # Get rows with NULL order, sorted by id (oldest first)
                    null_rows = db.fetch_all(
                        "SELECT id FROM user_selection WHERE exercise_order IS NULL ORDER BY id"
                    )
                    for row in null_rows:
                        current_order += 1
                        db.execute_query(
                            "UPDATE user_selection SET exercise_order = ? WHERE id = ?",
                            (current_order, row['id'])
                        )
                    logger.info(f"Initialized exercise_order for {len(null_rows)} rows")
            else:
                logger.info("Adding exercise_order column")
                # Add the column
                db.execute_query("ALTER TABLE user_selection ADD COLUMN exercise_order INTEGER")

                # Initialize with sequential order
                db.execute_query("""
                    UPDATE user_selection
                    SET exercise_order = (
                        SELECT ROW_NUMBER() OVER (ORDER BY routine, exercise)
                        FROM user_selection AS t2
                        WHERE t2.id = user_selection.id
                    )
                """)
                logger.info("Exercise order column initialized")

        return True
    except Exception as e:
        logger.exception("Error initializing exercise order")
        return False


def run_all_initializers(*, force_base: bool = False) -> None:
    """Run every schema initializer in the canonical startup order."""
    logger.info("Initializing database...")
    initialize_database(force=force_base)
    logger.info("Adding progression goals table...")
    add_progression_goals_table()
    logger.info("Adding volume tracking tables...")
    add_volume_tracking_tables()
    logger.info("Adding user profile tables...")
    add_user_profile_tables()
    logger.info("Adding body composition snapshots table...")
    add_body_composition_snapshots_table()
    logger.info("Adding strength calibration tables...")
    add_strength_calibration_tables()
    logger.info("Adding fatigue context settings table...")
    add_fatigue_context_settings_table()
    logger.info("Initializing exercise order...")
    initialize_exercise_order()
    logger.info("Initializing backup tables...")
    initialize_backup_tables()
    logger.info("Database initialization complete")


def drop_all_owned_tables(db: DatabaseHandler) -> None:
    """Drop application-owned user-state tables in FK-safe order."""
    for table in OWNED_TABLES_DROP_ORDER:
        db.execute_query(f"DROP TABLE IF EXISTS {table}")
