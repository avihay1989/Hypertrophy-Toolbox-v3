from .database import DatabaseHandler
from .logger import get_logger

logger = get_logger()

def get_workout_logs():
    """Fetch all workout log entries."""
    query = """
    SELECT 
        id,
        routine,
        exercise,
        planned_sets,
        planned_min_reps,
        planned_max_reps,
        planned_rir,
        planned_rpe,
        planned_weight,
        scored_min_reps,
        scored_max_reps,
        scored_rir,
        scored_rpe,
        scored_weight,
        last_progression_date,
        created_at
    FROM workout_log 
    ORDER BY routine, exercise
    """
    try:
        with DatabaseHandler() as db:
            return db.fetch_all(query)
    except Exception as e:
        logger.exception("Error fetching workout logs: %s", e)
        return []

def check_progression(log_entry):
    """Check if progressive overload was achieved."""
    conditions = [
        log_entry['scored_rir'] is not None and 
        log_entry['planned_rir'] is not None and 
        log_entry['scored_rir'] < log_entry['planned_rir'],

        log_entry['scored_rpe'] is not None and 
        log_entry['planned_rpe'] is not None and 
        log_entry['scored_rpe'] > log_entry['planned_rpe'],

        log_entry['scored_min_reps'] is not None and 
        log_entry['planned_min_reps'] is not None and 
        log_entry['scored_min_reps'] > log_entry['planned_min_reps'],

        log_entry['scored_max_reps'] is not None and 
        log_entry['planned_max_reps'] is not None and 
        log_entry['scored_max_reps'] > log_entry['planned_max_reps'],

        log_entry['scored_weight'] is not None and 
        log_entry['planned_weight'] is not None and 
        log_entry['scored_weight'] > log_entry['planned_weight']
    ]
    
    return any(conditions) 
