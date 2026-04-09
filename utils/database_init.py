from .database import DatabaseHandler
from .logger import get_logger

logger = get_logger()

def initialize_workout_log_table():
    """Create the workout_log table if it doesn't exist."""
    query = """
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
        last_progression_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (workout_plan_id) REFERENCES user_selection(id)
    );
    """
    try:
        with DatabaseHandler() as db:
            db.execute_query(query)
            logger.info("Workout log table initialized successfully")
    except Exception as e:
        logger.exception("Error initializing workout log table: %s", e) 
