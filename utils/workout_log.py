from .database import DatabaseHandler
from .logger import get_logger

logger = get_logger()


ASSISTED_BODYWEIGHT_EXERCISES = frozenset({
    "machine assisted chin up",
    "machine assisted narrow pull up",
    "machine assisted neutral chin up",
    "machine assisted parallel bar dips",
    "machine assisted pull up",
    "smith machine assisted pullup",
})


def _normalize_exercise_name(exercise_name):
    if exercise_name is None:
        return ""
    return " ".join(str(exercise_name).strip().lower().replace("-", " ").split())


def is_assisted_bodyweight_exercise(exercise_name):
    """Return True when logged weight means assistance, not external load."""
    return _normalize_exercise_name(exercise_name) in ASSISTED_BODYWEIGHT_EXERCISES


def is_weight_progression(exercise_name, planned_weight, scored_weight):
    """Compare weight-like fields, accounting for assisted bodyweight machines."""
    if planned_weight is None or scored_weight is None:
        return False

    try:
        planned = float(planned_weight)
        scored = float(scored_weight)
    except (TypeError, ValueError):
        return False

    if is_assisted_bodyweight_exercise(exercise_name):
        return scored < planned

    return scored > planned


def get_weight_progression_indicator(exercise_name, planned_weight, scored_weight):
    """Return render metadata for the scored-weight progression indicator."""
    if planned_weight is None or scored_weight is None:
        return None

    try:
        planned = float(planned_weight)
        scored = float(scored_weight)
    except (TypeError, ValueError):
        return None
    is_assisted = is_assisted_bodyweight_exercise(exercise_name)
    diff = round(scored - planned, 1)
    abs_diff = round(abs(diff), 1)

    if scored == planned:
        return {
            "icon": "fa-equals",
            "class": "text-warning",
            "title": "Same assistance" if is_assisted else "Same weight",
        }

    if is_assisted:
        if scored < planned:
            return {
                "icon": "fa-arrow-up",
                "class": "text-success",
                "title": f"Assistance decreased! (-{abs_diff}kg assistance)",
            }
        return {
            "icon": "fa-arrow-down",
            "class": "text-danger",
            "title": f"Assistance increased (+{abs_diff}kg assistance)",
        }

    if scored > planned:
        return {
            "icon": "fa-arrow-up",
            "class": "text-success",
            "title": f"Weight increased! (+{diff}kg)",
        }

    return {
        "icon": "fa-arrow-down",
        "class": "text-danger",
        "title": f"Weight decreased ({diff}kg)",
    }


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
        e.youtube_video_id,
        e.media_path
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
    exercise_name = log_entry.get('exercise') if hasattr(log_entry, 'get') else log_entry['exercise']
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

        is_weight_progression(
            exercise_name,
            log_entry['planned_weight'],
            log_entry['scored_weight'],
        )
    ]
    
    return any(conditions) 
