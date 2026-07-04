"""Tests for utils/auto_backup.py's API-response metadata helper.

`describe_snapshot()` turns the `Path | None` returned by
`create_startup_backup()` into the JSON-safe shape the `/erase-data` route
hands to the frontend's `showAutoBackupBanner()` (Track B WPB.8). It is
intentionally decoupled from the SQLite copy itself so the erase route's
response contract can be exercised without touching a real database file.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3

import utils.auto_backup as auto_backup
import utils.config
from utils.auto_backup import describe_snapshot


def test_describe_snapshot_returns_none_when_no_snapshot_taken():
    assert describe_snapshot(None) is None


def test_describe_snapshot_returns_filename_only():
    snapshot_path = Path("data") / "auto_backup" / "database_20260704_153012.db"

    result = describe_snapshot(snapshot_path)

    assert result == {"filename": "database_20260704_153012.db"}


def test_describe_snapshot_strips_directory_regardless_of_path_shape():
    # Accepts a bare string path too, not just a Path instance.
    result = describe_snapshot("/some/absolute/dir/database_20260101_000000.db")

    assert result == {"filename": "database_20260101_000000.db"}


def _seed_exercises(db_path: Path, count: int) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE exercises (exercise_name TEXT PRIMARY KEY)")
        conn.executemany(
            "INSERT INTO exercises (exercise_name) VALUES (?)",
            [(f"Exercise {index}",) for index in range(count)],
        )


def test_create_startup_backup_skips_in_test_mode(tmp_path, monkeypatch):
    live_db = tmp_path / "database.db"
    _seed_exercises(live_db, auto_backup.MIN_EXERCISES_TO_BACKUP)
    monkeypatch.setattr(utils.config, "DB_FILE", str(live_db))
    monkeypatch.setenv("TESTING", "1")

    assert auto_backup.create_startup_backup() is None
    assert not (tmp_path / auto_backup.AUTO_BACKUP_DIRNAME).exists()


def test_create_startup_backup_skips_missing_sparse_and_invalid_databases(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("TESTING", raising=False)

    missing = tmp_path / "missing.db"
    monkeypatch.setattr(utils.config, "DB_FILE", str(missing))
    assert auto_backup.create_startup_backup() is None

    sparse = tmp_path / "sparse.db"
    _seed_exercises(sparse, auto_backup.MIN_EXERCISES_TO_BACKUP - 1)
    monkeypatch.setattr(utils.config, "DB_FILE", str(sparse))
    assert auto_backup.create_startup_backup() is None

    invalid = tmp_path / "invalid.db"
    with sqlite3.connect(invalid) as conn:
        conn.execute("CREATE TABLE something_else (id INTEGER)")
    monkeypatch.setattr(utils.config, "DB_FILE", str(invalid))
    assert auto_backup.create_startup_backup() is None
    assert not (tmp_path / auto_backup.AUTO_BACKUP_DIRNAME).exists()


def test_create_startup_backup_copies_database_and_rotates_old_snapshots(
    tmp_path, monkeypatch
):
    live_db = tmp_path / "database.db"
    _seed_exercises(live_db, auto_backup.MIN_EXERCISES_TO_BACKUP)
    backup_dir = tmp_path / auto_backup.AUTO_BACKUP_DIRNAME
    backup_dir.mkdir()
    old_paths = []
    for index in range(auto_backup.AUTO_BACKUP_KEEP):
        path = backup_dir / f"database_20000101_00000{index}.db"
        path.write_bytes(b"old")
        os.utime(path, (index + 1, index + 1))
        old_paths.append(path)

    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setattr(utils.config, "DB_FILE", str(live_db))

    snapshot = auto_backup.create_startup_backup()

    assert snapshot is not None
    assert snapshot.parent == backup_dir
    assert snapshot.name.startswith("database_")
    assert snapshot.suffix == ".db"
    with sqlite3.connect(snapshot) as conn:
        count = conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
    assert count == auto_backup.MIN_EXERCISES_TO_BACKUP
    snapshots = list(backup_dir.glob("database_*.db"))
    assert len(snapshots) == auto_backup.AUTO_BACKUP_KEEP
    assert not old_paths[0].exists()


def test_create_startup_backup_returns_none_when_sqlite_open_fails(
    tmp_path, monkeypatch
):
    live_db = tmp_path / "database.db"
    live_db.touch()
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setattr(utils.config, "DB_FILE", str(live_db))

    def fail_connect(_path):
        raise sqlite3.OperationalError("forced open failure")

    monkeypatch.setattr(auto_backup.sqlite3, "connect", fail_connect)

    assert auto_backup.create_startup_backup() is None
