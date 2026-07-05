"""Seed the worktree DB with fixtures that exercise §4 thumbnail variants.

Idempotent: clears `user_selection` + `workout_log` before inserting.
Run only in a worktree -- the DB has skip-worktree applied so the
modified file stays out of the index.
"""
from __future__ import annotations

import sys

from utils.database import DatabaseHandler


# (exercise_name, routine, sets, min_reps, max_reps, rir, weight)
PLAN_FIXTURES = [
    ("Band Good Morning", "GYM - Full Body - Workout A", 3, 8, 12, 2, 30.0),
    ("Ankle Circle", "GYM - Full Body - Workout A", 2, 10, 15, 3, 0.0),
    ("Band Lateral Raise", "GYM - Full Body - Workout A", 3, 12, 15, 2, 7.5),
    ("Band Bench Press", "GYM - Full Body - Workout A", 3, 8, 12, 2, 20.0),
    ("Squat", "GYM - Full Body - Workout A", 4, 5, 8, 2, 100.0),
    ("Bench Press", "GYM - Full Body - Workout A", 4, 6, 10, 2, 80.0),
]


def main() -> int:
    with DatabaseHandler() as db:
        catalogue_rows = db.fetch_all(
            "SELECT exercise_name FROM exercises WHERE exercise_name IN ({})".format(
                ",".join("?" * len(PLAN_FIXTURES))
            ),
            tuple(name for name, *_ in PLAN_FIXTURES),
        )
        catalogue = {row["exercise_name"] for row in catalogue_rows}
        missing = [name for name, *_ in PLAN_FIXTURES if name not in catalogue]
        if missing:
            print(f"ERROR: catalogue missing exercises: {missing}", file=sys.stderr)
            return 1

        db.execute_query("DELETE FROM workout_log")
        db.execute_query("DELETE FROM user_selection")

        for name, routine, sets, min_reps, max_reps, rir, weight in PLAN_FIXTURES:
            db.execute_query(
                """
                INSERT INTO user_selection (routine, exercise, sets, min_rep_range, max_rep_range, rir, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (routine, name, sets, min_reps, max_reps, rir, weight),
            )

        plan_rows = db.fetch_all(
            "SELECT id, routine, exercise, sets, min_rep_range, max_rep_range, rir, weight FROM user_selection"
        )
        for row in plan_rows:
            db.execute_query(
                """
                INSERT INTO workout_log (
                    workout_plan_id, routine, exercise,
                    planned_sets, planned_min_reps, planned_max_reps,
                    planned_rir, planned_weight,
                    scored_min_reps, scored_max_reps, scored_rir, scored_weight
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"], row["routine"], row["exercise"],
                    row["sets"], row["min_rep_range"], row["max_rep_range"],
                    row["rir"], row["weight"],
                    row["min_rep_range"], row["max_rep_range"], max(0, row["rir"] - 1), row["weight"],
                ),
            )

        plan_count = db.fetch_one("SELECT COUNT(*) AS c FROM user_selection")["c"]
        log_count = db.fetch_one("SELECT COUNT(*) AS c FROM workout_log")["c"]
        thumb_count = db.fetch_one(
            "SELECT COUNT(*) AS c FROM user_selection us "
            "JOIN exercises e ON us.exercise = e.exercise_name "
            "WHERE e.media_path IS NOT NULL"
        )["c"]
        print(f"Seeded {plan_count} plan rows, {log_count} log rows, "
              f"{thumb_count} of which have media_path populated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
