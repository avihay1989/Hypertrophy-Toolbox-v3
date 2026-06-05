"""Generate a historical-schema SQLite DB to exercise the startup migration path.

Produces a DB as it looked BEFORE several startup migrations landed:
- ``user_selection`` has no ``exercise_order`` column (added later by
  ``initialize_exercise_order``), and none of the newer ``superset_group`` /
  ``execution_style`` / ``time_cap_seconds`` columns.
- None of the ``add_*_table`` tables exist yet (``progression_goals``,
  ``volume_plans`` / ``muscle_volumes``, ``user_profile*``,
  ``body_composition_snapshots``, the strength-calibration tables,
  ``program_backups`` / ``program_backup_items``).

Booting ``app.py`` against this DB must upgrade it in place without error and
preserve the seeded program row (CLAUDE.md §5 "exercise_order column"). The base
schema is produced by the app's own ``initialize_database`` so it never drifts
from production; this script only *withholds* the later migrations.

Used by the manual Deep Gate workflow (``.github/workflows/deep-gate.yml``).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def build(output: Path) -> Path:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    # Point the app's initializer at the target file and build ONLY the base
    # schema (exercises, exercise_isolated_muscles, user_selection, workout_log).
    # The add_*_table helpers and initialize_exercise_order are deliberately not
    # run here — that's what the startup migration under test must do.
    import utils.config

    utils.config.DB_FILE = str(output)
    from utils.db_initializer import initialize_database

    initialize_database(force=True)

    con = sqlite3.connect(str(output))
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute(
            "INSERT OR IGNORE INTO exercises (exercise_name, primary_muscle_group) VALUES (?, ?)",
            ("Legacy Bench Press", "Chest"),
        )
        con.execute(
            """
            INSERT INTO user_selection
                (routine, exercise, sets, min_rep_range, max_rep_range, rir, rpe, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("Legacy Routine", "Legacy Bench Press", 3, 6, 8, 2, 8.0, 100.0),
        )
        # Age the DB further so the boot must re-add these columns too. DROP COLUMN
        # needs SQLite 3.35+; if unavailable, the column simply stays (still a
        # valid, if slightly less old, fixture).
        for column in ("superset_group", "execution_style", "time_cap_seconds"):
            try:
                con.execute(f"ALTER TABLE user_selection DROP COLUMN {column}")
            except sqlite3.OperationalError:
                pass
        con.commit()
    finally:
        con.close()

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "data" / "database.db",
        help="Path to write the historical-schema DB (default: data/database.db)",
    )
    args = parser.parse_args()
    print(build(args.output))


if __name__ == "__main__":
    main()
