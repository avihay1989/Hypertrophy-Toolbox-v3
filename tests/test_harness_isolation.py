import sqlite3
from pathlib import Path

import utils.config
from routes.workout_plan import initialize_exercise_order
from utils.database import DatabaseHandler, add_progression_goals_table, add_volume_tracking_tables
from utils.db_initializer import initialize_database
from utils.program_backup import initialize_backup_tables


def _initialize_database_at_path(db_path: Path) -> None:
    original_db_file = utils.config.DB_FILE
    utils.config.DB_FILE = str(db_path)
    try:
        initialize_database(force=True)
        add_progression_goals_table()
        add_volume_tracking_tables()
        initialize_exercise_order()
        initialize_backup_tables()
    finally:
        utils.config.DB_FILE = original_db_file


def test_database_handler_uses_the_test_scoped_database_path(app, test_db_path):
    with DatabaseHandler() as db:
        assert Path(db.database_path) == Path(test_db_path)


def test_distinct_test_databases_do_not_share_sqlite_locks(tmp_path):
    primary_db = tmp_path / "primary.db"
    secondary_db = tmp_path / "secondary.db"
    _initialize_database_at_path(primary_db)
    _initialize_database_at_path(secondary_db)

    primary_connection = sqlite3.connect(primary_db, timeout=0.1, isolation_level=None)
    secondary_connection = sqlite3.connect(secondary_db, timeout=0.1)

    try:
        primary_connection.execute("PRAGMA foreign_keys = ON")
        secondary_connection.execute("PRAGMA foreign_keys = ON")

        primary_connection.execute("BEGIN EXCLUSIVE")
        primary_connection.execute(
            "INSERT INTO exercises (exercise_name) VALUES (?)",
            ("locked-db-exercise",),
        )

        secondary_connection.execute(
            "INSERT INTO exercises (exercise_name) VALUES (?)",
            ("isolated-db-exercise",),
        )
        secondary_connection.commit()

        row = secondary_connection.execute("SELECT COUNT(*) FROM exercises").fetchone()
        assert row is not None
        assert row[0] == 1
    finally:
        try:
            primary_connection.rollback()
        finally:
            primary_connection.close()
            secondary_connection.close()
