from .database import DatabaseHandler
from .logger import get_logger

logger = get_logger()

def get_workout_logs():
    """Fetch all workout log entries."""
    query = """
    SELECT
        wl.id,
        wl.routine,
        wl.exercise,
        wl.planned_sets,
        wl.planned_min_reps,
        wl.planned_max_reps,
        wl.planned_rir,
        wl.planned_rpe,
        wl.planned_weight,
        wl.scored_min_reps,
        wl.scored_max_reps,
        wl.scored_rir,
        wl.scored_rpe,
        wl.scored_weight,
        wl.last_progression_date,
        wl.created_at,
        e.youtube_video_id
    FROM workout_log wl
    LEFT JOIN exercises e ON wl.exercise = e.exercise_name COLLATE NOCASE
    ORDER BY wl.routine, wl.exercise
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
