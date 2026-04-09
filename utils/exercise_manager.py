from typing import Any, Dict, Optional

from utils.database import DatabaseHandler
from utils.filter_predicates import FilterPredicates
from utils.logger import get_logger
from utils.normalization import normalize_exercise_row, split_csv


logger = get_logger()


class ExerciseManager:
    """High-level operations for querying and mutating exercise data."""

    @staticmethod
    def get_exercises(filters: Optional[Dict[str, Any]] = None):
        """Fetch exercises from the database, optionally filtered via predicates."""
        return FilterPredicates.get_exercises(filters)

    @staticmethod
    def add_exercise(
        routine: str,
        exercise: str,
        sets: int,
        min_rep_range: int,
        max_rep_range: int,
        rir: Optional[int],
        weight: float,
        rpe: Optional[float] = None,
    ) -> str:
        """Add a selection entry, preventing duplicate routine/exercise pairs."""
        if not all([routine, exercise, sets, min_rep_range, max_rep_range, weight]):
            logger.warning("Rejecting add_exercise due to missing fields")
            return "Error: Missing required fields."

        if int(min_rep_range) > int(max_rep_range):
            logger.warning("Rejecting add_exercise: min_rep_range (%s) > max_rep_range (%s)", min_rep_range, max_rep_range)
            return "Error: Min rep range cannot exceed max rep range."

        if rir is not None and int(rir) < 0:
            logger.warning("Rejecting add_exercise: negative RIR (%s)", rir)
            return "Error: RIR cannot be negative."

        if float(weight) < 0:
            logger.warning("Rejecting add_exercise: negative weight (%s)", weight)
            return "Error: Weight cannot be negative."

        if float(weight) > 1000:
            logger.warning("Rejecting add_exercise: unreasonable weight (%s)", weight)
            return "Error: Weight exceeds maximum allowed value (1000)."

        duplicate_check_query = (
            "SELECT COUNT(*) AS count FROM user_selection WHERE routine = ? AND exercise = ?"
        )
        max_order_query = "SELECT COALESCE(MAX(exercise_order), 0) AS max_order FROM user_selection"
        insert_query_with_order = (
            "INSERT INTO user_selection "
            "(routine, exercise, sets, min_rep_range, max_rep_range, rir, weight, rpe, exercise_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        insert_query_without_order = (
            "INSERT INTO user_selection "
            "(routine, exercise, sets, min_rep_range, max_rep_range, rir, weight, rpe) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )

        try:
            with DatabaseHandler() as db:
                duplicate = db.fetch_one(duplicate_check_query, (routine, exercise))
                if duplicate and duplicate.get("count", 0) > 0:
                    logger.info("Duplicate exercise rejected for routine=%s exercise=%s", routine, exercise)
                    return "Exercise already exists in this routine."

                columns = db.fetch_all("PRAGMA table_info(user_selection)")
                has_exercise_order = any(row.get("name") == "exercise_order" for row in columns)

                if has_exercise_order:
                    # Place new rows at the bottom when exercise_order exists.
                    max_order_result = db.fetch_one(max_order_query)
                    next_order = (max_order_result.get("max_order", 0) or 0) + 1
                    db.execute_query(
                        insert_query_with_order,
                        (routine, exercise, sets, min_rep_range, max_rep_range, rir, weight, rpe, next_order),
                    )
                    logger.debug(
                        "Inserted exercise '%s' into routine '%s' with order %d",
                        exercise,
                        routine,
                        next_order,
                    )
                else:
                    # Backward-compatible insert for legacy schemas.
                    db.execute_query(
                        insert_query_without_order,
                        (routine, exercise, sets, min_rep_range, max_rep_range, rir, weight, rpe),
                    )
                    logger.warning(
                        "Inserted exercise '%s' without exercise_order (legacy schema detected)",
                        exercise,
                    )
                return "Exercise added successfully."
        except Exception as exc:  # pragma: no cover - logged for observability
            logger.exception("Database error while adding exercise")
            return f"Database error: {exc}"

    @staticmethod
    def delete_exercise(exercise_id: int) -> None:
        """Delete a user_selection entry by primary key."""
        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM user_selection WHERE id = ?", (exercise_id,))
            logger.debug("Removed user_selection row id=%s", exercise_id)

    # -- Exercise catalogue maintenance -------------------------------------
    @staticmethod
    def save_exercise(exercise_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update an exercise row after normalising its payload."""
        normalised = normalize_exercise_row(exercise_data)
        exercise_name = normalised.get("exercise_name")
        if not exercise_name:
            raise ValueError("exercise_name is required")

        columns = [
            "exercise_name",
            "primary_muscle_group",
            "secondary_muscle_group",
            "tertiary_muscle_group",
            "advanced_isolated_muscles",
            "utility",
            "grips",
            "stabilizers",
            "synergists",
            "force",
            "equipment",
            "mechanic",
            "difficulty",
        ]

        placeholders = ", ".join([":" + col for col in columns])
        update_clause = ", ".join(
            [f"{col} = excluded.{col}" for col in columns if col != "exercise_name"]
        )

        with DatabaseHandler() as db:
            conflict = db.fetch_one(
                "SELECT exercise_name FROM exercises WHERE exercise_name = ? COLLATE NOCASE",
                (exercise_name,),
            )
            if conflict and conflict["exercise_name"] != exercise_name:
                raise ValueError(
                    f"Exercise '{exercise_name}' conflicts with existing entry '{conflict['exercise_name']}'"
                )

            db.execute_query(
                (
                    "INSERT INTO exercises ({cols}) VALUES ({vals}) "
                    "ON CONFLICT(exercise_name) DO UPDATE SET {updates}"
                ).format(cols=", ".join(columns), vals=placeholders, updates=update_clause),
                normalised,
            )
            ExerciseManager._sync_isolated_muscles(db, exercise_name, normalised.get("advanced_isolated_muscles"))

        return normalised

    @staticmethod
    def remove_exercise_by_name(exercise_name: str) -> None:
        """Delete an exercise and any associated isolated muscle mappings."""
        with DatabaseHandler() as db:
            db.execute_query("DELETE FROM exercise_isolated_muscles WHERE exercise_name = ?", (exercise_name,))
            db.execute_query("DELETE FROM exercises WHERE exercise_name = ?", (exercise_name,))
            logger.debug("Removed exercise '%s'", exercise_name)

    @staticmethod
    def fetch_unique_values(table: str, column: str):
        """Fetch distinct values for a given table/column pair."""
        query = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL ORDER BY {column} ASC"
        with DatabaseHandler() as db:
            results = db.fetch_all(query)
            return [row[column] for row in results]

    # -- Internal helpers ---------------------------------------------------
    @staticmethod
    def _sync_isolated_muscles(db: DatabaseHandler, exercise_name: str, csv_muscles: Optional[str]) -> None:
        db.execute_query(
            "DELETE FROM exercise_isolated_muscles WHERE exercise_name = ?",
            (exercise_name,),
        )
        muscles = [muscle for muscle in split_csv(csv_muscles) if muscle]
        if muscles:
            db.executemany(
                "INSERT OR IGNORE INTO exercise_isolated_muscles (exercise_name, muscle) VALUES (?, ?)",
                [(exercise_name, muscle) for muscle in muscles],
            )


# Public interface shortcuts -------------------------------------------------
get_exercises = ExerciseManager.get_exercises
add_exercise = ExerciseManager.add_exercise
delete_exercise = ExerciseManager.delete_exercise
fetch_unique_values = ExerciseManager.fetch_unique_values
save_exercise = ExerciseManager.save_exercise
remove_exercise_by_name = ExerciseManager.remove_exercise_by_name
