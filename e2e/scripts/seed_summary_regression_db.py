"""Seed a deterministic database for Puppeteer summary regression checks.

This script is intentionally narrow: it creates one exercise and one plan row,
plus multiple workout_log entries for the same plan item to validate
session-summary inflation behavior.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import utils.config as config


def main() -> None:
    db_file = os.environ.get("DB_FILE")
    if not db_file:
        raise RuntimeError("DB_FILE env var is required")

    # Ensure runtime config points to the requested DB before importing DB users.
    config.DB_FILE = db_file

    from utils.db_initializer import initialize_database
    from utils.database import DatabaseHandler

    initialize_database(force=True)

    with DatabaseHandler() as db:
        # Start from clean state for deterministic assertions.
        db.execute_query("DELETE FROM workout_log")
        db.execute_query("DELETE FROM user_selection")
        db.execute_query("DELETE FROM exercise_isolated_muscles")
        db.execute_query("DELETE FROM exercises")

        db.execute_query(
            """
            INSERT INTO exercises (
                exercise_name,
                primary_muscle_group,
                secondary_muscle_group,
                tertiary_muscle_group,
                force,
                equipment,
                mechanic,
                utility,
                difficulty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Seed Bench",
                "Chest",
                None,
                None,
                "Push",
                "Barbell",
                "Compound",
                "Basic",
                "Intermediate",
            ),
        )

        db.execute_query(
            """
            INSERT INTO user_selection (
                routine,
                exercise,
                sets,
                min_rep_range,
                max_rep_range,
                rir,
                rpe,
                weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("Seed Routine", "Seed Bench", 12, 8, 10, 2, 8.0, 100.0),
        )

        inserted = db.fetch_one(
            "SELECT id, routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight FROM user_selection LIMIT 1"
        )
        if not inserted:
            raise RuntimeError("Failed to seed user_selection row")

        plan_id = inserted["id"]
        routine = inserted["routine"]
        exercise = inserted["exercise"]
        sets = inserted["sets"]
        min_reps = inserted["min_rep_range"]
        max_reps = inserted["max_rep_range"]
        rir = inserted["rir"]
        rpe = inserted["rpe"]
        weight = inserted["weight"]

        # Four logged sessions for the same plan row.
        session_dates = (
            "2026-02-01 09:00:00",
            "2026-02-03 09:00:00",
            "2026-02-05 09:00:00",
            "2026-02-07 09:00:00",
        )
        for created_at in session_dates:
            db.execute_query(
                """
                INSERT INTO workout_log (
                    workout_plan_id,
                    routine,
                    exercise,
                    planned_sets,
                    planned_min_reps,
                    planned_max_reps,
                    planned_rir,
                    planned_rpe,
                    planned_weight,
                    scored_weight,
                    scored_min_reps,
                    scored_max_reps,
                    scored_rir,
                    scored_rpe,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_id,
                    routine,
                    exercise,
                    sets,
                    min_reps,
                    max_reps,
                    rir,
                    rpe,
                    weight,
                    weight,
                    min_reps,
                    max_reps,
                    rir,
                    rpe,
                    created_at,
                ),
            )


if __name__ == "__main__":
    main()
