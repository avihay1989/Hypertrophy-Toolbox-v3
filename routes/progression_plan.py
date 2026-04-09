from flask import Blueprint, render_template, request, jsonify, redirect
from datetime import datetime

from utils.database import DatabaseHandler
from utils.errors import error_response, is_xhr_request, success_response
from utils.logger import get_logger
from utils.progression_plan import (
    get_exercise_history,
    generate_progression_suggestions,
    save_progression_goal
)

progression_plan_bp = Blueprint('progression_plan', __name__)
logger = get_logger()
VALID_GOAL_TYPES = {"weight", "reps", "sets", "technique"}
CURRENT_VALUE_GOAL_TYPES = {"weight", "reps", "sets"}


def _get_json_payload(route_name):
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        logger.warning("Invalid JSON in %s request", route_name)
        raise ValueError("Invalid JSON data")
    return data


def _require_text_field(data, field_name):
    value = data.get(field_name)
    if value is None:
        raise ValueError(f"{field_name} is required")

    normalized_value = str(value).strip()
    if not normalized_value:
        raise ValueError(f"{field_name} is required")

    return normalized_value


def _normalize_is_novice(value):
    if value is None:
        return True

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False

    return bool(value)


def _parse_numeric_goal_value(value, field_name):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc


def _normalize_progression_goal_payload(data):
    exercise = (data.get("exercise") or "").strip()
    goal_type = (data.get("goal_type") or "").strip().lower()
    goal_date = (data.get("goal_date") or "").strip()

    if not exercise or not goal_type or not goal_date:
        raise ValueError("Missing required data")

    if goal_type not in VALID_GOAL_TYPES:
        raise ValueError("Invalid goal type")

    try:
        normalized_goal_date = datetime.strptime(goal_date, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("goal_date must use YYYY-MM-DD format") from exc

    current_value = _parse_numeric_goal_value(data.get("current_value"), "current_value")
    target_value = _parse_numeric_goal_value(data.get("target_value"), "target_value")

    if goal_type == "technique":
        current_value = None
        target_value = None
    elif current_value is None or target_value is None:
        raise ValueError("current_value and target_value are required")

    return {
        "exercise": exercise,
        "goal_type": goal_type,
        "current_value": current_value,
        "target_value": target_value,
        "goal_date": normalized_goal_date,
    }


@progression_plan_bp.route("/progression")
def progression_plan():
    """Render the progression plan page."""
    try:
        with DatabaseHandler() as db:
            # Get unique exercises from user_selection (the workout plan)
            query = """
            SELECT DISTINCT exercise, routine
            FROM user_selection
            ORDER BY routine, exercise
            """
            exercises = db.fetch_all(query)
            logger.debug("Loaded progression exercises: %s", exercises)
            
            # Get existing progression goals
            goals_query = """
            SELECT * FROM progression_goals
            WHERE completed = 0
            ORDER BY goal_date
            """
            goals = db.fetch_all(goals_query)
            logger.debug("Loaded progression goals: %s", goals)
            
        return render_template(
            "progression_plan.html",
            exercises=exercises,
            goals=goals
        )
    except Exception as e:
        logger.exception("Error in progression_plan: %s", str(e))
        return render_template("error.html", message="Unable to load progression plan."), 500


@progression_plan_bp.route("/get_exercise_suggestions", methods=["POST"])
def get_suggestions():
    """
    Get progression suggestions for a specific exercise using double progression methodology.
    
    Request JSON:
        exercise: str - Exercise name
        is_novice: bool (optional) - Whether user is a novice (default True, more conservative)
    
    Returns:
        List of suggestion objects with type, title, description, action, priority
    """
    data = None
    try:
        data = _get_json_payload("get_exercise_suggestions")
        exercise = _require_text_field(data, "exercise")
        is_novice = _normalize_is_novice(data.get("is_novice"))

        history = get_exercise_history(exercise)

        if not history:
            suggestions = [{
                "type": "technique",
                "title": "Start Training",
                "description": f"Begin training {exercise} to generate progression suggestions.",
                "action": "Set initial goals",
                "priority": "high"
            }]
        else:
            suggestions = generate_progression_suggestions(history, is_novice=is_novice)

        return jsonify(success_response(data=suggestions))
    except ValueError as exc:
        logger.warning(
            "Validation error in get_suggestions",
            extra={
                "error": str(exc),
                "exercise": data.get("exercise") if isinstance(data, dict) else None,
            },
        )
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception(
            "Error in get_suggestions",
            extra={"exercise": data.get("exercise") if isinstance(data, dict) else None},
        )
        return error_response("INTERNAL_ERROR", "Failed to get exercise suggestions", 500)


@progression_plan_bp.route("/save_progression_goal", methods=["POST"])
def save_goal():
    """Save a new progression goal."""
    data = None
    try:
        if request.is_json:
            data = request.get_json(silent=True)
            if data is None or not isinstance(data, dict):
                logger.warning("Invalid JSON in save_progression_goal request")
                return error_response("VALIDATION_ERROR", "Invalid JSON data", 400)
        else:
            data = request.form.to_dict()

        if not data:
            return error_response("VALIDATION_ERROR", "No data provided", 400)

        normalized_data = _normalize_progression_goal_payload(data)
        goal_id = save_progression_goal(normalized_data)

        logger.info(
            "Saved progression goal",
            extra={
                "exercise": normalized_data["exercise"],
                "goal_type": normalized_data["goal_type"],
                "goal_id": goal_id,
            },
        )

        if is_xhr_request():
            return jsonify(
                success_response(
                    data={"goal_id": goal_id},
                    message="Goal saved successfully",
                )
            )

        return redirect('/progression')
    except ValueError as exc:
        logger.warning(
            "Validation error in save_progression_goal",
            extra={
                "error": str(exc),
                "exercise": data.get("exercise") if isinstance(data, dict) else None,
                "goal_type": data.get("goal_type") if isinstance(data, dict) else None,
            },
        )
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception as e:
        logger.exception(
            "Error saving progression goal",
            extra={
                "exercise": data.get("exercise") if isinstance(data, dict) else None,
                "goal_type": data.get("goal_type") if isinstance(data, dict) else None,
            },
        )
        return error_response("INTERNAL_ERROR", "Failed to save progression goal", 500)


@progression_plan_bp.route("/delete_progression_goal/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    try:
        with DatabaseHandler() as db:
            # Check if goal exists
            query = "SELECT * FROM progression_goals WHERE id = ?"
            goal = db.fetch_one(query, (goal_id,))

            if not goal:
                return error_response("NOT_FOUND", "Goal not found", 404)

            # Delete the goal
            query = "DELETE FROM progression_goals WHERE id = ?"
            db.execute_query(query, (goal_id,))

        logger.info("Deleted progression goal", extra={"goal_id": goal_id})
        return jsonify(success_response(message="Goal deleted successfully"))
    except Exception:
        logger.exception("Error deleting progression goal", extra={"goal_id": goal_id})
        return error_response("INTERNAL_ERROR", "Failed to delete progression goal", 500)


@progression_plan_bp.route("/complete_progression_goal/<int:goal_id>", methods=["POST"])
def complete_goal(goal_id):
    """Mark a progression goal as completed."""
    try:
        with DatabaseHandler() as db:
            # Check if goal exists
            query = "SELECT * FROM progression_goals WHERE id = ?"
            goal = db.fetch_one(query, (goal_id,))

            if not goal:
                return error_response("NOT_FOUND", "Goal not found", 404)

            # Mark the goal as completed
            query = "UPDATE progression_goals SET completed = 1 WHERE id = ?"
            db.execute_query(query, (goal_id,))

        logger.info("Completed progression goal", extra={"goal_id": goal_id})
        return jsonify(success_response(message="Goal marked as completed"))
    except Exception:
        logger.exception("Error completing progression goal", extra={"goal_id": goal_id})
        return error_response("INTERNAL_ERROR", "Failed to complete progression goal", 500)


@progression_plan_bp.route("/get_current_value", methods=["POST"])
def get_current_value():
    """Get the current value for an exercise based on recent workout history."""
    data = None
    try:
        data = _get_json_payload("get_current_value")
        exercise = _require_text_field(data, "exercise")
        goal_type = (data.get("goal_type") or "").strip().lower()
        if not goal_type:
            raise ValueError("goal_type is required")

        logger.debug(
            "Fetching current value for exercise=%s goal_type=%s",
            exercise,
            goal_type,
        )

        with DatabaseHandler() as db:
            if goal_type not in CURRENT_VALUE_GOAL_TYPES:
                return jsonify(success_response(data={"current_value": "N/A"}))

            if goal_type == 'weight':
                # Get maximum weight ever achieved for this exercise
                # Use scored_weight if available, otherwise fall back to planned_weight
                query = """
                    SELECT MAX(COALESCE(scored_weight, planned_weight)) as current_value 
                    FROM workout_log 
                    WHERE exercise = ?
                """
            elif goal_type == 'reps':
                # Get maximum reps ever achieved for this exercise
                # Use scored_max_reps if available, otherwise fall back to planned_max_reps
                query = """
                    SELECT MAX(COALESCE(scored_max_reps, planned_max_reps)) as current_value 
                    FROM workout_log 
                    WHERE exercise = ?
                """
            elif goal_type == 'sets':
                # Get most recent sets count for this exercise
                query = """
                    SELECT planned_sets as current_value 
                    FROM workout_log 
                    WHERE exercise = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """

            logger.debug("Executing current value query for exercise=%s", exercise)
            result = db.fetch_one(query, (exercise,))
            logger.debug("Current value query result: %s", result)

            current_value = result['current_value'] if result and result['current_value'] else 0
            logger.debug("Returning current_value=%s", current_value)

            return jsonify(success_response(data={"current_value": current_value}))
    except ValueError as exc:
        logger.warning(
            "Validation error in get_current_value",
            extra={
                "error": str(exc),
                "exercise": data.get("exercise") if isinstance(data, dict) else None,
                "goal_type": data.get("goal_type") if isinstance(data, dict) else None,
            },
        )
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception(
            "Error in get_current_value",
            extra={
                "exercise": data.get("exercise") if isinstance(data, dict) else None,
                "goal_type": data.get("goal_type") if isinstance(data, dict) else None,
            },
        )
        return error_response("INTERNAL_ERROR", "Failed to fetch current value", 500)
