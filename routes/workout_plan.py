from flask import Blueprint, render_template, request, jsonify
import json
import werkzeug.exceptions
from utils.database import DatabaseHandler
from utils.exercise_manager import (
    add_exercise as add_exercise_to_db,
    get_exercises,
)
from utils.errors import success_response, error_response
from utils.logger import get_logger
from routes.filters import ALLOWED_COLUMNS, validate_column_name
from utils.constants import DIFFICULTY, MECHANIC, UTILITY, ANTAGONIST_PAIRS
from utils.plan_generator import generate_starter_plan
from utils.volume_progress import get_volume_progress

workout_plan_bp = Blueprint('workout_plan', __name__)
logger = get_logger()

def fetch_unique_values(column):
    """Fetch unique values for a specified column from the exercises table."""
    # Validate column name is whitelisted
    if not validate_column_name(column):
        logger.warning(f"Invalid column name in fetch_unique_values: {column}")
        return []
    
    # Get safe column name from whitelist
    safe_column = ALLOWED_COLUMNS.get(column.lower())
    if not safe_column:
        logger.warning(f"Column not found in whitelist: {column}")
        return []
    
    enum_map = {
        'mechanic': sorted(set(MECHANIC.values())),
        'utility': sorted(set(UTILITY.values())),
        'difficulty': sorted(set(DIFFICULTY.values())),
    }

    try:
        with DatabaseHandler() as db:
            if safe_column in enum_map:
                return enum_map[safe_column]

            # Force column: query DB and normalize to title case to merge variants
            if safe_column == 'force':
                query = (
                    f"SELECT DISTINCT {safe_column} AS value FROM exercises "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    f"ORDER BY {safe_column}"
                )
                rows = db.fetch_all(query)
                # Normalize to title case and dedupe (merges 'push'/'Push', 'pull'/'Pull')
                seen = set()
                values = []
                for row in rows:
                    val = row['value']
                    if val:
                        normalized = val.strip().title()
                        if normalized not in seen:
                            seen.add(normalized)
                            values.append(normalized)
                return sorted(values)

            if safe_column == 'advanced_isolated_muscles':
                rows = db.fetch_all(
                    "SELECT DISTINCT muscle FROM exercise_isolated_muscles ORDER BY muscle"
                )
                return [row['muscle'] for row in rows]

            if safe_column in {
                'primary_muscle_group',
                'secondary_muscle_group',
                'tertiary_muscle_group',
            }:
                query = (
                    f"SELECT DISTINCT {safe_column} AS value FROM exercises "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    f"ORDER BY {safe_column}"
                )
                rows = db.fetch_all(query)
                return [row['value'] for row in rows]

            if safe_column == 'equipment':
                query = (
                    f"SELECT DISTINCT TRIM({safe_column}) AS value FROM exercises "
                    f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                    f"ORDER BY value"
                )
                rows = db.fetch_all(query)
                return [row['value'] for row in rows if row.get('value')]

            query = (
                f"SELECT DISTINCT {safe_column} AS value FROM exercises "
                f"WHERE {safe_column} IS NOT NULL AND TRIM({safe_column}) <> '' "
                f"ORDER BY {safe_column}"
            )
            rows = db.fetch_all(query)
            return [row['value'] for row in rows if row.get('value')]
    except Exception as e:
        logger.error(f"Error fetching unique values for {column}: {e}", exc_info=True)
        return []

@workout_plan_bp.route("/workout_plan")
def workout_plan():
    """Render the workout plan page with filters."""
    filters = {
        "Primary Muscle Group": fetch_unique_values("primary_muscle_group"),
        "Secondary Muscle Group": fetch_unique_values("secondary_muscle_group"),
        "Tertiary Muscle Group": fetch_unique_values("tertiary_muscle_group"),
        "Advanced Isolated Muscles": fetch_unique_values("advanced_isolated_muscles"),
        "Force": fetch_unique_values("force"),
        "Equipment": fetch_unique_values("equipment"),
        "Mechanic": fetch_unique_values("mechanic"),
        "Utility": fetch_unique_values("utility"),
        "Grips": fetch_unique_values("grips"),
        "Stabilizers": fetch_unique_values("stabilizers"),
        "Synergists": fetch_unique_values("synergists"),
        "Difficulty": fetch_unique_values("difficulty")
    }
    
    # Fetch initial exercises for the dropdown
    exercises = get_exercises()
    
    return render_template("workout_plan.html", filters=filters, exercises=exercises)


@workout_plan_bp.route("/api/volume_progress")
def volume_progress():
    """Return active volume-plan progress for the current workout plan."""
    try:
        return jsonify(success_response(data=get_volume_progress()))
    except Exception:
        logger.exception("Error fetching volume progress")
        return error_response("INTERNAL_ERROR", "Failed to fetch volume progress", 500)

@workout_plan_bp.route("/add_exercise", methods=["POST"])
def add_exercise():
    """Add a new exercise to the workout plan."""
    data = None
    try:
        data = request.get_json()
        if not data:
            return error_response("VALIDATION_ERROR", "No data provided", 400)
        
        # Log request with context
        logger.info(
            "Adding exercise to workout plan",
            extra={
                'routine': data.get('routine'),
                'exercise': data.get('exercise'),
                'sets': data.get('sets'),
                'min_rep': data.get('min_rep_range'),
                'max_rep': data.get('max_rep_range'),
                'weight': data.get('weight')
            }
        )
        
        result = add_exercise_to_db(
            routine=data.get('routine'),
            exercise=data.get('exercise'),
            sets=data.get('sets'),
            min_rep_range=data.get('min_rep_range'),
            max_rep_range=data.get('max_rep_range'),
            rir=data.get('rir'),
            weight=data.get('weight'),
            rpe=data.get('rpe')
        )

        if result != "Exercise added successfully.":
            message = result or "Failed to add exercise"
            message_lower = message.lower()
            is_validation_error = (
                message_lower.startswith("error:")
                or "missing required fields" in message_lower
                or "already exists" in message_lower
            )
            error_code = "VALIDATION_ERROR" if is_validation_error else "INTERNAL_ERROR"
            status_code = 400 if is_validation_error else 500
            logger.warning(
                "Failed to add exercise",
                extra={
                    'routine': data.get('routine'),
                    'exercise': data.get('exercise'),
                    'error': message,
                    'status_code': status_code
                }
            )
            return error_response(error_code, message, status_code)
        
        logger.info(
            "Exercise added successfully",
            extra={
                'routine': data.get('routine'),
                'exercise': data.get('exercise')
            }
        )
        return jsonify(success_response(message="Exercise added successfully"))
    except (werkzeug.exceptions.BadRequest, json.JSONDecodeError) as e:
        logger.warning(
            "Invalid JSON in add_exercise request",
            extra={'error': str(e)}
        )
        return error_response("VALIDATION_ERROR", "Invalid JSON data", 400)
    except Exception as e:
        logger.exception(
            "Error adding exercise",
            extra={
                'routine': data.get('routine', 'unknown') if data else 'unknown',
                'exercise': data.get('exercise', 'unknown') if data else 'unknown'
            }
        )
        return error_response("INTERNAL_ERROR", "Failed to add exercise", 500)

@workout_plan_bp.route("/get_exercise_details/<int:exercise_id>")
def get_exercise_details(exercise_id):
    """Get details for a specific exercise."""
    query = """
    SELECT
        us.id, us.routine, us.exercise, us.sets,
        us.min_rep_range, us.max_rep_range, us.rir, us.weight,
        e.primary_muscle_group, e.secondary_muscle_group,
        e.tertiary_muscle_group, e.advanced_isolated_muscles, e.utility,
        e.grips, e.stabilizers, e.synergists
    FROM user_selection us
    JOIN exercises e ON us.exercise = e.exercise_name
    WHERE us.id = ?
    """
    try:
        with DatabaseHandler() as db:
            result = db.fetch_one(query, (exercise_id,))
            if result:
                return jsonify(success_response(data=result))
            return error_response("NOT_FOUND", "Exercise not found", 404)
    except Exception as e:
        logger.exception(f"Error fetching exercise details for id {exercise_id}")
        return error_response("INTERNAL_ERROR", "Failed to fetch exercise details", 500) 

@workout_plan_bp.route("/get_workout_plan")
def get_workout_plan():
    """Fetch the current workout plan."""
    try:
        logger.debug("Fetching workout plan")
        
        # First check if exercise_order and superset_group columns exist
        with DatabaseHandler() as db:
            # Check if columns exist using PRAGMA
            has_order = column_exists(db, 'user_selection', 'exercise_order')
            has_superset = column_exists(db, 'user_selection', 'superset_group')
            has_execution_style = column_exists(db, 'user_selection', 'execution_style')
            
            # Build dynamic column selection
            extra_cols = []
            if has_order:
                extra_cols.append("us.exercise_order")
            if has_superset:
                extra_cols.append("us.superset_group")
            if has_execution_style:
                extra_cols.append("us.execution_style")
                extra_cols.append("us.time_cap_seconds")
                extra_cols.append("us.emom_interval_seconds")
                extra_cols.append("us.emom_rounds")
            
            extra_cols_str = ", " + ", ".join(extra_cols) if extra_cols else ""
            
            # Build ORDER BY clause - supersetted exercises should be adjacent
            if has_order:
                order_by_clause = "ORDER BY us.exercise_order, us.routine, us.exercise"
            else:
                order_by_clause = "ORDER BY us.routine, us.exercise"

            query = f"""
            SELECT 
                us.id, 
                us.routine, 
                us.exercise, 
                us.sets, 
                us.min_rep_range, 
                us.max_rep_range, 
                us.rir, 
                us.rpe,
                us.weight{extra_cols_str},
                e.primary_muscle_group, 
                e.secondary_muscle_group, 
                e.tertiary_muscle_group, 
                e.advanced_isolated_muscles,
                e.utility,
                e.grips,
                e.stabilizers,
                e.synergists,
                e.movement_pattern,
                e.movement_subpattern,
                e.youtube_video_id
            FROM user_selection us
            LEFT JOIN exercises e ON us.exercise = e.exercise_name
            {order_by_clause}
            """
            
            results = db.fetch_all(query)
            
            logger.info(
                "Workout plan fetched",
                extra={
                    'exercise_count': len(results),
                    'has_exercise_order': has_order,
                    'has_superset_group': has_superset,
                    'has_execution_style': has_execution_style
                }
            )
            
            return jsonify(success_response(data=results))
            
    except Exception as e:
        logger.exception("Error fetching workout plan")
        return error_response("INTERNAL_ERROR", "Failed to fetch workout plan", 500)

@workout_plan_bp.route("/remove_exercise", methods=["POST"])
def remove_exercise():
    data = None
    try:
        data = request.get_json()
        if not data:
            return error_response("VALIDATION_ERROR", "No data provided", 400)
        
        logger.debug(f"Received data for remove_exercise: {data}")

        exercise_id = data.get("id")
        if not exercise_id or not str(exercise_id).isdigit():
            return error_response("VALIDATION_ERROR", "Invalid exercise ID", 400)

        with DatabaseHandler() as db_handler:
            # First get exercise details for logging and superset handling
            exercise_info = db_handler.fetch_one(
                "SELECT routine, exercise, superset_group FROM user_selection WHERE id = ?",
                (int(exercise_id),)
            )
            
            # Return 404 if exercise doesn't exist
            if not exercise_info:
                return error_response("NOT_FOUND", f"Exercise with ID {exercise_id} not found", 404)
            
            # If exercise is part of a superset, unlink the partner exercise
            if exercise_info and exercise_info.get('superset_group'):
                superset_group = exercise_info['superset_group']
                # Set superset_group to NULL for the partner exercise(s)
                db_handler.execute_query(
                    "UPDATE user_selection SET superset_group = NULL WHERE superset_group = ? AND id != ?",
                    (superset_group, int(exercise_id))
                )
                logger.info(
                    "Unlinked partner exercise from superset due to removal",
                    extra={
                        'superset_group': superset_group,
                        'removed_exercise_id': exercise_id
                    }
                )
            
            # Delete related workout logs to avoid foreign key constraint error
            delete_logs_query = "DELETE FROM workout_log WHERE workout_plan_id = ?"
            db_handler.execute_query(delete_logs_query, (int(exercise_id),))
            
            # Then delete the exercise from user_selection
            delete_exercise_query = "DELETE FROM user_selection WHERE id = ?"
            db_handler.execute_query(delete_exercise_query, (int(exercise_id),))

        logger.info(
            "Exercise removed from workout plan",
            extra={
                'exercise_id': exercise_id,
                'routine': exercise_info.get('routine') if exercise_info else 'unknown',
                'exercise': exercise_info.get('exercise') if exercise_info else 'unknown'
            }
        )
        return jsonify(success_response(message="Exercise removed successfully"))
    except Exception as e:
        logger.exception(
            "Error removing exercise",
            extra={'exercise_id': data.get("id", 'unknown') if data else 'unknown'}
        )
        return error_response("INTERNAL_ERROR", "Unable to remove exercise", 500)


@workout_plan_bp.route("/clear_workout_plan", methods=["POST"])
def clear_workout_plan():
    """Clear all exercises from the workout plan."""
    try:
        with DatabaseHandler() as db_handler:
            # First delete all related workout logs to avoid foreign key constraint errors
            db_handler.execute_query("DELETE FROM workout_log WHERE workout_plan_id IN (SELECT id FROM user_selection)")
            
            # Then delete all exercises from user_selection
            db_handler.execute_query("DELETE FROM user_selection")

        logger.info("Workout plan cleared - all exercises removed")
        return jsonify(success_response(message="Workout plan cleared successfully"))
    except Exception as e:
        logger.exception("Error clearing workout plan")
        return error_response("INTERNAL_ERROR", "Unable to clear workout plan", 500)


@workout_plan_bp.route("/get_routine_options")
def get_routine_options():
    """Return the structured routine options with clear hierarchy."""
    return {
        "Gym": {
            "Full Body": {
                "name": "Full Body",
                "description": "Train all major muscle groups in each session",
                "routines": ["Fullbody1", "Fullbody2", "Fullbody3"]
            },
            "Split Programs": {
                "4 Week Split": {
                    "name": "4 Week Split",
                    "description": "Rotating 4-week program for maximum variety",
                    "routines": ["A1", "B1", "A2", "B2"]
                },
                "Push Pull Legs": {
                    "name": "Push, Pull, Legs",
                    "description": "Classic 6-day split focusing on movement patterns",
                    "routines": ["Push1", "Pull1", "Legs1", "Push2", "Pull2", "Legs2"]
                },
                "Upper Lower": {
                    "name": "Upper Lower",
                    "description": "4-day split targeting upper and lower body",
                    "routines": ["Upper1", "Lower1", "Upper2", "Lower2"]
                }
            },
            "Basic Splits": {
                "2 Days Split": {
                    "name": "2 Days Split",
                    "description": "Simple alternating workout pattern",
                    "routines": ["A", "B"]
                },
                "3 Days Split": {
                    "name": "3 Days Split",
                    "description": "Three-way split for balanced training",
                    "routines": ["A", "B", "C"]
                }
            }
        },
        "Home Workout": {
            "Full Body": {
                "name": "Full Body",
                "description": "Complete body workout with minimal equipment",
                "routines": ["Fullbody1", "Fullbody2", "Fullbody3"]
            },
            "Split Programs": {
                "4 Week Split": {
                    "name": "4 Week Split",
                    "description": "Home-adapted 4-week rotation",
                    "routines": ["A1", "B1", "A2", "B2"]
                },
                "Push Pull Legs": {
                    "name": "Push, Pull, Legs",
                    "description": "Bodyweight and minimal equipment PPL",
                    "routines": ["Push1", "Pull1", "Legs1", "Push2", "Pull2", "Legs2"]
                },
                "Upper Lower": {
                    "name": "Upper Lower",
                    "description": "Home-based upper/lower split",
                    "routines": ["Upper1", "Lower1", "Upper2", "Lower2"]
                }
            },
            "Basic Splits": {
                "2 Days Split": {
                    "name": "2 Days Split",
                    "description": "Simple home workout alternation",
                    "routines": ["A", "B"]
                },
                "3 Days Split": {
                    "name": "3 Days Split",
                    "description": "Three-way home training split",
                    "routines": ["A", "B", "C"]
                }
            }
        }
    } 

@workout_plan_bp.route("/get_user_selection")
def get_user_selection():
    """Get the current user selection data."""
    try:
        query = """
        SELECT 
            us.*, 
            e.primary_muscle_group,
            e.secondary_muscle_group,
            e.tertiary_muscle_group,
            e.advanced_isolated_muscles,
            e.utility,
            e.grips,
            e.stabilizers,
            e.synergists
        FROM user_selection us
        LEFT JOIN exercises e ON us.exercise = e.exercise_name
        ORDER BY us.routine, us.exercise
        """
        with DatabaseHandler() as db:
            results = db.fetch_all(query)
            return jsonify(success_response(data=results))
    except Exception as e:
        logger.exception("Error fetching user selection")
        return error_response("INTERNAL_ERROR", "Failed to fetch user selection", 500) 

@workout_plan_bp.route("/get_exercise_info/<exercise_name>")
def get_exercise_info(exercise_name):
    """Get detailed information about a specific exercise."""
    try:
        query = """
        SELECT *
        FROM exercises
        WHERE exercise_name = ?
        """
        with DatabaseHandler() as db:
            result = db.fetch_one(query, (exercise_name,))
            if result:
                return jsonify(success_response(data=result))
            return error_response("NOT_FOUND", "Exercise not found", 404)
    except Exception as e:
        logger.exception(f"Error fetching exercise info for {exercise_name}")
        return error_response("INTERNAL_ERROR", "Failed to fetch exercise info", 500) 

@workout_plan_bp.route("/get_routine_exercises/<routine>")
def get_routine_exercises(routine):
    """Get exercises for a specific routine."""
    try:
        # First try to get exercises already in the routine
        query = """
        SELECT DISTINCT e.exercise_name
        FROM exercises e
        LEFT JOIN user_selection us ON e.exercise_name = us.exercise
        WHERE us.routine = ? OR us.routine IS NULL
        ORDER BY e.exercise_name ASC
        """
        
        with DatabaseHandler() as db:
            results = db.fetch_all(query, (routine,))
            exercises = [row['exercise_name'] for row in results if row['exercise_name']]
            
            if not exercises:
                # If no exercises found, get all available exercises
                exercises = get_exercises()
            
            logger.debug(f"Found {len(exercises)} exercises for routine {routine}")
            return jsonify(success_response(data=exercises))
            
    except Exception as e:
        logger.exception(f"Error fetching exercises for routine {routine}")
        return error_response("INTERNAL_ERROR", "Failed to fetch exercises for routine", 500) 

@workout_plan_bp.route("/update_exercise", methods=["POST"])
def update_exercise():
    """Update exercise details in the workout plan."""
    exercise_id = None
    try:
        data = request.get_json()
        if not data:
            return error_response("VALIDATION_ERROR", "No data provided", 400)
        
        exercise_id = data.get('id')
        updates = data.get('updates', {})
        
        # Validate the input data
        if not exercise_id or not updates:
            return error_response("VALIDATION_ERROR", "Missing required data", 400)
        
        logger.debug(
            "Updating exercise",
            extra={
                'exercise_id': exercise_id,
                'fields_to_update': list(updates.keys())
            }
        )
            
        # Build the update query dynamically based on provided fields
        update_fields = []
        params = []
        valid_fields = {'sets', 'min_rep_range', 'max_rep_range', 'rir', 'rpe', 'weight'}
        
        for field, value in updates.items():
            if field in valid_fields:
                update_fields.append(f"{field} = ?")
                params.append(value)
        
        if not update_fields:
            return error_response("VALIDATION_ERROR", "No valid fields to update", 400)
            
        query = f"""
            UPDATE user_selection 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        params.append(exercise_id)
        
        with DatabaseHandler() as db:
            db.execute_query(query, tuple(params))
        
        logger.info(
            "Exercise updated successfully",
            extra={
                'exercise_id': exercise_id,
                'fields_updated': list(updates.keys())
            }
        )
            
        return jsonify(success_response(message="Exercise updated successfully"))
        
    except Exception as e:
        logger.exception(
            "Error updating exercise",
            extra={'exercise_id': exercise_id if exercise_id else 'unknown'}
        )
        return error_response("INTERNAL_ERROR", "Failed to update exercise", 500)

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

@workout_plan_bp.route("/update_exercise_order", methods=["POST"])
def update_exercise_order():
    """Update the order of exercises in the workout plan."""
    try:
        data = request.get_json()
        
        if not data:
            return error_response("VALIDATION_ERROR", "No data provided", 400)
        
        with DatabaseHandler() as db:
            for entry in data:
                if not entry.get("id") or not entry.get("order"):
                    return error_response("VALIDATION_ERROR", "Invalid entry data", 400)
                db.execute_query(
                    "UPDATE user_selection SET exercise_order = ? WHERE id = ?",
                    (entry["order"], entry["id"])
                )
                
        return jsonify(success_response(message="Exercise order updated successfully"))
    except Exception as e:
        logger.exception("Error updating exercise order")
        return error_response("INTERNAL_ERROR", "Failed to update exercise order", 500)


@workout_plan_bp.route("/generate_starter_plan", methods=["POST"])
def generate_starter_plan_route():
    """
    Generate a starter workout plan based on movement patterns.
    
    Request body (JSON):
        training_days: int (1-5, default 3)
        environment: "gym" | "home" (default "gym")
        experience_level: "novice" | "intermediate" | "advanced" (default "novice")
        goal: "hypertrophy" | "strength" | "general" (default "hypertrophy")
        volume_scale: float (default 1.0, use 0.8 for heavy lifters)
        equipment_whitelist: list[str] (optional, filter available equipment)
        exclude_exercises: list[str] (optional, exercises to exclude)
        preferred_exercises: dict (optional, pattern -> list of exercise names)
        movement_restrictions: dict (optional, e.g. {"no_overhead_press": true})
        target_muscle_groups: list[str] (optional, filter to specific muscles)
        priority_muscles: list[str] (optional, muscles to prioritize with extra volume)
        beginner_consistency_mode: bool (default true for novices)
        persist: bool (default true, save to database)
        overwrite: bool (default true, replace existing routines)
    
    Returns:
        JSON with generated plan structure and metadata
    """
    try:
        data = request.get_json() or {}
        
        logger.info(
            "Generating starter plan",
            extra={
                'training_days': data.get('training_days', 3),
                'environment': data.get('environment', 'gym'),
                'experience_level': data.get('experience_level', 'novice'),
                'goal': data.get('goal', 'hypertrophy'),
                'priority_muscles': data.get('priority_muscles'),
            }
        )
        
        # Extract and validate parameters
        training_days = data.get('training_days', 3)
        if not isinstance(training_days, int) or training_days < 1 or training_days > 5:
            return error_response(
                "VALIDATION_ERROR",
                "training_days must be an integer between 1 and 5",
                400
            )
        
        environment = data.get('environment', 'gym')
        if environment not in ('gym', 'home'):
            return error_response(
                "VALIDATION_ERROR",
                "environment must be 'gym' or 'home'",
                400
            )
        
        experience_level = data.get('experience_level', 'novice')
        if experience_level not in ('novice', 'intermediate', 'advanced'):
            return error_response(
                "VALIDATION_ERROR",
                "experience_level must be 'novice', 'intermediate', or 'advanced'",
                400
            )
        
        goal = data.get('goal', 'hypertrophy')
        if goal not in ('hypertrophy', 'strength', 'general'):
            return error_response(
                "VALIDATION_ERROR",
                "goal must be 'hypertrophy', 'strength', or 'general'",
                400
            )
        
        volume_scale = data.get('volume_scale', 1.0)
        if not isinstance(volume_scale, (int, float)) or volume_scale <= 0 or volume_scale > 2:
            return error_response(
                "VALIDATION_ERROR",
                "volume_scale must be a number between 0 and 2",
                400
            )
        
        # Phase 3: Validate time budget
        time_budget_minutes = data.get('time_budget_minutes')
        if time_budget_minutes is not None:
            if not isinstance(time_budget_minutes, int) or time_budget_minutes < 15 or time_budget_minutes > 180:
                return error_response(
                    "VALIDATION_ERROR",
                    "time_budget_minutes must be between 15 and 180",
                    400
                )
        
        # Phase 3: Merge mode flag
        merge_mode = data.get('merge_mode', False)
        
        # Generate the plan
        result = generate_starter_plan(
            training_days=training_days,
            environment=environment,
            experience_level=experience_level,
            goal=goal,
            volume_scale=float(volume_scale),
            equipment_whitelist=data.get('equipment_whitelist'),
            exclude_exercises=data.get('exclude_exercises'),
            preferred_exercises=data.get('preferred_exercises'),
            movement_restrictions=data.get('movement_restrictions'),
            target_muscle_groups=data.get('target_muscle_groups'),
            priority_muscles=data.get('priority_muscles'),
            time_budget_minutes=time_budget_minutes,
            merge_mode=merge_mode,
            beginner_consistency_mode=data.get('beginner_consistency_mode', True),
            persist=data.get('persist', True),
            overwrite=data.get('overwrite', True),
        )
        
        logger.info(
            "Starter plan generated successfully",
            extra={
                'total_exercises': result.get('total_exercises'),
                'routines': list(result.get('routines', {}).keys()),
                'persisted': result.get('persisted'),
                'merge_mode': merge_mode,
                'time_budget': time_budget_minutes,
            }
        )
        
        return jsonify(success_response(data=result))
        
    except ValueError as e:
        logger.warning(f"Validation error in generate_starter_plan: {e}")
        return error_response("VALIDATION_ERROR", str(e), 400)
    except Exception as e:
        logger.exception("Error generating starter plan")
        return error_response("INTERNAL_ERROR", "Failed to generate starter plan", 500)


@workout_plan_bp.route("/get_generator_options")
def get_generator_options():
    """
    Get available options for the plan generator.
    
    Returns configuration options including environments, goals,
    experience levels, and available equipment.
    """
    try:
        # Get available equipment from database
        with DatabaseHandler() as db:
            equipment_rows = db.fetch_all(
                "SELECT DISTINCT equipment FROM exercises WHERE equipment IS NOT NULL ORDER BY equipment"
            )
            available_equipment = [row['equipment'] for row in equipment_rows if row.get('equipment')]
            
            # Get available muscle groups for priority selection
            muscle_rows = db.fetch_all(
                "SELECT DISTINCT primary_muscle_group FROM exercises WHERE primary_muscle_group IS NOT NULL ORDER BY primary_muscle_group"
            )
            available_muscles = [row['primary_muscle_group'] for row in muscle_rows if row.get('primary_muscle_group')]
        
        options = {
            "training_days": {
                "min": 1,
                "max": 3,
                "default": 2,
                "descriptions": {
                    1: "Single full-body session per week",
                    2: "A/B split (2 sessions per week)",
                    3: "A/B/C rotation (3 sessions per week)",
                }
            },
            "environments": ["gym", "home"],
            "experience_levels": ["novice", "intermediate", "advanced"],
            "goals": ["hypertrophy", "strength", "general"],
            "available_equipment": available_equipment,
            "home_equipment": ["Bodyweight", "Dumbbells", "Band", "Kettlebells", "Trx"],
            "gym_equipment": available_equipment,
            "volume_scale": {
                "min": 0.5,
                "max": 1.5,
                "default": 1.0,
                "description": "Use lower values (e.g., 0.8) for advanced/heavy lifters"
            },
            "movement_restrictions": [
                "no_overhead_press",
                "no_deadlift",
            ],
            "priority_muscles": {
                "available": available_muscles,
                "description": "Select muscle groups to prioritize with extra volume",
                "max_selections": 2,
            },
            # Phase 3: Time budget optimization
            "time_budget": {
                "min": 15,
                "max": 180,
                "default": None,
                "presets": [30, 45, 60, 75, 90],
                "description": "Target workout duration in minutes. The generator will optimize exercises and sets to fit within this time."
            },
            # Phase 3: Merge mode
            "merge_mode": {
                "default": False,
                "description": "Keep existing exercises and only add exercises for missing movement patterns. Useful for enhancing an existing plan."
            },
        }
        
        return jsonify(success_response(data=options))
        
    except Exception as e:
        logger.exception("Error fetching generator options")
        return error_response("INTERNAL_ERROR", "Failed to fetch generator options", 500)


def suggest_replacement_exercise(current_exercise, muscle, equipment, candidates, strategy="fallback"):
    """
    Suggest a replacement exercise from the candidate pool.
    
    Args:
        current_exercise: The exercise being replaced
        muscle: Primary muscle group to match
        equipment: Equipment type to match
        candidates: List of valid candidate exercise names
        strategy: "ai" for AI-based suggestion, "fallback" for deterministic
    
    Returns:
        str: Selected exercise name from candidates, or None if no valid candidate
    """
    import random
    
    if not candidates:
        return None
    
    # AI strategy placeholder - for now, use heuristic ranking
    # In the future, this could call an LLM or ML model to rank candidates
    if strategy == "ai":
        # Simple heuristic: prefer exercises with similar name patterns
        # (e.g., "Barbell Bench Press" -> prefer other "Bench" or "Press" exercises)
        current_words = set(current_exercise.lower().split())
        
        def score_candidate(candidate):
            candidate_words = set(candidate.lower().split())
            # Count overlapping words (excluding common words like "the", "with")
            common_words = {'the', 'with', 'a', 'an', 'and', 'or', 'for', 'to'}
            meaningful_current = current_words - common_words
            meaningful_candidate = candidate_words - common_words
            overlap = len(meaningful_current & meaningful_candidate)
            return overlap
        
        # Score all candidates
        scored = [(score_candidate(c), c) for c in candidates]
        scored.sort(reverse=True, key=lambda x: x[0])
        
        # Find the top score and all candidates with that score
        top_score = scored[0][0]
        top_candidates = [name for score, name in scored if score == top_score]
        
        # If only one top candidate, also include next tier to add variety
        # This prevents deterministic cycling between just 2 exercises
        if len(top_candidates) == 1 and len(scored) > 1:
            second_score = scored[1][0]
            # Include second-tier candidates if they're close enough (within 1 point)
            if top_score - second_score <= 1:
                top_candidates.extend([name for score, name in scored if score == second_score])
        
        # Randomly pick from top candidates
        return random.choice(top_candidates)
    
    # Fallback: random selection
    return random.choice(candidates)


def _fetch_current_exercise_details(db: DatabaseHandler, exercise_id: int):
    return db.fetch_one("""
        SELECT 
            us.id, us.routine, us.exercise, us.sets,
            us.min_rep_range, us.max_rep_range, us.rir, us.rpe, us.weight,
            e.primary_muscle_group, e.equipment
        FROM user_selection us
        LEFT JOIN exercises e ON us.exercise = e.exercise_name
        WHERE us.id = ?
    """, (exercise_id,))


def _build_replacement_candidates(db: DatabaseHandler, routine: str, muscle: str, equipment: str, current_exercise: str) -> list[str]:
    candidates_query = """
        SELECT exercise_name
        FROM exercises
        WHERE LOWER(primary_muscle_group) = LOWER(?)
          AND LOWER(equipment) = LOWER(?)
          AND LOWER(exercise_name) != LOWER(?)
    """
    candidate_rows = db.fetch_all(candidates_query, (muscle, equipment, current_exercise))
    candidate_names = [row['exercise_name'] for row in candidate_rows]
    
    routine_exercises_query = """
        SELECT exercise FROM user_selection WHERE routine = ?
    """
    routine_exercises = db.fetch_all(routine_exercises_query, (routine,))
    routine_exercise_names_lower = {row['exercise'].lower() for row in routine_exercises}
    
    return [c for c in candidate_names if c.lower() not in routine_exercise_names_lower]


def _perform_exercise_swap(db: DatabaseHandler, exercise_id: int, new_exercise: str):
    db.execute_query(
        "UPDATE user_selection SET exercise = ? WHERE id = ?",
        (new_exercise, exercise_id)
    )
    
    updated_row_result = db.fetch_one("""
        SELECT 
            us.id, us.routine, us.exercise, us.sets,
            us.min_rep_range, us.max_rep_range, us.rir, us.rpe, us.weight,
            e.primary_muscle_group, e.secondary_muscle_group,
            e.tertiary_muscle_group, e.advanced_isolated_muscles,
            e.utility, e.grips, e.stabilizers, e.synergists, e.equipment
        FROM user_selection us
        LEFT JOIN exercises e ON us.exercise = e.exercise_name
        WHERE us.id = ?
    """, (exercise_id,))
    
    updated_row: dict = dict(updated_row_result) if updated_row_result else {}
    
    if column_exists(db, 'user_selection', 'exercise_order'):
        order_row = db.fetch_one(
            "SELECT exercise_order FROM user_selection WHERE id = ?",
            (exercise_id,)
        )
        if order_row and order_row.get('exercise_order'):
            updated_row['exercise_order'] = order_row['exercise_order']
            
    return updated_row


@workout_plan_bp.route("/replace_exercise", methods=["POST"])
def replace_exercise():
    """
    Replace an exercise in the workout plan with another matching the same
    primary muscle group and equipment.
    
    Request body (JSON):
        id: int - user_selection.id of the exercise to replace
        strategy: "ai"|"fallback" (optional, default "fallback")
    
    Returns:
        On success: { "ok": true, "data": { "updated_row": {...} } }
        On failure: { "ok": false, "error": { "code": "...", "reason": "..." } }
    """
    data = None
    try:
        data = request.get_json()
        if not data:
            return error_response("VALIDATION_ERROR", "No data provided", 400)
        
        exercise_id = data.get("id")
        strategy = data.get("strategy", "fallback")
        
        if not exercise_id or not str(exercise_id).isdigit():
            return error_response("VALIDATION_ERROR", "Invalid exercise ID", 400)
        
        exercise_id = int(exercise_id)
        
        with DatabaseHandler() as db:
            current_row = _fetch_current_exercise_details(db, exercise_id)
            
            if not current_row:
                return error_response("NOT_FOUND", "Exercise not found in workout plan", 404, reason="not_found")
            
            current_exercise = current_row['exercise']
            routine = current_row['routine']
            muscle = current_row['primary_muscle_group']
            equipment = current_row['equipment']
            
            if not muscle or not equipment:
                logger.warning(
                    "Cannot replace exercise - missing metadata",
                    extra={
                        'exercise_id': exercise_id,
                        'exercise': current_exercise,
                        'muscle': muscle,
                        'equipment': equipment
                    }
                )
                return error_response("VALIDATION_ERROR", "Exercise is missing muscle group or equipment metadata", 400, reason="missing_metadata")
            
            valid_candidates = _build_replacement_candidates(db, routine, muscle, equipment, current_exercise)
            
            if not valid_candidates:
                return jsonify({
                    "ok": False,
                    "status": "error",
                    "message": f"No alternative exercises found for {muscle} with {equipment}",
                    "error": {
                        "code": "NO_CANDIDATES",
                        "reason": "no_candidates",
                        "message": f"No alternative exercises found for {muscle} with {equipment}"
                    }
                }), 200
            
            new_exercise = suggest_replacement_exercise(current_exercise, muscle, equipment, valid_candidates, strategy)
            
            if not new_exercise:
                return jsonify({
                    "ok": False,
                    "status": "error",
                    "message": "Failed to select replacement exercise",
                    "error": {
                        "code": "SELECTION_FAILED",
                        "reason": "selection_failed",
                        "message": "Failed to select replacement exercise"
                    }
                }), 200
            
            duplicate_check = db.fetch_one(
                "SELECT id FROM user_selection WHERE routine = ? AND LOWER(exercise) = LOWER(?)",
                (routine, new_exercise)
            )
            
            if duplicate_check:
                remaining_candidates = [c for c in valid_candidates if c.lower() != new_exercise.lower()]
                if remaining_candidates:
                    new_exercise = suggest_replacement_exercise(current_exercise, muscle, equipment, remaining_candidates, "fallback")
                    if not new_exercise:
                        return jsonify({
                            "ok": False,
                            "status": "error",
                            "message": "Failed to select replacement exercise",
                            "error": {
                                "code": "SELECTION_FAILED",
                                "reason": "selection_failed",
                                "message": "Failed to select replacement exercise"
                            }
                        }), 200
                else:
                    return jsonify({
                        "ok": False,
                        "status": "error",
                        "message": "All candidate exercises are already in this routine",
                        "error": {
                            "code": "DUPLICATE",
                            "reason": "duplicate",
                            "message": "All candidate exercises are already in this routine"
                        }
                    }), 200
            
            updated_row = _perform_exercise_swap(db, exercise_id, new_exercise)
            
            logger.info(
                "Exercise replaced successfully",
                extra={
                    'exercise_id': exercise_id,
                    'routine': routine,
                    'old_exercise': current_exercise,
                    'new_exercise': new_exercise,
                    'muscle': muscle,
                    'equipment': equipment,
                    'candidates_available': len(valid_candidates)
                }
            )
            
            remaining_options = len([c for c in valid_candidates if c.lower() != new_exercise.lower()])
            
            return jsonify(success_response(
                data={
                    "updated_row": updated_row,
                    "old_exercise": current_exercise,
                    "new_exercise": new_exercise,
                    "remaining_options": remaining_options
                },
                message=f"Replaced {current_exercise} with {new_exercise}"
            ))
            
    except Exception as e:
        logger.exception(
            "Error replacing exercise",
            extra={'exercise_id': data.get('id') if data else 'unknown'}
        )
        return error_response("INTERNAL_ERROR", "Failed to replace exercise", 500)


# =============================================================================
# SUPERSET ENDPOINTS
# =============================================================================

def _validate_superset_link_request(db: DatabaseHandler, exercise_ids: list):
    # Check if superset_group column exists
    if not column_exists(db, 'user_selection', 'superset_group'):
        return None, (
            "INTERNAL_ERROR",
            "Superset feature not available - database migration required",
            500
        )
    
    # Fetch both exercises
    exercises = db.fetch_all(
        "SELECT id, routine, exercise, superset_group FROM user_selection WHERE id IN (?, ?)",
        tuple(exercise_ids)
    )
    
    if len(exercises) != 2:
        return None, (
            "NOT_FOUND",
            "One or both exercises not found",
            404
        )
    
    ex1, ex2 = exercises[0], exercises[1]
    
    # Validate same routine
    if ex1['routine'] != ex2['routine']:
        return None, (
            "VALIDATION_ERROR",
            f"Supersets must be within the same routine. '{ex1['exercise']}' is in '{ex1['routine']}' but '{ex2['exercise']}' is in '{ex2['routine']}'",
            400
        )
    
    # Validate neither is already in a superset
    if ex1.get('superset_group'):
        return None, (
            "VALIDATION_ERROR",
            f"'{ex1['exercise']}' is already in a superset. Unlink it first.",
            400
        )
    if ex2.get('superset_group'):
        return None, (
            "VALIDATION_ERROR",
            f"'{ex2['exercise']}' is already in a superset. Unlink it first.",
            400
        )
        
    return exercises, None


def _apply_superset_link(db: DatabaseHandler, exercise_ids: list, routine_name: str):
    import time
    superset_group = f"SS-{routine_name}-{int(time.time())}"
    
    # Update both exercises with the superset group
    db.execute_query(
        "UPDATE user_selection SET superset_group = ? WHERE id IN (?, ?)",
        (superset_group, exercise_ids[0], exercise_ids[1])
    )
    
    # Fetch updated exercises with full metadata
    updated_exercises = db.fetch_all("""
        SELECT 
            us.id, us.routine, us.exercise, us.sets,
            us.min_rep_range, us.max_rep_range, us.rir, us.rpe, us.weight,
            us.superset_group,
            e.primary_muscle_group, e.secondary_muscle_group,
            e.tertiary_muscle_group, e.advanced_isolated_muscles,
            e.utility, e.grips, e.stabilizers, e.synergists
        FROM user_selection us
        LEFT JOIN exercises e ON us.exercise = e.exercise_name
        WHERE us.id IN (?, ?)
    """, tuple(exercise_ids))
    
    return superset_group, updated_exercises


@workout_plan_bp.route("/api/superset/link", methods=["POST"])
def link_superset():
    """
    Link two exercises as a superset.
    
    Request body:
        exercise_ids: List of exactly 2 exercise IDs from user_selection
    
    Validation:
        - Exactly 2 exercise IDs required
        - Both exercises must be in the same routine
        - Neither exercise can already be in a superset
    
    Returns:
        superset_group: The generated superset group identifier
        exercises: Updated exercise data for both linked exercises
    """
    try:
        data = request.get_json()
        if not data:
            return error_response("VALIDATION_ERROR", "No data provided", 400)
        
        exercise_ids = data.get('exercise_ids', [])
        
        # Validate exactly 2 exercises
        if not isinstance(exercise_ids, list) or len(exercise_ids) != 2:
            return error_response(
                "VALIDATION_ERROR",
                "Exactly 2 exercise IDs are required for a superset",
                400
            )
        
        # Validate IDs are integers
        try:
            exercise_ids = [int(eid) for eid in exercise_ids]
        except (ValueError, TypeError):
            return error_response("VALIDATION_ERROR", "Invalid exercise IDs", 400)
        
        with DatabaseHandler() as db:
            exercises, error = _validate_superset_link_request(db, exercise_ids)
            if error:
                return error_response(*error)
            
            ex1, ex2 = exercises[0], exercises[1]
            routine_name = ex1['routine']
            
            superset_group, updated_exercises = _apply_superset_link(db, exercise_ids, routine_name)
            
            logger.info(
                "Superset created",
                extra={
                    'superset_group': superset_group,
                    'routine': routine_name,
                    'exercise_1': ex1['exercise'],
                    'exercise_2': ex2['exercise']
                }
            )
            
            return jsonify(success_response(
                data={
                    "superset_group": superset_group,
                    "exercises": [dict(ex) for ex in updated_exercises]
                },
                message=f"Linked '{ex1['exercise']}' and '{ex2['exercise']}' as superset"
            ))
            
    except Exception as e:
        logger.exception("Error creating superset")
        return error_response("INTERNAL_ERROR", "Failed to create superset", 500)


@workout_plan_bp.route("/api/superset/unlink", methods=["POST"])
def unlink_superset():
    """
    Unlink exercises from a superset.
    
    Request body (one of):
        exercise_id: Single exercise ID to unlink (also unlinks partner)
        superset_group: The superset group identifier to unlink entirely
    
    Returns:
        unlinked_ids: List of exercise IDs that were unlinked
    """
    try:
        data = request.get_json()
        if not data:
            return error_response("VALIDATION_ERROR", "No data provided", 400)
        
        exercise_id = data.get('exercise_id')
        superset_group = data.get('superset_group')
        
        if not exercise_id and not superset_group:
            return error_response(
                "VALIDATION_ERROR",
                "Either exercise_id or superset_group is required",
                400
            )
        
        with DatabaseHandler() as db:
            # Check if superset_group column exists
            if not column_exists(db, 'user_selection', 'superset_group'):
                return error_response(
                    "INTERNAL_ERROR",
                    "Superset feature not available - database migration required",
                    500
                )
            
            unlinked_ids = []
            
            if exercise_id:
                # Get the superset group for this exercise
                exercise = db.fetch_one(
                    "SELECT id, exercise, superset_group FROM user_selection WHERE id = ?",
                    (int(exercise_id),)
                )
                
                if not exercise:
                    return error_response("NOT_FOUND", "Exercise not found", 404)
                
                if not exercise.get('superset_group'):
                    return error_response(
                        "VALIDATION_ERROR",
                        f"'{exercise['exercise']}' is not in a superset",
                        400
                    )
                
                superset_group = exercise['superset_group']
            
            # Get all exercises in the superset group
            superset_exercises = db.fetch_all(
                "SELECT id, exercise FROM user_selection WHERE superset_group = ?",
                (superset_group,)
            )
            
            if not superset_exercises:
                return error_response(
                    "NOT_FOUND",
                    f"No exercises found with superset group '{superset_group}'",
                    404
                )
            
            # Unlink all exercises in the superset
            db.execute_query(
                "UPDATE user_selection SET superset_group = NULL WHERE superset_group = ?",
                (superset_group,)
            )
            
            unlinked_ids = [ex['id'] for ex in superset_exercises]
            unlinked_names = [ex['exercise'] for ex in superset_exercises]
            
            logger.info(
                "Superset unlinked",
                extra={
                    'superset_group': superset_group,
                    'unlinked_ids': unlinked_ids,
                    'exercises': unlinked_names
                }
            )
            
            return jsonify(success_response(
                data={"unlinked_ids": unlinked_ids},
                message=f"Unlinked superset: {', '.join(unlinked_names)}"
            ))
            
    except Exception as e:
        logger.exception("Error unlinking superset")
        return error_response("INTERNAL_ERROR", "Failed to unlink superset", 500)


# ==================== Phase 3: Execution Styles ====================

def _validate_and_normalize_execution_params(data: dict):
    if not data:
        return None, ("VALIDATION_ERROR", "No data provided", 400)
    
    exercise_id = data.get('exercise_id')
    execution_style = data.get('execution_style', 'standard')
    time_cap_seconds = data.get('time_cap_seconds')
    emom_interval_seconds = data.get('emom_interval_seconds')
    emom_rounds = data.get('emom_rounds')
    
    # Validate exercise_id
    if not exercise_id or not str(exercise_id).isdigit():
        return None, ("VALIDATION_ERROR", "Invalid exercise ID", 400)
    
    # Validate execution_style
    valid_styles = {'standard', 'amrap', 'emom'}
    if execution_style not in valid_styles:
        return None, (
            "VALIDATION_ERROR",
            f"Invalid execution style. Must be one of: {', '.join(valid_styles)}",
            400
        )
    
    # Apply defaults and validate based on style
    if execution_style == 'amrap':
        time_cap_seconds = time_cap_seconds if time_cap_seconds else 60
        if not isinstance(time_cap_seconds, int) or time_cap_seconds < 10 or time_cap_seconds > 600:
            return None, (
                "VALIDATION_ERROR",
                "time_cap_seconds must be between 10 and 600 seconds",
                400
            )
        emom_interval_seconds = None
        emom_rounds = None
    elif execution_style == 'emom':
        emom_interval_seconds = emom_interval_seconds if emom_interval_seconds else 60
        emom_rounds = emom_rounds if emom_rounds else 5
        
        if not isinstance(emom_interval_seconds, int) or emom_interval_seconds < 15 or emom_interval_seconds > 180:
            return None, (
                "VALIDATION_ERROR",
                "emom_interval_seconds must be between 15 and 180 seconds",
                400
            )
        if not isinstance(emom_rounds, int) or emom_rounds < 1 or emom_rounds > 20:
            return None, (
                "VALIDATION_ERROR",
                "emom_rounds must be between 1 and 20",
                400
            )
        time_cap_seconds = None
    else:  # standard
        time_cap_seconds = None
        emom_interval_seconds = None
        emom_rounds = None

    return {
        'exercise_id': int(exercise_id),
        'execution_style': execution_style,
        'time_cap_seconds': time_cap_seconds,
        'emom_interval_seconds': emom_interval_seconds,
        'emom_rounds': emom_rounds
    }, None


def _update_execution_style_db(db: DatabaseHandler, params: dict):
    # Check if columns exist
    cols = db.fetch_all("PRAGMA table_info(user_selection)")
    col_names = {row['name'] for row in cols}
    
    if 'execution_style' not in col_names:
        return None, (
            "INTERNAL_ERROR",
            "Execution style feature not available - database migration required",
            500
        )
    
    exercise_id = params['exercise_id']
    
    # Verify exercise exists
    exercise = db.fetch_one(
        "SELECT id, exercise, routine FROM user_selection WHERE id = ?",
        (exercise_id,)
    )
    
    if not exercise:
        return None, ("NOT_FOUND", "Exercise not found", 404)
    
    # Update execution style
    db.execute_query(
        """
        UPDATE user_selection 
        SET execution_style = ?,
            time_cap_seconds = ?,
            emom_interval_seconds = ?,
            emom_rounds = ?
        WHERE id = ?
        """,
        (
            params['execution_style'],
            params['time_cap_seconds'],
            params['emom_interval_seconds'],
            params['emom_rounds'],
            exercise_id
        )
    )
    
    # Fetch updated row
    updated = db.fetch_one(
        """
        SELECT id, routine, exercise, execution_style, 
               time_cap_seconds, emom_interval_seconds, emom_rounds
        FROM user_selection WHERE id = ?
        """,
        (exercise_id,)
    )
    
    return {'exercise': exercise, 'updated': updated}, None


@workout_plan_bp.route("/api/execution_style", methods=["POST"])
def set_execution_style():
    """
    Set the execution style for an exercise (AMRAP, EMOM, or standard).
    
    Request body (JSON):
        exercise_id: int - user_selection.id of the exercise
        execution_style: "standard" | "amrap" | "emom"
        time_cap_seconds: int (optional, for AMRAP - default 60)
        emom_interval_seconds: int (optional, for EMOM - default 60)
        emom_rounds: int (optional, for EMOM - default 5)
    
    Returns:
        Updated exercise data
    """
    try:
        data = request.get_json()
        params, error = _validate_and_normalize_execution_params(data)
        if error:
            return error_response(*error)
        
        with DatabaseHandler() as db:
            result, db_error = _update_execution_style_db(db, params)
            if db_error:
                return error_response(*db_error)
            
            exercise = result['exercise']
            updated = result['updated']
            
            logger.info(
                "Execution style updated",
                extra={
                    'exercise_id': params['exercise_id'],
                    'exercise': exercise['exercise'],
                    'execution_style': params['execution_style'],
                    'time_cap_seconds': params['time_cap_seconds'],
                    'emom_interval_seconds': params['emom_interval_seconds'],
                    'emom_rounds': params['emom_rounds']
                }
            )
            
            return jsonify(success_response(
                data=dict(updated) if updated else None,
                message=f"Set '{exercise['exercise']}' to {params['execution_style'].upper()} style"
            ))
            
    except Exception as e:
        logger.exception("Error setting execution style")
        return error_response("INTERNAL_ERROR", "Failed to set execution style", 500)


@workout_plan_bp.route("/api/execution_style_options")
def get_execution_style_options():
    """
    Get available execution style options with descriptions.
    
    Returns options and tooltips for AMRAP and EMOM modes.
    """
    options = {
        "styles": {
            "standard": {
                "name": "Standard",
                "description": "Traditional set-based training with rest between sets",
                "icon": "fa-dumbbell"
            },
            "amrap": {
                "name": "AMRAP",
                "full_name": "As Many Reps As Possible",
                "description": "Perform as many reps as possible within a time cap. Great for conditioning and metabolic stress.",
                "icon": "fa-stopwatch",
                "defaults": {
                    "time_cap_seconds": 60
                },
                "tooltip": "Set a time limit and perform maximum quality reps. Rest is minimal. Focus on form over speed."
            },
            "emom": {
                "name": "EMOM",
                "full_name": "Every Minute On the Minute",
                "description": "Start a set at the beginning of each minute. Remaining time is rest. Great for pacing and density.",
                "icon": "fa-clock",
                "defaults": {
                    "emom_interval_seconds": 60,
                    "emom_rounds": 5
                },
                "tooltip": "At the start of each interval, perform your target reps. Rest until the next interval begins. Builds work capacity."
            }
        },
        "limits": {
            "time_cap_seconds": {"min": 10, "max": 600},
            "emom_interval_seconds": {"min": 15, "max": 180},
            "emom_rounds": {"min": 1, "max": 20}
        }
    }
    
    return jsonify(success_response(data=options))


# ==================== Phase 3: Superset Auto-Suggestion ====================

def _group_exercises_by_routine(exercises: list) -> dict:
    routines = {}
    for ex in exercises:
        r = ex['routine']
        if r not in routines:
            routines[r] = []
        routines[r].append(ex)
    return routines


def _find_antagonist_pairings(routine_name: str, routine_exercises: list) -> list:
    suggestions = []
    
    # Skip exercises already in supersets
    available = [
        ex for ex in routine_exercises 
        if not ex.get('superset_group')
    ]
    
    paired = set()
    
    for i, ex1 in enumerate(available):
        if ex1['id'] in paired:
            continue
        
        muscle1 = (ex1.get('primary_muscle_group') or '').lower()
        if not muscle1:
            continue
        
        best_partner = None
        best_reason = None
        
        for j, ex2 in enumerate(available):
            if i == j or ex2['id'] in paired:
                continue
            
            muscle2 = (ex2.get('primary_muscle_group') or '').lower()
            if not muscle2:
                continue
            
            # Check for antagonist pairing
            antagonists = ANTAGONIST_PAIRS.get(muscle1, [])
            if muscle2 in antagonists or any(m in muscle2 for m in antagonists):
                # Calculate pairing score
                best_partner = ex2
                best_reason = f"Antagonist pair: {muscle1.title()} / {muscle2.title()} - allows one muscle to rest while the other works"
                break
        
        if best_partner:
            suggestions.append({
                "routine": routine_name,
                "exercise_1": {
                    "id": ex1['id'],
                    "name": ex1['exercise'],
                    "muscle": muscle1.title()
                },
                "exercise_2": {
                    "id": best_partner['id'],
                    "name": best_partner['exercise'],
                    "muscle": (best_partner.get('primary_muscle_group') or '').title()
                },
                "reason": best_reason,
                "benefit": "Saves time without compromising performance"
            })
            paired.add(ex1['id'])
            paired.add(best_partner['id'])
            
    return suggestions


@workout_plan_bp.route("/api/superset/suggest", methods=["GET"])
def suggest_supersets():
    """
    Analyze the workout plan and suggest optimal superset pairings.
    
    Suggestions are based on:
    1. Antagonist muscle pairing (e.g., biceps/triceps, chest/back, quads/hamstrings)
    2. Non-competing muscle groups to minimize fatigue interference
    3. Time efficiency optimization
    
    Returns:
        List of suggested superset pairings with reasoning
    """
    try:
        routine = request.args.get('routine')
        
        with DatabaseHandler() as db:
            # Fetch current workout plan
            query = """
                SELECT 
                    us.id, us.routine, us.exercise, us.superset_group,
                    e.primary_muscle_group, e.secondary_muscle_group
                FROM user_selection us
                LEFT JOIN exercises e ON us.exercise = e.exercise_name
            """
            params = []
            
            if routine:
                query += " WHERE us.routine = ?"
                params.append(routine)
            
            query += " ORDER BY us.routine, us.exercise_order"
            
            exercises = db.fetch_all(query, params if params else None)
            
            if not exercises:
                return jsonify(success_response(
                    data={"suggestions": [], "message": "No exercises found in workout plan"}
                ))
            
            routines = _group_exercises_by_routine(exercises)
            suggestions = []
            
            for routine_name, routine_exercises in routines.items():
                suggestions.extend(_find_antagonist_pairings(routine_name, routine_exercises))
            
            logger.info(
                "Superset suggestions generated",
                extra={
                    'routine_filter': routine,
                    'suggestion_count': len(suggestions)
                }
            )
            
            return jsonify(success_response(data={
                "suggestions": suggestions,
                "total_pairs": len(suggestions)
            }))
            
    except Exception as e:
        logger.exception("Error generating superset suggestions")
        return error_response("INTERNAL_ERROR", "Failed to generate superset suggestions", 500)
