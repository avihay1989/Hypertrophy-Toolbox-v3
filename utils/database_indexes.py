"""Database index management for performance optimization."""
import sqlite3
from utils.database import DatabaseHandler, get_db_connection, _DB_LOCK
from utils.logger import get_logger

logger = get_logger()

def create_performance_indexes():
    """Create indexes on hot filter columns and query optimization."""
    with DatabaseHandler() as db:
        indexes = [
            # Exercise filter indexes
            ("idx_exercises_primary_muscle", "exercises", "primary_muscle_group"),
            ("idx_exercises_equipment", "exercises", "equipment"),
            ("idx_exercises_mechanic", "exercises", "mechanic"),
            ("idx_exercises_force", "exercises", "force"),
            ("idx_exercises_name", "exercises", "exercise_name"),
            ("idx_exercises_secondary_muscle", "exercises", "secondary_muscle_group"),
            ("idx_exercises_difficulty", "exercises", "difficulty"),
            ("idx_exercises_utility", "exercises", "utility"),
            
            # Composite indexes for common filter combinations
            ("idx_exercises_primary_equipment", "exercises", "primary_muscle_group, equipment"),
            ("idx_exercises_primary_mechanic", "exercises", "primary_muscle_group, mechanic"),
            ("idx_exercises_equipment_mechanic", "exercises", "equipment, mechanic"),
            
            # Movement pattern indexes (for plan generator and pattern coverage)
            ("idx_exercises_movement_pattern", "exercises", "movement_pattern"),
            ("idx_exercises_pattern_muscle", "exercises", "movement_pattern, primary_muscle_group"),
            
            # User selection indexes (for plan queries and pattern coverage)
            ("idx_user_selection_routine", "user_selection", "routine"),
            ("idx_user_selection_routine_exercise", "user_selection", "routine, exercise"),
        ]
        for index_name, table_name, columns in indexes:
            try:
                check_query = "SELECT name FROM sqlite_master WHERE type='index' AND name=?"
                existing = db.fetch_one(check_query, (index_name,))
                if existing:
                    logger.info(f"Index {index_name} already exists, skipping")
                    continue
                create_index_query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})"
                db.execute_query(create_index_query)
                logger.info(f"Created index: {index_name} on {table_name}({columns})")
            except sqlite3.Error as e:
                logger.error(f"Error creating index {index_name}: {e}", exc_info=True)
                continue

def optimize_database():
    """Run SQLite maintenance commands under the global DB lock.

    ``ANALYZE`` and ``PRAGMA optimize`` are not currently classified as
    write operations by ``DatabaseHandler``. Keep the maintenance path on the
    raw connection helper for now, but hold ``_DB_LOCK`` explicitly so these
    long-running operations do not overlap with concurrent writes.
    """
    conn = None
    _DB_LOCK.acquire()
    try:
        conn = get_db_connection()
        conn.execute("ANALYZE")
        logger.info("Database analyzed successfully")
        conn.execute("PRAGMA optimize")
        logger.info("Database optimized successfully")
        conn.commit()
    except sqlite3.Error as e:
        if conn is not None:
            conn.rollback()
        logger.error(f"Error optimizing database: {e}", exc_info=True)
    finally:
        if conn is not None:
            conn.close()
        _DB_LOCK.release()

def analyze_query_plan(query, params=None):
    """Analyze query execution plan."""
    with DatabaseHandler() as db:
        explain_query = f"EXPLAIN QUERY PLAN {query}"
        results = db.fetch_all(explain_query, params) if params else db.fetch_all(explain_query)
        logger.info(f"Query plan for: {query[:100]}...")
        for row in results:
            logger.info(f"  {row}")
        return results

def get_index_list():
    """Get list of all indexes."""
    with DatabaseHandler() as db:
        query = "SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY tbl_name, name"
        results = db.fetch_all(query)
        logger.info(f"Found {len(results)} indexes in database")
        return results
