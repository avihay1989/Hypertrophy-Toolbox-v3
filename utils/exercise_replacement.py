"""Exercise-replacement selection and persistence service.

Routes retain request parsing and response shaping.  This module owns the
candidate query, case-insensitive routine de-duplication, selection/retry
policy, and the exercise-name swap in ``user_selection``.
"""
from __future__ import annotations

from typing import Any

from utils.database import DatabaseHandler
from utils.logger import get_logger

logger = get_logger()


class ExerciseReplacementError(Exception):
    """A user-facing replacement outcome mapped by the HTTP route."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        reason: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.reason = reason


def suggest_replacement_exercise(
    current_exercise: str,
    muscle: str,
    equipment: str,
    candidates: list[str],
    strategy: str = "fallback",
):
    """Suggest a replacement exercise from the candidate pool."""
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
                top_candidates.extend(
                    [name for score, name in scored if score == second_score]
                )

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


def _build_replacement_candidates(
    db: DatabaseHandler,
    routine: str,
    muscle: str,
    equipment: str,
    current_exercise: str,
) -> list[str]:
    candidates_query = """
        SELECT exercise_name
        FROM exercises
        WHERE LOWER(primary_muscle_group) = LOWER(?)
          AND LOWER(equipment) = LOWER(?)
          AND LOWER(exercise_name) != LOWER(?)
    """
    candidate_rows = db.fetch_all(
        candidates_query, (muscle, equipment, current_exercise)
    )
    candidate_names = [row['exercise_name'] for row in candidate_rows]

    routine_exercises_query = """
        SELECT exercise FROM user_selection WHERE routine = ?
    """
    routine_exercises = db.fetch_all(routine_exercises_query, (routine,))
    routine_exercise_names_lower = {
        row['exercise'].lower() for row in routine_exercises
    }

    return [
        candidate
        for candidate in candidate_names
        if candidate.lower() not in routine_exercise_names_lower
    ]


def _column_exists(db: DatabaseHandler, table_name: str, column_name: str) -> bool:
    columns = db.fetch_all(f"PRAGMA table_info({table_name})")
    return any(column['name'] == column_name for column in columns)


def _perform_exercise_swap(
    db: DatabaseHandler, exercise_id: int, new_exercise: str
) -> dict[str, Any]:
    db.execute_query(
        "UPDATE user_selection SET exercise = ? WHERE id = ?",
        (new_exercise, exercise_id),
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

    updated_row: dict[str, Any] = (
        dict(updated_row_result) if updated_row_result else {}
    )

    if _column_exists(db, 'user_selection', 'exercise_order'):
        order_row = db.fetch_one(
            "SELECT exercise_order FROM user_selection WHERE id = ?",
            (exercise_id,),
        )
        if order_row and order_row.get('exercise_order') is not None:
            updated_row['exercise_order'] = order_row['exercise_order']

    return updated_row


def replace_exercise_for_selection(
    exercise_id: int, strategy: str = "fallback"
) -> dict[str, Any]:
    """Select and persist a replacement for one workout-plan row."""
    with DatabaseHandler() as db:
        current_row = _fetch_current_exercise_details(db, exercise_id)

        if not current_row:
            raise ExerciseReplacementError(
                "NOT_FOUND",
                "Exercise not found in workout plan",
                404,
                "not_found",
            )

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
                    'equipment': equipment,
                },
            )
            raise ExerciseReplacementError(
                "VALIDATION_ERROR",
                "Exercise is missing muscle group or equipment metadata",
                400,
                "missing_metadata",
            )

        valid_candidates = _build_replacement_candidates(
            db, routine, muscle, equipment, current_exercise
        )

        if not valid_candidates:
            raise ExerciseReplacementError(
                "NO_CANDIDATES",
                f"No alternative exercises found for {muscle} with {equipment}",
                200,
                "no_candidates",
            )

        new_exercise = suggest_replacement_exercise(
            current_exercise,
            muscle,
            equipment,
            valid_candidates,
            strategy,
        )

        if not new_exercise:
            raise ExerciseReplacementError(
                "SELECTION_FAILED",
                "Failed to select replacement exercise",
                200,
                "selection_failed",
            )

        duplicate_check = db.fetch_one(
            "SELECT id FROM user_selection "
            "WHERE routine = ? AND LOWER(exercise) = LOWER(?)",
            (routine, new_exercise),
        )

        if duplicate_check:
            remaining_candidates = [
                candidate
                for candidate in valid_candidates
                if candidate.lower() != new_exercise.lower()
            ]
            if remaining_candidates:
                new_exercise = suggest_replacement_exercise(
                    current_exercise,
                    muscle,
                    equipment,
                    remaining_candidates,
                    "fallback",
                )
                if not new_exercise:
                    raise ExerciseReplacementError(
                        "SELECTION_FAILED",
                        "Failed to select replacement exercise",
                        200,
                        "selection_failed",
                    )
            else:
                raise ExerciseReplacementError(
                    "DUPLICATE",
                    "All candidate exercises are already in this routine",
                    200,
                    "duplicate",
                )

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
                'candidates_available': len(valid_candidates),
            },
        )

        remaining_options = len([
            candidate
            for candidate in valid_candidates
            if candidate.lower() != new_exercise.lower()
        ])

        return {
            "updated_row": updated_row,
            "old_exercise": current_exercise,
            "new_exercise": new_exercise,
            "remaining_options": remaining_options,
        }
