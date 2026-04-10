import sqlite3
from pathlib import Path

import utils.config
from utils import database as database_module
from utils import db_initializer


def test_seed_db_paths_point_to_backup_database():
    expected_suffix = Path("data") / "backup" / "database.db"

    assert db_initializer.SEED_DB_PATH.as_posix().endswith(expected_suffix.as_posix())
    assert database_module.SEED_DB_PATH.as_posix().endswith(expected_suffix.as_posix())
    assert db_initializer.SEED_DB_PATH == database_module.SEED_DB_PATH


def test_initialize_database_seeds_from_canonical_backup_path(monkeypatch, tmp_path):
    test_db_path = tmp_path / "seed-path-regression.db"

    monkeypatch.setattr(utils.config, "DB_FILE", str(test_db_path))
    monkeypatch.delenv("TESTING", raising=False)

    db_initializer.initialize_database(force=True)

    connection = sqlite3.connect(test_db_path)
    try:
        row = connection.execute("SELECT COUNT(*) FROM exercises").fetchone()
    finally:
        connection.close()

    assert row is not None
    assert row[0] >= db_initializer.MIN_EXERCISE_ROWS
