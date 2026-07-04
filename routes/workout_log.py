from flask import Blueprint, render_template, request, jsonify
from utils.database import DatabaseHandler
from utils.workout_log import (
    check_progression,
    get_weight_progression_indicator,
    get_workout_logs,
    is_assisted_bodyweight_exercise,
)
from utils.errors import success_response, error_response
from utils.export_utils import create_excel_workbook, generate_timestamped_filename
from utils.logger import get_logger
from utils.strength_calibration import (
    recompute_calibration_after_log,
    update_calibration_for_exercise,
)
from utils.workout_validation import UNSET, validate_workout_bounds

workout_log_bp = Blueprint('workout_log', __name__)
logger = get_logger()

@workout_log_bp.route("/workout_log")
def workout_log():
    """Render the workout log page."""
    try:
        workout_logs = get_workout_logs()
        return render_template(
            "workout_log.html",
            page_title="Workout Log",
            workout_logs=workout_logs,
            enumerate=enumerate,
            check_progression=check_progression,
            get_weight_progression_indicator=get_weight_progression_indicator,
            is_assisted_bodyweight_exercise=is_assisted_bodyweight_exercise,
        )
    except Exception as e:
        logger.exception("Error loading workout log page")
        return error_response("INTERNAL_ERROR", "Unable to load workout log.", 500)

@workout_log_bp.route("/update_workout_log", methods=["POST"])
def update_workout_log():
    """Update workout log entry."""
    try:
        data = request.get_json()
        log_id = data.get("id")
        updates = data.get("updates", {})

        if not log_id:
            return error_response("VALIDATION_ERROR", "Log ID is required", 400)

        valid_fields = {
            "scored_weight", "scored_min_reps", "scored_max_reps", 
            "scored_rir", "scored_rpe", "last_progression_date"
        }

        valid_updates = {k: v for k, v in updates.items() if k in valid_fields}

        if not valid_updates:
            return error_response("VALIDATION_ERROR", "No valid fields to update", 400)

        set_clause = ", ".join(f"{k} = ?" for k in valid_updates.keys())
        query = f"UPDATE workout_log SET {set_clause} WHERE id = ?"
        params = list(valid_updates.values()) + [log_id]
        scored_changed = any(k.startswith("scored_") for k in valid_updates)

        calibration = None
        with DatabaseHandler() as db:
            # Check if log entry exists
            check_query = (
                "SELECT id, exercise, scored_min_reps, scored_max_reps "
                "FROM workout_log WHERE id = ?"
            )
            existing = db.fetch_one(check_query, (log_id,))
            if not existing:
                return error_response("NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404)

            min_reps = max_reps = UNSET
            if "scored_min_reps" in valid_updates or "scored_max_reps" in valid_updates:
                min_reps = valid_updates.get("scored_min_reps", existing["scored_min_reps"])
                max_reps = valid_updates.get("scored_max_reps", existing["scored_max_reps"])
            bounds_error = validate_workout_bounds(
                weight=valid_updates.get("scored_weight", UNSET),
                rir=valid_updates.get("scored_rir", UNSET),
                min_reps=min_reps,
                max_reps=max_reps,
                allow_null=True,
            )
            if bounds_error:
                return error_response("VALIDATION_ERROR", bounds_error, 400)

            db.execute_query(query, params)

            # Recompute learned calibration from the updated logs, reusing the
            # open handler (plan §"DatabaseHandler Requirement"). Guarded so a
            # calibration failure never rolls back the user's log write. Only a
            # scored change is a "meaningful log update" worth notifying about
            # (plan §"Notifications").
            try:
                summary = recompute_calibration_after_log(existing["exercise"], db=db)
                if scored_changed:
                    calibration = summary
            except Exception:
                logger.exception(
                    "Calibration recompute failed for log %s; log update preserved", log_id
                )

        logger.info(f"Updated workout log {log_id}")
        return jsonify(success_response(
            data={"calibration": calibration} if calibration else None,
            message="Workout log updated successfully",
        ))
    except Exception as e:
        logger.exception("Error updating workout log")
        return error_response("INTERNAL_ERROR", "Failed to update workout log", 500)

@workout_log_bp.route('/delete_workout_log', methods=['POST'])
def delete_workout_log():
    try:
        data = request.get_json()
        log_id = data.get('id')
        
        if not log_id:
            return error_response("VALIDATION_ERROR", "No log ID provided", 400)
        
        with DatabaseHandler() as db:
            # Check if log entry exists
            check_query = "SELECT id, exercise FROM workout_log WHERE id = ?"
            existing = db.fetch_one(check_query, (log_id,))
            if not existing:
                return error_response("NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404)

            query = "DELETE FROM workout_log WHERE id = ?"
            db.execute_query(query, (log_id,))

            # Recompute against the remaining logs; clears the calibration row
            # when the deleted set was the last usable one (invalidate-on-delete).
            try:
                update_calibration_for_exercise(existing["exercise"], db=db)
            except Exception:
                logger.exception(
                    "Calibration recompute failed after deleting log %s", log_id
                )

        logger.info(f"Deleted workout log {log_id}")
        return jsonify(success_response(message="Log entry deleted successfully"))
        
    except Exception as e:
        logger.exception(f"Error deleting workout log")
        return error_response("INTERNAL_ERROR", "Failed to delete workout log", 500)

@workout_log_bp.route("/update_progression_date", methods=["POST"])
def update_progression_date():
    """Update the last progression date for a workout log entry."""
    try:
        data = request.get_json()
        log_id = data.get("id")
        new_date = data.get("date")

        if not log_id or not new_date:
            return error_response("VALIDATION_ERROR", "Log ID and date are required", 400)

        query = "UPDATE workout_log SET last_progression_date = ? WHERE id = ?"
        with DatabaseHandler() as db:
            # Check if log entry exists
            check_query = "SELECT id FROM workout_log WHERE id = ?"
            existing = db.fetch_one(check_query, (log_id,))
            if not existing:
                return error_response("NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404)
            
            db.execute_query(query, (new_date, log_id))

        logger.info(f"Updated progression date for log {log_id}")
        return jsonify(success_response(message="Progression date updated successfully"))
    except Exception as e:
        logger.exception("Error updating progression date")
        return error_response("INTERNAL_ERROR", "Failed to update progression date", 500) 

@workout_log_bp.route("/check_progression/<int:log_id>")
def check_progression_route(log_id):
    """Check if progressive overload was achieved for a specific log entry."""
    try:
        query = """
        SELECT 
            exercise, planned_min_reps, planned_max_reps, planned_weight,
            scored_min_reps, scored_max_reps, scored_weight,
            planned_rir, scored_rir,
            planned_rpe, scored_rpe
        FROM workout_log 
        WHERE id = ?
        """
        with DatabaseHandler() as db:
            log = db.fetch_one(query, (log_id,))
            if not log:
                return error_response("NOT_FOUND", "Log entry not found", 404)

            is_progressive = check_progression(log)

            return jsonify(success_response(data={
                "is_progressive": is_progressive,
                "status": "Achieved" if is_progressive else "Pending"
            }))

    except Exception as e:
        logger.exception("Error checking progression")
        return error_response("INTERNAL_ERROR", "Failed to check progression status", 500)

@workout_log_bp.route("/get_workout_logs")
def get_logs():
    """Get all workout logs."""
    try:
        query = """
        SELECT
            wl.*,
            us.routine as plan_routine,
            us.exercise as plan_exercise,
            e.youtube_video_id,
            e.media_path
        FROM workout_log wl
        LEFT JOIN user_selection us ON wl.workout_plan_id = us.id
        LEFT JOIN exercises e ON wl.exercise = e.exercise_name COLLATE NOCASE
        ORDER BY wl.created_at DESC
        """
        with DatabaseHandler() as db:
            results = db.fetch_all(query)
            return jsonify(success_response(data=results))
    except Exception as e:
        logger.exception("Error fetching workout logs")
        return error_response("INTERNAL_ERROR", "Failed to fetch workout logs", 500)

@workout_log_bp.route('/export_workout_log')
def export_workout_log():
    try:
        logs = get_workout_logs()
        if not logs:
            return error_response("NOT_FOUND", "No workout logs found to export", 404)

        filename = generate_timestamped_filename('workout_log')
        logger.info(f"Exporting {len(logs)} workout log rows to {filename}")
        return create_excel_workbook({'Workout Log': logs}, filename)

    except Exception as e:
        logger.exception("Error exporting workout log")
        return error_response("INTERNAL_ERROR", "Failed to export workout log", 500)

@workout_log_bp.route('/clear_workout_log', methods=['POST'])
def clear_workout_log():
    """Clear all entries from the workout log."""
    try:
        with DatabaseHandler() as db:
            # Count entries before clearing for the response message
            count_query = "SELECT COUNT(*) as count FROM workout_log"
            result = db.fetch_one(count_query)
            entry_count = result['count'] if result else 0
            
            if entry_count == 0:
                return jsonify(success_response(message="Workout log is already empty"))
            
            # Delete all entries
            delete_query = "DELETE FROM workout_log"
            db.execute_query(delete_query)
            
            logger.info(f"Cleared {entry_count} entries from workout log")
            return jsonify(success_response(
                message=f"Successfully cleared {entry_count} entries from workout log"
            ))
            
    except Exception as e:
        logger.exception("Error clearing workout log")
        return error_response("INTERNAL_ERROR", "Failed to clear workout log", 500)
