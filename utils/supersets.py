"""Superset validation, persistence, and antagonist suggestions.

The workout-plan routes retain HTTP parsing and response-envelope shaping;
this module owns superset domain rules and all related database access.
"""
from __future__ import annotations

from typing import Any, cast

from utils.constants import ANTAGONIST_PAIRS
from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()


class SupersetServiceError(Exception):
    """A user-facing service outcome mapped by the HTTP route."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _column_exists(
    db: DatabaseHandler, table_name: str, column_name: str
) -> bool:
    columns = db.fetch_all(f"PRAGMA table_info({table_name})")
    return any(column['name'] == column_name for column in columns)


def _validate_superset_link_request(
    db: DatabaseHandler, exercise_ids: list
):
    # Check if superset_group column exists
    if not _column_exists(db, 'user_selection', 'superset_group'):
        return None, (
            "INTERNAL_ERROR",
            "Superset feature not available - database migration required",
            500,
        )

    # Fetch both exercises. Deliberately no ORDER BY: preserve the historical
    # row ordering used for routine/name selection and response messages.
    exercises = db.fetch_all(
        "SELECT id, routine, exercise, superset_group "
        "FROM user_selection WHERE id IN (?, ?)",
        tuple(exercise_ids),
    )

    if len(exercises) != 2:
        return None, (
            "NOT_FOUND",
            "One or both exercises not found",
            404,
        )

    ex1, ex2 = exercises[0], exercises[1]

    # Validate same routine
    if ex1['routine'] != ex2['routine']:
        return None, (
            "VALIDATION_ERROR",
            f"Supersets must be within the same routine. "
            f"'{ex1['exercise']}' is in '{ex1['routine']}' but "
            f"'{ex2['exercise']}' is in '{ex2['routine']}'",
            400,
        )

    # Validate neither is already in a superset
    if ex1.get('superset_group'):
        return None, (
            "VALIDATION_ERROR",
            f"'{ex1['exercise']}' is already in a superset. Unlink it first.",
            400,
        )
    if ex2.get('superset_group'):
        return None, (
            "VALIDATION_ERROR",
            f"'{ex2['exercise']}' is already in a superset. Unlink it first.",
            400,
        )

    return exercises, None


def _apply_superset_link(
    db: DatabaseHandler, exercise_ids: list, routine_name: str
):
    import time

    superset_group = f"SS-{routine_name}-{int(time.time())}"

    # Update both exercises with the superset group
    db.execute_query(
        "UPDATE user_selection SET superset_group = ? WHERE id IN (?, ?)",
        (superset_group, exercise_ids[0], exercise_ids[1]),
    )

    # Fetch updated exercises with full metadata. Deliberately no ORDER BY.
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


def link_superset(exercise_ids: list[int]) -> dict[str, Any]:
    """Validate and persist a two-exercise superset."""
    with DatabaseHandler() as db:
        exercises, error = _validate_superset_link_request(db, exercise_ids)
        if error:
            raise SupersetServiceError(*error)

        validated_exercises = cast(list[dict[str, Any]], exercises)
        ex1, ex2 = validated_exercises[0], validated_exercises[1]
        routine_name = ex1['routine']

        superset_group, updated_exercises = _apply_superset_link(
            db, exercise_ids, routine_name
        )

        logger.info(
            "Superset created",
            extra={
                'superset_group': superset_group,
                'routine': routine_name,
                'exercise_1': ex1['exercise'],
                'exercise_2': ex2['exercise'],
            },
        )

        return {
            "superset_group": superset_group,
            "exercises": [dict(exercise) for exercise in updated_exercises],
            "exercise_1_name": ex1['exercise'],
            "exercise_2_name": ex2['exercise'],
        }


def unlink_superset(
    exercise_id: Any = None, superset_group: Any = None
) -> dict[str, Any]:
    """Unlink every exercise in the resolved superset group."""
    with DatabaseHandler() as db:
        # Check if superset_group column exists
        if not _column_exists(db, 'user_selection', 'superset_group'):
            raise SupersetServiceError(
                "INTERNAL_ERROR",
                "Superset feature not available - database migration required",
                500,
            )

        if exercise_id:
            # Keep historical coercion: invalid truthy values raise and become
            # the route's generic 500 rather than a validation response.
            exercise = db.fetch_one(
                "SELECT id, exercise, superset_group "
                "FROM user_selection WHERE id = ?",
                (int(exercise_id),),
            )

            if not exercise:
                raise SupersetServiceError(
                    "NOT_FOUND", "Exercise not found", 404
                )

            if not exercise.get('superset_group'):
                raise SupersetServiceError(
                    "VALIDATION_ERROR",
                    f"'{exercise['exercise']}' is not in a superset",
                    400,
                )

            superset_group = exercise['superset_group']

        # Get all exercises in the superset group. Deliberately no ORDER BY:
        # output ID/name and message order remain database-defined as before.
        superset_exercises = db.fetch_all(
            "SELECT id, exercise FROM user_selection WHERE superset_group = ?",
            (superset_group,),
        )

        if not superset_exercises:
            raise SupersetServiceError(
                "NOT_FOUND",
                f"No exercises found with superset group '{superset_group}'",
                404,
            )

        db.execute_query(
            "UPDATE user_selection SET superset_group = NULL "
            "WHERE superset_group = ?",
            (superset_group,),
        )

        unlinked_ids = [exercise['id'] for exercise in superset_exercises]
        unlinked_names = [exercise['exercise'] for exercise in superset_exercises]

        logger.info(
            "Superset unlinked",
            extra={
                'superset_group': superset_group,
                'unlinked_ids': unlinked_ids,
                'exercises': unlinked_names,
            },
        )

        return {
            "unlinked_ids": unlinked_ids,
            "unlinked_names": unlinked_names,
        }


def _group_exercises_by_routine(exercises: list) -> dict:
    routines = {}
    for exercise in exercises:
        routine = exercise['routine']
        if routine not in routines:
            routines[routine] = []
        routines[routine].append(exercise)
    return routines


def _find_antagonist_pairings(
    routine_name: str, routine_exercises: list
) -> list:
    suggestions = []

    # Skip exercises already in supersets
    available = [
        exercise
        for exercise in routine_exercises
        if not exercise.get('superset_group')
    ]

    paired = set()

    for index, exercise_1 in enumerate(available):
        if exercise_1['id'] in paired:
            continue

        muscle_1 = (
            exercise_1.get('primary_muscle_group') or ''
        ).lower()
        if not muscle_1:
            continue

        best_partner = None
        best_reason = None

        for partner_index, exercise_2 in enumerate(available):
            if index == partner_index or exercise_2['id'] in paired:
                continue

            muscle_2 = (
                exercise_2.get('primary_muscle_group') or ''
            ).lower()
            if not muscle_2:
                continue

            # Check for antagonist pairing
            antagonists = ANTAGONIST_PAIRS.get(muscle_1, [])
            if muscle_2 in antagonists or any(
                antagonist in muscle_2 for antagonist in antagonists
            ):
                best_partner = exercise_2
                best_reason = (
                    f"Antagonist pair: {muscle_1.title()} / "
                    f"{muscle_2.title()} - allows one muscle to rest while "
                    "the other works"
                )
                break

        if best_partner:
            suggestions.append({
                "routine": routine_name,
                "exercise_1": {
                    "id": exercise_1['id'],
                    "name": exercise_1['exercise'],
                    "muscle": muscle_1.title(),
                },
                "exercise_2": {
                    "id": best_partner['id'],
                    "name": best_partner['exercise'],
                    "muscle": (
                        best_partner.get('primary_muscle_group') or ''
                    ).title(),
                },
                "reason": best_reason,
                "benefit": "Saves time without compromising performance",
            })
            paired.add(exercise_1['id'])
            paired.add(best_partner['id'])

    return suggestions


def get_superset_suggestions(routine: Any = None) -> dict[str, Any]:
    """Return antagonist-pair suggestions, optionally for one routine."""
    with DatabaseHandler() as db:
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
            return {
                "suggestions": [],
                "message": "No exercises found in workout plan",
            }

        routines = _group_exercises_by_routine(exercises)
        suggestions = []

        for routine_name, routine_exercises in routines.items():
            suggestions.extend(
                _find_antagonist_pairings(routine_name, routine_exercises)
            )

        logger.info(
            "Superset suggestions generated",
            extra={
                'routine_filter': routine,
                'suggestion_count': len(suggestions),
            },
        )

        return {
            "suggestions": suggestions,
            "total_pairs": len(suggestions),
        }
