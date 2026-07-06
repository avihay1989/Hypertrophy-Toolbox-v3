"""Workout-log mutation and calibration-trigger orchestration.

Extracted from ``routes/workout_log.py`` (WP1.5). Routes parse/validate HTTP
input and shape responses; the persistence writes, bounds checks, and the
learned-calibration recompute/invalidate orchestration live here.

Behaviour is identical to the previous in-route implementation: the same
``DatabaseHandler`` usage, the same calibration functions called in the same
order under the same conditions, and the same guard so a calibration failure
never rolls back the user's log write.
"""
from __future__ import annotations

from typing import Any, Optional

from utils.database import DatabaseHandler
from utils.logger import get_logger
from utils.strength_calibration import (
    recompute_calibration_after_log,
    update_calibration_for_exercise,
)
from utils.workout_validation import UNSET, validate_workout_bounds

logger = get_logger()

VALID_UPDATE_FIELDS = {
    "scored_weight", "scored_min_reps", "scored_max_reps",
    "scored_rir", "scored_rpe", "last_progression_date",
}


class WorkoutLogServiceError(Exception):
    """A user-facing failure the route maps straight to ``error_response()``.

    Carries the exact ``code``/``message``/``status_code`` the route emitted
    inline before the extraction, so response envelopes are unchanged.
    """

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def update_log_entry(log_id: Any, updates: dict) -> Optional[dict]:
    """Apply a workout-log update and recompute learned calibration.

    Returns the calibration summary to surface (only after a *scored* change)
    or ``None``. Raises :class:`WorkoutLogServiceError` for the no-valid-fields,
    not-found, and bounds-validation outcomes.
    """
    valid_updates = {k: v for k, v in updates.items() if k in VALID_UPDATE_FIELDS}

    if not valid_updates:
        raise WorkoutLogServiceError("VALIDATION_ERROR", "No valid fields to update", 400)

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
            raise WorkoutLogServiceError(
                "NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404
            )

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
            raise WorkoutLogServiceError("VALIDATION_ERROR", bounds_error, 400)

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
    return calibration


def delete_log_entry(log_id: Any) -> None:
    """Delete a workout-log entry and invalidate/recompute its calibration.

    Raises :class:`WorkoutLogServiceError` (``NOT_FOUND``) when the entry is
    missing.
    """
    with DatabaseHandler() as db:
        # Check if log entry exists
        check_query = "SELECT id, exercise FROM workout_log WHERE id = ?"
        existing = db.fetch_one(check_query, (log_id,))
        if not existing:
            raise WorkoutLogServiceError(
                "NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404
            )

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


def update_progression_date_entry(log_id: Any, new_date: Any) -> None:
    """Update the last progression date for a workout-log entry.

    Raises :class:`WorkoutLogServiceError` (``NOT_FOUND``) when the entry is
    missing.
    """
    query = "UPDATE workout_log SET last_progression_date = ? WHERE id = ?"
    with DatabaseHandler() as db:
        # Check if log entry exists
        check_query = "SELECT id FROM workout_log WHERE id = ?"
        existing = db.fetch_one(check_query, (log_id,))
        if not existing:
            raise WorkoutLogServiceError(
                "NOT_FOUND", f"Workout log entry with ID {log_id} not found", 404
            )

        db.execute_query(query, (new_date, log_id))

    logger.info(f"Updated progression date for log {log_id}")


def clear_all_logs() -> int:
    """Delete every workout-log entry. Returns the number of rows removed."""
    with DatabaseHandler() as db:
        # Count entries before clearing for the response message
        count_query = "SELECT COUNT(*) as count FROM workout_log"
        result = db.fetch_one(count_query)
        entry_count = result['count'] if result else 0

        if entry_count == 0:
            return 0

        # Delete all entries
        delete_query = "DELETE FROM workout_log"
        db.execute_query(delete_query)

        logger.info(f"Cleared {entry_count} entries from workout log")
        return entry_count
